## 2026-09-07T06:17:32Z
You are Worker M3 Iteration 2: Milestone 3 Remediation Implementer.
Your working directory is: e:\tool\mcp\MorphoMesh\.agents\worker_m3_iter2
Your parent orchestrator conversation ID is: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9
The authoritative user request is at: e:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md (specifically § 2026-09-07T03:34:32Z). You MUST read this file first.
The project scope document is at: e:\tool\mcp\MorphoMesh\PROJECT.md (specifically Milestone 3).
The Gate status document is at: e:\tool\mcp\MorphoMesh\.agents\orchestrator_inspector_1\GATE_STATUS.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
You exclusively own and may edit the following files:
- `src/morphomesh/visual_critic.py`
- `tests/test_visual_critic.py`
- `tests/test_adversarial_bvh_penetration.py`
You MUST NOT edit any other implementation files.

Reference Input Artifacts (Read these for exact blueprints before coding):
- `e:\tool\mcp\MorphoMesh\.agents\explorer_m3_iter2_1\handoff.md` (3-tier geometric filter for skin burst, normal alignment filtering for forward penetration)
- `e:\tool\mcp\MorphoMesh\.agents\explorer_m3_iter2_2\handoff.md` (Shrinkwrap offset formula, Comb Brush recommendations, Möller coplanar 2D intersection, quad fan triangulation)
- `e:\tool\mcp\MorphoMesh\.agents\explorer_m3_iter2_3\handoff.md` (Canonical benchmark_defect_detection export, dual-schema dictionary, test additions, verbatim handoff protocol)
- `e:\tool\mcp\MorphoMesh\.agents\auditor_m3_qa_1\handoff.md` (Forensic auditor evidence report)
- `e:\tool\mcp\MorphoMesh\.agents\reviewer_m3_qa_1\handoff.md` (Reviewer M3_1 findings report)

Remediation Tasks:
1. Forensic Audit Integrity Rectification (`src/morphomesh/visual_critic.py`):
   - Export `benchmark_defect_detection` function (or alias to `run_defect_detection_benchmark`).
   - Standardize returned dictionary to include all required keys:
     'accuracy': 100.0, 'accuracy_ratio': 1.0, 'false_positive_rate': 0.0, 'tests_run': 9, 'total_states': 9, 'correct_classifications': 9, 'clean_states_tested': 4, 'defective_states_tested': 5, 'true_positives': 5, 'true_negatives': 4, 'false_positives': 0, 'false_negatives': 0.
   - Ensure `benchmark_defect_detection` and `run_defect_detection_benchmark` are in `__all__`.
   - Test directly:
     .venv\Scripts\python.exe -c "from morphomesh.visual_critic import benchmark_defect_detection; stats = benchmark_defect_detection(); print(stats); assert stats['accuracy'] >= 0.95 and stats['false_positive_rate'] == 0.0"
2. Skin Burst False-Positive Remediation (`src/morphomesh/visual_critic.py`):
   - In `evaluate_mesh_penetration` (lines 709–725), replace the unconstrained Z-envelope check with the 3-tier geometric filter from `explorer_m3_iter2_1`:
     * Height clamping: `g_min_z + 0.002 <= b_j[2] <= g_max_z - 0.002` so exposed body geometry above the collar or below the hem is never falsely flagged as skin burst.
     * Dual-sided surface normal alignment: Verify `_dot_product(b_norm, norm_g) > 0.3` (where `b_norm` is body vertex normal and `norm_g` is nearest garment surface normal).
     * Flag skin burst only when the body surface authentically pierces outward through the garment from the inside.
3. Forward Penetration Normal Alignment Filtering (`src/morphomesh/visual_critic.py`):
   - In `evaluate_mesh_penetration` (lines 692–708), compute garment vertex normal and require `_dot_product(g_norm, norm_b) > 0.3` (or cos alpha < -0.3 where inward garment orientation faces outward body normal).
4. Actionable Recommendations Remediation (`src/morphomesh/visual_critic.py`):
   - Shrinkwrap modifier: set `offset = round(1.25 * max_depth_m + 0.001, 4)` and in guidance include "Apply vertex weight proximity or Laplacian smoothing to the penetration vertex group".
   - Hair grooming: attach `CURVE_SCULPT_COMB_DEFLECTION` recommendations prescribing Curves Sculpt mode Comb Brush with front/side projection and 2.0mm collision clearance.
5. Tomas Möller 2D Coplanar Triangle-Triangle Overlap (`src/morphomesh/visual_critic.py`):
   - In `triangle_triangle_intersection_moller`, replace `max_d < 1e-8: return False` with authentic 2D coplanar intersection testing (project onto dominant coordinate plane, test 9 edge-edge crossings and point-in-triangle containment).
   - In `tests/test_adversarial_bvh_penetration.py` line 272, update `assert res is False` to `assert res is True` for overlapping coplanar triangles, and add a test case for disjoint coplanar triangles asserting `res is False`.
6. Quad Mesh Divergence Volume (`src/morphomesh/visual_critic.py`):
   - In `compute_mesh_signed_volume`, decompose polygons into triangle fans: `for i in range(1, len(f) - 1): tri = (f[0], f[i], f[i + 1])`.
7. Testing & Verification:
   - In `tests/test_visual_critic.py`, add tests verifying `benchmark_defect_detection` schema and importability, and exposed anatomy skin burst zero-false-positive test.
   - Run: .venv\Scripts\pytest.exe -v tests/test_visual_critic.py tests/test_adversarial_bvh_penetration.py tests/test_adversarial_critic_benchmark.py
   - Run full regression: .venv\Scripts\pytest.exe -v tests/test_inspector_camera.py tests/test_multiview_rendering.py tests/test_adversarial_camera_math.py tests/test_adversarial_viewport_capture.py tests/test_bridge_socket_parity.py tests/test_visual_critic.py tests/test_adversarial_bvh_penetration.py tests/test_adversarial_critic_benchmark.py
8. Reporting:
   - Run the direct benchmark command in PowerShell and paste the RAW, VERBATIM output directly into Section 5 of `e:\tool\mcp\MorphoMesh\.agents\worker_m3_iter2\handoff.md`.
   - Update `progress.md` and notify parent orchestrator via `send_message`.
