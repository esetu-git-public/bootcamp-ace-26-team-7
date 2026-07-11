import torch
import torch.nn as nn
import torchvision.models as models

class SimpleCNN(nn.Module):
    """Baseline 3-layer CNN architecture for defect classification."""
    def __init__(self, num_classes=4):
        super(SimpleCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)
        )
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d((7, 7)),
            nn.Flatten(),
            nn.Linear(128 * 7 * 7, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x


def get_resnet50(num_classes=4, pretrained=True, freeze_backbone=True):
    """Loads ResNet50 with custom fully connected layers."""
    weights = models.ResNet50_Weights.DEFAULT if pretrained else None
    model = models.resnet50(weights=weights)
    
    if freeze_backbone:
        for param in model.parameters():
            param.requires_grad = False
            
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Linear(in_features, 256),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(256, num_classes)
    )
    
    return model


def get_efficientnet_b0(num_classes=4, pretrained=True, freeze_backbone=True):
    """Loads EfficientNet-B0 with custom classifier head."""
    weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
    model = models.efficientnet_b0(weights=weights)
    
    if freeze_backbone:
        for param in model.parameters():
            param.requires_grad = False

    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 256),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(256, num_classes)
    )
    
    return model


def get_vit_b_16(num_classes=4, pretrained=True, freeze_backbone=True):
    """Loads ViT-B/16 with custom classification head."""
    weights = models.ViT_B_16_Weights.DEFAULT if pretrained else None
    model = models.vit_b_16(weights=weights, image_size=224)
    
    if freeze_backbone:
        for param in model.parameters():
            param.requires_grad = False

    in_features = model.heads.head.in_features
    model.heads.head = nn.Sequential(
        nn.Linear(in_features, 256),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(256, num_classes)
    )
    
    return model


def unfreeze_for_finetune(model, model_name):
    """Unfreeze the last stage + head for fine-tuning based on model type."""
    if model_name in ("resnet50",):
        for name, param in model.named_parameters():
            if "layer4" in name or "fc" in name:
                param.requires_grad = True
    elif model_name in ("efficientnet_b0",):
        for name, param in model.named_parameters():
            if "features.8" in name or "classifier" in name:
                param.requires_grad = True
    elif model_name in ("vit_b_16",):
        for name, param in model.named_parameters():
            if "encoder.ln" in name or "heads" in name:
                param.requires_grad = True


def get_model(model_name="resnet50", num_classes=4, pretrained=True, freeze_backbone=True):
    """Factory function — returns model by name."""
    builders = {
        "resnet50": get_resnet50,
        "efficientnet_b0": get_efficientnet_b0,
        "vit_b_16": get_vit_b_16,
    }
    builder = builders.get(model_name)
    if builder is None:
        raise ValueError(f"Unknown model: {model_name}. Choose from {list(builders.keys())}")
    return builder(num_classes=num_classes, pretrained=pretrained, freeze_backbone=freeze_backbone)
