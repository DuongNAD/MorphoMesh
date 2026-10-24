"""
Unit and Integration Test Suite for Milestone 2: Generation Engine & Fallback Harness
File: teamwork_projects/vegetation_library/tests/test_generator.py

Validates:
1. MeshyGenerator:
   - Configuration and API key resolution.
   - Preview & refine payload construction (prompts, negative blacklist, polycount, topology, art style).
   - Rate limit retry backoff on HTTP 429 with Retry-After header.
   - Transient server error retries on HTTP 500/503.
   - Terminal client error fast-fail on HTTP 401/403.
   - Max retries exceeded error.
   - Disk caching hit, miss, and invalidation behaviors.
   - Force regeneration cache bypass.
   - Full mocked two-stage workflow execution.
2. ProceduralBotanicalGenerator:
   - Procedural generation for representative species across all 7 biomes.
   - Vertex budget compliance [3000, 45000].
   - Ground root pivot alignment (Z_min = 0.0 ± 0.005m, base centering).
   - Zero skeletal armatures / skins / weights (N_bones = 0).
   - 4-channel PBR texture completeness (Albedo, Normal, Roughness, Metallic).
   - Deterministic repeatability across identical integer seeds.
   - Geometric diversity across different seeds.
   - Default seed derivation from species_id.
   - Bounding box dimensional sanity.
3. generate_plant Master Dispatch:
   - Explicit "procedural" mode routing.
   - Explicit "meshy" mode without key raises RuntimeError.
   - Explicit "meshy" mode with key succeeds.
   - "auto" mode without key falls back to procedural.
   - "auto" mode on API failure falls back to procedural.
   - "auto" mode with key dispatches to Meshy.
   - Identifier resolution: canonical species_id, binomial scientific name, common name.
   - Unknown identifier raises KeyError.
   - RawAsset contract compliance.
4. Binary GLB Structural Validation:
   - 4-byte container alignment and chunk padding.
   - Binary-level zero skins, bones, and animations.
   - glTF primitive attributes (POSITION, NORMAL, TEXCOORD_0).
   - Accessor bufferView bounds and min/max alignment.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import struct
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import MagicMock, patch
import urllib.error

import numpy as np
from PIL import Image
import pytest

from morphomesh.geometry.mesh import MeshGeometry
from vegetation_pipeline.catalog import (
    PlantSpecies,
    VegetationLibraryCatalog,
    get_catalog,
    get_species,
    UNIVERSAL_NEGATIVE_BLACKLIST,
)
from vegetation_pipeline.generator import (
    RawAsset,
    MeshyGenerator,
    MeshyGeneratorConfig,
    ProceduralBotanicalGenerator,
    ProceduralGeneratorConfig,
    generate_plant,
    parse_glb_vertex_and_face_counts,
    unpack_glb_header_and_json,
)


# ==============================================================================
# HELPER ASSERTIONS FOR BINARY GLB & PBR VALIDATION
# ==============================================================================

def assert_glb_static_mesh_invariants(glb_path: Union[str, Path]) -> None:
    """Strictly asserts that a GLB container contains ZERO armatures, skins, or weights."""
    gltf, _ = unpack_glb_header_and_json(glb_path)

    # 1. No skin definitions
    skins = gltf.get("skins")
    assert skins is None or len(skins) == 0, f"GLB contains skins: {skins}"

    # 2. No animation tracks
    animations = gltf.get("animations")
    assert animations is None or len(animations) == 0, f"GLB contains animations: {animations}"

    # 3. No joint or weight attributes on any primitive
    for m_idx, mesh in enumerate(gltf.get("meshes", [])):
        for p_idx, prim in enumerate(mesh.get("primitives", [])):
            attrs = prim.get("attributes", {})
            for attr_name in attrs.keys():
                assert not attr_name.startswith("JOINTS_"), (
                    f"Mesh {m_idx} prim {p_idx} contains skeletal joints: {attr_name}"
                )
                assert not attr_name.startswith("WEIGHTS_"), (
                    f"Mesh {m_idx} prim {p_idx} contains skinning weights: {attr_name}"
                )

    # 4. No node referencing skins
    for n_idx, node in enumerate(gltf.get("nodes", [])):
        assert "skin" not in node, f"Node {n_idx} references skin: {node}"


def assert_pbr_texture_suite_validity(textures: Dict[str, Image.Image]) -> None:
    """Asserts that all 4 PBR texture maps exist and contain authentic botanical data."""
    required_channels = ["albedo", "normal", "roughness", "metallic"]
    for channel in required_channels:
        assert channel in textures, f"Missing required PBR texture channel: '{channel}'"
        img = textures[channel]
        assert isinstance(img, Image.Image), f"Texture '{channel}' is not a PIL Image"
        assert img.width >= 256 and img.height >= 256, f"Texture '{channel}' resolution too low: {img.size}"

    # 1. Albedo: non-black and non-flat
    alb_arr = np.array(textures["albedo"].convert("RGB"), dtype=np.float32)
    assert alb_arr.mean() >= 15.0, f"Albedo texture is solid black or corrupt: mean={alb_arr.mean():.2f}"
    assert alb_arr.std() >= 3.0, f"Albedo texture has zero variation: std={alb_arr.std():.2f}"

    # 2. Normal: tangent-space outward (+Z dominant Blue channel)
    norm_arr = np.array(textures["normal"].convert("RGB"), dtype=np.float32)
    blue_mean = norm_arr[:, :, 2].mean()
    assert blue_mean >= 170.0, f"Normal map tangent-space Z is not outward dominant: blue_mean={blue_mean:.2f}"
    assert norm_arr.std() >= 1.0, f"Normal map lacks surface detail: std={norm_arr.std():.2f}"

    # 3. Roughness: realistic organic matte bounds [0.15, 0.95]
    rough_arr = np.array(textures["roughness"].convert("L"), dtype=np.float32) / 255.0
    assert 0.15 <= rough_arr.mean() <= 0.95, f"Roughness mean out of botanical bounds: {rough_arr.mean():.2f}"

    # 4. Metallic: strict dielectric plant tissue (<= 0.05)
    metal_arr = np.array(textures["metallic"].convert("L"), dtype=np.float32) / 255.0
    assert metal_arr.mean() <= 0.05, f"Botanical asset contains metallic material: mean={metal_arr.mean():.2f}"


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(scope="session")
def catalog() -> VegetationLibraryCatalog:
    return get_catalog()


@pytest.fixture(scope="session")
def representative_species_map(catalog: VegetationLibraryCatalog) -> Dict[str, PlantSpecies]:
    """Returns a representative species for each of the 7 biomes."""
    return {
        "broadleaf": catalog["veg_tree_oak_01"],
        "conifers": catalog["veg_conifer_pine_01"],
        "tropical": catalog["veg_tropical_palm_01"],
        "shrubs": catalog["veg_shrub_rose_01"],
        "groundcover": catalog["veg_ground_fern_01"],
        "succulents": catalog["veg_succulent_saguaro_01"],
        "vines": catalog["veg_vine_ivy_01"],
    }


@pytest.fixture
def sample_oak_species(catalog: VegetationLibraryCatalog) -> PlantSpecies:
    return catalog["veg_tree_oak_01"]


@pytest.fixture
def mock_glb_binary(tmp_path) -> bytes:
    """Generates a minimal valid binary GLB buffer with box geometry."""
    geom = MeshGeometry()
    geom.add_box((0.0, 0.0, 0.5), (1.0, 1.0, 1.0))
    temp_p = tmp_path / "temp_mock.glb"
    geom.export_glb(str(temp_p))
    with open(temp_p, "rb") as f:
        data = f.read()
    return data


# ==============================================================================
# 1. UNIT TESTS: MESHY GENERATOR (11 TESTS)
# ==============================================================================

class TestMeshyGeneratorUnit:
    """Unit tests for MeshyGenerator HTTP boundary, payloads, retries, and caching."""

    def test_meshy_generator_initialization_and_config(self):
        """1. Verifies default configuration parameters and API key precedence."""
        cfg = MeshyGeneratorConfig(api_key="test_key_123", target_polycount=30000)
        gen = MeshyGenerator(config=cfg)
        assert gen.config.api_key == "test_key_123"
        assert gen.config.ai_model == "meshy-6"
        assert gen.config.art_style == "realistic"
        assert gen.config.topology == "quad"
        assert gen.config.target_polycount == 30000
        assert gen.config.enable_pbr is True
        assert gen.config.texture_richness == "high"
        assert gen.config.max_retries == 5
        assert gen.resolve_api_key() == "test_key_123"

    def test_meshy_preview_payload_construction(self, sample_oak_species):
        """2. Asserts that preview request payload contains all conditioned prompt parameters."""
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_mock_test"))
        captured_payloads = []

        def mock_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            if "/openapi/v2/text-to-3d" in url and getattr(req, "method", None) == "POST":
                body = json.loads(req.data.decode("utf-8"))
                captured_payloads.append(body)
                resp = MagicMock()
                resp.read.return_value = json.dumps({"result": "task_prev_01"}).encode("utf-8")
                resp.__enter__.return_value = resp
                return resp
            raise ValueError(f"Unexpected URL: {url}")

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            task_id = gen._submit_preview(sample_oak_species, api_key="msy_mock_test")
            assert task_id == "task_prev_01"
            assert len(captured_payloads) == 1
            payload = captured_payloads[0]
            assert payload["mode"] == "preview"
            assert payload["prompt"] == sample_oak_species.meshy_spec.positive_prompt
            assert payload["negative_prompt"] == sample_oak_species.meshy_spec.negative_prompt
            assert payload["art_style"] == "realistic"
            assert payload["ai_model"] == "meshy-6"
            assert payload["topology"] == "quad"
            assert payload["target_polycount"] == sample_oak_species.meshy_spec.target_polycount
            assert payload["should_remesh"] is True

            # Verify negative blacklist tokens are strictly included
            for token in ["pot", "planter", "container", "human", "bones", "armature", "rig"]:
                assert token in payload["negative_prompt"].lower()

    def test_meshy_refine_payload_construction(self):
        """3. Asserts that refine request payload submits preview_task_id, enable_pbr, and richness."""
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_mock_test"))
        captured_payloads = []

        def mock_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            if "/openapi/v2/text-to-3d" in url and getattr(req, "method", None) == "POST":
                body = json.loads(req.data.decode("utf-8"))
                captured_payloads.append(body)
                resp = MagicMock()
                resp.read.return_value = json.dumps({"result": "task_refine_01"}).encode("utf-8")
                resp.__enter__.return_value = resp
                return resp
            raise ValueError(f"Unexpected URL: {url}")

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            refine_id = gen._submit_refine(preview_task_id="task_prev_01", api_key="msy_mock_test")
            assert refine_id == "task_refine_01"
            assert len(captured_payloads) == 1
            payload = captured_payloads[0]
            assert payload["mode"] == "refine"
            assert payload["preview_task_id"] == "task_prev_01"
            assert payload["enable_pbr"] is True
            assert payload["texture_richness"] == "high"

    def test_meshy_retry_backoff_on_429_rate_limit(self):
        """4. Verifies exponential backoff and Retry-After header parsing on HTTP 429."""
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", max_retries=3))
        calls = [0]
        sleep_intervals = []

        err_429 = urllib.error.HTTPError(
            "https://api.meshy.ai", 429, "Too Many Requests",
            {"Retry-After": "3.5"}, io.BytesIO(b'{"message": "Rate limit exceeded"}')
        )

        def mock_urlopen(req, **kwargs):
            calls[0] += 1
            if calls[0] == 1:
                raise err_429
            resp = MagicMock()
            resp.read.return_value = json.dumps({"result": "task_ok_after_retry"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), patch("time.sleep", side_effect=sleep_intervals.append):
            result = gen._request_with_retry(
                method="POST",
                url="https://api.meshy.ai/openapi/v2/text-to-3d",
                headers={"Authorization": "Bearer msy_test"},
                data=b"{}",
            )
            assert result["result"] == "task_ok_after_retry"
            assert calls[0] == 2
            assert len(sleep_intervals) == 1
            assert sleep_intervals[0] >= 3.5

    def test_meshy_retry_backoff_on_500_server_error(self):
        """5. Verifies exponential backoff retry progression on transient HTTP 500/503 errors."""
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", backoff_base_seconds=1.0, max_retries=4))
        calls = [0]
        sleep_intervals = []

        err_500 = urllib.error.HTTPError(
            "https://api.meshy.ai", 500, "Internal Server Error", {}, io.BytesIO(b'{"message": "Database timeout"}')
        )

        def mock_urlopen(req, **kwargs):
            calls[0] += 1
            if calls[0] <= 2:
                raise err_500
            resp = MagicMock()
            resp.read.return_value = json.dumps({"result": "task_recovered"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), patch("time.sleep", side_effect=sleep_intervals.append):
            result = gen._request_with_retry("GET", "https://api.meshy.ai/test", headers={})
            assert result["result"] == "task_recovered"
            assert calls[0] == 3
            assert len(sleep_intervals) == 2
            assert sleep_intervals[0] >= 1.0
            assert sleep_intervals[1] >= 2.0

    def test_meshy_terminal_error_after_max_retries(self):
        """6. Asserts that persistent HTTP 500 errors raise after exceeding max_retries."""
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", max_retries=2))
        err_500 = urllib.error.HTTPError("https://api.meshy.ai", 500, "Internal Error", {}, io.BytesIO(b"server down"))

        with patch("urllib.request.urlopen", side_effect=err_500), patch("time.sleep"):
            with pytest.raises(Exception) as exc_info:
                gen._request_with_retry("GET", "https://api.meshy.ai/test", headers={})
            assert "exceeded max retries" in str(exc_info.value).lower() or "500" in str(exc_info.value)

    def test_meshy_terminal_4xx_fails_fast_without_retry(self):
        """7. Asserts that client errors (HTTP 401, 403) fail immediately without retrying."""
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", max_retries=5))
        err_401 = urllib.error.HTTPError("https://api.meshy.ai", 401, "Unauthorized", {}, io.BytesIO(b"Invalid API key"))
        sleep_mock = MagicMock()

        with patch("urllib.request.urlopen", side_effect=err_401), patch("time.sleep", sleep_mock):
            with pytest.raises(Exception) as exc_info:
                gen._request_with_retry("GET", "https://api.meshy.ai/test", headers={})
            assert "401" in str(exc_info.value)
            sleep_mock.assert_not_called()

    def test_meshy_disk_caching_skips_network_calls(self, tmp_path, sample_oak_species, mock_glb_binary):
        """8. Asserts that valid existing disk cache returns RawAsset with source='cached' and zero HTTP requests."""
        cache_dir = tmp_path / "cache" / sample_oak_species.species_id
        cache_dir.mkdir(parents=True, exist_ok=True)

        glb_path = cache_dir / f"{sample_oak_species.species_id}.glb"
        with open(glb_path, "wb") as f:
            f.write(mock_glb_binary)

        # Write textures
        tex_dir = cache_dir / "textures"
        tex_dir.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (256, 256), (40, 100, 40))
        for tname in ["albedo.png", "normal.png", "roughness.png", "metallic.png"]:
            img.save(tex_dir / tname)

        # Write manifest
        manifest = {
            "species_id": sample_oak_species.species_id,
            "source": "meshy",
            "vertex_count": 24,
            "face_count": 12,
            "textures": {
                "albedo": "textures/albedo.png",
                "normal": "textures/normal.png",
                "roughness": "textures/roughness.png",
                "metallic": "textures/metallic.png",
            }
        }
        with open(cache_dir / "cache_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", cache_dir=tmp_path / "cache"))
        mock_urlopen = MagicMock()

        with patch("urllib.request.urlopen", mock_urlopen):
            raw_asset = gen.generate(sample_oak_species, output_dir=cache_dir)
            assert raw_asset.source == "cached"
            assert raw_asset.species_id == sample_oak_species.species_id
            assert raw_asset.glb_path.is_file()
            assert len(raw_asset.textures) == 4
            mock_urlopen.assert_not_called()

    def test_meshy_corrupted_cache_triggers_regeneration(self, tmp_path, sample_oak_species):
        """9. Asserts that 0-byte or corrupted cached files trigger regeneration."""
        cache_dir = tmp_path / "corrupt_cache" / sample_oak_species.species_id
        cache_dir.mkdir(parents=True, exist_ok=True)

        with open(cache_dir / f"{sample_oak_species.species_id}.glb", "wb") as f:
            f.write(b"")

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", cache_dir=tmp_path / "corrupt_cache"))
        cached = gen.check_cache(sample_oak_species, target_dir=cache_dir)
        assert cached is None, "Corrupted 0-byte cache must be invalidated"

    def test_meshy_force_regenerate_bypasses_cache(self, tmp_path, sample_oak_species, mock_glb_binary):
        """10. Asserts that force_regenerate=True ignores existing valid cache."""
        cache_dir = tmp_path / "cache" / sample_oak_species.species_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        with open(cache_dir / f"{sample_oak_species.species_id}.glb", "wb") as f:
            f.write(mock_glb_binary)

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", force_regenerate=True))
        cached = gen.check_cache(sample_oak_species, target_dir=cache_dir)
        assert cached is None, "force_regenerate=True must bypass disk cache"

    def test_meshy_two_stage_full_workflow_mocked(self, tmp_path, sample_oak_species, mock_glb_binary):
        """11. Simulates complete two-stage preview -> refine -> download workflow with mocked endpoints."""
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_full_test", polling_interval_seconds=0.01))
        out_dir = tmp_path / "meshy_full_out"

        def mock_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            method = getattr(req, "method", "GET")
            resp = MagicMock()
            if "/openapi/v2/text-to-3d" in url and method == "POST":
                body = json.loads(req.data.decode("utf-8"))
                if body.get("mode") == "preview":
                    resp.read.return_value = json.dumps({"result": "prev_123"}).encode("utf-8")
                else:
                    resp.read.return_value = json.dumps({"result": "ref_456"}).encode("utf-8")
            elif "/openapi/v2/text-to-3d/prev_123" in url:
                resp.read.return_value = json.dumps({"status": "SUCCEEDED", "id": "prev_123"}).encode("utf-8")
            elif "/openapi/v2/text-to-3d/ref_456" in url:
                resp.read.return_value = json.dumps({
                    "status": "SUCCEEDED",
                    "id": "ref_456",
                    "model_urls": {"glb": "https://assets.meshy.ai/model.glb"},
                }).encode("utf-8")
            elif "model.glb" in url:
                resp.read.side_effect = [mock_glb_binary, b""]
            else:
                resp.read.return_value = b"{}"
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            raw_asset = gen.generate(sample_oak_species, output_dir=out_dir)
            assert raw_asset.source == "meshy"
            assert raw_asset.species_id == sample_oak_species.species_id
            assert raw_asset.glb_path.is_file()
            assert len(raw_asset.textures) == 4

    def test_meshy_retry_after_strictly_capped_at_backoff_max_seconds(self):
        """Verifies that large Retry-After values (e.g. 86400s) are clamped to backoff_max_seconds."""
        cfg = MeshyGeneratorConfig(api_key="msy_test", backoff_max_seconds=15.0, max_retries=2)
        gen = MeshyGenerator(config=cfg)
        sleep_intervals = []
        err_429 = urllib.error.HTTPError(
            "https://api.meshy.ai", 429, "Too Many Requests",
            {"Retry-After": "86400"}, io.BytesIO(b'{"message": "Rate limit exceeded"}')
        )
        calls = [0]

        def mock_urlopen(req, **kwargs):
            calls[0] += 1
            if calls[0] == 1:
                raise err_429
            resp = MagicMock()
            resp.read.return_value = json.dumps({"result": "ok"}).encode("utf-8")
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), \
             patch("time.sleep", side_effect=sleep_intervals.append):
            res = gen._request_with_retry("POST", "https://api.meshy.ai/test", headers={})
            assert res["result"] == "ok"
            assert len(sleep_intervals) == 1
            assert sleep_intervals[0] == 15.0  # Strictly capped at backoff_max_seconds

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 405, 409, 413, 415, 422])
    def test_meshy_all_non_429_client_errors_fail_fast(self, status_code):
        """Verifies that all 4xx client errors except 429 fail fast on attempt 1 without sleeping."""
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

    def test_meshy_generate_raises_on_armature_or_skinning_violation(self, sample_oak_species, tmp_path):
        """Verifies that MeshyGenerator.generate() raises RuntimeError if downloaded GLB contains skins or bones."""
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test"))
        out_dir = tmp_path / "rigged_test"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Create a synthetic GLB with a 'skins' entry
        gltf_dict = {
            "asset": {"version": "2.0"},
            "skins": [{"joints": [0]}],
            "nodes": [{"name": "RootJoint"}],
            "meshes": [],
        }
        json_bytes = json.dumps(gltf_dict).encode("utf-8")
        pad = (4 - (len(json_bytes) % 4)) % 4
        json_bytes += b" " * pad

        total_len = 12 + 8 + len(json_bytes)
        header = struct.pack("<4sII", b"glTF", 2, total_len)
        chunk0_header = struct.pack("<II", len(json_bytes), 0x4E4F534A)
        mock_rigged_glb = header + chunk0_header + json_bytes

        def mock_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            resp = MagicMock()
            if "/openapi/v2/text-to-3d" in url and getattr(req, "method", "GET") == "POST":
                resp.read.return_value = json.dumps({"result": "task_prev"}).encode("utf-8")
            elif "/openapi/v2/text-to-3d/task_prev" in url:
                resp.read.return_value = json.dumps({
                    "status": "SUCCEEDED",
                    "model_urls": {"glb": "https://assets.meshy.ai/model.glb"},
                }).encode("utf-8")
            elif "model.glb" in url:
                resp.read.side_effect = [mock_rigged_glb, b""]
            else:
                resp.read.return_value = b"{}"
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            with pytest.raises(RuntimeError) as exc_info:
                gen.generate(sample_oak_species, output_dir=out_dir)
            assert "static mesh invariant" in str(exc_info.value).lower()

    def test_corrupted_magic_glb_triggers_cache_miss(self, tmp_path, sample_oak_species):
        """Rejects cached GLB files whose first 12 bytes do not match glTF 2.0 magic/version."""
        cache_dir = tmp_path / "cache_bad_magic" / sample_oak_species.species_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{sample_oak_species.species_id}.glb").write_bytes(b"CORRUPTED_NOT_GLTF_CONTAINER")
        tex_dir = cache_dir / "textures"
        tex_dir.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (64, 64), (50, 100, 50))
        for ch in ["albedo", "normal", "roughness", "metallic"]:
            img.save(tex_dir / f"{ch}.png")
        manifest = {"species_id": sample_oak_species.species_id, "source": "meshy", "vertex_count": 100, "face_count": 50}
        (cache_dir / "cache_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test"))
        cached = gen.check_cache(sample_oak_species, target_dir=cache_dir, expected_source="meshy")
        assert cached is None

    def test_check_cache_rejects_truncated_json_manifest(self, tmp_path, sample_oak_species, mock_glb_binary):
        """Invalid or truncated cache_manifest.json must be treated as cache miss."""
        cache_dir = tmp_path / "cache_bad_json" / sample_oak_species.species_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{sample_oak_species.species_id}.glb").write_bytes(mock_glb_binary)
        tex_dir = cache_dir / "textures"
        tex_dir.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (64, 64), (50, 100, 50))
        for ch in ["albedo", "normal", "roughness", "metallic"]:
            img.save(tex_dir / f"{ch}.png")
        (cache_dir / "cache_manifest.json").write_text('{"species_id": "veg_tree_oak_01", "truncated": ', encoding="utf-8")

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test"))
        cached = gen.check_cache(sample_oak_species, target_dir=cache_dir, expected_source="meshy")
        assert cached is None

    def test_check_cache_source_provenance_enforcement(self, tmp_path, sample_oak_species, mock_glb_binary):
        """Cached procedural assets must be rejected when expected_source='meshy'."""
        cache_dir = tmp_path / "cache_provenance" / sample_oak_species.species_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{sample_oak_species.species_id}.glb").write_bytes(mock_glb_binary)
        tex_dir = cache_dir / "textures"
        tex_dir.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (64, 64), (50, 100, 50))
        for ch in ["albedo", "normal", "roughness", "metallic"]:
            img.save(tex_dir / f"{ch}.png")
        manifest = {"species_id": sample_oak_species.species_id, "source": "procedural", "vertex_count": 100, "face_count": 50}
        (cache_dir / "cache_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test"))
        cached = gen.check_cache(sample_oak_species, target_dir=cache_dir, expected_source="meshy")
        assert cached is None


# ==============================================================================
# 2. UNIT TESTS: PROCEDURAL BOTANICAL GENERATOR (9 TESTS)
# ==============================================================================

class TestProceduralBotanicalGeneratorUnit:
    """Unit tests for offline procedural generator across all 7 biomes."""

    @pytest.mark.parametrize("biome_key,species_id", [
        ("broadleaf", "veg_tree_oak_01"),
        ("conifers", "veg_conifer_pine_01"),
        ("tropical", "veg_tropical_palm_01"),
        ("shrubs", "veg_shrub_rose_01"),
        ("groundcover", "veg_ground_fern_01"),
        ("succulents", "veg_succulent_saguaro_01"),
        ("vines", "veg_vine_ivy_01"),
    ])
    def test_procedural_generation_all_7_biomes(self, catalog, biome_key, species_id, tmp_path):
        """12. Asserts procedural generation succeeds and returns parseable GLB for all 7 biomes."""
        species = catalog[species_id]
        out_dir = tmp_path / species_id
        proc_gen = ProceduralBotanicalGenerator()

        raw_asset = proc_gen.generate(species, output_dir=out_dir, seed=42)

        assert raw_asset.source == "procedural"
        assert raw_asset.species_id == species_id
        assert raw_asset.glb_path.is_file()
        assert raw_asset.mesh is not None
        assert isinstance(raw_asset.mesh, MeshGeometry)

        verts, faces = parse_glb_vertex_and_face_counts(raw_asset.glb_path)
        assert verts > 0
        assert faces > 0

    @pytest.mark.parametrize("species_id", [
        "veg_tree_oak_01",
        "veg_conifer_pine_01",
        "veg_tropical_palm_01",
        "veg_shrub_rose_01",
        "veg_ground_fern_01",
        "veg_succulent_saguaro_01",
        "veg_vine_ivy_01",
    ])
    def test_vertex_count_budget_across_7_biomes(self, catalog, species_id, tmp_path):
        """13. Strictly asserts vertex count satisfies 3,000 <= V <= 45,000 for every biome."""
        species = catalog[species_id]
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(species, output_dir=tmp_path / species_id, seed=42)

        v_count = len(raw_asset.mesh.vertices)
        assert 3000 <= v_count <= 45000, (
            f"Species {species_id} vertex count {v_count} outside budget [3000, 45000]"
        )
        assert 3000 <= raw_asset.vertex_count <= 45000

        vert_coords = np.array(raw_asset.mesh.vertices, dtype=np.float32)
        assert np.isfinite(vert_coords).all(), f"Species {species_id} contains NaN or Inf coordinates"

    @pytest.mark.parametrize("species_id", [
        "veg_tree_oak_01",
        "veg_conifer_pine_01",
        "veg_tropical_palm_01",
        "veg_shrub_rose_01",
        "veg_ground_fern_01",
        "veg_succulent_saguaro_01",
        "veg_vine_ivy_01",
    ])
    def test_ground_pivot_root_alignment_across_7_biomes(self, catalog, species_id, tmp_path):
        """14. Strictly asserts that the lowest vertex sits at Z_min = 0.0 ± 0.005m ground contact."""
        species = catalog[species_id]
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(species, output_dir=tmp_path / species_id, seed=42)

        z_coords = [v[2] for v in raw_asset.mesh.vertices]
        min_z = min(z_coords)
        assert abs(min_z) <= 0.005, (
            f"Species {species_id} ground root base Z_min={min_z:.4f}m exceeds 5mm tolerance"
        )

        # Bottom 5% contact centroid centered near origin (0, 0)
        max_z = max(z_coords)
        h = max_z - min_z
        base_verts = [v for v in raw_asset.mesh.vertices if v[2] <= min_z + 0.05 * h]
        assert len(base_verts) > 0
        mean_x = np.mean([v[0] for v in base_verts])
        mean_y = np.mean([v[1] for v in base_verts])
        assert abs(mean_x) <= 0.05, f"Species {species_id} base off-center X={mean_x:.4f}m"
        assert abs(mean_y) <= 0.05, f"Species {species_id} base off-center Y={mean_y:.4f}m"

    @pytest.mark.parametrize("species_id", [
        "veg_tree_oak_01",
        "veg_conifer_pine_01",
        "veg_tropical_palm_01",
        "veg_shrub_rose_01",
        "veg_ground_fern_01",
        "veg_succulent_saguaro_01",
        "veg_vine_ivy_01",
    ])
    def test_zero_skeletal_armatures_in_glb_across_7_biomes(self, catalog, species_id, tmp_path):
        """15. Strictly asserts exported GLB contains zero skins, armatures, bones, or skinning weights."""
        species = catalog[species_id]
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(species, output_dir=tmp_path / species_id, seed=42)
        assert_glb_static_mesh_invariants(raw_asset.glb_path)

    @pytest.mark.parametrize("species_id", [
        "veg_tree_oak_01",
        "veg_conifer_pine_01",
        "veg_tropical_palm_01",
        "veg_shrub_rose_01",
        "veg_ground_fern_01",
        "veg_succulent_saguaro_01",
        "veg_vine_ivy_01",
    ])
    def test_pbr_texture_suite_completeness_across_7_biomes(self, catalog, species_id, tmp_path):
        """16. Asserts that all 4 PBR texture maps exist and satisfy physical value ranges."""
        species = catalog[species_id]
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(species, output_dir=tmp_path / species_id, seed=42)
        assert_pbr_texture_suite_validity(raw_asset.textures)

    def test_deterministic_repeatability_same_seed(self, catalog, tmp_path):
        """17. Asserts that identical integer seeds produce bit-for-bit identical mesh geometry."""
        species = catalog["veg_tree_oak_01"]
        proc_gen = ProceduralBotanicalGenerator()

        asset_a = proc_gen.generate(species, output_dir=tmp_path / "seed_a", seed=1337)
        asset_b = proc_gen.generate(species, output_dir=tmp_path / "seed_b", seed=1337)

        assert len(asset_a.mesh.vertices) == len(asset_b.mesh.vertices)
        assert len(asset_a.mesh.faces) == len(asset_b.mesh.faces)
        assert np.allclose(asset_a.mesh.vertices, asset_b.mesh.vertices, atol=1e-6)
        assert asset_a.mesh.faces == asset_b.mesh.faces

    def test_seed_diversity_different_seeds(self, catalog, tmp_path):
        """18. Asserts that different seeds produce organically varied geometric branching."""
        species = catalog["veg_tree_oak_01"]
        proc_gen = ProceduralBotanicalGenerator()

        asset_1 = proc_gen.generate(species, output_dir=tmp_path / "seed_1", seed=42)
        asset_2 = proc_gen.generate(species, output_dir=tmp_path / "seed_2", seed=99)

        assert not np.allclose(asset_1.mesh.vertices, asset_2.mesh.vertices, atol=1e-3)

    def test_procedural_generator_default_seed_from_species_id(self, catalog, tmp_path):
        """19. When seed is omitted, verifies determinism keyed to species identifier."""
        species = catalog["veg_conifer_pine_01"]
        proc_gen = ProceduralBotanicalGenerator()

        asset_1 = proc_gen.generate(species, output_dir=tmp_path / "default_s1")
        asset_2 = proc_gen.generate(species, output_dir=tmp_path / "default_s2")

        assert len(asset_1.mesh.vertices) == len(asset_2.mesh.vertices)
        assert np.allclose(asset_1.mesh.vertices, asset_2.mesh.vertices, atol=1e-6)

    def test_procedural_bounding_box_validity(self, catalog, tmp_path):
        """20. Validates computed bounding box dimensions are non-zero and aligned."""
        species = catalog["veg_shrub_rose_01"]
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(species, output_dir=tmp_path / "bbox_test", seed=42)

        bbox = raw_asset.mesh.compute_bounding_box()
        assert bbox.dimensions[0] > 0.1
        assert bbox.dimensions[1] > 0.1
        assert bbox.dimensions[2] > 0.1
        assert bbox.min_point[2] <= 0.005

    def test_conifer_zero_orphan_vertices_and_quad_faces(self, catalog, tmp_path):
        """Asserts conifer procedural generation produces zero orphan vertices and 100% pure quads."""
        species = catalog["veg_conifer_pine_01"]
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(species, output_dir=tmp_path / "conifer_orphan_check", seed=42)

        mesh = raw_asset.mesh
        all_face_v = set()
        for f in mesh.faces:
            all_face_v.update(f)
        orphans = set(range(len(mesh.vertices))) - all_face_v

        assert len(orphans) == 0, f"Conifer contains {len(orphans)} unindexed orphan vertices"
        assert raw_asset.metadata["quad_ratio"] == 1.0, f"Conifer quad ratio {raw_asset.metadata['quad_ratio']} != 1.0"
        assert raw_asset.metadata["tri_count"] == 0

    @pytest.mark.parametrize("boundary_seed", [-1, -42, 0, 2**32 - 1, 2**32, 2**32 + 5, 10**12, "test_string_seed", 3.14])
    def test_seed_modulo_boundary_values(self, catalog, boundary_seed, tmp_path):
        """Asserts seeds outside standard uint32 range or of non-int type are safely normalized without error."""
        species = catalog["veg_tree_oak_01"]
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(species, output_dir=tmp_path / f"seed_{abs(hash(str(boundary_seed))) % 10000}", seed=boundary_seed)

        assert 3000 <= raw_asset.vertex_count <= 45000
        assert raw_asset.mesh is not None
        assert 0 <= raw_asset.metadata["seed"] < 2**32

    def test_broadleaf_subcrown_proportional_scaling(self, catalog, tmp_path):
        """Asserts broadleaf tree subcrown dimensions scale down proportionally for miniature species."""
        species = catalog["veg_tree_oak_01"]
        mini_species = species.model_copy(deep=True)
        mini_species.dimensions.height_m = 0.05
        mini_species.dimensions.height_range_m = (0.01, 0.10)
        mini_species.dimensions.canopy_spread_m = 0.05
        mini_species.dimensions.trunk_stem_diameter_m = 0.01

        proc_gen = ProceduralBotanicalGenerator()
        mini_asset = proc_gen.generate(mini_species, output_dir=tmp_path / "mini_oak", seed=42)
        bbox = mini_asset.mesh.compute_bounding_box()

        # Bounding box should scale down (well below the unscaled 2.8m blowout)
        assert bbox.dimensions[0] < 1.0, f"Miniature tree width {bbox.dimensions[0]}m exceeds 1.0m"
        assert bbox.dimensions[1] < 1.0, f"Miniature tree depth {bbox.dimensions[1]}m exceeds 1.0m"


# ==============================================================================
# 3. INTEGRATION TESTS: MASTER DISPATCH (generate_plant) (11 TESTS)
# ==============================================================================

class TestGeneratePlantDispatch:
    """Tests master entry point routing across modes, fallback handling, and input types."""

    def test_dispatch_mode_procedural_explicit(self, sample_oak_species, tmp_path):
        """21. Explicit mode='procedural' must invoke ProceduralBotanicalGenerator with zero API calls."""
        mock_urlopen = MagicMock()
        with patch("urllib.request.urlopen", mock_urlopen):
            asset = generate_plant(sample_oak_species, mode="procedural", output_dir=tmp_path / "proc")
            assert asset.source == "procedural"
            assert asset.glb_path.is_file()
            assert 3000 <= asset.vertex_count <= 45000
            mock_urlopen.assert_not_called()

    def test_dispatch_mode_meshy_explicit_without_key_raises(self, sample_oak_species, monkeypatch, tmp_path):
        """22. Explicit mode='meshy' without an API key must raise an informative exception."""
        monkeypatch.delenv("MESHY_API_KEY", raising=False)
        monkeypatch.delenv("MESHY_AI_API_KEY", raising=False)
        with pytest.raises(Exception) as exc_info:
            generate_plant(sample_oak_species, mode="meshy", output_dir=tmp_path / "meshy_no_key")
        assert "api key" in str(exc_info.value).lower()

    def test_dispatch_mode_meshy_explicit_with_key(self, sample_oak_species, mock_glb_binary, tmp_path, monkeypatch):
        """23. Explicit mode='meshy' with an API key calls MeshyGenerator and returns meshy asset."""
        monkeypatch.setenv("MESHY_API_KEY", "msy_mock_test_key")

        def mock_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            resp = MagicMock()
            if "/openapi/v2/text-to-3d" in url and getattr(req, "method", "GET") == "POST":
                resp.read.return_value = json.dumps({"result": "task_id_1"}).encode("utf-8")
            elif "/openapi/v2/text-to-3d/task_id_1" in url:
                resp.read.return_value = json.dumps({
                    "status": "SUCCEEDED",
                    "model_urls": {"glb": "https://assets.meshy.ai/model.glb"},
                }).encode("utf-8")
            elif "model.glb" in url:
                resp.read.side_effect = [mock_glb_binary, b""]
            else:
                resp.read.return_value = b"{}"
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            asset = generate_plant(sample_oak_species, mode="meshy", output_dir=tmp_path / "meshy_exp")
            assert asset.source == "meshy"
            assert asset.species_id == sample_oak_species.species_id

    def test_dispatch_mode_auto_without_key_falls_back_to_procedural(self, sample_oak_species, monkeypatch, tmp_path):
        """24. When mode='auto' and no API key exists, gracefully fallback to procedural without crashing."""
        monkeypatch.delenv("MESHY_API_KEY", raising=False)
        monkeypatch.delenv("MESHY_AI_API_KEY", raising=False)
        asset = generate_plant(sample_oak_species, mode="auto", output_dir=tmp_path / "auto_fallback")
        assert asset.source == "procedural"
        assert asset.glb_path.is_file()
        assert 3000 <= asset.vertex_count <= 45000
        assert_pbr_texture_suite_validity(asset.textures)

    def test_dispatch_mode_auto_on_api_error_falls_back_to_procedural(self, sample_oak_species, monkeypatch, tmp_path):
        """25. When mode='auto' and Meshy API fails with HTTP 500, gracefully fallback to procedural."""
        monkeypatch.setenv("MESHY_API_KEY", "msy_mock_test_key")
        err_500 = urllib.error.HTTPError("https://api.meshy.ai", 500, "Server Down", {}, io.BytesIO(b"error"))

        with patch("urllib.request.urlopen", side_effect=err_500), patch("time.sleep"):
            asset = generate_plant(sample_oak_species, mode="auto", output_dir=tmp_path / "auto_api_err")
            assert asset.source == "procedural"
            assert asset.glb_path.is_file()
            assert 3000 <= asset.vertex_count <= 45000

    def test_dispatch_mode_auto_with_key_uses_meshy(self, sample_oak_species, mock_glb_binary, tmp_path, monkeypatch):
        """26. When mode='auto' and API key is present, succeeds via Meshy generation."""
        monkeypatch.setenv("MESHY_API_KEY", "msy_mock_test_key")

        def mock_urlopen(req, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else req
            resp = MagicMock()
            if "/openapi/v2/text-to-3d" in url and getattr(req, "method", "GET") == "POST":
                resp.read.return_value = json.dumps({"result": "task_id_auto"}).encode("utf-8")
            elif "/openapi/v2/text-to-3d/task_id_auto" in url:
                resp.read.return_value = json.dumps({
                    "status": "SUCCEEDED",
                    "model_urls": {"glb": "https://assets.meshy.ai/model.glb"},
                }).encode("utf-8")
            elif "model.glb" in url:
                resp.read.side_effect = [mock_glb_binary, b""]
            else:
                resp.read.return_value = b"{}"
            resp.__enter__.return_value = resp
            return resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            asset = generate_plant(sample_oak_species, mode="auto", output_dir=tmp_path / "auto_meshy")
            assert asset.source == "meshy"

    def test_dispatch_accepts_string_species_id(self, tmp_path):
        """27. generate_plant accepts canonical species_id string."""
        asset = generate_plant("veg_tree_oak_01", mode="procedural", output_dir=tmp_path / "str_id")
        assert asset.species_id == "veg_tree_oak_01"
        assert asset.source == "procedural"

    def test_dispatch_accepts_scientific_name(self, tmp_path):
        """28. generate_plant accepts botanical binomial scientific name."""
        asset = generate_plant("Quercus robur", mode="procedural", output_dir=tmp_path / "sci_name")
        assert asset.species_id == "veg_tree_oak_01"
        assert asset.source == "procedural"

    def test_dispatch_accepts_common_name(self, tmp_path):
        """29. generate_plant accepts common vernacular name."""
        asset = generate_plant("English Oak", mode="procedural", output_dir=tmp_path / "common_name")
        assert asset.species_id == "veg_tree_oak_01"
        assert asset.source == "procedural"

    def test_dispatch_invalid_species_raises_keyerror(self):
        """30. generate_plant raises KeyError when passed an unknown species identifier."""
        with pytest.raises(KeyError):
            generate_plant("fictional_alien_tree_99", mode="procedural")

    def test_raw_asset_contract_compliance(self, sample_oak_species, tmp_path):
        """31. Asserts that returned RawAsset strictly complies with the M2 <-> M3 contract."""
        asset = generate_plant(sample_oak_species, mode="procedural", output_dir=tmp_path / "contract")
        assert isinstance(asset, RawAsset)
        assert isinstance(asset.species_id, str)
        assert isinstance(asset.glb_path, Path)
        assert asset.glb_path.exists()
        assert isinstance(asset.textures, dict)
        assert set(asset.textures.keys()) == {"albedo", "normal", "roughness", "metallic"}
        assert asset.source in ("meshy", "procedural", "cached")
        assert isinstance(asset.vertex_count, int) and asset.vertex_count >= 3000
        assert isinstance(asset.face_count, int) and asset.face_count > 0
        assert isinstance(asset.metadata, dict)

    def test_cache_provenance_rejects_procedural_for_explicit_meshy(self, sample_oak_species, monkeypatch, tmp_path):
        """Even if procedural cache exists at output_dir, mode='meshy' without key must raise without returning cache."""
        monkeypatch.delenv("MESHY_API_KEY", raising=False)
        monkeypatch.delenv("MESHY_AI_API_KEY", raising=False)
        shared_dir = tmp_path / "ambient_procedural"
        proc_gen = ProceduralBotanicalGenerator(seed=42)
        proc_gen.generate(sample_oak_species, output_dir=shared_dir)

        with pytest.raises(Exception) as exc_info:
            generate_plant(sample_oak_species, mode="meshy", output_dir=shared_dir)
        assert "api key" in str(exc_info.value).lower()

    @pytest.mark.parametrize("invalid_mode", ["invalid", "mesh", "procedurial", "hybrid", ""])
    def test_dispatch_invalid_mode_raises_value_error(self, sample_oak_species, invalid_mode):
        """Invalid mode string must raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            generate_plant(sample_oak_species, mode=invalid_mode)  # type: ignore
        assert "invalid generation mode" in str(exc_info.value).lower()


# ==============================================================================
# 4. BINARY GLTF / GLB STRUCTURAL VALIDATION (4 TESTS)
# ==============================================================================

class TestGlbBinaryValidation:
    """Low-level binary glTF container structural compliance tests."""

    def test_glb_container_alignment_and_padding(self, sample_oak_species, tmp_path):
        """32. Validates that glTF chunk lengths and total file size are aligned to 4-byte boundaries."""
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(sample_oak_species, output_dir=tmp_path / "bin_align", seed=42)

        with open(raw_asset.glb_path, "rb") as f:
            data = f.read()

        assert len(data) % 4 == 0, "Total GLB file size must be 4-byte aligned"
        magic, version, length = struct.unpack_from("<4sII", data, 0)
        assert magic == b"glTF"
        assert version == 2
        assert length == len(data)

        # Chunk 0 (JSON)
        c0_len, c0_type = struct.unpack_from("<I4s", data, 12)
        assert c0_type == b"JSON"
        assert c0_len % 4 == 0, "JSON chunk must be padded to 4-byte boundary"

        # Chunk 1 (BIN)
        c1_offset = 12 + 8 + c0_len
        c1_len, c1_type = struct.unpack_from("<I4s", data, c1_offset)
        assert c1_type.startswith(b"BIN")
        assert c1_len % 4 == 0, "BIN chunk must be padded to 4-byte boundary"
        assert 12 + (8 + c0_len) + (8 + c1_len) == length

    def test_glb_zero_bones_and_skins_binary_level(self, sample_oak_species, tmp_path):
        """33. Asserts zero skins or bones exist in glTF JSON chunk structure."""
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(sample_oak_species, output_dir=tmp_path / "bin_skin", seed=42)
        gltf, _ = unpack_glb_header_and_json(raw_asset.glb_path)
        assert gltf.get("skins") is None or len(gltf.get("skins")) == 0
        assert gltf.get("animations") is None or len(gltf.get("animations")) == 0

    def test_glb_primitive_attributes_presence(self, sample_oak_species, tmp_path):
        """34. Asserts primitives define valid POSITION, NORMAL, TEXCOORD_0 attributes and valid indices."""
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(sample_oak_species, output_dir=tmp_path / "bin_attrs", seed=42)
        gltf, _ = unpack_glb_header_and_json(raw_asset.glb_path)

        meshes = gltf.get("meshes", [])
        assert len(meshes) > 0
        for m in meshes:
            for p in m.get("primitives", []):
                attrs = p.get("attributes", {})
                assert "POSITION" in attrs
                assert "NORMAL" in attrs
                assert "TEXCOORD_0" in attrs
                assert "indices" in p

    def test_glb_accessors_and_bufferviews_bounds(self, sample_oak_species, tmp_path):
        """35. Validates accessor min/max bounds and bufferView byte lengths."""
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(sample_oak_species, output_dir=tmp_path / "bin_bounds", seed=42)
        gltf, bin_bytes = unpack_glb_header_and_json(raw_asset.glb_path)

        accessors = gltf.get("accessors", [])
        bvs = gltf.get("bufferViews", [])
        assert len(accessors) >= 4
        assert len(bvs) >= 4

        pos_acc = accessors[0]
        assert "min" in pos_acc and "max" in pos_acc
        assert pos_acc["min"][2] <= 0.005  # Ground root alignment in glTF accessor min bound
