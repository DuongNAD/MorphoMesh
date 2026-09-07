"""
MorphoMesh: Comprehensive Test Suite for Google Gemini & Imagen 3 Image Connector.

Verifies:
  1. Configuration & Credential Resolution (GEMINI_API_KEY, GOOGLE_API_KEY, precedence, absent keys).
  2. Connector Lifecycle, Health Probes, and Dependency Auditing.
  3. 2D Anatomical Concept Art Synthesis (clean alpha extraction, prompt enrichment, deterministic seed).
  4. Character Turnaround Model Sheet Synthesis (synchronized front, side, and back view slicing).
  5. PBR Texture Map Reference Synthesis (Albedo, Normal, Roughness, Metallic suite).
  6. Multi-Mode Execution: GenAI SDK mocking, REST API HTTP response mocking, and offline procedural fallback.
  7. Circuit Breaker Fault Tolerance, state transitions, and recovery.
  8. ConnectorRegistry Integration (singleton lifecycle, aliasing, multi-stage filtering).
  9. InferenceAdapter Integration (dynamic routing via backend="gemini", turnaround & texture helpers).
  10. FastMCP Server Integration (morphomesh_generate_concept tool invocation with backend="gemini").
"""

from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error

import numpy as np
import pytest
from PIL import Image

from morphomesh.connectors import (
    CircuitBreaker,
    CircuitBreakerState,
    ConnectorRegistry,
    DependencyCheckResult,
    GeminiImageConfig,
    GeminiImageConnector,
    GeminiImageInput,
    GeminiImageOutput,
    HealthCheckResult,
    PBRTextureMaps,
)
from morphomesh.inference_adapter import (
    InferenceAdapter,
    MockInferenceAdapter,
    get_inference_adapter,
)
from morphomesh.models import (
    GenerateConceptInput,
    GenerateConceptOutput,
)
from morphomesh.server import morphomesh_generate_concept


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(autouse=True)
def reset_env_and_registry(monkeypatch):
    """Ensure environment credentials and registry singletons are clean for each test."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("MORPHOMESH_CONCEPT_BACKEND", raising=False)
    ConnectorRegistry.reset_all()
    yield
    ConnectorRegistry.reset_all()


@pytest.fixture
def mock_png_bytes() -> bytes:
    """Create a 64x64 valid PNG image as bytes for network response mocking."""
    img = Image.new("RGBA", (64, 64), (100, 150, 200, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ==============================================================================
# 1. CONFIGURATION & CREDENTIAL RESOLUTION TESTS
# ==============================================================================

class TestGeminiConfigAndAuth:
    """Verify configuration parsing and authentication key discovery."""

    def test_default_config(self):
        cfg = GeminiImageConfig()
        assert cfg.model_name == "imagen-3.0-generate-002"
        assert cfg.mode == "auto"
        assert cfg.timeout_seconds == 60.0
        assert cfg.aspect_ratio == "1:1"
        assert cfg.api_key is None

    def test_api_key_from_gemini_env(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key-12345")
        conn = GeminiImageConnector()
        assert conn._resolve_api_key() == "test-gemini-key-12345"

    def test_api_key_from_google_env(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key-67890")
        conn = GeminiImageConnector()
        assert conn._resolve_api_key() == "test-google-key-67890"

    def test_key_precedence_config_over_env(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        monkeypatch.setenv("GOOGLE_API_KEY", "fallback-env-key")
        cfg = GeminiImageConfig(api_key="explicit-config-key")
        conn = GeminiImageConnector(config=cfg)
        assert conn._resolve_api_key() == "explicit-config-key"

    def test_key_precedence_gemini_over_google(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "primary-gemini-key")
        monkeypatch.setenv("GOOGLE_API_KEY", "secondary-google-key")
        conn = GeminiImageConnector()
        assert conn._resolve_api_key() == "primary-gemini-key"

    def test_no_keys_operates_gracefully(self):
        conn = GeminiImageConnector()
        assert conn._resolve_api_key() is None
        assert conn.initialize() is True
        assert conn.is_initialized is True

    def test_whitespace_api_key_treated_as_none(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "   \t  \n ")
        conn = GeminiImageConnector()
        assert conn._resolve_api_key() is None
        health = conn.health_check()
        assert health.status == "degraded"
        assert health.details["api_key_configured"] is False


# ==============================================================================
# 2. CONNECTOR LIFECYCLE & DIAGNOSTICS TESTS
# ==============================================================================

class TestGeminiConnectorLifecycle:
    """Verify health check diagnostics, dependency auditing, and resource cleanup."""

    def test_health_check_without_api_key(self):
        conn = GeminiImageConnector()
        conn.initialize()
        health = conn.health_check()

        assert isinstance(health, HealthCheckResult)
        assert health.status == "degraded"
        assert health.dependencies_met is True
        assert "mock" in health.message.lower()
        assert health.details["api_key_configured"] is False

    def test_health_check_with_api_key(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "valid-fake-key")
        conn = GeminiImageConnector()
        conn.initialize()
        health = conn.health_check()

        assert isinstance(health, HealthCheckResult)
        assert health.status == "healthy"
        assert health.dependencies_met is True
        assert health.details["api_key_configured"] is True

    def test_check_dependencies_always_satisfied(self):
        conn = GeminiImageConnector()
        dep = conn.check_dependencies()

        assert isinstance(dep, DependencyCheckResult)
        assert dep.satisfied is True
        assert dep.hardware_supported is True
        assert "has_pillow" in dep.details

    def test_is_available_always_true(self):
        conn = GeminiImageConnector()
        # Even without key (status='degraded'), connector is available due to zero-VRAM mock fallback
        assert conn.is_available() is True

    def test_close_resets_state(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "key")
        conn = GeminiImageConnector()
        conn.initialize()
        assert conn.is_initialized is True
        conn.close()
        assert conn.is_initialized is False
        assert conn._sdk_client is None


# ==============================================================================
# 3. 2D ANATOMICAL CONCEPT ART SYNTHESIS TESTS
# ==============================================================================

class TestGeminiConceptSynthesis:
    """Verify 2D concept generation, alpha mask isolation, and prompt augmentation."""

    def test_generate_concept_mock_basic(self, tmp_path: Path):
        conn = GeminiImageConnector()
        inp = GeminiImageInput(
            prompt="Shadow Stalker chimera with venomous tail",
            creature_type="quadruped",
            pose="standing_neutral",
            style="realistic",
            background="white_neutral",
            width=512,
            height=512,
            output_dir=str(tmp_path),
        )

        out = conn.execute(inp)

        assert isinstance(out, GeminiImageOutput)
        assert out.asset_id.startswith("gemini-")
        assert os.path.isfile(out.image_path)
        assert out.rgba_image_path is not None
        assert os.path.isfile(out.rgba_image_path)
        assert out.execution_mode == "mock"
        assert out.task_type == "concept"

        # Validate RGB primary image
        with Image.open(out.image_path) as img:
            assert img.size == (512, 512)
            assert img.format == "PNG"

        # Validate RGBA segmented image
        with Image.open(out.rgba_image_path) as rgba:
            assert rgba.size == (512, 512)
            assert rgba.mode == "RGBA"
            alpha_chan = np.array(rgba)[:, :, 3]
            # Ensure there is both foreground (opaque) and background (transparent)
            assert np.any(alpha_chan > 200)
            assert np.any(alpha_chan < 50)

    def test_deterministic_seed_concept(self, tmp_path: Path):
        conn = GeminiImageConnector()
        inp1 = GeminiImageInput(
            prompt="Gargoyle guardian",
            seed=4242,
            width=256,
            height=256,
            output_dir=str(tmp_path / "run1"),
        )
        inp2 = GeminiImageInput(
            prompt="Gargoyle guardian",
            seed=4242,
            width=256,
            height=256,
            output_dir=str(tmp_path / "run2"),
        )

        out1 = conn.execute(inp1)
        out2 = conn.execute(inp2)

        arr1 = np.array(Image.open(out1.image_path))
        arr2 = np.array(Image.open(out2.image_path))
        np.testing.assert_array_equal(arr1, arr2)

    @pytest.mark.parametrize("creature_type", ["quadruped", "biped", "winged", "custom"])
    def test_creature_archetype_prompts(self, tmp_path: Path, creature_type: str):
        conn = GeminiImageConnector()
        inp = GeminiImageInput(
            prompt=f"A mythological {creature_type}",
            creature_type=creature_type,
            output_dir=str(tmp_path),
        )
        out = conn.execute(inp)
        assert creature_type in out.prompt_enhanced.lower()
        assert "concept art" in out.prompt_enhanced.lower()
        assert os.path.isfile(out.image_path)

    def test_empty_or_whitespace_prompt_rejected(self):
        with pytest.raises(Exception):
            GeminiImageInput(prompt="   \n \t ")

    def test_aspect_ratio_normalization(self):
        inp_wide = GeminiImageInput(prompt="test", aspect_ratio="16:9")
        assert inp_wide.aspect_ratio == "16:9"
        inp_alias = GeminiImageInput(prompt="test", aspect_ratio="landscape")
        assert inp_alias.aspect_ratio == "16:9"
        inp_invalid = GeminiImageInput(prompt="test", aspect_ratio="unknown_ratio")
        assert inp_invalid.aspect_ratio == "1:1"

    def test_execute_string_with_task_type_kwargs(self, tmp_path: Path):
        conn = GeminiImageConnector()
        out = conn.execute("Chimera beast", task_type="turnaround", output_dir=str(tmp_path))
        assert out.task_type == "turnaround"
        assert "front" in out.views
        assert os.path.isfile(out.views["front"])

    def test_input_kwargs_override(self, tmp_path: Path):
        conn = GeminiImageConnector()
        inp = GeminiImageInput(prompt="Original prompt", width=512, height=512)
        out = conn.execute(inp, output_dir=str(tmp_path))
        assert Path(out.image_path).parent == tmp_path


# ==============================================================================
# 4. CHARACTER TURNAROUND MODEL SHEET SYNTHESIS TESTS
# ==============================================================================

class TestGeminiTurnaroundSheetSynthesis:
    """Verify synchronized orthographic front, side, and back view generation and slicing."""

    def test_generate_turnaround_sheet_mock(self, tmp_path: Path):
        conn = GeminiImageConnector()
        inp = GeminiImageInput(
            prompt="Forest Troll warrior",
            task_type="turnaround",
            view_mode="turnaround_sheet",
            creature_type="biped",
            pose="neutral_a_pose",
            width=768,
            height=512,
            output_dir=str(tmp_path),
        )

        out = conn.execute(inp)

        assert isinstance(out, GeminiImageOutput)
        assert out.task_type == "turnaround"
        assert "turnaround_sheet" in out.views
        assert "front" in out.views
        assert "side" in out.views
        assert "back" in out.views

        # Verify full turnaround sheet
        assert os.path.isfile(out.views["turnaround_sheet"])

        # Verify individual view crops exist and are valid images
        for view_name in ("front", "side", "back"):
            crop_path = out.views[view_name]
            assert os.path.isfile(crop_path)
            with Image.open(crop_path) as c_img:
                assert c_img.format == "PNG"
                assert c_img.height == 512
                assert c_img.width > 0

            # Verify corresponding RGBA alpha crop
            rgba_crop_key = f"{view_name}_rgba"
            assert rgba_crop_key in out.views
            assert os.path.isfile(out.views[rgba_crop_key])
            with Image.open(out.views[rgba_crop_key]) as c_rgba:
                assert c_rgba.mode == "RGBA"

    def test_turnaround_prompt_enrichment(self):
        conn = GeminiImageConnector()
        inp = GeminiImageInput(
            prompt="Cerberus three-headed dog",
            task_type="turnaround",
            creature_type="quadruped",
        )
        prompt = conn._build_enhanced_prompt(inp)

        assert "turnaround model sheet" in prompt.lower()
        assert "front view" in prompt.lower()
        assert "side profile view" in prompt.lower()
        assert "back view" in prompt.lower()
        assert "orthographic" in prompt.lower()


# ==============================================================================
# 5. PBR TEXTURE MAP REFERENCE SYNTHESIS TESTS
# ==============================================================================

class TestGeminiPBRTextureSynthesis:
    """Verify decoupled Albedo, Normal, Roughness, and Metallic texture map synthesis."""

    def test_generate_pbr_textures_mock(self, tmp_path: Path):
        conn = GeminiImageConnector()
        inp = GeminiImageInput(
            prompt="Reptilian dragon scales",
            task_type="texture",
            texture_type="scales",
            width=512,
            height=512,
            output_dir=str(tmp_path),
        )

        out = conn.execute(inp)

        assert out.task_type == "texture"
        assert out.pbr_textures is not None
        pbr: PBRTextureMaps = out.pbr_textures

        # Check Albedo Map
        assert pbr.albedo_path is not None and os.path.isfile(pbr.albedo_path)
        with Image.open(pbr.albedo_path) as alb:
            assert alb.size == (512, 512)

        # Check Tangent Normal Map
        assert pbr.normal_path is not None and os.path.isfile(pbr.normal_path)
        with Image.open(pbr.normal_path) as nrm:
            assert nrm.size == (512, 512)
            # Tangent normals typically have high Z (blue channel >= 128)
            arr = np.array(nrm)
            assert np.mean(arr[:, :, 2]) > 120

        # Check Roughness Map
        assert pbr.roughness_path is not None and os.path.isfile(pbr.roughness_path)
        with Image.open(pbr.roughness_path) as rgh:
            assert rgh.size == (512, 512)
            assert rgh.mode == "L"

        # Check Metallic Map
        assert pbr.metallic_path is not None and os.path.isfile(pbr.metallic_path)
        with Image.open(pbr.metallic_path) as met:
            assert met.size == (512, 512)
            assert met.mode == "L"


# ==============================================================================
# 6. SDK & REST EXECUTION PATHS (NETWORK MOCKING)
# ==============================================================================

class TestSDKAndRESTExecutionPaths:
    """Verify live SDK and REST execution paths via clean network mocking."""

    def test_generate_via_sdk_mocked(self, monkeypatch, tmp_path: Path, mock_png_bytes: bytes):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-api-key")

        # Mock GenAI SDK client
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_image_item = MagicMock()
        mock_image_item.image.image_bytes = mock_png_bytes
        mock_resp.generated_images = [mock_image_item]
        mock_client.models.generate_images.return_value = mock_resp

        with patch("morphomesh.connectors.gemini_image_connector._HAS_GOOGLE_GENAI", True), \
             patch("morphomesh.connectors.gemini_image_connector.genai") as mock_genai_mod:
            mock_genai_mod.Client.return_value = mock_client

            conn = GeminiImageConnector(config=GeminiImageConfig(mode="sdk"))
            conn.initialize()

            inp = GeminiImageInput(prompt="Cybernetic panther", output_dir=str(tmp_path))
            out = conn.execute(inp)

            assert out.execution_mode == "sdk"
            assert os.path.isfile(out.image_path)
            assert mock_client.models.generate_images.called

    def test_generate_via_rest_mocked(self, monkeypatch, tmp_path: Path, mock_png_bytes: bytes):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-api-key")

        # Prepare base64 encoded response matching Google AI REST Imagen 3 format
        b64_str = base64.b64encode(mock_png_bytes).decode("utf-8")
        json_resp = json.dumps({"predictions": [{"bytesBase64Encoded": b64_str}]}).encode("utf-8")

        mock_http_response = MagicMock()
        mock_http_response.read.return_value = json_resp
        mock_http_response.__enter__.return_value = mock_http_response

        with patch("urllib.request.urlopen", return_value=mock_http_response):
            conn = GeminiImageConnector(config=GeminiImageConfig(mode="rest"))
            conn.initialize()

            inp = GeminiImageInput(prompt="Steampunk owl", output_dir=str(tmp_path))
            out = conn.execute(inp)

            assert out.execution_mode == "rest"
            assert os.path.isfile(out.image_path)

    def test_rest_network_failure_falls_back_to_mock(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-api-key")

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            breaker = CircuitBreaker(failure_threshold=2)
            conn = GeminiImageConnector(
                config=GeminiImageConfig(mode="rest"),
                circuit_breaker=breaker,
            )
            conn.initialize()

            inp = GeminiImageInput(prompt="Gryphon rider", output_dir=str(tmp_path))
            out = conn.execute(inp)

            # Execution gracefully falls back to mock procedural synthesis without raising
            assert out.execution_mode == "mock"
            assert os.path.isfile(out.image_path)
            assert breaker.failure_count == 1

    def test_sdk_image_bytes_string_base64_decoding(self, monkeypatch, tmp_path: Path, mock_png_bytes: bytes):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-api-key")
        b64_str = base64.b64encode(mock_png_bytes).decode("utf-8")

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_image_item = MagicMock()
        mock_image_item.image.image_bytes = b64_str  # String base64 instead of raw bytes
        mock_resp.generated_images = [mock_image_item]
        mock_client.models.generate_images.return_value = mock_resp

        with patch("morphomesh.connectors.gemini_image_connector._HAS_GOOGLE_GENAI", True), \
             patch("morphomesh.connectors.gemini_image_connector.genai") as mock_genai_mod:
            mock_genai_mod.Client.return_value = mock_client

            conn = GeminiImageConnector(config=GeminiImageConfig(mode="sdk"))
            conn.initialize()

            inp = GeminiImageInput(prompt="Neon dragon", output_dir=str(tmp_path))
            out = conn.execute(inp)

            assert out.execution_mode == "sdk"
            assert os.path.isfile(out.image_path)

    def test_rest_http_error_includes_response_body(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-api-key")

        error_json = json.dumps({"error": {"code": 429, "message": "Resource has been exhausted (e.g. check quota)."}}).encode("utf-8")
        fp = io.BytesIO(error_json)
        http_err = urllib.error.HTTPError("http://api", 429, "Too Many Requests", {}, fp)

        with patch("urllib.request.urlopen", side_effect=http_err):
            conn = GeminiImageConnector(config=GeminiImageConfig(mode="rest", fallback_to_mock=False))
            conn.initialize()

            inp = GeminiImageInput(prompt="Exhausted quota creature", output_dir=str(tmp_path))
            with pytest.raises(Exception) as exc_info:
                conn.execute(inp)
            assert "429" in str(exc_info.value)
            assert "Resource has been exhausted" in str(exc_info.value)


# ==============================================================================
# 7. CIRCUIT BREAKER FAULT TOLERANCE TESTS
# ==============================================================================

class TestGeminiCircuitBreaker:
    """Verify circuit breaker transitions and failure protection."""

    def test_circuit_trips_to_open_after_threshold(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-api-key")

        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("http://err", 500, "Server Error", {}, None)):
            breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=30.0)
            conn = GeminiImageConnector(
                config=GeminiImageConfig(mode="rest"),
                circuit_breaker=breaker,
            )

            inp = GeminiImageInput(prompt="Wyvern", output_dir=str(tmp_path))

            # Call 1: failure recorded
            out1 = conn.execute(inp)
            assert out1.execution_mode == "mock"
            assert breaker.state == CircuitBreakerState.CLOSED

            # Call 2: failure reaches threshold -> state OPEN
            out2 = conn.execute(inp)
            assert out2.execution_mode == "mock"
            assert breaker.state == CircuitBreakerState.OPEN

            # Call 3: circuit is OPEN -> network attempt skipped immediately
            assert breaker.can_attempt() is False
            out3 = conn.execute(inp)
            assert out3.execution_mode == "mock"

    def test_circuit_trips_via_execute_with_resilience(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-api-key")

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network unreachable")):
            breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=30.0)
            conn = GeminiImageConnector(
                config=GeminiImageConfig(mode="rest"),
                circuit_breaker=breaker,
            )

            inp = GeminiImageInput(prompt="Phoenix bird", output_dir=str(tmp_path))

            # Invocation 1 through execute_with_resilience
            out1 = conn.execute_with_resilience(inp)
            assert out1.execution_mode == "mock"
            assert breaker.failure_count == 1
            assert breaker.state == CircuitBreakerState.CLOSED

            # Invocation 2: trips breaker to OPEN
            out2 = conn.execute_with_resilience(inp)
            assert out2.execution_mode == "mock"
            assert breaker.failure_count == 2
            assert breaker.state == CircuitBreakerState.OPEN

            # Invocation 3: fast route to fallback without network attempt
            assert breaker.can_attempt() is False
            out3 = conn.execute_with_resilience(inp)
            assert out3.execution_mode == "mock"

    def test_execute_with_fallback_invokes_custom_fallback(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-api-key")

        fallback_called = False
        def custom_fallback(*args, **kwargs):
            nonlocal fallback_called
            fallback_called = True
            return "custom_fallback_output"

        with patch("morphomesh.connectors.gemini_image_connector._HAS_GOOGLE_GENAI", False), \
             patch("urllib.request.urlopen", side_effect=urllib.error.URLError("DNS resolution error")):
            res = ConnectorRegistry.execute_with_fallback(
                "gemini_image",
                custom_fallback,
                GeminiImageInput(prompt="Abyssal serpent", output_dir=str(tmp_path)),
            )

            assert fallback_called is True
            assert res == "custom_fallback_output"

    def test_fallback_to_mock_false_raises_exception(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-api-key")

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            conn = GeminiImageConnector(config=GeminiImageConfig(mode="rest", fallback_to_mock=False))
            with pytest.raises(Exception) as exc_info:
                conn.execute(GeminiImageInput(prompt="Strict test", output_dir=str(tmp_path)))
            assert "Google Gemini image generation failed" in str(exc_info.value)


# ==============================================================================
# 8. CONNECTOR REGISTRY INTEGRATION TESTS
# ==============================================================================

class TestRegistryIntegration:
    """Verify registration, singleton instantiation, and multi-stage listing in ConnectorRegistry."""

    def test_get_gemini_image_singleton(self):
        c1 = ConnectorRegistry.get("gemini_image")
        c2 = ConnectorRegistry.get("gemini_image")
        assert c1 is c2
        assert isinstance(c1, GeminiImageConnector)
        assert c1.connector_id == "gemini_image"
        assert c1.stage == 1

    def test_get_gemini_alias_resolves_same_class(self):
        c_alias = ConnectorRegistry.get("gemini")
        assert isinstance(c_alias, GeminiImageConnector)

    def test_canonical_list_connectors_preserved(self):
        # Existing tests require list_connectors() to return the 5 canonical 3D connectors
        connectors = ConnectorRegistry.list_connectors()
        expected = ["animals3d", "anycreature", "hunyuan", "meshanything", "trellis"]
        assert sorted(connectors) == expected

    def test_list_connectors_stage_filtering(self):
        # Stage 1: Gemini Image Connector
        stage1_connectors = ConnectorRegistry.list_connectors(stage=1)
        assert "gemini_image" in stage1_connectors
        assert "gemini" in stage1_connectors

    def test_list_all_connectors_includes_gemini(self):
        all_conns = ConnectorRegistry.list_all_connectors()
        assert "gemini_image" in all_conns
        assert "trellis" in all_conns
        assert "hunyuan" in all_conns


# ==============================================================================
# 9. INFERENCE ADAPTER INTEGRATION TESTS
# ==============================================================================

class TestInferenceAdapterIntegration:
    """Verify dynamic routing in InferenceAdapter using backend='gemini'."""

    def test_generate_concept_backend_gemini(self):
        adapter = get_inference_adapter(mode="mock")
        req = GenerateConceptInput(
            prompt="Frost Giant warrior with ice axe",
            creature_type="biped",
            backend="gemini",
        )

        res = adapter.generate_concept(req)

        assert isinstance(res, GenerateConceptOutput)
        assert res.concept_id.startswith("gemini-")
        assert os.path.isfile(res.image_path)
        assert res.rgba_image_path is not None and os.path.isfile(res.rgba_image_path)
        assert res.backend_used == "gemini"
        assert res.status in ("success", "mock_success")

    def test_generate_concept_backend_default_mock(self):
        adapter = get_inference_adapter(mode="mock")
        req = GenerateConceptInput(
            prompt="Cave Bear",
            creature_type="quadruped",
            backend="default",
        )

        res = adapter.generate_concept(req)

        assert res.concept_id.startswith("concept-")
        assert res.backend_used == "mock"
        assert res.status == "mock_success"

    def test_concept_backend_env_var_override(self, monkeypatch):
        monkeypatch.setenv("MORPHOMESH_CONCEPT_BACKEND", "gemini")
        adapter = get_inference_adapter(mode="mock")
        req = GenerateConceptInput(
            prompt="Thunderbird mythical avian",
            creature_type="winged",
            backend="default",
        )
        res = adapter.generate_concept(req)
        assert res.concept_id.startswith("gemini-")
        assert res.backend_used == "gemini"

    def test_adapter_generate_turnaround_sheet(self):
        adapter = InferenceAdapter()
        res = adapter.generate_turnaround_sheet(
            prompt="Centaur archer",
            creature_type="quadruped",
            width=512,
            height=512,
        )

        assert res["task_type"] == "turnaround"
        assert "turnaround_sheet" in res["views"]
        assert "front" in res["views"]
        assert "side" in res["views"]
        assert "back" in res["views"]

    def test_adapter_synthesize_textures_with_gemini(self):
        adapter = InferenceAdapter()
        res = adapter.synthesize_textures_with_gemini(
            prompt="Dragon chitin carapace",
            texture_resolution=256,
        )

        assert res["task_type"] == "texture"
        assert res["pbr_textures"] is not None
        assert "albedo_path" in res["pbr_textures"]
        assert "normal_path" in res["pbr_textures"]


# ==============================================================================
# 10. FASTMCP SERVER TOOL INTEGRATION TESTS
# ==============================================================================

class TestFastMCPServerToolIntegration:
    """Verify morphomesh_generate_concept tool execution with backend='gemini'."""

    @pytest.mark.asyncio
    async def test_morphomesh_generate_concept_gemini_backend(self):
        result = await morphomesh_generate_concept(
            prompt="Hydra nine-headed serpent",
            creature_type="serpentine",
            backend="gemini",
            width=512,
            height=512,
        )

        assert isinstance(result, dict)
        assert "concept_id" in result
        assert result["concept_id"].startswith("gemini-")
        assert os.path.isfile(result["image_path"])
        assert os.path.isfile(result["rgba_image_path"])
        assert result["backend_used"] == "gemini"

    @pytest.mark.asyncio
    async def test_morphomesh_generate_concept_turnaround_mode(self):
        result = await morphomesh_generate_concept(
            prompt="Gorgon medusa",
            view_mode="turnaround_sheet",
            backend="gemini",
            width=512,
            height=512,
        )

        assert isinstance(result, dict)
        assert "views" in result
        assert "turnaround_sheet" in result["views"]
        assert "front" in result["views"]
        assert "side" in result["views"]
        assert "back" in result["views"]
