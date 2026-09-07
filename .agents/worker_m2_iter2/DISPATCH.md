## 2026-09-07T05:02:42Z

You are Worker M2 Iteration 2: Milestone 2 Remediation Implementer.
Your working directory is: e:\tool\mcp\MorphoMesh\.agents\worker_m2_iter2
Your parent orchestrator conversation ID is: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9
The authoritative user request is at: e:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md (specifically § 2026-09-07T03:34:32Z). You MUST read this file first.
The project scope document is at: e:\tool\mcp\MorphoMesh\PROJECT.md (specifically Milestone 2).
The Gate status document is at: e:\tool\mcp\MorphoMesh\.agents\orchestrator_inspector_1\GATE_STATUS.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

File Ownership:
You exclusively own and may edit the following files:
- `src/morphomesh/camera_rig.py`
- `src/morphomesh/__init__.py`
- `blender_addon/morphomesh/listener.py`
- `src/morphomesh/blender_bridge.py`
- `tests/test_inspector_camera.py`
- `tests/test_multiview_rendering.py`
- `tests/test_adversarial_viewport_capture.py`
You MUST NOT edit any other implementation files.

Reference Input Artifacts (Read these for exact blueprints before coding):
- `e:\tool\mcp\MorphoMesh\.agents\explorer_m2_iter2_1\handoff.md` (Authentic look-at basis R, Shepperd quaternion, XYZ Euler extraction, Euler.to_matrix transposition fix, and recursive calculate_hierarchy_bounds)
- `e:\tool\mcp\MorphoMesh\.agents\explorer_m2_iter2_2\handoff.md` (De-certifying tests in test_inspector_camera.py and test_multiview_rendering.py, valid 70-byte PNG bitstream)
- `e:\tool\mcp\MorphoMesh\.agents\explorer_m2_iter2_3\handoff.md` (Decoupling pydantic in __init__.py, _ensure_morphomesh_src() in listener.py, removing forbidden imports in blender_bridge.py, and addon deployment)

Remediation Tasks:
1. `src/morphomesh/camera_rig.py`:
   - Replace fake `Quaternion` / pitch-yaw list facade with authentic look-at tracking $R = [\hat{r} \mid \hat{u} \mid -\hat{f}]$ and Shepperd quaternion conversion matching Blender's `to_track_quat('-Z', 'Y')`.
   - Ensure `calculate_spherical_camera_position` produces exact XYZ Euler angles matching Blender 4.5 bit-for-bit (`three_quarter` produces [75.0°, 0.0°, 45.0°], `top` produces [2.0°, 0.0°, 0.0°], miss distance = 0).
   - Fix `Euler.to_matrix()` transposition and 3x3 `Matrix.__matmul__`.
   - Implement `calculate_hierarchy_bounds` with recursive `children`/`children_recursive` traversal for Empty and Armature parents (keep alias `calculate_character_bounds = calculate_hierarchy_bounds`).
   - Replace truncated 29-byte PNG fallback with the valid 70-byte transparent 1x1 RGBA PNG bitstream (`FALLBACK_PNG_BYTES`).
   - Expose `encode_image_to_base64(path)`.
2. `src/morphomesh/__init__.py`:
   - Guard `models.py` import so importing `camera_rig.py` inside Blender's bundled Python does not trigger `ModuleNotFoundError: No module named 'pydantic'`.
3. `blender_addon/morphomesh/listener.py`:
   - Add centralized multi-tiered path discovery `_ensure_morphomesh_src()`.
   - Catch `ImportError` in `capture_multi_angle_inspection` and provide in-addon fallback loop.
   - Deploy the updated `listener.py` into `%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\morphomesh\listener.py` and trigger hot reload if reachable on port 9876.
4. `src/morphomesh/blender_bridge.py`:
   - Remove `import sys` and `import os` from headless scripts in `_generate_headless_script()`; pass `PYTHONPATH` via subprocess environment.
   - Ensure fallback scripts sent to `execute_code` over socket do not trigger forbidden imports in `AddonSecurityValidator`.
5. Test Suites:
   - In `tests/test_inspector_camera.py`: De-certify `test_look_at_forward_ray_hits_target_center` to use $R(\text{cam\_rot}) \cdot [0, 0, -1]$. De-certify `test_rotation_matrix_orthonormality_and_up_vector`. Add test verifying `calculate_hierarchy_bounds` on Empty/Armature parent with child meshes.
   - In `tests/test_multiview_rendering.py`: De-certify `TestDualModeExecution` and `test_missing_file_base64_grace`.
   - In `tests/test_adversarial_viewport_capture.py`: Update fallback PNG test to assert valid PIL image opening.
6. Verification:
   - Run: `.venv\Scripts\pytest.exe -v tests/test_inspector_camera.py tests/test_multiview_rendering.py tests/test_adversarial_camera_math.py tests/test_adversarial_viewport_capture.py`
   - Run full regression: `.venv\Scripts\pytest.exe -v tests/test_bridge_socket_parity.py tests/test_m1_adversarial_socket.py tests/test_adversarial_dispatch_m1_2.py tests/test_blender_bridge.py`
   - Verify 100% pass rate.
7. Reporting:
   - Update progress in `e:\tool\mcp\MorphoMesh\.agents\worker_m2_iter2\progress.md`.
   - Write comprehensive handoff report to `e:\tool\mcp\MorphoMesh\.agents\worker_m2_iter2\handoff.md`.
   - Send completion message to parent orchestrator (`577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`).
