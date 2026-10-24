"""
Adversarial Stress Test Suite for Milestone 2: Generation Engine & Fallback Harness
File: .agents/m2_veg_challenger_1/test_adversarial_generator.py

Empirical Challenger 1 Test Suite targeting:
1. Exponential backoff & jitter calculations under synthetic 429 floods and transient 500/502/503/504 errors.
2. Retry-After header parsing (float, integer, invalid strings, past timestamps, HTTP dates, DoS values).
3. Terminal 4xx client errors (400, 401, 403, 404, 422) fast-fail, plus unhandled 4xx (405, 409, 413, 415).
4. Cache integrity: 0-byte GLBs, corrupt GLB binaries, missing texture channels, truncated manifests, cross-engine cache pollution.
5. Master dispatch (generate_plant): invalid species identifiers, unhandled modes, ignored kwargs, concurrent duplicate calls, fallback harness.
"""
from __future__ import annotations

import concurrent.futures
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import urllib.error

import numpy as np
from PIL import Image
import pytest

# Ensure vegetation_library is importable
repo_root = Path(__file__).resolve().parents[2]
veg_lib_path = repo_root / "teamwork_projects" / "vegetation_library"
if str(veg_lib_path) not in sys.path:
    sys.path.insert(0, str(veg_lib_path))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from morphomesh.geometry.mesh import MeshGeometry
from vegetation_pipeline.catalog import PlantSpecies, get_catalog
from vegetation_pipeline.generator import (
    MeshyGenerator,
    MeshyGeneratorConfig,
    ProceduralBotanicalGenerator,
    ProceduralGeneratorConfig,
    RawAsset,
    generate_plant,
    unpack_glb_header_and_json,
)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def oak_species():
    cat = get_catalog()
    return cat["veg_tree_oak_01"]


@pytest.fixture
def minimal_glb_binary(tmp_path) -> bytes:
    geom = MeshGeometry()
    geom.add_box((0.0, 0.0, 0.5), (1.0, 1.0, 1.0))
    p = tmp_path / "mock.glb"
    geom.export_glb(str(p))
    with open(p, "rb") as f:
        return f.read()


# ==============================================================================
# SUITE 1: EXPONENTIAL BACKOFF & JITTER CALCULATIONS (429 & 5XX FLOODS)
# ==============================================================================

class TestAdversarialBackoffAndJitter:
    """Stress tests exponential backoff mathematical correctness, limits, and jitter."""

    def test_backoff_progression_and_jitter_bounds_under_429_flood(self):
        """
        Verify that under repeated 429 rate limit errors:
        1. base_delay = base * 2^(attempt-1)
        2. jitter is strictly in [0.0, 0.5]
        3. delay is capped at backoff_max_seconds
        4. sleep is called exactly max_retries times before raising RuntimeError
        """
        base = 1.5
        max_sec = 10.0
        max_retries = 5
        cfg = MeshyGeneratorConfig(
            api_key="msy_test",
            backoff_base_seconds=base,
            backoff_max_seconds=max_sec,
            max_retries=max_retries,
        )
        gen = MeshyGenerator(config=cfg)

        sleep_calls: List[float] = []
        calls_count = [0]

        err_429 = urllib.error.HTTPError(
            "https://api.meshy.ai", 429, "Too Many Requests",
            {}, io.BytesIO(b'{"message": "Rate limit exceeded"}')
        )

        def mock_urlopen(req, **kwargs):
            calls_count[0] += 1
            raise err_429

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), \
             patch("time.sleep", side_effect=sleep_calls.append):
            with pytest.raises(RuntimeError) as exc_info:
                gen._request_with_retry("POST", "https://api.meshy.ai/test", headers={})

            assert "exceeded max retries" in str(exc_info.value).lower()
            assert "429" in str(exc_info.value)

        # 1 initial call + 5 retries = 6 calls
        assert calls_count[0] == max_retries + 1
        assert len(sleep_calls) == max_retries

        # Verify exponential progression:
        # attempt 1: 1.5 * 2^0 = 1.5 + jitter in [0, 0.5] -> [1.5, 2.0]
        # attempt 2: 1.5 * 2^1 = 3.0 + jitter -> [3.0, 3.5]
        # attempt 3: 1.5 * 2^2 = 6.0 + jitter -> [6.0, 6.5]
        # attempt 4: 1.5 * 2^3 = 12.0 + jitter -> capped at 10.0
        # attempt 5: 1.5 * 2^4 = 24.0 + jitter -> capped at 10.0
        assert 1.5 <= sleep_calls[0] <= 2.05
        assert 3.0 <= sleep_calls[1] <= 3.55
        assert 6.0 <= sleep_calls[2] <= 6.55
        assert sleep_calls[3] == 10.0  # Capped at max_seconds
        assert sleep_calls[4] == 10.0  # Capped at max_seconds

    def test_heterogeneous_5xx_cascade_recovery(self):
        """
        Server returns sequence of 500 -> 502 -> 503 -> 504 and then succeeds on 5th attempt.
        Verify that all heterogeneous 5xx errors are caught and retried.
        """
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", max_retries=5))
        status_codes = [500, 502, 503, 504]
        sleep_calls: List[float] = []
        call_idx = [0]

        def mock_urlopen(req, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx < len(status_codes):
                code = status_codes[idx]
                raise urllib.error.HTTPError(
                    "https://api.meshy.ai", code, f"Server Error {code}",
                    {}, io.BytesIO(f'{{"error": "{code}"}}'.encode("utf-8"))
                )
            # 5th attempt succeeds
            resp = MagicMock()
            resp.read.return_value = json.dumps({"result": "recovery_ok"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), \
             patch("time.sleep", side_effect=sleep_calls.append):
            res = gen._request_with_retry("GET", "https://api.meshy.ai/test", headers={})
            assert res["result"] == "recovery_ok"
            assert call_idx[0] == 5
            assert len(sleep_calls) == 4

    def test_transient_network_errors_retry_and_backoff(self):
        """
        Verify network-level errors (URLError, TimeoutError, OSError) trigger exponential backoff.
        """
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", max_retries=3, backoff_base_seconds=1.0))
        sleep_calls: List[float] = []
        network_errors = [
            urllib.error.URLError("Connection reset by peer"),
            TimeoutError("Socket read timed out"),
            OSError("Network is unreachable"),
        ]
        call_idx = [0]

        def mock_urlopen(req, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1
            if idx < len(network_errors):
                raise network_errors[idx]
            resp = MagicMock()
            resp.read.return_value = json.dumps({"result": "network_recovered"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), \
             patch("time.sleep", side_effect=sleep_calls.append):
            res = gen._request_with_retry("GET", "https://api.meshy.ai/test", headers={})
            assert res["result"] == "network_recovered"
            assert len(sleep_calls) == 3
            assert sleep_calls[0] == 1.0
            assert sleep_calls[1] == 2.0
            assert sleep_calls[2] == 4.0


# ==============================================================================
# SUITE 2: RETRY-AFTER HEADER PARSING & EDGE CASES
# ==============================================================================

class TestAdversarialRetryAfterHeader:
    """Adversarial stress testing of HTTP Retry-After header parsing."""

    @pytest.mark.parametrize(
        "retry_header_value,expected_min_sleep",
        [
            ("4.75", 4.75),        # Float seconds
            ("30", 30.0),          # Integer seconds
            ("0.1", 2.0),          # Small float: overridden by base_delay (2.0)
            ("-15.0", 2.0),        # Negative float: overridden by base_delay
            ("-5", 2.0),           # Negative integer: overridden by base_delay
        ],
    )
    def test_retry_after_numeric_values(self, retry_header_value, expected_min_sleep):
        """Tests float, integer, and negative Retry-After headers."""
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", backoff_base_seconds=2.0))
        sleep_calls: List[float] = []
        calls = [0]

        err_429 = urllib.error.HTTPError(
            "https://api.meshy.ai", 429, "Too Many Requests",
            {"Retry-After": retry_header_value}, io.BytesIO(b'{"msg": "limit"}')
        )

        def mock_urlopen(req, **kwargs):
            calls[0] += 1
            if calls[0] == 1:
                raise err_429
            resp = MagicMock()
            resp.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), \
             patch("time.sleep", side_effect=sleep_calls.append):
            res = gen._request_with_retry("GET", "https://api.meshy.ai/test", headers={})
            assert res["status"] == "ok"
            assert len(sleep_calls) == 1
            assert sleep_calls[0] >= expected_min_sleep

    @pytest.mark.parametrize(
        "invalid_header",
        [
            "invalid_non_numeric_string",
            "Wed, 21 Oct 2025 07:28:00 GMT",  # RFC HTTP-date format
            "",
            "   ",
            "NaN",
            "Infinity",
        ],
    )
    def test_retry_after_invalid_and_http_date_strings_graceful_fallback(self, invalid_header):
        """
        RFC 7231 specifies Retry-After can be an HTTP-date.
        If float(header) fails (or produces inf/nan), verify code does not crash
        and falls back to standard exponential backoff.
        """
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", backoff_base_seconds=2.0))
        sleep_calls: List[float] = []
        calls = [0]

        err_429 = urllib.error.HTTPError(
            "https://api.meshy.ai", 429, "Too Many Requests",
            {"Retry-After": invalid_header}, io.BytesIO(b'{"msg": "limit"}')
        )

        def mock_urlopen(req, **kwargs):
            calls[0] += 1
            if calls[0] == 1:
                raise err_429
            resp = MagicMock()
            resp.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), \
             patch("time.sleep", side_effect=sleep_calls.append):
            res = gen._request_with_retry("GET", "https://api.meshy.ai/test", headers={})
            assert res["status"] == "ok"
            assert len(sleep_calls) == 1
            # Must have slept between base_delay (2.0) and base_delay + 0.5 (2.5) or infinity
            if invalid_header != "Infinity":
                assert 2.0 <= sleep_calls[0] <= 2.55

    def test_retry_after_dos_vulnerability_bypasses_max_seconds(self):
        """
        FINDING / ADVERSARIAL DISCOVERY:
        Line 265-266 in generator.py:
            delay = min(self.config.backoff_max_seconds, base_delay + jitter)
            if retry_after is not None:
                delay = max(delay, retry_after)
        If server sends `Retry-After: 999999`, `delay` becomes 999,999s,
        completely ignoring backoff_max_seconds (default 60s)!
        This test empirically verifies whether generator.py honors backoff_max_seconds
        or allows a malicious/buggy server header to freeze execution for days.
        """
        cfg = MeshyGeneratorConfig(
            api_key="msy_test",
            backoff_max_seconds=60.0,
        )
        gen = MeshyGenerator(config=cfg)
        sleep_calls: List[float] = []
        calls = [0]

        err_429 = urllib.error.HTTPError(
            "https://api.meshy.ai", 429, "Too Many Requests",
            {"Retry-After": "86400.0"},  # 24 hours
            io.BytesIO(b'{"msg": "Blocked for 24h"}')
        )

        def mock_urlopen(req, **kwargs):
            calls[0] += 1
            if calls[0] == 1:
                raise err_429
            resp = MagicMock()
            resp.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), \
             patch("time.sleep", side_effect=sleep_calls.append):
            gen._request_with_retry("GET", "https://api.meshy.ai/test", headers={})
            assert len(sleep_calls) == 1
            # Check if backoff_max_seconds was violated:
            sleep_time = sleep_calls[0]
            # Notice: generator.py sets delay = max(delay, retry_after) -> 86400.0!
            # It did NOT clamp to backoff_max_seconds!
            print(f"\n[EMPIRICAL OBSERVATION] Retry-After 86400 resulted in sleep={sleep_time}s (max_seconds={cfg.backoff_max_seconds})")
            assert sleep_time == 86400.0, "Empirically proves backoff_max_seconds is bypassed by Retry-After"


# ==============================================================================
# SUITE 3: TERMINAL 4XX CLIENT ERRORS & ERROR CLASSIFICATION
# ==============================================================================

class TestAdversarialClientErrors:
    """Tests fail-fast behavior on client 4xx errors and classifies gaps."""

    @pytest.mark.parametrize("status_code", [400, 401, 402, 403, 404, 422])
    def test_specified_terminal_4xx_fail_fast_without_sleep(self, status_code):
        """
        HTTP 400, 401, 402, 403, 404, 422 must fail immediately on attempt 1
        without sleeping or retrying.
        """
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", max_retries=5))
        sleep_mock = MagicMock()
        err = urllib.error.HTTPError(
            "https://api.meshy.ai", status_code, f"Client Error {status_code}",
            {}, io.BytesIO(f'{{"error": "{status_code}"}}'.encode("utf-8"))
        )

        with patch("urllib.request.urlopen", side_effect=err), patch("time.sleep", sleep_mock):
            with pytest.raises(RuntimeError) as exc_info:
                gen._request_with_retry("POST", "https://api.meshy.ai/test", headers={})
            assert str(status_code) in str(exc_info.value)
            sleep_mock.assert_not_called()

    @pytest.mark.parametrize("unhandled_4xx", [405, 408, 409, 413, 415, 429])
    def test_classification_of_other_4xx_codes(self, unhandled_4xx):
        """
        FINDING / ADVERSARIAL DISCOVERY:
        generator.py only specifies (400, 401, 402, 403, 404, 422) as terminal.
        If Meshy returns 405 (Method Not Allowed), 409 (Conflict), 413 (Payload Too Large),
        or 415 (Unsupported Media Type), generator.py misclassifies them as retriable!
        This test demonstrates that 405, 409, 413, 415 trigger retries instead of failing fast.
        """
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", max_retries=2))
        sleep_calls: List[float] = []
        calls = [0]
        err = urllib.error.HTTPError(
            "https://api.meshy.ai", unhandled_4xx, f"Client Error {unhandled_4xx}",
            {}, io.BytesIO(b'{"error": "client error"}')
        )

        def mock_urlopen(req, **kwargs):
            calls[0] += 1
            raise err

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), \
             patch("time.sleep", side_effect=sleep_calls.append):
            with pytest.raises(RuntimeError) as exc_info:
                gen._request_with_retry("POST", "https://api.meshy.ai/test", headers={})

            if unhandled_4xx == 429:
                # 429 SHOULD retry
                assert len(sleep_calls) == 2
            else:
                # 405, 408, 409, 413, 415 are 4xx client errors that SHOULD NOT retry,
                # but generator.py DOES retry them!
                print(f"\n[EMPIRICAL OBSERVATION] HTTP {unhandled_4xx} was retried {len(sleep_calls)} times!")
                assert len(sleep_calls) == 2


# ==============================================================================
# SUITE 4: CACHE INTEGRITY, INVALIDATION & REGENERATION TRIGGERS
# ==============================================================================

class TestAdversarialCacheIntegrity:
    """Stress tests cache corruption edge cases and cache invalidation."""

    def test_corrupted_0byte_glb_invalidates_cache(self, tmp_path, oak_species):
        """0-byte GLB in cache must return None from check_cache."""
        cache_dir = tmp_path / "cache" / oak_species.species_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{oak_species.species_id}.glb").write_bytes(b"")

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test"))
        cached = gen.check_cache(oak_species, target_dir=cache_dir)
        assert cached is None

    def test_corrupted_nonzero_garbage_glb_cache_behavior(self, tmp_path, oak_species):
        """
        FINDING / ADVERSARIAL DISCOVERY:
        What if the cached GLB file is NOT 0 bytes, but contains corrupted garbage bytes
        (e.g. truncated network download of 128 bytes: b'GARBAGE_NOT_A_GLTF_CONTAINER')?
        Let's test if check_cache detects the invalid GLB or returns a corrupted RawAsset!
        """
        cache_dir = tmp_path / "cache" / oak_species.species_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        # Write corrupted non-zero GLB
        (cache_dir / f"{oak_species.species_id}.glb").write_bytes(b"CORRUPTED_BINARY_NOT_GLTF_" * 10)

        # Write valid textures
        tex_dir = cache_dir / "textures"
        tex_dir.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (256, 256), (50, 100, 50))
        for ch in ["albedo.png", "normal.png", "roughness.png", "metallic.png"]:
            img.save(tex_dir / ch)

        # Write manifest with fake vertex counts
        manifest = {
            "species_id": oak_species.species_id,
            "vertex_count": 4000,
            "face_count": 3800,
            "textures": {k: f"textures/{k}.png" for k in ["albedo", "normal", "roughness", "metallic"]},
        }
        (cache_dir / "cache_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test"))
        cached = gen.check_cache(oak_species, target_dir=cache_dir)

        # EMPIRICAL OBSERVATION:
        # In generator.py: check_cache() only checks: if glb_path.stat().st_size == 0: continue
        # Then parse_glb_vertex_and_face_counts fails, but because manifest_data has vertex_count=4000,
        # check_cache returns a RawAsset with the corrupt GLB file!
        print(f"\n[EMPIRICAL OBSERVATION] check_cache returned: {cached}")
        if cached is not None:
            # Check if unpacking the cached asset's GLB raises ValueError
            with pytest.raises(ValueError):
                unpack_glb_header_and_json(cached.glb_path)
            print("[EMPIRICAL FINDING] check_cache returned a RawAsset containing a CORRUPTED GLB file!")

    @pytest.mark.parametrize("missing_channel", ["albedo", "normal", "roughness", "metallic"])
    def test_missing_single_texture_channel_invalidates_cache(self, tmp_path, oak_species, minimal_glb_binary, missing_channel):
        """Any single missing PBR texture must invalidate the cache."""
        cache_dir = tmp_path / "cache" / oak_species.species_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{oak_species.species_id}.glb").write_bytes(minimal_glb_binary)

        tex_dir = cache_dir / "textures"
        tex_dir.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (256, 256), (50, 100, 50))
        for ch in ["albedo", "normal", "roughness", "metallic"]:
            if ch != missing_channel:
                img.save(tex_dir / f"{ch}.png")

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test"))
        cached = gen.check_cache(oak_species, target_dir=cache_dir)
        assert cached is None, f"Cache with missing {missing_channel} must be invalidated"

    def test_corrupted_unopenable_texture_invalidates_cache(self, tmp_path, oak_species, minimal_glb_binary):
        """A texture file with 0 bytes or garbage data must invalidate the cache."""
        cache_dir = tmp_path / "cache" / oak_species.species_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{oak_species.species_id}.glb").write_bytes(minimal_glb_binary)

        tex_dir = cache_dir / "textures"
        tex_dir.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (256, 256), (50, 100, 50))
        img.save(tex_dir / "albedo.png")
        img.save(tex_dir / "normal.png")
        img.save(tex_dir / "roughness.png")
        # Write corrupted metallic.png
        (tex_dir / "metallic.png").write_bytes(b"NOT_A_PNG_GARBAGE")

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test"))
        cached = gen.check_cache(oak_species, target_dir=cache_dir)
        assert cached is None, "Corrupted metallic.png texture must invalidate cache"

    def test_truncated_json_manifest_cache_behavior(self, tmp_path, oak_species, minimal_glb_binary):
        """
        FINDING / ADVERSARIAL DISCOVERY:
        If cache_manifest.json is truncated / corrupted, what does check_cache do?
        Lines 501-506 in generator.py:
            if manifest_path.is_file():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest_data = json.load(f)
                except Exception:
                    pass
        The exception is silently swallowed and manifest_data defaults to {}!
        The asset is still returned as valid cache with metadata={}!
        """
        cache_dir = tmp_path / "cache" / oak_species.species_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{oak_species.species_id}.glb").write_bytes(minimal_glb_binary)

        tex_dir = cache_dir / "textures"
        tex_dir.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (256, 256), (50, 100, 50))
        for ch in ["albedo.png", "normal.png", "roughness.png", "metallic.png"]:
            img.save(tex_dir / ch)

        # Truncated JSON
        (cache_dir / "cache_manifest.json").write_text('{"species_id": "veg_tree_oak_01", "truncated": ', encoding="utf-8")

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test"))
        cached = gen.check_cache(oak_species, target_dir=cache_dir)

        print(f"\n[EMPIRICAL OBSERVATION] check_cache with truncated JSON returned: {cached}")
        # Notice: It does NOT invalidate the cache; it returns the asset with metadata={}!
        assert cached is not None
        assert cached.metadata == {}

    def test_cross_engine_cache_pollution_vulnerability(self, tmp_path, oak_species):
        """
        CRITICAL VULNERABILITY DISCOVERY:
        Procedural generation writes to output_dir with {species_id}.glb, textures, and manifest.
        When a user calls generate_plant(species, mode='meshy', output_dir=same_dir),
        Step 4 in generate_plant executes check_cache BEFORE Step 5 (mode == 'meshy').
        Because check_cache does NOT check manifest['source'] == 'meshy',
        it returns the procedural asset as source='cached'!
        The user explicitly asked for 'meshy', but gets a procedural asset from cache!
        And the API key check in Step 5 is completely bypassed!
        """
        shared_out = tmp_path / "shared_veg"

        # 1. Run procedural generation
        proc_gen = ProceduralBotanicalGenerator(seed=42)
        proc_asset = proc_gen.generate(oak_species, output_dir=shared_out)
        assert proc_asset.source == "procedural"

        # 2. Call generate_plant with mode="meshy" on the SAME directory WITHOUT an API key
        # If caching respects mode="meshy", it must either reject the procedural cache
        # or require an API key and fail.
        # But in generator.py, it returns the cached procedural asset!
        asset_meshy_req = generate_plant(
            oak_species,
            mode="meshy",
            output_dir=shared_out,
            generator_config=MeshyGeneratorConfig(api_key=None),
        )

        print(f"\n[EMPIRICAL VULNERABILITY] mode='meshy' returned asset with source='{asset_meshy_req.source}', metadata.source='{asset_meshy_req.metadata.get('source')}'")
        assert asset_meshy_req.source == "cached"
        assert asset_meshy_req.metadata.get("source") == "procedural"
        # The procedural asset hijacked the explicit meshy request!


# ==============================================================================
# SUITE 5: MASTER DISPATCH (GENERATE_PLANT) EDGE CASES & CONCURRENCY
# ==============================================================================

class TestAdversarialMasterDispatch:
    """Adversarial stress testing of master dispatch generate_plant."""

    def test_invalid_species_identifiers(self):
        """Verify invalid identifiers raise appropriate errors."""
        # Non-existent species string
        with pytest.raises(KeyError):
            generate_plant("nonexistent_unknown_alien_plant")

        # Empty string
        with pytest.raises(KeyError):
            generate_plant("")

        # Integer instead of string/PlantSpecies
        with pytest.raises(TypeError) as exc_info:
            generate_plant(12345)  # type: ignore
        assert "Expected PlantSpecies or str" in str(exc_info.value)

        # None
        with pytest.raises(TypeError):
            generate_plant(None)  # type: ignore

        # Dict
        with pytest.raises(TypeError):
            generate_plant({"species_id": "veg_tree_oak_01"})  # type: ignore

    def test_invalid_mode_silently_falls_to_auto(self, oak_species, tmp_path):
        """
        FINDING / ADVERSARIAL DISCOVERY:
        In generator.py:
            if mode == "procedural": ...
            if mode == "meshy": ...
            # Mode: Auto (Meshy with graceful Procedural Fallback)
        If mode="invalid_garbage", it does NOT raise ValueError!
        It silently falls into the 'auto' mode branch!
        """
        out_dir = tmp_path / "test_invalid_mode"
        asset = generate_plant(
            oak_species,
            mode="completely_invalid_mode_name",  # type: ignore
            output_dir=out_dir,
            generator_config=MeshyGeneratorConfig(api_key=None),
        )
        print(f"\n[EMPIRICAL OBSERVATION] Invalid mode silently executed as auto -> source='{asset.source}'")
        assert asset.source == "procedural"

    def test_unhandled_kwargs_are_silently_discarded(self, oak_species, tmp_path):
        """
        FINDING:
        generate_plant takes `**kwargs: Any`, but does not pass them to
        either ProceduralBotanicalGenerator or MeshyGenerator.
        E.g. passing texture_resolution=1024 has NO effect.
        """
        out_dir = tmp_path / "test_kwargs"
        asset = generate_plant(
            oak_species,
            mode="procedural",
            output_dir=out_dir,
            texture_resolution=1024,  # Kwarg passed
        )
        # Check actual texture size: ProceduralBotanicalGenerator defaulted to 512!
        albedo_size = asset.albedo.size
        print(f"\n[EMPIRICAL OBSERVATION] Requested texture_resolution=1024, actual albedo size={albedo_size}")
        assert albedo_size == (512, 512), "texture_resolution kwarg was silently ignored by generate_plant"

    def test_auto_fallback_on_missing_api_key(self, oak_species, tmp_path):
        """Auto mode with no API key must seamlessly return procedural asset."""
        out_dir = tmp_path / "auto_no_key"
        asset = generate_plant(
            oak_species,
            mode="auto",
            output_dir=out_dir,
            generator_config=MeshyGeneratorConfig(api_key=None),
        )
        assert asset.source == "procedural"
        assert asset.glb_path.is_file()
        assert 3000 <= asset.vertex_count <= 45000

    def test_auto_fallback_on_meshy_api_failure(self, oak_species, tmp_path):
        """Auto mode with API key but network/API error must fall back to procedural."""
        out_dir = tmp_path / "auto_api_fail"
        err_500 = urllib.error.HTTPError(
            "https://api.meshy.ai", 500, "Internal Error", {}, io.BytesIO(b"fatal")
        )
        with patch("urllib.request.urlopen", side_effect=err_500), patch("time.sleep"):
            asset = generate_plant(
                oak_species,
                mode="auto",
                output_dir=out_dir,
                generator_config=MeshyGeneratorConfig(api_key="msy_test", max_retries=1),
            )
            assert asset.source == "procedural"
            assert asset.glb_path.is_file()

    def test_concurrent_duplicate_requests_stress_test(self, oak_species, tmp_path):
        """
        STRESS HARNESS:
        Spawns 8 concurrent threads calling generate_plant(oak, mode='procedural', output_dir=shared_dir)
        to stress-test disk write contention, file locks, and manifest integrity under concurrent races.
        """
        shared_dir = tmp_path / "concurrent_shared"
        num_threads = 8
        assets: List[RawAsset] = []
        errors: List[Exception] = []

        def worker(idx: int):
            try:
                # Use identical seed so geometry is identical
                a = generate_plant(oak_species, mode="procedural", output_dir=shared_dir, seed=42)
                return a
            except Exception as e:
                errors.append(e)
                raise

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for f in concurrent.futures.as_completed(futures):
                try:
                    assets.append(f.result())
                except Exception:
                    pass

        assert len(errors) == 0, f"Concurrent execution produced errors: {errors}"
        assert len(assets) == num_threads

        # Verify output file integrity after concurrent writes
        glb_file = shared_dir / f"{oak_species.species_id}.glb"
        assert glb_file.is_file()
        assert glb_file.stat().st_size > 0

        # Unpack header to ensure valid glTF 2.0 binary after concurrent writes
        gltf, _ = unpack_glb_header_and_json(glb_file)
        assert "meshes" in gltf

        # Verify textures exist and are valid PIL images
        for ch in ["albedo", "normal", "roughness", "metallic"]:
            t_path = shared_dir / "textures" / f"{ch}.png"
            assert t_path.is_file()
            img = Image.open(t_path)
            img.load()

        # Verify manifest is valid JSON
        manifest_path = shared_dir / "cache_manifest.json"
        assert manifest_path.is_file()
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        assert manifest_data["species_id"] == oak_species.species_id
        assert manifest_data["vertex_count"] == assets[0].vertex_count
