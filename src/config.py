import os

try:
    import torch
    _TORCH_AVAILABLE = True
except ModuleNotFoundError:
    _TORCH_AVAILABLE = False
    torch = None

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
    ENSEMBLE_MODELS = []  # empty = single-model mode; only one weights file (best_model.pth) exists on HF
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
    
    # Label smoothing
    LABEL_SMOOTHING = 0.1
    
    # Mixup / CutMix
    MIXUP_ALPHA = 0.2
    CUTMIX_ALPHA = 0.2
    MIXUP_PROB = 0.5
    
    # Test-Time Augmentation
    TTA_ENABLED = True
    
    # Hardware device configuration
    if _TORCH_AVAILABLE:
        DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        DEVICE = None
    
    # Models folder
    MODELS_DIR = "models"
    REPORTS_DIR = "reports"

    @staticmethod
    def get_model_path(model_name=None):
        return os.path.join(Config.MODELS_DIR, "best_model.pth")
    
    # Pothole priority (class index 2) — extra weight multiplier
    POTHOLE_PRIORITY = 1.5
    
    # Weights & Biases
    WANDB_ENABLED = False
    WANDB_PROJECT = "surface-crack-detection"
    WANDB_ENTITY = None

    # HuggingFace Hub
    HF_MODEL_REPO = "amruthjakku/surface-crack-detection-model"
