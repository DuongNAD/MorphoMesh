# Milestone 4 Iteration 2 Explorer Report: Strict Enum Parameter Validation Blueprint

**Agent**: Explorer M4 Iteration 2 - 1 (`.agents/explorer_m4_iter2_1`)  
**Role**: Teamwork Explorer (Read-Only Investigation & Synthesis)  
**Date**: 2026-09-07T07:08:00Z  
**Parent Orchestrator**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Handoff Type**: Hard (Investigation & Technical Blueprint Complete)  
**Target Milestone**: Milestone 4 — FastMCP Tool Integration & Verification Suite (Iteration 2 Remediation)

---

## 1. Observation

### 1.1 Direct Adversarial Test Execution & Verbatim Failures
The adversarial test suite `tests/test_adversarial_error_injection_m4.py` was executed directly against `.venv`:
```powershell
.venv\Scripts\pytest.exe -v tests/test_adversarial_error_injection_m4.py
```
**Observed Result**: Exactly 22 failed, 24 passed (exit code 1).
Among the 22 failures, 20 are caused directly by missing enum/parameter validation:
1. **Viewpoint Failures** (`TestCameraRigParameterValidation`):
   - `test_invalid_viewpoints_rejected[nadir_flipped]` -> FAILED
   - `test_invalid_viewpoints_rejected[]` -> FAILED
   - `test_invalid_viewpoints_rejected[zenith_99]` -> FAILED
   - `test_invalid_viewpoints_rejected[diagonal_underneath]` -> FAILED
   - `test_invalid_viewpoints_rejected[UPWARD_45]` -> FAILED
2. **Shading Mode Failures** (`TestCaptureViewportParameterValidation`):
   - `test_invalid_shading_modes_rejected[PATH_TRACING]` -> FAILED
   - `test_invalid_shading_modes_rejected[RAYTRACING]` -> FAILED
   - `test_invalid_shading_modes_rejected[UNLIT_DEBUG]` -> FAILED
   - `test_invalid_shading_modes_rejected[]` -> FAILED
   - `test_invalid_shading_modes_rejected[NORMAL_MAP_PREVIEW]` -> FAILED
3. **Color Type Failures** (`TestCaptureViewportParameterValidation`):
   - `test_invalid_color_types_rejected[INVALID_COLOR_TYPE]` -> FAILED
   - `test_invalid_color_types_rejected[NEON_RAINBOW]` -> FAILED
   - `test_invalid_color_types_rejected[HSV_GRADIENT]` -> FAILED
   - `test_invalid_color_types_rejected[]` -> FAILED
   - `test_invalid_color_types_rejected[DEBUG_UV]` -> FAILED
4. **Target Preset Failures** (`TestVisualCritiqueParameterValidation`):
   - `test_invalid_target_preset_rejected[alien_hydra]` -> FAILED
   - `test_invalid_target_preset_rejected[draconic_quadruped]` -> FAILED
   - `test_invalid_target_preset_rejected[spider_titan]` -> FAILED
   - `test_invalid_target_preset_rejected[]` -> FAILED
   - `test_invalid_target_preset_rejected[unknown_preset]` -> FAILED

### 1.2 Existing Implementation Analysis

#### A. `src/morphomesh/server.py`
- **Tool 1: `morphomesh_setup_inspector_camera_rig`** (lines 1100–1120):
  ```python
  @mcp.tool(name="morphomesh_setup_inspector_camera_rig")
  async def morphomesh_setup_inspector_camera_rig(
      viewpoint: str = "three_quarter",
      target_center: Optional[List[float]] = None,
      sub_region: Optional[str] = None,
      focal_length: float = 50.0,
      camera_name: str = "MorphoMesh_Inspector_Camera",
      mesh_objects: Optional[List[str]] = None,
      ctx: Optional[Context] = None,
  ) -> Dict[str, Any]:
      ...
      # Pre-flight parameter validation
      if focal_length < 10.0 or focal_length > 300.0:
          raise ToolError(...)
      if target_center is not None and (not isinstance(target_center, (list, tuple)) or len(target_center) != 3):
          raise ToolError(...)
      if not camera_name or not camera_name.strip():
          raise ToolError(...)
  ```
  *Defect*: `viewpoint` parameter is never checked against allowed values or empty strings.
- **Tool 2: `morphomesh_capture_viewport`** (lines 1148–1174):
  ```python
  @mcp.tool(name="morphomesh_capture_viewport")
  async def morphomesh_capture_viewport(
      output_path: Optional[str] = None,
      camera_name: str = "MorphoMesh_Inspector_Camera",
      resolution: List[int] = [1024, 1024],
      shading_mode: str = "SOLID",
      color_type: str = "RANDOM",
      ctx: Optional[Context] = None,
  ) -> Dict[str, Any]:
      ...
      # Pre-flight validation
      if not isinstance(resolution, (list, tuple)) or len(resolution) != 2 or any(r <= 0 for r in resolution):
          raise ToolError(...)
      if not camera_name or not camera_name.strip():
          raise ToolError(...)
  ```
  *Defect*: Neither `shading_mode` nor `color_type` is validated.
- **Tool 3: `morphomesh_critique_visual_quality`** (lines 1223–1251):
  ```python
  @mcp.tool(name="morphomesh_critique_visual_quality")
  async def morphomesh_critique_visual_quality(
      character_name: str = "MorphoMesh_Character",
      target_object: Optional[str] = None,
      camera_angles: Optional[List[str]] = None,
      clearance_tolerance: float = 0.0005,
      target_preset: str = "stylized_heroine",
      ctx: Optional[Context] = None,
  ) -> Dict[str, Any]:
      ...
      # Pre-flight validation
      if clearance_tolerance < 0.0:
          raise ToolError(...)
      if not character_name and not target_object:
          raise ToolError(...)
  ```
  *Defect*: `target_preset` parameter is never validated against allowed presets or empty strings.

#### B. `src/morphomesh/camera_rig.py`
- Lines 392–422 define `CANONICAL_VIEWPOINTS`:
  Contains `front`, `side`, `side_left`, `back`, `three_quarter`, `top`, `head`, `close_up_head`, `portrait`, `hands`, `close_up_hands`, `torso`, `feet`, plus aliases (`front_view`, `view_front`, `side_right`, `view_side`, `view_side_left`, `view_back`, `back_view`, `front_three_quarter`, `three_quarter_left`, `back_three_quarter`, `head_close_up`, `hands_close_up`, `marionette`, `bodice`, `sandals`, `shoes`).
- Missing keys: `"bottom"`, `"turntable"`, `"turntable_4views"`.
- Line 839: `vp_spec = CANONICAL_VIEWPOINTS.get(vp_clean, CANONICAL_VIEWPOINTS["three_quarter"])` silently falls back to `"three_quarter"` for any unknown viewpoint string.
- Lines 940–944 in `capture_viewport_image`:
  ```python
  norm_shading = shading_mode.upper() if shading_mode and shading_mode.upper() in valid_shading else "SOLID"
  norm_color = color_type.upper() if color_type and color_type.upper() in valid_colors else "RANDOM"
  ```
  Silently coerces unknown shading/color to `"SOLID"` and `"RANDOM"`.

#### C. `src/morphomesh/visual_critic.py`
- Lines 1301–1332 define `ANTHROPOMETRIC_PRESETS`:
  Only 3 presets exist: `"realistic_human"`, `"stylized_heroine"`, `"chibi_petite"`.
- Missing keys required by specification: `"realistic_female"`, `"heroic_male"`, `"chibi"`.
- Line 1366 in `evaluate_body_proportions`:
  `preset = ANTHROPOMETRIC_PRESETS.get(target_preset, ANTHROPOMETRIC_PRESETS["stylized_heroine"])`
  Silently defaults unknown presets to `"stylized_heroine"`.

#### D. `src/morphomesh/models.py`
- `InspectorViewpoint` Enum lacks `BOTTOM = "bottom"`, `TURNTABLE = "turntable"`, and `TURNTABLE_4VIEWS = "turntable_4views"`.
- `DiagnosticShadingMode` and `DiagnosticColorType` exist and match canonical values (`SOLID`, `FLAT`, `WIREFRAME`, `MATERIAL`, `RENDERED` / `RANDOM`, `MATERIAL`, `SINGLE`, `OBJECT`, `TEXTURE`).
- There is no `AnthropometricPreset` (or `TargetPreset`) Enum.
- Pydantic models (`SetupInspectorCameraInput`, `CaptureViewportInput`, `VisualCritiqueInput`) declare unconstrained `str` fields without `@field_validator` constraints.

---

## 2. Logic Chain

1. **Direct Invocation vs. FastMCP Protocol**:
   - In FastMCP, tool functions registered via `@mcp.tool()` can be invoked via two distinct paths:
     a) Protocol-level via `mcp.call_tool(name, args)`: FastMCP parses and coerces arguments against function type annotations.
     b) Direct Python async function calls via `await morphomesh_setup_inspector_camera_rig(...)` as executed in `test_adversarial_error_injection_m4.py`.
   - Direct Python function calls execute the underlying function directly, completely bypassing FastMCP's argument serialization.
   - Therefore, strict parameter validation MUST exist inside the pre-flight block of each tool function in `server.py`, explicitly raising `ToolError`.

2. **Schema Stability & FastMCP Type Annotation Strategy**:
   - In `tests/test_fastmcp_inspection_tools.py` (line 137, 148, 149, 159), tests explicitly assert properties on the generated `inputSchema`:
     `props1["viewpoint"]["default"] == "three_quarter"`
     `props2["shading_mode"]["default"] == "SOLID"`
     `props2["color_type"]["default"] == "RANDOM"`
     `props3["target_preset"]["default"] == "stylized_heroine"`
   - If function signatures in `server.py` are modified to use strict Enum annotations (e.g. `viewpoint: InspectorViewpoint`), FastMCP's Pydantic schema generator converts the property into a `$defs` reference (`{"$ref": "#/$defs/InspectorViewpoint", "default": "three_quarter"}`), altering the JSON Schema structure and potentially breaking downstream MCP clients or schema tests that expect primitive string types.
   - Preserving `viewpoint: str = "three_quarter"`, `shading_mode: str = "SOLID"`, `color_type: str = "RANDOM"`, and `target_preset: str = "stylized_heroine"` in the function signatures while enforcing strict validation in the function body guarantees 100% schema backward compatibility.
   - Concurrently, adding `@field_validator` rules to the Pydantic models in `src/morphomesh/models.py` guarantees model-level validation whenever input models are instantiated.

3. **Domain Parity Across the 4 Layers**:
   - For validation to be cohesive, the allowed parameter sets must be identical across:
     - `src/morphomesh/server.py` (pre-flight validation raising `ToolError`)
     - `src/morphomesh/models.py` (Pydantic Enums and `@field_validator` raising `ValidationError`)
     - `src/morphomesh/camera_rig.py` (`CANONICAL_VIEWPOINTS` coordinate dictionaries)
     - `src/morphomesh/visual_critic.py` (`ANTHROPOMETRIC_PRESETS` ratio dictionaries)

---

## 3. Concrete Blueprint & Proposed Implementations

### Blueprint 1: `src/morphomesh/models.py`

#### 1.1 Update `InspectorViewpoint`
Add `BOTTOM`, `TURNTABLE`, and `TURNTABLE_4VIEWS`:
```python
class InspectorViewpoint(str, Enum):
    FRONT = "front"
    SIDE = "side"
    SIDE_LEFT = "side_left"
    BACK = "back"
    THREE_QUARTER = "three_quarter"
    TOP = "top"
    BOTTOM = "bottom"
    HEAD = "head"
    CLOSE_UP_HEAD = "close_up_head"
    PORTRAIT = "portrait"
    HANDS = "hands"
    CLOSE_UP_HANDS = "close_up_hands"
    TORSO = "torso"
    FEET = "feet"
    TURNTABLE = "turntable"
    TURNTABLE_4VIEWS = "turntable_4views"
```

#### 1.2 Add `AnthropometricPreset` Enum
```python
class AnthropometricPreset(str, Enum):
    REALISTIC_HUMAN = "realistic_human"
    STYLIZED_HEROINE = "stylized_heroine"
    CHIBI_PETITE = "chibi_petite"
    REALISTIC_FEMALE = "realistic_female"
    HEROIC_MALE = "heroic_male"
    CHIBI = "chibi"

TargetPreset = AnthropometricPreset
```

#### 1.3 Add Field Validators to Input Models
```python
VALID_INSPECTOR_VIEWPOINTS_SET = {e.value for e in InspectorViewpoint} | {
    "view_front", "front_view", "side_right", "view_side", "view_side_left",
    "view_back", "back_view", "front_three_quarter", "three_quarter_left",
    "back_three_quarter", "head_close_up", "hands_close_up", "marionette",
    "bodice", "sandals", "shoes",
}

# In SetupInspectorCameraInput:
@field_validator("viewpoint")
@classmethod
def validate_viewpoint(cls, v: str) -> str:
    if not v or not isinstance(v, str) or not v.strip():
        raise ValueError("viewpoint cannot be empty")
    v_clean = v.lower().strip()
    if v_clean not in VALID_INSPECTOR_VIEWPOINTS_SET:
        raise ValueError(f"Invalid viewpoint '{v}'. Allowed: {sorted(list(VALID_INSPECTOR_VIEWPOINTS_SET))}")
    return v_clean

# In CaptureViewportInput:
@field_validator("shading_mode")
@classmethod
def validate_shading_mode(cls, v: str) -> str:
    if not v or not isinstance(v, str) or not v.strip():
        raise ValueError("shading_mode cannot be empty")
    v_upper = v.upper().strip()
    valid_shading = {e.value for e in DiagnosticShadingMode}
    if v_upper not in valid_shading:
        raise ValueError(f"Invalid shading_mode '{v}'. Allowed: {sorted(list(valid_shading))}")
    return v_upper

@field_validator("color_type")
@classmethod
def validate_color_type(cls, v: str) -> str:
    if not v or not isinstance(v, str) or not v.strip():
        raise ValueError("color_type cannot be empty")
    v_upper = v.upper().strip()
    valid_colors = {e.value for e in DiagnosticColorType}
    if v_upper not in valid_colors:
        raise ValueError(f"Invalid color_type '{v}'. Allowed: {sorted(list(valid_colors))}")
    return v_upper

# In VisualCritiqueInput:
@field_validator("target_preset")
@classmethod
def validate_target_preset(cls, v: str) -> str:
    if not v or not isinstance(v, str) or not v.strip():
        raise ValueError("target_preset cannot be empty")
    v_clean = v.lower().strip()
    valid_presets = {e.value for e in AnthropometricPreset}
    if v_clean not in valid_presets:
        raise ValueError(f"Invalid target_preset '{v}'. Allowed: {sorted(list(valid_presets))}")
    return v_clean
```

---

### Blueprint 2: `src/morphomesh/server.py`

#### 2.1 Constants Definition (near top of inspection tool section)
```python
VALID_INSPECTOR_VIEWPOINTS: Set[str] = {
    "front", "side", "side_left", "back", "three_quarter", "top", "bottom",
    "head", "close_up_head", "portrait", "hands", "close_up_hands",
    "torso", "feet", "turntable", "turntable_4views",
    "view_front", "front_view", "side_right", "view_side", "view_side_left",
    "view_back", "back_view", "front_three_quarter", "three_quarter_left",
    "back_three_quarter", "head_close_up", "hands_close_up", "marionette",
    "bodice", "sandals", "shoes",
}

VALID_SHADING_MODES: Set[str] = {"SOLID", "FLAT", "WIREFRAME", "MATERIAL", "RENDERED"}
VALID_COLOR_TYPES: Set[str] = {"RANDOM", "MATERIAL", "SINGLE", "OBJECT", "TEXTURE"}
VALID_TARGET_PRESETS: Set[str] = {
    "realistic_human", "stylized_heroine", "chibi_petite",
    "realistic_female", "heroic_male", "chibi",
}
```

#### 2.2 Pre-flight Validation in `morphomesh_setup_inspector_camera_rig`
Replace lines 1113–1120 in `src/morphomesh/server.py`:
```python
    # Pre-flight parameter validation
    if not viewpoint or not isinstance(viewpoint, str) or not viewpoint.strip():
        raise ToolError("MorphoMesh Parameter Validation Error: 'viewpoint' cannot be empty.")
    vp_norm = viewpoint.lower().strip()
    if vp_norm not in VALID_INSPECTOR_VIEWPOINTS:
        raise ToolError(
            f"MorphoMesh Parameter Validation Error: Invalid viewpoint '{viewpoint}'. "
            f"Allowed viewpoints: {sorted(list(VALID_INSPECTOR_VIEWPOINTS))}."
        )

    if focal_length < 10.0 or focal_length > 300.0:
        raise ToolError(f"MorphoMesh Parameter Validation Error: 'focal_length' must be between 10.0 and 300.0 mm (got {focal_length}).")
    if target_center is not None and (not isinstance(target_center, (list, tuple)) or len(target_center) != 3):
        raise ToolError("MorphoMesh Parameter Validation Error: 'target_center' must be a list of 3 coordinates [x, y, z].")
    if not camera_name or not camera_name.strip():
        raise ToolError("MorphoMesh Parameter Validation Error: 'camera_name' cannot be empty.")
```

#### 2.3 Pre-flight Validation in `morphomesh_capture_viewport`
Replace lines 1169–1174 in `src/morphomesh/server.py`:
```python
    # Pre-flight validation
    if not shading_mode or not isinstance(shading_mode, str) or not shading_mode.strip():
        raise ToolError("MorphoMesh Parameter Validation Error: 'shading_mode' cannot be empty.")
    shading_norm = shading_mode.upper().strip()
    if shading_norm not in VALID_SHADING_MODES:
        raise ToolError(
            f"MorphoMesh Parameter Validation Error: Invalid shading_mode '{shading_mode}'. "
            f"Allowed shading modes: {sorted(list(VALID_SHADING_MODES))}."
        )

    if not color_type or not isinstance(color_type, str) or not color_type.strip():
        raise ToolError("MorphoMesh Parameter Validation Error: 'color_type' cannot be empty.")
    color_norm = color_type.upper().strip()
    if color_norm not in VALID_COLOR_TYPES:
        raise ToolError(
            f"MorphoMesh Parameter Validation Error: Invalid color_type '{color_type}'. "
            f"Allowed color types: {sorted(list(VALID_COLOR_TYPES))}."
        )

    if not isinstance(resolution, (list, tuple)) or len(resolution) != 2 or any(r <= 0 for r in resolution):
        raise ToolError("MorphoMesh Parameter Validation Error: 'resolution' must be a list/tuple of 2 positive integers [width, height].")
    if not camera_name or not camera_name.strip():
        raise ToolError("MorphoMesh Parameter Validation Error: 'camera_name' cannot be empty.")
```
And pass `shading_mode=shading_norm` and `color_type=color_norm` to `blender_bridge.capture_viewport`.

#### 2.4 Pre-flight Validation in `morphomesh_critique_visual_quality`
Replace lines 1246–1251 in `src/morphomesh/server.py`:
```python
    # Pre-flight validation
    if not target_preset or not isinstance(target_preset, str) or not target_preset.strip():
        raise ToolError("MorphoMesh Parameter Validation Error: 'target_preset' cannot be empty.")
    preset_norm = target_preset.lower().strip()
    if preset_norm not in VALID_TARGET_PRESETS:
        raise ToolError(
            f"MorphoMesh Parameter Validation Error: Invalid target_preset '{target_preset}'. "
            f"Allowed target presets: {sorted(list(VALID_TARGET_PRESETS))}."
        )

    if clearance_tolerance < 0.0:
        raise ToolError("MorphoMesh Parameter Validation Error: 'clearance_tolerance' must be non-negative.")
    if not character_name and not target_object:
        raise ToolError("MorphoMesh Parameter Validation Error: Either 'character_name' or 'target_object' must be provided.")
```
And pass `target_preset=preset_norm` to `blender_bridge.critique_visual_quality`.

---

### Blueprint 3: `src/morphomesh/camera_rig.py`

Add missing keys to `CANONICAL_VIEWPOINTS` (lines 392–422):
```python
CANONICAL_VIEWPOINTS: Dict[str, Dict[str, Any]] = {
    ...
    "bottom": {"azimuth": 0.0, "elevation": -88.0, "subregion": "full_body", "default_focal": 50.0, "margin": 0.20},
    "turntable": {"azimuth": 45.0, "elevation": 15.0, "subregion": "full_body", "default_focal": 50.0, "margin": 0.15},
    "turntable_4views": {"azimuth": 0.0, "elevation": 0.0, "subregion": "full_body", "default_focal": 50.0, "margin": 0.15},
    ...
}
```

---

### Blueprint 4: `src/morphomesh/visual_critic.py`

Add missing presets to `ANTHROPOMETRIC_PRESETS` (lines 1301–1332):
```python
ANTHROPOMETRIC_PRESETS: Dict[str, Dict[str, Any]] = {
    "realistic_human": {
        "head_ratio_min": 7.0,
        "head_ratio_max": 8.0,
        "head_ratio_nominal": 7.5,
        "arm_span_ratio_min": 0.95,
        "arm_span_ratio_max": 1.05,
        "shoulder_to_hip_feminine": (0.90, 1.05),
        "shoulder_to_hip_masculine": (1.20, 1.45),
        "typical_height_range": (1.55, 1.90),
    },
    "stylized_heroine": {
        "head_ratio_min": 6.0,
        "head_ratio_max": 7.6,
        "head_ratio_nominal": 6.8,
        "arm_span_ratio_min": 0.90,
        "arm_span_ratio_max": 1.08,
        "shoulder_to_hip_feminine": (0.85, 1.10),
        "shoulder_to_hip_masculine": (1.15, 1.35),
        "typical_height_range": (1.50, 1.75),
    },
    "chibi_petite": {
        "head_ratio_min": 2.0,
        "head_ratio_max": 5.0,
        "head_ratio_nominal": 3.5,
        "arm_span_ratio_min": 0.80,
        "arm_span_ratio_max": 1.05,
        "shoulder_to_hip_feminine": (0.85, 1.10),
        "shoulder_to_hip_masculine": (0.95, 1.15),
        "typical_height_range": (0.80, 1.35),
    },
    "realistic_female": {
        "head_ratio_min": 7.0,
        "head_ratio_max": 8.0,
        "head_ratio_nominal": 7.5,
        "arm_span_ratio_min": 0.95,
        "arm_span_ratio_max": 1.05,
        "shoulder_to_hip_feminine": (0.90, 1.05),
        "shoulder_to_hip_masculine": (1.20, 1.45),
        "typical_height_range": (1.55, 1.80),
    },
    "heroic_male": {
        "head_ratio_min": 7.5,
        "head_ratio_max": 8.5,
        "head_ratio_nominal": 8.0,
        "arm_span_ratio_min": 0.98,
        "arm_span_ratio_max": 1.08,
        "shoulder_to_hip_feminine": (1.00, 1.20),
        "shoulder_to_hip_masculine": (1.30, 1.55),
        "typical_height_range": (1.80, 2.05),
    },
    "chibi": {
        "head_ratio_min": 2.0,
        "head_ratio_max": 5.0,
        "head_ratio_nominal": 3.5,
        "arm_span_ratio_min": 0.80,
        "arm_span_ratio_max": 1.05,
        "shoulder_to_hip_feminine": (0.85, 1.10),
        "shoulder_to_hip_masculine": (0.95, 1.15),
        "typical_height_range": (0.80, 1.35),
    },
}
```

---

## 4. Caveats

1. **Direct Async Invocation vs Protocol Call**:
   - Calling the python function directly (e.g. `await morphomesh_setup_inspector_camera_rig(viewpoint="...")`) invokes the unwrapped async function directly.
   - Calling through FastMCP client (e.g. `await mcp.call_tool("morphomesh_setup_inspector_camera_rig", {"viewpoint": "..."})`) routes through FastMCP's internal tool executor.
   - Both paths MUST consistently raise `mcp.server.fastmcp.exceptions.ToolError`. The proposed design guarantees both paths raise `ToolError`.
2. **Offline Bridge Resilience**:
   - In addition to the 20 enum validation failures, 2 failures in `test_adversarial_error_injection_m4.py` were caused by offline bridge execution when `blender_bridge.is_interactive_connected() == False` and `blender_bin_path == None`.
   - In `setup_inspector_camera_rig` and `capture_viewport`, the catch blocks in `server.py` (or fallbacks in `blender_bridge.py`) must catch `MorphoMeshException("ERR_BLENDER_UNAVAILABLE")` and return mock camera metadata / `FALLBACK_PNG_BYTES` with `status="success"`.
3. **Read-Only Explorer Scope**:
   - Explorer M4_Iter2_1 performed strictly read-only exploration and prototyping. No source code files in `src/` or `tests/` were modified.

---

## 5. Conclusion

- **Root Cause Identified**:
  The failure of 20 adversarial parameter validation tests was due to the complete absence of pre-flight checks for `viewpoint`, `shading_mode`, `color_type`, and `target_preset` in `src/morphomesh/server.py`, coupled with silent `.get(key, default)` fallback behavior in downstream calculation modules (`camera_rig.py` and `visual_critic.py`).
- **Solution Strategy**:
  Implement explicit pre-flight parameter validation in `server.py` raising `ToolError` with informative error messages satisfying test regex patterns. Synchronize `InspectorViewpoint`, `AnthropometricPreset`, and Pydantic field validators in `models.py`. Update `CANONICAL_VIEWPOINTS` in `camera_rig.py` and `ANTHROPOMETRIC_PRESETS` in `visual_critic.py` to achieve complete 4-layer parity.
- **Impact on Schema**:
  Preserves `type: "string"` and `default: ...` in the FastMCP tool JSON Schema, guaranteeing 100% backward compatibility with `test_fastmcp_inspection_tools.py`, `test_adversarial_m4_gating.py`, and `test_tools_schema.py`.

---

## 6. Verification Method

To independently verify the blueprint:

1. **Verify Adversarial Test Suite Coverage**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_adversarial_error_injection_m4.py
   ```
   *Expected After Remediation*: 46 passed (0 failed).

2. **Verify Regression Test Suites Unaffected**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_fastmcp_inspection_tools.py tests/test_inspector_camera.py tests/test_visual_critic.py tests/test_adversarial_m4_gating.py
   ```
   *Expected After Remediation*: 100% passed with zero regressions.

3. **Verify Pure-Python Invocations**:
   ```powershell
   .venv\Scripts\python.exe -c "import asyncio; from mcp.server.fastmcp.exceptions import ToolError; from morphomesh.server import morphomesh_setup_inspector_camera_rig; 
   try:
       asyncio.run(morphomesh_setup_inspector_camera_rig(viewpoint='nadir_flipped'))
   except ToolError as e:
       print('Successfully caught ToolError:', e)"
   ```
   *Expected Result*: Catches `ToolError` containing `"MorphoMesh Parameter Validation Error: Invalid viewpoint 'nadir_flipped'"`.
