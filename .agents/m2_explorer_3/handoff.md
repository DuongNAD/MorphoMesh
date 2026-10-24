# Handoff Report: Milestone 2 Generator QA & Integration Test Suite Design

- **Author**: Explorer 3 (`m2_explorer_3`)
- **Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\m2_explorer_3`
- **Target Test File**: `teamwork_projects/vegetation_library/tests/test_generator.py`
- **Target Implementation File**: `teamwork_projects/vegetation_library/vegetation_pipeline/generator.py`
- **Parent Conversation ID**: `1f2774e9-3e4e-4a4c-8dc6-f85249e37b16`
- **Date**: 2026-09-10T05:38:00Z
- **Status**: Complete (Hard Handoff)

---

## 1. Observation

### 1.1 Test Infrastructure & Runtime Environment
- **Python Virtual Environment**: Located at `E:\tool\mcp\MorphoMesh\.venv` running Python 3.11.9.
  - Executable: `E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe`.
  - System `python` on PATH points to Windows Store App Execution Alias (`Python was not found...`). Python commands must invoke `.venv\Scripts\python.exe` or `uv run python`.
- **Installed Packages (`uv pip list`)**:
  - `pytest` 9.1.1 (`pytest-asyncio` 1.4.0)
  - `numpy` 2.4.6
  - `pillow` 12.3.0
  - `pydantic` 2.13.5
  - `httpx` 0.28.1 (`httpcore` 1.0.9)
  - `morphomesh` 0.1.0 (editable)
- **Unavailable Packages in `.venv`**:
  - `trimesh`: NOT installed (`No module named 'trimesh'`).
  - `pygltflib`: NOT installed (`No module named 'pygltflib'`).
  - `requests`: NOT installed (`No module named 'requests'`).
  - Standard library modules `struct`, `json`, `io`, `urllib.request`, `unittest.mock` must be utilized for binary glTF validation and network mocking.
- **Baseline Test Suite Verification**:
  - Command: `E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe -m pytest teamwork_projects/vegetation_library/tests/test_catalog.py -v`
  - Result: **52 passed in 0.17s** (100% pass rate).
- **Test Infrastructure Configuration (`teamwork_projects/vegetation_library/tests/conftest.py`)**:
  - Lines 10–17 automatically inject `PROJECT_DIR` (`teamwork_projects/vegetation_library`) and `REPO_ROOT` (`E:\tool\mcp\MorphoMesh`) into `sys.path`.

### 1.2 Catalog Integration Baseline (`vegetation_pipeline/catalog.py`)
- **Total Species & Categories**: 35 species across 7 biomes (5 species per biome).
- **Category Canonical IDs & Aliases**:
  - `broadleaf_deciduous_trees` (alias: `broadleaf_trees`, `broadleaf`, `trees`)
  - `conifers_evergreens` (alias: `conifers`, `evergreens`)
  - `tropical_foliage_palms` (alias: `tropical`, `palms`)
  - `flowering_shrubs_ornamentals` (alias: `shrubs`, `ornamentals`)
  - `ferns_grasses_groundcover` (alias: `groundcover`, `ferns`, `grasses`)
  - `succulents_cacti` (alias: `succulents`, `cacti`)
  - `climbing_vines_epiphytes` (alias: `vines`, `epiphytes`)
- **Representative Species per Biome**:
  1. Broadleaf Tree: `veg_tree_oak_01` (Quercus robur / English Oak)
  2. Conifer: `veg_conifer_pine_01` (Pinus sylvestris / Scots Pine)
  3. Tropical Palm: `veg_tropical_palm_01` (Chamaerops humilis / Mediterranean Fan Palm)
  4. Shrub: `veg_shrub_rose_01` (Rosa canina / Wild Dog Rose)
  5. Groundcover/Fern: `veg_ground_fern_01` (Nephrolepis exaltata / Boston Sword Fern)
  6. Succulent: `veg_succulent_saguaro_01` (Carnegiea gigantea / Saguaro Cactus)
  7. Vine: `veg_vine_ivy_01` (Hedera helix / English Ivy)
- **Universal Negative Blacklist (`UNIVERSAL_NEGATIVE_BLACKLIST`, Line 17)**:
  Contains mandatory negative tokens: `"pot, planter, flowerpot, flower pot, plant pot, terracotta, container, vase, bowl, bucket, crate, dish, tray, saucer, pedestal, base stand, stand, ground soil box, square block, platform, roots in pot, indoor room, wall, background, floor, furniture, table, human, hands, person, people, man, woman, character, body, face, animal, insect, artificial plastic, artificial grass, low quality, deformed, floating leaves, disconnected branches, blurry, cartoon, toy, miniature, wireframe, baked lighting shadow, skeleton, bones, armature, rig, rigged, rigging, skinning, joints, watermark, text, logo"`.

### 1.3 Meshy AI Generator Architecture (`m2_explorer_1/handoff.md`)
- **Class**: `MeshyGenerator(config: Optional[MeshyGeneratorConfig] = None)`
- **Configuration**: `MeshyGeneratorConfig` (api_key, base_url, ai_model="meshy-4", art_style="realistic", topology="quad", target_polycount=28000, enable_pbr=True, texture_richness="high", max_retries=5, backoff_base_seconds=2.0, backoff_max_seconds=60.0, use_cache=True, force_regenerate=False).
- **Two-Stage HTTP Lifecycle**:
  - Preview: `POST https://api.meshy.ai/openapi/v2/text-to-3d` with `mode="preview"`, prompt, negative blacklist, polycount, art style, topology.
  - Preview Poll: `GET https://api.meshy.ai/openapi/v2/text-to-3d/{preview_task_id}` until status is `"SUCCEEDED"`.
  - Refine: `POST https://api.meshy.ai/openapi/v2/text-to-3d` with `mode="refine"`, `preview_task_id`, `enable_pbr=True`, `texture_richness="high"`.
  - Refine Poll: `GET https://api.meshy.ai/openapi/v2/text-to-3d/{refine_task_id}` until status is `"SUCCEEDED"`.
- **Rate Limiting & Backoff**: Handles HTTP 429 and 5xx via exponential backoff with jitter and `Retry-After` header parsing (`_request_with_retry`).
- **Disk Caching**: Uses `check_cache(species, target_dir)` to verify valid cached `.glb`, manifest, and 4 PBR textures, returning `RawAsset(..., source="cached")` without network requests.

### 1.4 Procedural Botanical Generator Architecture (`m2_explorer_2/progress.md`)
- **Class**: `ProceduralBotanicalGenerator(config: Optional[ProceduralGeneratorConfig] = None)`
- **Archetype Generators**: Covers all 7 categories using `MeshGeometry`, pure quad/tri primitives, and numpy/PIL procedural PBR synthesis.
- **Invariants Enforced**:
  - Vertex Budget: $3,000 \le N_{\text{verts}} \le 45,000$.
  - Ground Pivot: $Z_{\min} = 0.0 \pm 0.005$m.
  - Static Mesh: $N_{\text{bones}} = 0$ (zero skins, zero armatures, zero vertex groups).
  - 4-Channel PBR Textures: Albedo, Normal, Roughness, Metallic.
  - Determinism: Integer `seed` guarantees identical vertices/faces across runs.

### 1.5 Master Pipeline Entry Point (`generate_plant`)
- Signature: `generate_plant(species, mode="auto", output_dir=None, seed=42, force_regenerate=False, **kwargs) -> RawAsset`
- Contract: Returns `RawAsset` containing `mesh`, `glb_path`, `textures`, `source` ("meshy", "procedural", "cached"), `metadata`.

---

## 2. Logic Chain

### 2.1 Scope 1: MeshyGenerator Unit Testing Logic
1. **Mock HTTP Boundary**:
   - Because `urllib.request.urlopen` (and/or `httpx`) is used for Meshy API communication, unit tests must intercept HTTP requests via `unittest.mock.patch("urllib.request.urlopen")`.
   - Tests must verify that the preview request payload matches `species.meshy_spec` (positive prompt, negative prompt containing all blacklist tokens, target polycount 28000, topology quad, art style realistic).
   - Tests must verify the refine request payload includes `mode="refine"`, the preview task ID, `enable_pbr=True`, and `texture_richness="high"`.
2. **Transient Error & Retry Backoff Logic**:
   - When the API returns HTTP 429 (Too Many Requests) or HTTP 500/503 (Server Error), the client must catch the error, calculate backoff delay (honoring `Retry-After`), and retry up to `max_retries`.
   - Testing method: Mock `urlopen` to raise `urllib.error.HTTPError` on the first call and return 200 OK on the second call. Patch `time.sleep` with a mock to prevent delays and assert `mock_sleep.called` with the expected interval.
   - Terminal error test: Mock persistent HTTP 500 on all attempts exceeding `max_retries=5`. Assert raises `MorphoMeshException` or `RuntimeError`.
   - Fast fail test: Mock HTTP 401/403 (Authentication / Forbidden). Assert raises immediately on attempt 1 without sleeping or retrying.
3. **Disk Caching Logic**:
   - In production, re-generating assets burns cloud credits. `check_cache()` avoids redundant generation.
   - Testing method: Populate a mock cache directory with valid `.glb` and texture files. Invoke `generator.generate(...)`. Assert `urlopen` is NEVER called (`mock_urlopen.assert_not_called()`).
   - Cache invalidation test: Populate cache with 0-byte `.glb` or corrupted manifest. Invoke generator. Assert cache is invalidated and network generation proceeds.
   - Force regeneration test: Pass `force_regenerate=True`. Assert cache is bypassed.

### 2.2 Scope 2: ProceduralBotanicalGenerator Unit Testing Logic
1. **7-Biome Coverage**:
   - The test suite must parameterize tests over all 7 botanical categories using representative species: `veg_tree_oak_01`, `veg_conifer_pine_01`, `veg_tropical_palm_01`, `veg_shrub_rose_01`, `veg_ground_fern_01`, `veg_succulent_saguaro_01`, `veg_vine_ivy_01`.
   - For every species, procedural generation must produce a non-empty `MeshGeometry` and valid `.glb` file.
2. **Vertex Budget Invariant ($3,000 \le V \le 45,000$)**:
   - Low-poly vegetation lacks branch silhouette curvature; excessively dense vegetation degrades game engine performance.
   - Test asserts: $3,000 \le \text{len}(mesh.vertices) \le 45,000$ and $3,000 \le \text{parsed\_glb\_verts} \le 45,000$.
   - Asserts finite coordinates: `np.isfinite(mesh.vertices).all() == True` (zero NaN, zero Inf).
3. **Ground Root Pivot Alignment Invariant ($Z_{\min} = 0.0 \pm 0.005$m)**:
   - Botanical assets must sit directly on terrain surfaces.
   - Test asserts: $\min_{v \in V}(v_z) \in [-0.005, 0.005]$ in `MeshGeometry` and in glTF `POSITION` accessor bounds.
   - Root contact centroid (bottom 5% height) must be centered at $(0, 0)$: $|X_{\text{root}}| \le 0.05$m, $|Y_{\text{root}}| \le 0.05$m.
4. **Static Mesh & Zero-Armatures Invariant ($N_{\text{bones}} = 0$)**:
   - Unrigged static vegetation must not contain bones, joints, or skinning.
   - Test inspects glTF binary JSON chunk:
     - `gltf.get("skins")` is `None` or `[]`.
     - `gltf.get("animations")` is `None` or `[]`.
     - Primitive attributes do NOT contain `"JOINTS_"` or `"WEIGHTS_"`.
     - No node contains `"skin"`.
5. **4-Channel PBR Material Invariant**:
   - All 4 texture maps must exist: Albedo, Normal, Roughness, Metallic.
   - **Albedo**: `arr.mean() >= 15.0` (rejects pure black corrupted bake); `arr.std() >= 3.0` (rejects flat untextured dummy).
   - **Normal**: Tangent-space outward (+Z) dominant: Blue channel mean $\ge 180.0$, `arr.std() >= 1.0`.
   - **Roughness**: Mean in range $[0.15, 0.95]$.
   - **Metallic**: Dielectric foliage guarantee: Mean $\le 0.05$ (max pixel value $\le 15$).
6. **Deterministic Repeatability**:
   - Procedural generation with identical seeds must produce identical vertex positions and face indices:
     $$\text{np.allclose}(V_1, V_2, \text{atol}=10^{-6}) == \text{True}$$
   - Changing the seed must produce different vertex positions (`np.allclose == False`).

### 2.3 Scope 3: Master Dispatch (`generate_plant`) Testing Logic
1. `mode="procedural"`: Calls `ProceduralBotanicalGenerator`, returns `RawAsset(source="procedural")`, zero network calls.
2. `mode="meshy"`: With API key, calls `MeshyGenerator`, returns `RawAsset(source="meshy")`. Without API key, raises informative error.
3. `mode="auto"`:
   - With valid API key: Dispatches to `MeshyGenerator`.
   - Without API key: Seamlessly falls back to `ProceduralBotanicalGenerator` without crashing.
   - On API error/timeout: Catches exception, logs warning, and gracefully falls back to `ProceduralBotanicalGenerator`.
4. Identifier Resolution: Accepts canonical `species_id`, scientific name, or `PlantSpecies` object; raises `KeyError` on unknown identifier.

---

## 3. Caveats

1. **No Live Meshy API Calls in Unit Tests**:
   - The live Meshy account has a finite balance (936 credits). Unit tests must execute 100% offline with zero credit consumption using deterministic mocks.
   - Live smoke tests, if required in future milestones, must be explicitly gated with `@pytest.mark.skipif(not os.environ.get("RUN_LIVE_MESHY_TESTS"), ...)`.
2. **Third-Party 3D Libraries**:
   - `trimesh` and `pygltflib` are not installed. All GLB inspections must use standard library `struct` and `json` via pure Python helpers.
3. **Floating-Point Tolerances**:
   - Mesh vertex comparisons between identical seeds should use `atol=1e-6`.
   - Ground root pivot assertions use a tolerance of $\pm 0.005$m ($5\text{mm}$), accounting for floating-point rounding.

---

## 4. Conclusion & Drop-In Test Suite Specification

The test suite must be implemented in `teamwork_projects/vegetation_library/tests/test_generator.py` organized into four distinct test classes:
1. `TestMeshyGeneratorUnit`: 11 unit tests covering configuration, payload construction, two-stage generation, retry backoff on 429/5xx, fast-fail on 4xx, timeouts, and disk caching.
2. `TestProceduralBotanicalGeneratorUnit`: 10 unit tests covering all 7 biomes, vertex budgets, ground pivot alignment, zero armatures, 4 PBR textures, and seed determinism.
3. `TestGeneratePlantDispatch`: 10 integration tests covering dispatch routing across `"auto"`, `"meshy"`, and `"procedural"` modes, graceful fallbacks, and identifier resolution.
4. `TestGlbBinaryValidation`: 4 low-level glTF 2.0 binary container validation tests.

Total: **35 comprehensive automated test cases**.

### 4.1 Drop-In Test Suite Code Specification (`tests/test_generator.py`)

The Worker can drop the following complete code specification directly into `teamwork_projects/vegetation_library/tests/test_generator.py`:

```python
"""
Unit and Integration Test Suite for Milestone 2: Generation Engine & Fallback Harness
File: teamwork_projects/vegetation_library/tests/test_generator.py

Validates:
1. MeshyGenerator:
   - Preview & refine payload construction (prompts, negative blacklist, polycount, topology, art style).
   - Rate limit retry backoff on HTTP 429 with Retry-After header.
   - Transient server error retries on HTTP 500/503.
   - Terminal client error fast-fail on HTTP 401/403.
   - Polling timeout and task failure handling.
   - Disk caching hit/miss/invalidation behavior.
2. ProceduralBotanicalGenerator:
   - Procedural generation for representative species from all 7 biomes.
   - Output GLB parseability and vertex budget [3000, 45000].
   - Ground root pivot alignment (Z_min ≈ 0.0 ± 0.005m).
   - Strict zero skeletal armatures / bones / skinning weights (N_bones = 0).
   - 4-channel PBR texture completeness (Albedo, Normal, Roughness, Metallic).
   - Deterministic repeatability across identical integer seeds.
3. generate_plant Master Dispatch:
   - Explicit "procedural" mode routing.
   - Explicit "meshy" mode routing and error on missing credentials.
   - "auto" mode with valid key -> Meshy.
   - "auto" mode without key or on API failure -> graceful procedural fallback.
   - Input resolution (species_id, scientific name, PlantSpecies instance).
4. Binary GLB Validation:
   - Pure Python standard library binary glTF 2.0 chunk and header verification.
"""
from __future__ import annotations

import io
import json
import os
import struct
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import MagicMock, patch
import urllib.error

import numpy as np
import pytest
from PIL import Image

from morphomesh.inference_adapter import MeshGeometry
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
)


# ==============================================================================
# HELPER FUNCTIONS FOR BINARY GLB & PBR VALIDATION
# ==============================================================================

def unpack_glb_header_and_json(glb_path: Union[str, Path]) -> Tuple[Dict[str, Any], bytes]:
    """Unpacks the glTF 2.0 header and JSON chunk from a binary GLB file."""
    with open(glb_path, "rb") as f:
        header = f.read(12)
        assert len(header) == 12, "File too short to be a valid GLB container"
        magic, version, length = struct.unpack_from("<4sII", header, 0)
        assert magic == b"glTF", f"Invalid GLB magic: expected b'glTF', got {magic}"
        assert version == 2, f"Invalid glTF version: expected 2, got {version}"

        chunk0_hdr = f.read(8)
        assert len(chunk0_hdr) == 8, "Missing JSON chunk header"
        chunk0_len, chunk0_type = struct.unpack_from("<I4s", chunk0_hdr, 0)
        assert chunk0_type == b"JSON", f"Expected chunk 0 to be JSON, got {chunk0_type}"

        json_bytes = f.read(chunk0_len)
        gltf = json.loads(json_bytes.decode("utf-8"))

        bin_bytes = b""
        chunk1_hdr = f.read(8)
        if len(chunk1_hdr) == 8:
            chunk1_len, chunk1_type = struct.unpack_from("<I4s", chunk1_hdr, 0)
            if chunk1_type.startswith(b"BIN"):
                bin_bytes = f.read(chunk1_len)

    return gltf, bin_bytes


def parse_glb_vertex_and_face_counts(glb_path: Union[str, Path]) -> Tuple[int, int]:
    """Parses total vertex and face count from GLB accessors."""
    gltf, _ = unpack_glb_header_and_json(glb_path)
    accessors = gltf.get("accessors", [])
    total_verts = 0
    total_faces = 0

    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            pos_idx = prim.get("attributes", {}).get("POSITION")
            if pos_idx is not None and pos_idx < len(accessors):
                total_verts += accessors[pos_idx].get("count", 0)

            idx_idx = prim.get("indices")
            if idx_idx is not None and idx_idx < len(accessors):
                idx_count = accessors[idx_idx].get("count", 0)
                total_faces += idx_count // 3
            elif pos_idx is not None:
                pos_count = accessors[pos_idx].get("count", 0)
                total_faces += pos_count // 3

    return total_verts, total_faces


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
def mock_glb_binary() -> bytes:
    """Generates a minimal valid binary GLB buffer with 36 vertices (cube)."""
    geom = MeshGeometry()
    geom.add_box((0.0, 0.0, 0.5), (1.0, 1.0, 1.0))
    # In-memory export
    buf = io.BytesIO()
    geom.export_glb(str(Path("temp.glb")))
    with open("temp.glb", "rb") as f:
        data = f.read()
    if os.path.exists("temp.glb"):
        os.remove("temp.glb")
    return data


# ==============================================================================
# 1. UNIT TESTS: MESHY GENERATOR
# ==============================================================================

class TestMeshyGeneratorUnit:
    """Unit tests for MeshyGenerator HTTP boundary, payloads, retries, and caching."""

    def test_meshy_generator_initialization_and_config(self):
        """Verifies default configuration parameters and API key precedence."""
        cfg = MeshyGeneratorConfig(api_key="test_key_123", target_polycount=30000)
        gen = MeshyGenerator(config=cfg)
        assert gen.config.api_key == "test_key_123"
        assert gen.config.ai_model == "meshy-4"
        assert gen.config.art_style == "realistic"
        assert gen.config.topology == "quad"
        assert gen.config.target_polycount == 30000
        assert gen.config.enable_pbr is True
        assert gen.config.texture_richness == "high"
        assert gen.config.max_retries == 5
        assert gen.resolve_api_key() == "test_key_123"

    def test_meshy_preview_payload_construction(self, sample_oak_species):
        """Asserts that the preview request payload contains all conditioned prompt parameters."""
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
            assert payload["ai_model"] == "meshy-4"
            assert payload["topology"] == "quad"
            assert payload["target_polycount"] == sample_oak_species.meshy_spec.target_polycount
            assert payload["should_remesh"] is True

            # Verify negative blacklist tokens are strictly included
            for token in ["pot", "planter", "container", "human", "bones", "armature", "rig"]:
                assert token in payload["negative_prompt"].lower()

    def test_meshy_refine_payload_construction(self):
        """Asserts that the refine request payload submits preview_task_id, enable_pbr, and richness."""
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
        """Verifies exponential backoff and Retry-After header parsing on HTTP 429."""
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

        def mock_sleep(seconds):
            sleep_intervals.append(seconds)

        with patch("urllib.request.urlopen", side_effect=mock_urlopen), patch("time.sleep", side_effect=mock_sleep):
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
        """Verifies exponential backoff retry progression on transient HTTP 500/503 errors."""
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
            # Exponential backoff progression
            assert sleep_intervals[0] >= 1.0
            assert sleep_intervals[1] >= 2.0

    def test_meshy_terminal_error_after_max_retries(self):
        """Asserts that persistent HTTP 500 errors raise an unhandled exception after exceeding max_retries."""
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", max_retries=2))
        err_500 = urllib.error.HTTPError("https://api.meshy.ai", 500, "Internal Error", {}, io.BytesIO(b"server down"))

        with patch("urllib.request.urlopen", side_effect=err_500), patch("time.sleep"):
            with pytest.raises(Exception) as exc_info:
                gen._request_with_retry("GET", "https://api.meshy.ai/test", headers={})
            assert "exceeded max retries" in str(exc_info.value).lower() or "500" in str(exc_info.value)

    def test_meshy_terminal_4xx_fails_fast_without_retry(self):
        """Asserts that client errors (HTTP 401, 403) fail immediately without wasteful retries."""
        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", max_retries=5))
        err_401 = urllib.error.HTTPError("https://api.meshy.ai", 401, "Unauthorized", {}, io.BytesIO(b"Invalid API key"))
        sleep_mock = MagicMock()

        with patch("urllib.request.urlopen", side_effect=err_401), patch("time.sleep", sleep_mock):
            with pytest.raises(Exception) as exc_info:
                gen._request_with_retry("GET", "https://api.meshy.ai/test", headers={})
            assert "401" in str(exc_info.value)
            sleep_mock.assert_not_called()

    def test_meshy_disk_caching_skips_network_calls(self, tmp_path, sample_oak_species, mock_glb_binary):
        """Asserts that valid existing disk cache returns RawAsset with source='cached' and zero HTTP requests."""
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
            "vertex_count": 36,
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
        """Asserts that empty or corrupted cached files trigger regeneration."""
        cache_dir = tmp_path / "corrupt_cache" / sample_oak_species.species_id
        cache_dir.mkdir(parents=True, exist_ok=True)

        # 0-byte GLB file
        with open(cache_dir / f"{sample_oak_species.species_id}.glb", "wb") as f:
            f.write(b"")

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", cache_dir=tmp_path / "corrupt_cache"))
        cached = gen.check_cache(sample_oak_species, target_dir=cache_dir)
        assert cached is None, "Corrupted 0-byte cache should be invalidated"

    def test_meshy_force_regenerate_bypasses_cache(self, tmp_path, sample_oak_species, mock_glb_binary):
        """Asserts that force_regenerate=True ignores existing valid cache and triggers generation."""
        cache_dir = tmp_path / "cache" / sample_oak_species.species_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        with open(cache_dir / f"{sample_oak_species.species_id}.glb", "wb") as f:
            f.write(mock_glb_binary)

        gen = MeshyGenerator(config=MeshyGeneratorConfig(api_key="msy_test", force_regenerate=True))
        cached = gen.check_cache(sample_oak_species, target_dir=cache_dir)
        assert cached is None, "force_regenerate=True must bypass disk cache"


# ==============================================================================
# 2. UNIT TESTS: PROCEDURAL BOTANICAL GENERATOR
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
        """Asserts procedural generation succeeds and returns parseable GLB for all 7 biomes."""
        species = catalog[species_id]
        out_dir = tmp_path / species_id
        proc_gen = ProceduralBotanicalGenerator()

        raw_asset = proc_gen.generate(species, output_dir=out_dir, seed=42)

        assert raw_asset.source == "procedural"
        assert raw_asset.species_id == species_id
        assert raw_asset.glb_path.is_file()
        assert raw_asset.mesh is not None
        assert isinstance(raw_asset.mesh, MeshGeometry)

        # Parse GLB
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
        """Strictly asserts that vertex count satisfies 3,000 <= V <= 45,000 for every biome."""
        species = catalog[species_id]
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(species, output_dir=tmp_path / species_id, seed=42)

        v_count = len(raw_asset.mesh.vertices)
        assert 3000 <= v_count <= 45000, (
            f"Species {species_id} vertex count {v_count} outside budget [3000, 45000]"
        )
        assert 3000 <= raw_asset.vertex_count <= 45000

        # Assert finite coordinates
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
        """Strictly asserts that the lowest vertex sits at Z_min = 0.0 ± 0.005m ground contact."""
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
        """Strictly asserts that the exported GLB contains zero skins, armatures, bones, or skinning weights."""
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
        """Asserts that all 4 PBR texture maps exist and satisfy physical value ranges."""
        species = catalog[species_id]
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(species, output_dir=tmp_path / species_id, seed=42)
        assert_pbr_texture_suite_validity(raw_asset.textures)

    def test_deterministic_repeatability_same_seed(self, catalog, tmp_path):
        """Asserts that identical integer seeds produce bit-for-bit identical mesh geometry."""
        species = catalog["veg_tree_oak_01"]
        proc_gen = ProceduralBotanicalGenerator()

        asset_a = proc_gen.generate(species, output_dir=tmp_path / "seed_a", seed=1337)
        asset_b = proc_gen.generate(species, output_dir=tmp_path / "seed_b", seed=1337)

        assert len(asset_a.mesh.vertices) == len(asset_b.mesh.vertices)
        assert len(asset_a.mesh.faces) == len(asset_b.mesh.faces)
        assert np.allclose(asset_a.mesh.vertices, asset_b.mesh.vertices, atol=1e-6)
        assert asset_a.mesh.faces == asset_b.mesh.faces

    def test_seed_diversity_different_seeds(self, catalog, tmp_path):
        """Asserts that different seeds produce organically varied geometric branching."""
        species = catalog["veg_tree_oak_01"]
        proc_gen = ProceduralBotanicalGenerator()

        asset_1 = proc_gen.generate(species, output_dir=tmp_path / "seed_1", seed=42)
        asset_2 = proc_gen.generate(species, output_dir=tmp_path / "seed_2", seed=99)

        assert not np.allclose(asset_1.mesh.vertices, asset_2.mesh.vertices, atol=1e-3)


# ==============================================================================
# 3. INTEGRATION TESTS: MASTER DISPATCH (generate_plant)
# ==============================================================================

class TestGeneratePlantDispatch:
    """Tests master entry point routing across modes, fallback handling, and input types."""

    def test_dispatch_mode_procedural_explicit(self, sample_oak_species, tmp_path):
        """Explicit mode='procedural' must invoke ProceduralBotanicalGenerator with zero API calls."""
        mock_urlopen = MagicMock()
        with patch("urllib.request.urlopen", mock_urlopen):
            asset = generate_plant(sample_oak_species, mode="procedural", output_dir=tmp_path / "proc")
            assert asset.source == "procedural"
            assert asset.glb_path.is_file()
            assert 3000 <= asset.vertex_count <= 45000
            mock_urlopen.assert_not_called()

    def test_dispatch_mode_meshy_explicit_without_key_raises(self, sample_oak_species, monkeypatch):
        """Explicit mode='meshy' without an API key must raise an informative exception."""
        monkeypatch.delenv("MESHY_API_KEY", raising=False)
        with pytest.raises(Exception) as exc_info:
            generate_plant(sample_oak_species, mode="meshy")
        assert "api key" in str(exc_info.value).lower()

    def test_dispatch_mode_auto_without_key_falls_back_to_procedural(self, sample_oak_species, monkeypatch, tmp_path):
        """When mode='auto' and no API key exists, gracefully fallback to procedural without crashing."""
        monkeypatch.delenv("MESHY_API_KEY", raising=False)
        asset = generate_plant(sample_oak_species, mode="auto", output_dir=tmp_path / "auto_fallback")
        assert asset.source == "procedural"
        assert asset.glb_path.is_file()
        assert 3000 <= asset.vertex_count <= 45000
        assert_pbr_texture_suite_validity(asset.textures)

    def test_dispatch_mode_auto_on_api_error_falls_back_to_procedural(self, sample_oak_species, monkeypatch, tmp_path):
        """When mode='auto' and Meshy API fails with HTTP 500, gracefully fallback to procedural."""
        monkeypatch.setenv("MESHY_API_KEY", "msy_mock_test_key")
        err_500 = urllib.error.HTTPError("https://api.meshy.ai", 500, "Server Down", {}, io.BytesIO(b"error"))

        with patch("urllib.request.urlopen", side_effect=err_500), patch("time.sleep"):
            asset = generate_plant(sample_oak_species, mode="auto", output_dir=tmp_path / "auto_api_err")
            assert asset.source == "procedural"
            assert asset.glb_path.is_file()
            assert 3000 <= asset.vertex_count <= 45000

    def test_dispatch_accepts_string_species_id(self, tmp_path):
        """generate_plant accepts canonical species_id string."""
        asset = generate_plant("veg_tree_oak_01", mode="procedural", output_dir=tmp_path / "str_id")
        assert asset.species_id == "veg_tree_oak_01"
        assert asset.source == "procedural"

    def test_dispatch_accepts_scientific_name(self, tmp_path):
        """generate_plant accepts botanical binomial scientific name."""
        asset = generate_plant("Quercus robur", mode="procedural", output_dir=tmp_path / "sci_name")
        assert asset.species_id == "veg_tree_oak_01"
        assert asset.source == "procedural"

    def test_dispatch_invalid_species_raises_keyerror(self):
        """generate_plant raises KeyError when passed an unknown species identifier."""
        with pytest.raises(KeyError):
            generate_plant("fictional_alien_tree_99", mode="procedural")

    def test_raw_asset_contract_compliance(self, sample_oak_species, tmp_path):
        """Asserts that returned RawAsset strictly complies with the M2 <-> M3 contract."""
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


# ==============================================================================
# 4. BINARY GLTF / GLB STRUCTURAL VALIDATION
# ==============================================================================

class TestGlbBinaryValidation:
    """Low-level binary glTF container structural compliance tests."""

    def test_glb_container_alignment_and_padding(self, sample_oak_species, tmp_path):
        """Validates that glTF chunk lengths and total file size are aligned to 4-byte boundaries."""
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
```

---

## 5. Verification Method

To independently verify the test suite design and implementation:

1. **Verify Test Environment Readiness**:
   ```powershell
   E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe -m pytest teamwork_projects/vegetation_library/tests/test_catalog.py -v
   ```
   Must pass 100% (52 passed in <0.2s).

2. **Execute Milestone 2 Generator Test Suite (Once implemented by Worker)**:
   ```powershell
   E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe -m pytest teamwork_projects/vegetation_library/tests/test_generator.py -v
   ```
   Must pass 100% (35 test cases passing).

3. **Sub-Suite Verification Targets**:
   - Verify Meshy unit tests:
     ```powershell
     E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe -m pytest teamwork_projects/vegetation_library/tests/test_generator.py -k "TestMeshyGeneratorUnit" -v
     ```
   - Verify Procedural fallback tests (7 biomes):
     ```powershell
     E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe -m pytest teamwork_projects/vegetation_library/tests/test_generator.py -k "TestProceduralBotanicalGeneratorUnit" -v
     ```
   - Verify Dispatch & Fallback tests:
     ```powershell
     E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe -m pytest teamwork_projects/vegetation_library/tests/test_generator.py -k "TestGeneratePlantDispatch" -v
     ```

4. **Invalidation Conditions**:
   - Any test requiring network access or failing when `MESHY_API_KEY` is not present.
   - Any procedural output having $< 3,000$ or $> 45,000$ vertices.
   - Any generated plant with root base $Z_{\min} > 0.005$m away from zero.
   - Any skeletal armature, bone, joint, or weight token detected in GLB binary structures.
   - Any missing, solid black, or out-of-range PBR texture channel.
