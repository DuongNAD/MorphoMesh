# Task Assignment: Worker M3-2 (Topology, Normal Winding & Scale Clearance Remediation)

## Mission
Remediate the 3 critical defects identified by Challenger M3-1 in `src/morphomesh/armor.py` and update test assertions in `tests/test_m3_adversarial_materials_and_armor.py` to confirm full resolution.

## Authoritative Reference
- Request: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`
- Project Scope: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`
- Challenger M3-1 Report: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_m3_1/handoff.md`
- Adversarial Test Suite: `tests/test_m3_adversarial_materials_and_armor.py`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## File Ownership
- `src/morphomesh/armor.py`
- `tests/test_m3_adversarial_materials_and_armor.py`
- `tests/test_materials_and_armor.py`

## Specific Defect Remediations
1. **Armor_Pauldron_R Non-Manifold Topology in Blender (Line 665)**:
   - In `src/morphomesh/armor.py` line 665:
     Fix `faces.append((og[i][j], og[i][j+1], og[i+1][j+1], og[i][j]))`
     To: `faces.append((og[i][j], og[i][j+1], og[i+1][j+1], og[i+1][j]))`.
   - Ensure all 6 armor plates in Blender have 0 non-manifold edges and `is_watertight is True`.

2. **Armor_Backplate Inverted Face Normals (Lines 509 & 786)**:
   - In `src/morphomesh/armor.py` lines 509 & 786:
     Reverse the vertex winding on outer backplate quads:
     Change `(og[i][j], og[i+1][j], og[i+1][j+1], og[i][j+1])`
     To: `(og[i][j], og[i][j+1], og[i+1][j+1], og[i+1][j])`.
     Ensure inner backplate quads point inward (toward bear):
     Change `(ig[i][j], ig[i][j+1], ig[i+1][j+1], ig[i+1][j])`
     To: `(ig[i][j], ig[i+1][j], ig[i+1][j+1], ig[i][j+1])`.
   - Verify signed volume in Blender is strictly positive ($> 0$).

3. **Adaptive Scapular Hump Sampling & Clearance Under Scaling (Lines 460-464 & 765-768)**:
   - In `src/morphomesh/armor.py`:
     Multiply all bounding box and search radius constants by `scale` (`sc`):
     `-0.15 * sc <= v[1] <= 0.45 * sc`, `abs(v[0]) <= 0.30 * sc`, `v[2] >= 0.80 * sc`, and `(0.08 * sc) ** 2`.
   - Also ensure that pauldron and armor plate clearances enforce an absolute minimum clearance:
     `max(0.015, base_clearance * scale)` or maintain $d_{\min} \ge 0.015$m across all scales (0.5x to 2.0x).
   - Ensure no body intersection or vertex collision occurs at scale 0.5x ($d_{\min} \ge 0.015$m).

4. **Adversarial Test Suite Conversion**:
   - In `tests/test_m3_adversarial_materials_and_armor.py`:
     Convert the bug reproduction tests (`test_armor_pauldron_r_blender_manifold_defect`, `test_armor_backplate_inverted_normals_defect`, and `test_scale_clearance_behavior`) into positive compliance assertions:
     * `Armor_Pauldron_R`: assert `non_manifold_edge_count == 0` and `is_watertight is True`.
     * `Armor_Backplate`: assert `signed_volume > 0`.
     * Scale 0.5x to 2.0x: assert `d_min >= 0.015` for all plates across all scales.

5. **Validation**:
   - Run `pytest -v tests/test_m3_adversarial_materials_and_armor.py`.
   - Run `pytest -v tests/test_materials_and_armor.py`.
   - Run full repo test suite `pytest -v tests/` (assert all tests pass with 0 failures).
   - Test in headless Blender 5.2.1 LTS.
   - Deliver handoff report at `.agents/worker_m3_2/handoff.md` and message orchestrator when done.
