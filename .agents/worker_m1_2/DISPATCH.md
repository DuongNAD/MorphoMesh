# Dispatch Assignment: Worker M1-2 (Topology & Normal Winding Remediation)

**Identity**: teamwork_preview_worker
**Assigned Task**: Remediation of Polar Degenerate Faces and Inverted Normals (Milestone M1 Iteration 2)
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m1_2`
**Authoritative Request**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`
**Project Plan**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`
**Input Reports & Patches**:
- Explorer M1-Iter2-1: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_iter2_1/survey_report.md` (polar triangle fans for `add_sphere` & `add_ellipsoid`)
- Explorer M1-Iter2-2: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_iter2_2/inverted_normals.patch` (`add_box` & `add_cylinder` counter-clockwise winding)
- Explorer M1-Iter2-3: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_iter2_3/blender_script_fix.patch` (`get_blender_generation_script()` normal winding & polar fans)
- Adversarial Test Suite: `tests/test_m1_topology_and_facial_stress.py`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## File Ownership
- `src/morphomesh/inference_adapter.py`
- `src/morphomesh/creature_generator.py`
- `tests/test_m1_topology_and_facial_stress.py`
- `tests/test_anatomy_generator.py`

## Objectives
1. Apply the polar triangle fan fix to `add_sphere` and `add_ellipsoid` in `src/morphomesh/inference_adapter.py` per Explorer M1-Iter2-1's outward formulas:
   - North Pole: `add_triangle(north_idx, ring_1[s], ring_1[s + 1])`
   - South Pole: `add_triangle(ring_last[s], south_idx, ring_last[s + 1])`
   - Intermediate bands: `add_quad(...)`
2. Apply the counter-clockwise vertex winding order to `add_box` and `add_cylinder(axis="Y")` per Explorer M1-Iter2-2's patch.
3. Apply the `get_blender_generation_script()` patch from Explorer M1-Iter2-3 in `src/morphomesh/creature_generator.py`.
4. Ensure `tests/test_m1_topology_and_facial_stress.py` passes 100% (11/11 tests pass).
5. Run full test suite: `pytest -v tests/` (assert 240+ tests pass with 0 failures).
6. Verify in Blender 5.2.1 LTS that `Bear_Base_Mesh` has exactly 0 zero-area polygons and 0 inverted normals.
7. Deliver handoff report to `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m1_2/handoff.md` and message orchestrator.

## 2026-09-05T16:15:58Z
You are Worker M1-2 (Topology & Normal Winding Remediation Specialist).
Your working directory is `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m1_2`.
Read your dispatch assignment at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m1_2/DISPATCH.md`, `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`, and `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`.
Also consult:
- `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_iter2_1/survey_report.md`
- `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_iter2_2/inverted_normals.patch`
- `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m1_iter2_3/blender_script_fix.patch`
- `tests/test_m1_topology_and_facial_stress.py`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
- `src/morphomesh/inference_adapter.py`
- `src/morphomesh/creature_generator.py`
- `tests/test_m1_topology_and_facial_stress.py`
- `tests/test_anatomy_generator.py`

Execute the remediation:
1. Implement the polar triangle fan fix for `add_sphere` and `add_ellipsoid` in `src/morphomesh/inference_adapter.py` per Explorer M1-Iter2-1's outward formulas.
2. Implement counter-clockwise vertex winding for `add_box` and `add_cylinder(axis="Y")` per Explorer M1-Iter2-2.
3. Apply normal winding and polar fans to `get_blender_generation_script()` in `src/morphomesh/creature_generator.py` per Explorer M1-Iter2-3.
4. Run `pytest -v tests/test_m1_topology_and_facial_stress.py` (all 11 tests must PASS).
5. Run full test suite `pytest -v tests/` (assert all tests pass with 0 failures).
6. Verify in Blender 5.2.1 LTS that zero-area polygons drop to 0 and all normals point outward.
7. Deliver handoff report at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m1_2/handoff.md` and message orchestrator when done.
