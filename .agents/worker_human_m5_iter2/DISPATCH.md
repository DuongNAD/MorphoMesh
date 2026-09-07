# Task Assignment: Milestone 5 Iteration 2 UV Unwrapping & Multi-Format Exports Remediation Worker

## 2026-09-06T22:59:49Z

## Agent Identity
- Agent: `worker_human_m5_iter2`
- Archetype: `teamwork_preview_worker`
- Parent: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)
- Working Directory: `E:\tool\mcp\MorphoMesh\.agents\worker_human_m5_iter2`

## Mandatory Reading
1. `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md`
2. `E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md`
3. `E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md`
4. Reviewer 2 Milestone 5 Report: `E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m5_2\handoff.md`
5. Worker M5 Handoff: `E:\tool\mcp\MorphoMesh\.agents\worker_human_m5\handoff.md`
6. Master Asset: `output/yu_nian_an/Yu_Nian_An_Master.blend`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Write Ownership
You have exclusive write ownership of:
- `src/morphomesh/character_assembler.py`
- `tests/test_production_exports.py`
- `output/yu_nian_an/` (Yu_Nian_An_Master.blend, Yu_Nian_An.fbx, Yu_Nian_An.glb, textures/, README_EXPORT.md)
- `E:\tool\mcp\MorphoMesh\.agents\worker_human_m5_iter2\`

Do NOT alter Yu_Nian_An_Body's 2,036 pure quads / 2,144 vertices base topology in `human_generator.py`.

## Technical Objectives

### 1. UV Coordinate Generation & Texture Atlas Quadrant Mapping
- In `src/morphomesh/character_assembler.py`, implement robust UV unwrap / mapping logic applied before export:
  * For `Yu_Nian_An_Body`: generate continuous UV coordinates mapped into the 4K texture atlas:
    - Head & facial vertices ($Z \ge 1.45\text{m}$): cylindrical/projective unwrapping mapped to Q1 $[0.0, 0.5] \times [0.0, 0.5]$ (Head & Face).
    - Torso, arms, legs ($Z < 1.45\text{m}$): cylindrical/projective unwrapping mapped to Q2 $[0.5, 1.0] \times [0.0, 0.5]$ (Body & Limbs).
  * For `Mesh_Dress_Bodice` and `Mesh_Dress_PleatedSkirt`: cylindrical UV mapping mapped to Q3 $[0.0, 0.5] \times [0.5, 1.0]$ (Silk Dress).
  * For `Mesh_Dress_WaistSash` and `Mesh_Sandal_L/R`: UV mapping mapped to Q4 $[0.5, 1.0] \times [0.5, 1.0]$ (Sash & Sandals).
  * For `Mesh_Lips`: scale and offset UVs into the mouth region of Q1 $[0.18, 0.32] \times [0.08, 0.20]$.
- Ensure the active UV layer is named `UVMap` and populated across all face loops (`mesh.uv_layers.new(name="UVMap")`).

### 2. Re-Export Production Assets with `TEXCOORD_0`
- Re-export `output/yu_nian_an/Yu_Nian_An_Master.blend` with UV layers saved.
- Re-export `output/yu_nian_an/Yu_Nian_An.fbx` and `output/yu_nian_an/Yu_Nian_An.glb`:
  * Confirm `TEXCOORD_0` attribute is present on all mesh primitives in `Yu_Nian_An.glb`.
  * Confirm UV layers are present in `Yu_Nian_An.fbx`.
  * Verify 163 Rigify DEF bones and 52 ARKit FACS shape keys remain 100% functional.

### 3. Generate Pre-Packed Texture Maps (ORM & MaskMap)
- In `output/yu_nian_an/textures/`:
  * Generate `Yu_Nian_An_ORM_4K.png` (Unreal Engine format: R = Ambient Occlusion, G = Roughness, B = Metallic, A = SSS mask).
  * Generate `Yu_Nian_An_MaskMap_4K.png` (Unity HDRP format: R = Metallic, G = Ambient Occlusion, B = Detail/SSS, A = Smoothness / 1-Roughness).
  * Verify all 9 texture maps are strictly $4096 \times 4096$.

### 4. Update Engine Documentation (`output/yu_nian_an/README_EXPORT.md`)
- Section 5.A (Unreal Engine 5.4+): Add explicit instruction to double-click `Yu_Nian_An_Normal_4K.png` in Content Browser and check **Flip Green Channel** (for OpenGL to DirectX tangent space conversion).
- Section 5.C (Three.js WebGL): Update code sample to demonstrate loading `Yu_Nian_An_BaseColor_4K.png`, `Normal`, `Roughness`, and `ORM` via `THREE.TextureLoader` and binding them to the character's mesh material.

### 5. Update Automated Test Suite
- In `tests/test_production_exports.py`:
  * Add unit tests asserting `TEXCOORD_0` exists on `Yu_Nian_An_Body`, dress, and sandal meshes in `Yu_Nian_An.glb`.
  * Add unit tests verifying `Yu_Nian_An_ORM_4K.png` and `Yu_Nian_An_MaskMap_4K.png` exist and have dimensions $4096 \times 4096$.
  * Verify full repository regression test suite `pytest tests/` (100% pass rate).

### 6. Delivery
- Deliver your handoff report to `E:\tool\mcp\MorphoMesh\.agents\worker_human_m5_iter2\handoff.md` and message orchestrator_human_1.
