# Dispatch Assignment: worker_human_m5_iter3

## 2026-09-07T06:15:00Z
**Role**: Milestone 5 Iteration 3 Remediation Worker  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\worker_human_m5_iter3`  
**Parent**: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  

---

### Mandatory Reading Files
1. `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md`
2. `E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md`
3. `E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\DEAD_ENDS.md`
4. Reviewer 2 Milestone 5 Iteration 2 Report: `E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m5_iter2_2\handoff.md`
5. Worker M5 Iteration 2 Handoff: `E:\tool\mcp\MorphoMesh\.agents\worker_human_m5_iter2\handoff.md`
6. Master Asset: `output/yu_nian_an/Yu_Nian_An_Master.blend`

---

### MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

---

### Write Ownership
You have exclusive write ownership of:
- `src/morphomesh/character_assembler.py`
- `tests/test_production_exports.py`
- `output/yu_nian_an/` (`Yu_Nian_An_Master.blend`, `Yu_Nian_An.fbx`, `Yu_Nian_An.glb`)
- `.agents/worker_human_m5_iter3/`

Do NOT alter `Yu_Nian_An_Body`'s 2,036 quads / 2,144 vertices base topology in `human_generator.py`.

---

### Implementation Tasks

#### 1. Fix UV Coordinate V-Axis Inversion in `src/morphomesh/character_assembler.py`
In `_get_uv_unwrapping_script_snippet()`:
Reviewer 2 identified that the 2D texture generation in `generate_yu_nian_an_pbr_textures()` sets:
- Rows 0 to 2047 ($y < 2048$, top half of PNG): Q1 Head & Face ($X < 2048$) and Q2 Body Skin ($X \ge 2048$).
- Rows 2048 to 4095 ($y \ge 2048$, bottom half of PNG): Q3 Silk Dress ($X < 2048$) and Q4 Sash & Sandals ($X \ge 2048$).

In Blender UV space, $(U, V) = (0, 0)$ is at the bottom-left of the image:
- $V \in [0.0, 0.5]$ maps to rows 2048 to 4095 (bottom half = Silk Dress, Sash & Sandals).
- $V \in [0.5, 1.0]$ maps to rows 0 to 2047 (top half = Head, Face, Lips, Body Skin).

In glTF standard export ($V_{\text{glTF}} = 1.0 - V_{\text{Blender}}$):
- $V_{\text{Blender}} \in [0.5, 1.0] \implies V_{\text{glTF}} \in [0.0, 0.5]$ (samples top half of texture).
- $V_{\text{Blender}} \in [0.0, 0.5] \implies V_{\text{glTF}} \in [0.5, 1.0]$ (samples bottom half of texture).

Therefore, update `_get_uv_unwrapping_script_snippet()`:
- **`Yu_Nian_An_Body` Head/Face** ($Z \ge 1.45\text{m}$):
  Map $U \in [0.0, 0.5]$, $V \in [0.5, 1.0]$ (Q1).
- **`Yu_Nian_An_Body` Body/Limbs** ($Z < 1.45\text{m}$):
  Map $U \in [0.5, 1.0]$, $V \in [0.5, 1.0]$ (Q2).
- **`Mesh_Dress_Bodice` & `Mesh_Dress_PleatedSkirt`**:
  Map $U \in [0.0, 0.5]$, $V \in [0.0, 0.5]$ (Q3, ivory silk dress).
- **`Mesh_Dress_WaistSash` & `Mesh_Sandal_L/R`**:
  Map $U \in [0.5, 1.0]$, $V \in [0.0, 0.5]$ (Q4, ice-blue sash & sandals).
- **`Mesh_Lips`**:
  In Blender UV space, mouth region in Q1 corresponds to $U \in [0.20, 0.30]$ and $V \in [0.60, 0.68]$ (where lips are drawn at row $\approx 1475$, $V = 1.0 - 1475/4096 \approx 0.64$).
  Ensure `Mesh_Lips` UVs map into this exact region.

#### 2. Re-Export Production Assets
- Re-run script to regenerate `output/yu_nian_an/Yu_Nian_An_Master.blend` with corrected UVs.
- Re-export `output/yu_nian_an/Yu_Nian_An.fbx` and `output/yu_nian_an/Yu_Nian_An.glb`.
- Confirm all 34 primitives in `Yu_Nian_An.glb` have `TEXCOORD_0`.
- Confirm 163 DEF bones and 52 ARKit blendshapes remain functional.

#### 3. Implement Semantic Texture Sampling Verification in `tests/test_production_exports.py`
Add `test_glb_uv_semantic_texture_sampling`:
- Parse `output/yu_nian_an/Yu_Nian_An.glb` and extract vertex UV coordinates for:
  * `Mesh_Lips_Mesh`
  * `Mesh_Dress_PleatedSkirt_Mesh`
  * `Mesh_Dress_Bodice_Mesh`
  * `Yu_Nian_An_Body` (head)
- Sample `output/yu_nian_an/textures/Yu_Nian_An_BaseColor_4K.png` at those UV coordinates.
- Assert:
  * `Mesh_Lips_Mesh` samples rose vermilion ($R > G + 30$ and $R > B + 30$, $R > 180$).
  * `Mesh_Dress_PleatedSkirt_Mesh` and `Mesh_Dress_Bodice_Mesh` sample ivory silk ($R, G, B > 230$ and $|R - G| < 10$).
  * `Yu_Nian_An_Body` head samples porcelain skin ($R > 200, G > 180, B > 170$).

#### 4. Run Test Suites
- Run `pytest tests/test_production_exports.py -v`.
- Run full regression suite `pytest tests/` (100% pass rate required).

---

### Delivery
Write your completion handoff report to `E:\tool\mcp\MorphoMesh\.agents\worker_human_m5_iter3\handoff.md` and send a completion message to `orchestrator_human_1`.
