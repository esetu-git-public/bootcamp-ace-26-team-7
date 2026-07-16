import io
import os
import logging
import numpy as np
from PIL import Image
from backend.pdf_generator import generate_pdf
from backend.cost import estimate_repair_cost, estimate_repair_time
from backend.actions import get_action_plan

logger = logging.getLogger(__name__)

CLASSES = ["Cracks", "Patch", "Potholes", "Surface Defects"]

CLASS_SEVERITY = {
    "Cracks": 0.50,
    "Patch": 0.25,
    "Potholes": 0.75,
    "Surface Defects": 0.60,
}


def get_active_model_name():
    return _active_model


def get_active_model_status():
    return ACTIVE_MODEL_STATUS


MODEL_REGISTRY = {
    "resnet50": {
        "display_name": "ResNet50",
        "hf_file": "best_model.pth",
        "hf_repo": "amruthjakku/surface-crack-detection-model",
        "size_mb": 96,
    },
    "efficientnet_b0": {
        "display_name": "EfficientNet-B0",
        "hf_file": "efficientnet_b0_best.pth",
        "hf_repo": "amruthjakku/surface-crack-detection-model",
        "size_mb": 18,
    },
    "vit_b_16": {
        "display_name": "ViT-B/16",
        "hf_file": "vit_b_16_best.pth",
        "hf_repo": "amruthjakku/surface-crack-detection-model",
        "size_mb": 344,
    },
}

_loaded = {}
_model_transforms = {}
_active_model = "resnet50"
ACTIVE_MODEL_STATUS = "unavailable"
_model_statuses = {}


def get_available_models():
    result = []
    for key, info in MODEL_REGISTRY.items():
        result.append({
            "name": key,
            "display_name": info["display_name"],
            "size_mb": info["size_mb"],
            "is_loaded": key in _loaded,
            "is_active": key == _active_model,
            "status": _model_statuses.get(key, "unavailable"),
        })
    return result


def select_model(model_name):
    global _active_model, ACTIVE_MODEL_STATUS
    if model_name not in MODEL_REGISTRY:
        return {"success": False, "message": f"Unknown model: {model_name}"}
    _active_model = model_name
    if model_name in _loaded:
        ACTIVE_MODEL_STATUS = "loaded"
        return {"success": True, "active_model": model_name, "status": "loaded"}
    ACTIVE_MODEL_STATUS = "loading"
    _model_statuses[model_name] = "loading"
    try:
        load_model(model_name)
        ACTIVE_MODEL_STATUS = "loaded"
    except Exception as e:
        logger.warning("select_model: load FAILED for '%s': %s", model_name, e, exc_info=True)
        ACTIVE_MODEL_STATUS = "unavailable"
        _model_statuses[model_name] = "unavailable"
        return {"success": False, "active_model": model_name, "status": "unavailable", "message": str(e)}
    return {"success": True, "active_model": model_name, "status": "loaded"}


def load_model(model_name):
    global _model_statuses
    if model_name in _loaded:
        return _loaded[model_name], _model_transforms[model_name]

    _model_statuses[model_name] = "loading"
    info = MODEL_REGISTRY.get(model_name)
    if info is None:
        _model_statuses[model_name] = "unavailable"
        raise ValueError(f"Unknown model: {model_name}")

    logger.info("load_model: starting '%s' (display=%s, size=%dMB)", model_name, info["display_name"], info["size_mb"])

    try:
        from torchvision import transforms
        from src.model import get_model
        from src.config import Config
        import torch
        logger.info("Imports OK: torch=%s, device=%s", torch.__version__, Config.DEVICE)
    except ImportError as e:
        logger.warning("Import FAILED: %s", e, exc_info=True)
        _model_statuses[model_name] = "unavailable"
        raise

    transform = transforms.Compose([
        transforms.Resize((Config.IMAGE_SIZE, Config.IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    model_path = Config.get_model_path(model_name=model_name)
    logger.info("Model path: '%s', exists=%s", model_path, os.path.exists(model_path))

    if not os.path.exists(model_path):
        logger.info("Path not found. models/ dir: %s", os.listdir("models") if os.path.isdir("models") else "DIR NOT FOUND")
        try:
            from huggingface_hub import hf_hub_download
            os.makedirs("models", exist_ok=True)
            logger.info("Downloading '%s' from HF Hub (file=%s)", model_name, info["hf_file"])
            downloaded = hf_hub_download(
                repo_id=info["hf_repo"],
                filename=info["hf_file"],
                local_dir="models"
            )
            file_size = os.path.getsize(downloaded) if os.path.exists(downloaded) else -1
            logger.info("Download SUCCESS: path='%s', size=%d bytes", downloaded, file_size)
            model_path = downloaded
        except Exception as e:
            logger.warning("Download FAILED for '%s': %s", model_name, e, exc_info=True)
            _model_statuses[model_name] = "unavailable"
            raise

    try:
        logger.info("Loading model '%s' from '%s'", model_name, model_path)
        m = get_model(model_name=model_name, num_classes=Config.NUM_CLASSES, pretrained=False)
        data = torch.load(model_path, map_location=Config.DEVICE)
        if isinstance(data, dict):
            logger.info("Checkpoint keys: %s", list(data.keys()))
            if "model_state_dict" in data or "state_dict" in data:
                data = data.get("model_state_dict") or data["state_dict"]
                logger.info("Extracted state_dict from checkpoint wrapper")
        m.load_state_dict(data)
        m.to(Config.DEVICE)
        m.eval()
        num_params = sum(p.numel() for p in m.parameters())
        logger.info("Model '%s' loaded OK: %d parameters, device=%s", model_name, num_params, Config.DEVICE)
        _loaded[model_name] = m
        _model_transforms[model_name] = transform
        _model_statuses[model_name] = "loaded"
        return m, transform
    except Exception as e:
        logger.warning("Model load FAILED for '%s': %s", model_name, e, exc_info=True)
        _model_statuses[model_name] = "unavailable"
        raise


def get_active_model():
    if _active_model not in _loaded:
        try:
            load_model(_active_model)
        except Exception:
            return None, None
    return _loaded[_active_model], _model_transforms[_active_model]


def _tta_predict(models, input_tensor):
    from src.config import Config
    import torch
    from torchvision import transforms as T

    all_probs = []
    with torch.no_grad():
        for m in models:
            outputs = m(input_tensor)
            probs = torch.softmax(outputs, dim=1).squeeze(0).cpu().numpy()
            all_probs.append(probs)

    if not Config.TTA_ENABLED:
        return np.mean(all_probs, axis=0)

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


def predict_image(image_bytes: bytes, filename: str = "upload.jpg", currency: str = "USD") -> dict:

    os.makedirs("temp", exist_ok=True)

    image_path = os.path.join("temp", filename)

    with open(image_path, "wb") as f:
        f.write(image_bytes)
    model, transform = get_active_model()

    if model is not None:
        try:
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            import torch
            input_tensor = transform(pil_image).unsqueeze(0).to("cpu")

            avg_probs = _tta_predict([model], input_tensor)
            pred_idx = int(np.argmax(avg_probs))
            confidence = float(avg_probs[pred_idx])
            predicted_class = CLASSES[pred_idx]
        except Exception:
            predicted_class = "N/A"
            confidence = 0.0
            avg_probs = np.array([0.25, 0.25, 0.25, 0.25])
    else:
        predicted_class = "N/A"
        confidence = 0.0
        avg_probs = np.array([0.25, 0.25, 0.25, 0.25])

    base_sev = CLASS_SEVERITY.get(predicted_class, 0.5)
    severity_score = round(min(base_sev * (0.5 + 0.5 * confidence), 1.0), 3)

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
    # Only estimate cost/time/action if we have a real prediction
    if predicted_class in CLASS_SEVERITY:
        cost_estimate = estimate_repair_cost(predicted_class, severity_label, confidence, currency=currency)
        time_estimate = estimate_repair_time(predicted_class, severity_label, confidence)
        action_plan = get_action_plan(predicted_class, severity_label)
        result["repair_cost"] = cost_estimate
        result["repair_time"] = time_estimate
        result["action_plan"] = action_plan
    else:
        result["repair_cost"] = None
        result["repair_time"] = None
        result["action_plan"] = None


    try:
        pdf_path = generate_pdf(
            image_path=image_path,
            prediction=predicted_class,
            confidence=confidence,
            severity=severity_label,
            repair_cost=result["repair_cost"],
            repair_time=result["repair_time"],
        )
        result["pdf_path"] = pdf_path
    except Exception:
        result["pdf_path"] = None

    return result