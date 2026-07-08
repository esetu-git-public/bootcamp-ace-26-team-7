import pytest

from backend.prediction import CLASSES, CLASS_SEVERITY, predict_image


class TestFallbackPrediction:
    def test_fallback_returns_potholes(self, mock_model_fallback, sample_image_bytes):
        result = predict_image(image_bytes=sample_image_bytes, filename="test.jpg")
        assert result["success"] is True
        assert result["predicted_class"] == "Potholes"

    def test_fallback_confidence(self, mock_model_fallback, sample_image_bytes):
        result = predict_image(image_bytes=sample_image_bytes, filename="test.jpg")
        assert result["confidence"] == 0.85

    def test_fallback_probabilities(self, mock_model_fallback, sample_image_bytes):
        result = predict_image(image_bytes=sample_image_bytes, filename="test.jpg")
        probs = result["class_probabilities"]
        assert probs == {"Cracks": 0.05, "Patch": 0.05, "Potholes": 0.85, "Surface Defects": 0.05}

    def test_fallback_returns_all_expected_keys(self, mock_model_fallback, sample_image_bytes):
        result = predict_image(image_bytes=sample_image_bytes, filename="test.jpg")
        expected_keys = {
            "success", "predicted_class", "confidence",
            "class_probabilities", "severity_score", "severity_label",
        }
        assert set(result.keys()) == expected_keys


class TestSeverityComputation:
    @pytest.mark.parametrize("cls,base_sev", [
        ("Cracks", 0.50),
        ("Patch", 0.25),
        ("Potholes", 0.75),
        ("Surface Defects", 0.60),
    ])
    def test_base_severity_mapping(self, cls, base_sev):
        assert CLASS_SEVERITY[cls] == base_sev

    def test_classes_match(self, expected_classes):
        assert set(CLASSES) == set(expected_classes)

    def test_class_probabilities_order(self, mock_model_fallback, sample_image_bytes):
        result = predict_image(image_bytes=sample_image_bytes, filename="test.jpg")
        probs = result["class_probabilities"]
        keys = list(probs.keys())
        assert keys == CLASSES

    def test_predict_with_filename(self, mock_model_fallback, sample_image_bytes):
        result = predict_image(
            image_bytes=sample_image_bytes, filename="road_crack.jpg"
        )
        assert result["success"] is True


class TestErrorHandling:
    def test_invalid_image_bytes_raises(self):
        with pytest.raises(Exception):
            predict_image(image_bytes=b"not an image", filename="bad.jpg")
