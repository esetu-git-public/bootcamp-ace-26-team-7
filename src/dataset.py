import os
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from src.config import Config

class SurfaceCrackDataset(Dataset):
    """Custom PyTorch dataset for road surface crack/defect classification."""
    def __init__(self, data_dir, transform=None):
        self.data_dir = data_dir
        self.transform = transform
        self.images = []
        self.labels = []
        
        # ponytail: simple loop to scan folders, keeping code minimal
        if os.path.exists(data_dir):
            for class_idx, class_name in enumerate(Config.CLASSES):
                class_path = os.path.join(data_dir, class_name)
                if os.path.isdir(class_path):
                    for img_name in os.listdir(class_path):
                        if img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                            self.images.append(os.path.join(class_path, img_name))
                            self.labels.append(class_idx)

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
    # Data augmentation for training
    train_transform = transforms.Compose([
        transforms.Resize((Config.IMAGE_SIZE, Config.IMAGE_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # Simple resize and normalize for validation / test
    val_test_transform = transforms.Compose([
        transforms.Resize((Config.IMAGE_SIZE, Config.IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    return train_transform, val_test_transform

def get_dataloaders():
    """Helper to return train, val, and test DataLoader instances."""
    train_transform, val_test_transform = get_transforms()
    
    train_dataset = SurfaceCrackDataset(Config.TRAIN_DIR, transform=train_transform)
    val_dataset = SurfaceCrackDataset(Config.VAL_DIR, transform=val_test_transform)
    test_dataset = SurfaceCrackDataset(Config.TEST_DIR, transform=val_test_transform)
    
    train_loader = DataLoader(train_dataset, batch_size=Config.BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=Config.BATCH_SIZE, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=Config.BATCH_SIZE, shuffle=False, num_workers=0)
    
    return train_loader, val_loader, test_loader
