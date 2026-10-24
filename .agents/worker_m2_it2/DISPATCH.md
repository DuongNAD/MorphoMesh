## 2026-09-07T15:25:07Z

You are a Worker subagent (Worker M2 Iteration 2: Wardrobe Geometric Remediation Implementer) for MorphoMesh Milestone M2.
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\worker_m2_it2

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY FIRST STEP:
Read the following authoritative specification and blueprint files before modifying any code:
1. ORIGINAL_REQUEST.md at: E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
2. PROJECT.md at: E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_anatomy_gen2\PROJECT.md
3. Explorer M2.1 It2 Handoff at: E:\tool\mcp\MorphoMesh\.agents\explorer_m2_it2_1\handoff.md
4. Explorer M2.2 It2 Handoff at: E:\tool\mcp\MorphoMesh\.agents\explorer_m2_it2_2\handoff.md
5. Explorer M2.3 It2 Handoff at: E:\tool\mcp\MorphoMesh\.agents\explorer_m2_it2_3\handoff.md

EXCLUSIVE FILE OWNERSHIP:
You exclusively own and may edit:
- `src/morphomesh/wardrobe.py`
- Test files: `tests/test_wardrobe_m2.py`, `tests/test_challenger_m2_sash.py`, `tests/test_challenger_m2_empirical.py`

SPECIFIC IMPLEMENTATION TASKS:
Apply the exact drop-in replacement snippets formulated by the three Iteration 2 Explorers:
1. **Skirt Normal Vector Winding Order**:
   - In `src/morphomesh/wardrobe.py` (`generate_dress_organic_skirt`), change the quad face definition from clockwise `mesh.add_quad(v_bl, v_br, v_tr, v_tl)` to counter-clockwise `mesh.add_quad(v_bl, v_tl, v_tr, v_br)`. Verify that 100% of the 1440 skirt quads have outward-pointing face normals.
2. **Posterior Sash Band Clearance**:
   - In `src/morphomesh/wardrobe.py` (`generate_dress_waist_sash`), add lower ring flare compensation ($\Delta r = +0.0020\cdot s$, $\Delta yo = +0.0025\cdot s$ weighted by $\max(0.0, 1.0 - 2.0 u_z)$) so that posterior sash clearance at the lowest ring ($Z=1.0275\cdot s$) is strictly $\ge +2.5\text{mm}$ across all angles and parameters, eliminating any Z-fighting or penetration with the flared skirt.
3. **Bodice Inframammary Chord Clearance Compensation**:
   - In `src/morphomesh/wardrobe.py` (`generate_dress_bodice`), eliminate the inward fold tuck and apply the inframammary chord clearance compensation from Explorer M2.2 It2 handoff ($c_{\text{waist}}=3.8\text{mm}, c_{\text{imf}}=4.5\text{mm}, c_{\text{mid}}=1.8\text{mm}$), ensuring signed distance to body is strictly $\ge +1.5\text{mm}$ across all vertices with 0 penetrations.
4. **Spaghetti Strap Parameter Decoupling**:
   - In `src/morphomesh/wardrobe.py` (`generate_dress_bodice`), decouple spaghetti strap X coordinates and shoulder arch keyframes from chest volume scaling ($k_{\text{chest}}$), scaling with shoulder width ($k_{\text{shoulder}}$) instead. Verify zero strap skin penetration even under extreme bust scaling ($k_{\text{chest}}=0.70$).
5. **Barrel Knot 3-Quad Closed Manifold Caps**:
   - In `src/morphomesh/wardrobe.py` (`generate_dress_waist_sash`), add the missing 3rd quad spanning vertices $(2, 3, 4, 5)$ on both bottom and top caps of the barrel cuff knot: `mesh.add_quad(R0[2], R0[5], R0[4], R0[3])` and `mesh.add_quad(R3[2], R3[3], R3[4], R3[5])`. Verify that all boundary edges are eliminated and the knot is a strictly closed 2-manifold.
6. **Streamer Tip Bias Cut**:
   - In `src/morphomesh/wardrobe.py` line 773, replace the dead-code formula with `tip_bias = (0.5 * w) if step == streamer_steps else 0.0`, ensuring a functional $45^\circ$ bias cut across ribbon width.
7. **Testing & Verification**:
   - Update `tests/test_wardrobe_m2.py` with an explicit edge-manifoldness check on the knot caps (`open_boundary_edges == 0`).
   - Remove `@pytest.mark.xfail` markers from `tests/test_challenger_m2_sash.py` and `tests/test_challenger_m2_empirical.py`.
   - Run tests: `uv run pytest tests/test_wardrobe.py tests/test_wardrobe_m2.py tests/test_challenger_m2_sash.py tests/test_challenger_m2_empirical.py -v`.
   - Ensure 100% PASS across all suites with 0 FAIL and 0 XFAIL.

DELIVERABLES:
- Write `E:\tool\mcp\MorphoMesh\.agents\worker_m2_it2\changes.md`.
- Write `E:\tool\mcp\MorphoMesh\.agents\worker_m2_it2\handoff.md`.
- Update `E:\tool\mcp\MorphoMesh\.agents\worker_m2_it2\progress.md`.
- Send completion message to parent with test run commands and passing outputs.
