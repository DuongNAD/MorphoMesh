# Dispatch — Worker M4 Remediation (Milestone M4 Iteration 2)

## Working Directory
`/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m4_remediation`

## References
- Authoritative Request: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`
- Project Master Plan: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_gen2/PROJECT.md`
- Reviewer M4 Critical Findings: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/reviewer_m4/handoff.md`
- Explorer 1 (Anatomy & Continuity) Report: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m4_iter2_1/survey_report.md`
- Explorer 2 (Pauldron BVH Clearance) Report: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m4_iter2_2/survey_report.md`
- Explorer 3 (Test & Verification Infra) Report: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m4_iter2_3/survey_report.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Assigned Tasks
1. **Finding 3 Remediation in `src/morphomesh/inference_adapter.py` & `src/morphomesh/creature_generator.py`**:
   - In `inference_adapter.py`: Add `cap_ends: bool = False, cap_bottom: Optional[bool] = None, cap_top: Optional[bool] = None` to `MeshGeometry.add_cylinder`.
   - In `inference_adapter.py`: Upgrade `add_articulated_head` from box shapes to lofted rounded rostrum, organic rhinarium, almond eyelid folds, and cupped pinnae while strictly preserving nostril nares, dentition, and mouth cavity constraints.
   - In `creature_generator.py`: Fix front paw `py = -0.35*s` with `foot_center = (px, py - 0.05*s, 0.04*s)` and `foot_size = (0.24*s, 0.24*s, 0.08*s)`. Lower forearm base to $z = 0.03*s$ ($height = 0.40*s$) with `cap_ends=True`. Adjust hind shank to $y = 0.38*s, z = 0.03*s$ with `cap_ends=True`. Update `get_blender_generation_script` accordingly.
2. **Finding 2 Remediation in `src/morphomesh/armor.py` & `src/morphomesh/blender_bridge.py`**:
   - In `armor.py`: Set $cx = \pm 0.350*s$, $cy = -0.250*s$, $cz = 0.980*s$, $ry = 0.170*s + \Delta r$. Set $\phi_L \in [-0.25\pi, 0.55\pi]$ and $\phi_R \in [0.45\pi, 1.25\pi]$. Remove reversed quad winding for R (use unified outward quad winding).
   - In `blender_bridge.py`: Update `make_pauldron` in `generate_war_armor` to match new parameters and unified winding.
3. **Finding 1 Remediation in `tests/test_bear_anatomy.py` & `verify_bear_anatomy.py`**:
   - In `tests/test_bear_anatomy.py`: Replace dummy `test_pauldron_clearance_and_watertightness` with genuine 2-manifold closed shell check, positive signed volume assertion ($V > 0$), and true surface clearance assertion ($d_{\min} \ge 0.015\text{m}$).
   - In `verify_bear_anatomy.py`: Upgrade clearance check using `mathutils.bvhtree.BVHTree.FromPolygons` in Blender mode (evaluating signed distance, asserting 0 inside vertices and $d_{\min} \ge 0.015\text{m}$) with vectorized point-to-triangle projection fallback in standalone Python.
4. **Master Scene Re-Assembly & Beauty Rendering (`scripts/assemble_and_render_armored_war_bear.py`)**:
   - In `assemble_and_render_armored_war_bear.py`: Set `scene.cycles.curves_shape = "STRIP"`, assign `Mat_Bear_Fur` to fur particle systems, keep `ribbon_obj.hide_render = True`, and ensure proper camera framing and lighting.
   - Execute scene assembly and export:
     * Overwrite `examples/Armored_War_Bear_HD.blend`
     * Overwrite `examples/Armored_War_Bear_HD.glb`
     * Re-render the 4 beauty renders in `examples/renders/`
5. **Verification**:
   - Run `pytest -v tests/` (all tests must pass with exit code 0).
   - Run `python3 verify_bear_anatomy.py` (must pass 100%).
   - Run headless Blender verification: `/Applications/Blender.app/Contents/MacOS/Blender --background examples/Armored_War_Bear_HD.blend --python verify_bear_anatomy.py` (must pass 100%).
   - Verify 0 inside vertices and $d_{\min} \ge 0.015\text{m}$ on pauldrons.

## Output Requirements
Write `handoff.md` with full execution outputs, passing test logs, and verification commands, then message the orchestrator.

## 2026-09-06T04:08:02Z
You are Worker M4 Remediation.
Your working directory is: /Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m4_remediation
Mission:
Implement the complete remediation for Reviewer M4's Findings 1, 2, and 3 using the concrete code diffs and mathematical parameters formulated by Explorers 1, 2, and 3.

