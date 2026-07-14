import os
import sys
import random
import time
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from tqdm.auto import tqdm

try:
    import wandb
    _WANDB_AVAILABLE = True
except ModuleNotFoundError:
    wandb = None
    _WANDB_AVAILABLE = False
from src.config import Config
from src.dataset import get_dataloaders
from src.model import get_model, unfreeze_for_finetune
from src.utils import plot_training_curves
from src.session import SessionTracker

def _get_classifier(model, model_name):
    if model_name == "resnet50":
        return model.fc
    elif model_name == "efficientnet_b0":
        return model.classifier
    elif model_name == "vit_b_16":
        return model.heads.head
    elif model_name == "mobilenet_v3_small":
        return model.classifier
    raise ValueError(f"Unknown model: {model_name}")

def calculate_class_weights(loader):
    """Computes inverse class frequencies to handle imbalanced datasets."""
    class_counts = [0] * Config.NUM_CLASSES
    for _, labels in loader:
        for label in labels:
            class_counts[label.item()] += 1
            
    total_samples = sum(class_counts)
    if total_samples == 0:
        return torch.ones(Config.NUM_CLASSES).to(Config.DEVICE)
        
    weights = [total_samples / (Config.NUM_CLASSES * count) if count > 0 else 1.0 for count in class_counts]
    weights[2] *= Config.POTHOLE_PRIORITY
    return torch.tensor(weights, dtype=torch.float).to(Config.DEVICE)

def mixup_data(images, labels, alpha=Config.MIXUP_ALPHA):
    """Applies Mixup augmentation to a batch."""
    if alpha > 0 and random.random() < Config.MIXUP_PROB:
        lam = np.random.beta(alpha, alpha)
        batch_size = images.size(0)
        index = torch.randperm(batch_size).to(images.device)
        mixed_images = lam * images + (1 - lam) * images[index]
        return mixed_images, labels, labels[index], lam
    return images, labels, labels, 1.0

def mixup_criterion(criterion, pred, y_a, y_b, lam):
    """Computes the Mixup loss as a weighted combination."""
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)

def train_epoch(model, loader, criterion, optimizer, epoch_desc=""):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    pbar = tqdm(loader, desc=epoch_desc, leave=False, file=sys.stdout)
    for images, labels in pbar:
        images, labels = images.to(Config.DEVICE), labels.to(Config.DEVICE)
        
        # Apply Mixup
        mixed_images, labels_a, labels_b, lam = mixup_data(images, labels)
        
        optimizer.zero_grad()
        outputs = model(mixed_images)
        loss = mixup_criterion(criterion, outputs, labels_a, labels_b, lam)
        loss.backward()
        optimizer.step()
        
        if torch.isnan(loss):
            print(f"\nNaN loss detected at batch {total // images.size(0) + 1} — skipping", flush=True)
            continue
        
        running_loss += loss.item() * images.size(0)
        _, preds = torch.max(outputs, 1)
        correct += torch.sum(preds == labels.data).item()
        total += labels.size(0)
        
        pbar.set_postfix(loss=f"{loss.item():.4f}")
        
    return running_loss / total, correct / total

def validate(model, loader, criterion):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(Config.DEVICE), labels.to(Config.DEVICE)
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            correct += torch.sum(preds == labels.data).item()
            total += labels.size(0)
            
    return running_loss / total, correct / total

def _find_checkpoint(model_name):
    """Find the best available checkpoint. Returns (path, source) or (None, None)."""
    local_path = Config.get_model_path(model_name)
    if os.path.exists(local_path):
        return local_path, "local"
    if Config.HF_AUTO_SYNC:
        try:
            from huggingface_hub import hf_hub_download
            hub_path = hf_hub_download(
                repo_id=Config.HF_MODEL_REPO,
                filename=f"{model_name}_best.pth",
                repo_type="model",
            )
            if hub_path:
                return hub_path, "hub"
        except Exception:
            pass
    return None, None


def run_training(model_name=None, fold=None):
    model_name = model_name or Config.MODEL_NAME
    train_loader, val_loader, test_loader = get_dataloaders(fold=fold)
    
    # Calculate weighted loss for class imbalance
    class_weights = calculate_class_weights(train_loader)
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=Config.LABEL_SMOOTHING)
    
    # Instantiate Model
    print(f"Initializing {model_name} Transfer Learning model...", flush=True)
    model = get_model(model_name=model_name, num_classes=Config.NUM_CLASSES, pretrained=True, freeze_backbone=True)
    model = model.to(Config.DEVICE)
    
    train_losses, val_losses = [], []
    train_accs, val_accs = [], []
    
    # Checkpoint resume detection
    resumed_from = None
    if Config.RESUME_ENABLED and fold is None:
        ckpt_path, ckpt_source = _find_checkpoint(model_name)
        if ckpt_path is not None:
            print(f"Found existing checkpoint at {ckpt_path} (source: {ckpt_source})", flush=True)
            resume = input(f"Resume training from checkpoint? (Y/n): ").strip().lower()
            if resume not in ("n", "no"):
                model.load_state_dict(torch.load(ckpt_path, map_location=Config.DEVICE))
                resumed_from = {"source": ckpt_source, "path": ckpt_path}
                print(f"Resumed from {ckpt_source} checkpoint. Skipping warmup phase.", flush=True)
    
    # wandb init
    if _WANDB_AVAILABLE and Config.WANDB_ENABLED:
        run_name = f"{model_name}-{time.strftime('%Y%m%d-%H%M%S')}"
        wandb.init(
            project=Config.WANDB_PROJECT,
            entity=Config.WANDB_ENTITY,
            name=run_name,
            config={
                "model": model_name,
                "resumed_from": resumed_from["source"] if resumed_from else None,
                "batch_size": Config.BATCH_SIZE,
                "lr_warmup": Config.LEARNING_RATE,
                "lr_finetune": Config.FINE_TUNE_LR,
                "epochs_warmup": Config.EPOCHS_WARMUP,
                "epochs_finetune": Config.EPOCHS_FINE_TUNE,
                "label_smoothing": Config.LABEL_SMOOTHING,
                "mixup_alpha": Config.MIXUP_ALPHA,
                "early_stop_patience": Config.EARLY_STOP_PATIENCE,
                "scheduler_patience": Config.SCHEDULER_PATIENCE,
                "pothole_priority": Config.POTHOLE_PRIORITY,
                "tta_enabled": Config.TTA_ENABLED,
            }
        )
        wandb.watch(model, log="gradients", log_freq=10)
    
    fold_tag = f" [Fold {fold}]" if fold is not None else ""
    best_val_loss = float("inf")
    early_stop_counter = 0

    # Phase 1: Warmup (skip if resumed from checkpoint)
    if resumed_from is not None:
        print(f"--- Skipping Warmup{fold_tag} (resumed from checkpoint) ---", flush=True)
        unfreeze_for_finetune(model, model_name)
        optimizer = optim.AdamW(model.parameters(), lr=Config.FINE_TUNE_LR)
    else:
        n_batches = len(train_loader)
        print(f"--- Phase 1: Warmup Training{fold_tag} ({n_batches} batches/epoch) ---", flush=True)
        optimizer = optim.AdamW(_get_classifier(model, model_name).parameters(), lr=Config.LEARNING_RATE)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=Config.SCHEDULER_FACTOR,
            patience=Config.SCHEDULER_PATIENCE, min_lr=Config.SCHEDULER_MIN_LR
        )

        for epoch in range(Config.EPOCHS_WARMUP):
            train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, f"Warmup {epoch+1}/{Config.EPOCHS_WARMUP}")
            val_loss, val_acc = validate(model, val_loader, criterion)
            train_losses.append(train_loss)
            val_losses.append(val_loss)
            train_accs.append(train_acc)
            val_accs.append(val_acc)
            current_lr = optimizer.param_groups[0]["lr"]
            print(f"Warmup Epoch {epoch+1}/{Config.EPOCHS_WARMUP} | Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f} | LR: {current_lr:.2e}", flush=True)
            scheduler.step(val_loss)
            if _WANDB_AVAILABLE and Config.WANDB_ENABLED:
                wandb.log({
                    "phase": "warmup",
                    "epoch": epoch + 1,
                    "train_loss": train_loss,
                    "val_loss": val_loss,
                    "train_acc": train_acc,
                    "val_acc": val_acc,
                    "learning_rate": current_lr,
                })
        
    # Phase 2: Fine-tuning
    print("--- Phase 2: Fine-Tuning Training ---", flush=True)
    unfreeze_for_finetune(model, model_name)
            
    optimizer = optim.AdamW(model.parameters(), lr=Config.FINE_TUNE_LR)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=Config.SCHEDULER_FACTOR,
        patience=Config.SCHEDULER_PATIENCE, min_lr=Config.SCHEDULER_MIN_LR
    )
    
    for epoch in range(Config.EPOCHS_FINE_TUNE):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, f"Fine-tune {epoch+1}/{Config.EPOCHS_FINE_TUNE}")
        val_loss, val_acc = validate(model, val_loader, criterion)
        train_losses.append(train_loss)
        val_losses.append(val_loss)
        train_accs.append(train_acc)
        val_accs.append(val_acc)
        current_lr = optimizer.param_groups[0]["lr"]
        print(f"Fine-Tune Epoch {epoch+1}/{Config.EPOCHS_FINE_TUNE} | Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f} | LR: {current_lr:.2e}", flush=True)
        
        scheduler.step(val_loss)
        
        # Save best model
        if fold is not None:
            model_path = os.path.join(Config.MODELS_DIR, f"fold_{fold}_best_model.pth")
        else:
            model_path = Config.get_model_path(model_name)
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            early_stop_counter = 0
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            torch.save(model.state_dict(), model_path)
            print(f"Saved new best model checkpoint to {model_path}", flush=True)
        else:
            early_stop_counter += 1
            if early_stop_counter >= Config.EARLY_STOP_PATIENCE:
                print(f"Early stopping triggered after {epoch+1} fine-tune epochs (no improvement for {Config.EARLY_STOP_PATIENCE} epochs).", flush=True)
                break
        
        if _WANDB_AVAILABLE and Config.WANDB_ENABLED:
            wandb.log({
                "phase": "finetune",
                "epoch": epoch + 1 + Config.EPOCHS_WARMUP,
                "train_loss": train_loss,
                "val_loss": val_loss,
                "train_acc": train_acc,
                "val_acc": val_acc,
                "learning_rate": current_lr,
                "best_val_loss": best_val_loss,
            })
    
    # Plot and save training curves
    curves_path = os.path.join(Config.REPORTS_DIR, f"training_curves_{model_name}.png")
    plot_training_curves(train_losses, val_losses, train_accs, val_accs, curves_path)
    
    if _WANDB_AVAILABLE and Config.WANDB_ENABLED:
        wandb.log({"training_curves": wandb.Image(curves_path)})
        wandb.finish()
    
    return {
        "best_val_loss": best_val_loss,
        "best_val_acc": max(val_accs) if val_accs else 0.0,
        "train_losses": train_losses,
        "val_losses": val_losses,
        "fold": fold,
        "resumed_from": resumed_from,
    }

def run_kfold(model_name=None):
    """Run K-fold cross-validation, aggregating metrics across all folds."""
    model_name = model_name or Config.MODEL_NAME
    print(f"\n{'='*60}", flush=True)
    print(f"Starting {Config.N_FOLDS}-Fold Cross-Validation ({model_name})", flush=True)
    print(f"{'='*60}", flush=True)

    fold_results = []
    for k in range(Config.N_FOLDS):
        print(f"\n{'='*60}", flush=True)
        print(f"Fold {k + 1}/{Config.N_FOLDS}", flush=True)
        print(f"{'='*60}", flush=True)
        result = run_training(model_name=model_name, fold=k)
        result["fold"] = k
        fold_results.append(result)

    # Aggregate metrics
    val_losses = [r["best_val_loss"] for r in fold_results]
    val_accs = [r["best_val_acc"] for r in fold_results]
    avg_val_loss = sum(val_losses) / len(val_losses)
    avg_val_acc = sum(val_accs) / len(val_accs)
    std_val_acc = (sum((a - avg_val_acc) ** 2 for a in val_accs) / len(val_accs)) ** 0.5

    print(f"\n{'='*60}", flush=True)
    print(f"K-Fold Cross-Validation Results ({Config.N_FOLDS} folds)", flush=True)
    print(f"{'='*60}", flush=True)
    for k, r in enumerate(fold_results):
        print(f"  Fold {k}: val_loss={r['best_val_loss']:.4f} val_acc={r['best_val_acc']:.4f}")
    print(f"  Average: val_loss={avg_val_loss:.4f} val_acc={avg_val_acc:.4f} ± {std_val_acc:.4f}")
    print(f"{'='*60}", flush=True)

    # Log to wandb
    if _WANDB_AVAILABLE and Config.WANDB_ENABLED:
        try:
            wandb.init(
                project=Config.WANDB_PROJECT_KFOLD,
                entity=Config.WANDB_ENTITY,
                name=f"kfold-{model_name}-{time.strftime('%Y%m%d-%H%M%S')}",
                config={"model": model_name, "n_folds": Config.N_FOLDS},
            )
            table = wandb.Table(columns=["fold", "val_loss", "val_acc"])
            for k, r in enumerate(fold_results):
                table.add_data(k, round(r["best_val_loss"], 4), round(r["best_val_acc"], 4))
            wandb.log({"per_fold_table": table})
            wandb.log({
                "avg_val_loss": avg_val_loss,
                "avg_val_acc": avg_val_acc,
                "std_val_acc": std_val_acc,
            })
            wandb.finish()
        except Exception:
            pass

    return {
        "fold_results": fold_results,
        "avg_val_loss": avg_val_loss,
        "avg_val_acc": avg_val_acc,
        "std_val_acc": std_val_acc,
        "n_folds": Config.N_FOLDS,
    }

if __name__ == "__main__":
    import sys
    if "--kfold" in sys.argv:
        run_kfold()
    else:
        run_training()
