# Milestone 4 Adversarial Challenge Handoff Report: Error Injection & Schema Stress

**Agent**: Challenger M4_2 (`.agents/challenger_m4_insp_2`)  
**Role**: critic, specialist  
**Date**: 2026-09-07T07:02:00Z  
**Parent Orchestrator**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Handoff Type**: Hard (Challenge Evaluation Complete)  
**Empirical Verdict**: **REJECT**  

---

## 1. Observation

An adversarial test harness was constructed and executed at `tests/test_adversarial_error_injection_m4.py` (46 test cases) evaluating parameter bounds, type coercion, FastMCP `ToolError` enforcement, and offline bridge resilience.

```powershell
.venv\Scripts\pytest.exe -v tests/test_adversarial_error_injection_m4.py
```

### 1.1 Test Execution Output Summary
```
=========================== short test summary info ===========================
FAILED tests/test_adversarial_error_injection_m4.py::TestCameraRigParameterValidation::test_invalid_viewpoints_rejected[nadir_flipped]
FAILED tests/test_adversarial_error_injection_m4.py::TestCameraRigParameterValidation::test_invalid_viewpoints_rejected[]
FAILED tests/test_adversarial_error_injection_m4.py::TestCameraRigParameterValidation::test_invalid_viewpoints_rejected[zenith_99]
FAILED tests/test_adversarial_error_injection_m4.py::TestCameraRigParameterValidation::test_invalid_viewpoints_rejected[diagonal_underneath]
FAILED tests/test_adversarial_error_injection_m4.py::TestCameraRigParameterValidation::test_invalid_viewpoints_rejected[UPWARD_45]
FAILED tests/test_adversarial_error_injection_m4.py::TestCaptureViewportParameterValidation::test_invalid_shading_modes_rejected[PATH_TRACING]
FAILED tests/test_adversarial_error_injection_m4.py::TestCaptureViewportParameterValidation::test_invalid_shading_modes_rejected[RAYTRACING]
FAILED tests/test_adversarial_error_injection_m4.py::TestCaptureViewportParameterValidation::test_invalid_shading_modes_rejected[UNLIT_DEBUG]
FAILED tests/test_adversarial_error_injection_m4.py::TestCaptureViewportParameterValidation::test_invalid_shading_modes_rejected[]
FAILED tests/test_adversarial_error_injection_m4.py::TestCaptureViewportParameterValidation::test_invalid_shading_modes_rejected[NORMAL_MAP_PREVIEW]
FAILED tests/test_adversarial_error_injection_m4.py::TestCaptureViewportParameterValidation::test_invalid_color_types_rejected[INVALID_COLOR_TYPE]
FAILED tests/test_adversarial_error_injection_m4.py::TestCaptureViewportParameterValidation::test_invalid_color_types_rejected[NEON_RAINBOW]
FAILED tests/test_adversarial_error_injection_m4.py::TestCaptureViewportParameterValidation::test_invalid_color_types_rejected[HSV_GRADIENT]
FAILED tests/test_adversarial_error_injection_m4.py::TestCaptureViewportParameterValidation::test_invalid_color_types_rejected[]
FAILED tests/test_adversarial_error_injection_m4.py::TestCaptureViewportParameterValidation::test_invalid_color_types_rejected[DEBUG_UV]
FAILED tests/test_adversarial_error_injection_m4.py::TestVisualCritiqueParameterValidation::test_invalid_target_preset_rejected[alien_hydra]
FAILED tests/test_adversarial_error_injection_m4.py::TestVisualCritiqueParameterValidation::test_invalid_target_preset_rejected[draconic_quadruped]
FAILED tests/test_adversarial_error_injection_m4.py::TestVisualCritiqueParameterValidation::test_invalid_target_preset_rejected[spider_titan]
FAILED tests/test_adversarial_error_injection_m4.py::TestVisualCritiqueParameterValidation::test_invalid_target_preset_rejected[]
FAILED tests/test_adversarial_error_injection_m4.py::TestVisualCritiqueParameterValidation::test_invalid_target_preset_rejected[unknown_preset]
FAILED tests/test_adversarial_error_injection_m4.py::TestOfflineBridgeResilience::test_capture_viewport_offline_produces_fallback_png
FAILED tests/test_adversarial_error_injection_m4.py::TestOfflineBridgeResilience::test_setup_camera_rig_offline_returns_mock_metadata
======================= 22 failed, 24 passed in 18.46s ========================
```

### 1.2 Detailed Observations by Component

#### Defect 1: Missing Viewpoint Validation in `morphomesh_setup_inspector_camera_rig`
- **File**: `src/morphomesh/server.py` lines 1113–1120 & `src/morphomesh/camera_rig.py` line 839.
- **Code in `server.py`**:
  ```python
  # Pre-flight parameter validation
  if focal_length < 10.0 or focal_length > 300.0:
      raise ToolError(...)
  if target_center is not None and (not isinstance(target_center, (list, tuple)) or len(target_center) != 3):
      raise ToolError(...)
  if not camera_name or not camera_name.strip():
      raise ToolError(...)
  ```
- **Code in `camera_rig.py`**:
  ```python
  vp_spec = CANONICAL_VIEWPOINTS.get(vp_clean, CANONICAL_VIEWPOINTS["three_quarter"])
  ```
- **Direct Empirical Observation**: Invoking `morphomesh_setup_inspector_camera_rig(viewpoint="nadir_flipped")` or `viewpoint=""` succeeds with `status: "success"` and silently falls back to `"three_quarter"` instead of raising `ToolError`.

#### Defect 2: Missing Shading Mode & Color Type Validation in `morphomesh_capture_viewport`
- **File**: `src/morphomesh/server.py` lines 1169–1174 & `src/morphomesh/camera_rig.py` lines 940–944.
- **Code in `server.py`**:
  ```python
  if not isinstance(resolution, (list, tuple)) or len(resolution) != 2 or any(r <= 0 for r in resolution):
      raise ToolError(...)
  if not camera_name or not camera_name.strip():
      raise ToolError(...)
  ```
- **Code in `camera_rig.py`**:
  ```python
  norm_shading = shading_mode.upper() if shading_mode and shading_mode.upper() in valid_shading else "SOLID"
  norm_color = color_type.upper() if color_type and color_type.upper() in valid_colors else "RANDOM"
  ```
- **Direct Empirical Observation**: Invoking `morphomesh_capture_viewport(shading_mode="PATH_TRACING")` or `color_type="INVALID_COLOR_TYPE"` succeeds with `status: "success"` and silently coerces to `"SOLID"` and `"RANDOM"` without raising `ToolError`.

#### Defect 3: Missing Target Preset Validation in `morphomesh_critique_visual_quality`
- **File**: `src/morphomesh/server.py` lines 1246–1251 & `src/morphomesh/visual_critic.py` line 1366.
- **Code in `server.py`**:
  ```python
  if clearance_tolerance < 0.0:
      raise ToolError(...)
  if not character_name and not target_object:
      raise ToolError(...)
  ```
- **Code in `visual_critic.py`**:
  ```python
  preset = ANTHROPOMETRIC_PRESETS.get(target_preset, ANTHROPOMETRIC_PRESETS["stylized_heroine"])
  ```
- **Direct Empirical Observation**: Invoking `morphomesh_critique_visual_quality(target_preset="alien_hydra")` succeeds with `status: "success"` and silently scores against `"stylized_heroine"` rather than raising `ToolError`.

#### Defect 4: Offline Bridge Resilience Failure (Crash on Offline Bridge)
- **File**: `src/morphomesh/server.py` lines 1125–1141 and lines 1176–1216.
- **Verbatim Error**:
  ```
  mcp.server.fastmcp.exceptions.ToolError: MorphoMesh Tool Error: [ERR_BLENDER_UNAVAILABLE] Blender binary not found. Set BLENDER_BIN_PATH or install Blender at /Applications/Blender.app/Contents/MacOS/Blender
  ```
- **Direct Empirical Observation**:
  - `morphomesh_capture_viewport` contains code to encode `FALLBACK_PNG_BYTES` at lines 1196–1206, but it is located *after* `res = blender_bridge.capture_viewport(...)`. When the bridge is unreachable (`is_interactive_connected() == False` and `blender_bin_path == None`), `blender_bridge.execute` throws `MorphoMeshException("ERR_BLENDER_UNAVAILABLE")`.
  - `server.py` catches this exception at line 1211 and immediately raises `ToolError`, aborting execution before `FALLBACK_PNG_BYTES` is ever returned.
  - Similarly, `morphomesh_setup_inspector_camera_rig` calls `blender_bridge.setup_inspector_camera(...)`, which lacks an offline fallback handler, causing `server.py` to raise `ToolError` instead of returning valid mock metadata.

---

## 2. Logic Chain

1. **Observation 1.1**: 22 out of 46 adversarial tests failed across viewpoint validation, shading mode validation, color type validation, target preset validation, and offline bridge resilience.
2. **Observation 1.2 (Defects 1–3)**: The schemas in `src/morphomesh/models.py` (`SetupInspectorCameraInput`, `CaptureViewportInput`, `VisualCritiqueInput`) declare `viewpoint: str`, `shading_mode: str`, `color_type: str`, and `target_preset: str` as unconstrained strings. In `server.py`, pre-flight validation blocks check only focal lengths, target center tuple length, camera names, resolutions, and non-negative tolerances.
3. **Logic Step 1**: Downstream libraries (`camera_rig.py` and `visual_critic.py`) silently catch unknown enum keys via `.get(key, default)`. While defensive programming is useful internally, in an MCP tool layer, unvalidated parameters violate the FastMCP contract by masking client errors and silently executing unintended actions. Invalid inputs like `"nadir_flipped"`, `"PATH_TRACING"`, and `"alien_hydra"` must be rejected upfront with clean `ToolError` messages.
4. **Observation 1.2 (Defect 4)**: The user specification explicitly requires:
   > "Force bridge offline/unreachable: verify `morphomesh_capture_viewport` produces valid transparent 1x1 RGBA fallback PNG (`FALLBACK_PNG_BYTES`), and `morphomesh_setup_inspector_camera_rig` returns valid mock metadata without throwing uncaught connection errors."
5. **Logic Step 2**: When Blender is offline (interactive socket disconnected and headless binary missing/unreachable), `blender_bridge.execute()` raises `ERR_BLENDER_UNAVAILABLE` or `ConnectionError`. Because `setup_inspector_camera` and `capture_viewport` in `blender_bridge.py` do not handle offline execution fallback (unlike `groom_human` or `dress_human`), and `server.py` wraps the bridge calls in exception blocks that re-raise as `ToolError`, offline execution raises `ToolError` and fails to deliver the transparent fallback PNG or mock metadata.
6. **Conclusion**: The implementation fails 4 key validation checks and offline resilience requirements. Verdict must be **REJECT**.

---

## 3. Caveats

- Tests were run using standard `pytest` under `.venv` on Windows 11.
- Valid parameter checks (focal length ranges 10–300mm, resolution $> 0$, target center 3D coordinates, and clearance tolerance $\ge 0$) correctly raise `ToolError` and passed 24/24 tests.
- When Blender 4.5 is installed and accessible locally, headless Workbench rendering functions properly; the failure in Defect 4 occurs specifically when Blender is offline or unreachable as mandated by test scenario 3.

---

## 4. Conclusion & Actionable Remediation Plan

### Empirical Verdict: **REJECT**

Milestone 4 cannot be approved until Worker M4 remediates the following 4 issues:

### Required Remediation Items for Worker M4:

1. **Enforce Viewpoint Validation in `morphomesh_setup_inspector_camera_rig`**:
   - In `src/morphomesh/server.py` line 1113:
     ```python
     valid_viewpoints = {"front", "side", "side_left", "back", "three_quarter", "top", "head", "close_up_head", "portrait", "hands", "close_up_hands", "torso", "feet", "turntable"}
     if not viewpoint or viewpoint.lower().strip() not in valid_viewpoints:
         raise ToolError(f"MorphoMesh Parameter Validation Error: Invalid viewpoint '{viewpoint}'. Allowed: {sorted(list(valid_viewpoints))}.")
     ```
2. **Enforce Shading Mode & Color Type Validation in `morphomesh_capture_viewport`**:
   - In `src/morphomesh/server.py` line 1169:
     ```python
     valid_shading = {"SOLID", "FLAT", "WIREFRAME", "MATERIAL", "RENDERED"}
     if not shading_mode or shading_mode.upper().strip() not in valid_shading:
         raise ToolError(f"MorphoMesh Parameter Validation Error: Invalid shading_mode '{shading_mode}'. Allowed: {sorted(list(valid_shading))}.")

     valid_colors = {"RANDOM", "MATERIAL", "SINGLE", "OBJECT", "TEXTURE"}
     if not color_type or color_type.upper().strip() not in valid_colors:
         raise ToolError(f"MorphoMesh Parameter Validation Error: Invalid color_type '{color_type}'. Allowed: {sorted(list(valid_colors))}.")
     ```
3. **Enforce Target Preset Validation in `morphomesh_critique_visual_quality`**:
   - In `src/morphomesh/server.py` line 1246:
     ```python
     valid_presets = {"realistic_human", "stylized_heroine", "chibi_petite"}
     if not target_preset or target_preset.strip() not in valid_presets:
         raise ToolError(f"MorphoMesh Parameter Validation Error: Invalid target_preset '{target_preset}'. Allowed: {sorted(list(valid_presets))}.")
     ```
4. **Implement Offline Bridge Resilience**:
   - In `src/morphomesh/blender_bridge.py`: Add `try ... except Exception as e:` fallbacks inside `setup_inspector_camera()` and `capture_viewport()` (or in `src/morphomesh/server.py` within the tool exception handlers):
     - For `morphomesh_capture_viewport`: When bridge call fails due to `ERR_BLENDER_UNAVAILABLE`, `ConnectionError`, or `TimeoutError`, write `FALLBACK_PNG_BYTES` to `output_path`, base64 encode it into `base64_preview`, and return a valid dictionary with `status="success"`.
     - For `morphomesh_setup_inspector_camera_rig`: When bridge call fails due to `ERR_BLENDER_UNAVAILABLE`, `ConnectionError`, or `TimeoutError`, invoke `morphomesh.camera_rig.setup_inspector_camera(...)` directly in mock/pure-python mode or return a valid mock metadata dictionary with `status="success"`.

---

## 5. Verification Method

To independently reproduce the failures:

1. **Execute the adversarial test suite**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_adversarial_error_injection_m4.py
   ```
   *Observed Result*: Exactly 22 failed, 24 passed.

2. **Verify specific viewpoint failure**:
   ```powershell
   .venv\Scripts\python.exe -c "import asyncio; from morphomesh.server import morphomesh_setup_inspector_camera_rig; print(asyncio.run(morphomesh_setup_inspector_camera_rig(viewpoint='nadir_flipped')))"
   ```
   *Observed Result*: Returns `{'status': 'success', ...}` instead of raising `ToolError`.

3. **Verify specific offline capture failure**:
   ```powershell
   .venv\Scripts\python.exe -c "import asyncio; from unittest.mock import patch; from morphomesh.server import morphomesh_capture_viewport, blender_bridge; (patch.object(blender_bridge, 'is_interactive_connected', return_value=False), patch.object(blender_bridge, 'blender_bin_path', None))[0].start(); print(asyncio.run(morphomesh_capture_viewport()))"
   ```
   *Observed Result*: Raises `ToolError: [ERR_BLENDER_UNAVAILABLE]` instead of returning transparent 1x1 fallback PNG.

4. **Invalidation Conditions**:
   - All 46 tests in `tests/test_adversarial_error_injection_m4.py` pass with exit code 0.
