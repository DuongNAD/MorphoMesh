# Handoff Report — Milestone 2 Review: 52 ARKit FACS Blendshapes & Blender Bridge Auto-Rigging

**Agent**: `reviewer_human_m2_2`  
**Parent**: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Date**: 2026-09-07T02:00:00+07:00  
**Role**: Reviewer & Adversarial Critic  
**Verdict**: **REQUEST_CHANGES**  

---

## 1. Observation

### 1.1 Test Suite & Static Lint Results
- **Human Rigging Test Suite**:
  - Command: `py -3.11 -m pytest tests/test_human_rigging.py -v`
  - Result: `20 passed in 0.32s` (100% pass rate).
- **FastMCP Human Tools Test Suite**:
  - Command: `py -3.11 -m pytest tests/test_fastmcp_human_tools.py -v`
  - Result: `17 passed in 5.52s` (100% pass rate).
- **Comprehensive Human Pipeline Suite**:
  - Command: `py -3.11 -m pytest tests/test_human_generator.py tests/test_adversarial_human_generator.py tests/test_human_rigging.py tests/test_fastmcp_human_tools.py tests/test_adversarial_fastmcp_bridge_human.py -v`
  - Result: `151 passed in 16.24s` (100% pass rate).
- **Syntax & Style Linter**:
  - Command: `py -3.11 -m flake8 --select=F src/morphomesh/human_rigging.py tests/test_human_rigging.py`
  - Result: Exit code 0, 0 errors.

### 1.2 52 Apple ARKit Standard Blendshapes Analysis
- File: `src/morphomesh/human_rigging.py`:
  - Lines 155–177: `ARKIT_52_BLENDSHAPES` defines all 52 standard Apple ARKit blendshapes in canonical camelCase naming:
    - Eye (14): `eyeBlinkLeft`, `eyeLookDownLeft`, `eyeLookInLeft`, `eyeLookOutLeft`, `eyeLookUpLeft`, `eyeSquintLeft`, `eyeWideLeft`, `eyeBlinkRight`, `eyeLookDownRight`, `eyeLookInRight`, `eyeLookOutRight`, `eyeLookUpRight`, `eyeSquintRight`, `eyeWideRight`.
    - Jaw (4): `jawForward`, `jawLeft`, `jawRight`, `jawOpen`.
    - Mouth (23): `mouthClose`, `mouthFunnel`, `mouthPucker`, `mouthLeft`, `mouthRight`, `mouthSmileLeft`, `mouthSmileRight`, `mouthFrownLeft`, `mouthFrownRight`, `mouthDimpleLeft`, `mouthDimpleRight`, `mouthStretchLeft`, `mouthStretchRight`, `mouthRollLower`, `mouthRollUpper`, `mouthShrugLower`, `mouthShrugUpper`, `mouthPressLeft`, `mouthPressRight`, `mouthLowerDownLeft`, `mouthLowerDownRight`, `mouthUpperUpLeft`, `mouthUpperUpRight`.
    - Brows (5): `browDownLeft`, `browDownRight`, `browInnerUp`, `browOuterUpLeft`, `browOuterUpRight`.
    - Cheeks (3): `cheekPuff`, `cheekSquintLeft`, `cheekSquintRight`.
    - Nose (2): `noseSneerLeft`, `noseSneerRight`.
    - Tongue (1): `tongueOut`.
  - Lines 894–1103: `generate_arkit_52_blendshapes(mesh, landmarks, scale)` implements 52 distinct conditional branches computing sparse 3D displacement vectors `(dx, dy, dz)` targeting anatomical vertex groups (`v_eyes_l`, `v_eyes_r`, `v_mouth`, `v_lips`, `v_eyebrows`, `v_tongue`, `v_face`).
  - Displacements follow authentic FACS vectors (e.g. `eyeBlinkLeft` moves $-Z$ and $+Y$, `jawOpen` moves $-Z$ and $-Y$, `mouthSmileLeft` moves $+X$ and $+Z$, `browDownLeft` moves $-X$ and $-Z$, `tongueOut` moves $+Y$).

### 1.3 Standalone Blender Rigging Script Execution in Real Blender 4.5.4 LTS
- Live environment probe: Blender 4.5.4 LTS is installed at `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`.
- Standalone execution test: Evaluated `get_rigging_script("Test_Rig_Mesh")` inside real Blender 4.5.4 LTS in headless mode:
  - AST Parsing: Verified syntactically valid Python AST (`ast.parse(script)` succeeds without error).
  - Blender Execution output:
    ```
    Verified DEF bones: 163 (64 body + 99 facial)
    Verified Shape keys: 52 ARKit keys
    REAL BLENDER 4.5 TEST: DEF bones count = 163
    REAL BLENDER 4.5 TEST: ALL ASSERTIONS PASSED!
    Return code: 0
    ```
  - Dual Quaternion Skinning verified: `obj.modifiers['Armature'].use_deform_preserve_volume == True`.
  - Bone counts verified: 163 total DEF bones (64 body DEF bones + 99 facial DEF bones).

### 1.4 Interactive Socket RPC Empirical Failure
- Live environment probe: Blender PID 30652 was actively listening on `127.0.0.1:9876`.
  - Probe: `bridge.send_socket_request('morphomesh.ping', {})` returned `{'status': 'pong', 'blender_version': '4.5.4', 'mode': 'interactive'}`.
- Direct invocation of `auto_rig_human`:
  - Command: `bridge.auto_rig_human(mesh_object_name='Human_Base_Mesh')`
  - Direct socket response:
    ```
    Raw response: {"jsonrpc": "2.0", "id": "req-xxx", "status": "error", "error": {"code": -32000, "message": "Unknown RPC method: morphomesh.auto_rig_human"}}
    ```
  - Fallback socket response (`execute_code` with generated script):
    ```
    Raw response: {"jsonrpc": "2.0", "id": "req-yyy", "status": "error", "error": {"code": -32000, "message": "Forbidden import: sys"}}
    ```
  - Bridge console output:
    ```
    [WARNING] Interactive socket execute_code failed ([ERR_BLENDER_EXECUTION_FAILED] Blender Socket Error: Unknown error), falling back to headless runner.
    ```
  - The bridge fell back to launching an independent CLI subprocess (`blender.exe --background ...`), entirely failing to execute over the interactive socket bridge on the artist's active Blender scene.

### 1.5 Blender Scene Shape Key Vertex Delta Omission
- File: `src/morphomesh/human_rigging.py`:
  - Lines 1358–1379:
    ```python
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)
    for k_name in arkit_52:
        if k_name not in obj.data.shape_keys.key_blocks:
            obj.shape_key_add(name=k_name, from_mix=False)
    ```
  - In Blender, `obj.shape_key_add(from_mix=False)` initializes all vertex coordinates in the new key block to match the Basis key block.
  - In `get_rigging_script` and `_generate_headless_script`, the script stops at adding the key block name. It does **not** iterate over vertices to assign `kb.data[vi].co += (dx, dy, dz)`.
  - In the resulting `.blend` / `.fbx` asset, adjusting any of the 52 shape keys from 0.0 to 1.0 produces 0.0m vertex displacement in 3D viewport.

---

## 2. Logic Chain

1. **Test Verification**:
   - The test suite (`pytest tests/test_human_rigging.py` and `tests/test_fastmcp_human_tools.py`) passes 100% (37/37 tests pass; 151/151 across the entire digital human suite).
   - Python code logic for Rigify 163 DEF bones metarig generation, landmark snapping, pre-bend enforcement, and anti-pinch skin weights is mathematically complete, non-trivial, and sound.

2. **Blendshapes Authenticity in Python vs Blender**:
   - `generate_arkit_52_blendshapes` calculates genuine 3D sparse displacement deltas for all 52 shape keys on `MeshGeometry` in memory.
   - However, in `get_rigging_script` (and the headless script generator in `blender_bridge.py`), while the 52 shape key blocks are allocated in Blender via `obj.shape_key_add(name=k_name)`, the vertex delta coordinates are not baked into `key_block.data[vi].co`.
   - Consequently, in Blender, all 52 shape keys have zero displacement relative to Basis. While the shape key containers exist for mocap channel binding, they act as unpopulated facades in 3D space unless the computed vertex offsets are injected into the Blender mesh key blocks.

3. **Socket RPC Failure on Port 9876**:
   - `ORIGINAL_REQUEST.md` (§Acceptance Criteria) and `PROJECT.md` (§F03) mandate:
     `Module human_rigging.py tự động sinh và nắn chỉnh armature Rigify Human 163 xương DEF trực tiếp trên Blender qua socket bridge 127.0.0.1:9876 mà không gặp bất kỳ lỗi thực thi nào.`
   - Our empirical test against the live running Blender socket server revealed that `send_socket_request("morphomesh.auto_rig_human")` is rejected with `Unknown RPC method: morphomesh.auto_rig_human` because `blender_addon/morphomesh/listener.py` only implements `ping`, `get_scene_status`, and `execute_custom_script`.
   - The bridge's secondary interactive socket fallback (`execute_code`) is rejected with `Forbidden import: sys` because `_generate_headless_script` imports `sys`, `os`, `tempfile`, and `uuid`, which violate `AddonSecurityValidator`.
   - The operation only succeeds because it abandons the interactive socket and launches a detached background CLI process. When an interactive Blender session is open, this fails to modify the user's active session.

4. **Error Masking in Socket Bridge**:
   - In `BlenderBridge.send_socket_request` (lines 345–355 of `src/morphomesh/blender_bridge.py`), `if response.get("status") == "error":` is checked before `if "error" in response:`. Because `listener.py` formats errors as `{"status": "error", "error": {"message": ...}}` without a top-level `"message"` key, the bridge throws `Blender Socket Error: Unknown error`, masking the real error from the server (`Forbidden import: sys` / `Unknown RPC method`).

---

## 3. Review Findings & Challenges

### [Critical / Integrity Concern] Finding 1: Blender Shape Keys Lack 3D Vertex Displacements in Standalone Script
- **What**: `get_rigging_script` creates 52 shape key blocks via `obj.shape_key_add(name=k_name, from_mix=False)` but does not assign the computed 3D vertex displacements to `key_block.data[vi].co`.
- **Where**: `src/morphomesh/human_rigging.py`, lines 1358–1379; `src/morphomesh/blender_bridge.py`, lines 1775–1776.
- **Why**: In Blender 4.5+, shape keys added with `from_mix=False` copy the Basis vertex coordinates. Without applying vertex offsets, all 52 shape keys have 0 displacement in Blender, meaning facial expressions cannot deform the 3D model.
- **Suggestion**: In `get_rigging_script` and `_generate_headless_script`, iterate over the facial vertex groups (`eyes_left`, `eyes_right`, `mouth`, `lips`, `eyebrows`, `tongue`, `face`) or serialize the displacement dictionary from `generate_arkit_52_blendshapes` so the script executes:
  ```python
  for k_name, deltas in shape_deltas.items():
      kb = obj.data.shape_keys.key_blocks.get(k_name)
      if kb:
          for vi, (dx, dy, dz) in deltas.items():
              if vi < len(kb.data):
                  kb.data[vi].co.x += dx
                  kb.data[vi].co.y += dy
                  kb.data[vi].co.z += dz
  ```

### [Major] Finding 2: Socket RPC Dispatch Fails Over Interactive Port 9876
- **What**: Interactive socket dispatch for `auto_rig_human` fails both direct RPC (`Unknown RPC method: morphomesh.auto_rig_human`) and fallback code execution (`Forbidden import: sys`), forcing a fallback to background headless CLI.
- **Where**: `blender_addon/morphomesh/listener.py`, lines 215–291; `src/morphomesh/blender_bridge.py`, lines 480–498 & 2273.
- **Why**: Violates the acceptance criterion that rigging must execute cleanly over socket bridge 127.0.0.1:9876 without execution errors. It prevents live interactive rigging in an artist's open Blender session.
- **Suggestion**:
  1. Add `morphomesh.auto_rig_human` (and related human methods) to `listener.py`'s `_dispatch` method.
  2. For `execute_code`, ensure generated rigging code conforms to `AddonSecurityValidator` by eliminating unneeded imports (`sys`, `os`, `tempfile`) or executing the rigging operators natively.

### [Minor] Finding 3: JSON-RPC Error Message Masking in `send_socket_request`
- **What**: `BlenderBridge.send_socket_request` masks the server error message with `'Unknown error'`.
- **Where**: `src/morphomesh/blender_bridge.py`, lines 345–355.
- **Why**: When `listener.py` responds with `{"status": "error", "error": {"code": -32000, "message": "..."}}`, line 347 looks for `response.get("message", "Unknown error")` at the root, completely ignoring `response["error"]["message"]`.
- **Suggestion**: Update line 347 to:
  ```python
  err_msg = response.get("message") or response.get("error", {}).get("message", "Unknown error")
  ```

---

## 4. Caveats

- In an offline environment where Blender is not running or Blender binary is not installed, the bridge fallback gracefully creates FBX mock assets and returns compliant data structures adhering to `HumanRigResult`.
- The anti-pinch skinning and metarig 163 DEF bones implementation in `src/morphomesh/human_rigging.py` is exceptionally well-engineered, with robust mathematics (olecranon cosine gradient, patella locking $\ge 90\%$, axilla clamping $\ge 70\%$, finger cylinder isolation, and strict weight sum=1.0).
- The requested changes focus on bridging the in-memory Python calculations into the Blender runtime (socket listener dispatch and shape key coordinate baking).

---

## 5. Conclusion

**Verdict: REQUEST_CHANGES**

Milestone 2 has accomplished great algorithmic foundations in `src/morphomesh/human_rigging.py` (163 DEF bones metarig, 52 ARKit FACS displacement vectors, pre-bends, and anti-pinch skin weights). However, changes are required before Milestone 2 can be approved:
1. **Interactive Socket RPC**: Update `blender_addon/morphomesh/listener.py` to register and handle `morphomesh.auto_rig_human` so that socket RPC over port 9876 succeeds cleanly without throwing errors or triggering CLI fallbacks.
2. **Blender Shape Key Coordinate Baking**: Update `get_rigging_script` (and headless script generation) to bake the 3D vertex displacement coordinates into `key_block.data[vi].co` so that shape keys actually deform the facial mesh inside Blender.
3. **Socket Error Parsing**: Fix `BlenderBridge.send_socket_request` to parse nested `response["error"]["message"]` without falling back to `'Unknown error'`.

---

## 6. Verification Method

To independently verify these findings and check subsequent fixes:

```powershell
# 1. Run unit test suites
py -3.11 -m pytest tests/test_human_rigging.py tests/test_fastmcp_human_tools.py -v

# 2. Test live Blender socket RPC when Blender is running on port 9876
$env:PYTHONPATH='src'
py -3.11 -c "
from morphomesh.blender_bridge import BlenderBridge
bridge = BlenderBridge()
# Direct socket request must not raise BlenderExecutionError
res = bridge.send_socket_request('morphomesh.auto_rig_human', {'mesh_object_name': 'Human_Base_Mesh'})
print('Socket RPC status:', res.get('status'))
"

# 3. Test shape key vertex displacements in Blender
py -3.11 -c "
import subprocess, tempfile
from morphomesh.human_generator import get_human_generation_script, HumanAnatomyConfig
from morphomesh.human_rigging import get_rigging_script

script = get_human_generation_script('Test_Mesh', HumanAnatomyConfig()) + '\n\n' + get_rigging_script('Test_Mesh') + '''
obj = bpy.data.objects['Test_Mesh']
kb = obj.data.shape_keys.key_blocks['jawOpen']
basis = obj.data.shape_keys.key_blocks['Basis']
deltas = [abs(kb.data[i].co.z - basis.data[i].co.z) for i in range(len(kb.data))]
max_delta = max(deltas)
print(f'Max jawOpen Z displacement in Blender: {max_delta:.4f}m')
assert max_delta > 0.005, 'Shape key in Blender has 0 displacement!'
'''
with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
    f.write(script)
    p = f.name
subprocess.run(['C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe', '--background', '--factory-startup', '--python', p], check=True)
"

# 4. Invalidation Condition:
# The verdict remains REQUEST_CHANGES until socket RPC executes cleanly without errors on port 9876 and max_delta > 0.005m for facial shape keys in Blender.
```
