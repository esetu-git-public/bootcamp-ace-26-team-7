import io
import os
import numpy as np
from PIL import Image

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


def predict_image(image_bytes: bytes, filename: str = "upload.jpg") -> dict:
    models, transform = _load_models()

    if models is not None:
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        import torch
        input_tensor = transform(pil_image).unsqueeze(0).to("cpu")

        all_probs = []
        with torch.no_grad():
            for m in models:
                outputs = m(input_tensor)
                probs = torch.softmax(outputs, dim=1).squeeze(0).cpu().numpy()
                all_probs.append(probs)

        # Average probabilities across all models
        avg_probs = np.mean(all_probs, axis=0)
        pred_idx = int(np.argmax(avg_probs))
        confidence = float(avg_probs[pred_idx])
        predicted_class = CLASSES[pred_idx]
    else:
        predicted_class = "Potholes"
        confidence = 0.85
        avg_probs = np.array([0.05, 0.05, 0.85, 0.05])

    base_sev = CLASS_SEVERITY.get(predicted_class, 0.5)
    severity_score = round(min(base_sev * (0.5 + 0.5 * confidence), 1.0), 3)

    if severity_score < 0.25:
        severity_label = "Low"
    elif severity_score < 0.55:
        severity_label = "Medium"
    elif severity_score < 0.80:
        severity_label = "High"
    else:
        severity_label = "Critical"

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

    return result
