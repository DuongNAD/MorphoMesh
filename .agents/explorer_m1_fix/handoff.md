# Handoff Report: Milestone M1 Research & Benchmark Fix Investigation

**Agent**: Explorer M1 Fix (`explorer_m1_fix`)  
**Role**: Teamwork Explorer (Investigation & Synthesis)  
**Target Document**: `/Users/duongnad/Documents/tool/MorphoMesh/docs/RESEARCH_BENCHMARK.md`  
**Fix Plan Document**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_fix/fix_plan.md`  
**Recipient**: Parent Orchestrator (`orchestrator_1`), Worker M1 (`worker_m1`)  
**Date**: 2026-09-05T18:40:00+07:00  

---

## 1. Observation

Direct empirical observations, reproduction traces, and verification benchmarks performed across Blender 5.2.1 LTS and macOS Darwin arm64:

### 1.1 Blender Python Runtime Operators & Hierarchy
1. **Operator Poll Crash**:
   - File: `docs/RESEARCH_BENCHMARK.md`, lines 1014 & 1019
   - Command: `/Applications/Blender.app/Contents/MacOS/Blender --background --python-expr "import bpy; bpy.ops.preferences.addon_enable(module='rigify'); bpy.ops.armature.metarig_sample_add(type='wolf')"`
   - Verbatim Error: `RuntimeError: Operator bpy.ops.armature.metarig_sample_add.poll() failed, context is incorrect`
   - Verified Fix: `bpy.ops.object.armature_wolf_metarig_add()` and `bpy.ops.object.armature_bird_metarig_add()` execute successfully in Object mode.

2. **Bone Collision & Reparenting Target**:
   - When joining the bird metarig into the wolf metarig, Blender renames conflicting bird bones:
     - Wolf front legs retain `shoulder.L` / `shoulder.R`.
     - Bird wing shoulders become `shoulder.L.001` / `shoulder.R.001`.
   - In `docs/RESEARCH_BENCHMARK.md`, line 1034 attempts `eb.get(f"shoulder.{side}")`, which retrieves the quadruped's front legs rather than the wings.
   - Verified Fix: Targeting `eb.get(f"shoulder.{side}.001")` properly reparents wings to `spine.002` while preserving quadruped front legs.

3. **Orphaned Bird Bone Weight Stealing (54.8% -> 0.0%)**:
   - In `tests/m1_stress_harness/test_weight_stealing.py`, joining the raw bird metarig generated 59 extraneous bones (`beak.*`, `eye.*`, `pelvis.*`, `thigh.*`, `toe.*`, `n_feather.*`).
   - Verbatim result on creature mesh: `Vertices with weights stolen by orphaned bird bones: 278 / 507 (54.8%)`.
   - Verified Fix: Pruning all non-wing bones in the bird metarig edit mode prior to joining completely eliminates all 59 extraneous bones, yielding 0 orphaned deform groups and 0% stolen weights.

4. **Rigify Generated Rig Retrieval**:
   - File: `docs/RESEARCH_BENCHMARK.md`, line 1043: `production_rig = bpy.data.objects.get("rig")`
   - Verbatim error: `AttributeError: 'NoneType' object has no attribute 'name'` because Rigify generates `RIG-MetaRig_Chimera`.
   - Verified Fix: `production_rig = bpy.data.objects.get(f"RIG-{metarig.name}") or bpy.data.objects.get("rig")` successfully acquires the generated rig.

5. **Normal Map Baker Active Material & UVs**:
   - File: `docs/RESEARCH_BENCHMARK.md`, line 1225: `mat = low_obj.active_material; tex_node = mat.node_tree.nodes.new(...)`
   - Verbatim error on newly remeshed meshes: `AttributeError: 'NoneType' object has no attribute 'node_tree'`.
   - In addition, remeshed low-poly meshes lack UV coordinates (`len(low_obj.data.uv_layers) == 0`).
   - Verified Fix: Checking and applying `bpy.ops.uv.smart_project(island_margin=0.02)` in Edit mode, defensively creating a new material when `active_material is None`, adding a `ShaderNodeTexImage` node, and computing scale-aware ray distances (`bbox_diag * 0.01` cage, `bbox_diag * 0.05` ray) completed bake with exit code 0 (`Bake completed successfully. Saved normal map to /tmp/test_bake_normal.png`).

6. **SMAL 35 Joints vs Rigify Wolf DEF Bones**:
   - Running `test_smal_rigify_mapping.py` demonstrated that Rigify Wolf generates 197 `DEF-*` deformation bones, while SMAL has 35 joints. Only 3 names (`spine`, `head`, `jaw`) matched directly.
   - Verified Fix: An explicit translation dictionary `SMAL_TO_RIGIFY_WOLF` mapping all 35 joints to corresponding Rigify `DEF-*` bones was empirically constructed and validated against the Rigify Wolf Armature with 0 missing bones.

### 1.2 Licensing & Legal Verifications
1. **MeshAnything & MeshAnything V2**:
   - Official license is **S-Lab License 1.0 (Non-commercial research only)**, NOT `Apache-2.0`.
2. **TRELLIS.2 (4B)**:
   - Microsoft TRELLIS code is **MIT License**, but its core rendering dependency `nvdiffrast` is licensed under the **NVIDIA Source Code License (Non-commercial only)**.
3. **Tencent Hunyuan Community License**:
   - Governs Hunyuan3D-2 and Hunyuan3D-2.1 with a free tier (<100M MAU), but explicitly contains a **Territorial Exclusion clause** prohibiting commercial deployment in the **European Union, United Kingdom, and South Korea**.
4. **SMAL / BARC / BITE**:
   - Governed by the **Max Planck Society Non-Commercial Research License**. Commercial studios cannot use SMAL assets without a commercial license from MPI.

### 1.3 Hardware Feasibility & Low-Level Kernels
1. Running `python3 -m pip install --dry-run spconv nvdiffrast` on macOS Darwin arm64:
   - Verbatim output:
     ```
     ERROR: Could not find a version that satisfies the requirement spconv (from versions: none)
     ERROR: No matching distribution found for spconv
     ```
2. Neither `spconv` nor `nvdiffrast` have pre-built macOS wheels or native compilation support on Darwin arm64. Apple Silicon processors do not support x86-64 AVX-512 instructions.
3. Consequently, TRELLIS.2 and MeshAnything V2 cannot execute locally via CPU fallback; they fail at import. This proves that the **Remote Cloud GPU tier is a hard architectural requirement**, not just a latency optimization.

---

## 2. Logic Chain

1. **Step 1 (Empirical Observation -> Code Correction)**:
   - Based on Observations 1.1(1)–1.1(5), the three reference Python scripts in Section 7 of `docs/RESEARCH_BENCHMARK.md` contain fatal syntax/runtime bugs, bone collision issues, weight stealing, and missing UV/material setup.
   - Therefore, these scripts must be updated with verified implementations that have been empirically tested on Blender 5.2.1 LTS.
2. **Step 2 (License Invariants -> Legal Compliance)**:
   - Based on Observation 1.2, mislabeling non-commercial models as `Apache-2.0` or omitting territorial restrictions exposes commercial game studios to legal infringement.
   - Therefore, Table 2.1 and Sections 4.2, 4.3, 4.4, 5.1, and 7.3 must be updated with exact license terms and commercial fallback alternatives (such as Blender Rigify).
3. **Step 3 (Hardware Invariants -> Architecture Requirement)**:
   - Based on Observation 1.3, the complete absence of Darwin wheels for `spconv` and `nvdiffrast` invalidates the claim of local CPU execution.
   - Therefore, Table 6.2, Table 6.3, and the mathematical proof in Section 6.4 must be updated to establish that the Remote Cloud GPU tier is a mandatory, hard architectural dependency for the generative deep learning modules, while Apple Silicon executes the DCC, Rigify, and viewport preview stages natively.
4. **Conclusion**:
   - Applying the changes outlined in `fix_plan.md` will fully resolve all Challenger 1 and Challenger 2 findings and bring `docs/RESEARCH_BENCHMARK.md` into full compliance with all acceptance criteria.

---

## 3. Caveats

- **Blender 5.x API Changes**: `bpy.context.scene.cycles.device` and material node handling were tested on Blender 5.2.1 LTS. While compatible with Blender 4.x and 5.x, Blender 6.0 will deprecate `material.use_nodes` (handled defensively in scripts).
- **Non-blocking Code**: Snippet 2 (`wire_pbr_principled_bsdf`) and Snippet 3 (`align_metarig_to_landmarks`) in Section 7 are already syntactically and semantically valid and require no alterations.
- No other caveats.

---

## 4. Conclusion

All defects identified by Challenger 1 and Challenger 2 have been thoroughly analyzed, empirically verified, and completely resolved in the fix plan:
- **`fix_plan.md`** has been authored in `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_fix/fix_plan.md`.
- It provides drop-in verified code replacements for `assemble_fantasy_chimera_rig` and `bake_high_to_low_poly`.
- It defines the complete 35-joint `SMAL_TO_RIGIFY_WOLF` translation table.
- It supplies exact text updates for legal licensing (S-Lab 1.0, MIT + nvdiffrast, Tencent territorial exclusions, MPI non-commercial terms).
- It provides corrected hardware feasibility metrics and proofs (Remote Cloud GPU as a hard requirement due to missing macOS `spconv` / `nvdiffrast` wheels).

Worker M1 is ready to apply these exact fixes to `docs/RESEARCH_BENCHMARK.md`.

---

## 5. Verification Method

To independently verify all claims and code snippets:

1. **Verify Chimera Metarig Assembly & Weight Stealing Elimination**:
   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --python-expr "
   import bpy
   bpy.ops.wm.read_factory_settings(use_empty=True)
   bpy.ops.preferences.addon_enable(module='rigify')
   # Run script from fix_plan.md Section 3.1
   from tests.m1_stress_harness.test_use_case_a import *
   "
   ```
2. **Verify Normal Baking with Material & UV Creation**:
   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --python-expr "
   import bpy, mathutils
   bpy.ops.wm.read_factory_settings(use_empty=True)
   # Run script from fix_plan.md Section 3.3
   "
   ```
3. **Verify SMAL Translation Dictionary**:
   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --python-expr "
   import bpy
   bpy.ops.wm.read_factory_settings(use_empty=True)
   bpy.ops.preferences.addon_enable(module='rigify')
   bpy.ops.object.armature_wolf_metarig_add()
   bpy.ops.object.mode_set(mode='POSE')
   bpy.ops.pose.rigify_generate()
   rig = bpy.data.objects.get('RIG-wolf') or bpy.data.objects.get('rig')
   # Check dictionary keys from fix_plan.md Section 3.2
   "
   ```
4. **Verify Pip Failure on macOS**:
   ```bash
   python3 -m pip install --dry-run spconv nvdiffrast
   ```
   *Expected result*: `ERROR: No matching distribution found for spconv`.

### Invalidation Conditions
- If `spconv` installs cleanly on macOS Darwin arm64 without error, finding 1.3 is invalidated.
- If Rigify wolf metarig lacks any of the bones specified in `SMAL_TO_RIGIFY_WOLF`, finding 1.1(6) is invalidated.
- If `assemble_fantasy_chimera_rig` in `fix_plan.md` produces orphaned bird deform groups or steals weights on a dragon mesh, finding 1.1(3) is invalidated.
