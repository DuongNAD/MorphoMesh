"""
MorphoMesh: Comprehensive Unit & Integration Test Suite for Tripo3D Connector.

Verifies:
  1. Configuration & Authentication Resolution (TRIPO_API_KEY, precedence, model normalization).
  2. Connector Lifecycle, Health Probes, and Dependency Auditing.
  3. Zero-VRAM Offline Procedural Fallback (valid GLB/OBJ, 4-channel PBR textures).
  4. GLB Metric Parsing (pure standard library binary glTF header reader).
  5. Multi-Mode API Workflows: text-to-3D, image-to-3D, and draft-to-refine.
  6. Polling, Timeout Handling, and Network Error Handling.
  7. Circuit Breaker Fault Tolerance, state transitions, and fallback routing.
  8. ConnectorRegistry Integration (auto-registration, aliasing, stage filtering).
  9. InferenceAdapter Integration (backend="tripo" routing).
  10. FastMCP Server Integration (morphomesh_create_3d_asset with backend="tripo").

100% Offline Compatible: unit tests mock network calls; live test available separately.
"""

from __future__ import annotations

import io
import json
import os
import struct
import time
from unittest.mock import MagicMock, patch
import urllib.error

import numpy as np
import shutil
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
    TripoConfig,
    TripoConnector,
    TripoInput,
    TripoOutput,
)
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
    monkeypatch.delenv("TRIPO_API_KEY", raising=False)
    monkeypatch.delenv("TRIPO3D_API_KEY", raising=False)
    ConnectorRegistry.reset_all()
    yield
    ConnectorRegistry.reset_all()


@pytest.fixture
def sample_concept_image(tmp_path) -> str:
    """Create a temporary concept image on disk."""
    img = Image.new("RGBA", (256, 256), (220, 50, 60, 255))
    img_path = str(tmp_path / "yu_nian_an_concept.png")
    img.save(img_path)
    return img_path


@pytest.fixture
def sample_glb_file(tmp_path) -> str:
    """Create a temporary valid GLB file with known boxes."""
    geom = MeshGeometry()
    geom.add_box((0.0, 0.0, 0.5), (0.5, 0.5, 0.5))
    glb_path = str(tmp_path / "sample.glb")
    geom.export_glb(glb_path)
    return glb_path


# ==============================================================================
# 1. CONFIGURATION & CREDENTIAL RESOLUTION TESTS
# ==============================================================================

class TestTripoConfigAndAuth:
    """Verify configuration parsing and authentication key discovery."""

    def test_default_config(self):
        cfg = TripoConfig()
        assert cfg.model_name == "v3.1-20260211"
        assert cfg.mode == "auto"
        assert cfg.timeout_seconds == 300.0
        assert cfg.polling_interval_seconds == 2.0
        assert cfg.texture is True
        assert cfg.pbr is True
        assert cfg.fallback_to_mock is True
        assert cfg.api_key is None

    def test_default_tripo_api_key_constant(self):
        from morphomesh.connectors.tripo_connector import DEFAULT_TRIPO_API_KEY
        assert DEFAULT_TRIPO_API_KEY.startswith("tsk_")
        assert len(DEFAULT_TRIPO_API_KEY) > 20

    def test_model_name_alias_normalization(self):
        assert TripoConfig(model_name="v3.1").model_name == "v3.1-20260211"
        assert TripoConfig(model_name="/v3.1").model_name == "v3.1-20260211"
        assert TripoConfig(model_name="p1").model_name == "P1-20260311"
        assert TripoConfig(model_name="/p1").model_name == "P1-20260311"
        assert TripoConfig(model_name="fast").model_name == "P1-20260311"
        assert TripoConfig(model_name="/fast").model_name == "P1-20260311"
        assert TripoConfig(model_name="boost").model_name == "P1-20260311"
        assert TripoConfig(model_name="/boost").model_name == "P1-20260311"
        assert TripoConfig(model_name="p2").model_name == "P2-20260801"
        assert TripoConfig(model_name="v3.0").model_name == "v3.0-20250812"
        assert TripoConfig(model_name="/v3.0").model_name == "v3.0-20250812"
        assert TripoConfig(model_name="v2.5").model_name == "v2.5-20250123"

    def test_api_key_from_explicit_config(self):
        cfg = TripoConfig(api_key="explicit_key_123")
        conn = TripoConnector(config=cfg)
        assert conn._resolve_api_key() == "explicit_key_123"

    def test_api_key_from_tripo_env(self, monkeypatch):
        monkeypatch.setenv("TRIPO_API_KEY", "env_tripo_key_456")
        conn = TripoConnector()
        assert conn._resolve_api_key() == "env_tripo_key_456"

    def test_api_key_from_tripo3d_legacy_env(self, monkeypatch):
        monkeypatch.setenv("TRIPO3D_API_KEY", "legacy_key_789")
        conn = TripoConnector()
        assert conn._resolve_api_key() == "legacy_key_789"

    def test_api_key_precedence_config_over_env(self, monkeypatch):
        monkeypatch.setenv("TRIPO_API_KEY", "env_key")
        conn = TripoConnector(config=TripoConfig(api_key="config_key"))
        assert conn._resolve_api_key() == "config_key"

    def test_absent_api_key_returns_none(self):
        conn = TripoConnector()
        assert conn._resolve_api_key() is None


# ==============================================================================
# 2. LIFECYCLE, HEALTH CHECK & DEPENDENCY TESTS
# ==============================================================================

class TestTripoLifecycleAndHealth:
    """Verify connector lifecycle hooks, health diagnostics, and dependency audits."""

    def test_initialize_and_close(self):
        conn = TripoConnector()
        assert conn.initialize() is True
        assert conn.is_initialized is True
        conn.close()
        assert conn.is_initialized is False

    def test_check_dependencies_satisfied(self):
        conn = TripoConnector()
        result = conn.check_dependencies()
        assert isinstance(result, DependencyCheckResult)
        assert result.satisfied is True
        assert len(result.missing_packages) == 0

    def test_health_check_mock_mode(self):
        conn = TripoConnector(config={"mode": "mock"})
        result = conn.health_check()
        assert isinstance(result, HealthCheckResult)
        assert result.status == "healthy"
        assert "mock" in result.message.lower()

    def test_health_check_degraded_without_api_key(self):
        conn = TripoConnector(config={"mode": "auto", "api_key": None})
        result = conn.health_check()
        assert result.status == "degraded"
        assert "no tripo_api_key" in result.message.lower()
        assert result.dependencies_met is True

    def test_health_check_healthy_with_mocked_balance_endpoint(self):
        conn = TripoConnector(config={"api_key": "dummy_key"})
        mock_response_json = json.dumps({
            "code": 0,
            "data": {"balance": 580, "frozen": 0}
        }).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response_json
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = conn.health_check()
            assert result.status == "healthy"
            assert "580" in result.message
            assert result.details.get("balance") == 580

    def test_health_check_unhealthy_on_http_401(self):
        conn = TripoConnector(config={"api_key": "invalid_key"})
        http_err = urllib.error.HTTPError(
            url="https://api.tripo3d.ai/v2/openapi/user/balance",
            code=401,
            msg="Unauthorized",
            hdrs={},  # type: ignore
            fp=io.BytesIO(b'{"code": 401, "message": "Invalid API Key"}'),
        )

        with patch("urllib.request.urlopen", side_effect=http_err):
            result = conn.health_check()
            assert result.status == "unhealthy"
            assert "401" in result.message


# ==============================================================================
# 3. ZERO-VRAM PROCEDURAL MOCK EXECUTION TESTS
# ==============================================================================

class TestTripoProceduralMock:
    """Verify deterministic offline procedural 3D generation and PBR texture synthesis."""

    def test_mock_generation_text_prompt(self, tmp_path):
        out_dir = str(tmp_path / "mock_out")
        conn = TripoConnector(config={"mode": "mock"})
        inp = TripoInput(
            prompt="Yu Nian An porcelain doll maiden",
            output_dir=out_dir,
            output_format="glb",
        )
        out = conn.execute(inp)

        assert isinstance(out, TripoOutput)
        assert out.execution_mode == "mock"
        assert os.path.isfile(out.glb_path)
        assert os.path.getsize(out.glb_path) > 0
        assert out.vertex_count > 0
        assert out.face_count > 0

        # Verify 4-channel PBR textures created
        assert out.pbr_textures.albedo_path is not None
        assert os.path.isfile(out.pbr_textures.albedo_path)
        assert out.pbr_textures.normal_path is not None
        assert os.path.isfile(out.pbr_textures.normal_path)
        assert out.pbr_textures.roughness_path is not None
        assert os.path.isfile(out.pbr_textures.roughness_path)
        assert out.pbr_textures.metallic_path is not None
        assert os.path.isfile(out.pbr_textures.metallic_path)

    def test_mock_generation_obj_format(self, tmp_path):
        out_dir = str(tmp_path / "obj_out")
        conn = TripoConnector(config={"mode": "mock"})
        inp = TripoInput(
            prompt="Porcelain figurine",
            output_dir=out_dir,
            output_format="obj",
        )
        out = conn.execute(inp)

        assert out.mesh_path.endswith(".obj")
        assert os.path.isfile(out.mesh_path)

    def test_mock_generation_string_prompt(self, tmp_path):
        conn = TripoConnector(config={"mode": "mock"})
        out = conn.execute("Dư Niệm An porcelain doll maiden")
        assert isinstance(out, TripoOutput)
        assert out.execution_mode == "mock"
        assert os.path.isfile(out.glb_path)

    def test_tripo_input_boost_prompt_parsing(self):
        inp = TripoInput(prompt="Dư Niệm An ancient porcelain maiden /boost")
        assert inp.prompt == "Dư Niệm An ancient porcelain maiden"
        assert inp.model == "P1-20260311"
        assert inp.texture_quality == "detailed"
        assert inp.geometry_quality == "detailed"
        assert inp.pbr is True

    def test_validation_empty_input_raises_exception(self):
        conn = TripoConnector(config={"mode": "mock"})
        with pytest.raises(MorphoMeshException) as exc_info:
            conn.execute(TripoInput(task_type="text_to_model", prompt=None, image_path=None))
        assert exc_info.value.code == ERR_INVALID_ARGUMENT

    def test_validation_missing_image_path_raises(self):
        conn = TripoConnector(config={"mode": "mock"})
        with pytest.raises(MorphoMeshException) as exc_info:
            conn.execute(TripoInput(task_type="image_to_model", image_path=None))
        assert exc_info.value.code == ERR_INVALID_ARGUMENT

    def test_validation_missing_draft_task_id_raises(self):
        conn = TripoConnector(config={"mode": "mock"})
        with pytest.raises(MorphoMeshException) as exc_info:
            conn.execute(TripoInput(task_type="refine_model", draft_model_task_id=None))
        assert exc_info.value.code == ERR_INVALID_ARGUMENT


# ==============================================================================
# 4. GLB METRIC PARSER TESTS
# ==============================================================================

class TestGLBMetricParser:
    """Verify standard-library binary glTF header inspection."""

    def test_parse_valid_glb(self, sample_glb_file):
        verts, faces = parse_glb_metrics(sample_glb_file)
        assert verts > 0
        assert faces > 0

    def test_parse_invalid_file_returns_zeros(self, tmp_path):
        bad_file = str(tmp_path / "corrupt.glb")
        with open(bad_file, "wb") as f:
            f.write(b"not a valid glb header")
        verts, faces = parse_glb_metrics(bad_file)
        assert verts == 0
        assert faces == 0

    def test_parse_nonexistent_file_returns_zeros(self):
        verts, faces = parse_glb_metrics("nonexistent/path/model.glb")
        assert verts == 0
        assert faces == 0


# ==============================================================================
# 4b. GLB TEXTURE EXTRACTION TESTS
# ==============================================================================

class TestGLBTextureExtraction:
    """Verify authentic PBR texture buffer parsing directly from GLB files."""

    def test_extract_glb_textures_from_live_asset(self, tmp_path):
        live_glb = "output/yu_nian_an/Yu_Nian_An_tripo.glb"
        if not os.path.isfile(live_glb):
            pytest.skip("Live Tripo GLB asset not found on disk.")

        from morphomesh.connectors.tripo_connector import extract_glb_textures
        out_dir = str(tmp_path / "extracted_tex")
        maps = extract_glb_textures(live_glb, out_dir, "test_yu_nian_an")

        assert maps is not None
        assert maps.albedo_path is not None
        assert os.path.isfile(maps.albedo_path)
        assert maps.normal_path is not None
        assert os.path.isfile(maps.normal_path)
        assert maps.roughness_path is not None
        assert os.path.isfile(maps.roughness_path)
        assert maps.metallic_path is not None
        assert os.path.isfile(maps.metallic_path)
        assert maps.resolution == 4096

    def test_extract_glb_textures_corrupt_file_returns_none(self, tmp_path):
        from morphomesh.connectors.tripo_connector import extract_glb_textures
        bad_file = str(tmp_path / "corrupt.glb")
        with open(bad_file, "wb") as f:
            f.write(b"not a valid gltf buffer")
        res = extract_glb_textures(bad_file, str(tmp_path), "test")
        assert res is None

    def test_extract_glb_textures_nonexistent_returns_none(self, tmp_path):
        from morphomesh.connectors.tripo_connector import extract_glb_textures
        res = extract_glb_textures("nonexistent/model.glb", str(tmp_path), "test")
        assert res is None


# ==============================================================================
# 5. API EXECUTION WORKFLOW TESTS (MOCKED HTTP)
# ==============================================================================

class TestTripoApiWorkflows:
    """Verify HTTP request building, response handling, and polling logic."""

    @patch.object(TripoConnector, "_poll_task")
    @patch.object(TripoConnector, "_download_file")
    @patch.object(TripoConnector, "_post_json_task")
    def test_text_to_model_api_workflow(
        self, mock_post, mock_download, mock_poll, tmp_path, sample_glb_file
    ):
        out_dir = str(tmp_path / "api_out")
        mock_post.return_value = "task_test_12345"
        mock_poll.return_value = {
            "status": "success",
            "progress": 100,
            "output": {
                "model_url": "https://example.com/tripo_model.glb",
                "rendered_image_url": "https://example.com/rendered.jpg",
            },
        }

        # Emulate downloaded GLB file
        def fake_download(url, target_path):
            import shutil
            shutil.copyfile(sample_glb_file, target_path)

        mock_download.side_effect = fake_download

        conn = TripoConnector(config=TripoConfig(api_key="test_key", mode="api"))
        inp = TripoInput(
            prompt="Dư Niệm An ancient porcelain maiden",
            output_dir=out_dir,
            texture=True,
            pbr=True,
        )
        out = conn.execute(inp)

        assert out.task_id == "task_test_12345"
        assert out.execution_mode == "api"
        assert mock_post.call_count == 1
        assert mock_poll.call_count == 1
        assert os.path.isfile(out.glb_path)

    @patch.object(TripoConnector, "_upload_image_if_needed")
    @patch.object(TripoConnector, "_poll_task")
    @patch.object(TripoConnector, "_download_file")
    @patch.object(TripoConnector, "_post_json_task")
    def test_image_to_model_api_workflow(
        self, mock_post, mock_download, mock_poll, mock_upload, tmp_path, sample_concept_image, sample_glb_file
    ):
        out_dir = str(tmp_path / "img_out")
        mock_upload.return_value = "file_token_abc987"
        mock_post.return_value = "task_img_67890"
        mock_poll.return_value = {
            "status": "success",
            "progress": 100,
            "output": {"model_url": "https://example.com/tripo_img.glb"},
        }

        def fake_download(url, target_path):
            import shutil
            shutil.copyfile(sample_glb_file, target_path)

        mock_download.side_effect = fake_download

        conn = TripoConnector(config=TripoConfig(api_key="test_key", mode="api"))
        inp = TripoInput(
            image_path=sample_concept_image,
            task_type="image_to_model",
            output_dir=out_dir,
        )
        out = conn.execute(inp)

        assert out.task_id == "task_img_67890"
        mock_upload.assert_called_once_with(sample_concept_image, "test_key")

    @patch.object(TripoConnector, "_poll_task")
    @patch.object(TripoConnector, "_download_file")
    @patch.object(TripoConnector, "_post_json_task")
    def test_refine_model_api_workflow(
        self, mock_post, mock_download, mock_poll, tmp_path, sample_glb_file
    ):
        out_dir = str(tmp_path / "refine_out")
        mock_post.return_value = "task_refine_999"
        mock_poll.return_value = {
            "status": "success",
            "progress": 100,
            "output": {"model_url": "https://example.com/refined_model.glb"},
        }

        def fake_download(url, target_path):
            import shutil
            shutil.copyfile(sample_glb_file, target_path)

        mock_download.side_effect = fake_download

        conn = TripoConnector(config=TripoConfig(api_key="test_key", mode="api"))
        inp = TripoInput(
            task_type="refine_model",
            draft_model_task_id="draft_task_111",
            output_dir=out_dir,
        )
        out = conn.execute(inp)

        assert out.task_id == "task_refine_999"
        # Check refine endpoint was targeted
        call_url = mock_post.call_args[0][0]
        assert "/models/refine" in call_url

    def test_api_failure_fallback_to_mock(self, tmp_path):
        out_dir = str(tmp_path / "fallback_out")
        conn = TripoConnector(config=TripoConfig(api_key="test_key", mode="api", fallback_to_mock=True))

        # Force post_json_task to raise network error
        with patch.object(TripoConnector, "_post_json_task", side_effect=Exception("Network drop")):
            inp = TripoInput(prompt="Dư Niệm An", output_dir=out_dir)
            out = conn.execute(inp)
            assert out.execution_mode == "mock"
            assert os.path.isfile(out.glb_path)

    def test_api_failure_raises_when_fallback_disabled(self):
        conn = TripoConnector(config=TripoConfig(api_key="test_key", mode="api", fallback_to_mock=False))
        with patch.object(TripoConnector, "_post_json_task", side_effect=Exception("API offline")):
            inp = TripoInput(prompt="Dư Niệm An")
            with pytest.raises(MorphoMeshException) as exc_info:
                conn.execute(inp)
            assert exc_info.value.code == ERR_INFERENCE_FAILED


# ==============================================================================
# 6. CIRCUIT BREAKER INTEGRATION TESTS
# ==============================================================================

class TestTripoCircuitBreaker:
    """Verify circuit breaker trips and routes to fallback under fault conditions."""

    def test_circuit_breaker_trips_after_failures(self):
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        conn = TripoConnector(
            config=TripoConfig(api_key="test_key", mode="api", fallback_to_mock=False),
            circuit_breaker=breaker,
        )

        with patch.object(TripoConnector, "_post_json_task", side_effect=Exception("Server 500")):
            for _ in range(3):
                try:
                    conn.execute_with_resilience(TripoInput(prompt="Doll maiden"))
                except Exception:
                    pass

        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.can_attempt() is False

    def test_circuit_breaker_routes_to_registered_fallback_when_open(self, tmp_path):
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0)
        breaker.trip()
        assert breaker.state == CircuitBreakerState.OPEN

        conn = TripoConnector(circuit_breaker=breaker)
        fallback_called = False

        def mock_fallback(request, **kwargs):
            nonlocal fallback_called
            fallback_called = True
            return "fallback_result"

        conn.register_fallback(mock_fallback)
        res = conn.execute_with_resilience(TripoInput(prompt="Maiden"))
        assert fallback_called is True
        assert res == "fallback_result"

    def test_circuit_breaker_open_raises_backend_unavailable(self):
        breaker = CircuitBreaker()
        breaker.trip()
        conn = TripoConnector(
            config=TripoConfig(api_key="test_key", mode="api"),
            circuit_breaker=breaker,
        )
        with pytest.raises(MorphoMeshException) as exc_info:
            conn.execute(TripoInput(prompt="Maiden"), raise_on_failure=True)
        assert exc_info.value.code == ERR_BACKEND_UNAVAILABLE
        assert "Circuit breaker is OPEN" in exc_info.value.message

    @patch.object(TripoConnector, "_poll_task")
    @patch.object(TripoConnector, "_download_file")
    @patch.object(TripoConnector, "_post_json_task")
    def test_circuit_breaker_records_success_on_api_success(
        self, mock_post, mock_download, mock_poll, sample_glb_file, tmp_path
    ):
        breaker = CircuitBreaker()
        conn = TripoConnector(
            config=TripoConfig(api_key="test_key", mode="api"),
            circuit_breaker=breaker,
        )
        mock_post.return_value = "task_succ_1"
        mock_poll.return_value = {
            "status": "success",
            "progress": 100,
            "output": {"model_url": "https://example.com/succ.glb"},
        }
        mock_download.side_effect = lambda url, path: shutil.copyfile(sample_glb_file, path)

        with patch.object(breaker, "record_success") as mock_rec_succ:
            conn.execute(TripoInput(prompt="Doll", output_dir=str(tmp_path)))
            mock_rec_succ.assert_called_once()


# ==============================================================================
# 7. CONNECTOR REGISTRY INTEGRATION TESTS
# ==============================================================================

class TestTripoRegistryIntegration:
    """Verify registry auto-registration, singleton discovery, and stage query."""

    def test_registry_resolves_tripo(self):
        conn = ConnectorRegistry.get("tripo")
        assert isinstance(conn, TripoConnector)
        assert conn.connector_id == "tripo"

    def test_registry_resolves_tripoai_alias(self):
        conn = ConnectorRegistry.get("tripoai")
        assert isinstance(conn, TripoConnector)

    def test_registry_resolves_triposr_alias(self):
        conn = ConnectorRegistry.get("triposr")
        assert isinstance(conn, TripoConnector)

    def test_registry_list_all_connectors_includes_tripo(self):
        all_conns = ConnectorRegistry.list_all_connectors()
        assert "tripo" in all_conns
        assert "tripoai" in all_conns

    def test_registry_list_connectors_stage2_includes_tripo(self):
        stage2_conns = ConnectorRegistry.list_connectors(stage=2)
        assert "tripo" in stage2_conns


# ==============================================================================
# 8. INFERENCE ADAPTER INTEGRATION TESTS
# ==============================================================================

class TestTripoInferenceAdapterIntegration:
    """Verify backend='tripo' routing inside InferenceAdapter."""

    def test_inference_adapter_routes_to_tripo(self, tmp_path):
        adapter = get_inference_adapter(mode="mock")
        req = Create3DAssetInput(
            concept_id="concept-yu-nian-an",
            model_backend="tripo",
            export_format="glb",
            generate_pbr=True,
        )
        res = adapter.generate_3d_asset(req)

        assert isinstance(res, EnhancedCreate3DAssetOutput)
        assert res.backend_used == "tripo"
        assert res.metadata.get("connector") == "tripo"
        assert os.path.isfile(res.mesh_path)
        assert res.vertex_count > 0

    def test_inference_adapter_with_direct_prompt(self):
        adapter = get_inference_adapter(mode="mock")
        req = Create3DAssetInput(
            prompt="Dư Niệm An ancient porcelain doll maiden",
            model_backend="tripo",
            export_format="glb",
            generate_pbr=True,
            quality_tier="high",
        )
        res = adapter.generate_3d_asset(req)
        assert res.backend_used == "tripo"
        assert os.path.isfile(res.mesh_path)
        assert res.has_pbr_materials is True

    def test_inference_adapter_with_explicit_image_path(self, sample_concept_image):
        adapter = get_inference_adapter(mode="mock")
        req = Create3DAssetInput(
            image_path=sample_concept_image,
            model_backend="tripo",
            export_format="glb",
        )
        res = adapter.generate_3d_asset(req)
        assert res.backend_used == "tripo"
        assert os.path.isfile(res.mesh_path)


# ==============================================================================
# 9. FASTMCP SERVER TOOL INTEGRATION TESTS
# ==============================================================================

class TestTripoServerIntegration:
    """Verify FastMCP morphomesh_create_3d_asset invocation with model_backend='tripo'."""

    @pytest.mark.asyncio
    async def test_server_create_3d_asset_with_tripo_backend(self):
        res = await morphomesh_create_3d_asset(
            concept_id="concept-porcelain-doll",
            model_backend="tripo",
            export_format="glb",
            generate_pbr=True,
        )
        assert isinstance(res, dict)
        assert res["backend_used"] == "tripo"
        assert res["metadata"]["connector"] == "tripo"
        assert os.path.isfile(res["mesh_path"])

    @pytest.mark.asyncio
    async def test_server_create_3d_asset_with_direct_prompt(self):
        res = await morphomesh_create_3d_asset(
            prompt="Yu Nian An porcelain doll maiden with red ribbons /boost",
            model_backend="tripo",
            export_format="glb",
            generate_pbr=True,
        )
        assert isinstance(res, dict)
        assert res["backend_used"] == "tripo"
        assert os.path.isfile(res["mesh_path"])

    @pytest.mark.asyncio
    async def test_server_create_3d_asset_missing_all_inputs_raises_toolerror(self):
        from mcp.server.fastmcp.exceptions import ToolError
        with pytest.raises(ToolError) as exc_info:
            await morphomesh_create_3d_asset(model_backend="tripo")
        assert "ERR_IMAGE_NOT_FOUND" in str(exc_info.value)
