import os
import sys
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
from tqdm.auto import tqdm
from src.config import Config
from src.dataset import get_dataloaders
from src.model import get_model
from src.train import validate, calculate_class_weights, mixup_data
from src.utils import plot_training_curves

try:
    import wandb
    _WANDB_AVAILABLE = True
except ModuleNotFoundError:
    wandb = None
    _WANDB_AVAILABLE = False


def load_teacher(model_name, device):
    path = Config.get_model_path(model_name)
    if not os.path.exists(path):
        print(f"Teacher {model_name} checkpoint not found at {path}")
        return None
    model = get_model(model_name=model_name, num_classes=Config.NUM_CLASSES, pretrained=False)
    model.load_state_dict(torch.load(path, map_location=device))
    model = model.to(device)
    model.eval()
    for p in model.parameters():
        p.requires_grad = False
    return model


@torch.no_grad()
def teacher_logits(teachers, images, temperature=Config.DISTILL_TEMPERATURE):
    logits_list = []
    for teacher in teachers:
        if teacher is None:
            continue
        logits = teacher(images)
        logits_list.append(logits)
    if not logits_list:
        return None
    avg_logits = torch.stack(logits_list).mean(dim=0)
    return avg_logits / temperature


def distillation_loss(student_logits, teacher_soft, hard_labels, temperature, alpha):
    soft_loss = F.kl_div(
        F.log_softmax(student_logits / temperature, dim=1),
        teacher_soft,
        reduction="batchmean",
    ) * (temperature ** 2)
    hard_loss = F.cross_entropy(student_logits, hard_labels)
    return alpha * soft_loss + (1 - alpha) * hard_loss


def run_distillation(model_name=None):
    model_name = model_name or Config.DISTILL_STUDENT
    device = Config.DEVICE

    print("Loading teacher ensemble...", flush=True)
    teachers = []
    for t_name in Config.DISTILL_TEACHERS:
        t = load_teacher(t_name, device)
        if t is not None:
            teachers.append(t)
            print(f"  Loaded teacher: {t_name} ({sum(p.numel() for p in t.parameters()):,} params)", flush=True)

    if len(teachers) == 0:
        print("No teachers available. Train models first.")
        return

    train_loader, val_loader, test_loader = get_dataloaders()

    class_weights = calculate_class_weights(train_loader)

    print(f"Initializing student model: {model_name}", flush=True)
    student = get_model(model_name=model_name, num_classes=Config.NUM_CLASSES, pretrained=True, freeze_backbone=True)
    student = student.to(device)

    optimizer = optim.AdamW(_get_classifier(student, model_name).parameters(), lr=Config.LEARNING_RATE)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=Config.SCHEDULER_FACTOR,
        patience=Config.SCHEDULER_PATIENCE, min_lr=Config.SCHEDULER_MIN_LR
    )

    temperature = Config.DISTILL_TEMPERATURE
    alpha = Config.DISTILL_ALPHA

    train_losses, val_losses = [], []
    train_accs, val_accs = [], []
    best_val_loss = float("inf")
    early_stop_counter = 0

    total_epochs = Config.DISTILL_EPOCHS
    print(f"--- Distillation Training ({total_epochs} epochs, T={temperature}, alpha={alpha}) ---", flush=True)

    # wandb init
    if _WANDB_AVAILABLE and Config.WANDB_ENABLED:
        wandb.init(
            project=Config.WANDB_PROJECT_DISTILL,
            entity=Config.WANDB_ENTITY,
            name=f"distill-{model_name}-{time.strftime('%Y%m%d-%H%M%S')}",
            config={
                "student": model_name,
                "teachers": Config.DISTILL_TEACHERS,
                "temperature": temperature,
                "alpha": alpha,
                "epochs": total_epochs,
            },
        )

    for epoch in range(total_epochs):
        student.train()
        running_loss = 0.0
        correct = 0
        total = 0

        pbar = tqdm(train_loader, desc=f"Distill {epoch+1}/{total_epochs}", leave=False, file=sys.stdout)
        for images, labels in pbar:
            images, labels = images.to(device), labels.to(device)

            mixed_images, labels_a, labels_b, lam = mixup_data(images, labels)

            optimizer.zero_grad()
            student_logits = student(mixed_images)

            with torch.no_grad():
                soft_targets = teacher_logits(teachers, mixed_images, temperature)
                if soft_targets is None:
                    loss = F.cross_entropy(student_logits, labels)
                else:
                    soft_probs = F.softmax(soft_targets, dim=1)
                    loss = distillation_loss(student_logits, soft_probs, labels, temperature, alpha)

            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(student_logits, 1)
            correct += torch.sum(preds == labels.data).item()
            total += labels.size(0)

            pbar.set_postfix(loss=f"{loss.item():.4f}")

        train_loss = running_loss / total
        train_acc = correct / total
        val_loss, val_acc = validate(student, val_loader, nn.CrossEntropyLoss(weight=class_weights))

        train_losses.append(train_loss)
        val_losses.append(val_loss)
        train_accs.append(train_acc)
        val_accs.append(val_acc)

        current_lr = optimizer.param_groups[0]["lr"]
        print(f"Epoch {epoch+1}/{total_epochs} | Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f} | LR: {current_lr:.2e}", flush=True)

        if _WANDB_AVAILABLE and Config.WANDB_ENABLED:
            wandb.log({
                "epoch": epoch + 1,
                "train_loss": train_loss,
                "val_loss": val_loss,
                "train_acc": train_acc,
                "val_acc": val_acc,
                "learning_rate": current_lr,
            })

        scheduler.step(val_loss)

        student_path = os.path.join(Config.MODELS_DIR, f"student_{model_name}.pth")
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            early_stop_counter = 0
            os.makedirs(os.path.dirname(student_path), exist_ok=True)
            torch.save(student.state_dict(), student_path)
            print(f"Saved best student checkpoint to {student_path}", flush=True)
        else:
            early_stop_counter += 1
            if early_stop_counter >= Config.EARLY_STOP_PATIENCE:
                print(f"Early stopping triggered after {epoch+1} epochs.", flush=True)
                break

    curves_path = os.path.join(Config.REPORTS_DIR, f"distillation_curves_{model_name}.png")
    plot_training_curves(train_losses, val_losses, train_accs, val_accs, curves_path)
    print(f"Saved training curves to {curves_path}", flush=True)

    if _WANDB_AVAILABLE and Config.WANDB_ENABLED:
        wandb.log({"distillation_curves": wandb.Image(curves_path)})
        wandb.finish()

    return {
        "best_val_loss": best_val_loss,
        "best_val_acc": max(val_accs) if val_accs else 0.0,
    }


def _get_classifier(model, model_name):
    if model_name == "resnet50":
        return model.fc
    elif model_name == "efficientnet_b0":
        return model.classifier
    elif model_name == "vit_b_16":
        return model.heads.head
    elif model_name == "mobilenet_v3_small":
        return model.classifier
    raise ValueError(f"Unknown model: {model_name}")


if __name__ == "__main__":
    run_distillation()
