import io
import os
import numpy as np
from PIL import Image
from backend.cost import estimate_repair_cost, estimate_repair_time

CLASSES = ["Cracks", "Patch", "Potholes", "Surface Defects"]

CLASS_SEVERITY = {
    "Cracks": 0.50,
    "Patch": 0.25,
    "Potholes": 0.75,
    "Surface Defects": 0.60,
}

_models = None
_transform = None


def _load_models():
    global _models, _transform
    if _models is not None:
        return _models, _transform

    try:
        from torchvision import transforms
        from src.model import get_model
        from src.config import Config
        import torch
    except ImportError:
        return None, None

    _transform = transforms.Compose([
        transforms.Resize((Config.IMAGE_SIZE, Config.IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    _models = []
    model_names = Config.ENSEMBLE_MODELS if len(Config.ENSEMBLE_MODELS) > 0 else [Config.MODEL_NAME]

    for name in model_names:
        model_path = Config.get_model_path(model_name=name)
        if not os.path.exists(model_path):
            try:
                from huggingface_hub import hf_hub_download
                hf_hub_download(
                    repo_id="amruthjakku/surface-crack-detection-model",
                    filename=f"{name}_best.pth",
                    local_dir="models"
                )
            except Exception:
                pass

        if os.path.exists(model_path):
            m = get_model(model_name=name, num_classes=Config.NUM_CLASSES, pretrained=False)
            m.load_state_dict(torch.load(model_path, map_location=Config.DEVICE))
            m.to(Config.DEVICE)
            m.eval()
            _models.append(m)

    if len(_models) == 0:
        _models = None
    return _models, _transform


def _tta_predict(models, input_tensor):
    """Run inference with Test-Time Augmentation and return averaged probabilities."""
    from src.config import Config
    import torch
    from torchvision import transforms as T

    all_probs = []
    # Base prediction
    with torch.no_grad():
        for m in models:
            outputs = m(input_tensor)
            probs = torch.softmax(outputs, dim=1).squeeze(0).cpu().numpy()
            all_probs.append(probs)

    if not Config.TTA_ENABLED:
        return np.mean(all_probs, axis=0)

    # Test-time augmentations
    tta_transforms = [
        lambda x: x,
        lambda x: T.functional.hflip(x),
        lambda x: T.functional.vflip(x),
        lambda x: T.functional.rotate(x, 90),
        lambda x: T.functional.rotate(x, 180),
        lambda x: T.functional.rotate(x, 270),
    ]
    for aug in tta_transforms[1:]:
        aug_tensor = aug(input_tensor)
        with torch.no_grad():
            for m in models:
                outputs = m(aug_tensor)
                probs = torch.softmax(outputs, dim=1).squeeze(0).cpu().numpy()
                all_probs.append(probs)

    return np.mean(all_probs, axis=0)


def predict_image(image_bytes: bytes, filename: str = "upload.jpg") -> dict:
    models, transform = _load_models()

    if models is not None:
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        import torch
        input_tensor = transform(pil_image).unsqueeze(0).to("cpu")

        avg_probs = _tta_predict(models, input_tensor)
        pred_idx = int(np.argmax(avg_probs))
        confidence = float(avg_probs[pred_idx])
        predicted_class = CLASSES[pred_idx]
    else:
        predicted_class = "N/A"
        confidence = 0.0
        avg_probs = np.array([0.25, 0.25, 0.25, 0.25])

    base_sev = CLASS_SEVERITY.get(predicted_class, 0.5)
    severity_score = round(min(base_sev * (0.5 + 0.5 * confidence), 1.0), 3)

    # 3-tier severity: Low / Medium / High
    if severity_score < 0.35:
        severity_label = "Low"
    elif severity_score < 0.65:
        severity_label = "Medium"
    else:
        severity_label = "High"

    result = {
        "success": True,
        "predicted_class": predicted_class,
        "confidence": round(confidence, 4),
        "class_probabilities": {
            cls: round(float(p), 4) for cls, p in zip(CLASSES, avg_probs)
        },
        "severity_score": severity_score,
        "severity_label": severity_label,
    }

    # Only estimate cost/time if we have a real prediction
    if predicted_class in CLASS_SEVERITY:
        cost_estimate = estimate_repair_cost(predicted_class, severity_label, confidence)
        time_estimate = estimate_repair_time(predicted_class, severity_label, confidence)
        result["repair_cost"] = cost_estimate
        result["repair_time"] = time_estimate
    else:
        result["repair_cost"] = None
        result["repair_time"] = None

    return result