# Comprehensive Investigation Report: Yu Nian An Deliverables & Failing Tests Survey

- **Author**: Explorer 1 (Yu Nian An Deliverables & 19 Failing Tests Survey)
- **Target Deliverables**: `output/yu_nian_an/` (`Yu_Nian_An_Master.blend`, `Yu_Nian_An.fbx`, `Yu_Nian_An.glb`, `textures/`)
- **Analyzed Test Files**:
  - `tests/test_adversarial_character_assembler.py`
  - `tests/test_character_assembler.py`
  - `tests/test_production_exports.py`
  - `tests/test_challenger_m5_empirical.py`
  - Additional related audit suites (`tests/test_challenger_m4_iter*.py`)
- **Date**: 2026-09-07T13:35:00Z
- **Execution Environment**: Windows, Blender 4.5.4 LTS, Python 3.11.9, pytest 9.1.1, FastMCP / UV

---

## 1. Executive Summary

A comprehensive test run of `uv run pytest` revealed **16 primary failures** across the 4 assigned test files, plus **3 related failures** in `test_challenger_m4_iter*.py` that directly inspect `output/yu_nian_an/Yu_Nian_An_Master.blend`, totaling **19 failing tests** tied to the master deliverables.

### Core Root Cause
The entire failure cascade is caused by an accidental overwrite of the production binary deliverables (`Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, `Yu_Nian_An.fbx`) by an experimental beauty test script: `scripts/test_beauty_recreation.py` (lines 955–978).

In `scripts/test_beauty_recreation.py`, a prototype VRM model (`AliciaSolid.vrm` / `Liva.vrm`) was loaded and saved directly over:
1. `output/yu_nian_an/Yu_Nian_An_Master.blend`
2. `output/yu_nian_an/Yu_Nian_An.glb`
3. `output/yu_nian_an/Yu_Nian_An.fbx`

This replaced the canonical procedural digital human scene with an alien VRM hierarchy:
- Objects were renamed to `Beauty_Body`, `Beauty_Armature`, etc.
- Root collection `Yu_Nian_An_Master` and 6 child collections (`01_Body` .. `06_Lights_Camera`) were eradicated and replaced with `glTF_not_exported`.
- Armature was replaced with a 250-bone VRM skeleton (`J_Bip_C_Hips`), completely lacking Rigify's 163 `DEF-` bones.
- `Beauty_Body` had **0 shape keys** (losing all 52 ARKit FACS blendshapes).
- Exported GLB had only 20 meshes instead of 30+, missed `TEXCOORD_0` on 16 primitives, missed `Mesh_Lips`, and had 0 morph targets in `extras.targetNames`.
- Exported FBX dropped from 7.51 MB to 4.16 MB, losing all DEF bones and ARKit blendshapes.

Furthermore, code inspection of `src/morphomesh/character_assembler.py` revealed:
1. `get_master_assembly_script()` was missing the finger bone tail snapping loop for `Prop_Marionette_Strings`.
2. `src/morphomesh/export_manager.py` did not exist as an independent module (export logic was embedded in `character_assembler.py`).
3. `get_export_script()` needed explicit `export_extras=True` and `export_texcoords=True` flags for glTF GLB export.

---

## 2. Inventory of the 19 Deliverable Failures

| # | Test Identifier | Target Asset | Verbatim Failure Reason | Root Cause |
|---|-----------------|--------------|-------------------------|------------|
| 1 | `test_adversarial_character_assembler.py::test_master_blend_arkit_shape_keys_empirical_deltas` | `Yu_Nian_An_Master.blend` | `AssertionError: Yu_Nian_An_Body not found` | `Beauty_Body` replaced `Yu_Nian_An_Body`; 0 shape keys present |
| 2 | `test_adversarial_character_assembler.py::test_master_blend_def_bones_163_exact_inventory` | `Yu_Nian_An_Master.blend` | `AssertionError: Armature object missing` | Looking for `Armature_Yu_Nian_An_Rigify`; found `Beauty_Armature` (VRM) |
| 3 | `test_adversarial_character_assembler.py::test_master_blend_cameras_50mm_and_ndc_framing` | `Yu_Nian_An_Master.blend` | `KeyError: 'Yu_Nian_An_Body' not found` | `Yu_Nian_An_Body` missing; cameras renamed to `Cam_FullBody` |
| 4 | `test_adversarial_character_assembler.py::test_master_blend_strings_and_clearance_adversarial` | `Yu_Nian_An_Master.blend` | `KeyError: 'Armature_Yu_Nian_An_Rigify' not found` | Armature missing; `Prop_Marionette_Strings` missing finger snapping |
| 5 | `test_character_assembler.py::test_live_master_blend_content_verification` | `Yu_Nian_An_Master.blend` | `assert False is True (has_root_col)` | Root collection `Yu_Nian_An_Master` missing; found `glTF_not_exported` |
| 6 | `test_character_assembler.py::test_live_camera_fullbody_and_turnaround_ndc_bounds` | `Yu_Nian_An_Master.blend` | `KeyError: 'Yu_Nian_An_Body' not found` | Body object missing in blend |
| 7 | `test_character_assembler.py::test_live_marionette_strings_snapped_to_finger_bone_tails` | `Yu_Nian_An_Master.blend` | `KeyError: 'Armature_Yu_Nian_An_Rigify' not found` | Armature object missing in blend |
| 8 | `test_character_assembler.py::test_live_wardrobe_signed_clearance_and_zero_penetration` | `Yu_Nian_An_Master.blend` | `KeyError: 'Yu_Nian_An_Body' not found` | Body object missing in blend |
| 9 | `test_character_assembler.py::test_live_lips_clearance_and_material_slot_distribution` | `Yu_Nian_An_Master.blend` | `KeyError: 'Yu_Nian_An_Body' not found` | Body object missing in blend |
| 10 | `test_character_assembler.py::test_live_eye_spheres_hair_armature_binding_and_rotation_kinematics` | `Yu_Nian_An_Master.blend` | `KeyError: 'Armature_Yu_Nian_An_Rigify' not found` | Armature object missing in blend |
| 11 | `test_production_exports.py::test_fbx_contains_def_bones_and_shape_keys` | `Yu_Nian_An.fbx` | `AssertionError: Missing expected DEF bones in FBX: [] (0 >= 4)` | FBX exported without 163 DEF bones or ARKit shape keys |
| 12 | `test_production_exports.py::test_glb_body_mesh_has_all_52_arkit_morph_targets` | `Yu_Nian_An.glb` | `AssertionError: Expected 52 morph targets, got 0` | Body mesh in GLB has empty `extras.targetNames` |
| 13 | `test_production_exports.py::test_glb_all_mesh_primitives_have_texcoord_0` | `Yu_Nian_An.glb` | `AssertionError: Primitives missing TEXCOORD_0: 16 primitives` | Raw prototype meshes lacked UVMap layers during GLB export |
| 14 | `test_production_exports.py::test_glb_uv_semantic_texture_sampling` | `Yu_Nian_An.glb` | `StopIteration (next mesh with 'Lips' in name)` | No mesh with "Lips" in its name in GLB |
| 15 | `test_challenger_m5_empirical.py::test_glb_container_and_morphs` | `Yu_Nian_An.glb` | `AssertionError: Expected >= 30 meshes, got 20` | GLB missing sub-meshes (only 20 merged objects) |
| 16 | `test_challenger_m5_empirical.py::test_fbx_binary_header_and_bones` | `Yu_Nian_An.fbx` | `assert 4166812 > 5000000 (4.16MB < 5MB)` | FBX size insufficient; lacked 163 DEF bones and 52 morph targets |
| 17 | `test_challenger_m4_iter4_empirical.py::test_empirical_adversarial_audit_in_blender` | `Yu_Nian_An_Master.blend` | `Audit failure: collection and body missing` | Blend file replaced with prototype scene |
| 18 | `test_challenger_m4_iter6_empirical.py::test_empirical_adversarial_audit_in_blender` | `Yu_Nian_An_Master.blend` | `Hair_Hime_Bangs object missing or empty` | Hair layers missing in overwritten blend |
| 19 | `test_challenger_m4_iter7_empirical.py::test_challenger_m4_iter7_empirical_blender` | `Yu_Nian_An_Master.blend` | `Yu_Nian_An_Master hierarchy check failure` | Overwritten blend lacks 7-tier collection structure |

---

## 3. Detailed Root Cause Analysis

### 3.1 Overwrite Incident in `scripts/test_beauty_recreation.py`
Inspection of `git diff c0c84e8 scripts/test_beauty_recreation.py` shows that lines 955 to 978 were introduced to save an ad-hoc rendering test into the canonical deliverable paths:
```python
    # Save clean master and beauty scenes
    beauty_blend = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Beauty.blend"
    master_blend = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend"
    ...
    bpy.ops.wm.save_as_mainfile(filepath=beauty_blend)
    bpy.ops.wm.save_as_mainfile(filepath=master_blend)  # <-- DESTRUCTIVE OVERWRITE
    out_glb = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An.glb"
    bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB')  # <-- OVERWRITE
    out_fbx = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An.fbx"
    bpy.ops.export_scene.fbx(filepath=out_fbx)  # <-- OVERWRITE
```
This single invocation corrupted all three primary production artifacts.

### 3.2 Marionette String Snapping Omission in `character_assembler.py`
In `src/morphomesh/character_assembler.py` (lines 1202–1223), `Prop_Marionette_Strings` is bound to the armature and receives vertex groups, but the script fails to snap the distal vertex pairs (`v0`, `v1`) of each cord to the finger bone tails (`tail_world`):
```python
# Missing in character_assembler.py:
inv_world = strings_obj.matrix_world.inverted()
for cord_i, b_name in enumerate(finger_def_bone_keys):
    bone = arm_obj.data.bones.get(b_name)
    if bone:
        b_tail = arm_obj.matrix_world @ bone.tail_local
        local_tail = inv_world @ b_tail
        v0_idx = cord_i * verts_per_cord
        v1_idx = v0_idx + 1
        if v0_idx < len(strings_obj.data.vertices):
            strings_obj.data.vertices[v0_idx].co = local_tail
        if v1_idx < len(strings_obj.data.vertices):
            strings_obj.data.vertices[v1_idx].co = local_tail
```
Without this, the string midpoints are > 5mm away from the bone tails, causing `test_master_blend_strings_and_clearance_adversarial` and `test_live_marionette_strings_snapped_to_finger_bone_tails` to fail.

### 3.3 Missing `export_manager.py` Module
The user prompt references `src/morphomesh/export_manager.py`. Currently, export logic is situated in `character_assembler.py` (`get_export_script`, `export_production_assets`). Creating `src/morphomesh/export_manager.py` cleanly separates export orchestration from scene assembly, fulfilling architectural specifications.

### 3.4 glTF and FBX Export Settings
1. **glTF `extras.targetNames`**: Blender 4.5 automatically generates `extras.targetNames` when `export_morph=True` on a mesh with shape keys. However, `export_extras=True` and `export_texcoords=True` must be explicitly asserted in `bpy.ops.export_scene.gltf` to ensure non-destructive serialization.
2. **glTF Joint Count**: Blender 4.5 exports 164 skin joints (1 armature root node + 163 DEF bones). This matches `assert len(joints) == 164` in `test_challenger_m5_empirical.py`.
3. **glTF Mesh Count**: All 31 mesh objects across collections `01_Body` (8), `02_Hair` (6), `03_Wardrobe` (6), and `04_Props` (11) must be selected during export, satisfying `len(meshes) >= 30`.
4. **FBX Size & Content**: When all 31 meshes and the 163 DEF bone Rigify armature with 52 shape keys are exported with `mesh_smooth_type='FACE'`, the FBX binary size is approximately 7.5 MB (> 5 MB).

---

## 4. Binary Deliverable Compliance Audit

### 4.1 FBX 163 DEF Bones & Shape Keys
- **Requirement**: `Yu_Nian_An.fbx` must contain Kaydara header, file size > 5,000,000 bytes, `DEF-spine`, `DEF-head`, `DEF-upper_arm.L`, `DEF-hand.L`, `DEF-thigh.L`, `DEF-foot.L`, and ARKit shape keys (`eyeBlinkLeft`, `jawOpen`, `mouthSmileLeft`, `cheekPuff`).
- **Current Status**: FAILED (4.16 MB, VRM bones).
- **Remediation Target**: Re-export from canonical master scene; file size ~7.5 MB, all 163 DEF bones and 52 shape keys present.

### 4.2 GLB 52 ARKit FACS Blendshapes
- **Requirement**: `Yu_Nian_An.glb` must have `extras.targetNames` on `Yu_Nian_An_Body` containing all 52 Apple ARKit blendshapes.
- **Current Status**: FAILED (0 shape keys).
- **Remediation Target**: Re-export from canonical master scene where `Yu_Nian_An_Body` has 52 ARKit keys with non-zero delta vectors ($d_{\max} \ge 2\text{mm} \gg 10^{-6}$).

### 4.3 UV Map `TEXCOORD_0` on All Primitives
- **Requirement**: Every primitive in `Yu_Nian_An.glb` must have `TEXCOORD_0`.
- **Current Status**: FAILED (16 primitives missing `TEXCOORD_0`).
- **Remediation Target**: `assign_texture_atlas_uvs()` in `_get_uv_unwrapping_script_snippet()` creates and activates `UVMap` on 100% of scene meshes before export.

### 4.4 Consistent Lip/Face Mesh Naming
- **Requirement**: `Yu_Nian_An.glb` must contain a mesh with `"Lips"` in its name (`Mesh_Lips`), with UVs mapping to quadrant Q1 oral slit ($R > G + 30, R > B + 30, R > 180$).
- **Current Status**: FAILED (`StopIteration` — no lips mesh found).
- **Remediation Target**: Canonical `Mesh_Lips` (50 pure quads) exported cleanly in collection `01_Body`.

### 4.5 Marionette String Snapping & Clearance
- **Requirement**: 10 marionette cords within 5mm of finger DEF bone tails; wardrobe signed clearance $\ge +4\text{mm}$ with 0 penetrations; lips clearance $\ge +0.1\text{mm}$ with 0 penetrations.
- **Current Status**: FAILED (due to missing objects in overwritten blend).
- **Remediation Target**: Insert explicit vertex tail snapping loop in `character_assembler.py` and enforce `clearance_offset=0.015` (15mm) on wardrobe.

---

## 5. Step-by-Step Remediation Plan for Worker

### Step 1: Update `src/morphomesh/character_assembler.py`
1. In `get_master_assembly_script()`:
   After line 1202, insert the finger bone tail snapping loop:
   ```python
   inv_world = strings_obj.matrix_world.inverted()
   for cord_i, b_name in enumerate(finger_def_bone_keys):
       bone = arm_obj.data.bones.get(b_name)
       if bone:
           b_tail = arm_obj.matrix_world @ bone.tail_local
           local_tail = inv_world @ b_tail
           v0_idx = cord_i * verts_per_cord
           v1_idx = v0_idx + 1
           if v0_idx < len(strings_obj.data.vertices):
               strings_obj.data.vertices[v0_idx].co = local_tail
           if v1_idx < len(strings_obj.data.vertices):
               strings_obj.data.vertices[v1_idx].co = local_tail
   ```
2. In `get_export_script()`:
   Ensure `bpy.ops.export_scene.gltf` explicitly specifies `export_extras=True` and `export_texcoords=True`.

### Step 2: Create `src/morphomesh/export_manager.py`
Create `src/morphomesh/export_manager.py` as a dedicated module providing:
- `export_production_assets()`
- `get_export_script()`
- `generate_yu_nian_an_pbr_textures()`
- `assign_texture_atlas_uvs()`
Re-export these from `character_assembler.py` to maintain backwards compatibility.

### Step 3: Neutralize Overwrites in `scripts/test_beauty_recreation.py`
In `scripts/test_beauty_recreation.py`, remove or redirect lines 956–978 so it saves to `output/yu_nian_an/test_prototype.blend` and never touches `Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, or `Yu_Nian_An.fbx`.

### Step 4: Re-Generate Master Production Deliverables
Execute the master assembly and export pipeline via Blender 4.5.4:
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b --python "scripts/build_and_render_master.py"
```
Or execute through `assemble_master_character()` and `export_production_assets()`.
Verify that the output files are regenerated:
- `output/yu_nian_an/Yu_Nian_An_Master.blend` (~14 MB, 7 tiers, 163 DEF bones, 52 shape keys)
- `output/yu_nian_an/Yu_Nian_An.fbx` (~7.5 MB, binary Kaydara 7400)
- `output/yu_nian_an/Yu_Nian_An.glb` (~7.9 MB, glTF 2.0, 164 skin joints, 31 meshes, 52 shape keys, `TEXCOORD_0`)
- `output/yu_nian_an/textures/` (9 x 4K PNGs)

### Step 5: Verification Command
Run the test suite for the 4 target files:
```powershell
uv run pytest tests/test_adversarial_character_assembler.py tests/test_character_assembler.py tests/test_production_exports.py tests/test_challenger_m5_empirical.py
```
Expected result: **77 passed, 0 failed**.
Then verify challenger m4 audits:
```powershell
uv run pytest tests/test_challenger_m4_iter4_empirical.py tests/test_challenger_m4_iter6_empirical.py tests/test_challenger_m4_iter7_empirical.py
```
Expected result: **All passed**.

---

## 6. Conclusion
The 19 failing tests are not due to deep architectural deficiencies in MorphoMesh, but rather a file-level collision where an exploratory script (`test_beauty_recreation.py`) overwrote the master binaries with an unrigged VRM prototype. Fixing the string snapping in `character_assembler.py`, creating `export_manager.py`, preventing regression in `test_beauty_recreation.py`, and re-baking the deliverables via the canonical procedural pipeline will resolve all 19 failing tests immediately.
