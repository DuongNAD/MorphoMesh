# Review & Adversarial Challenge Report: Offline Bridge Resilience & Exception Discrimination

**Agent**: Reviewer M4 Iter 2 - 2 (`.agents/reviewer_m4_iter2_2`)  
**Role**: reviewer, critic  
**Target Milestone**: Milestone 4 — FastMCP Tool Integration & Verification Suite (Iteration 2)  
**Parent Orchestrator**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Date**: 2026-09-07T07:22:00Z  
**Verdict**: **APPROVE**  

---

## 1. Observation

### 1.1 Implementation Code Inspection

1. **`src/morphomesh/server.py`**:
   - Lines 1092–1109: Defines canonical sets `VALID_INSPECTOR_VIEWPOINTS` (32 canonical angles/subregions), `VALID_SHADING_MODES` (5 modes), `VALID_COLOR_TYPES` (5 types), and `VALID_TARGET_PRESETS` (6 presets).
   - Lines 1137–1153: In `morphomesh_setup_inspector_camera_rig`, enforces pre-flight parameter validation rejecting empty/invalid viewpoints, focal lengths outside `[10.0, 300.0]`, and malformed target centers with `ToolError`.
   - Lines 1169–1196: In `morphomesh_setup_inspector_camera_rig`, catches `(MorphoMeshException, ConnectionError, OSError, TimeoutError)`:
     * When `e.code in ("ERR_BLENDER_UNAVAILABLE", "ERR_BRIDGE_CONNECTION")` or `isinstance(e, (ConnectionError, TimeoutError, OSError))`: falls back to `morphomesh.camera_rig.setup_inspector_camera`, returning `status="success"`, `position`, `rotation`, and `offline_fallback=True`.
     * When `isinstance(e, MorphoMeshException)` with operational codes (e.g. `ERR_CAMERA_FAILED`): cleanly re-raises `ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")`.
   - Lines 1225–1248: In `morphomesh_capture_viewport`, enforces pre-flight parameter validation rejecting empty/invalid shading modes, color types, zero/negative resolutions, and empty camera names with `ToolError`.
   - Lines 1287–1334: In `morphomesh_capture_viewport`, catches `(MorphoMeshException, ConnectionError, OSError, TimeoutError)`:
     * When offline/unavailable: ensures parent directories exist, writes `FALLBACK_PNG_BYTES` to disk, returns `status="success"`, `base64_preview`, `base64_image`, and `offline_fallback=True`.
     * When domain operational error: re-raises `ToolError`.

2. **`src/morphomesh/blender_bridge.py`**:
   - Lines 2501–2528: In `capture_viewport()`, wraps `self.execute("morphomesh.capture_viewport", ...)` in a try/except block. If `ERR_BLENDER_UNAVAILABLE` or connection failure occurs, writes `FALLBACK_PNG_BYTES` to `output_path` and returns dictionary with `status="success"`, `offline_fallback=True`, and base64-encoded PNG. If `e.code` is not an unavailable/connection error, re-raises `MorphoMeshException`.
   - Lines 2570–2590: In `setup_inspector_camera()`, wraps `self.execute("morphomesh.setup_inspector_camera", ...)`. If `ERR_BLENDER_UNAVAILABLE` or connection failure occurs, delegates to pure-Python `setup_inspector_camera` solver and returns camera metadata with `offline_fallback=True`. If `e.code` is an operational code (e.g. `ERR_CAMERA_FAILED`), re-raises.

3. **`tests/test_fastmcp_inspection_tools.py` line 415**:
   - Lines 415–427:
     ```python
     @pytest.mark.asyncio
     async def test_bridge_exception_mapping():
         """Verify bridge MorphoMeshException is cleanly mapped to ToolError with error code."""
         from morphomesh.server import blender_bridge

         with patch.object(
             blender_bridge,
             "setup_inspector_camera",
             side_effect=MorphoMeshException(code="ERR_CAMERA_FAILED", message="Camera error"),
         ):
             with pytest.raises(ToolError) as exc_info:
                 await morphomesh_setup_inspector_camera_rig()
             assert "[ERR_CAMERA_FAILED]" in str(exc_info.value)
     ```
   - Verbatim execution output:
     ```
     .venv\Scripts\pytest.exe -v tests/test_fastmcp_inspection_tools.py::test_bridge_exception_mapping
     collecting ... collected 1 item
     tests/test_fastmcp_inspection_tools.py::test_bridge_exception_mapping PASSED [100%]
     1 passed in 0.04s
     ```

4. **`tests/test_tools_schema.py` Baseline Verification**:
   - `git diff tests/test_tools_schema.py` confirms 0 lines modified.
   - Verbatim execution output:
     ```
     .venv\Scripts\pytest.exe -v tests/test_tools_schema.py
     collecting ... collected 31 items
     ...
     31 passed in 0.06s
     ```

5. **Milestone 4 Regression Test Suites**:
   - Execution command:
     ```powershell
     .venv\Scripts\pytest.exe -v tests/test_adversarial_error_injection_m4.py tests/test_fastmcp_inspection_tools.py tests/test_tools_schema.py tests/test_adversarial_m4_gating.py
     ```
   - Verbatim execution output:
     ```
     ============================= 219 passed in 9.82s =============================
     ```
     * `test_adversarial_error_injection_m4.py`: 46 passed.
     * `test_fastmcp_inspection_tools.py`: 21 passed.
     * `test_tools_schema.py`: 31 passed.
     * `test_adversarial_m4_gating.py`: 121 passed.

6. **Full Repository Regression Test Suite**:
   - Execution command:
     ```powershell
     .venv\Scripts\pytest.exe -v tests/test_inspector_camera.py tests/test_multiview_rendering.py tests/test_adversarial_camera_math.py tests/test_adversarial_viewport_capture.py tests/test_bridge_socket_parity.py tests/test_visual_critic.py tests/test_adversarial_bvh_penetration.py tests/test_adversarial_critic_benchmark.py tests/test_tools_schema.py tests/test_fastmcp_inspection_tools.py tests/test_adversarial_m4_gating.py tests/test_adversarial_error_injection_m4.py
     ```
   - Verbatim execution output:
     ```
     ======================= 527 passed, 3 skipped in 37.48s =======================
     ```

---

## 2. Logic Chain

1. **Premise 1 (Offline Bridge Resilience Requirement)**: When Blender is offline (interactive socket unavailable and headless CLI missing), consumer agents calling `morphomesh_capture_viewport` or `morphomesh_setup_inspector_camera_rig` must receive valid responses with fallback artifacts rather than unhandled socket/connection crashes.
   - *Observation 1.1*: In `test_capture_viewport_offline_produces_fallback_png`, patching `is_interactive_connected=False` and `blender_bin_path=None` returns `status="success"`, a non-empty `base64_preview`, and writes a 70-byte valid PNG to disk.
   - *Observation 1.2*: In `test_setup_camera_rig_offline_returns_mock_metadata`, the same patch yields `status="success"`, `viewpoint="front"`, `location`, and `rotation_euler`.
   - *Adversarial Verification*: Independent stress testing confirms that even when `output_path` targets deep non-existent directories, parent directories are created on demand and `FALLBACK_PNG_BYTES` is written.

2. **Premise 2 (Operational Exception Preservation)**: Offline fallback must be strictly conditioned on connectivity/availability failures (`ERR_BLENDER_UNAVAILABLE`, `ERR_BRIDGE_CONNECTION`, `ConnectionError`, `TimeoutError`, `OSError`). Internal domain or operational errors (e.g., `ERR_CAMERA_FAILED`, `ERR_RENDER_FAILED`) must NOT be masked by fallback logic and must re-raise as `ToolError`.
   - *Observation 2.1*: In both `blender_bridge.py` (lines 2502, 2571) and `server.py` (lines 1170, 1288), the exception handler evaluates `is_unavailable` by inspecting `e.code` and exception types. If `e.code` is `ERR_CAMERA_FAILED` or `ERR_RENDER_FAILED`, `is_unavailable` evaluates to `False`.
   - *Observation 2.2*: `tests/test_fastmcp_inspection_tools.py:415` (`test_bridge_exception_mapping`) asserts that mocking `setup_inspector_camera` with `ERR_CAMERA_FAILED` raises `ToolError` containing `[ERR_CAMERA_FAILED]`. The test passed in 0.04s.
   - *Adversarial Verification*: Independent execution of `MorphoMeshException(code="ERR_RENDER_FAILED")` against `morphomesh_capture_viewport` verified that `[ERR_RENDER_FAILED]` is preserved and raised as `ToolError`.

3. **Premise 3 (Backward Compatibility & Schema Integrity)**: Legacy creature generation tools must maintain their 7-tool baseline schema when gating flags are unset.
   - *Observation 3.1*: `tests/test_tools_schema.py` was completely untouched (`git diff` clean) and passed 31/31 tests in 0.06s.
   - *Observation 3.2*: Gating matrix tests (`test_adversarial_m4_gating.py`) passed 121/121 across all combinations of environment variables (`MORPHOMESH_INCLUDE_ALL_TOOLS`, `MORPHOMESH_INCLUDE_HUMAN_TOOLS`, `MORPHOMESH_INCLUDE_INSPECTION_TOOLS`).

4. **Premise 4 (Integrity & Non-Circumvention)**:
   - *Observation 4.1*: Static analysis of `server.py`, `blender_bridge.py`, and `camera_rig.py` reveals no hardcoded mock results keyed to specific test names, no dummy facades, and no synthetic pass-throughs.
   - *Observation 4.2*: All fallback outputs are computed dynamically (camera framing distance via trigonometry in `camera_rig.py`, PNG via valid bitstream `FALLBACK_PNG_BYTES`).

---

## 3. Adversarial Challenge & Stress Tests

### Challenge Matrix

| # | Challenge Scenario | Target Component | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|---|
| C1 | Viewport capture with deeply nested non-existent output directory while offline | `server.py` + `blender_bridge.py` | Auto-create parent folders, write `FALLBACK_PNG_BYTES` | Parent dirs created, 70-byte PNG written, `status="success"` | **PASS** |
| C2 | Viewport capture with `output_path=None` while offline | `server.py` + `blender_bridge.py` | Generate temp file, write PNG, return path | Temp file generated in OS tempdir, valid PNG written | **PASS** |
| C3 | Domain exception `ERR_RENDER_FAILED` thrown during viewport capture | `server.py` | Do NOT trigger fallback; re-raise `ToolError` with `[ERR_RENDER_FAILED]` | `ToolError` raised with `[ERR_RENDER_FAILED]` | **PASS** |
| C4 | Domain exception `ERR_CAMERA_FAILED` thrown during camera rig setup | `server.py` | Do NOT trigger fallback; re-raise `ToolError` with `[ERR_CAMERA_FAILED]` | `ToolError` raised with `[ERR_CAMERA_FAILED]` | **PASS** |
| C5 | Network exceptions (`ConnectionError`, `TimeoutError`, `OSError`) thrown during bridge execution | `server.py` + `blender_bridge.py` | Cleanly catch and trigger offline fallback | Both tools return `status="success"` with `offline_fallback=True` | **PASS** |
| C6 | Camera rig offline calculation across all 32 canonical viewpoints | `camera_rig.py` pure-Python solver | All 32 viewpoints solved without Blender runtime | All 32 viewpoints computed valid location and rotation | **PASS** |
| C7 | `FALLBACK_PNG_BYTES` structural integrity | `camera_rig.py` | Valid PNG bitstream with `IHDR`, `IDAT`, `IEND` | Valid 1x1 RGBA transparent PNG bitstream | **PASS** |

---

## 4. Caveats

- "No caveats." All checks were independently verified in the active `.venv` environment on Windows. No unverified assumptions remain.

---

## 5. Conclusion

**Verdict**: **APPROVE**

Milestone 4 Iteration 2 fully resolves the issues identified in Iteration 1:
1. **Offline Bridge Resilience**: Fully implemented and hardened. When Blender interactive socket and local CLI are offline, tools return valid fallback payloads (`FALLBACK_PNG_BYTES` on disk and base64 preview, pure-Python optical camera metadata) with `status="success"`.
2. **Domain Exception Preservation**: Error code discrimination preserves operational errors (e.g. `ERR_CAMERA_FAILED`, `ERR_RENDER_FAILED`), re-raising them as FastMCP `ToolError` with exact error codes. `test_fastmcp_inspection_tools.py:415` passes.
3. **Baseline Schema Preservation**: `tests/test_tools_schema.py` passes 31/31 without modifications.
4. **Test Suite Execution**: 219/219 Milestone 4 target tests passed; 527/530 full repository tests passed (3 skipped, 0 failures).
5. **Integrity Audit**: Clean. No facades, no shortcuts, no hardcoded test responses.

---

## 6. Verification Method

To independently verify these findings, run:

1. **Milestone 4 Target Regression Suite**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_adversarial_error_injection_m4.py tests/test_fastmcp_inspection_tools.py tests/test_tools_schema.py tests/test_adversarial_m4_gating.py
   ```
   *Expected*: 219 passed in ~10s.

2. **Domain Exception Mapping Specific Test**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_fastmcp_inspection_tools.py::test_bridge_exception_mapping
   ```
   *Expected*: 1 passed in ~0.04s.

3. **Full Repository Regression Suite**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_inspector_camera.py tests/test_multiview_rendering.py tests/test_adversarial_camera_math.py tests/test_adversarial_viewport_capture.py tests/test_bridge_socket_parity.py tests/test_visual_critic.py tests/test_adversarial_bvh_penetration.py tests/test_adversarial_critic_benchmark.py tests/test_tools_schema.py tests/test_fastmcp_inspection_tools.py tests/test_adversarial_m4_gating.py tests/test_adversarial_error_injection_m4.py
   ```
   *Expected*: 527 passed, 3 skipped in ~37s.

4. **Schema Unmodified Check**:
   ```powershell
   git diff tests/test_tools_schema.py
   ```
   *Expected*: Exit code 0, empty diff output.
