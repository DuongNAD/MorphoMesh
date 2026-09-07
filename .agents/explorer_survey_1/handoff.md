# Handoff Report: Codebase & Architecture Exploration for MorphoMesh Inspection, Auto-Critic QA, and Socket Parity
**Agent**: Explorer 1 (`explorer_survey_1`)  
**Target Milestone**: 2026-09-07T03:34:32Z (R1-R4 Architecture Survey)  
**Working Directory**: `e:\tool\mcp\MorphoMesh\.agents\explorer_survey_1`  
**Parent Conversation ID**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Handoff Type**: Hard (Investigation Complete)  

---

## 1. Observation

### 1.1 Project Structure & Execution Environment
- **Project Root**: `e:\tool\mcp\MorphoMesh`
- **Configuration & Dependencies** (`pyproject.toml` lines 1-57):
  - Build backend: `setuptools.build_meta`, requires Python `>=3.11`.
  - Core dependencies: `mcp>=1.2.0,<2.0.0`, `pydantic>=2.0.0`, `pillow>=10.0.0`, `numpy>=1.24.0`, `pytest>=7.0.0`, `pytest-asyncio>=0.21.0`.
  - Scripts exposed: `morphomesh = morphomesh.main:main`, `morphomesh-server = morphomesh.main:main`.
- **Python Runtime**:
  - Virtual environment verified at `e:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe` (Python 3.11.9).
  - Pytest executable verified at `e:\tool\mcp\MorphoMesh\.venv\Scripts\pytest.exe` (pytest-9.1.1).
- **Blender 4.5 LTS Runtime**:
  - Binary verified at `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`.
  - Version: `Blender 4.5.4 LTS` (build date 2025-10-28, branch `blender-v4.5-release`, hash `b3efe983cc58`).
  - Active interactive Blender process (PID 30652) is currently running and listening on `127.0.0.1:9876`.
  - Live probe test result: `BlenderBridge().ping()` returned `{'status': 'pong', 'blender_version': '4.5.4', 'mode': 'interactive'}`.
  - Active scene `Scene` contains 43 objects including `Yu_Nian_An_Body`, eye meshes, 6 hair strata, dress components, props (strings and 10 butterflies), and Rigify armature.

### 1.2 MCP Server Architecture (`src/morphomesh/server.py`)
- **FastMCP Server Initialization** (lines 64-85):
  - `FastMCP(name="MorphoMeshServer", host="127.0.0.1", port=8765)`
  - Bridge instance: `BlenderBridge(host="127.0.0.1", port=9876)`
  - Adapter instance: `inference_adapter = get_inference_adapter(mode=_backend_mode)`
- **Exposed MCP Tools** (14 tools total):
  - **7 Canonical Creature Tools**:
    1. `morphomesh_generate_concept` (line 91)
    2. `morphomesh_create_3d_asset` (line 148)
    3. `morphomesh_optimize_topology` (line 206)
    4. `morphomesh_auto_rig` (line 297)
    5. `morphomesh_blender_execute` (line 427)
    6. `morphomesh_get_scene_status` (line 471)
    7. `morphomesh_render_preview` (line 510)
  - **7 Digital Human Tools**:
    8. `morphomesh_create_human_asset` (line 593)
    9. `morphomesh_auto_rig_human` (line 701)
    10. `morphomesh_setup_human_materials` (line 764)
    11. `morphomesh_groom_human` (line 827)
    12. `morphomesh_dress_human` (line 898)
    13. `morphomesh_assemble_master_character` (line 969)
    14. `morphomesh_export_production_character` (line 1028)
- **Tool Listing & Compatibility Filter** (lines 1103-1135):
  - Wrapped `_filtered_list_tools` checks `os.environ.get("MORPHOMESH_INCLUDE_HUMAN_TOOLS")`.
  - If unset, returns exactly the 7 creature tools to guarantee legacy test suite compliance (`tests/test_tools_schema.py` asserts `len(tools) == 7`).
  - If set to `"1"` / `"true"`, returns the expanded toolset.

### 1.3 Blender Bridge Client (`src/morphomesh/blender_bridge.py`)
- **Dual-Mode IPC Mechanism**:
  - `is_interactive_connected()` (line 316): TCP socket probe to `127.0.0.1:9876`.
  - `send_socket_request()` (lines 324-393): JSON-RPC 2.0 framing over TCP socket.
  - `run_headless_script()` (lines 395-483): Subprocess CLI execution (`blender.exe --background --factory-startup --python <temp_file>`) parsing sentinel tokens (`MORPHOMESH_START_JSON` ... `MORPHOMESH_END_JSON`).
  - `execute()` (lines 488-516): Tries direct socket RPC first; on failure tries socket `execute_code`; on socket absence falls back to `_dispatch_headless()`.
- **AST Security Validator (`BpyCodeValidator`)** (lines 106-265):
  - Strictly whitelist-based. Allowed modules: `bpy`, `math`, `mathutils`, `bmesh`, `numpy`, `random`, `json`, `collections`, `itertools`, `time`.
  - Blocks `os`, `sys`, `subprocess`, `open`, `eval`, `exec`, `__import__`, `__subclasses__`.
- **Existing Camera Auto-Framing (`ensure_auto_camera`)** (lines 718-756):
  - Finds all mesh objects in scene, calculates axis-aligned bounding box min/max corners.
  - Bounding center: `(min + max) / 2.0`, radius: `max(max - min) / 2.0`.
  - Distance hardcoded: `dist = radius * 3.5`.
  - Location fixed at three-quarter perspective: `center + (dist * 0.7, -dist * 0.7, dist * 0.5)`.
  - **Limitations**:
    * Does NOT support directional viewpoints (`front`, `side`, `back`, `turntable_4views`).
    * Does NOT support anatomical close-ups (`head`, `hands`).
    * Does NOT compute bounding box of a specific selected character or active hierarchy.
    * If `scene.camera` already exists, it aborts without updating framing or viewpoint!

### 1.4 Interactive Blender Socket Addon (`blender_addon/morphomesh/listener.py`)
- **Main-Thread Synchronization**:
  - Runs a background listener thread accepting TCP connections, placing commands into `queue.Queue`.
  - Registers persistent timer via `bpy.app.timers.register(self._drain_queue, persistent=True)` running every 20ms on Blender's main thread to safely execute bpy operations.
- **Dispatch Implementation Discrepancy (Parity Gap)**:
  - Methods supported in `_dispatch` (lines 216-557):
    `morphomesh.ping`, `morphomesh.get_scene_status`, `morphomesh.execute_custom_script`, `morphomesh.auto_rig_human`, `morphomesh.setup_human_materials`, `morphomesh.groom_human`, `morphomesh.dress_human`, `morphomesh.assemble_master_character`.
  - **Missing Handlers in `listener.py`**:
    * `morphomesh.render_preview`: Missing! Socket call fails with `ValueError: Unknown RPC method: morphomesh.render_preview`.
    * `morphomesh.capture_viewport`: Missing!
    * `morphomesh.create_human_asset`: Missing!
    * `morphomesh.optimize_topology`: Missing!
    * `morphomesh.create_armature`: Missing!
    * Any camera rig or visual inspection/critique methods: Missing!
  - **Result**: Calling `render_preview()` through `BlenderBridge.execute()` in interactive mode causes an exception on `send_socket_request()`, falls back to `execute_code`, where `listener.py` executes code but does not return image metadata in `res`, leading to malformed response handling.

### 1.5 Viewport Capture & Rendering Mechanics (Empirical Benchmark)
- **Interactive Socket Mode Test**:
  - Executed `bpy.ops.render.opengl(write_still=True)` on live session (PID 30652).
  - Execution time: **0.176 seconds**.
  - Output: Valid 766 KB PNG file captured directly from the 3D Viewport framebuffer.
- **Headless CLI Mode Test**:
  - Executed `blender.exe --background --python <script>` with `bpy.ops.render.opengl(write_still=True)`.
  - Result: Fails with `Error: Cannot use OpenGL render in background mode (no opengl context)`.
  - Executed `scene.render.engine = 'BLENDER_WORKBENCH'` with `bpy.ops.render.render(write_still=True)`.
  - Result: **Success in 0.64 seconds**, saving valid 1.7 MB PNG image.

### 1.6 Visual Quality Critique Foundations in Test Suites
- In `tests/inspect_penetration.py` and `tests/test_challenger_m4_deep_audit.py`:
  - **BVH Penetration Detection**:
    ```python
    bm_body = bmesh.new()
    bm_body.from_mesh(body_obj.data)
    bm_body.transform(body_obj.matrix_world)
    body_bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)
    loc, normal, idx, dist = body_bvh.find_nearest(v)
    dot = (v - loc).dot(normal)  # dot < 0 means penetrating interior!
    ```
  - **BVH Face Overlap Detection**:
    ```python
    overlaps = body_bvh.overlap(garment_bvh)  # List of intersecting face pairs
    ```
  - **Anthropometric Proportion Checks**:
    Checks height ($1.65\text{m}$), head ratio ($7.41\pm0.15$), waist-to-hip ratio ($0.58/0.86 \approx 0.674$), and shoulder width.
  - **Rig & Skinning Pinch Checks**:
    Evaluates deformed mesh displacement during joint rotation (`pose.bones[...].rotation_euler = ...`) and detects orphaned vertices with zero bone deform weights.
  - **Grooming Strata Checks**:
    Evaluates hair geometry vertices via `evaluated_get(depsgraph).to_mesh()`, asserts strand count $\ge 10,000$, and verifies absence of zero-vertex hair objects.

---

## 2. Logic Chain

### 2.1 R1: Multi-Angle Inspector Camera & Fast Viewport Capture
1. **Camera Rig Positioning Mathematics**:
   - Given target object(s) or character root collection:
     - Accumulate world coordinates of all bounding box corners across constituent meshes:
       $v_{\text{world}} = M_{\text{world}} \cdot v_{\text{local}}$
     - Find bounding box extents $[x_{\min}, x_{\max}]$, $[y_{\min}, y_{\max}]$, $[z_{\min}, z_{\max}]$.
     - Anatomical center: $C = \left(\frac{x_{\min} + x_{\max}}{2}, \frac{y_{\min} + y_{\max}}{2}, \frac{z_{\min} + z_{\max}}{2}\right)$.
     - Bounding radius: $R = \frac{\max(x_{\max}-x_{\min}, y_{\max}-y_{\min}, z_{\max}-z_{\min})}{2}$.
   - Camera Distance & FOV:
     - For focal length $f = 50\text{mm}$ (sensor width $w = 36\text{mm}$), horizontal FOV is $2 \arctan(w / (2f)) \approx 39.6^\circ$.
     - Framing distance with $25\%$ safety margin: $d = \frac{R}{\sin(\text{FOV}/2)} \times 1.25$.
   - Viewpoints:
     - `front`: Location $(C_x, C_y - d, C_z)$, Rotation $(90^\circ, 0^\circ, 0^\circ)$
     - `side`: Location $(C_x + d, C_y, C_z)$, Rotation $(90^\circ, 0^\circ, 90^\circ)$
     - `back`: Location $(C_x, C_y + d, C_z)$, Rotation $(90^\circ, 0^\circ, 180^\circ)$
     - `three_quarter`: Location $(C_x + \frac{d}{\sqrt{2}}, C_y - \frac{d}{\sqrt{2}}, C_z + 0.15d)$, TrackTo $C$.
     - `turntable_4views`: Sequential capture of `front`, `three_quarter`, `side`, `back`.
     - `close_up_head`: Filter vertices by vertex group (`head`, `snout`, `eyes`, `ears`) or $Z \ge C_z + 0.55 R$; recalculate sub-bounding box and set $f = 85\text{mm}$ or $135\text{mm}$.
     - `close_up_hands`: Filter vertices by vertex group (`fingers`, `hands`, `claws_front`); frame sub-bounding box.
2. **Dual-Mode Viewport Capture Engine**:
   - In interactive socket mode: Dispatch to Blender to call `bpy.ops.render.opengl(write_still=True)` from camera view ($\approx 0.18\text{s}$).
   - In headless CLI mode: Fall back to `scene.render.engine = 'BLENDER_WORKBENCH'` and call `bpy.ops.render.render(write_still=True)` ($\approx 0.64\text{s}$).
   - Encode captured PNG to base64 preview string and return image path + metadata.

### 2.2 R2: Closed-Loop Visual Quality Critique (Auto-Critic QA)
1. **Automated Structural Evaluation Pipeline**:
   - The MCP tool `morphomesh_critique_visual_quality` triggers multi-angle captures via the R1 inspector camera rig.
   - Concurrently executes 4 quantitative geometric integrity audit routines in Blender:
     a. **Garment Clipping / Mesh Penetration**:
        - Builds BVH tree of body mesh.
        - Samples all garment vertices: checks signed distance $\delta = \text{offset} \cdot \vec{n}$.
        - Flags vertices with $\delta < 0$ (penetration) or $0 \le \delta < 0.004\text{m}$ (insufficient clearance).
        - Computes BVH face-to-face overlaps: `body_bvh.overlap(garment_bvh)`.
     b. **Anthropometric Proportion Analysis**:
        - Measures total height, head height, chest/waist/hip girths, limb lengths.
        - Asserts head ratio $H_{\text{total}} / H_{\text{head}} \in [7.0, 7.8]$ and WHR $\in [0.62, 0.74]$.
     c. **Rig Deformation & Skinning Artifacts**:
        - Audits bone weight vertex groups: checks for orphan vertices (total weight $< 0.01$).
        - Performs rotation stress test on primary joints (elbows, knees, shoulders) and computes mesh volume shrinkage / acute pinching.
     d. **Grooming & Hair Intersections**:
        - Checks hair curve evaluated geometry vertex count $> 0$ and $\ge 10,000$ strands.
        - Detects whether hair root points lie on the scalp mesh surface.
2. **Structured Diagnostic Feedback Schema**:
   - Output schema `VisualCritiqueOutput`:
     - `overall_status`: `"PASS"` | `"WARN"` | `"FAIL"`
     - `quality_score`: float `[0.0, 1.0]`
     - `defects`: List of `DefectReport` objects:
       * `defect_type`: `"clipping"` | `"proportion_deviation"` | `"skinning_artifact"` | `"grooming_intersection"`
       * `affected_objects`: `List[str]`
       * `severity`: `"CRITICAL"` | `"HIGH"` | `"MEDIUM"` | `"LOW"`
       * `confidence`: float `[0.0, 1.0]`
       * `metrics`: `Dict[str, Any]` (e.g. `{"penetrating_vertices": 14, "min_clearance_mm": -3.2}`)
       * `remediation_advice`: Specific actionable instructions (e.g., `"Increase Bodice clearance_offset by +0.005m in dress_human"`).
     - `captured_images`: List of multi-angle render previews with base64 data.
3. **Baseline Verification Demo**:
   - Test harness purposefully injects known defects (e.g. scales bodice by 0.95 causing 40+ body penetrations).
   - Verifies that `morphomesh_critique_visual_quality` flags `"clipping"` on `"Mesh_Dress_Bodice"` with confidence $> 0.90$ and status `"FAIL"`.

### 2.3 R3: Interactive Blender Socket Bridge Parity & Reliability
1. **Bridge Parity Gap Resolution**:
   - In `blender_addon/morphomesh/listener.py`, expand `_dispatch` to natively support:
     * `morphomesh.render_preview` & `morphomesh.capture_viewport`
     * `morphomesh.setup_inspector_camera`
     * `morphomesh.critique_visual_quality`
     * `morphomesh.get_scene_status` (ensure complete parity for materials, polycounts, lights, cameras)
     * `morphomesh.create_human_asset`
   - In `src/morphomesh/blender_bridge.py`:
     * Add `capture_viewport(...)`, `setup_inspector_camera(...)`, and `critique_visual_quality(...)` methods.
     * Ensure socket responses are normalized and returned as typed Pydantic models.
     * Ensure connection errors gracefully trigger the headless runner without hanging or dropping connections.

### 2.4 R4: Automated Verification Suite
1. **Comprehensive Pytest Coverage**:
   - `tests/test_inspector_camera.py`: Validates bounding box calculations, camera positioning distances, viewpoint angles, close-up framing, and headless vs socket capture modes.
   - `tests/test_visual_critic.py`: Validates critique pipeline, defect classification schemas, BVH penetration metrics, proportion checking, and the baseline intentional defect injection demo.
   - `tests/test_bridge_socket_parity.py`: Validates socket RPC dispatch for all MCP preview, camera, and scene inspection methods, asserting 100% parity with zero unhandled method errors.
   - Maintain backward compatibility so existing tests in `test_tools_schema.py` continue to pass.

---

## 3. Caveats

1. **OpenGL Headless Restriction**:
   As empirically proven on Windows (`Blender 4.5.4 LTS`), `bpy.ops.render.opengl()` fails in `--background` mode without an active OpenGL window context. The architecture must dynamically route to `BLENDER_WORKBENCH` via `bpy.ops.render.render()` when running headless, while leveraging `bpy.ops.render.opengl()` when running interactively via socket.
2. **Ast Sandbox Permissiveness for Geometry Analysis**:
   Calculating BVH trees requires `mathutils.bvhtree`. Both `BpyCodeValidator` in `blender_bridge.py` and `AddonSecurityValidator` in `listener.py` already allow `mathutils`, which ensures full compatibility.
3. **Backward Compatibility with `test_tools_schema.py`**:
   `tests/test_tools_schema.py` asserts that `mcp.list_tools()` returns exactly 7 tools unless specific environment variables are set. Any new FastMCP tools (such as `morphomesh_capture_viewport` or `morphomesh_critique_visual_quality`) must either be grouped under extended feature flags (e.g. `MORPHOMESH_INCLUDE_QA_TOOLS` / `MORPHOMESH_INCLUDE_HUMAN_TOOLS`) or registered such that existing legacy schema tests remain unaffected.

---

## 4. Conclusion & Architecture Implementation Roadmap

The architectural survey is complete. The exact file boundaries and implementation requirements are mapped:

| Component | Target File | Proposed Scope |
|---|---|---|
| **Camera Rig & Framing** | `src/morphomesh/camera_rig.py` (new) | Bounding box & anatomical center calculation, FOV/distance solver, 6 viewpoints (`front`, `side`, `back`, `three_quarter`, `close_up_head`, `close_up_hands`), `turntable_4views`. |
| **Visual Critic Engine** | `src/morphomesh/visual_critic.py` (new) | Multi-angle defect analysis: BVH penetration/clearance, proportion variance, rig/skinning pinch, grooming density, structured diagnostic reporting. |
| **Models & Schemas** | `src/morphomesh/models.py` | `ViewportCaptureInput`, `ViewportCaptureOutput`, `VisualCritiqueInput`, `VisualCritiqueOutput`, `DefectReport`, `DefectType`. |
| **Bridge Client** | `src/morphomesh/blender_bridge.py` | Add `setup_inspector_camera`, `capture_viewport`, `critique_visual_quality` with dual-mode execution (socket opengl vs headless workbench). |
| **Socket Listener** | `blender_addon/morphomesh/listener.py` | Native `_dispatch` methods for `morphomesh.render_preview`, `capture_viewport`, `setup_inspector_camera`, `critique_visual_quality`. |
| **FastMCP Tools** | `src/morphomesh/server.py` | Expose `morphomesh_capture_viewport` and `morphomesh_critique_visual_quality` with typed docstrings and progress reporting. |
| **Test Suites** | `tests/test_inspector_camera.py`, `tests/test_visual_critic.py`, `tests/test_bridge_socket_parity.py` | Unit and integration verification for camera math, auto-critic diagnostics, intentional defect baseline, and socket RPC parity. |

---

## 5. Verification Method

To independently verify the findings in this report:

1. **Verify Python & Blender Environment**:
   ```powershell
   .venv\Scripts\python.exe --version
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --version
   ```
2. **Verify Interactive Socket Connection & Scene Status**:
   ```powershell
   .venv\Scripts\python.exe -c "from morphomesh.blender_bridge import BlenderBridge; b = BlenderBridge(); print(b.ping()); print('Objects:', len(b.get_scene_status().objects))"
   ```
3. **Verify Interactive Fast Viewport OpenGL Grab**:
   ```powershell
   .venv\Scripts\python.exe -c "from morphomesh.blender_bridge import BlenderBridge; import tempfile, os; b = BlenderBridge(); tmp = os.path.join(tempfile.gettempdir(), 'test_grab.png').replace('\\', '/'); res = b.execute_custom_script(f'''import bpy`nbpy.context.scene.render.filepath = '{tmp}'`nbpy.ops.render.opengl(write_still=True)`nexists = True''', return_variables=['exists']); print(res); print('File size:', os.path.getsize(tmp))"
   ```

4. **Verify Existing Unit Test Suite Baseline**:
   ```powershell
   .venv\Scripts\pytest.exe -k "test_tools_schema"
   ```
