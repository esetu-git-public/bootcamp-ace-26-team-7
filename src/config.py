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
    
    # Hyperparameters
    BATCH_SIZE = 16
    LEARNING_RATE = 1e-3
    FINE_TUNE_LR = 1e-5
    EPOCHS_WARMUP = 5
    EPOCHS_FINE_TUNE = 15
    IMAGE_SIZE = 224
    
    # Hardware device configuration
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Models folder
    MODEL_SAVE_PATH = "models/best_model.pth"
    REPORTS_DIR = "reports"
    
    # Pothole priority (class index 2) — extra weight multiplier
    POTHOLE_PRIORITY = 1.5
