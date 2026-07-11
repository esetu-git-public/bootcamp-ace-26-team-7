import os
import shutil
from src.config import Config
from sklearn.model_selection import StratifiedShuffleSplit

def _collect_images(raw_dir):
    """Collect all image paths and class labels from data/raw/."""
    all_images, all_labels, label_names = [], [], []
    for class_idx, class_name in enumerate(Config.CLASSES):
        class_path = os.path.join(raw_dir, class_name)
        if not os.path.isdir(class_path):
            continue
        images = [
            os.path.join(class_path, f)
            for f in os.listdir(class_path)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        all_images.extend(images)
        all_labels.extend([class_idx] * len(images))
        label_names.extend([class_name] * len(images))
    return all_images, all_labels, label_names

def prepare_data():
    """Splits raw dataset in data/raw into train/val/test directories (stratified)."""
    for split in ["train", "val", "test"]:
        for class_name in Config.CLASSES:
            os.makedirs(os.path.join(Config.PROCESSED_DATA_DIR, split, class_name), exist_ok=True)

    if not os.path.exists(Config.RAW_DATA_DIR):
        print(f"Warning: Raw data directory '{Config.RAW_DATA_DIR}' not found. Please place raw images there.")
        return

    images, labels, _ = _collect_images(Config.RAW_DATA_DIR)
    if len(images) == 0:
        print("No images found in raw data directory.")
        return

    # Two-stage stratified split: train 70%, then val/test from remaining 30%
    sss1 = StratifiedShuffleSplit(n_splits=1, test_size=1.0 - Config.SPLIT_RATIOS["train"], random_state=42)
    train_idx, temp_idx = next(sss1.split(images, labels))

    # Val/test split of the temp set (50/50 → 15%/15% of total)
    temp_labels = [labels[i] for i in temp_idx]
    sss2 = StratifiedShuffleSplit(n_splits=1, test_size=0.5, random_state=42)
    val_idx_rel, test_idx_rel = next(sss2.split(temp_idx, temp_labels))
    val_idx = [temp_idx[i] for i in val_idx_rel]
    test_idx = [temp_idx[i] for i in test_idx_rel]

    splits = {
        "train": train_idx,
        "val": val_idx,
        "test": test_idx,
    }

    for split_name, indices in splits.items():
        for idx in indices:
            img_path = images[idx]
            class_name = Config.CLASSES[labels[idx]]
            dest = os.path.join(Config.PROCESSED_DATA_DIR, split_name, class_name, os.path.basename(img_path))
            shutil.copy(img_path, dest)

    print("Data preparation and stratified split completed successfully!")
    for split_name, indices in splits.items():
        counts = {}
        for idx in indices:
            cls = Config.CLASSES[labels[idx]]
            counts[cls] = counts.get(cls, 0) + 1
        print(f"  {split_name}: {counts}")

if __name__ == "__main__":
    prepare_data()
