# Dispatch for M1 Remediation Worker (Iteration 2 Fixes)

## Mission
Apply the three targeted remediations formulated by the Iteration 2 Explorers in `src/morphomesh/human_generator.py`:
1. **Axilla Continuity Scaling**:
   In `src/morphomesh/human_generator.py` around line 655, anchor the arm span scaling to the expanded shoulder width:
   `transformed_verts[i][0] = sign_x * (0.18 * s * k_shoulder + dist_out * k_arm)`
   (Eliminating the boundary crossover that inverted face 20360 under `realistic_female`).
2. **Micro-Relaxation Offsets for Minimal Face Area**:
   Apply the optimized 20-vertex tangential micro-relaxation displacements from `E:\tool\mcp\MorphoMesh\.agents\m1_explorer_micro_area_iter2_1\relaxation_fix.patch` (or handoff report) in `load_anatomical_base_mold()`.
3. **API Interface Signature Alignment**:
   Apply the signature alignment and `resolve_human_anatomy_config()` from `E:\tool\mcp\MorphoMesh\.agents\m1_explorer_api_signatures_iter2_1\api_signature_alignment.patch` (or handoff report).
4. Run tests:
   - `uv run pytest tests/test_m1_challenger_2_stress.py`
   - `uv run python tests/run_m1_challenger_2_audit.py`
   - `uv run pytest tests/test_m1_anatomical_base_mold.py`
   - `uv run pytest tests/test_m1_challenger_1_anatomy_contours.py`
   Ensure 100% of these tests pass.

## Input Files
- E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
- E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md
- E:\tool\mcp\MorphoMesh\.agents\m1_challenger_2\handoff.md
- E:\tool\mcp\MorphoMesh\.agents\m1_explorer_axilla_scaling_iter2_1\handoff.md
- E:\tool\mcp\MorphoMesh\.agents\m1_explorer_micro_area_iter2_1\handoff.md
- E:\tool\mcp\MorphoMesh\.agents\m1_explorer_micro_area_iter2_1\relaxation_fix.patch
- E:\tool\mcp\MorphoMesh\.agents\m1_explorer_api_signatures_iter2_1\handoff.md
- E:\tool\mcp\MorphoMesh\.agents\m1_explorer_api_signatures_iter2_1\api_signature_alignment.patch

## Exclusive Write Ownership
- `src/morphomesh/human_generator.py`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Working Directory
E:\tool\mcp\MorphoMesh\.agents\m1_worker_remediation_1

## Output File
E:\tool\mcp\MorphoMesh\.agents\m1_worker_remediation_1\handoff.md
