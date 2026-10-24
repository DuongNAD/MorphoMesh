"""
Adversarial Stress Test Suite - Milestone 2 Iteration 2 Challenger 1
Location: E:\\tool\\mcp\\MorphoMesh\\.agents\\m2_iter2_veg_challenger_1\\test_adversarial_m2_iter2.py

Comprehensive Adversarial Stress Testing & Empirical Verification:
1. Retry-After Capping & Anti-DoS
   - 24-hour Retry-After header (86400s) strictly clamped to default backoff_max_seconds (60.0s)
   - Custom backoff_max_seconds (e.g. 10.0s, 15.0s) strictly respected
   - Multi-attempt 429 flood: all retry attempts clamped, max_retries enforced
   - Malformed/non-numeric Retry-After strings handled gracefully without crashing
2. Fast-Fail on Non-429 4xx Client Errors
   - Required status codes: 400, 401, 403, 404, 405, 408, 409, 413, 415, 422
   - Extended edge codes: 402, 406, 410, 411, 412, 414, 418, 428, 431, 451
   - Asserts 1 HTTP attempt, 0 retries, 0 sleep calls, RuntimeError raised
   - Contrast with 5xx (500, 502, 503, 504) which MUST retry up to max_retries
3. Cache Provenance & Credential Isolation
   - Procedural asset in cache with keys stripped -> generate_plant(mode='meshy') raises RuntimeError
   - Procedural asset NEVER returned when mode='meshy' (even with valid key or missing key)
   - Missing manifest or manifest without 'source' rejected when expected_source is set
   - Valid meshy cache returned when mode='meshy' and key is provided
4. Corrupt & Malformed GLB Detection
   - 100-byte non-zero ASCII garbage file rejected as cache miss
   - 0-byte, 1-byte, 11-byte (<12 bytes) rejected as cache miss
   - Bad magic bytes (b'RIFF', b'\\x89PNG', b'PK\\x03\\x04') rejected
   - Bad glTF version (0, 1, 3) rejected
   - Truncated GLB (header length > disk file size) rejected
5. Truncated & Corrupted Manifest Handling
   - Truncated JSON mid-stream rejected as cache miss
   - 0-byte manifest rejected as cache miss
   - Malformed syntax JSON rejected as cache miss
6. Generation Mode Validation
   - Invalid modes ('invalid_xyz', '', 'MESHY', None, 123) raise ValueError
   - Valid modes ('auto', 'meshy', 'procedural') pass mode gate
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

# Ensure project imports are resolvable
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "teamwork_projects" / "vegetation_library"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vegetation_pipeline.catalog import get_catalog, PlantSpecies
from vegetation_pipeline.generator import (
    MeshyGenerator,
    MeshyGeneratorConfig,
    ProceduralBotanicalGenerator,
    RawAsset,
    generate_plant,
)


@pytest.fixture
def sample_species() -> PlantSpecies:
    cat = get_catalog()
    return cat["veg_tree_oak_01"]


@pytest.fixture
def sample_pine_species() -> PlantSpecies:
    cat = get_catalog()
    return cat["veg_conifer_pine_01"]


@pytest.fixture
def minimal_valid_glb() -> bytes:
    """Generates a minimal valid 12-byte GLB header matching glTF 2.0 binary container."""
    # 4 bytes magic (glTF), 4 bytes uint32 version (2), 4 bytes uint32 length (12)
    return struct.pack("<4sII", b"glTF", 2, 12)


def create_mock_texture_files(directory: Path, prefix: str = "") -> None:
    """Creates dummy 16x16 PNG textures for albedo, normal, roughness, metallic."""
    directory.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (16, 16), (60, 120, 60))
    for ch in ["albedo", "normal", "roughness", "metallic"]:
        filename = f"{prefix}_{ch}.png" if prefix else f"{ch}.png"
        img.save(directory / filename)


# ==============================================================================
# 1. RETRY-AFTER CAPPING & BACKOFF DoS DEFENSE TESTS
# ==============================================================================

class TestRetryAfterCapping:
    """Verifies that large or malicious Retry-After headers cannot freeze execution threads."""

    def test_retry_after_86400_clamped_to_default_60s(self):
        """
        Adversarial Test 1.1:
        Meshy API returns Retry-After: 86400 (24-hour sleep denial-of-service).
        Verify sleep delay is strictly clamped to default backoff_max_seconds (60.0s).
        """
        cfg = MeshyGeneratorConfig(api_key="msy_mock_test", max_retries=2)
        assert cfg.backoff_max_seconds == 60.0, "Default backoff_max_seconds must be 60.0s"
        gen = MeshyGenerator(config=cfg)

        sleep_recorded: list[float] = []
        err_429 = urllib.error.HTTPError(
            "https://api.meshy.ai/test",
            429,
            "Too Many Requests",
            {"Retry-After": "86400"},
            io.BytesIO(b'{"message": "Daily rate limit exceeded"}'),
        )

        calls = [0]
        def mock_urlopen(req, **kwargs):
            calls[0] += 1
            if calls[0] == 1:
                raise err_429
            resp = MagicMock()
            resp.read.return_value = json.dumps({"result": "recovered_task_id"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), \
             patch("time.sleep", side_effect=sleep_recorded.append):
            result = gen._request_with_retry("POST", "https://api.meshy.ai/test", headers={})

            assert result["result"] == "recovered_task_id"
            assert calls[0] == 2, "Must retry once and recover"
            assert len(sleep_recorded) == 1, "Must sleep exactly once for single 429"
            assert sleep_recorded[0] == 60.0, (
                f"Sleep delay must be strictly clamped to 60.0s, got {sleep_recorded[0]}"
            )

    def test_retry_after_clamped_to_custom_backoff_max(self):
        """
        Adversarial Test 1.2:
        Test with custom backoff_max_seconds=10.0 and Retry-After: 3600.
        Verify sleep delay is clamped to 10.0s.
        """
        cfg = MeshyGeneratorConfig(api_key="msy_mock_test", backoff_max_seconds=10.0, max_retries=2)
        gen = MeshyGenerator(config=cfg)

        sleep_recorded: list[float] = []
        err_429 = urllib.error.HTTPError(
            "https://api.meshy.ai/test",
            429,
            "Too Many Requests",
            {"Retry-After": "3600"},
            io.BytesIO(b'{"message": "Rate limited"}'),
        )

        calls = [0]
        def mock_urlopen(req, **kwargs):
            calls[0] += 1
            if calls[0] == 1:
                raise err_429
            resp = MagicMock()
            resp.read.return_value = json.dumps({"result": "task_custom_max"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), \
             patch("time.sleep", side_effect=sleep_recorded.append):
            result = gen._request_with_retry("POST", "https://api.meshy.ai/test", headers={})
            assert result["result"] == "task_custom_max"
            assert sleep_recorded[0] == 10.0

    def test_multi_attempt_429_flood_strictly_capped_and_exceeds_max_retries(self):
        """
        Adversarial Test 1.3:
        Repeated 429 errors with large Retry-After values across all retry attempts.
        Verify each sleep is clamped to backoff_max_seconds, and max_retries limit is enforced.
        """
        cfg = MeshyGeneratorConfig(api_key="msy_mock_test", backoff_max_seconds=25.0, max_retries=3)
        gen = MeshyGenerator(config=cfg)

        sleep_recorded: list[float] = []
        err_429 = urllib.error.HTTPError(
            "https://api.meshy.ai/test",
            429,
            "Too Many Requests",
            {"Retry-After": "999999"},
            io.BytesIO(b'{"message": "Rate limit"}'),
        )

        with patch("urllib.request.urlopen", side_effect=err_429), \
             patch("time.sleep", side_effect=sleep_recorded.append):
            with pytest.raises(RuntimeError) as exc_info:
                gen._request_with_retry("POST", "https://api.meshy.ai/test", headers={})

            assert "exceeded max retries (3)" in str(exc_info.value)
            assert len(sleep_recorded) == 3, f"Expected 3 retry sleeps, got {len(sleep_recorded)}"
            for i, s in enumerate(sleep_recorded):
                assert s == 25.0, f"Attempt {i+1} sleep was {s}, expected 25.0s"

    def test_retry_after_malformed_string_graceful_fallback(self):
        """
        Adversarial Test 1.4:
        Retry-After contains non-numeric string or invalid HTTP date.
        Verify it falls back to normal exponential backoff without crashing.
        """
        cfg = MeshyGeneratorConfig(api_key="msy_mock_test", backoff_base_seconds=2.0, max_retries=2)
        gen = MeshyGenerator(config=cfg)

        sleep_recorded: list[float] = []
        err_429 = urllib.error.HTTPError(
            "https://api.meshy.ai/test",
            429,
            "Too Many Requests",
            {"Retry-After": "invalid-non-numeric-header-data"},
            io.BytesIO(b'{"message": "Rate limited"}'),
        )

        calls = [0]
        def mock_urlopen(req, **kwargs):
            calls[0] += 1
            if calls[0] == 1:
                raise err_429
            resp = MagicMock()
            resp.read.return_value = json.dumps({"result": "task_malformed_header"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), \
             patch("time.sleep", side_effect=sleep_recorded.append):
            result = gen._request_with_retry("POST", "https://api.meshy.ai/test", headers={})
            assert result["result"] == "task_malformed_header"
            assert len(sleep_recorded) == 1
            # Base delay = 2.0 * (2^0) = 2.0 + jitter in [0, 0.5]
            assert 2.0 <= sleep_recorded[0] <= 2.5


# ==============================================================================
# 2. FAST-FAIL ON NON-429 4XX CLIENT ERRORS
# ==============================================================================

class TestFastFailOnNon429ClientErrors:
    """Verifies that all standard and edge 4xx client errors terminate immediately."""

    @pytest.mark.parametrize(
        "status_code",
        [400, 401, 403, 404, 405, 408, 409, 413, 415, 422],
    )
    def test_fast_fail_required_4xx_codes(self, status_code: int):
        """
        Adversarial Test 2.1:
        Verify HTTP 400, 401, 403, 404, 405, 408, 409, 413, 415, 422
        immediately terminate with RuntimeError on attempt 1,
        with 0 retries and 0 sleep calls.
        """
        cfg = MeshyGeneratorConfig(api_key="msy_mock_test", max_retries=5)
        gen = MeshyGenerator(config=cfg)

        mock_urlopen = MagicMock()
        mock_sleep = MagicMock()
        err = urllib.error.HTTPError(
            "https://api.meshy.ai/test",
            status_code,
            f"Client Error {status_code}",
            {},
            io.BytesIO(f'{{"error": "client_error_{status_code}"}}'.encode("utf-8")),
        )
        mock_urlopen.side_effect = err

        with patch("urllib.request.urlopen", mock_urlopen), patch("time.sleep", mock_sleep):
            with pytest.raises(RuntimeError) as exc_info:
                gen._request_with_retry("POST", "https://api.meshy.ai/test", headers={})

            err_msg = str(exc_info.value)
            assert f"Meshy API client error {status_code}" in err_msg
            assert mock_urlopen.call_count == 1, (
                f"HTTP {status_code} must NOT retry; expected exactly 1 call, got {mock_urlopen.call_count}"
            )
            mock_sleep.assert_not_called(), (
                f"HTTP {status_code} must NOT sleep; sleep was called {mock_sleep.call_count} times"
            )

    @pytest.mark.parametrize(
        "edge_code",
        [402, 406, 410, 411, 412, 414, 418, 428, 431, 451],
    )
    def test_fast_fail_extended_edge_4xx_codes(self, edge_code: int):
        """
        Adversarial Test 2.2:
        Extended edge client error codes (e.g. 402, 410, 418, 428)
        must also terminate immediately without retries or sleep.
        """
        cfg = MeshyGeneratorConfig(api_key="msy_mock_test", max_retries=5)
        gen = MeshyGenerator(config=cfg)

        mock_urlopen = MagicMock()
        mock_sleep = MagicMock()
        err = urllib.error.HTTPError(
            "https://api.meshy.ai/test",
            edge_code,
            f"Client Error {edge_code}",
            {},
            io.BytesIO(f'{{"error": "{edge_code}"}}'.encode("utf-8")),
        )
        mock_urlopen.side_effect = err

        with patch("urllib.request.urlopen", mock_urlopen), patch("time.sleep", mock_sleep):
            with pytest.raises(RuntimeError) as exc_info:
                gen._request_with_retry("POST", "https://api.meshy.ai/test", headers={})

            assert f"Meshy API client error {edge_code}" in str(exc_info.value)
            assert mock_urlopen.call_count == 1
            mock_sleep.assert_not_called()

    @pytest.mark.parametrize("server_code", [500, 502, 503, 504])
    def test_server_5xx_errors_do_retry_with_backoff(self, server_code: int):
        """
        Adversarial Test 2.3:
        In contrast to 4xx errors, transient 5xx errors MUST retry with backoff.
        """
        cfg = MeshyGeneratorConfig(api_key="msy_mock_test", backoff_base_seconds=1.0, max_retries=3)
        gen = MeshyGenerator(config=cfg)

        calls = [0]
        sleep_recorded: list[float] = []
        err_5xx = urllib.error.HTTPError(
            "https://api.meshy.ai/test",
            server_code,
            f"Server Error {server_code}",
            {},
            io.BytesIO(b'{"message": "Internal gateway failure"}'),
        )

        def mock_urlopen(req, **kwargs):
            calls[0] += 1
            if calls[0] <= 2:
                raise err_5xx
            resp = MagicMock()
            resp.read.return_value = json.dumps({"result": "recovered_5xx"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), \
             patch("time.sleep", side_effect=sleep_recorded.append):
            result = gen._request_with_retry("POST", "https://api.meshy.ai/test", headers={})
            assert result["result"] == "recovered_5xx"
            assert calls[0] == 3, f"Expected 3 calls for 5xx recovery, got {calls[0]}"
            assert len(sleep_recorded) == 2, f"Expected 2 retry sleeps, got {len(sleep_recorded)}"


# ==============================================================================
# 3. CACHE PROVENANCE & CREDENTIAL ENFORCEMENT TESTS
# ==============================================================================

class TestCacheProvenanceAndCredentialEnforcement:
    """Verifies that procedural cache assets can never masquerade as Meshy AI assets."""

    def test_mode_meshy_with_keys_stripped_rejects_procedural_cache(self, sample_species, tmp_path, minimal_valid_glb):
        """
        Adversarial Test 3.1:
        A valid procedural asset exists in cache (with GLB, textures, manifest source='procedural').
        API keys are completely stripped from environment.
        User calls generate_plant(..., mode="meshy").
        Assert: RuntimeError is raised ("MESHY_API_KEY API key environment variable is not set").
        Assert: Procedural cached asset is NEVER returned.
        """
        target_dir = tmp_path / "proc_cache_test"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Populate a complete procedural asset in target_dir
        with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
            f.write(minimal_valid_glb)
        create_mock_texture_files(target_dir / "textures")
        manifest = {
            "species_id": sample_species.species_id,
            "source": "procedural",
            "vertex_count": 5000,
            "face_count": 4800,
            "textures": {
                "albedo": "textures/albedo.png",
                "normal": "textures/normal.png",
                "roughness": "textures/roughness.png",
                "metallic": "textures/metallic.png",
            },
        }
        with open(target_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        # Strip environment variables
        env_clean = {k: v for k, v in os.environ.items() if not k.startswith("MESHY")}
        with patch.dict(os.environ, env_clean, clear=True):
            assert os.environ.get("MESHY_API_KEY") is None
            assert os.environ.get("MESHY_AI_API_KEY") is None

            with pytest.raises(RuntimeError) as exc_info:
                generate_plant(sample_species, mode="meshy", output_dir=target_dir)

            assert "MESHY_API_KEY API key environment variable is not set" in str(exc_info.value)

    def test_mode_meshy_with_key_rejects_procedural_cache_provenance(self, sample_species, tmp_path, minimal_valid_glb):
        """
        Adversarial Test 3.2:
        API key is provided, but cache on disk has source='procedural'.
        Verify check_cache(..., expected_source='meshy') rejects the procedural asset,
        and MeshyGenerator attempts live generation instead of returning procedural cache.
        """
        target_dir = tmp_path / "proc_cache_with_key"
        target_dir.mkdir(parents=True, exist_ok=True)

        with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
            f.write(minimal_valid_glb)
        create_mock_texture_files(target_dir / "textures")
        manifest = {
            "species_id": sample_species.species_id,
            "source": "procedural",
            "vertex_count": 5000,
            "face_count": 4800,
        }
        with open(target_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_valid_test_key"))
        cached = gen.check_cache(sample_species, target_dir=target_dir, expected_source="meshy")
        assert cached is None, "check_cache must reject procedural cache when expected_source='meshy'"

    def test_check_cache_rejects_manifest_without_source_tag(self, sample_species, tmp_path, minimal_valid_glb):
        """
        Adversarial Test 3.3:
        Manifest exists with valid GLB and textures, but lacks 'source' field (legacy format).
        Verify check_cache(..., expected_source='meshy') returns None (rejected).
        """
        target_dir = tmp_path / "no_source_manifest"
        target_dir.mkdir(parents=True, exist_ok=True)

        with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
            f.write(minimal_valid_glb)
        create_mock_texture_files(target_dir / "textures")
        manifest = {
            "species_id": sample_species.species_id,
            "vertex_count": 100,
            "face_count": 50,
            # 'source' omitted
        }
        with open(target_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        gen = MeshyGenerator()
        cached = gen.check_cache(sample_species, target_dir=target_dir, expected_source="meshy")
        assert cached is None, "Manifest without 'source' field must be rejected when expected_source is set"

    def test_check_cache_rejects_missing_manifest_when_expected_source_specified(
        self, sample_species, tmp_path, minimal_valid_glb
    ):
        """
        Adversarial Test 3.4:
        GLB and textures exist, but cache_manifest.json is completely absent.
        Verify check_cache(..., expected_source='meshy') returns None (rejected).
        """
        target_dir = tmp_path / "missing_manifest"
        target_dir.mkdir(parents=True, exist_ok=True)

        with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
            f.write(minimal_valid_glb)
        create_mock_texture_files(target_dir / "textures")
        # Do not create cache_manifest.json

        gen = MeshyGenerator()
        cached = gen.check_cache(sample_species, target_dir=target_dir, expected_source="meshy")
        assert cached is None, "Missing manifest must be rejected when provenance is expected"

    def test_valid_meshy_cache_returned_when_credentials_present(
        self, sample_species, tmp_path, minimal_valid_glb
    ):
        """
        Adversarial Test 3.5:
        When cache has source='meshy' and API key is present,
        generate_plant(mode='meshy') returns cached asset without network calls.
        """
        target_dir = tmp_path / "valid_meshy_cache"
        target_dir.mkdir(parents=True, exist_ok=True)

        with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
            f.write(minimal_valid_glb)
        create_mock_texture_files(target_dir / "textures")
        manifest = {
            "species_id": sample_species.species_id,
            "source": "meshy",
            "vertex_count": 24,
            "face_count": 12,
        }
        with open(target_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        mock_urlopen = MagicMock()
        with patch.dict(os.environ, {"MESHY_API_KEY": "msy_live_key"}), \
             patch("urllib.request.urlopen", mock_urlopen):
            asset = generate_plant(sample_species, mode="meshy", output_dir=target_dir)
            assert asset.source == "cached"
            assert asset.species_id == sample_species.species_id
            mock_urlopen.assert_not_called()


# ==============================================================================
# 4. CORRUPT GLB DETECTION TESTS
# ==============================================================================

class TestCorruptGlbDetection:
    """Verifies that check_cache rejects invalid, malformed, or garbage GLB files."""

    def test_corrupt_glb_100_bytes_ascii_garbage_rejected(self, sample_species, tmp_path):
        """
        Adversarial Test 4.1:
        A 100-byte non-zero ASCII garbage file named {species_id}.glb is in cache.
        Verify check_cache rejects it as a cache miss (returns None).
        """
        target_dir = tmp_path / "corrupt_ascii"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Write exactly 100 bytes of ASCII text
        garbage = b"THIS_IS_NOT_A_VALID_GLTF_BINARY_FILE_JUST_100_BYTES_OF_ASCII_GARBAGE_CHARACTERS_FOR_TESTING_PURPOSES!!"[:100]
        assert len(garbage) == 100
        with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
            f.write(garbage)

        create_mock_texture_files(target_dir / "textures")
        with open(target_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            json.dump({"species_id": sample_species.species_id, "source": "meshy"}, f)

        gen = MeshyGenerator()
        cached = gen.check_cache(sample_species, target_dir=target_dir)
        assert cached is None, "100-byte ASCII garbage file must trigger cache miss"

    def test_corrupt_glb_less_than_12_bytes(self, sample_species, tmp_path):
        """
        Adversarial Test 4.2:
        GLB file with size < 12 bytes (insufficient header).
        Verify check_cache rejects it as a cache miss.
        """
        target_dir = tmp_path / "corrupt_short"
        target_dir.mkdir(parents=True, exist_ok=True)

        with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
            f.write(b"glTF2")  # only 5 bytes

        create_mock_texture_files(target_dir / "textures")
        with open(target_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            json.dump({"species_id": sample_species.species_id, "source": "meshy"}, f)

        gen = MeshyGenerator()
        cached = gen.check_cache(sample_species, target_dir=target_dir)
        assert cached is None, "Sub-12-byte GLB must trigger cache miss"

    def test_corrupt_glb_zero_bytes(self, sample_species, tmp_path):
        """
        Adversarial Test 4.3:
        GLB file is 0 bytes.
        Verify check_cache rejects it as a cache miss.
        """
        target_dir = tmp_path / "corrupt_zero"
        target_dir.mkdir(parents=True, exist_ok=True)

        with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
            f.write(b"")

        create_mock_texture_files(target_dir / "textures")
        with open(target_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            json.dump({"species_id": sample_species.species_id, "source": "meshy"}, f)

        gen = MeshyGenerator()
        cached = gen.check_cache(sample_species, target_dir=target_dir)
        assert cached is None, "0-byte GLB must trigger cache miss"

    def test_corrupt_glb_invalid_magic_bytes(self, sample_species, tmp_path):
        """
        Adversarial Test 4.4:
        12-byte file with invalid magic bytes (b'RIFF', b'\x89PNG', b'PK\x03\x04').
        Verify check_cache rejects each one.
        """
        target_dir = tmp_path / "corrupt_magic"
        target_dir.mkdir(parents=True, exist_ok=True)
        create_mock_texture_files(target_dir / "textures")
        with open(target_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            json.dump({"species_id": sample_species.species_id, "source": "meshy"}, f)

        gen = MeshyGenerator()
        for bad_magic in [b"RIFF", b"\x89PNG", b"PK\x03\x04"]:
            fake_header = struct.pack("<4sII", bad_magic, 2, 12)
            with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
                f.write(fake_header)

            cached = gen.check_cache(sample_species, target_dir=target_dir)
            assert cached is None, f"Invalid magic {bad_magic} must trigger cache miss"

    def test_corrupt_glb_invalid_version(self, sample_species, tmp_path):
        """
        Adversarial Test 4.5:
        12-byte file with magic b'glTF' but version=0, 1, or 3.
        Verify check_cache rejects each one.
        """
        target_dir = tmp_path / "corrupt_version"
        target_dir.mkdir(parents=True, exist_ok=True)
        create_mock_texture_files(target_dir / "textures")
        with open(target_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            json.dump({"species_id": sample_species.species_id, "source": "meshy"}, f)

        gen = MeshyGenerator()
        for bad_version in [0, 1, 3]:
            fake_header = struct.pack("<4sII", b"glTF", bad_version, 12)
            with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
                f.write(fake_header)

            cached = gen.check_cache(sample_species, target_dir=target_dir)
            assert cached is None, f"Invalid glTF version {bad_version} must trigger cache miss"

    def test_corrupt_glb_truncated_total_length(self, sample_species, tmp_path):
        """
        Adversarial Test 4.6:
        GLB header specifies total_length=10000 bytes, but actual file size on disk is 12 bytes.
        Verify check_cache rejects it as truncated.
        """
        target_dir = tmp_path / "corrupt_truncated"
        target_dir.mkdir(parents=True, exist_ok=True)

        fake_header = struct.pack("<4sII", b"glTF", 2, 10000)
        with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
            f.write(fake_header)

        create_mock_texture_files(target_dir / "textures")
        with open(target_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            json.dump({"species_id": sample_species.species_id, "source": "meshy"}, f)

        gen = MeshyGenerator()
        cached = gen.check_cache(sample_species, target_dir=target_dir)
        assert cached is None, "Truncated GLB (header length > file size) must trigger cache miss"


# ==============================================================================
# 5. TRUNCATED / CORRUPT MANIFEST TESTS
# ==============================================================================

class TestTruncatedManifestHandling:
    """Verifies that truncated or invalid JSON manifests trigger safe cache misses."""

    def test_truncated_json_in_cache_manifest(self, sample_species, tmp_path, minimal_valid_glb):
        """
        Adversarial Test 5.1:
        cache_manifest.json is truncated mid-write (incomplete JSON).
        Verify check_cache logs warning and treats it as cache miss (returns None).
        """
        target_dir = tmp_path / "truncated_manifest"
        target_dir.mkdir(parents=True, exist_ok=True)

        with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
            f.write(minimal_valid_glb)
        create_mock_texture_files(target_dir / "textures")

        # Truncated JSON
        with open(target_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            f.write('{"species_id": "veg_tree_oak_01", "source": "mes')

        gen = MeshyGenerator()
        cached = gen.check_cache(sample_species, target_dir=target_dir)
        assert cached is None, "Truncated JSON in manifest must trigger cache miss"

    def test_zero_byte_cache_manifest(self, sample_species, tmp_path, minimal_valid_glb):
        """
        Adversarial Test 5.2:
        cache_manifest.json is an empty 0-byte file.
        Verify check_cache rejects it as a cache miss.
        """
        target_dir = tmp_path / "zero_manifest"
        target_dir.mkdir(parents=True, exist_ok=True)

        with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
            f.write(minimal_valid_glb)
        create_mock_texture_files(target_dir / "textures")

        with open(target_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            f.write("")

        gen = MeshyGenerator()
        cached = gen.check_cache(sample_species, target_dir=target_dir)
        assert cached is None, "0-byte JSON manifest must trigger cache miss"

    def test_syntax_corrupt_cache_manifest(self, sample_species, tmp_path, minimal_valid_glb):
        """
        Adversarial Test 5.3:
        cache_manifest.json contains invalid syntax characters (e.g. '{{{{{').
        Verify check_cache rejects it as a cache miss.
        """
        target_dir = tmp_path / "syntax_corrupt_manifest"
        target_dir.mkdir(parents=True, exist_ok=True)

        with open(target_dir / f"{sample_species.species_id}.glb", "wb") as f:
            f.write(minimal_valid_glb)
        create_mock_texture_files(target_dir / "textures")

        with open(target_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            f.write("{{{{corrupt_json_structure: true}}}}")

        gen = MeshyGenerator()
        cached = gen.check_cache(sample_species, target_dir=target_dir)
        assert cached is None, "Syntax corrupt JSON manifest must trigger cache miss"


# ==============================================================================
# 6. MODE VALIDATION TESTS
# ==============================================================================

class TestModeValidation:
    """Verifies that invalid generation modes are rejected immediately with ValueError."""

    @pytest.mark.parametrize(
        "invalid_mode",
        [
            "invalid_xyz",
            "",
            "MESHY",
            "PROCEDURAL",
            "AUTO",
            "mesh",
            "procedural_fallback",
            "random_mode",
            None,
        ],
    )
    def test_invalid_generation_modes_raise_value_error(self, sample_species, invalid_mode):
        """
        Adversarial Test 6.1:
        Passing any invalid, empty, or case-mismatched mode must raise ValueError immediately.
        """
        with pytest.raises(ValueError) as exc_info:
            generate_plant(sample_species, mode=invalid_mode)

        assert f"Invalid generation mode: '{invalid_mode}'" in str(exc_info.value)

    @pytest.mark.parametrize("valid_mode", ["auto", "meshy", "procedural"])
    def test_valid_generation_modes_accepted_at_entry_boundary(self, sample_species, valid_mode):
        """
        Adversarial Test 6.2:
        'auto', 'meshy', and 'procedural' pass the mode validation gate without ValueError.
        """
        # For 'procedural', run directly
        if valid_mode == "procedural":
            with tempfile.TemporaryDirectory() as td:
                asset = generate_plant(sample_species, mode="procedural", output_dir=td, seed=42)
                assert isinstance(asset, RawAsset)
                assert asset.source == "procedural"

        # For 'meshy', test with stripped keys -> raises RuntimeError (not ValueError!)
        elif valid_mode == "meshy":
            env_clean = {k: v for k, v in os.environ.items() if not k.startswith("MESHY")}
            with patch.dict(os.environ, env_clean, clear=True):
                with pytest.raises(RuntimeError) as exc_info:
                    generate_plant(sample_species, mode="meshy")
                assert "MESHY_API_KEY" in str(exc_info.value)

        # For 'auto', test with stripped keys -> falls back to procedural cleanly
        elif valid_mode == "auto":
            env_clean = {k: v for k, v in os.environ.items() if not k.startswith("MESHY")}
            with patch.dict(os.environ, env_clean, clear=True):
                with tempfile.TemporaryDirectory() as td:
                    asset = generate_plant(sample_species, mode="auto", output_dir=td, seed=42)
                    assert isinstance(asset, RawAsset)
                    assert asset.source == "procedural"


# ==============================================================================
# STANDALONE CLI TEST RUNNER
# ==============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING ADVERSARIAL STRESS TEST SUITE (Milestone 2 Iteration 2 Challenger 1)")
    print("=" * 80)

    import sys
    ret = pytest.main(["-v", "-s", __file__])
    sys.exit(ret)
