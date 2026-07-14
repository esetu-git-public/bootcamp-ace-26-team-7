import os
import time
import torch
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from src.config import Config

try:
    import wandb
    _WANDB_AVAILABLE = True
except ModuleNotFoundError:
    wandb = None
    _WANDB_AVAILABLE = False
from src.dataset import get_dataloaders
from src.model import get_model

def run_evaluation(model_name=None):
    """Runs model validation on the test subset, saving the classification report and matrix."""
    model_name = model_name or Config.MODEL_NAME
    model_path = Config.get_model_path(model_name)
    _, _, test_loader = get_dataloaders()
    
    # Load model
    model = get_model(model_name=model_name, num_classes=Config.NUM_CLASSES, pretrained=False)
    
    if not os.path.exists(model_path):
        print(f"Error: Model checkpoint not found at '{model_path}'. Train the model first.")
        return
        
    model.load_state_dict(torch.load(model_path, map_location=Config.DEVICE))
    model = model.to(Config.DEVICE)
    model.eval()
    
    y_true = []
    y_pred = []
    
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(Config.DEVICE)
            outputs = model(images)
            _, preds = torch.max(outputs, 1)
            
            y_true.extend(labels.numpy())
            y_pred.extend(preds.cpu().numpy())
            
    # Compute metrics
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    
    if len(y_true) == 0:
        print("Test dataset is empty. Cannot run evaluation.")
        return
        
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    print(f"Test Accuracy: {acc:.4f}")
    print(f"Test Weighted F1: {f1:.4f}")
    
    report = classification_report(y_true, y_pred, target_names=Config.CLASSES, zero_division=0)
    print("\nClassification Report:\n", report)
    
    os.makedirs(Config.REPORTS_DIR, exist_ok=True)
    report_text_path = os.path.join(Config.REPORTS_DIR, f"classification_report_{model_name}.txt")
    with open(report_text_path, "w") as f:
        f.write(report)
    print(f"Saved classification report to {report_text_path}")
        
    # Generate and save confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=Config.CLASSES, yticklabels=Config.CLASSES)
    plt.title(f"Confusion Matrix — {model_name}")
    plt.ylabel("True Class")
    plt.xlabel("Predicted Class")
    
    cm_path = os.path.join(Config.REPORTS_DIR, f"confusion_matrix_{model_name}.png")
    plt.savefig(cm_path)
    plt.close()
    print(f"Saved confusion matrix plot to {cm_path}")
    
    # Log to wandb
    if _WANDB_AVAILABLE and Config.WANDB_ENABLED:
        wandb.init(
            project=Config.WANDB_PROJECT,
            entity=Config.WANDB_ENTITY,
            name=f"eval-{model_name}-{time.strftime('%Y%m%d-%H%M%S')}",
            config={"model": model_name}
        )
        wandb.log({
            "test_accuracy": acc,
            "test_weighted_f1": f1,
            "confusion_matrix": wandb.Image(cm_path),
        })
        wandb.log({"classification_report": wandb.Html(report.replace("\n", "<br>"))})
        # Per-class metrics table
        report_dict = classification_report(y_true, y_pred, target_names=Config.CLASSES, zero_division=0, output_dict=True)
        per_class_table = wandb.Table(columns=["class", "precision", "recall", "f1", "support"])
        for cls in Config.CLASSES:
            if cls in report_dict:
                per_class_table.add_data(
                    cls,
                    round(report_dict[cls]["precision"], 4),
                    round(report_dict[cls]["recall"], 4),
                    round(report_dict[cls]["f1-score"], 4),
                    int(report_dict[cls]["support"]),
                )
        wandb.log({"per_class_metrics": per_class_table})
        wandb.finish()

    # Return metrics for session tracking
    report_dict = classification_report(y_true, y_pred, target_names=Config.CLASSES, zero_division=0, output_dict=True)
    per_class = {}
    for cls in Config.CLASSES:
        if cls in report_dict:
            per_class[cls] = {
                "f1": round(report_dict[cls]["f1-score"], 4),
                "recall": round(report_dict[cls]["recall"], 4),
                "precision": round(report_dict[cls]["precision"], 4),
                "support": int(report_dict[cls]["support"]),
            }
    return {"accuracy": round(acc, 4), "weighted_f1": round(f1, 4), "per_class": per_class}

if __name__ == "__main__":
    run_evaluation()
