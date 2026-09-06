# Dispatch — Explorer M4-Iter2-2 (Armor Clearance & BVH Penetration Specialist)

## 2026-09-06T06:41:58Z

### Working Directory
`/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m4_iter2_2`

### References
- Authoritative Request: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`
- Project Master Plan: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_gen2/PROJECT.md`
- Reviewer M4 Handoff Report: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/reviewer_m4/handoff.md`
- Gate Status: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_gen2/GATE_STATUS.md`

### Mission
Investigate and formulate the code-level remediation strategy for Reviewer M4's Findings 1 and 2 regarding pauldron mesh penetration, flawed vertex clearance checking, and the facade test in `tests/test_bear_anatomy.py`.

### Specific Technical Investigation Questions
1. Finding 2: In `src/morphomesh/armor.py`, why do `Armor_Pauldron_L` and `Armor_Pauldron_R` penetrate -33.6 mm into the bear torso geometry (9 vertices inside each, minimum surface distance 0.0002m)? What exact adjustments to `cx`, shoulder radial radius/height, clearance offset $\Delta r$, and outer/inner shell boundaries are required so that true BVH point-to-surface distance satisfies $d_{\min} \ge 0.015\text{m}$ (expecting 0.020m - 0.035m) with 0 inside vertices across all scales?
2. Finding 2: In `verify_bear_anatomy.py:419-427`, why did vertex-to-vertex Euclidean distance fail to detect pauldron penetration? How should the clearance check be updated using `mathutils.bvhtree.BVHTree.FromPolygons` to evaluate true point-to-surface signed distance in Blender headless mode, with fallback for standalone Python?
3. Finding 1: In `tests/test_bear_anatomy.py:209-219`, `test_pauldron_clearance_and_watertightness` only checks `len > 50`. Formulate a genuine implementation that asserts:
   - Watertightness: 0 non-manifold edges (`is_watertight is True`)
   - Surface clearance: $d_{\min} \ge 0.015\text{m}$ from bear mesh vertices and polygons
   - Positive signed volume: $V > 0$.

### Output Requirements
Do NOT edit production code. Write a thorough investigation report with proposed code patches at:
`/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m4_iter2_2/survey_report.md`
And write `handoff.md` with your summary, then message the orchestrator.
