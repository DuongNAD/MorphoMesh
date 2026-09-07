# Handoff Report: Review & Adversarial Audit of Milestone 3 PBR Shaders

**Reviewer Agent**: `reviewer_human_m3_1`  
**Parent Orchestrator**: `orchestrator_human_1` (Conversation ID: `fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Target Subject**: Milestone 3 (`src/morphomesh/human_materials.py` and related scripts)  
**Date**: 2026-09-06T19:30:30Z  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Direct Test Suite Execution
1. Executed unit test suite for materials:
   ```powershell
   pytest -v tests/test_human_materials.py
   ```
   *Result*: `10 passed in 0.02s` (Exit code: 0).
2. Executed full digital human test suite:
   ```powershell
   pytest -v tests/test_human_generator.py tests/test_adversarial_human_generator.py tests/test_human_rigging.py tests/test_human_materials.py tests/test_human_grooming.py tests/test_wardrobe.py tests/test_fastmcp_human_tools.py tests/test_adversarial_fastmcp_bridge_human.py
   ```
   *Result*: `184 passed in 17.20s` (Exit code: 0).

### 1.2 Verification of Material Physical Parameter Specifications
Inspected `src/morphomesh/human_materials.py`:
- **Principled BSDF v2 Skin SSS (`Mat_Human_Skin_SSS`)** (lines 91–111):
  * `subsurface_weight = 0.28`, `subsurface_radius = (1.0, 0.2, 0.1)`, `subsurface_scale = 0.024`, `subsurface_method = "RANDOM_WALK"`, `subsurface_ior = 1.40`.
  * `ior = 1.45`, `roughness = 0.35`, `specular_ior_level = 0.50`, `metallic = 0.0`.
  * Micro-roughness specular bump: `bump_strength = 0.030`, `bump_scale = 380.0`, `texture_type = "NOISE"`.
  * Base color: `(0.918, 0.791, 0.723, 1.0)` (#F6E4DA porcelain fair).
- **Outer Cornea (`Mat_Human_Eye_Outer_Cornea`)** (lines 114–125, 375–399, 602–624):
  * `transmission_weight = 1.0`, `roughness = 0.02`, `ior = 1.376` (true anatomical corneal index).
  * Light Path shadow bypass: `ShaderNodeLightPath` output `Is Shadow Ray` connects to `ShaderNodeMixShader.inputs['Fac']`, switching to `ShaderNodeBsdfTransparent` for shadow rays to eliminate dark cast shadows on the inner iris.
- **Inner Iris & Pupil (`Mat_Human_Eye_Inner_Iris`)** (lines 128–144, 477–503, 694–716):
  * Base color: `(0.141, 0.165, 0.188, 1.0)` (#2D343B dark charcoal/slate stroma).
  * SSS: `subsurface_weight = 0.18`, `radius = (0.6, 0.2, 0.1)`.
  * Radial fiber gradient: `ShaderNodeTexCoord` -> `ShaderNodeVectorMath` (`LENGTH`) -> `ShaderNodeValToRGB` (ColorRamp).
  * ColorRamp contains pupil at `0.0`, stroma at `pupil_dilation = 0.35`, limbal ring at `0.85`, and edge at `0.98`.
- **Sclera (`Mat_Human_Eye_Sclera`)** (lines 146–161):
  * Base color: `(0.949, 0.945, 0.941, 1.0)` (#F2F1F0 moist off-white).
  * `roughness = 0.08`, `subsurface_weight = 0.20`, `radius = (0.8, 0.3, 0.1)`.
  * Subtle vascular red noise bump: `bump_strength = 0.04`, `bump_scale = 250.0`.
- **Melanin Hair BSDF (`Mat_Human_Hair`)** (lines 163–176, 350–374, 586–601):
  * `is_hair = True`, `melanin = 0.85`, `melanin_redness = 0.12`.
  * `roughness = 0.25`, `radial_roughness = 0.45`, `coat_weight = 0.45` (angel-ring specular halo), `ior = 1.55`.
  * Builds `ShaderNodeBsdfHairPrincipled` with corresponding socket bindings.
- **Wardrobe & Magic Materials** (lines 178–252):
  * `Mat_Dress_WhiteSilk`: Base `(0.95, 0.95, 0.95, 1.0)`, `sheen_weight = 0.60`, `roughness = 0.40`, `subsurface_weight = 0.14`.
  * `Mat_Dress_WaistBelt`: Base `(0.15, 0.15, 0.15, 1.0)`, `roughness = 0.50`.
  * `Mat_Sandal_Leather`: Base `(0.10, 0.08, 0.07, 1.0)`, `roughness = 0.45`.
  * `Mat_Marionette_RedString`: Base `(0.902, 0.0, 0.149, 1.0)`, `emission_strength = 6.5`, `emission_color = (1.0, 0.122, 0.239, 1.0)`.
  * `Mat_Magic_Butterfly`: Base `(1.0, 1.0, 1.0, 1.0)`, `subsurface_weight = 0.45`, `emission_strength = 3.2`.

### 1.3 Direct Adversarial Runtime Execution Failure
When executing the generated script from `get_material_setup_script()` under Python with mocked `bpy`:
```python
import sys
from unittest.mock import MagicMock
sys.modules['bpy'] = MagicMock()
from morphomesh.human_materials import get_material_setup_script
exec(get_material_setup_script())
```
*Direct Error Observed*:
```
NameError: name 'false' is not defined
```
*Exact Location in Generated Script* (line 59 of generated script):
```python
MAT_CONFIGS = {
  "Mat_Human_Skin_SSS": {
    ...
    "is_hair": false,
    ...
  }
}
```
*Source Code in `src/morphomesh/human_materials.py`* (lines 548–560):
```python
mat_configs_serialized = {k: v.to_dict() for k, v in STANDARD_HUMAN_MATERIALS.items()}
mat_json = json.dumps(mat_configs_serialized, indent=2)

script = f'''...
MAT_CONFIGS = {mat_json}
...'''
```
*Related Silent Failure in `src/morphomesh/blender_bridge.py`* (lines 1796–1800):
```python
try:
    from morphomesh.human_materials import get_material_setup_script
    exec(get_material_setup_script(target_object=mesh_name, material_preset=preset))
except Exception:
    # Silent fallback facade executed!
    for m_name in created_mats:
        mat = bpy.data.materials.get(m_name) or bpy.data.materials.new(name=m_name)
        ...
```
*Related Failure in `src/morphomesh/wardrobe.py`* (line 579):
When running `exec(get_wardrobe_script())`, Python crashes with:
```
NameError: name 'true' is not defined
```
caused by `CFG = {cfg_json}` where `json.dumps` serialized `include_sandals: true`.

---

## 2. Logic Chain

1. **Physical Shader Definitions Are Sound (Obs 1.2)**:
   The physical configuration parameters for `Mat_Human_Skin_SSS`, `Mat_Human_Eye_Outer_Cornea`, `Mat_Human_Eye_Inner_Iris`, `Mat_Human_Eye_Sclera`, `Mat_Human_Hair`, dress silk, belt, sandals, red strings, and butterflies strictly match all physical optics requirements from `ORIGINAL_REQUEST.md`, `PROJECT.md`, and the survey. The node builder logic in `build_principled_bsdf_v2_material` cleanly constructs valid Cycles/EEVEE Principled BSDF v2 and Hair BSDF graphs.

2. **The Standalone Script Generator Has a Fatal Syntax-Runtime Mismatch (Obs 1.3)**:
   In `src/morphomesh/human_materials.py` line 559, `mat_json` is produced by `json.dumps(mat_configs_serialized, indent=2)` and interpolated directly into python code as an f-string: `MAT_CONFIGS = {mat_json}`.
   Because JSON specifications dictate lowercase boolean literals (`false`, `true`), the resulting Python source code contains unquoted lowercase `false` (`"is_hair": false`).

3. **Shallow Test Verification Concealed the Runtime Crash (Obs 1.1, Obs 1.3)**:
   In `tests/test_human_materials.py` line 139, `test_script_generates_valid_python_ast` tests the script only via `ast.parse(script)`. In Python grammar, `false` is parsed validly as an `ast.Name(id='false')` node (an identifier expression). `ast.parse()` only validates abstract syntax grammar; it performs no symbol lookup or runtime execution.
   Consequently, the test passed 100% while the script is unexecutable in Python or Blender.

4. **Silent Exception Masking in Bridge Concealed the Defect from Bridge Tests (Obs 1.3)**:
   In `src/morphomesh/blender_bridge.py` lines 1797–1800, `exec(get_material_setup_script(...))` is enclosed in a broad `try ... except Exception:` block. When `exec` crashes with `NameError: name 'false' is not defined`, the bridge silently catches the error and activates a hardcoded fallback loop that creates basic materials, masking the crash from callers and tests.

5. **Same Defect Exists in `wardrobe.py`**:
   `src/morphomesh/wardrobe.py` line 579 similarly does `CFG = {cfg_json}`, which crashes at runtime with `NameError: name 'true' is not defined`.

6. **Graphical Flaw in Iris Radial UV Mapping (Obs 1.2)**:
   In `build_principled_bsdf_v2_material` (line 482) and `get_material_setup_script` (line 697), `ShaderNodeVectorMath` with operation `LENGTH` directly samples `ShaderNodeTexCoord.outputs['UV']`. In standard normalized UV coordinates $[0, 1] \times [0, 1]$, `LENGTH` computes distance from UV origin $(0.0, 0.0)$ (the corner of the texture space) rather than the center $(0.5, 0.5)$. If applied to standard planar UVs, the pupil is placed at the corner rather than the center of the eye dish.

---

## 3. Caveats

- **Cycles Raytracing Dependency**: Random Walk Subsurface Scattering and the Cornea Light Path shadow bypass are optimized for Cycles path tracing. When rendered in EEVEE Next, raytraced transmission and screen-space subsurface scattering must be explicitly enabled.
- **Dual-Chamber Geometry Separation**: The material script maps cornea and skin on the base body mesh, and maps separate eye objects (`Mesh_Eye_Left_CorneaSclera` and `Mesh_Eye_Left_IrisPupil`) to cornea and iris materials. This works properly as long as Milestone 4 assembly uses the dual-chamber eye meshes.
- **Character Limit in `BpyCodeValidator`**: `BpyCodeValidator.validate()` in `blender_bridge.py` enforces a 10,000-character limit for user-submitted interactive scripts. Generated headless scripts (~26,000 characters) are executed via CLI file runners or socket RPC rather than user script submission, which is by design.

---

## 4. Conclusion & Findings

### Finding 1: [Critical / Defect] Standalone Script Generators Fail Runtime with `NameError`
- **Location**:
  * `src/morphomesh/human_materials.py`: line 559 (`MAT_CONFIGS = {mat_json}`)
  * `src/morphomesh/wardrobe.py`: line 579 (`CFG = {cfg_json}`)
- **Impact**: Any direct execution of `get_material_setup_script()` or `get_wardrobe_script()` inside Blender or Python raises `NameError: name 'false' is not defined` (or `name 'true' is not defined`), aborting script execution and triggering the silent fallback facade in `blender_bridge.py`.
- **Root Cause**: Embedding raw `json.dumps()` output directly into Python source without converting JSON booleans to Python literals or wrapping in `json.loads(...)`.
- **Recommended Fix**:
  In `src/morphomesh/human_materials.py`:
  Replace:
  ```python
  MAT_CONFIGS = {mat_json}
  ```
  with:
  ```python
  MAT_CONFIGS = json.loads('''{mat_json}''')
  ```
  (or embed Python literal representation `repr(mat_configs_serialized)`).
  Apply the identical fix to `src/morphomesh/wardrobe.py`:
  ```python
  CFG = json.loads('''{cfg_json}''')
  ```

### Finding 2: [Major / Test Blind Spot] Self-Certifying AST Syntax Check
- **Location**: `tests/test_human_materials.py`: lines 128–142 (`test_script_generates_valid_python_ast`)
- **Impact**: Allowed unexecutable code with fatal runtime errors to pass as verified.
- **Root Cause**: Using only `ast.parse(script)` which verifies syntax but not runtime execution or variable names.
- **Recommended Fix**:
  Update `test_script_generates_valid_python_ast` to also verify compilation and execution in a controlled environment:
  ```python
  code_obj = compile(script, "<generated_script>", "exec")
  mock_scope = {"bpy": MagicMock(), "math": math, "json": json}
  exec(code_obj, mock_scope, mock_scope)
  ```

### Finding 3: [Minor / Shader Improvement] Iris Radial Mapping UV Center Offset
- **Location**: `src/morphomesh/human_materials.py`: lines 482–486, 697–701
- **Impact**: Iris radial gradient calculates `LENGTH` from $(0, 0)$ instead of the $(0.5, 0.5)$ center of normalized UV coordinates.
- **Recommended Fix**:
  Insert a `ShaderNodeVectorMath` node with operation `SUBTRACT` subtracting `(0.5, 0.5, 0.0)` before the `LENGTH` node (or use `ShaderNodeTexCoord.outputs['Object']`).

---

## 5. Verification Method

To independently verify the defect and validate the remediation:

1. **Reproduce the Fatal Runtime Crash**:
   Run the following command:
   ```bash
   python -c "import sys; from unittest.mock import MagicMock; sys.modules['bpy'] = MagicMock(); from morphomesh.human_materials import get_material_setup_script; exec(get_material_setup_script())"
   ```
   *Expected Current Output*: `NameError: name 'false' is not defined`.
   *Target Remediated Output*: Clean execution without exceptions.

2. **Verify Wardrobe Script Execution**:
   ```bash
   python -c "import sys; from unittest.mock import MagicMock; sys.modules['bpy'] = MagicMock(); sys.modules['mathutils'] = MagicMock(); from morphomesh.wardrobe import get_wardrobe_script; exec(get_wardrobe_script())"
   ```
   *Expected Current Output*: `NameError: name 'true' is not defined`.
   *Target Remediated Output*: Clean execution without exceptions.

3. **Run Full Regression Suite**:
   ```bash
   pytest -v tests/test_human_materials.py tests/test_wardrobe.py tests/test_fastmcp_human_tools.py
   ```
