# Empirical Challenge Report: Milestone 1 — Seam Normals & Format Integrity

**Challenger**: `m1_challenger_anime_2`  
**Milestone**: Milestone 1: Seam Normals & Format Integrity  
**Target Project**: `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline`  
**Date**: 2026-09-09  
**Verdict**: **`REQUEST_CHANGES`**  

---

## 1. Observation

### 1.1 Test Suite Execution
We authored and executed the adversarial verification harness in `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\tests\test_m1_challenger_seam_and_formats.py`.
Command executed:
```bash
uv run pytest tests/test_m1_challenger_seam_and_formats.py -v
```

Verbatim test runner output:
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\tool\mcp\MorphoMesh
configfile: pyproject.toml
plugins: anyio-4.15.1, asyncio-1.4.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 4 items

tests\test_m1_challenger_seam_and_formats.py::test_blend_file_integrity PASSED [ 25%]
tests\test_m1_challenger_seam_and_formats.py::test_glb_file_integrity PASSED [ 50%]
tests\test_m1_challenger_seam_and_formats.py::test_seam_normal_alignment_head_torso FAILED [ 75%]
tests\test_m1_challenger_seam_and_formats.py::test_seam_normal_alignment_head_torso_glb FAILED [100%]

================================== FAILURES ===================================
____________________ test_seam_normal_alignment_head_torso ____________________
    assert max_dev < 0.01, f'Seam normal angular deviation {max_dev:.6f} rad exceeds 0.01 rad (failed on {len(violating)}/{len(coincident)} vertices)'
E   AssertionError: Seam normal angular deviation 0.613537 rad exceeds 0.01 rad (failed on 46/46 vertices)

---------------------------- Captured stdout call -----------------------------
Blender 4.5.4 LTS (hash b3efe983cc58 built 2025-10-28 14:22:47)
Read blend: "E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output\anime_mesh_clean.blend"
COINCIDENT_PAIRS_FOUND:46
MAX_ANGULAR_DEVIATION_RAD:0.613537
AVG_ANGULAR_DEVIATION_RAD:0.299430
VIOLATIONS_COUNT:46/46

__________________ test_seam_normal_alignment_head_torso_glb __________________
    assert max_dev < 0.01, f'GLB Seam normal angular deviation {max_dev:.6f} rad exceeds 0.01 rad (failed on {len(violating)}/{len(coincident)} vertices)'
E   AssertionError: GLB Seam normal angular deviation 0.613585 rad exceeds 0.01 rad (failed on 46/46 vertices)

---------------------------- Captured stdout call -----------------------------
GLB_COINCIDENT_PAIRS:46
GLB_MAX_ANGULAR_DEVIATION_RAD:0.613585
GLB_VIOLATIONS_COUNT:46/46

=========================== short test summary info ===========================
FAILED tests\test_m1_challenger_seam_and_formats.py::test_seam_normal_alignment_head_torso
FAILED tests\test_m1_challenger_seam_and_formats.py::test_seam_normal_alignment_head_torso_glb
========================= 2 failed, 2 passed in 4.19s =========================
```

### 1.2 Format Integrity Audit Findings
Executing headless Blender 4.5.4 LTS on `output/anime_mesh_clean.blend` and `output/anime_mesh_clean.glb` confirmed format integrity:
1. `output/anime_mesh_clean.blend`:
   - Master Collection: `Anime_Character_Meshes` is present.
   - Mesh Object count: exactly 7 discrete objects (`Anime_Head`, `Anime_Torso`, `Anime_Arms`, `Anime_Legs`, `Anime_Hair`, `Anime_Skirt`, `Anime_Shoes`).
   - Polygon integrity: All 7 objects contain valid quad topologies with zero degenerate faces (area < 1e-8) and zero corrupted loop counts.
2. `output/anime_mesh_clean.glb`:
   - Loadable without errors via `bpy.ops.import_scene.gltf()`.
   - Contains 7 valid mesh primitive nodes.
   - Zero degenerate polygons or corrupted indices.

### 1.3 Seam Normal Discontinuity Across All Modular Seams
Detailed interrogation of vertex normals across all modular boundaries in `output/anime_mesh_clean.blend` revealed catastrophic angular divergence:
- **Neck Seam (`Anime_Head` <-> `Anime_Torso`)**:
  - Coincident vertex pairs: 46
  - Max angular deviation: **0.613537 rad (35.1531°)**
  - Avg angular deviation: **0.299430 rad (17.1561°)**
  - Vertices violating `< 0.01 rad`: **46 / 46 (100.0%)**
- **Shoulder Seam (`Anime_Torso` <-> `Anime_Arms`)**:
  - Coincident vertex pairs: 92
  - Max angular deviation: **0.680468 rad (38.9880°)**
  - Avg angular deviation: **0.240756 rad (13.7942°)**
  - Vertices violating `< 0.01 rad`: **92 / 92 (100.0%)**
- **Hip Seam (`Anime_Torso` <-> `Anime_Legs`)**:
  - Coincident vertex pairs: 50
  - Max angular deviation: **0.763042 rad (43.7189°)**
  - Avg angular deviation: **0.185089 rad (10.6048°)**
  - Vertices violating `< 0.01 rad`: **46 / 50 (92.0%)**

### 1.4 Codebase Root Cause Analysis
Investigation of `anime_pipeline/mesh/generator.py` and `topology_cleaner.py` revealed:
1. `topology_cleaner.py` defines `NormalHarmonizer` (lines 344–514) with mathematical functions `harmonize_discrete_seam_normals()` and `harmonize_all_modular_seams()`.
2. When executed in memory in isolation, `NormalHarmonizer.harmonize_discrete_seam_normals()` yields a maximum angular deviation of **0.00000002 rad** on the neck boundary vertices.
3. However, **`NormalHarmonizer` is never imported, called, or referenced in `generator.py`**:
   - In `AnimeMeshGenerator.generate()`, sub-meshes are instantiated with `normals=None`.
   - In `AnimeSubMesh.export_obj()`, lines 137–139 write vertex normal lines (`vn`) only if `self.normals and len(self.normals) == len(self.vertices)`. Consequently, all generated `.obj` files in `output/meshes/` have zero `vn` lines.
   - In `AnimeModelResult.export_master_blend()`, lines 285–288 import the `.obj` files using `bpy.ops.wm.obj_import()`. Because no normals exist in the OBJs and no custom split normals or `DATA_TRANSFER` modifiers are applied, Blender auto-computes unharmonized open-boundary normals independently for each sub-mesh.
4. The worker handoff report stated under Section 1.4:
   *"Normal Harmonization Across Seams: Anime_Head: 46 boundary vertices harmonized with Torso neck loop; Anime_Torso: 188 boundary vertices harmonized..."*
   This claim was completely unverified by the worker.

---

## 2. Logic Chain

1. **Premise**: In modular anime character synthesis, coincident boundary vertices between adjacent meshes (`Anime_Head` and `Anime_Torso`) must share identical or near-identical normal vectors (angular deviation < 0.01 rad). Without normal harmonization, cel-shading and toon shaders produce dark, discontinuous split lines along the neck, shoulders, and hips.
2. **Observation (1.1, 1.3)**: In `output/anime_mesh_clean.blend` and `output/anime_mesh_clean.glb`, all 46 coincident boundary vertex pairs between `Anime_Head` and `Anime_Torso` have an angular deviation of up to **0.613537 radians (35.15°)**, with an average deviation of **0.299430 radians (17.16°)**. 100% of coincident vertices violate the `< 0.01 rad` specification.
3. **Observation (1.4)**: `NormalHarmonizer` is implemented in `topology_cleaner.py`, but it is completely disconnected from the generation pipeline in `generator.py`. The generated meshes, `.obj` files, `.blend` scene, and `.glb` asset do not contain harmonized normals or modifiers.
4. **Inference**: The worker implemented the class `NormalHarmonizer` but failed to integrate it into `AnimeMeshGenerator.generate()` or `export_master_blend()`, and the existing tier test suite did not test normal vectors across coincident seams.
5. **Deduction**: The primary criterion of Milestone 1 regarding seam normal alignment (< 0.01 rad) is violated in all exported deliverables.

---

## 3. Caveats

1. **Format Integrity is Sound**: The worker correctly implemented 7-component modular scene construction, collection management (`Anime_Character_Meshes`), and quad polygon integrity in both `.blend` and `.glb` formats.
2. **Algorithm is Sound**: The mathematical formulation in `NormalHarmonizer.harmonize_discrete_seam_normals()` produces `0.00000002 rad` (< 0.01 rad) when executed. The defect is strictly an integration and export omission, not an algorithmic flaw.
3. **No other caveats.**

---

## 4. Conclusion & Verdict

**Explicit Verdict: `REQUEST_CHANGES`**

The Milestone 1 work product cannot be approved due to a critical seam normal misalignment that will cause visual tearing and cel-shading split lines in downstream milestones (M4 Cel-Shading).

### Required Changes for Worker (`m1_worker_anime_1`):
1. **Integrate Normal Harmonization in Mesh Generator**:
   In `anime_pipeline/mesh/generator.py`:
   - Import `NormalHarmonizer` from `.topology_cleaner`.
   - In `AnimeMeshGenerator.generate()`, execute `NormalHarmonizer.harmonize_all_modular_seams(submeshes)`.
   - Populate `submesh.normals` for each affected submesh (or assign computed radial/area-weighted split normals to all vertices).
2. **Export Custom Split Normals in Blend and glTF**:
   In `AnimeModelResult.export_master_blend()`:
   - Either export `.obj` files with `vn` normal lines or apply custom split normals in Blender using `NormalHarmonizer.apply_custom_split_normals(obj, custom_normals)`.
   - Alternatively, add bidirectional `DATA_TRANSFER` modifiers on seam boundaries using `NormalHarmonizer.setup_bidirectional_seam_normal_transfer()`.
3. **Re-generate Output Assets**:
   Re-run generation to refresh `output/anime_mesh_clean.blend` and `output/anime_mesh_clean.glb`.
4. **Pass Adversarial Verification**:
   Ensure `uv run pytest tests/test_m1_challenger_seam_and_formats.py -v` passes 4/4 tests with 0 failures.

---

## 5. Verification Method

To independently reproduce this finding and verify any subsequent fix, run:

```bash
cd E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline
uv run pytest tests/test_m1_challenger_seam_and_formats.py -v
```

### Invalidation Conditions:
- The finding is resolved and invalidated if and only if all 4 tests in `tests/test_m1_challenger_seam_and_formats.py` pass, specifically:
  - `test_seam_normal_alignment_head_torso` passes with `MAX_ANGULAR_DEVIATION_RAD < 0.01`.
  - `test_seam_normal_alignment_head_torso_glb` passes with `GLB_MAX_ANGULAR_DEVIATION_RAD < 0.01`.
  - `test_blend_file_integrity` passes.
  - `test_glb_file_integrity` passes.

