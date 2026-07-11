import os
import torch

class Config:
    # Dataset configurations
    RAW_DATA_DIR = "data/raw"
    PROCESSED_DATA_DIR = "data/processed"
    TRAIN_DIR = os.path.join(PROCESSED_DATA_DIR, "train")
    VAL_DIR = os.path.join(PROCESSED_DATA_DIR, "val")
    TEST_DIR = os.path.join(PROCESSED_DATA_DIR, "test")
    
    # Class categories
    CLASSES = ["Cracks", "Patch", "Potholes", "Surface Defects"]
    NUM_CLASSES = len(CLASSES)
    
    # Stratified split ratios
    SPLIT_RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}
    
    # Model selection
    MODEL_NAME = "resnet50"  # Options: "resnet50", "efficientnet_b0", "vit_b_16"
    ENSEMBLE_MODELS = ["resnet50", "efficientnet_b0"]  # Used when ensemble=True
    
    # Hyperparameters
    BATCH_SIZE = 16
    LEARNING_RATE = 1e-3
    FINE_TUNE_LR = 1e-5
    EPOCHS_WARMUP = 5
    EPOCHS_FINE_TUNE = 15
    IMAGE_SIZE = 224
    
    # Learning rate scheduler
    SCHEDULER_PATIENCE = 3
    SCHEDULER_FACTOR = 0.5
    SCHEDULER_MIN_LR = 1e-7
    
    # Early stopping
    EARLY_STOP_PATIENCE = 7
    
    # Mixup / CutMix
    MIXUP_ALPHA = 0.2
    CUTMIX_ALPHA = 0.2
    MIXUP_PROB = 0.5
    
    # Hardware device configuration
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Models folder
    MODELS_DIR = "models"
    REPORTS_DIR = "reports"

    @staticmethod
    def get_model_path(model_name=None):
        name = model_name or Config.MODEL_NAME
        return os.path.join(Config.MODELS_DIR, f"{name}_best.pth")
    
    # Pothole priority (class index 2) — extra weight multiplier
    POTHOLE_PRIORITY = 1.5
