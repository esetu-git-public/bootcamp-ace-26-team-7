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

def run_training(model_name=None):
    model_name = model_name or Config.MODEL_NAME
    train_loader, val_loader, test_loader = get_dataloaders()
    
    # Calculate weighted loss for class imbalance
    class_weights = calculate_class_weights(train_loader)
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=Config.LABEL_SMOOTHING)
    
    # Instantiate Model
    print(f"Initializing {model_name} Transfer Learning model...", flush=True)
    model = get_model(model_name=model_name, num_classes=Config.NUM_CLASSES, pretrained=True, freeze_backbone=True)
    model = model.to(Config.DEVICE)
    
    train_losses, val_losses = [], []
    train_accs, val_accs = [], []
    
    # wandb init
    if _WANDB_AVAILABLE and Config.WANDB_ENABLED:
        run_name = f"{model_name}-{time.strftime('%Y%m%d-%H%M%S')}"
        wandb.init(
            project=Config.WANDB_PROJECT,
            entity=Config.WANDB_ENTITY,
            name=run_name,
            config={
                "model": model_name,
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
    
    # Phase 1: Warmup
    n_batches = len(train_loader)
    print(f"--- Phase 1: Warmup Training ({n_batches} batches/epoch) ---", flush=True)
    optimizer = optim.AdamW(_get_classifier(model, model_name).parameters(), lr=Config.LEARNING_RATE)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=Config.SCHEDULER_FACTOR,
        patience=Config.SCHEDULER_PATIENCE, min_lr=Config.SCHEDULER_MIN_LR
    )
    best_val_loss = float("inf")
    early_stop_counter = 0

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
        "train_losses": train_losses,
        "val_losses": val_losses,
    }

if __name__ == "__main__":
    run_training()
