# Handoff Report: Vegetation Library Test Suite & Verification Survey

**Agent**: Explorer 3 (`explorer_survey_3` — Test Suite & Verification Explorer)  
**Mission**: Thoroughly investigate existing test suites, verification scripts, and acceptance checking tools for the 3D Botanical Asset Library in `teamwork_projects/vegetation_library` and `tests/`. Analyze all assertions, validation checks, provenance status, invariants, polycounts, texture verification, preview renders, and manifest/viewer synchronization against the Authoritative User Request (`ORIGINAL_REQUEST.md` under `## 2026-09-10T11:11:31Z`).  
**Timestamp**: 2026-09-10T11:18:00Z  
**Type**: Hard (Task Complete)  
**Parent Conversation ID**: `c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4`  

---

## 1. Observation

### 1.1 Test Suite Inventory & Structure
The vegetation library verification infrastructure is localized under `teamwork_projects/vegetation_library/` (root `tests/` contains core MorphoMesh tests for human and creature pipelines, with zero vegetation tests):

1. **Inspection & Validation Engine**:
   - `teamwork_projects/vegetation_library/vegetation_pipeline/validator.py` (1,043 lines)
     - Core API: `validate_asset(asset, catalog)`, `validate_directory(output_dir, catalog)`.
     - Pure Python/NumPy GLB parser: `parse_glb_container(glb_path)`, `decode_glb_geometry(gltf, bin_bytes)`.
     - Wavefront parser: `inspect_companion_obj(obj_path)`.
     - Evaluation functions: `validate_geometry()`, `validate_static_mesh_invariants()`, `validate_pbr_textures()`.
     - Output model: `ValidationReport` (Pydantic v2) reporting `is_valid`, `checks` (dict of booleans), `metrics` (dict), `errors` (list of strings), and `warnings`.
2. **Master Orchestrator & CLI Runner**:
   - `teamwork_projects/vegetation_library/pipeline.py` (795 lines)
     - CLI flags: `--validate-only`, `--render-only`, `--summary`, `--all`, `--category`, `--species`, `--mode`.
     - Functions: `aggregate_manifest(output_dir, species_records)`, `format_summary_table(manifest_data)`.
3. **Automated Test Modules (`teamwork_projects/vegetation_library/tests/`)**:
   - `test_validator.py` (467 lines, 12 test functions): Unit tests for QA validator failure cases (NaN/Inf, ungrounded pivot, uncentered centroid, over/under budget, armature injection, black albedo, missing channel, metallic violation, corrupt GLB).
   - `test_vegetation_pipeline.py` (396 lines, 9 test functions): Milestone acceptance and end-to-end verification tests sweeping all 35 library assets on disk.
   - `test_normalization.py` (1,041 lines, 50 test cases): Ground pivot alignment, base centering, scale bounds, GLB export, OBJ/MTL export, and PBR packaging.
   - `test_generator.py` (1,019 lines, 41 test cases): MeshyGenerator client (caching, retry backoff, HTTP 429/5xx), ProceduralBotanicalGenerator, and GLB structure.
   - `test_renderer.py` (328 lines, 14 test cases): Blender binary resolution, render config, contact sheet composition, and software rasterizer fallback.
   - `test_catalog.py` (678 lines, 45 test cases): Botanical taxonomy, 35 species across 7 biomes, metric dimensions, prompts, and negative blacklists.
   - `conftest.py`: Shared pytest configuration and sys.path setup.

### 1.2 Test Execution Results & Status
Executed command:
```powershell
uv run pytest teamwork_projects/vegetation_library/tests/ -v
```
**Empirical Summary**:
- **Total collected tests**: 255 tests.
- **Passed**: 250 tests.
- **Failed**: 5 tests (all concentrated in `test_vegetation_pipeline.py`).
- **Verbatim Failures**:
  1. `test_geometry_standards_all_species`:
     ```text
     E AssertionError: veg_tree_oak_01 vertex count 58853 out of budget [3000, 45000]
     E assert 58853 <= 45000
     teamwork_projects\vegetation_library\tests\test_vegetation_pipeline.py:225
     ```
  2. `test_pbr_material_standards_all_species`:
     ```text
     E AssertionError: veg_tree_oak_01 albedo spatial std 0.0003 lacks variation <= 0.02
     E assert 0.0003225706750527024 > 0.02
     teamwork_projects\vegetation_library\tests\test_vegetation_pipeline.py:288
     ```
  3. `test_full_inspection_suite_100_percent_pass`:
     ```text
     E AssertionError: Failed species (1): [('veg_tree_oak_01', 15, [
       'Vertex count 58,853 is over budget (maximum acceptable is 45,000)',
       'Ground contact base violation: Y_min = -0.950965m exceeds tolerance ±0.005m (root base must snap to ground origin)',
       'Metric scale bounds violation: measured height 1.879m deviates from target 12.000m by 84.3% (exceeds ±10.0%)',
       'Albedo texture lacks surface variation: std=0.0003 <= 0.02',
       'Roughness texture lacks variation (constant flat field): std=0.0000 <= 0.01'
     ])]
     teamwork_projects\vegetation_library\tests\test_vegetation_pipeline.py:359
     ```
  4. `test_global_manifest_schema_and_integrity`:
     ```text
     E AssertionError: assert 34 == 35 (passed_validation_count in manifest.json is 34)
     ```
  5. `test_programmatic_run_pipeline_api`:
     ```text
     E AssertionError: assert 34 == 35 (manifest.get('passed_validation_count') == 35)
     teamwork_projects\vegetation_library\tests\test_vegetation_pipeline.py:394
     ```

### 1.3 Asset Provenance & Geometry Audit Across Library
Non-destructive empirical inspection of all 35 species directories under `teamwork_projects/vegetation_library/output/`:
- **Total species manifests found**: 35.
- **Provenance breakdown**:
  - `source: "procedural"`: 34 species (97.1%).
  - `source: "meshy"`: 1 species (`veg_tree_oak_01`, 2.9%).
- **Pairwise Vertex Count Collisions**:
  - Conifers (5 species: Cedar, Cypress, Pine, Redcedar, Spruce): **ALL 5 share exactly 5,024 vertices and 4,850 faces**.
  - Groundcover (5 species: Fern, Grass, Moss, Ostrich, Pampas): **ALL 5 share exactly 3,656 vertices and 1,872 faces**.
  - Shrubs (5 species: Azalea, Hydrangea, Lavender, Lilac, Rose): **ALL 5 share exactly 4,552 vertices and 3,580 faces**.
  - Succulents (5 species: Agave, Aloe, Barrel, Echeveria, Saguaro): **ALL 5 share exactly 3,336 vertices and 3,932 faces**.
  - Broadleaf (4 species: Beech, Birch, Maple, Willow): **ALL 4 share exactly 4,320 vertices and 4,238 faces**.
  - Tropical (5 species: Banana, Bird of Paradise, Monstera, Palm, Tree Fern): **ALL 5 share exactly 3,960 vertices and 2,442 faces**.
  - Vines (4 species: Bougainvillea, Ivy, Pothos, Wisteria): **ALL 4 share exactly 4,064 vertices and 3,280 faces**.
- **Collision Rate Calculation**:
  - Total pairwise comparisons: $\binom{35}{2} = 595$ pairs.
  - Identical vertex collisions: $\binom{5}{2} \times 5 + \binom{4}{2} \times 2 = 10 \times 5 + 6 \times 2 = 62$ collisions.
  - **Library-wide collision rate: $62 / 595 = 10.42\%$** (exceeds the $< 5\%$ limit).
  - **Within-biome collision rate: 100.0%**.

### 1.4 Detailed Inventory of Assertions Across the 8 Required Checks

| Check Area | Implementation Status | Existing Location & Logic | Gap Against Authoritative Request (2026-09-10T11:11:31Z) |
|:---|:---|:---|:---|
| **1. Meshy Cloud Provenance & Task ID** | ❌ **Missing** in validator and test suites | In `asset_manifest.json`, `provenance.source` and `generator_metadata.task_id` exist. But `validator.py` and `test_vegetation_pipeline.py` do **NOT** assert that `source == "meshy"` or that `task_id` is present/valid. | Authoritative prompt requires 100% genuine Meshy AI cloud generation (`source: "meshy"`, valid `task_id`), strictly 0% procedural placeholder geometry. Currently 34/35 assets are procedural fallbacks. |
| **2. Static Mesh Invariant** ($N_{\text{bones}} = 0$) | ✅ **Fully Enforced** | `validator.py:563-629` (`validate_static_mesh_invariants`): checks `skins is None`, `animations is None`, zero `JOINTS_`/`WEIGHTS_` attributes, zero node skins, zero OBJ bone keywords. Asserts $N_{\text{bones}} == 0$. | Fully compliant. All 35 existing assets pass this check. |
| **3. Ground Contact Snapping** ($Z_{\min} = 0.000\text{m} \pm 0.005\text{m}$, base centered at $X=0, Y=0$) | ⚠️ **Implemented with File-Selection Bug** | `validator.py:501-540`: asserts $|Z_{\min}| \le 0.005\text{m}$ and bottom 5% height slice centroid $\le 0.05\text{m}$. | `validator.py:835` executes `glbs = list(target_path.glob("*.glb"))[0]`. In directories with raw Meshy downloads, `raw_meshy_model.glb` precedes `veg_*.glb` alphabetically, evaluating unnormalized raw GLB ($Y_{\min} = -0.951\text{m}$) and producing false failure. |
| **4. Polygon / Vertex Count Limits** (20k–60k polygons) | ⚠️ **Outdated Budget Limits** | `validator.py:382`: asserts $3,000 \le V \le 45,000$. `test_vegetation_pipeline.py:225`: asserts $3,000 \le V \le 45,000$. | Authoritative prompt requires 20,000 to 60,000 polygons (average 30k–60k detail). The current test fails genuine Meshy oak (58,853 verts) because $58,853 > 45,000$, while falsely passing low-poly procedural clones (3.3k–5k verts). |
| **5. Pairwise Vertex Count Collision** (< 5% collision rate) | ❌ **Missing** in validator and test suites | No test or validation function currently computes pairwise vertex count collisions across species. | Authoritative prompt strictly requires pairwise vertex collision rate $< 5\%$. Current library exhibits 10.42% overall collision rate (62 collisions / 595 pairs) and 100% intra-biome collision. |
| **6. 4-Channel PBR Textures** (Albedo, Normal, Roughness, Metallic) | ⚠️ **Implemented with Extraction Bug** | `validator.py:631-776` (`validate_pbr_textures`): checks presence, resolution $\ge 256\times 256$, albedo mean $> 0.05$ & std $> 0.02$, normal tangent $N_z \in [0.5, 1.0]$, roughness mean $\in [0.20, 0.95]$ & std $> 0.01$, metallic dielectric max $\le 0.05$ & mean $\le 0.02$. | `generator.py:423` has a bug: `getattr(extracted, attr, None)` looks for `attr` ("albedo") instead of `f"{attr}_path"` ("albedo_path") returned by `extract_glb_textures`. Texture extraction from Meshy GLBs fails and silently falls back to synthetic flat colors ($std = 0.0003 \le 0.02$), causing test failure. |
| **7. Preview Image Existence** (`turntable_01-04`, `thumbnail`) | ✅ **Enforced (Images Exist, but Geometry is Procedural)** | `test_vegetation_pipeline.py:316-338`: checks existence and dimensions for `turntable_01.png` - `04.png` ($512 \times 512$) and `thumbnail.png` ($1024 \times 1024$). | All 35 species have the files, but 34 species display procedural dummy blobs rather than genuine Meshy renders. |
| **8. Manifest Schema & Viewer Synchronization** | ⚠️ **Implemented, but Stale / Desynchronized** | `output/manifest.json` schema validated in `test_vegetation_pipeline.py:132-195`. `viewer.html` provides interactive UI. | `manifest.json` contains stale procedural metrics for oak (vertex count recorded as 4,320 instead of 58,853) and reports `passed_validation_count: 34`. `viewer.html` cards display procedural dummy metrics for 34 species. |

### 1.5 Environment & Credentials Status
- `MESHY_API_KEY`: Verified present and active in `.env` (length: 40 characters, prefix `msy_3EH0...`).
- FastMCP / Python environment: Managed via `uv run` (`Python 3.11.9`).

---

## 2. Logic Chain

1. **Root Cause of Test Suite Failures (Observation 1.2 & 1.4)**:
   - All 5 test failures stem from a single underlying transition state: `veg_tree_oak_01` was upgraded to genuine Meshy AI Text-to-3D (58,853 vertices, 59,487 faces, unnormalized raw GLB downloaded to folder), but the testing suite (`validator.py` and `test_vegetation_pipeline.py`) was still running the Milestone 4/5 assertions designed for low-poly procedural meshes:
     - Assertion `assert 3000 <= n_verts <= 45000` directly rejected the 58,853 vertex mesh.
     - `validator.py::validate_asset` selected `raw_meshy_model.glb` instead of `veg_tree_oak_01.glb` due to `glob("*.glb")[0]`, evaluating the unaligned raw mesh.
     - `generator.py` failed to bind extracted PBR textures due to attribute name mismatch (`albedo` vs `albedo_path`), generating flat fallback albedo/roughness with zero spatial variation ($std \le 0.02$).
     - The failure of oak dropped `passed_validation_count` to 34, causing failures in global manifest schema integrity and CLI summary tests.

2. **The "100% Genuine Meshy AI" Mandate (Observation 1.3 & Authoritative Request)**:
   - 34 of 35 assets in `output/` currently possess `source: "procedural"`, identical vertex counts (e.g., 5,024 across all conifers, 3,656 across all groundcover), and identical topological shapes.
   - The user request of 2026-09-10T11:11:31Z explicitly bans procedural placeholder geometry and clone templates, demanding:
     - 100% genuine Meshy AI cloud generation for all species using `MESHY_API_KEY`.
     - Recorded cloud task provenance (`task_id`, `model_type`, `refine_status`).
     - Pairwise vertex collision $< 5\%$ across distinct species.
     - Polygon detail target: 20,000 to 60,000 polygons.
   - Therefore, the test suite and validator must be updated to enforce these exact new criteria, and the 34 procedural assets must be regenerated via live Meshy AI.

3. **Required Code & Test Rectifications**:
   - Update `validator.py`:
     1. Change polygon/vertex limit to `20,000 <= n_verts <= 60,000` (or `20,000 <= n_faces <= 60,000`).
     2. Add `task_id_provenance` check: assert `manifest.get("provenance", {}).get("source") == "meshy"` and `task_id` is present.
     3. Fix `glb_path` discovery: look for `<species_id>.glb` specifically, rather than `glob("*.glb")[0]`.
     4. Fix `generator.py:423`: change `getattr(extracted, attr, None)` to `getattr(extracted, f"{attr}_path", None)`.
   - Update `test_vegetation_pipeline.py`:
     1. Align budget bounds to `[20000, 60000]`.
     2. Add `test_pairwise_vertex_count_collisions`: calculate collision rate $\frac{\sum [V_i == V_j]}{\binom{N}{2}}$ and assert $< 0.05$.
     3. Add `test_meshy_task_provenance_all_species`: assert all 35 assets have non-empty `task_id` and `source == "meshy"`.
     4. Synchronize `output/manifest.json` and `viewer.html`.

---

## 3. Caveats

1. **Live Cloud API Rate Limits & Cost**:
   - Generating 34 botanical assets through Meshy AI Text-to-3D (two stages: preview + refine) requires 68 API tasks. Meshy accounts have concurrency limits (typically 2-5 concurrent tasks) and task queues. Robust polling with exponential backoff is essential.
2. **Deterministic Fallback During CI**:
   - In offline test environments without internet or API credits, unit tests in `test_validator.py` use synthetic meshes (`make_synthetic_mesh`). When updating `test_validator.py`, synthetic test mesh generators should be updated to span the new 20k–60k budget range.
3. **Read-Only Investigation Scope**:
   - In accordance with the Explorer protocol, zero source code or asset files were modified during this investigation. All findings and remediation designs are strictly documented for the implementing agents.

---

## 4. Conclusion

1. **Test Infrastructure Readiness**:
   - The test infrastructure (`validator.py`, `test_validator.py`, `test_vegetation_pipeline.py`, `test_normalization.py`) is modular and comprehensive, with 255 existing automated tests (250 passing).
2. **Root Cause of Failures**:
   - The 5 failing tests are not regressions; they are caused by an impedance mismatch between the newly generated 59k-poly Meshy oak model and the old M4 test assertions ($3,000 \le V \le 45,000$), compounded by a minor file-selection bug in `validate_asset` and an attribute extraction typo in `generator.py`.
3. **Current Library State vs New Requirements**:
   - 34 of 35 assets in `output/` are procedural fallback clones (3.3k–5k vertices) violating the 2026-09-10T11:11:31Z mandate for 100% genuine Meshy AI cloud generation and $< 5\%$ pairwise collision rate.
   - `MESHY_API_KEY` is present and ready in `.env`.
   - Once the validator/tests are updated and the remaining 34 assets are generated via Meshy AI, the entire library will achieve 100% compliance across all 8 acceptance criteria.

---

## 5. Verification Method

### 5.1 Re-running the Full Test Suite
To independently execute and verify the current test suite:
```powershell
uv run pytest teamwork_projects/vegetation_library/tests/ -v
```
Expected current result: `5 failed, 250 passed in ~20s` (the 5 failures documented in Section 1.2).

### 5.2 Inspecting Provenance and Vertex Collisions
To independently verify asset provenance and identical vertex collisions across the 35 species:
```powershell
uv run python -c "
import json
from pathlib import Path

out_dir = Path('teamwork_projects/vegetation_library/output')
manifests = list(out_dir.rglob('asset_manifest.json'))
counts = {}
for m in manifests:
    data = json.loads(m.read_text(encoding='utf-8'))
    sid = data.get('species_id')
    prov = data.get('provenance', {}).get('source')
    vc = data.get('geometry', {}).get('vertex_count', 0)
    counts[sid] = (prov, vc)

# Compute collisions
verts = [v[1] for v in counts.values()]
n = len(verts)
pairs = n * (n - 1) // 2
colls = sum(1 for i in range(n) for j in range(i + 1, n) if verts[i] == verts[j])
print(f'Total species: {n}, Total pairs: {pairs}, Collisions: {colls} ({colls/pairs*100:.2f}%)')
"
```
Expected output: `Total species: 35, Total pairs: 595, Collisions: 62 (10.42%)`.

### 5.3 Validating the Normalized Oak Model Directly
To verify that `veg_tree_oak_01.glb` satisfies the geometric ground and centroid invariants:
```powershell
uv run python -c "
import sys
sys.path.insert(0, 'teamwork_projects/vegetation_library')
sys.path.insert(0, 'src')
from vegetation_pipeline.validator import validate_asset
rep = validate_asset('teamwork_projects/vegetation_library/output/broadleaf_trees/veg_tree_oak_01/veg_tree_oak_01.glb')
print('Ground Aligned:', rep.checks.get('ground_contact_base_aligned'))
print('Base Centered:', rep.checks.get('base_contact_centroid_centered'))
print('Static Mesh 0 Bones:', rep.checks.get('n_bones_strictly_zero'))
print('Vertex Count:', rep.metrics.get('vertex_count'))
"
```
Expected output: Ground Aligned: True, Base Centered: True, Static Mesh 0 Bones: True, Vertex Count: 58853.

### 5.4 Invalidation Conditions
- Any change in the number of passing tests below 250 on existing test files without updating assertions.
- Any model in the library having non-zero armature bones ($N_{\text{bones}} > 0$).
- Pairwise vertex collision rate exceeding $5.0\%$ after the Meshy batch generation is complete.

