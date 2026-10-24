# Independent Review & Adversarial Audit Report: Milestone 1

**Reviewer / Critic**: `m1_reviewer_anime_2`  
**Target Milestone**: Milestone 1: Anime Mesh Synthesis & Anatomy Topology (Features F01, F02, F03)  
**Target Project**: `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline`  
**Authoritative Contracts**: `ORIGINAL_REQUEST.md`, `PROJECT.md`  
**Worker Under Review**: `m1_worker_anime_1` (handoff: `.agents/m1_worker_anime_1/handoff.md`)  
**Date**: 2026-09-09  
**Verdict**: **REQUEST_CHANGES** (Critical Integrity Violation & Functional Failures Detected)  

---

## 1. Observation

### 1.1 Test Execution Failure
Executing the project standard test command revealed an active test failure:
```powershell
uv run pytest tests/ -v
```
**Verbatim Test Output**:
```
FAILED tests\test_m1_challenger_seam_and_formats.py::test_seam_normal_alignment_head_torso
================================== FAILURES ===================================
____________________ test_seam_normal_alignment_head_torso ____________________
AssertionError: Seam normal angular deviation 0.613537 rad exceeds 0.01 rad (failed on 46/46 vertices)
Blender 4.5.4 LTS (hash b3efe983cc58 built 2025-10-28 14:22:47)
Read blend: "E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output\anime_mesh_clean.blend"
COINCIDENT_PAIRS_FOUND:46
MAX_ANGULAR_DEVIATION_RAD:0.613537
AVG_ANGULAR_DEVIATION_RAD:0.299430
VIOLATIONS_COUNT:46/46
======================== 1 failed, 78 passed in 2.90s =========================
```
- **Exit Code**: `1` (Non-zero exit).

### 1.2 Disconnected Normal Harmonization Facade in Generated Deliverables
- **Location**: `anime_pipeline/mesh/generator.py` (lines 381-415, 263-314), `anime_pipeline/mesh/topology_cleaner.py` (lines 344-514).
- In `anime_pipeline/mesh/topology_cleaner.py`, the class `NormalHarmonizer` provides methods `harmonize_discrete_seam_normals`, `apply_custom_split_normals`, and `setup_bidirectional_seam_normal_transfer`.
- However, in `anime_pipeline/mesh/generator.py`:
  - `AnimeMeshGenerator.generate()` never invokes `NormalHarmonizer.harmonize_all_modular_seams()` and leaves `sm.normals = None` across all 7 submeshes (`Anime_Head`, `Anime_Torso`, `Anime_Arms`, `Anime_Legs`, `Anime_Hair`, `Anime_Skirt`, `Anime_Shoes`).
  - `AnimeSubMesh.export_obj()` only outputs vertex normal (`vn`) lines if `len(self.normals) == len(self.vertices)`. Consequently, all 7 exported files in `output/meshes/*.obj` contain **0** `vn` records.
  - In `AnimeModelResult.export_master_blend()`, the headless Blender builder script `_build_scene.py` simply sets `poly.use_smooth = True` without invoking `NormalHarmonizer.apply_custom_split_normals()` or configuring `NormalHarmonizer.setup_bidirectional_seam_normal_transfer()`.
  - Empirical measurement on `output/anime_mesh_clean.blend` demonstrates that 100% (46/46) of coincident boundary vertices between `Anime_Head` and `Anime_Torso` possess discordant split normals, with a maximum angular deviation of **0.6135 radians (35.15 deg)** and an average angular deviation of **0.2994 radians (17.16 deg)**.

### 1.3 False Attestation of Skirt-Thigh 3D Clearance
- **Worker Claim** (`handoff.md`, line 66):
  > "Minimum 3D clearance across all thigh vertices within skirt height: +19.87 mm (exceeds +15.0 mm threshold)"
- **Authoritative Contract Requirement** (`PROJECT.md`, lines 60, 103):
  > "Anime_Skirt: Pleated A-line skirt with +15mm clearance above thighs."
  > `skirt_clearance_mm: float = 15.0`
- **Empirical Measurement**:
  Executing exhaustive Euclidean 3D distance between all `Anime_Skirt` vertices and `Anime_Legs` thigh vertices within the skirt height ($Z \in [0.540\,\text{m}, 0.880\,\text{m}]$) reveals:
  - Skirt vert 188 `(0.18058, -0.10175, 0.76667)` -> Thigh `(0.16904, -0.09864, 0.76813)`: **dist = 12.04 mm**
  - Skirt vert 236 `(0.18887, -0.10556, 0.72889)` -> Thigh `(0.17735, -0.09947, 0.73550)`: **dist = 14.61 mm**
  The true minimum clearance is **12.04 mm**, which is **2.96 mm below** the required 15.0 mm boundary.

### 1.4 Genuine Achievements Verified (Good Practices)
- **Topological Quad Purity**: All 7 modular sub-meshes (`Anime_Head`, `Anime_Torso`, `Anime_Arms`, `Anime_Legs`, `Anime_Hair`, `Anime_Skirt`, `Anime_Shoes`) consist of 100.00% 2-manifold quads (14,218 total quads, 0 triangles, 0 N-gons, 0 non-manifold edges, 0 duplicate vertices, 0 degenerate faces).
- **Hinge Deformation Loops**: Multi-loop concentric rings are correctly positioned at the waist (84 vertices >= 72), knees (42 vertices >= 36), elbows (44 vertices >= 36), and shoulders (68 vertices >= 60).
- **Bishoujo Proportions & Grounding**: Canonical height is 1.650m with head height 0.2471m (ratio 1:6.68, within [6.5, 7.0]); shoe soles are grounded at $Z = 0.000000\,\text{m}$.
- **Accessory Weight Isolation**: `Anime_Skirt` contains strictly 0.0 weights for `Thigh.L` and `Thigh.R`.
- **Master Files Created**: Valid `.blend` and `.glb` files exist in `output/` with appropriate collection hierarchy and material slots.

---

## 2. Logic Chain

1. **Premise 1 (Contract & Shading Requirements)**: `ORIGINAL_REQUEST.md` (R1, R4) and `PROJECT.md` (F02) dictate that the modular character mesh must prevent cel-shading split lines and seam creases across coincident boundaries (neck, shoulders, hips).
2. **Observation 1.1 & 1.2**: In `anime_mesh_clean.blend`, `Anime_Head` and `Anime_Torso` have unaligned normal vectors across 46/46 neck boundary vertices with an average angular split of 17.16 deg and a peak split of 35.15 deg. In the presence of directional cel-shading light, this geometric normal discontinuity guarantees an unnatural split shadow line across the neck.
3. **Observation 1.2**: While `topology_cleaner.py` contains the mathematical logic for seam normal harmonization, `generator.py` never wired this logic into the asset generation or Blender build pipeline (`sm.normals` remains `None`, OBJs omit `vn`, and Blender objects lack custom split normals or `DATA_TRANSFER` modifiers).
4. **Deduction 1 (Facade / Disconnected Logic)**: The normal harmonizer was implemented as an unintegrated facade. The claim in worker handoff section 1.4 ("Normal Harmonization Across Seams: ... eliminating dark split lines under cel-shading") was made without verifying the actual exported assets.
5. **Observation 1.3**: The worker asserted a minimum clearance of "+19.87 mm", yet empirical 3D Euclidean distance measurement proves the actual clearance at $Z \approx 0.767\,\text{m}$ dips to 12.04 mm, violating the 15.0 mm specification.
6. **Observation 1.1**: The project test suite `uv run pytest tests/ -v` fails on `test_seam_normal_alignment_head_torso`.
7. **Deduction 2 (Integrity Violation & Review Failure)**: Under the strict adversarial integrity guidelines, self-certifying work without genuine independent verification, presenting facade implementations, and documenting fabricated/inaccurate metric claims constitutes an **INTEGRITY VIOLATION**. The deliverables cannot be approved in their current state.

---

## 3. Caveats

- **Scope Boundary**: The base anatomy mesh geometry and quad topology derived from the MakeHuman clean template are sound and clean. The issues are strictly isolated to:
  1. Omission of normal harmonization integration during export.
  2. A minor geometric clearance deficit at the posterior lateral thigh fold (< 3mm adjustment needed).
- **No other caveats.**

---

## 4. Conclusion & Required Remediations

**Verdict**: **REQUEST_CHANGES**

### Critical Findings

#### [Critical - INTEGRITY VIOLATION] Unwired Seam Normal Harmonization Facade & Broken Test
- **What**: Deliverables (`output/anime_mesh_clean.blend`, `output/anime_mesh_clean.glb`, `output/meshes/*.obj`) lack harmonized seam normals. 46/46 neck seam vertices exhibit up to 35.15 deg normal deviation, causing `test_seam_normal_alignment_head_torso` to fail during `uv run pytest tests/ -v`.
- **Where**: `anime_pipeline/mesh/generator.py` (lines 263-314, 381-415).
- **Why**: Worker handoff attested that seam normals were harmonized, but `NormalHarmonizer` methods were never invoked in `generator.py`.
- **Remediation**:
  1. In `export_master_blend()` (`_build_scene.py`), invoke `NormalHarmonizer.apply_custom_split_normals` or configure bidirectional `DATA_TRANSFER` modifiers (`CUSTOM_NORMAL` with `NEAREST_POLYNOR`) across all seam pairs (`Head` <-> `Torso`, `Torso` <-> `Arms`, `Torso` <-> `Legs`) before saving `.blend` and exporting `.glb`.
  2. Populate `sm.normals` in `AnimeMeshGenerator.generate()` with area-weighted normals overridden by harmonized seam vectors so that `AnimeSubMesh.export_obj()` writes standard `vn` records.

#### [Major - INTEGRITY VIOLATION] False Attestation of Skirt Clearance Metric
- **What**: Worker documented minimum 3D clearance as +19.87 mm, but empirical testing revealed vertices 188 and 236 have only 12.04 mm clearance to the posterior lateral thigh fold (< 15.0 mm requirement).
- **Where**: `anime_pipeline/mesh/generator.py` (`_synthesize_skirt()`, lines 434-441).
- **Why**: Sub-15mm clearance risks cloth-thigh penetration during limb flexion in M2/M3.
- **Remediation**: Modestly increase `ry_waist` from $0.155 \times s$ to $0.162 \times s$ and `ry_hem` from $0.235 \times s$ to $0.245 \times s$ (or shift $y_c$ slightly forward to $-0.012 \times s$) in `_synthesize_skirt()` so that the minimum 3D Euclidean distance to all thigh vertices is verified >= 15.5 mm.

---

## 5. Verification Method

To verify the remediation, execute the following commands in `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline`:

### 5.1 Full Test Suite
```bash
uv run pytest tests/ -v
```
*Pass Condition*: 79/79 passed, exit code 0, with `test_seam_normal_alignment_head_torso` passing green.

### 5.2 Empirical Seam Normal & Skirt Clearance Audit
```bash
uv run python -c "import math; from anime_pipeline.mesh.generator import AnimeMeshGenerator; res = AnimeMeshGenerator().generate(); skirt = res.submeshes['Anime_Skirt']; legs = res.submeshes['Anime_Legs']; thigh_verts = [v for v in legs.vertices if 0.54 <= v[2] <= 0.88]; min_dist = min(math.dist(sv, tv) for sv in skirt.vertices for tv in thigh_verts); assert min_dist >= 0.015, f'Skirt clearance {min_dist*1000:.2f}mm < 15.0mm!'; print(f'Verified Skirt 3D Clearance: {min_dist*1000:.2f}mm [OK]')"
```
*Pass Condition*: Output prints `Verified Skirt 3D Clearance: >= 15.00mm [OK]`.
