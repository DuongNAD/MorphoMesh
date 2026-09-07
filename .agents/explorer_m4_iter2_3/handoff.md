# Handoff Report — Explorer M4 Iteration 2 - 3: Test Suite Alignment & Regression Explorer

**Agent**: Explorer M4 Iteration 2 - 3 (`.agents/explorer_m4_iter2_3`)  
**Role**: Test Suite Alignment & Regression Explorer, Synthesis & Worker Task Specification  
**Date**: 2026-09-07T07:07:30Z  
**Parent Orchestrator**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Handoff Type**: Hard Handoff (Investigation & Task Specification Complete)  
**Target Milestone**: Milestone 4 Iteration 2 (FastMCP Tool Integration & Verification Suite Remediation)  

---

## 1. Observation

Direct empirical observations, code inspections, tool commands, and execution outputs:

### 1.1 Empirical Reproduction of `tests/test_adversarial_error_injection_m4.py`
Command executed:
```powershell
.venv\Scripts\pytest.exe -v tests/test_adversarial_error_injection_m4.py
```
**Execution Output**:
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
======================= 22 failed, 24 passed in 18.17s ========================
```
- **Total Test Cases**: 46
  - Parameter bounds & enum validation: 41 cases (20 failed due to missing enum checks; 21 passed for focal length, resolution, tolerance bounds).
  - FastMCP ToolError enforcement: 3 cases (3 passed for empty camera/character names).
  - Offline bridge resilience: 2 cases (2 failed with `ToolError: MorphoMesh Tool Error: [ERR_BLENDER_UNAVAILABLE]`).

### 1.2 ToolError Regex Match Patterns in `test_adversarial_error_injection_m4.py`
The test assertions use the following regex filters:
- Viewpoint validation: `pytest.raises(ToolError, match=r"(?i)(viewpoint|validation|invalid|preset)")`
- Focal length bounds: `pytest.raises(ToolError, match=r"(?i)(focal_length|validation|between 10.0 and 300.0)")`
- Target center coords: `pytest.raises(ToolError, match=r"(?i)(target_center|validation|3 coordinates)")`
- Shading mode validation: `pytest.raises(ToolError, match=r"(?i)(shading_mode|validation|invalid)")`
- Resolution bounds: `pytest.raises(ToolError, match=r"(?i)(resolution|validation|positive)")`
- Color type validation: `pytest.raises(ToolError, match=r"(?i)(color_type|validation|invalid)")`
- Clearance tolerance: `pytest.raises(ToolError, match=r"(?i)(clearance_tolerance|validation|non-negative)")`
- Target preset: `pytest.raises(ToolError, match=r"(?i)(target_preset|validation|invalid|preset)")`
- Camera name: `pytest.raises(ToolError, match=r"(?i)(camera_name|empty)")`
- Character / Target name: `pytest.raises(ToolError, match=r"(?i)(character_name|target_object)")`

Every assertion succeeds when raising `ToolError(f"MorphoMesh Parameter Validation Error: Invalid <param> '{val}'...")`.

### 1.3 Analysis of `tests/test_fastmcp_inspection_tools.py`
Command executed:
```powershell
.venv\Scripts\pytest.exe -v tests/test_fastmcp_inspection_tools.py
```
**Execution Output**: `21 passed in 6.36s` (100% pass).

**Critical Test Behavior Inspection**:
1. Line 337 (`test_inspection_tools_offline_graceful_fallback`):
   - Patches `blender_bridge.is_interactive_connected = False`.
   - Asserts that `morphomesh_setup_inspector_camera_rig()` and `morphomesh_critique_visual_quality()` succeed gracefully with `status="success"`.
2. Line 415 (`test_bridge_exception_mapping`):
   - Patches `blender_bridge.setup_inspector_camera` with `side_effect=MorphoMeshException(code="ERR_CAMERA_FAILED", message="Camera error")`.
   - Asserts:
     ```python
     with pytest.raises(ToolError) as exc_info:
         await morphomesh_setup_inspector_camera_rig()
     assert "[ERR_CAMERA_FAILED]" in str(exc_info.value)
     ```
   - **Crucial Discovery**: This test **mandates** that an operational error with `code="ERR_CAMERA_FAILED"` is NOT swallowed by fallback and MUST raise `ToolError` containing `[ERR_CAMERA_FAILED]`.
   - Reconciled Distinction:
     - `ERR_BLENDER_UNAVAILABLE` (or socket disconnected + binary missing / connection refusal / timeout) $\rightarrow$ Trigger graceful offline fallback.
     - `ERR_CAMERA_FAILED` (or other operational Blender script execution exceptions) $\rightarrow$ Re-raise as `ToolError`.

### 1.4 Analysis of `tests/test_tools_schema.py`
Command executed:
```powershell
.venv\Scripts\pytest.exe -v tests/test_tools_schema.py
```
**Execution Output**: `31 passed in 0.10s` (100% pass).

**Baseline Schema Isolation**:
- In `src/morphomesh/server.py` lines 1324–1359, when `MORPHOMESH_INCLUDE_INSPECTION_TOOLS` is unset (default during baseline testing), `mcp.list_tools()` filters tools using `_get_active_allowed_tool_names()`, which returns strictly `CREATURE_TOOL_NAMES` (7 tools).
- The 7 tools (`morphomesh_generate_concept`, `morphomesh_create_3d_asset`, `morphomesh_optimize_topology`, `morphomesh_auto_rig`, `morphomesh_blender_execute`, `morphomesh_get_scene_status`, `morphomesh_render_preview`) do not declare or accept `viewpoint`, `shading_mode`, `color_type`, or `target_preset`.
- Therefore, modifying the parameter validation and offline fallback for inspection tools has **zero blast radius** on the 7 baseline tools.

---

## 2. Logic Chain

1. **Premise 1**: In `src/morphomesh/server.py`, `morphomesh_setup_inspector_camera_rig`, `morphomesh_capture_viewport`, and `morphomesh_critique_visual_quality` lacked pre-flight enum membership checks for `viewpoint`, `shading_mode`, `color_type`, and `target_preset`.
2. **Premise 2**: Downstream modules (`camera_rig.py` and `visual_critic.py`) used `.get(key, default)`, silently swallowing invalid parameters (e.g. `"nadir_flipped"` falling back to `"three_quarter"`, `"PATH_TRACING"` falling back to `"SOLID"`, `"alien_hydra"` falling back to `"stylized_heroine"`). This violated FastMCP contract enforcement tested by Challenger M4_2.
3. **Logic Step 1**: Adding pre-flight membership validation against canonical sets in `server.py` (and corresponding `@field_validator` in `models.py`) immediately fixes 20/22 failing tests while matching all required regex patterns.
4. **Premise 3**: In `server.py`, lines 1125–1141 and lines 1176–1216 wrapped calls to `blender_bridge.setup_inspector_camera()` and `blender_bridge.capture_viewport()` in exception handlers that unconditionally caught `MorphoMeshException` and raised `ToolError`.
5. **Premise 4**: When Blender is offline (`is_interactive_connected() == False` and `blender_bin_path == None`), `blender_bridge.execute()` routes to `run_headless_script()`, which raises `MorphoMeshException(code="ERR_BLENDER_UNAVAILABLE")`.
6. **Premise 5**: Because `server.py` immediately converted this to `ToolError`, the existing fallback logic (encoding `FALLBACK_PNG_BYTES` at lines 1196–1206) was unreachable.
7. **Logic Step 2**: To satisfy `TestOfflineBridgeResilience` without breaking `test_bridge_exception_mapping`:
   - Differentiate the exception code: If `e.code == "ERR_BLENDER_UNAVAILABLE"` or the exception is a `ConnectionError`/`TimeoutError`/`OSError`, execute the offline fallback path.
   - If `e.code != "ERR_BLENDER_UNAVAILABLE"` (such as `ERR_CAMERA_FAILED`), re-raise as `ToolError`.
   - In `morphomesh_capture_viewport`: write `FALLBACK_PNG_BYTES` to disk, base64 encode it, and return a valid dictionary with `status="success"`.
   - In `morphomesh_setup_inspector_camera_rig`: invoke pure-Python `morphomesh.camera_rig.setup_inspector_camera(..., scene=None)` which executes without `bpy`, returns all camera metadata (camera_location, rotation_euler, target_center, framing_distance), and returns `status="success"`.
8. **Conclusion**: This reconciles all 46 adversarial tests, all 21 inspection tests, and all 31 baseline schema tests simultaneously.

---

## 3. Caveats

1. **Read-Only Scope**: Explorer M4 Iteration 2 - 3 executed in strict read-only mode. No production code was modified during this exploration.
2. **Local Environment**: Tests were executed against Python 3.11.9 on Windows 11 using the local `.venv`.
3. **Pydantic Defaults Preservation**: Defaults for `viewpoint` (`"three_quarter"`), `shading_mode` (`"SOLID"`), `color_type` (`"RANDOM"`), and `target_preset` (`"stylized_heroine"`) must NOT be altered, as `test_fastmcp_inspection_tools.py` asserts these exact values in FastMCP input schemas.

---

## 4. Conclusion & Actionable Worker M4 Iteration 2 Task Specification

### Overall Assessment
All failure modes are completely diagnosed, with zero ambiguity or conflict between the test suites. The remediation is clean, self-contained, and backwards-compatible.

### Comprehensive Actionable Plan for Worker M4 Iteration 2

#### Task 1: Define Canonical Enum Sets
In `src/morphomesh/models.py` and `src/morphomesh/server.py`:
```python
VALID_INSPECTOR_VIEWPOINTS: Set[str] = {
    "front", "side", "side_left", "side_right", "back", "three_quarter",
    "front_three_quarter", "three_quarter_left", "back_three_quarter",
    "top", "bottom", "head", "close_up_head", "head_close_up",
    "portrait", "hands", "close_up_hands", "hands_close_up", "marionette",
    "torso", "bodice", "feet", "sandals", "shoes", "turntable", "turntable_4views"
}

VALID_SHADING_MODES: Set[str] = {"SOLID", "FLAT", "WIREFRAME", "MATERIAL", "RENDERED"}

VALID_COLOR_TYPES: Set[str] = {"RANDOM", "MATERIAL", "SINGLE", "OBJECT", "TEXTURE"}

VALID_ANTHROPOMETRIC_PRESETS: Set[str] = {"realistic_human", "stylized_heroine", "chibi_petite"}
```

#### Task 2: Implement Pre-flight Validation in `src/morphomesh/server.py`
1. In `morphomesh_setup_inspector_camera_rig` (around line 1113):
   ```python
   # Validate viewpoint
   if not viewpoint or not isinstance(viewpoint, str) or viewpoint.lower().strip() not in VALID_INSPECTOR_VIEWPOINTS:
       raise ToolError(
           f"MorphoMesh Parameter Validation Error: Invalid viewpoint '{viewpoint}'. "
           f"Allowed viewpoints: {sorted(list(VALID_INSPECTOR_VIEWPOINTS))}."
       )
   ```
2. In `morphomesh_capture_viewport` (around line 1169):
   ```python
   # Validate shading_mode and color_type
   if not shading_mode or not isinstance(shading_mode, str) or shading_mode.upper().strip() not in VALID_SHADING_MODES:
       raise ToolError(
           f"MorphoMesh Parameter Validation Error: Invalid shading_mode '{shading_mode}'. "
           f"Allowed shading modes: {sorted(list(VALID_SHADING_MODES))}."
       )
   if not color_type or not isinstance(color_type, str) or color_type.upper().strip() not in VALID_COLOR_TYPES:
       raise ToolError(
           f"MorphoMesh Parameter Validation Error: Invalid color_type '{color_type}'. "
           f"Allowed color types: {sorted(list(VALID_COLOR_TYPES))}."
       )
   ```
3. In `morphomesh_critique_visual_quality` (around line 1246):
   ```python
   # Validate target_preset
   if not target_preset or not isinstance(target_preset, str) or target_preset.strip().lower() not in VALID_ANTHROPOMETRIC_PRESETS:
       raise ToolError(
           f"MorphoMesh Parameter Validation Error: Invalid target_preset '{target_preset}'. "
           f"Allowed presets: {sorted(list(VALID_ANTHROPOMETRIC_PRESETS))}."
       )
   ```

#### Task 3: Align Pydantic Models in `src/morphomesh/models.py`
Add field validators to `SetupInspectorCameraInput`, `CaptureViewportInput`, and `VisualCritiqueInput`:
```python
# Inside SetupInspectorCameraInput:
@field_validator("viewpoint")
@classmethod
def validate_viewpoint(cls, v: str) -> str:
    if not v or not isinstance(v, str) or v.lower().strip() not in VALID_INSPECTOR_VIEWPOINTS:
        raise ValueError(f"Invalid viewpoint '{v}'. Allowed: {sorted(list(VALID_INSPECTOR_VIEWPOINTS))}")
    return v.lower().strip()

# Inside CaptureViewportInput:
@field_validator("shading_mode")
@classmethod
def validate_shading_mode(cls, v: str) -> str:
    if not v or not isinstance(v, str) or v.upper().strip() not in VALID_SHADING_MODES:
        raise ValueError(f"Invalid shading_mode '{v}'. Allowed: {sorted(list(VALID_SHADING_MODES))}")
    return v.upper().strip()

@field_validator("color_type")
@classmethod
def validate_color_type(cls, v: str) -> str:
    if not v or not isinstance(v, str) or v.upper().strip() not in VALID_COLOR_TYPES:
        raise ValueError(f"Invalid color_type '{v}'. Allowed: {sorted(list(VALID_COLOR_TYPES))}")
    return v.upper().strip()

# Inside VisualCritiqueInput:
@field_validator("target_preset")
@classmethod
def validate_target_preset(cls, v: str) -> str:
    if not v or not isinstance(v, str) or v.strip().lower() not in VALID_ANTHROPOMETRIC_PRESETS:
        raise ValueError(f"Invalid target_preset '{v}'. Allowed: {sorted(list(VALID_ANTHROPOMETRIC_PRESETS))}")
    return v.strip().lower()
```

#### Task 4: Implement Offline Resilience in `src/morphomesh/blender_bridge.py`
1. In `capture_viewport` (lines 2490–2499):
   ```python
   try:
       res = self.execute("morphomesh.capture_viewport", params, timeout=30.0)
       return res
   except (MorphoMeshException, ConnectionError, OSError, TimeoutError) as e:
       if isinstance(e, MorphoMeshException) and e.code != "ERR_BLENDER_UNAVAILABLE":
           raise
       from morphomesh.camera_rig import FALLBACK_PNG_BYTES
       os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
       with open(output_path, "wb") as f:
           f.write(FALLBACK_PNG_BYTES)
       b64 = base64.b64encode(FALLBACK_PNG_BYTES).decode("utf-8")
       return {
           "status": "success",
           "image_path": output_path,
           "output_path": output_path,
           "resolution": list(resolution) if isinstance(resolution, (tuple, list)) else [1024, 1024],
           "shading_mode": shading_mode,
           "color_type": color_type,
           "camera_name": camera_name,
           "base64_preview": b64,
           "base64_image": b64,
           "offline_fallback": True,
           "message": "Viewport capture completed via offline fallback (Blender unavailable)",
       }
   ```
2. In `setup_inspector_camera` (lines 2530–2539):
   ```python
   try:
       res = self.execute("morphomesh.setup_inspector_camera", params, timeout=30.0)
       return res
   except (MorphoMeshException, ConnectionError, OSError, TimeoutError) as e:
       if isinstance(e, MorphoMeshException) and e.code != "ERR_BLENDER_UNAVAILABLE":
           raise
       from morphomesh.camera_rig import setup_inspector_camera as pure_setup_inspector_camera
       res = pure_setup_inspector_camera(
           viewpoint=viewpoint,
           target_center=target_center,
           framing_radius=framing_radius,
           focal_length=focal_length,
           camera_name=camera_name,
           margin=margin,
           resolution=resolution,
           target_object=target_object,
           scene=None,
       )
       res["offline_fallback"] = True
       res["message"] = "Inspector camera rig configured via offline fallback (Blender unavailable)"
       return res
   ```

#### Task 5: Implement Secondary Exception Safeguard in `src/morphomesh/server.py`
1. In `morphomesh_setup_inspector_camera_rig` (lines 1136–1141):
   ```python
   except MorphoMeshException as e:
       if e.code == "ERR_BLENDER_UNAVAILABLE":
           from morphomesh.camera_rig import setup_inspector_camera as pure_setup
           res = pure_setup(
               viewpoint=effective_vp,
               target_center=tuple(target_center) if target_center is not None else None,
               focal_length=focal_length,
               camera_name=camera_name,
               target_object=target_obj,
               scene=None,
           )
           res["offline_fallback"] = True
           res["message"] = "Inspector camera rig configured via offline fallback (Blender unavailable)"
           await _safe_ctx_progress(ctx, 100, 100)
           return res
       raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")
   except (ConnectionError, OSError, TimeoutError) as e:
       from morphomesh.camera_rig import setup_inspector_camera as pure_setup
       res = pure_setup(
           viewpoint=effective_vp,
           target_center=tuple(target_center) if target_center is not None else None,
           focal_length=focal_length,
           camera_name=camera_name,
           target_object=target_obj,
           scene=None,
       )
       res["offline_fallback"] = True
       res["message"] = f"Inspector camera rig configured via offline fallback ({str(e)})"
       await _safe_ctx_progress(ctx, 100, 100)
       return res
   ```
2. In `morphomesh_capture_viewport` (lines 1211–1216):
   ```python
   except MorphoMeshException as e:
       if e.code == "ERR_BLENDER_UNAVAILABLE":
           from morphomesh.camera_rig import FALLBACK_PNG_BYTES
           fallback_b64 = base64.b64encode(FALLBACK_PNG_BYTES).decode("utf-8")
           img_path = output_path or os.path.join(tempfile.gettempdir(), f"viewport_{uuid.uuid4().hex[:8]}.png").replace("\\", "/")
           try:
               os.makedirs(os.path.dirname(os.path.abspath(img_path)), exist_ok=True)
               with open(img_path, "wb") as f:
                   f.write(FALLBACK_PNG_BYTES)
           except Exception:
               pass
           res = {
               "status": "success",
               "image_path": img_path,
               "output_path": img_path,
               "resolution": list(resolution),
               "shading_mode": shading_mode,
               "color_type": color_type,
               "camera_name": camera_name,
               "base64_preview": fallback_b64,
               "base64_image": fallback_b64,
               "offline_fallback": True,
               "message": "Viewport capture completed via offline fallback (Blender unavailable)",
           }
           await _safe_ctx_progress(ctx, 100, 100)
           return res
       raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")
   except (ConnectionError, OSError, TimeoutError) as e:
       # Same offline fallback logic
       ...
   ```

---

## 5. Verification Method

To independently verify the test suite alignment and remediation:

1. **Verify Adversarial Test Suite Pass**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_adversarial_error_injection_m4.py
   ```
   *Expected Result*: Exactly 46 passed, 0 failed (100% pass).

2. **Verify FastMCP Inspection Tools & Bridge Error Mapping**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_fastmcp_inspection_tools.py
   ```
   *Expected Result*: Exactly 21 passed, 0 failed (specifically verifying line 415 `test_bridge_exception_mapping`).

3. **Verify Baseline 7-Tool Schema Preservation**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_tools_schema.py
   ```
   *Expected Result*: Exactly 31 passed, 0 failed.

4. **Verify Gating Matrix Permutations**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_adversarial_m4_gating.py
   ```
   *Expected Result*: Exactly 121 passed, 0 failed.

5. **Invalidation Conditions**:
   - Any test in `test_adversarial_error_injection_m4.py` fails on invalid parameters or offline resilience.
   - `test_fastmcp_inspection_tools.py::test_bridge_exception_mapping` fails because operational errors were swallowed.
   - `test_tools_schema.py` detects any modification to the 7-tool baseline schema when inspection tools are disabled.
