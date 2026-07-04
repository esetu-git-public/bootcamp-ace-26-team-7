import os
import shutil
import random
from src.config import Config

def prepare_data():
    """Splits raw dataset in data/raw into train/val/test directories."""
    # Ensure processed folders exist
    for split in ["train", "val", "test"]:
        for class_name in Config.CLASSES:
            os.makedirs(os.path.join(Config.PROCESSED_DATA_DIR, split, class_name), exist_ok=True)
            
    # ponytail: Keep file copier and split ratios simple and clean
    if not os.path.exists(Config.RAW_DATA_DIR):
        print(f"Warning: Raw data directory '{Config.RAW_DATA_DIR}' not found. Please place raw images there.")
        return

    random.seed(42)
    
    for class_name in Config.CLASSES:
        class_raw_dir = os.path.join(Config.RAW_DATA_DIR, class_name)
        if not os.path.exists(class_raw_dir):
            continue
            
        images = [f for f in os.listdir(class_raw_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        random.shuffle(images)
        
        n_total = len(images)
        n_train = int(n_total * Config.SPLIT_RATIOS["train"])
        n_val = int(n_total * Config.SPLIT_RATIOS["val"])
        
        train_imgs = images[:n_train]
        val_imgs = images[n_train:n_train + n_val]
        test_imgs = images[n_train + n_val:]
        
        splits = {
            "train": train_imgs,
            "val": val_imgs,
            "test": test_imgs
        }
        
        for split_name, split_imgs in splits.items():
            dest_dir = os.path.join(Config.PROCESSED_DATA_DIR, split_name, class_name)
            for img_name in split_imgs:
                shutil.copy(
                    os.path.join(class_raw_dir, img_name),
                    os.path.join(dest_dir, img_name)
                )
                
    print("Data preparation and stratified split completed successfully!")

if __name__ == "__main__":
    prepare_data()
