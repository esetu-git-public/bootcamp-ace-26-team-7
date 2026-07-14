import os
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from src.config import Config

try:
    import wandb
    _WANDB_AVAILABLE = True
except ModuleNotFoundError:
    wandb = None
    _WANDB_AVAILABLE = False

class SurfaceCrackDataset(Dataset):
    """Custom PyTorch dataset for road surface crack/defect classification."""
    def __init__(self, data_dir, transform=None, include_synthetic=False):
        self.data_dir = data_dir
        self.transform = transform
        self.images = []
        self.labels = []
        
        def _load_from_dir(directory, multiplier=1.0):
            if not os.path.exists(directory):
                return
            for class_idx, class_name in enumerate(Config.CLASSES):
                class_path = os.path.join(directory, class_name)
                if os.path.isdir(class_path):
                    imgs = [f for f in os.listdir(class_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                    count = max(1, int(len(imgs) * multiplier)) if multiplier < 1.0 else len(imgs)
                    for img_name in imgs[:count]:
                        self.images.append(os.path.join(class_path, img_name))
                        self.labels.append(class_idx)

        _load_from_dir(data_dir)

        if include_synthetic and os.path.isdir(Config.SYNTHETIC_DIR):
            _load_from_dir(Config.SYNTHETIC_DIR, multiplier=Config.SYNTHETIC_FACTOR)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_path = self.images[idx]
        label = self.labels[idx]
        
        # Load image in RGB
        image = Image.open(img_path).convert("RGB")
        
        if self.transform:
            image = self.transform(image)
            
        return image, torch.tensor(label, dtype=torch.long)

def get_transforms():
    """Returns training, validation and test dataset transforms."""
    # Data augmentation for training (stronger for small dataset)
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(Config.IMAGE_SIZE, scale=(0.75, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.15, hue=0.1),
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
        transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.0)),
        transforms.ToTensor(),
        transforms.RandomErasing(p=0.2, scale=(0.02, 0.15)),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # Simple resize and normalize for validation / test
    val_test_transform = transforms.Compose([
        transforms.Resize((Config.IMAGE_SIZE, Config.IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    return train_transform, val_test_transform

_logged_dataset_stats = False


def get_dataloaders(fold=None):
    """Helper to return train, val, and test DataLoader instances.
    
    Args:
        fold: If provided, loads from k-fold split directories.
    """
    global _logged_dataset_stats
    train_transform, val_test_transform = get_transforms()
    
    if fold is not None:
        train_dir = os.path.join(Config.KFOLD_DIR, f"fold_{fold}", "train")
        val_dir = os.path.join(Config.KFOLD_DIR, f"fold_{fold}", "val")
    else:
        train_dir = Config.TRAIN_DIR
        val_dir = Config.VAL_DIR
    
    train_dataset = SurfaceCrackDataset(train_dir, transform=train_transform, include_synthetic=Config.SYNTHETIC_ENABLED)
    val_dataset = SurfaceCrackDataset(val_dir, transform=val_test_transform)
    test_dataset = SurfaceCrackDataset(Config.TEST_DIR, transform=val_test_transform)
    
    # Log class distribution to wandb once
    if _WANDB_AVAILABLE and Config.WANDB_ENABLED and not _logged_dataset_stats:
        _logged_dataset_stats = True
        try:
            train_counts = {cls: 0 for cls in Config.CLASSES}
            for _, label in train_dataset:
                train_counts[Config.CLASSES[label.item()]] += 1
            wandb.log({"dataset/train_class_distribution": wandb.Table(
                columns=["class", "count"],
                data=[[c, train_counts[c]] for c in Config.CLASSES],
            )})
        except Exception:
            pass
    
    train_loader = DataLoader(train_dataset, batch_size=Config.BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=Config.BATCH_SIZE, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=Config.BATCH_SIZE, shuffle=False, num_workers=0)
    
    return train_loader, val_loader, test_loader
