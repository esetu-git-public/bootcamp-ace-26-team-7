import matplotlib.pyplot as plt
from PIL import Image
import torch
import os

def plot_training_curves(train_losses, val_losses, train_accs, val_accs, save_path):
    """Generates training history curves for losses and accuracies."""
    epochs = range(1, len(train_losses) + 1)
    
    plt.figure(figsize=(12, 5))
    
    # Loss curves
    plt.subplot(1, 2, 1)
    plt.plot(epochs, train_losses, label="Train Loss")
    plt.plot(epochs, val_losses, label="Val Loss")
    plt.title("Loss Curves")
    plt.xlabel("Epochs")
    plt.ylabel("Loss")
    plt.legend()
    
    # Accuracy curves
    plt.subplot(1, 2, 2)
    plt.plot(epochs, train_accs, label="Train Accuracy")
    plt.plot(epochs, val_accs, label="Val Accuracy")
    plt.title("Accuracy Curves")
    plt.xlabel("Epochs")
    plt.ylabel("Accuracy")
    plt.legend()
    
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path)
    plt.close()
    print(f"Saved training curves plot to {save_path}")

def load_and_preprocess_image(img_path, transform, device):
    """Helper to load a single PIL image and convert it for PyTorch inference."""
    image = Image.open(img_path).convert("RGB")
    if transform:
        image = transform(image)
    # Add batch dimension and transfer to device
    return image.unsqueeze(0).to(device)
