"""
╔═══════════════════════════════════════════════════════════════╗
║  TDD — Varnitha (Scrum Master)                               ║
║  Module: backend/prediction.py — Model Registry & Selection  ║
║  Run:  pytest TDD/Varnitha_test_model_selection.py -v        ║
╚═══════════════════════════════════════════════════════════════╝

Tests covering:
  - Model registry (get_available_models)
  - Model selection & activation (select_model)
  - Status tracking (get_active_model_name, get_active_model_status)
  - API endpoints (GET /api/models, POST /api/model/select,
    GET /api/model/status)
  - Per-model status isolation
  - Registry consistency with MODEL_REGISTRY
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ── Mock Supabase before importing app ──────────────────────────────
_mock_supabase = MagicMock()
_mock_service = MagicMock()
_table_mock = MagicMock()
_query_mock = MagicMock()
_table_mock.select.return_value = _query_mock
_query_mock.eq.return_value = _query_mock
_query_mock.execute.return_value = MagicMock(data=[])
_mock_supabase.table.return_value = _table_mock
_mock_service.table.return_value = _table_mock
_mock_supabase.auth.exchange_code_for_session.return_value = MagicMock(
    user=MagicMock(id="gh-uid", email="gh@user.com",
                   user_metadata={"user_name": "ghuser", "full_name": "GH User"}),
    session=MagicMock(access_token="gh-token"),
)

patch("backend.database.get_supabase", return_value=_mock_supabase).start()
patch("backend.database.get_service_client", return_value=_mock_service).start()

from backend.main import app, create_jwt_token

client = TestClient(app)


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_registry():
    """Reset all global state in prediction.py before each test."""
    import backend.prediction as pred
    pred._loaded = {}
    pred._model_transforms = {}
    pred._model_statuses = {}
    pred._active_model = "resnet50"
    pred.ACTIVE_MODEL_STATUS = "unavailable"


@pytest.fixture
def auth_header():
    """Standard bearer token for authenticated requests."""
    token = create_jwt_token("uid-1", "testuser")
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════
#  get_available_models()
#  Returns all 3 models with name, display_name, size_mb,
#  is_loaded, is_active, and status fields.
# ═══════════════════════════════════════════════════════════════════

class TestGetAvailableModels:

    def test_returns_three_models(self):
        from backend.prediction import get_available_models
        models = get_available_models()
        assert len(models) == 3

    def test_model_names(self):
        from backend.prediction import get_available_models
        names = [m["name"] for m in get_available_models()]
        assert "resnet50" in names
        assert "efficientnet_b0" in names
        assert "vit_b_16" in names

    def test_display_names_match(self):
        from backend.prediction import get_available_models
        by_name = {m["name"]: m["display_name"] for m in get_available_models()}
        assert by_name["resnet50"] == "ResNet50"
        assert by_name["efficientnet_b0"] == "EfficientNet-B0"
        assert by_name["vit_b_16"] == "ViT-B/16"

    def test_all_have_size_mb(self):
        from backend.prediction import get_available_models
        for m in get_available_models():
            assert isinstance(m["size_mb"], int)
            assert m["size_mb"] > 0

    def test_default_active_model(self):
        """Default active model is resnet50 (only one is_active=True)."""
        from backend.prediction import get_available_models
        active = [m for m in get_available_models() if m["is_active"]]
        assert len(active) == 1
        assert active[0]["name"] == "resnet50"

    def test_all_start_unloaded(self):
        """No model is loaded by default."""
        from backend.prediction import get_available_models
        assert all(m["is_loaded"] is False for m in get_available_models())

    def test_all_start_unavailable(self):
        """All models start with status 'unavailable'."""
        from backend.prediction import get_available_models
        assert all(m["status"] == "unavailable" for m in get_available_models())


# ═══════════════════════════════════════════════════════════════════
#  select_model(model_name)
#  Switches the active model. Returns {success, active_model, status}.
# ═══════════════════════════════════════════════════════════════════

class TestSelectModel:

    def test_select_valid_model_returns_success(self):
        from backend.prediction import select_model
        result = select_model("vit_b_16")
        assert result["success"] is True
        assert result["active_model"] == "vit_b_16"

    def test_select_changes_active_model(self):
        from backend.prediction import select_model, get_active_model_name
        select_model("efficientnet_b0")
        assert get_active_model_name() == "efficientnet_b0"

    def test_select_unknown_model_returns_fail(self):
        from backend.prediction import select_model
        result = select_model("nonexistent")
        assert result["success"] is False
        assert "Unknown" in result.get("message", "")

    def test_select_same_model_twice_idempotent(self):
        """Selecting the same model twice is safe."""
        from backend.prediction import select_model, get_active_model_name
        select_model("resnet50")
        assert get_active_model_name() == "resnet50"
        select_model("resnet50")
        assert get_active_model_name() == "resnet50"

    def test_select_fails_gracefully_on_network_error(self, mock_model_fallback):
        """With mocked network error, selection fails but stays active."""
        from backend.prediction import select_model
        result = select_model("vit_b_16")
        assert result["success"] is False
        assert result["active_model"] == "vit_b_16"
        assert result["status"] == "unavailable"


# ═══════════════════════════════════════════════════════════════════
#  Model Status
#  ACTIVE_MODEL_STATUS and getter functions track the current state.
# ═══════════════════════════════════════════════════════════════════

class TestModelStatus:

    def test_default_status_unavailable(self):
        from backend.prediction import get_active_model_status
        assert get_active_model_status() == "unavailable"

    def test_status_getter(self):
        from backend.prediction import get_active_model_name
        assert get_active_model_name() == "resnet50"

    def test_status_endpoint_returns_active_model(self):
        """GET /api/model/status includes active_model field."""
        r = client.get("/api/model/status")
        assert r.status_code == 200
        body = r.json()
        assert "status" in body
        assert "active_model" in body
        assert body["active_model"] == "resnet50"


# ═══════════════════════════════════════════════════════════════════
#  GET /api/models — Public endpoint returning full model list.
# ═══════════════════════════════════════════════════════════════════

class TestModelsEndpoint:

    def test_returns_list(self):
        r = client.get("/api/models")
        assert r.status_code == 200
        body = r.json()
        assert "models" in body
        assert isinstance(body["models"], list)

    def test_contains_three_entries(self):
        r = client.get("/api/models")
        assert len(r.json()["models"]) == 3

    def test_each_has_all_fields(self):
        r = client.get("/api/models")
        required = {"name", "display_name", "size_mb",
                    "is_loaded", "is_active", "status"}
        for m in r.json()["models"]:
            assert set(m.keys()) == required, f"Missing fields in {m['name']}"


# ═══════════════════════════════════════════════════════════════════
#  POST /api/model/select — Switch active model via API.
# ═══════════════════════════════════════════════════════════════════

class TestSelectModelEndpoint:

    def test_select_valid_model(self):
        r = client.post("/api/model/select",
                        json={"model_name": "vit_b_16"})
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["active_model"] == "vit_b_16"

    def test_select_invalid_model(self):
        r = client.post("/api/model/select",
                        json={"model_name": "unknown"})
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is False

    def test_select_missing_model_name(self):
        r = client.post("/api/model/select", json={})
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is False

    def test_select_updates_status_endpoint(self):
        client.post("/api/model/select",
                    json={"model_name": "efficientnet_b0"})
        r = client.get("/api/model/status")
        assert r.json()["active_model"] == "efficientnet_b0"

    def test_select_updates_models_endpoint(self):
        client.post("/api/model/select",
                    json={"model_name": "vit_b_16"})
        r = client.get("/api/models")
        active = [m for m in r.json()["models"] if m["is_active"]]
        assert len(active) == 1
        assert active[0]["name"] == "vit_b_16"

    def test_select_is_idempotent(self):
        r1 = client.post("/api/model/select",
                         json={"model_name": "resnet50"})
        r2 = client.post("/api/model/select",
                         json={"model_name": "resnet50"})
        assert r1.json()["active_model"] == r2.json()["active_model"]


# ═══════════════════════════════════════════════════════════════════
#  Per-Model Status Isolation
#  Each model tracks its own load status independently.
# ═══════════════════════════════════════════════════════════════════

class TestPerModelStatus:

    def test_statuses_after_select(self):
        from backend.prediction import select_model, get_available_models

        select_model("efficientnet_b0")
        models = {m["name"]: m for m in get_available_models()}

        assert models["efficientnet_b0"]["is_active"] is True
        assert models["resnet50"]["is_active"] is False

    def test_only_one_active_at_a_time(self):
        from backend.prediction import select_model, get_available_models

        select_model("vit_b_16")
        active = [m for m in get_available_models() if m["is_active"]]
        assert len(active) == 1

        select_model("resnet50")
        active = [m for m in get_available_models() if m["is_active"]]
        assert len(active) == 1


# ═══════════════════════════════════════════════════════════════════
#  MODEL_REGISTRY Consistency
#  The MODEL_REGISTRY dict must have all 3 models with correct keys.
# ═══════════════════════════════════════════════════════════════════

class TestModelRegistryConsistency:

    def test_registry_keys_match_model_names(self):
        from backend.prediction import MODEL_REGISTRY, get_available_models
        registry_keys = set(MODEL_REGISTRY.keys())
        model_names = {m["name"] for m in get_available_models()}
        assert registry_keys == model_names

    def test_each_registry_entry_has_required_fields(self):
        from backend.prediction import MODEL_REGISTRY
        required = {"display_name", "hf_file", "hf_repo", "size_mb"}
        for name, info in MODEL_REGISTRY.items():
            assert set(info.keys()) == required, f"{name} missing fields"

    def test_all_hf_repos_point_same_repo(self):
        from backend.prediction import MODEL_REGISTRY
        repos = {info["hf_repo"] for info in MODEL_REGISTRY.values()}
        assert len(repos) == 1
        assert "surface-crack-detection-model" in repos.pop()
