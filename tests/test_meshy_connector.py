"""
MorphoMesh: Comprehensive Unit & Integration Test Suite for Meshy AI Connector.

Verifies:
  1. Configuration & Authentication Resolution (MESHY_API_KEY, precedence, model normalization).
  2. Connector Lifecycle, Health Probes, and Dependency Auditing.
  3. Zero-VRAM Offline Procedural Fallback (valid GLB/OBJ, 4-channel PBR textures, /boost high-fidelity).
  4. Native /boost & --boost prompt parsing and multi-stage workflow configuration.
  5. Multi-Mode API Workflows: text-to-3d (preview & refine), image-to-3d (base64 and remote URL).
  6. Polling, Timeout Handling, and Network Error Handling.
  7. Circuit Breaker Fault Tolerance, state transitions, and fallback routing.
  8. ConnectorRegistry Integration (auto-registration, aliasing, stage filtering).
  9. InferenceAdapter Integration (backend="meshy" routing, boost flag propagation).
  10. FastMCP Server Integration (morphomesh_create_3d_asset with backend="meshy").

100% Offline Compatible: unit tests mock network calls with standard library unittest.mock.
"""

from __future__ import annotations

import base64
import io
import json
import os
import struct
import time
from unittest.mock import MagicMock, patch
import urllib.error

import numpy as np
import pytest
from PIL import Image

from morphomesh.connectors import (
    BaseConnector,
    CircuitBreaker,
    CircuitBreakerState,
    ConnectorRegistry,
    DependencyCheckResult,
    HealthCheckResult,
    PBRTextureMaps,
    MeshyConfig,
    MeshyConnector,
    MeshyInput,
    MeshyOutput,
)
from morphomesh.connectors.meshy_connector import MESHY_API_BASE, MESHY_MODEL_MAP
from morphomesh.connectors.tripo_connector import parse_glb_metrics
from morphomesh.inference_adapter import (
    EnhancedCreate3DAssetOutput,
    MeshGeometry,
    get_inference_adapter,
)
from morphomesh.models import (
    ERR_BACKEND_UNAVAILABLE,
    ERR_IMAGE_NOT_FOUND,
    ERR_INFERENCE_FAILED,
    ERR_INVALID_ARGUMENT,
    Create3DAssetInput,
    MorphoMeshException,
)
from morphomesh.server import morphomesh_create_3d_asset


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(autouse=True)
def reset_env_and_registry(monkeypatch):
    """Ensure environment credentials and registry singletons are clean for each test."""
    monkeypatch.delenv("MESHY_API_KEY", raising=False)
    monkeypatch.delenv("MESHY_AI_API_KEY", raising=False)
    ConnectorRegistry.reset_all()
    yield
    ConnectorRegistry.reset_all()


@pytest.fixture
def sample_concept_image(tmp_path) -> str:
    """Create a temporary concept image on disk."""
    img = Image.new("RGBA", (256, 256), (180, 40, 50, 255))
    img_path = str(tmp_path / "meshy_test_concept.png")
    img.save(img_path)
    return img_path


@pytest.fixture
def sample_glb_file(tmp_path) -> str:
    """Create a temporary valid GLB file."""
    geom = MeshGeometry()
    geom.add_box((0.0, 0.0, 0.5), (0.5, 0.5, 0.5))
    glb_path = str(tmp_path / "sample_mesh.glb")
    geom.export_glb(glb_path)
    return glb_path


# ==============================================================================
# 1. CONFIGURATION & CREDENTIAL RESOLUTION TESTS
# ==============================================================================

class TestMeshyConfigAndAuth:
    """Verify configuration parsing and authentication key discovery."""

    def test_default_config(self):
        cfg = MeshyConfig()
        assert cfg.ai_model == "meshy-4"
        assert cfg.mode == "auto"
        assert cfg.base_url == "https://api.meshy.ai"
        assert cfg.timeout_seconds == 300.0
        assert cfg.polling_interval_seconds == 2.0
        assert cfg.art_style == "realistic"
        assert cfg.topology == "quad"
        assert cfg.target_polycount == 30000
        assert cfg.texture_richness == "high"
        assert cfg.pbr is True
        assert cfg.fallback_to_mock is True
        assert cfg.api_key is None

    def test_ai_model_normalization(self):
        cfg1 = MeshyConfig(ai_model="v4")
        assert cfg1.ai_model == "meshy-4"

        cfg2 = MeshyConfig(ai_model="meshy-3")
        assert cfg2.ai_model == "meshy-3"

        cfg3 = MeshyConfig(ai_model="latest")
        assert cfg3.ai_model == "meshy-4"

        cfg4 = MeshyConfig(ai_model="/boost")
        assert cfg4.ai_model == "meshy-4"

    def test_api_key_from_explicit_config(self):
        conn = MeshyConnector(config={"api_key": "msy_explicit_secret_key_12345"})
        assert conn._resolve_api_key() == "msy_explicit_secret_key_12345"

    def test_api_key_from_meshy_env(self, monkeypatch):
        monkeypatch.setenv("MESHY_API_KEY", "msy_env_secret_key_67890")
        conn = MeshyConnector()
        assert conn._resolve_api_key() == "msy_env_secret_key_67890"

    def test_api_key_from_meshy_ai_legacy_env(self, monkeypatch):
        monkeypatch.setenv("MESHY_AI_API_KEY", "msy_legacy_secret_key_99999")
        conn = MeshyConnector()
        assert conn._resolve_api_key() == "msy_legacy_secret_key_99999"

    def test_api_key_precedence_config_over_env(self, monkeypatch):
        monkeypatch.setenv("MESHY_API_KEY", "env_key")
        monkeypatch.setenv("MESHY_AI_API_KEY", "legacy_key")
        conn = MeshyConnector(config={"api_key": "config_key"})
        assert conn._resolve_api_key() == "config_key"

    def test_absent_api_key_returns_none(self):
        conn = MeshyConnector()
        assert conn._resolve_api_key() is None


# ==============================================================================
# 2. LIFECYCLE, HEALTH PROBES & DEPENDENCY AUDIT TESTS
# ==============================================================================

class TestMeshyLifecycleAndHealth:
    """Verify connector lifecycle hooks, health check diagnostic probes, and dependencies."""

    def test_initialize_and_close(self):
        conn = MeshyConnector()
        assert not conn.is_initialized
        assert conn.initialize() is True
        assert conn.is_initialized
        conn.close()
        assert not conn.is_initialized

    def test_check_dependencies_satisfied(self):
        conn = MeshyConnector()
        deps = conn.check_dependencies()
        assert isinstance(deps, DependencyCheckResult)
        assert deps.satisfied is True
        assert len(deps.missing_packages) == 0

    def test_health_check_mock_mode(self):
        conn = MeshyConnector(config={"mode": "mock"})
        health = conn.health_check()
        assert isinstance(health, HealthCheckResult)
        assert health.status == "healthy"
        assert health.circuit_state == "CLOSED"
        assert "mock" in health.message.lower()

    def test_health_check_degraded_without_api_key(self):
        conn = MeshyConnector()
        health = conn.health_check()
        assert health.status == "degraded"
        assert "no meshy_api_key" in health.message.lower()

    def test_health_check_healthy_with_mocked_api(self):
        conn = MeshyConnector(config={"api_key": "msy_valid_key"})
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            health = conn.health_check()
            assert health.status == "healthy"
            assert health.latency_ms >= 0.0
            assert "online" in health.message.lower()

    def test_health_check_extracts_credit_balance(self):
        conn = MeshyConnector(config={"api_key": "msy_valid_key"})
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({"balance": 1500}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            health = conn.health_check()
            assert health.status == "healthy"
            assert health.details.get("credit_balance") == 1500

    def test_health_check_unhealthy_on_http_401(self):
        conn = MeshyConnector(config={"api_key": "msy_invalid_key"})
        err = urllib.error.HTTPError("https://api.meshy.ai/openapi/v2/text-to-3d", 401, "Unauthorized", {}, io.BytesIO(b"{}"))

        with patch("urllib.request.urlopen", side_effect=err):
            health = conn.health_check()
            assert health.status == "unhealthy"
            assert health.dependencies_met is False
            assert "401" in health.message

    def test_health_check_degraded_on_network_error(self):
        conn = MeshyConnector(config={"api_key": "msy_key"})
        err = urllib.error.URLError("Connection refused")

        with patch("urllib.request.urlopen", side_effect=err):
            health = conn.health_check()
            assert health.status == "degraded"
            assert "unreachable" in health.message.lower()


# ==============================================================================
# 3. ZERO-VRAM OFFLINE PROCEDURAL MOCK & /BOOST PARSING TESTS
# ==============================================================================

class TestMeshyProceduralMock:
    """Verify offline mock fallback, /boost handling, geometry synthesis, and textures."""

    def test_mock_generation_text_prompt(self, tmp_path):
        conn = MeshyConnector(config={"mode": "mock"})
        inp = MeshyInput(
            prompt="cybernetic chimera",
            output_dir=str(tmp_path / "out_chimera"),
        )
        out = conn.execute(inp)

        assert isinstance(out, MeshyOutput)
        assert out.execution_mode == "mock"
        assert os.path.isfile(out.glb_path)
        assert os.path.isfile(out.mesh_path)
        assert out.vertex_count > 0
        assert out.face_count > 0
        assert out.pbr_textures is not None
        assert os.path.isfile(out.pbr_textures.albedo_path)
        assert os.path.isfile(out.pbr_textures.normal_path)
        assert os.path.isfile(out.pbr_textures.roughness_path)
        assert os.path.isfile(out.pbr_textures.metallic_path)
        assert os.path.isfile(out.rendered_image_path)
        assert out.boost_applied is False

    def test_mock_generation_with_boost_flag(self, tmp_path):
        conn = MeshyConnector(config={"mode": "mock"})
        inp = MeshyInput(
            prompt="mystic jade dragon /boost",
            output_dir=str(tmp_path / "out_boost"),
        )
        out = conn.execute(inp)

        assert out.boost_applied is True
        assert out.refine_task_id is not None
        assert out.pbr_textures.resolution == 2048
        assert "refined" in out.raw_task_output.get("stage")

    def test_boost_prompt_parsing_and_cleaning(self):
        inp1 = MeshyInput(prompt="ancient guardian /boost")
        assert inp1.prompt == "ancient guardian"
        assert inp1.boost is True
        assert inp1.auto_refine is True
        assert inp1.texture_richness == "high"

        inp2 = MeshyInput(prompt="crimson phoenix --boost")
        assert inp2.prompt == "crimson phoenix"
        assert inp2.boost is True
        assert inp2.auto_refine is True

    def test_boost_prompt_variations_and_case_insensitivity(self):
        """Verify uppercase /BOOST, --BOOST, /Boost, and prefix tokens are cleaned."""
        inp1 = MeshyInput(prompt="Cyber Dragon /BOOST")
        assert inp1.prompt == "Cyber Dragon"
        assert inp1.boost is True
        assert inp1.auto_refine is True

        inp2 = MeshyInput(prompt="Chimera --BOOST")
        assert inp2.prompt == "Chimera"
        assert inp2.boost is True

        inp3 = MeshyInput(prompt="/boost Void Titan")
        assert inp3.prompt == "Void Titan"
        assert inp3.boost is True

        inp4 = MeshyInput(prompt="Titan /Boost")
        assert inp4.prompt == "Titan"
        assert inp4.boost is True

    def test_explicit_boost_flag_without_prompt_token(self):
        """Verify passing boost=True explicitly activates auto_refine and high richness."""
        inp = MeshyInput(prompt="Cyber Hound", boost=True)
        assert inp.prompt == "Cyber Hound"
        assert inp.boost is True
        assert inp.auto_refine is True
        assert inp.texture_richness == "high"

    def test_string_prompt_input_coercion(self, tmp_path):
        conn = MeshyConnector(config={"mode": "mock"})
        out = conn.execute("robotic hound")
        assert out.execution_mode == "mock"
        assert os.path.isfile(out.glb_path)

    def test_mock_generation_obj_format(self, tmp_path):
        conn = MeshyConnector(config={"mode": "mock"})
        inp = MeshyInput(
            prompt="stone golem",
            output_format="obj",
            output_dir=str(tmp_path / "out_obj"),
        )
        out = conn.execute(inp)
        assert out.mesh_path.endswith(".obj")
        assert os.path.isfile(out.mesh_path)

    def test_validation_empty_input_raises_exception(self):
        conn = MeshyConnector(config={"mode": "mock"})
        with pytest.raises(MorphoMeshException) as exc_info:
            conn.execute(MeshyInput(prompt=None, image_path=None))
        assert exc_info.value.code == ERR_INVALID_ARGUMENT

    def test_validation_missing_image_path_raises(self):
        conn = MeshyConnector(config={"mode": "mock"})
        with pytest.raises(MorphoMeshException) as exc_info:
            conn.execute(MeshyInput(task_type="image_to_3d", image_path=None))
        assert exc_info.value.code == ERR_INVALID_ARGUMENT

    def test_validation_missing_preview_task_id_raises(self):
        conn = MeshyConnector(config={"mode": "mock"})
        with pytest.raises(MorphoMeshException) as exc_info:
            conn.execute(MeshyInput(task_type="refine_text_to_3d", preview_task_id=None))
        assert exc_info.value.code == ERR_INVALID_ARGUMENT


# ==============================================================================
# 4. API WORKFLOW TESTS (MOCKED HTTP BOUNDARY)
# ==============================================================================

class TestMeshyApiWorkflows:
    """Verify live HTTP workflow parsing for text-to-3d, image-to-3d, and refine stages."""

    def test_text_to_3d_preview_api_workflow(self, tmp_path, sample_glb_file):
        """Test single-stage preview text-to-3d generation."""
        conn = MeshyConnector(config={"api_key": "msy_live_mock_key", "mode": "api"})

        post_resp = io.BytesIO(json.dumps({"result": "task_preview_001"}).encode("utf-8"))
        poll_resp = io.BytesIO(
            json.dumps({
                "id": "task_preview_001",
                "status": "SUCCEEDED",
                "progress": 100,
                "model_urls": {"glb": "https://assets.meshy.ai/model.glb"},
                "thumbnail_url": "https://assets.meshy.ai/thumb.png",
                "texture_urls": [],
            }).encode("utf-8")
        )
        with open(sample_glb_file, "rb") as f:
            glb_bytes = f.read()

        preview_img = Image.new("RGB", (64, 64), (100, 150, 200))
        prev_bytes = io.BytesIO()
        preview_img.save(prev_bytes, "JPEG")
        prev_bytes.seek(0)

        def mock_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            if "/openapi/v2/text-to-3d" in url and getattr(req, "method", None) == "POST":
                m = MagicMock()
                m.read.return_value = post_resp.getvalue()
                m.__enter__.return_value = m
                return m
            elif "/openapi/v2/text-to-3d/task_preview_001" in url:
                m = MagicMock()
                m.read.return_value = poll_resp.getvalue()
                m.__enter__.return_value = m
                return m
            elif "model.glb" in url:
                m = MagicMock()
                m.read.return_value = glb_bytes
                m.__enter__.return_value = m
                return m
            elif "thumb.png" in url:
                m = MagicMock()
                m.read.return_value = prev_bytes.getvalue()
                m.__enter__.return_value = m
                return m
            raise ValueError(f"Unexpected URL: {url}")

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            inp = MeshyInput(
                prompt="armored pangolin",
                output_dir=str(tmp_path / "api_preview"),
            )
            out = conn.execute(inp)

            assert out.task_id == "task_preview_001"
            assert out.execution_mode == "api"
            assert out.boost_applied is False
            assert os.path.isfile(out.glb_path)
            assert out.vertex_count > 0

    def test_text_to_3d_with_boost_api_workflow(self, tmp_path, sample_glb_file):
        """Test multi-stage text-to-3d (/boost preview followed by auto-refine)."""
        conn = MeshyConnector(config={"api_key": "msy_live_mock_key", "mode": "api"})

        prev_post = io.BytesIO(json.dumps({"result": "task_preview_002"}).encode("utf-8"))
        prev_poll = io.BytesIO(
            json.dumps({
                "id": "task_preview_002",
                "status": "SUCCEEDED",
                "progress": 100,
                "model_urls": {"glb": "https://assets.meshy.ai/prev.glb"},
            }).encode("utf-8")
        )

        refine_post = io.BytesIO(json.dumps({"result": "task_refine_002"}).encode("utf-8"))
        refine_poll = io.BytesIO(
            json.dumps({
                "id": "task_refine_002",
                "status": "SUCCEEDED",
                "progress": 100,
                "model_urls": {"glb": "https://assets.meshy.ai/refined.glb"},
                "thumbnail_url": "https://assets.meshy.ai/refined_thumb.jpg",
                "texture_urls": [{
                    "base_color": "https://assets.meshy.ai/albedo.png",
                    "normal": "https://assets.meshy.ai/normal.png",
                    "roughness": "https://assets.meshy.ai/roughness.png",
                    "metallic": "https://assets.meshy.ai/metallic.png",
                }],
            }).encode("utf-8")
        )

        with open(sample_glb_file, "rb") as f:
            glb_bytes = f.read()

        tex_bytes = io.BytesIO()
        Image.new("RGB", (64, 64), (128, 128, 255)).save(tex_bytes, "PNG")
        tex_bytes.seek(0)

        def mock_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            if "/openapi/v2/text-to-3d" in url and getattr(req, "method", None) == "POST":
                body = json.loads(req.data.decode("utf-8"))
                if body.get("mode") == "preview":
                    m = MagicMock()
                    m.read.return_value = prev_post.getvalue()
                    m.__enter__.return_value = m
                    return m
                elif body.get("mode") == "refine":
                    m = MagicMock()
                    m.read.return_value = refine_post.getvalue()
                    m.__enter__.return_value = m
                    return m
            elif "/openapi/v2/text-to-3d/task_preview_002" in url:
                m = MagicMock()
                m.read.return_value = prev_poll.getvalue()
                m.__enter__.return_value = m
                return m
            elif "/openapi/v2/text-to-3d/task_refine_002" in url:
                m = MagicMock()
                m.read.return_value = refine_poll.getvalue()
                m.__enter__.return_value = m
                return m
            elif ".glb" in url:
                m = MagicMock()
                m.read.return_value = glb_bytes
                m.__enter__.return_value = m
                return m
            elif any(t in url for t in ("albedo", "normal", "roughness", "metallic", "thumb")):
                m = MagicMock()
                m.read.return_value = tex_bytes.getvalue()
                m.__enter__.return_value = m
                return m
            raise ValueError(f"Unexpected URL: {url}")

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            inp = MeshyInput(
                prompt="celestial griffin /boost",
                output_dir=str(tmp_path / "api_boost"),
            )
            out = conn.execute(inp)

            assert out.boost_applied is True
            assert out.preview_task_id == "task_preview_002"
            assert out.refine_task_id == "task_refine_002"
            assert out.task_id == "task_refine_002"
            assert out.execution_mode == "api"
            assert os.path.isfile(out.glb_path)

    def test_image_to_3d_api_workflow(self, tmp_path, sample_concept_image, sample_glb_file):
        """Test image-to-3d generation with local image converted to data URI."""
        conn = MeshyConnector(config={"api_key": "msy_live_mock_key", "mode": "api"})

        post_resp = io.BytesIO(json.dumps({"result": "task_img_001"}).encode("utf-8"))
        poll_resp = io.BytesIO(
            json.dumps({
                "id": "task_img_001",
                "status": "SUCCEEDED",
                "progress": 100,
                "model_urls": {"glb": "https://assets.meshy.ai/img_model.glb"},
                "thumbnail_url": "https://assets.meshy.ai/img_thumb.png",
                "texture_urls": [],
            }).encode("utf-8")
        )
        with open(sample_glb_file, "rb") as f:
            glb_bytes = f.read()

        def mock_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            if "/openapi/v1/image-to-3d" in url and getattr(req, "method", None) == "POST":
                body = json.loads(req.data.decode("utf-8"))
                assert body.get("image_url", "").startswith("data:image/png;base64,")
                m = MagicMock()
                m.read.return_value = post_resp.getvalue()
                m.__enter__.return_value = m
                return m
            elif "/openapi/v1/image-to-3d/task_img_001" in url:
                m = MagicMock()
                m.read.return_value = poll_resp.getvalue()
                m.__enter__.return_value = m
                return m
            elif "img_model.glb" in url:
                m = MagicMock()
                m.read.return_value = glb_bytes
                m.__enter__.return_value = m
                return m
            elif "img_thumb.png" in url:
                m = MagicMock()
                m.read.return_value = b"\x89PNG\r\n\x1a\n"
                m.__enter__.return_value = m
                return m
            raise ValueError(f"Unexpected URL: {url}")

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            inp = MeshyInput(
                image_path=sample_concept_image,
                task_type="image_to_3d",
                output_dir=str(tmp_path / "api_image"),
            )
            out = conn.execute(inp)

            assert out.task_id == "task_img_001"
            assert out.execution_mode == "api"
            assert os.path.isfile(out.glb_path)

    def test_api_failure_fallback_to_mock(self, tmp_path):
        conn = MeshyConnector(config={"api_key": "msy_key", "mode": "api", "fallback_to_mock": True})
        err = urllib.error.HTTPError("https://api.meshy.ai", 500, "Internal Server Error", {}, io.BytesIO(b"server down"))

        with patch("urllib.request.urlopen", side_effect=err):
            inp = MeshyInput(prompt="frost wolf", output_dir=str(tmp_path / "fail_fallback"))
            out = conn.execute(inp)
            assert out.execution_mode == "mock"
            assert os.path.isfile(out.glb_path)

    def test_api_failure_raises_when_fallback_disabled(self):
        conn = MeshyConnector(config={"api_key": "msy_key", "mode": "api", "fallback_to_mock": False})
        err = urllib.error.HTTPError("https://api.meshy.ai", 500, "Internal Server Error", {}, io.BytesIO(b"server down"))

        with patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(MorphoMeshException) as exc_info:
                conn.execute(MeshyInput(prompt="frost wolf"), raise_on_failure=True)
            assert exc_info.value.code == ERR_INFERENCE_FAILED

    def test_polling_task_failure_raises(self):
        conn = MeshyConnector(config={"api_key": "msy_key", "mode": "api"})

        post_resp = io.BytesIO(json.dumps({"result": "task_fail_01"}).encode("utf-8"))
        poll_resp = io.BytesIO(
            json.dumps({
                "id": "task_fail_01",
                "status": "FAILED",
                "task_error": {"message": "Content moderation policy violation"},
            }).encode("utf-8")
        )

        def mock_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            m = MagicMock()
            if getattr(req, "method", None) == "POST":
                m.read.return_value = post_resp.getvalue()
            else:
                m.read.return_value = poll_resp.getvalue()
            m.__enter__.return_value = m
            return m

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            with pytest.raises(MorphoMeshException) as exc_info:
                conn.execute(MeshyInput(prompt="forbidden content"), raise_on_failure=True)
            assert exc_info.value.code == ERR_INFERENCE_FAILED
            assert "Content moderation" in exc_info.value.message

    def test_post_json_task_handles_null_data_envelope(self):
        """Verify _post_json_task handles responses with data: None without throwing AttributeError."""
        conn = MeshyConnector(config={"api_key": "msy_test_key"})

        # Case 1: data is None, top-level id is present
        resp1 = MagicMock()
        resp1.read.return_value = json.dumps({"data": None, "id": "task_null_data_123"}).encode("utf-8")
        resp1.__enter__.return_value = resp1

        with patch("urllib.request.urlopen", return_value=resp1):
            tid1 = conn._post_json_task("https://api.meshy.ai/openapi/v2/text-to-3d", {"prompt": "foo"}, "msy_key")
            assert tid1 == "task_null_data_123"

        # Case 2: data is nested dict with id
        resp2 = MagicMock()
        resp2.read.return_value = json.dumps({"data": {"id": "task_nested_456"}}).encode("utf-8")
        resp2.__enter__.return_value = resp2

        with patch("urllib.request.urlopen", return_value=resp2):
            tid2 = conn._post_json_task("https://api.meshy.ai/openapi/v2/text-to-3d", {"prompt": "foo"}, "msy_key")
            assert tid2 == "task_nested_456"

    def test_api_workflow_output_envelope_and_dict_textures(self, tmp_path, sample_glb_file):
        """Verify handling of output envelope and dict-format texture_urls."""
        conn = MeshyConnector(config={"api_key": "msy_live_mock_key", "mode": "api"})

        post_resp = io.BytesIO(json.dumps({"result": "task_env_001"}).encode("utf-8"))
        poll_resp = io.BytesIO(
            json.dumps({
                "id": "task_env_001",
                "status": "SUCCEEDED",
                "output": {
                    "model_urls": {"glb": "https://assets.meshy.ai/env_model.glb"},
                    "thumbnail_url": "https://assets.meshy.ai/env_thumb.png",
                    "texture_urls": {
                        "base_color": "https://assets.meshy.ai/albedo.png",
                        "normal": "https://assets.meshy.ai/normal.png",
                    },
                },
            }).encode("utf-8")
        )
        with open(sample_glb_file, "rb") as f:
            glb_bytes = f.read()

        def mock_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            m = MagicMock()
            if getattr(req, "method", None) == "POST":
                m.read.return_value = post_resp.getvalue()
            elif "task_env_001" in url:
                m.read.return_value = poll_resp.getvalue()
            elif "env_model.glb" in url:
                m.read.return_value = glb_bytes
            elif "env_thumb.png" in url:
                m.read.return_value = b"\x89PNG\r\n\x1a\n"
            elif "albedo.png" in url or "normal.png" in url:
                m.read.return_value = b"\x89PNG\r\n\x1a\n"
            else:
                raise ValueError(f"Unexpected URL: {url}")
            m.__enter__.return_value = m
            return m

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            inp = MeshyInput(prompt="armored pangolin", output_dir=str(tmp_path / "env_test"))
            out = conn.execute(inp)
            assert out.task_id == "task_env_001"
            assert os.path.isfile(out.glb_path)
            assert out.pbr_textures is not None
            assert out.pbr_textures.albedo_path is not None
            assert out.pbr_textures.normal_path is not None

    def test_convert_glb_to_obj_extracts_real_mesh(self, tmp_path, sample_glb_file):
        """Verify GLB binary buffer parser correctly writes OBJ vertices and triangle faces."""
        obj_path = str(tmp_path / "extracted.obj")
        conn = MeshyConnector()
        conn._convert_or_export_obj(sample_glb_file, obj_path)

        assert os.path.isfile(obj_path)
        with open(obj_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        v_lines = [l for l in lines if l.startswith("v ")]
        f_lines = [l for l in lines if l.startswith("f ")]
        assert len(v_lines) > 0
        assert len(f_lines) > 0


# ==============================================================================
# 5. CIRCUIT BREAKER FAULT TOLERANCE TESTS
# ==============================================================================

class TestMeshyCircuitBreaker:
    """Verify Circuit Breaker integration with Meshy connector."""

    def test_circuit_breaker_trips_after_failures(self):
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0)
        conn = MeshyConnector(
            config={"api_key": "msy_key", "mode": "api", "fallback_to_mock": False},
            circuit_breaker=breaker,
        )

        err = urllib.error.HTTPError("https://api.meshy.ai", 503, "Service Unavailable", {}, io.BytesIO(b"{}"))
        with patch("urllib.request.urlopen", side_effect=err):
            # Attempt 1 -> fails
            with pytest.raises(MorphoMeshException):
                conn.execute(MeshyInput(prompt="creature"), raise_on_failure=True)
            assert breaker.state == CircuitBreakerState.CLOSED

            # Attempt 2 -> trips to OPEN
            with pytest.raises(MorphoMeshException):
                conn.execute(MeshyInput(prompt="creature"), raise_on_failure=True)
            assert breaker.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_routes_to_mock_when_open(self, tmp_path):
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        breaker.trip()
        assert breaker.state == CircuitBreakerState.OPEN

        conn = MeshyConnector(
            config={"api_key": "msy_key", "mode": "api", "fallback_to_mock": True},
            circuit_breaker=breaker,
        )

        # When OPEN and fallback_to_mock is True, does not make HTTP calls and executes mock
        inp = MeshyInput(prompt="sand beast", output_dir=str(tmp_path / "cb_mock"))
        out = conn.execute(inp, raise_on_failure=False)
        assert out.execution_mode == "mock"
        assert os.path.isfile(out.glb_path)

    def test_circuit_breaker_open_raises_backend_unavailable(self):
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        breaker.trip()

        conn = MeshyConnector(
            config={"api_key": "msy_key", "mode": "api"},
            circuit_breaker=breaker,
        )

        with pytest.raises(MorphoMeshException) as exc_info:
            conn.execute(MeshyInput(prompt="test"), raise_on_failure=True)
        assert exc_info.value.code == ERR_BACKEND_UNAVAILABLE


# ==============================================================================
# 6. CONNECTOR REGISTRY INTEGRATION TESTS
# ==============================================================================

class TestMeshyRegistryIntegration:
    """Verify registration, aliasing, and stage enumeration in ConnectorRegistry."""

    def test_registry_resolves_meshy(self):
        conn = ConnectorRegistry.get("meshy")
        assert isinstance(conn, MeshyConnector)
        assert conn.connector_id == "meshy"

    def test_registry_resolves_meshyai_alias(self):
        conn = ConnectorRegistry.get("meshyai")
        assert isinstance(conn, MeshyConnector)

    def test_registry_resolves_meshy_ai_alias(self):
        conn = ConnectorRegistry.get("meshy_ai")
        assert isinstance(conn, MeshyConnector)

    def test_registry_list_all_connectors_includes_meshy(self):
        connectors = ConnectorRegistry.list_all_connectors()
        assert "meshy" in connectors

    def test_registry_list_connectors_stage2_includes_meshy(self):
        s2 = ConnectorRegistry.list_connectors(stage=2)
        assert "meshy" in s2


# ==============================================================================
# 7. INFERENCE ADAPTER INTEGRATION TESTS
# ==============================================================================

class TestMeshyInferenceAdapterIntegration:
    """Verify backend routing in InferenceAdapter."""

    def test_inference_adapter_routes_to_meshy_text(self, tmp_path):
        adapter = get_inference_adapter(mode="mock")
        req = Create3DAssetInput(
            prompt="golden mechanical scarab",
            model_backend="meshy",
            export_format="glb",
        )
        res = adapter.generate_3d_asset(req)
        assert isinstance(res, EnhancedCreate3DAssetOutput)
        assert os.path.isfile(res.mesh_path)
        assert res.backend_used == "meshy"
        assert res.metadata.get("connector") == "meshy"

    def test_inference_adapter_routes_to_meshy_with_boost(self, tmp_path):
        adapter = get_inference_adapter(mode="mock")
        req = Create3DAssetInput(
            prompt="celestial dragon /boost",
            model_backend="meshy",
            export_format="glb",
        )
        res = adapter.generate_3d_asset(req)
        assert res.metadata.get("boost_applied") is True

    def test_inference_adapter_routes_to_meshy_image(self, sample_concept_image):
        adapter = get_inference_adapter(mode="mock")
        req = Create3DAssetInput(
            image_path=sample_concept_image,
            model_backend="meshy",
            export_format="glb",
        )
        res = adapter.generate_3d_asset(req)
        assert res.metadata.get("connector") == "meshy"
        assert os.path.isfile(res.mesh_path)

    def test_inference_adapter_routes_with_backend_alias(self):
        adapter = get_inference_adapter(mode="mock")
        req = Create3DAssetInput(
            prompt="crimson drake",
            backend="meshy",
            export_format="glb",
        )
        res = adapter.generate_3d_asset(req)
        assert res.backend_used == "meshy"
        assert res.metadata.get("connector") == "meshy"


# ==============================================================================
# 8. SERVER TOOL INTEGRATION TESTS
# ==============================================================================

class TestMeshyServerIntegration:
    """Verify FastMCP server tool execution with model_backend='meshy' or backend='meshy'."""

    @pytest.mark.asyncio
    async def test_server_create_3d_asset_with_meshy_backend(self):
        res = await morphomesh_create_3d_asset(
            prompt="silver cyber wolf",
            model_backend="meshy",
            export_format="glb",
        )
        assert isinstance(res, dict)
        assert "asset_id" in res
        assert "mesh_path" in res
        assert os.path.isfile(res["mesh_path"])
        assert res["format"] == "glb"

    @pytest.mark.asyncio
    async def test_server_create_3d_asset_with_backend_kwarg(self):
        """Verify selecting Meshy backend via backend='meshy' parameter."""
        res = await morphomesh_create_3d_asset(
            prompt="neon mantis",
            backend="meshy",
            export_format="glb",
        )
        assert isinstance(res, dict)
        assert "asset_id" in res
        assert res.get("backend_used") == "meshy"
        assert os.path.isfile(res["mesh_path"])

    @pytest.mark.asyncio
    async def test_server_create_3d_asset_with_boost_prompt(self):
        res = await morphomesh_create_3d_asset(
            prompt="void leviathan /boost",
            model_backend="meshy",
            export_format="glb",
        )
        assert isinstance(res, dict)
        assert res["metadata"]["boost_applied"] is True
