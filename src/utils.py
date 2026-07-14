import matplotlib.pyplot as plt
from PIL import Image
import torch
import os

def sync_models_from_hub(repo_id=None, token=None, models_dir=None):
    """Download latest model checkpoints from HF Hub to local models/ dir."""
    from src.config import Config
    from huggingface_hub import hf_hub_download, HfApi
    from huggingface_hub.utils import RepositoryNotFoundError

    repo_id = repo_id or Config.HF_MODEL_REPO
    models_dir = models_dir or Config.MODELS_DIR
    os.makedirs(models_dir, exist_ok=True)

    candidates = Config.DISTILL_TEACHERS + [Config.DISTILL_STUDENT]
    downloaded = 0
    for model_name in candidates:
        remote_name = f"{model_name}_best.pth"
        local_path = os.path.join(models_dir, remote_name)
        if os.path.exists(local_path):
            continue
        try:
            hf_hub_download(
                repo_id=repo_id, filename=remote_name,
                local_dir=models_dir, repo_type="model",
                token=token,
            )
            print(f"  Downloaded {remote_name} from HF Hub")
            downloaded += 1
        except Exception:
            pass
    if downloaded == 0:
        print("  No new models to sync from HF Hub")
    return downloaded


def sync_models_to_hub(repo_id=None, token=None, models_dir=None, reports_dir=None):
    """Push all model checkpoints + reports to HF Hub."""
    from src.config import Config
    from huggingface_hub import HfApi, login

    repo_id = repo_id or Config.HF_MODEL_REPO
    models_dir = models_dir or Config.MODELS_DIR
    reports_dir = reports_dir or Config.REPORTS_DIR

    login(token=token)
    api = HfApi()
    pushed = 0

    candidates = Config.DISTILL_TEACHERS + [Config.DISTILL_STUDENT]
    for model_name in candidates:
        local_path = os.path.join(models_dir, f"{model_name}_best.pth")
        if not os.path.exists(local_path):
            continue
        remote_name = f"{model_name}_best.pth"
        try:
            api.upload_file(
                path_or_fileobj=local_path,
                path_in_repo=remote_name,
                repo_id=repo_id, repo_type="model",
            )
            print(f"  Pushed {remote_name}")
            pushed += 1
        except Exception as e:
            print(f"  Failed to push {remote_name}: {e}")

    student_path = os.path.join(models_dir, f"student_{Config.DISTILL_STUDENT}.pth")
    if os.path.exists(student_path):
        try:
            api.upload_file(
                path_or_fileobj=student_path,
                path_in_repo=f"student_{Config.DISTILL_STUDENT}.pth",
                repo_id=repo_id, repo_type="model",
            )
            print(f"  Pushed student_{Config.DISTILL_STUDENT}.pth")
            pushed += 1
        except Exception as e:
            print(f"  Failed to push student model: {e}")

    if os.path.isdir(reports_dir):
        for fname in os.listdir(reports_dir):
            fpath = os.path.join(reports_dir, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                api.upload_file(
                    path_or_fileobj=fpath,
                    path_in_repo=f"reports/{fname}",
                    repo_id=repo_id, repo_type="model",
                )
                print(f"  Pushed reports/{fname}")
            except Exception:
                pass

    print(f"Pushed {pushed} file(s) to {repo_id}")
    return pushed


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
