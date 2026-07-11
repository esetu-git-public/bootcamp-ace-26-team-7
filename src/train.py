import os
import random
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from src.config import Config
from src.dataset import get_dataloaders
from src.model import get_model, unfreeze_for_finetune
from src.utils import plot_training_curves

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

def train_epoch(model, loader, criterion, optimizer):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for images, labels in loader:
        images, labels = images.to(Config.DEVICE), labels.to(Config.DEVICE)
        
        # Apply Mixup
        mixed_images, labels_a, labels_b, lam = mixup_data(images, labels)
        
        optimizer.zero_grad()
        outputs = model(mixed_images)
        loss = mixup_criterion(criterion, outputs, labels_a, labels_b, lam)
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item() * images.size(0)
        _, preds = torch.max(outputs, 1)
        correct += torch.sum(preds == labels.data).item()
        total += labels.size(0)
        
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

def run_training():
    train_loader, val_loader, test_loader = get_dataloaders()
    
    # Calculate weighted loss for class imbalance
    class_weights = calculate_class_weights(train_loader)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    
    # Instantiate Model
    print(f"Initializing {Config.MODEL_NAME} Transfer Learning model...")
    model = get_model(model_name=Config.MODEL_NAME, num_classes=Config.NUM_CLASSES, pretrained=True, freeze_backbone=True)
    model = model.to(Config.DEVICE)
    
    train_losses, val_losses = [], []
    train_accs, val_accs = [], []
    
    # Phase 1: Warmup
    print("--- Phase 1: Warmup Training ---")
    optimizer = optim.AdamW(model.fc.parameters(), lr=Config.LEARNING_RATE)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=Config.SCHEDULER_FACTOR,
        patience=Config.SCHEDULER_PATIENCE, min_lr=Config.SCHEDULER_MIN_LR
    )
    best_val_loss = float("inf")
    early_stop_counter = 0

    for epoch in range(Config.EPOCHS_WARMUP):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer)
        val_loss, val_acc = validate(model, val_loader, criterion)
        train_losses.append(train_loss)
        val_losses.append(val_loss)
        train_accs.append(train_acc)
        val_accs.append(val_acc)
        current_lr = optimizer.param_groups[0]["lr"]
        print(f"Warmup Epoch {epoch+1}/{Config.EPOCHS_WARMUP} | Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f} | LR: {current_lr:.2e}")
        scheduler.step(val_loss)
        
    # Phase 2: Fine-tuning
    print("--- Phase 2: Fine-Tuning Training ---")
    unfreeze_for_finetune(model, Config.MODEL_NAME)
            
    optimizer = optim.AdamW(model.parameters(), lr=Config.FINE_TUNE_LR)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=Config.SCHEDULER_FACTOR,
        patience=Config.SCHEDULER_PATIENCE, min_lr=Config.SCHEDULER_MIN_LR
    )
    
    for epoch in range(Config.EPOCHS_FINE_TUNE):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer)
        val_loss, val_acc = validate(model, val_loader, criterion)
        train_losses.append(train_loss)
        val_losses.append(val_loss)
        train_accs.append(train_acc)
        val_accs.append(val_acc)
        current_lr = optimizer.param_groups[0]["lr"]
        print(f"Fine-Tune Epoch {epoch+1}/{Config.EPOCHS_FINE_TUNE} | Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f} | LR: {current_lr:.2e}")
        
        scheduler.step(val_loss)
        
        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            early_stop_counter = 0
            os.makedirs(os.path.dirname(Config.get_model_path()), exist_ok=True)
            torch.save(model.state_dict(), Config.get_model_path())
            print(f"Saved new best model checkpoint to {Config.get_model_path()}")
        else:
            early_stop_counter += 1
            if early_stop_counter >= Config.EARLY_STOP_PATIENCE:
                print(f"Early stopping triggered after {epoch+1} fine-tune epochs (no improvement for {Config.EARLY_STOP_PATIENCE} epochs).")
                break
    
    # Plot and save training curves
    plot_training_curves(train_losses, val_losses, train_accs, val_accs,
                         os.path.join(Config.REPORTS_DIR, "training_curves.png"))

if __name__ == "__main__":
    run_training()
