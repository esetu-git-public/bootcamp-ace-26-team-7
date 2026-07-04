import os
import torch
import torch.nn as nn
import torch.optim as optim
from src.config import Config
from src.dataset import get_dataloaders
from src.model import get_resnet50, SimpleCNN

def calculate_class_weights(loader):
    """Computes inverse class frequencies to handle imbalanced datasets."""
    # ponytail: default equal weights if empty, otherwise calculate class counts
    class_counts = [0] * Config.NUM_CLASSES
    for _, labels in loader:
        for label in labels:
            class_counts[label.item()] += 1
            
    total_samples = sum(class_counts)
    if total_samples == 0:
        return torch.ones(Config.NUM_CLASSES).to(Config.DEVICE)
        
    weights = [total_samples / (Config.NUM_CLASSES * count) if count > 0 else 1.0 for count in class_counts]
    return torch.tensor(weights, dtype=torch.float).to(Config.DEVICE)

def train_epoch(model, loader, criterion, optimizer):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for images, labels in loader:
        images, labels = images.to(Config.DEVICE), labels.to(Config.DEVICE)
        
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
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
    print("Initializing ResNet50 Transfer Learning model...")
    model = get_resnet50(num_classes=Config.NUM_CLASSES, pretrained=True, freeze_backbone=True)
    model = model.to(Config.DEVICE)
    
    # Phase 1: Warmup
    print("--- Phase 1: Warmup Training ---")
    optimizer = optim.AdamW(model.fc.parameters(), lr=Config.LEARNING_RATE)
    best_val_loss = float("inf")
    
    for epoch in range(Config.EPOCHS_WARMUP):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer)
        val_loss, val_acc = validate(model, val_loader, criterion)
        print(f"Warmup Epoch {epoch+1}/{Config.EPOCHS_WARMUP} | Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f}")
        
    # Phase 2: Fine-tuning
    print("--- Phase 2: Fine-Tuning Training ---")
    # Unfreeze the last layer blocks of ResNet backbone
    for name, param in model.named_parameters():
        if "layer4" in name or "fc" in name:
            param.requires_grad = True
            
    optimizer = optim.AdamW(model.parameters(), lr=Config.FINE_TUNE_LR)
    
    for epoch in range(Config.EPOCHS_FINE_TUNE):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer)
        val_loss, val_acc = validate(model, val_loader, criterion)
        print(f"Fine-Tune Epoch {epoch+1}/{Config.EPOCHS_FINE_TUNE} | Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f}")
        
        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            os.makedirs(os.path.dirname(Config.MODEL_SAVE_PATH), exist_ok=True)
            torch.save(model.state_dict(), Config.MODEL_SAVE_PATH)
            print(f"Saved new best model checkpoint to {Config.MODEL_SAVE_PATH}")

if __name__ == "__main__":
    run_training()
