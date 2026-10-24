# Dispatch for M2 Remediation Worker (Iteration 2 Targeted Fixes)

## Mission
Apply the two targeted remediations for Milestone M2 in `src/morphomesh/wardrobe.py`:
1. **Fix Blender 4.5+ LTS Collision RNA Attribute (Reviewer 1 finding)**:
   In `src/morphomesh/wardrobe.py` lines 1908-1912 (`get_wardrobe_script()`):
   `CollisionModifier` parameters reside under `col_mod.settings` in Blender 4.5+ LTS:
   ```python
   col_mod = body_obj.modifiers.new(name="Body_Cloth_Collision", type='COLLISION')
   if hasattr(col_mod, "settings"):
       col_mod.settings.thickness_outer = 0.003
       col_mod.settings.cloth_friction = 0.5
   elif hasattr(col_mod, "collision_settings"):
       col_mod.collision_settings.thickness_outer = 0.003
       col_mod.collision_settings.cloth_friction = 0.5
   ```
2. **Fix Sandal Metatarsal Strap Scaling & Elevation at Extreme Heights (Challenger 2 finding)**:
   In `src/morphomesh/wardrobe.py` lines 1347-1348 (`generate_flat_strappy_sandals()`):
   - Use `s_len` (not raw `s`) for metatarsal strap longitudinal Y placement: `y_strap = -0.124 * s_len`, preventing overhang past the sole front.
   - Maintain proper vertical clearance above foot dorsal skin across all scales $H \in [1.40, 1.95]\text{m}$ so minimum clearance is $\ge +1.5\text{mm}$ and 0 penetrations occur.
3. Run test verification and ensure 100% pass:
   - `uv run pytest tests/test_challenger_m2_multiscale_sandals.py`
   - `uv run pytest tests/test_wardrobe_m2.py`
   - `uv run pytest tests/test_wardrobe_m3.py`
   - `uv run pytest tests/test_challenger_m2_empirical.py`
   - `uv run pytest tests/test_challenger_m2_sash.py`
   - `uv run pytest tests/test_challenger_m3_sandals.py`

## Input Files
- E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
- E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md
- E:\tool\mcp\MorphoMesh\.agents\m2_reviewer_1\handoff.md
- E:\tool\mcp\MorphoMesh\.agents\m2_challenger_2\handoff.md
- E:\tool\mcp\MorphoMesh\src\morphomesh\wardrobe.py

## Exclusive Write Ownership
- `src/morphomesh/wardrobe.py`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Working Directory
E:\tool\mcp\MorphoMesh\.agents\m2_worker_remediation_1

## Output File
E:\tool\mcp\MorphoMesh\.agents\m2_worker_remediation_1\handoff.md

## 2026-09-07T19:24:21Z
Received dispatch for M2 Remediation Worker (Iteration 2 Targeted Fixes):
- Fix Blender 4.5+ LTS Collision RNA Attribute in `src/morphomesh/wardrobe.py:get_wardrobe_script()`.
- Fix Sandal Metatarsal Strap Longitudinal Scaling and Vertical Elevation in `src/morphomesh/wardrobe.py:generate_flat_strappy_sandals()`.
- Run test verification and ensure 100% pass across all test suites.

