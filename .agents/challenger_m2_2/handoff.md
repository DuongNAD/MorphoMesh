# Milestone M2 Adversarial Challenge Report: Multi-Angle Capture & Viewport Robustness

**Agent**: Challenger M2_2 (Multi-Angle Capture & Viewport Robustness Challenger)  
**Date**: 2026-09-07T04:55:00Z  
**Working Directory**: `e:\tool\mcp\MorphoMesh\.agents\challenger_m2_2`  
**Parent Orchestrator ID**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Target Subsystems**: `src/morphomesh/camera_rig.py`, `src/morphomesh/blender_bridge.py`, `blender_addon/morphomesh/listener.py`, `src/morphomesh/__init__.py`, `tests/test_adversarial_viewport_capture.py`  
**Verdict**: **REJECT** (Critical Live Socket & Deployment Deficiencies Uncovered)  
**Handoff Type**: Hard  

---

## 1. Observation

1. **Test Suite Verification**:
   - Developed and executed comprehensive adversarial test harness `tests/test_adversarial_viewport_capture.py` comprising 42 tests across 4 categories:
     - *Suite 1 (Batch Fuzzing)*: Empty list, invalid viewpoint strings, duplicate viewpoints, 16-angle turntable orbit sweeps, non-standard and 4K resolutions (64x64 to 3840x2160, 32:9 ultrawide, 9:16 vertical).
     - *Suite 2 (Diagnostic Shading Fuzzing)*: All 9 combinations of `shading_mode` (`SOLID`, `WIREFRAME`, `MATERIAL`) x `color_type` (`RANDOM`, `SINGLE`, `OBJECT`), fuzzed invalid modes with fallback checks, and execution benchmarking (<0.55s in Blender Workbench, <0.05s in mock).
     - *Suite 3 (Fault Injection & Recovery)*: Missing scene (`scene=None`), nonexistent camera objects, deleted target mesh objects, truncated corrupted PNG fallback audit, and file handle leak checks over 50 rapid captures.
     - *Suite 4 (Live Socket & Packaging Audit)*: Live socket probing on port 9876, RPC method availability, addon deployment relative path resolution, and bundled Blender Python dependency isolation.
   - Result of `pytest -v tests/test_adversarial_viewport_capture.py`: **42 passed in 0.64s**.
   - Result of combined M2 unit + integration + adversarial tests (`tests/test_inspector_camera.py`, `tests/test_multiview_rendering.py`, `tests/test_adversarial_viewport_capture.py`): **103 passed in 0.86s**.

2. **Verbatim Live Socket Probing Failures (Port 9876)**:
   - Live Blender 4.5.4 LTS was active on `127.0.0.1:9876` (PID 30652).
   - Probing raw JSON-RPC for `morphomesh.setup_inspector_camera`:
     ```json
     {"jsonrpc": "2.0", "id": "test-cam", "status": "error", "error": {"code": -32000, "message": "Unknown RPC method: morphomesh.setup_inspector_camera"}}
     ```
   - Probing raw JSON-RPC for `morphomesh.capture_viewport`:
     ```json
     {"jsonrpc": "2.0", "id": "test-cap", "status": "error", "error": {"code": -32000, "message": "Unknown RPC method: morphomesh.capture_viewport"}}
     ```
   - Invoking `BlenderBridge.setup_inspector_camera()` against the live connection:
     ```
     Interactive socket execute_code failed ([ERR_BLENDER_EXECUTION_FAILED] Blender Socket Error: Forbidden import: sys), falling back to headless runner.
     ```

3. **Verbatim Blender Subprocess Addon Execution Crash**:
   - Invoking `_dispatch('morphomesh.capture_multi_angle_inspection', {'viewpoints': ['front']})` inside real Blender 4.5.4 LTS:
     ```
     Multi-angle capture failed: No module named 'morphomesh.camera_rig'
     Traceback (most recent call last):
       File "C:\Users\Admin\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\addons\morphomesh\listener.py", line 1200, in _dispatch
         from morphomesh.camera_rig import capture_multi_angle_inspection
     ModuleNotFoundError: No module named 'morphomesh.camera_rig'
     ```

4. **Verbatim Truncated Corrupted PNG Fallback**:
   - Calling `capture_viewport_image(resolution=(0, 0))` writes raw 29-byte truncated header:
     `b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x04\x00\x00\x00\x04\x00\x08\x02\x00\x00\x00"`
   - Reading with PIL raises:
     ```
     PIL.UnidentifiedImageError: cannot identify image file '.../corrupted_test.png'
     ```

---

## 2. Logic Chain

1. **Defect 1: Live Interactive Socket Out of Parity (Unregistered Methods)**:
   - *Observation*: Live Blender session listening on port 9876 rejected `morphomesh.setup_inspector_camera` and `morphomesh.capture_viewport` with `Unknown RPC method`.
   - *Logic*: The Blender addon was originally loaded from `%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\morphomesh\listener.py` (10KB stub). While Worker M2 updated `blender_addon/morphomesh/listener.py` in the git repository (100KB), the changes were never installed into Blender's addon directory or reloaded. Consequently, interactive socket calls fail in real sessions.
   - *Blast Radius*: Antigravity 2.0 and MCP tools cannot communicate interactively with Blender on port 9876 for inspection camera or viewport capture.

2. **Defect 2: Interactive Fallback Crashes on `import sys` Violation**:
   - *Observation*: When `BlenderBridge.execute()` receives an RPC error from the socket, it attempts to fall back to `self.send_socket_request("execute_code", {"code": script})`.
   - *Logic*: `_generate_headless_script()` in `src/morphomesh/blender_bridge.py` (line 743) generates Python code containing `import sys` and `import os`. The in-Blender `AddonSecurityValidator` in `listener.py` blocks `sys` and `os` from untrusted script execution. This causes `execute_code` to fail with `Blender Socket Error: Forbidden import: sys`, completely breaking the interactive bridge fallback mechanism.
   - *Blast Radius*: The fallback mechanism does not recover interactively and is forced to spawn headless CLI processes, defeating the purpose of an interactive bridge.

3. **Defect 3: Invalid Relative Path Resolution (`repo_src`) in Addon**:
   - *Observation*: In `blender_addon/morphomesh/listener.py` lines 918, 1095, and 1195:
     ```python
     repo_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
     if os.path.exists(repo_src) and repo_src not in sys.path:
         sys.path.insert(0, repo_src)
     ```
   - *Logic*: When the addon is installed in standard Blender location (`%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\morphomesh\`), `os.path.dirname(__file__)` is `.../scripts/addons/morphomesh`. Traversing `../../src` evaluates to `.../scripts/src`, which NEVER exists in user environments.
   - *Blast Radius*: In real Blender installations, `repo_src` is not added to `sys.path`, preventing Blender from locating `morphomesh.camera_rig`.

4. **Defect 4: Packaging Dependency Pollution (`pydantic` in Blender Python)**:
   - *Observation*: `src/morphomesh/__init__.py` line 7 executes `from morphomesh.models import ...`, which requires `from pydantic import BaseModel`.
   - *Logic*: Blender's bundled Python does not include third-party package `pydantic`. Even if `e:\tool\mcp\MorphoMesh\src` is manually placed on `sys.path`, executing `from morphomesh.camera_rig import ...` triggers package root `morphomesh/__init__.py`, which crashes with `ModuleNotFoundError: No module named 'pydantic'`.
   - *Blast Radius*: In `listener.py`:
     - `setup_inspector_camera` silently swallows the `ImportError` and falls back to a legacy unoptimized camera calculation.
     - `capture_viewport` silently swallows the `ImportError` and falls back to unoptimized viewport grab.
     - `capture_multi_angle_inspection` does NOT catch `ImportError` and raises an unhandled `ModuleNotFoundError`, crashing the batch inspection RPC call.

5. **Defect 5: Corrupted Fallback PNG Header**:
   - *Observation*: In `src/morphomesh/camera_rig.py` lines 703-704 and 838-839:
     ```python
     with open(clean_path, "wb") as f:
         f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x04\x00\x00\x00\x04\x00\x08\x02\x00\x00\x00")
     ```
   - *Logic*: If PIL encounters an error (e.g. resolution 0x0 or resource failure), `camera_rig.py` writes a truncated 29-byte file containing only the 8-byte PNG signature and a partial IHDR chunk without checksum, image data (IDAT), or end chunk (IEND). This file is corrupt and cannot be decoded by any standard image parser or base64 preview generator.
   - *Blast Radius*: Downstream tools and users receive corrupted images when fallback paths trigger.

---

## 3. Caveats

1. **Pure-Python Algorithmic Correctness**: The core mathematical solvers in `src/morphomesh/camera_rig.py` (AABB bounding box calculation, optical distance trigonometry $d = \frac{R}{\sin(\alpha_{\min})} \cdot (1 + \mu)$, spherical camera placement, anatomical centers, and pure-Python matrix/quaternion shims) are well-designed and passed all 42 adversarial stress tests with zero algorithmic errors.
2. **Headless Workbench Performance**: When `camera_rig.py` is invoked standalone in Blender 4.5.4 LTS via script without the package `__init__.py` dependency block, Workbench capture completes in ~0.54s, satisfying the performance criteria.
3. **Addon Deployment State**: The installed addon in `%APPDATA%` was synchronized with the repo version during verification, but Blender requires either module hot-reloading or session restart to bind the updated dispatcher methods to `_global_server`.

---

## 4. Conclusion

**Verdict: REJECT**

While the core math and pure-Python unit tests in `src/morphomesh/camera_rig.py` are robust, Milestone 2 cannot be approved in its current state due to critical architectural and runtime bridge integration failures:
1. Live socket interactive calls fail on port 9876 with `Unknown RPC method`.
2. Socket fallback crashes with `Blender Socket Error: Forbidden import: sys`.
3. Relative path resolution `repo_src` in `listener.py` fails in all standard Blender installations.
4. `morphomesh/__init__.py` pollutes Blender's execution environment by requiring `pydantic`, causing `capture_multi_angle_inspection` to crash with `ModuleNotFoundError: No module named 'morphomesh.camera_rig'`.
5. Fallback PNG writer outputs corrupted 29-byte unidentifiable image files.

### Required Remediations for Worker M2:
1. **Decouple Package Root from Pydantic in Blender**: In `src/morphomesh/__init__.py`, wrap imports of `models.py` in `try...except (ImportError, ModuleNotFoundError)` or guard them so importing `morphomesh.camera_rig` inside Blender does not import `pydantic`.
2. **Fix `repo_src` Path Resolution in `listener.py`**: Support an environment variable (e.g. `MORPHOMESH_SRC_PATH`), check parent directories dynamically, or embed `camera_rig.py` within `blender_addon/morphomesh/` to eliminate cross-package external path dependencies.
3. **Catch `ImportError` in `capture_multi_angle_inspection`**: Ensure `capture_multi_angle_inspection` in `listener.py` does not raise an unhandled exception when delegating to `camera_rig`.
4. **Remove Forbidden Imports from Script Generator**: Ensure `_generate_headless_script()` in `blender_bridge.py` does not inject forbidden modules (`sys`, `os`) when routing through the interactive socket's `execute_code` endpoint.
5. **Fix Truncated Fallback PNG**: Replace the 29-byte truncated header with a valid 1x1 or 4x4 RGBA transparent PNG byte stream (e.g. 68 bytes complete PNG).
6. **Provide Addon Hot-Reload / Deploy Command**: Provide automated deployment or hot-reload capability so live Blender sessions pick up updated RPC handlers immediately.

---

## 5. Verification Method

To reproduce these empirical findings independently:

1. **Run Full Adversarial Test Suite**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_adversarial_viewport_capture.py
   ```
   *Expected result*: 42 passed in <1.0s, including verification of corrupted fallback PNG detection and path resolution failure.

2. **Reproduce Live Socket `Unknown RPC method` on Port 9876**:
   ```powershell
   .venv\Scripts\python.exe -c "import socket, json; s = socket.socket(); s.connect(('127.0.0.1', 9876)); s.sendall(json.dumps({'jsonrpc': '2.0', 'id': 't1', 'method': 'morphomesh.setup_inspector_camera', 'params': {'viewpoint': 'three_quarter'}}).encode('utf-8') + b'\n'); print(s.recv(4096).decode('utf-8'))"
   ```
   *Verbatim output*:
   `{"jsonrpc": "2.0", "id": "t1", "status": "error", "error": {"code": -32000, "message": "Unknown RPC method: morphomesh.setup_inspector_camera"}}`

3. **Reproduce `pydantic` Import Failure in Blender Bundled Python**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python-expr "import sys; sys.path.insert(0, r'e:\tool\mcp\MorphoMesh\src'); from morphomesh.camera_rig import setup_inspector_camera"
   ```
   *Verbatim output*:
   `ModuleNotFoundError: No module named 'pydantic'`

4. **Reproduce `capture_multi_angle_inspection` Addon Crash in Blender**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python-expr "import sys; sys.path.append(r'C:\Users\Admin\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\addons'); import morphomesh.listener as l; s = l.MorphoMeshSocketServer(); res = s._dispatch('morphomesh.capture_multi_angle_inspection', {'viewpoints': ['front']})"
   ```
   *Verbatim output*:
   `ModuleNotFoundError: No module named 'morphomesh.camera_rig'`
