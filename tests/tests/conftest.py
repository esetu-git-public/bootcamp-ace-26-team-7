import os
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_IMAGE_PATH = FIXTURES_DIR / "sample.jpg"


@pytest.fixture
def sample_image_bytes():
    with open(SAMPLE_IMAGE_PATH, "rb") as f:
        return f.read()


@pytest.fixture
def sample_image_path():
    return SAMPLE_IMAGE_PATH


@pytest.fixture
def expected_classes():
    return ["Cracks", "Patch", "Potholes", "Surface Defects"]


@pytest.fixture(autouse=True)
def reset_prediction_cache():
    import backend.prediction as pred
    pred._model = None
    pred._transform = None


@pytest.fixture
def mock_model_fallback(monkeypatch):
    monkeypatch.setattr("backend.prediction.MODEL_PATH", "/nonexistent/model.pth")

    def mock_download(*args, **kwargs):
        raise Exception("Simulated network error")

    try:
        monkeypatch.setattr(
            "huggingface_hub.hf_hub_download", mock_download
        )
    except ModuleNotFoundError:
        pass

    import backend.prediction as pred
    pred._model = None
    pred._transform = None

    yield

    pred._model = None
    pred._transform = None
