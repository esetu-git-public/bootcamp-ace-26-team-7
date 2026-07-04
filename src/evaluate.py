import os
import torch
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from src.config import Config
from src.dataset import get_dataloaders
from src.model import get_resnet50

def run_evaluation():
    """Runs model validation on the test subset, saving the classification report and matrix."""
    _, _, test_loader = get_dataloaders()
    
    # Load model
    model = get_resnet50(num_classes=Config.NUM_CLASSES, pretrained=False)
    
    if not os.path.exists(Config.MODEL_SAVE_PATH):
        print(f"Error: Model checkpoint not found at '{Config.MODEL_SAVE_PATH}'. Train the model first.")
        return
        
    model.load_state_dict(torch.load(Config.MODEL_SAVE_PATH, map_location=Config.DEVICE))
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
    
    # ponytail: fallback if test set is empty
    if len(y_true) == 0:
        print("Test dataset is empty. Cannot run evaluation.")
        return
        
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="weighted")
    print(f"Test Accuracy: {acc:.4f}")
    print(f"Test Weighted F1: {f1:.4f}")
    
    report = classification_report(y_true, y_pred, target_names=Config.CLASSES)
    print("\nClassification Report:\n", report)
    
    # Save text report to reports directory
    os.makedirs(Config.REPORTS_DIR, exist_ok=True)
    report_text_path = os.path.join(Config.REPORTS_DIR, "classification_report.txt")
    with open(report_text_path, "w") as f:
        f.write(report)
    print(f"Saved classification report to {report_text_path}")
        
    # Generate and save confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=Config.CLASSES, yticklabels=Config.CLASSES)
    plt.title("Confusion Matrix")
    plt.ylabel("True Class")
    plt.xlabel("Predicted Class")
    
    cm_path = os.path.join(Config.REPORTS_DIR, "confusion_matrix.png")
    plt.savefig(cm_path)
    plt.close()
    print(f"Saved confusion matrix plot to {cm_path}")

if __name__ == "__main__":
    run_evaluation()
