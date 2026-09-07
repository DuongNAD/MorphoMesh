## 2026-09-07T05:39:11Z

You are Worker M3: Closed-Loop Visual Quality Critique Engine Implementer.
Your working directory is: e:\tool\mcp\MorphoMesh\.agents\worker_m3
Your parent orchestrator conversation ID is: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9
The authoritative user request is at: e:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md (specifically § 2026-09-07T03:34:32Z). You MUST read this file first.
The project scope document is at: e:\tool\mcp\MorphoMesh\PROJECT.md (specifically Milestone 3).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
You exclusively own and may edit the following files:
- `src/morphomesh/visual_critic.py` (New module)
- `src/morphomesh/models.py`
- `src/morphomesh/blender_bridge.py`
- `blender_addon/morphomesh/listener.py`
- `tests/test_visual_critic.py` (New test suite)
You MUST NOT edit any other implementation files.

Reference Input Artifacts (Read these for exact blueprints before coding):
- `e:\tool\mcp\MorphoMesh\.agents\explorer_m3_1\handoff.md` (Penetration BVH signed distance, hair curve audit, and PurePythonBVHTree spatial index)
- `e:\tool\mcp\MorphoMesh\.agents\explorer_m3_2\handoff.md` (Anthropometric proportions, joint volume conservation, dihedral creasing, slice volume math)
- `e:\tool\mcp\MorphoMesh\.agents\explorer_m3_3\handoff.md` (Pydantic v2 schemas, bridge/listener RPC, 4 procedural defect injection fixtures, test plan)

Milestone 3 Tasks:
1. `src/morphomesh/models.py`:
   - Add Pydantic v2 schemas: `DefectSeverity`, `DefectCategory`, `ActionableRecommendation`, `DefectItem`, `VisualCritiqueInput`, `VisualCritiqueOutput` with backward-compatible normalizers as blueprinted in explorer_m3_3/handoff.md.
2. `src/morphomesh/visual_critic.py`:
   - Implement `evaluate_mesh_penetration`: BVH signed distance $s_i = (w_i - p_i) \cdot \hat{n}_i < -0.5\text{mm}$, normal alignment filter, reverse penetration (skin burst), and triangle face overlap.
   - Implement `evaluate_hair_grooming_intersections`: Submerged roots ($s < -1\text{mm}$), detached roots ($s > +4\text{mm}$), hair shaft penetration ($s_{\text{eff}} < -0.5\text{mm}$), clothing clipping.
   - Implement `PurePythonBVHTree`: Self-contained offline AABB/BVH tree with exact point-to-triangle distance, ray-triangle intersection, and triangle overlap for 100% offline pytest execution without `mathutils.bvhtree`.
   - Implement `evaluate_body_proportions`: Total height, head height ($H_{\text{total}}/H_{\text{head}}$ against `realistic_human`, `stylized_heroine`, `chibi_petite` presets), arm span to height ratio, shoulder-to-hip breadth ratio.
   - Implement `evaluate_rig_skinning_deformation`: Volume conservation ($\rho_V = V_{\text{posed}} / V_{\text{rest}}$) and acute dihedral angle creasing ($\cos\theta < -0.85$).
   - Implement `run_visual_critique(input_data: VisualCritiqueInput) -> VisualCritiqueOutput`.
   - Implement procedural defect injection fixtures and clean baselines: garment penetration, proportion skew, joint skinning collapse, and hair root clipping with ground truth metrics demonstrating >95% accuracy.
3. Hook into `src/morphomesh/blender_bridge.py` and `blender_addon/morphomesh/listener.py`:
   - Add client method `critique_visual_quality()` in `blender_bridge.py`.
   - Implement `morphomesh.critique_visual_quality` RPC handler in `listener.py` with native in-addon fallback.
   - Sync `listener.py` to `%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\morphomesh\listener.py`.
4. Create `tests/test_visual_critic.py`:
   - Implement comprehensive unit and integration tests per explorer_m3_3 test plan covering all 4 defect categories, schema validation, bridge dispatch, and procedural defect injection fixtures.
5. Verification:
   - Run: `.venv\Scripts\pytest.exe -v tests/test_visual_critic.py`
   - Run full regression: `.venv\Scripts\pytest.exe -v tests/test_inspector_camera.py tests/test_multiview_rendering.py tests/test_adversarial_camera_math.py tests/test_adversarial_viewport_capture.py tests/test_bridge_socket_parity.py tests/test_m1_adversarial_socket.py tests/test_adversarial_dispatch_m1_2.py tests/test_blender_bridge.py`
   - Verify 100% pass rate.
6. Reporting:
   - Update progress in `e:\tool\mcp\MorphoMesh\.agents\worker_m3\progress.md`.
   - Write comprehensive handoff report to `e:\tool\mcp\MorphoMesh\.agents\worker_m3\handoff.md`.
   - Send completion message to parent orchestrator (`577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`).
