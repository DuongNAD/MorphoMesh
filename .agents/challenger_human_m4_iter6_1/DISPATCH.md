# Dispatch Instructions - challenger_human_m4_iter6_1

**Agent ID**: challenger_human_m4_iter6_1
**Archetype**: teamwork_preview_challenger
**Parent**: orchestrator_human_1 (conversation ID: fa73b7ae-2239-4440-89d0-f3a69497b7b7)
**Date**: 2026-09-07T05:21:00+07:00

## Mandatory Reading (Read FIRST)
1. E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
2. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md
3. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md
4. Worker M4 Iteration 6 Handoff: E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter6\handoff.md
5. Master Asset: output/yu_nian_an/Yu_Nian_An_Master.blend

## Assignment: Empirical Adversarial Stress Audit in Live Blender 4.5.4 LTS
Execute deep empirical scripts and stress tests directly against `output/yu_nian_an/Yu_Nian_An_Master.blend`:
1. **Bangs Quad Width & Gap Empirical Stress Audit**:
   - Measure actual quad X-widths of `Hair_Hime_Bangs` (verify average width >= 7.0mm, min width >= 5.0mm).
   - Test adjacent spline X-overlap across all 36 splines: verify min overlap >= 1.0mm and 0 gaps across the forehead.
2. **Modular Face Geometry & Rigging Stress**:
   - Verify `Mesh_Lips`: 100% pure quads (50 quads, 66 verts), parented to `Yu_Nian_An_Body`, 100% weighted to `DEF-head`.
   - Verify `Mesh_Eyelid_Left` / `Mesh_Eyelid_Right`: 100% quads, parented to body, 100% weighted to `DEF-head`.
   - Verify `Yu_Nian_An_Body`: exactly 2,036 pure quads, 2,144 verts, 0 tris/ngons. Polygons 377 and 378 have `material_index == 0` (`slot_skin`).
   - Rotate `DEF-head` bone by 30 degrees and verify that `Mesh_Lips`, eyelids, and eye spheres transform seamlessly without detaching or shearing!
3. **Deep BVH Clearance & Props Kinematics**:
   - Bodice-to-body BVH overlaps: must be 0 face intersections. Minimum signed clearance >= +4.0mm.
   - 10 marionette cords: roots snapped to finger DEF bone tails with distance <= 1.0mm.
   - 45°/60° finger bone rotations dynamically deform cords and translate butterflies in 3D mid-air.
4. **Cranial Apex Specular Glare & Optics**:
   - Verify 73 scalp polygons have `Mat_Human_Scalp` (`Roughness = 0.70`, `Coat = 0.0`).
   - Verify `Mat_Human_Hair` has `Coat Weight <= 0.10`, `Coat Roughness >= 0.25`, `Anisotropic >= 0.65`.
5. Run test suites:
   - `pytest tests/test_character_assembler.py tests/test_human_grooming.py -v`
   - `pytest tests/test_challenger_m4_iter4_empirical.py -v`
6. Deliver your empirical verdict (CONFIRM or CHALLENGE) in `E:\tool\mcp\MorphoMesh\.agents\challenger_human_m4_iter6_1\handoff.md` and message orchestrator_human_1.
