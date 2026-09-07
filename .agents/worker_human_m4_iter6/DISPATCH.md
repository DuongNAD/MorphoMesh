# Dispatch Instructions - worker_human_m4_iter6

**Agent ID**: worker_human_m4_iter6
**Archetype**: teamwork_preview_worker
**Parent**: orchestrator_human_1 (conversation ID: fa73b7ae-2239-4440-89d0-f3a69497b7b7)
**Date**: 2026-09-07T05:06:00+07:00

## Mandatory Reading (Read FIRST)
1. E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
2. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md
3. E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md
4. Reviewer 2 Iteration 5 Full Report: E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter5_2\handoff.md
5. Explorer 1 Remediation Plan: E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_m4_6_1\handoff.md
6. Explorer 2 Remediation Plan: E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_m4_6_2\handoff.md
7. Explorer 3 Remediation Plan: E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_m4_6_3\handoff.md
8. Reference Turnaround Art: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership Boundaries
You have EXCLUSIVE write ownership of:
- `src/morphomesh/human_grooming.py`
- `src/morphomesh/character_assembler.py`
- `src/morphomesh/human_materials.py`
- `tests/test_character_assembler.py`
- `tests/test_human_grooming.py`
- `tests/test_human_materials.py`
- `output/yu_nian_an/` (Master blend and beauty renders)
- `.agents/worker_human_m4_iter6/`

Do NOT modify `src/morphomesh/human_generator.py` or alter the 2,036 pure quads / 2,144 vertices topology of `Yu_Nian_An_Body`.

## Assignment: Milestone 4 Iteration 6 Remediation Implementation

### 1. Bangs Ribbon Math & Gap Elimination (`src/morphomesh/human_grooming.py`)
Per Explorer 1 (`explorer_remediation_m4_6_1/handoff.md`):
- In `convert_curves_to_ribbon_mesh`: Replace division by 3D tangent length `dlen` with horizontal length `xy_len = math.sqrt(xy_sq)`:
  `sx = -dy / xy_len * half_w`, `sy = dx / xy_len * half_w`, `sz = 0.0`.
  This guarantees 100% invariant 7.5mm ribbon width regardless of steepness `dz`.
- In `generate_hime_cut_splines`:
  * Set `bangs_count = max(36, count)`.
  * Curve lateral roots and tips backward along the temporal contour ($y_{tip} = (-0.130 + 0.055 \cdot |u_{rel}|^2) \cdot s$).
  * Curve lateral tips gently downward at temples ($target\_z = (1.540 - 0.010 - 0.035 \cdot \max(0.0, |u_{rel}| - 0.35)^{1.5}) \cdot s$).
  * Set `layer_ribbon_widths["Hair_Hime_Bangs"] = 0.0075`.
- In `Hair_Scalp_Crown`: generate 36 splines originating along central sagittal parting ($Y \in [-0.055\text{m}, 0.065\text{m}]$, $Z \approx 1.648\text{m}$) draping laterally across the parietal dome, physically covering Polygon 522 and the upper skull.

### 2. Delicate Anime Mouth / Lips (`src/morphomesh/character_assembler.py` & `src/morphomesh/human_materials.py`)
Per Explorer 2 (`explorer_remediation_m4_6_2/handoff.md`):
- Reset body mesh polygons 377 and 378 back to `slot_skin` (eliminating the flat 25mm x 33mm pink sticker).
- Implement `create_delicate_anime_lips_mesh()` generating pure-quad `Mesh_Lips` (6 rows x 11 columns = 50 pure quads, 66 vertices, 22mm width) in collection `01_Body`, parented to `Yu_Nian_An_Body` and rigged to `DEF-head` with 100% weight.
- Model upper cupid's bow, recessed dark oral commissure slit (`Mat_Human_Oral_Slit`), and pillowed soft rose lower lip vermilion (`Mat_Human_Lips`). Ensure `use_fake_user = True` on all materials.

### 3. Almond Eyelids & High-Contrast Eye Optics (`src/morphomesh/character_assembler.py` & `src/morphomesh/human_materials.py`)
Per Explorer 2 (`explorer_remediation_m4_6_2/handoff.md`):
- Refine `create_almond_eyelid_mesh()`:
  * Upper eyelid ($sin\_t \ge -0.10$): Extrude upward by +3.0mm with subtle outer wing, assigned matte velvety `Mat_Human_Eyeliner` (`(0.01, 0.01, 0.015, 1.0)`, roughness 0.65, specular 0.10).
  * Lower eyelid ($sin\_t < -0.10$): Taper downward 1.0mm flush with cheek ($dy_{out} = dy_{sphere} - 0.0002\text{m}$), assigned `Mat_Human_Skin_SSS`.
- In `create_uv_sphere_mesh()` for eye spheres: Populate forward planar UV coordinates (`UVMap`).
- In `_build_inner_iris_node_tree()`: Multi-stop ramp with deep black pupil ($R \le 0.16$), slate-grey iris ($0.16 < R \le 0.38$), dark limbal ring ($0.38 < R \le 0.44$), and pure white sclera ($R > 0.44$).

### 4. Cranial Apex Glare Elimination & Silky East Asian Hair Sheen (`src/morphomesh/character_assembler.py`)
Per Explorer 3 (`explorer_remediation_m4_6_3/handoff.md`):
- Scalp: Assign dedicated matte `Mat_Human_Scalp` (`(0.012, 0.011, 0.012)`, roughness 0.70, specular 0.25, `Coat Weight = 0.0`) to the 73 scalp polygons ($Z \ge 1.60\text{m}$) on `Yu_Nian_An_Body`.
- Hair Material `Mat_Human_Hair`: Set `Roughness = 0.32`, `Specular IOR Level = 0.48`, `Coat Weight = 0.08`, `Coat Roughness = 0.30`, `Anisotropic = 0.70`, `Anisotropic Rotation = 0.25`, `Sheen Weight = 0.35`.
- Soften rim light `Light_Rim_HairLight` from 750W to 450W with area size 1.0m.

### 5. Regeneration & Testing
- Regenerate `output/yu_nian_an/Yu_Nian_An_Master.blend` using live Blender 4.5.4 LTS.
- Re-render:
  * `output/yu_nian_an/master_portrait_clean.png` (verify visible delicate anime lips, framed almond eyes with dark lash line and slate iris/pupil, full gap-free bangs, and zero white crescent glare on cranium).
  * `output/yu_nian_an/master_fullbody_clean.png`.
- Run test suites:
  * `pytest tests/test_character_assembler.py tests/test_human_grooming.py tests/test_human_materials.py -v`
  * `pytest tests/` (verify 100% pass rate).
- Deliver your handoff report to `E:\tool\mcp\MorphoMesh\.agents\worker_human_m4_iter6\handoff.md` and message orchestrator_human_1.
