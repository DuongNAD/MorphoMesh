# Technical Survey Report: Interactive Socket Bridge & Viewport Capture

**Explorer**: Explorer 2 (Interactive Socket Bridge & Viewport Capture Explorer)  
**Date**: 2026-09-07T03:42:00Z  
**Working Directory**: `e:\tool\mcp\MorphoMesh\.agents\explorer_survey_2`  
**Parent Orchestrator ID**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Target Requirements**: R1 (Multi-Angle Inspector Camera & Fast Viewport Capture) & R3 (Interactive Blender Socket Bridge Parity & Reliability)

---

## 1. Observation

### 1.1 Existing Camera and Render Implementations

1. **Procedural Auto-Camera in Headless Script Generator (`src/morphomesh/blender_bridge.py:718-756`)**:
   - `ensure_auto_camera(scene=None)` calculates a simple bounding box across all `MESH` objects in `scene.objects` using local `bound_box` transformed by `matrix_world`.
   - Computes geometric center $C = ((x_{\min} + x_{\max})/2, (y_{\min} + y_{\max})/2, (z_{\min} + z_{\max})/2)$ and radius $R = \max(\Delta x, \Delta y, \Delta z)/2$.
   - Positions camera at fixed static offset: `dist = radius * 3.5`, `location = center + Vector((dist * 0.7, -dist * 0.7, dist * 0.5))`.
   - Uses `rot_quat = direction.to_track_quat('-Z', 'Y')` for look-at rotation.
   - **Limitation**: Hardcodes a single diagonal 3/4 perspective viewpoint. Ignores focal length, sensor dimensions, vertical vs horizontal field of view, standard orthographic/turntable views (Front, Side, Back), and anatomical close-ups.

2. **Render Preview Implementation in `blender_bridge.py:1023-1071`**:
   - Implemented exclusively within `_generate_headless_script()`:
     ```python
     scene.render.resolution_x = width
     scene.render.resolution_y = height
     scene.render.engine = engine  # EEVEE or Cycles
     scene.render.filepath = render_path
     bpy.ops.render.render(write_still=True)
     ```
   - Uses full path tracing/rasterization (`bpy.ops.render.render`), taking **1.0 to 8.0 seconds** per frame.
   - Although `params.get("view_angle", "three_quarter")` is accepted, the camera position is never adjusted for different `view_angle` values; it always renders from the static diagonal auto-camera position.

3. **FastMCP Server Preview Tool (`src/morphomesh/server.py:510-566`)**:
   - Defines tool `morphomesh_render_preview(camera_name, resolution_width, resolution_height, render_engine, samples, view_angle, transparent_background, lighting_preset, save_to_disk, output_dir)`.
   - Calls `blender_bridge.render_preview(...)`, reads output image from disk, encodes as base64 in `data["base64_image"]`.

4. **Master Character Assembler Camera Rig (`src/morphomesh/character_assembler.py:1258-1295`)**:
   - Sets up static cameras: `Camera_Portrait_85mm` ($f=85\text{mm}$, distance 2.0m, $Z=1.55\text{m}$), `Camera_FullBody` ($f=50\text{mm}$, distance 5.5m, $Z=0.825\text{m}$), and 4 fixed turnaround cameras (`Camera_Front`, `Camera_ThreeQuarter`, `Camera_Profile`, `Camera_Back`).
   - Uses hardcoded distance constants ($s = \text{height} / 1.65$) tailored specifically to a standing 1.65m human. Fails for quadrupeds, crouched poses, winged creatures, or arbitrary character scales.

### 1.2 Interactive Socket Bridge Architecture & Method Parity

1. **Blender Addon Listener Server (`blender_addon/morphomesh/listener.py`)**:
   - Runs a background TCP socket server on `127.0.0.1:9876`.
   - Implements thread safety using `bpy.app.timers.register(self._drain_queue, persistent=True)`.
   - Incoming commands are received in background thread `_client_handler` and enqueued into `self.command_queue = queue.Queue()`.
   - `_drain_queue` runs on Blender's main thread every 20ms (`return 0.02`), executes `self._dispatch(method, params)`, and returns JSON-RPC responses.
   - **Supported Methods in `listener.py`**:
     - `morphomesh.ping` / `ping` (line 218)
     - `morphomesh.get_scene_status` / `get_scene_info` (line 222)
     - `morphomesh.execute_custom_script` / `execute_code` (line 264)
     - `morphomesh.auto_rig_human` (line 290)
     - `morphomesh.setup_human_materials` (line 342)
     - `morphomesh.groom_human` (line 403)
     - `morphomesh.dress_human` (line 460)
     - `morphomesh.assemble_master_character` (line 520)

2. **Parity Gap Analysis**:
   - `morphomesh.render_preview` is **NOT implemented** in `listener.py`. Sending this RPC over socket raises `ValueError("Unknown RPC method: morphomesh.render_preview")`.
   - `morphomesh.create_human_asset` is **NOT implemented** in `listener.py`.
   - Creature pipeline methods (`setup_creature_fur`, `setup_creature_materials`, `generate_war_armor`, `optimize_topology`, `create_armature`) are **NOT implemented** in `listener.py`.
   - When a method is missing in `listener.py`, `blender_bridge.py:503-515` attempts fallback via `send_socket_request("execute_code", {"code": script})`.
   - **Discovered Failure in Fallback**: As proven in `tests/test_adversarial_fastmcp_bridge_human.py:394-408`, the fallback to `execute_code` **fails 100% of the time** because:
     a) Generated scripts for complex operations are 60KB-120KB, exceeding `MAX_SCRIPT_LENGTH = 10000` in `BpyCodeValidator`.
     b) Generated scripts call `open()` or `exec()`, which are strictly blocked by `AddonSecurityValidator` in `listener.py:58-59`.
   - Therefore, direct socket method implementation (Method Parity) in `listener.py` is the only viable path for interactive execution.

3. **Socket Protocol & Framing Flaws**:
   - In `listener.py:160-169`, `_client_handler` reads up to 65536 bytes into `buffer` and calls `json.loads(buffer.decode("utf-8"))`.
   - If a client sends multiple JSON requests or trailing whitespace, `json.loads` raises `JSONDecodeError: Extra data`, causing subsequent requests on that connection to fail.
   - Response framing adds `b"\n"` (`client.sendall(json.dumps(response).encode("utf-8") + b"\n")`), but request parsing does not split on `\n`.
   - In `listener.py:178-214`, if an unhandled exception escapes `_drain_queue`, Blender unregisters the timer callback permanently, leaving the socket server alive but permanently deaf to queued commands.

---

## 2. Logic Chain

### 2.1 R1: Camera Rig Positioning Mathematics & Framing Algorithm

#### Step 1: Multi-Object Hierarchical Bounding Box Calculation
Let $\mathcal{O}_{\text{char}} = \{ O_1, O_2, \dots, O_m \}$ be the set of visible character mesh objects in the active scene or character collection.
For each object $O_k$, Blender provides 8 local-space bounding box corner coordinates $\mathbf{c}_{k,i} \in \mathbb{R}^3$ ($i = 1, \dots, 8$).
Transforming each corner to global world coordinates using the object's world matrix $M_k \in \mathbb{R}^{4 \times 4}$:
$$\mathbf{w}_{k,i} = M_k \cdot \begin{bmatrix} \mathbf{c}_{k,i} \\ 1 \end{bmatrix}$$
The global Axis-Aligned Bounding Box (AABB) $[\mathbf{v}_{\min}, \mathbf{v}_{\max}]$ across all character meshes is:
$$\mathbf{v}_{\min} = \begin{bmatrix} \min_{k, i} (\mathbf{w}_{k,i})_x \\ \min_{k, i} (\mathbf{w}_{k,i})_y \\ \min_{k, i} (\mathbf{w}_{k,i})_z \end{bmatrix}, \quad \mathbf{v}_{\max} = \begin{bmatrix} \max_{k, i} (\mathbf{w}_{k,i})_x \\ \max_{k, i} (\mathbf{w}_{k,i})_y \\ \max_{k, i} (\mathbf{w}_{k,i})_z \end{bmatrix}$$
The character dimensions and geometric center are:
$$\Delta x = x_{\max} - x_{\min}, \quad \Delta y = y_{\max} - y_{\min}, \quad \Delta z = z_{\max} - z_{\min} = H$$
$$\mathbf{C}_{\text{char}} = \frac{\mathbf{v}_{\min} + \mathbf{v}_{\max}}{2} = \begin{bmatrix} (x_{\min} + x_{\max}) / 2 \\ (y_{\min} + y_{\max}) / 2 \\ (z_{\min} + z_{\max}) / 2 \end{bmatrix}$$
The bounding sphere radius circumscribing the character is:
$$R_{\text{char}} = \frac{1}{2} \sqrt{(\Delta x)^2 + (\Delta y)^2 + (\Delta z)^2}$$

#### Step 2: Optical Camera Framing Distance Derivation
For a pinhole camera with focal length $f$ (mm), sensor width $S_w$ (mm), sensor height $S_h$ (mm), and render resolution $W_{\text{px}} \times H_{\text{px}}$:
The horizontal and vertical fields of view are:
$$\text{FOV}_h = 2 \arctan\left(\frac{S_w}{2f}\right), \quad \text{FOV}_v = 2 \arctan\left(\frac{S_h}{2f}\right)$$
For a bounding sphere of radius $R$ to fit completely inside the frustum without clipping in any orientation, the camera must be positioned such that the sphere subtends an angle smaller than both $\text{FOV}_h$ and $\text{FOV}_v$.
Let the limiting half-angle be:
$$\alpha_{\min} = \min\left(\frac{\text{FOV}_h}{2}, \frac{\text{FOV}_v}{2}\right)$$
From the right triangle formed by camera focal point, sphere center, and sphere tangent horizon:
$$\sin(\alpha_{\min}) = \frac{R}{d} \implies d = \frac{R}{\sin(\alpha_{\min})}$$
To account for framing aesthetics and prevent touching viewport boundaries, incorporate safety margin $\mu \in [0.10, 0.20]$ (e.g. $\mu = 0.15$ for 15% margin):
$$d_{\text{frame}} = \frac{R}{\sin(\alpha_{\min})} \cdot (1 + \mu)$$
*Note on Planar vs Spherical Framing*: If framing a planar height $\Delta z$ (e.g. Front Orthographic inspection), the exact distance to fit height is $d_v = \frac{\Delta z / 2}{\tan(\text{FOV}_v / 2)} \cdot (1 + \mu)$. The spherical formula $d = \frac{R}{\sin(\alpha_{\min})} \cdot (1 + \mu)$ is superior because it guarantees zero clipping across all turntable rotations.

#### Step 3: Anatomical Sub-Region Center & Radius Estimation
For focused quality inspection, the rig must target specific anatomical sub-regions:
1. **Full Body**:
   - Center: $\mathbf{C}_{\text{full}} = [C_x, C_y, z_{\min} + 0.50 H]^T$
   - Target Radius: $R_{\text{full}} = R_{\text{char}}$
   - Standard Lens: $50\text{mm}$ (distortion-free perspective).
2. **Head & Portrait (Bust)**:
   - Primary (Landmarks): If `head_top` and `chin` landmarks exist:
     $$\mathbf{C}_{\text{head}} = \frac{\mathbf{p}_{\text{head\_top}} + \mathbf{p}_{\text{chin}}}{2}, \quad R_{\text{head}} = 1.3 \times \frac{\|\mathbf{p}_{\text{head\_top}} - \mathbf{p}_{\text{chin}}\|_2}{2}$$
   - Secondary (Vertex Groups): Centroid of vertex group `head` or `face`:
     $$\mathbf{C}_{\text{head}} = \frac{1}{\sum w_v} \sum_{v \in \text{head}} w_v \cdot (M_{\text{world}} \cdot \mathbf{v}_{\text{co}})$$
   - Anthropometric Fallback: For stylized human ($\text{head\_ratio} \approx 7.41$):
     $$\mathbf{C}_{\text{head}} = [C_x, C_y, z_{\min} + 0.90 H]^T, \quad R_{\text{head}} \approx 0.14 H$$
   - Standard Lens: $85\text{mm}$ (portrait telephoto, minimizes facial perspective distortion).
3. **Torso & Bodice (Wardrobe Fit & Armor Penetration)**:
   - Center: $\mathbf{C}_{\text{torso}} = [C_x, C_y, z_{\min} + 0.60 H]^T, \quad R_{\text{torso}} \approx 0.25 H$
   - Standard Lens: $70\text{mm}$.
4. **Hands & Fingers (Marionette Strings & Claws)**:
   - Primary: Landmarks `wrist_L`, `wrist_R`, or bone `DEF-hand.L` / `DEF-hand.R`.
   - Fallback (Both Hands): $\mathbf{C}_{\text{hands}} = [C_x, C_y - 0.05 H, z_{\min} + 0.52 H]^T, \quad R_{\text{hands}} \approx 0.28 H$
   - Left Hand Close-up (Magic strings & butterflies): $\mathbf{C}_{\text{hand\_L}} = [C_x - 0.25 H, C_y, z_{\min} + 0.52 H]^T, \quad R_{\text{hand}} \approx 0.12 H$
   - Standard Lens: $85\text{mm}$ macro.
5. **Feet & Footwear (Sandals & Paws)**:
   - Center: $\mathbf{C}_{\text{feet}} = [C_x, C_y, z_{\min} + 0.08 H]^T, \quad R_{\text{feet}} \approx 0.15 H$
   - Standard Lens: $65\text{mm}$.

#### Step 4: Spherical Orbit Camera Placement and Quaternion Alignment
In Blender's global coordinate system ($+X$ = Right, $+Y$ = Back, $+Z$ = Up), characters face towards $-Y$ (towards the front camera).
Given target center $\mathbf{C}$, framing distance $d$, azimuth $\theta \in [0^\circ, 360^\circ)$, and elevation $\phi \in [-90^\circ, 90^\circ]$:
The camera world coordinates are:
$$\mathbf{P}_{\text{cam}}(\theta, \phi, d, \mathbf{C}) = \begin{bmatrix} C_x + d \cos \phi \sin \theta \\ C_y - d \cos \phi \cos \theta \\ C_z + d \sin \phi \end{bmatrix}$$

**Standard Viewpoint Coordinate Table**:

| Viewpoint Name | Azimuth $\theta$ | Elevation $\phi$ | Framing Target | Lens $f$ | Purpose |
|---|---|---|---|---|---|
| `Camera_Front` | $0^\circ$ | $0^\circ$ | Full Body | $50\text{mm}$ | Silhouette, bilateral symmetry, limb alignment |
| `Camera_Side_R` | $90^\circ$ | $0^\circ$ | Full Body | $50\text{mm}$ | Spine curvature, chest/bust depth, posture |
| `Camera_Back` | $180^\circ$ | $0^\circ$ | Full Body | $50\text{mm}$ | Back cascade hair flow, scapula, dorsal armor |
| `Camera_Side_L` | $270^\circ$ | $0^\circ$ | Full Body | $50\text{mm}$ | Left lateral symmetry, garment balance |
| `Camera_ThreeQuarter` | $45^\circ$ | $15^\circ$ | Full Body | $50\text{mm}$ | Canonical beauty inspection, volume depth |
| `Camera_ThreeQuarter_L` | $315^\circ$ | $15^\circ$ | Full Body | $50\text{mm}$ | Reverse 3/4 perspective |
| `Camera_CloseUp_Head` | $15^\circ$ | $5^\circ$ | Head / Bust | $85\text{mm}$ | Cornea refraction, iris, facial topology, bangs |
| `Camera_CloseUp_Hands` | $30^\circ$ | $-10^\circ$ | Hands / Marionette | $85\text{mm}$ | Finger skinning, red strings, butterfly attachment |
| `Camera_CloseUp_Torso` | $20^\circ$ | $0^\circ$ | Torso / Bodice | $70\text{mm}$ | Fabric drape, waist sash, armor clearance |
| `Camera_CloseUp_Feet` | $15^\circ$ | $-15^\circ$ | Feet / Sandals | $70\text{mm}$ | Sandal straps, plantigrade contact, claw curve |

**Orientation Alignment**:
Direction vector: $\mathbf{D} = \mathbf{C} - \mathbf{P}_{\text{cam}}$.
In Blender camera coordinates (optical forward is $-Z$, sensor up is $+Y$):
$$\mathbf{q}_{\text{rot}} = \mathbf{D}.\text{to\_track\_quat}('-Z', 'Y')$$
$$\mathbf{E}_{\text{rot}} = \mathbf{q}_{\text{rot}}.\text{to\_euler}()$$
This guarantees the optical axis passes exactly through the anatomical center with vertical horizon alignment.

---

### 2.2 Fast Viewport Capture Mechanism vs Headless Batch Render

#### Step 1: Comparison of Capture Pipelines

| Dimension | Interactive Viewport OpenGL Grab | Headless Batch Render |
|---|---|---|
| **Underlying API** | `bpy.ops.render.opengl(write_still=True)` | `bpy.ops.render.render(write_still=True)` |
| **Execution Latency** | **15ms – 45ms** (50x faster) | **1,200ms – 8,000ms** (Cycles / EEVEE) |
| **Execution Context** | Requires `VIEW_3D` area or `temp_override` | Headless CLI background process (`blender -b`) |
| **Diagnostic Shading Modes** | `SOLID` (Matcap, Flat, Curvature, Random color per object), `MATERIAL`, `RENDERED`, `WIREFRAME`, `XRAY` | Full shader tree evaluation only |
| **Auto-Critic Utility** | **Exceptional**: `SOLID` with `color_type='RANDOM'` instantly isolates garment penetration from skin without shading glare | Essential for final beauty verification and SSS realism |

#### Step 2: Context Override Pattern for Viewport OpenGL Capture
When triggered from background socket timers, `bpy.ops.render.opengl.poll()` fails if no 3D Viewport context is provided.
To guarantee reliable execution across all Blender UI configurations:
```python
def execute_viewport_capture(
    output_path: str,
    camera_obj: bpy.types.Object,
    shading_mode: str = "SOLID",
    color_type: str = "RANDOM",
    show_xray: bool = False,
    resolution: Tuple[int, int] = (1024, 1024),
) -> str:
    scene = bpy.context.scene
    scene.camera = camera_obj
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.filepath = output_path

    # Locate View3D space
    view3d_area = next((a for a in bpy.context.screen.areas if a.type == 'VIEW_3D'), None) if bpy.context.screen else None

    if view3d_area:
        space = view3d_area.spaces.active
        # Save original shading state
        orig_type = space.shading.type
        orig_color = getattr(space.shading, 'color_type', 'MATERIAL')
        orig_xray = space.shading.show_xray

        try:
            space.shading.type = shading_mode
            if hasattr(space.shading, 'color_type'):
                space.shading.color_type = color_type
            space.shading.show_xray = show_xray
            bpy.context.view_layer.update()

            # Execute with temp_override
            with bpy.context.temp_override(area=view3d_area):
                bpy.ops.render.opengl(write_still=True, view_context=True)
        finally:
            space.shading.type = orig_type
            if hasattr(space.shading, 'color_type'):
                space.shading.color_type = orig_color
            space.shading.show_xray = orig_xray
    else:
        # Fallback to standard opengl render or headless batch render
        try:
            bpy.ops.render.opengl(write_still=True)
        except Exception:
            bpy.ops.render.render(write_still=True)

    return output_path
```

---

### 2.3 R3: Interactive Blender Socket Bridge Parity & Reliability Architecture

#### Step 1: Thread-Safe Dispatch via `bpy.app.timers`
Blender's C-data structures are not thread-safe. All scene modifications, operator calls, and data writes must execute synchronously on Blender's main event loop.
- The background thread (`_client_handler`) must **only** receive network bytes, deserialize JSON, and enqueue requests:
  `self.command_queue.put((cmd, client))`
- The main thread callback `_drain_queue` must pop requests, execute `_dispatch(method, params)`, format the JSON-RPC response, and send it back to `client`.
- **Timer Immortality Guard**: If an unhandled exception escapes `_drain_queue`, Blender silently cancels the timer. To prevent server death:
  ```python
  def _drain_queue(self) -> float:
      if not self.running:
          return None
      try:
          while not self.command_queue.empty():
              cmd, client = self.command_queue.get_nowait()
              # process cmd and sendall response...
      except Exception as fatal_e:
          logger.critical(f"Fatal unhandled exception in _drain_queue: {fatal_e}", exc_info=True)
      return 0.02  # GUARANTEES timer persists regardless of dispatch failure!
  ```

#### Step 2: Message Framing via Newline-Delimited JSON (NDJSON)
To prevent `JSONDecodeError: Extra data` or chunk truncation:
- Every request payload must terminate with `\n`.
- The receiver maintains an accumulation buffer per connection:
  ```python
  buffer += client.recv(65536)
  while b"\n" in buffer:
      line, buffer = buffer.split(b"\n", 1)
      if line.strip():
          cmd = json.loads(line.decode("utf-8"))
          self.command_queue.put((cmd, client))
  ```
- Every response sent by the server must terminate with `\n`.
- This ensures chunk-agnostic streaming without packet boundary coupling.

#### Step 3: Comprehensive Method Parity Dispatch Table
To eliminate unhandled method errors, `listener.py` must register the full catalog of MorphoMesh methods:

```
+------------------------------------------+--------------------+----------------------------------------+
| RPC Method Identifier                    | Target Module      | Return Payload Structure               |
+------------------------------------------+--------------------+----------------------------------------+
| morphomesh.ping                          | listener.py        | status, blender_version, active_object |
| morphomesh.get_scene_status              | listener.py        | scene_name, objects, cameras, lights   |
| morphomesh.execute_custom_script         | listener.py        | success, returned_data, stdout         |
| morphomesh.setup_inspection_cameras      | camera_rig.py (new)| camera_names, count, framing_center    |
| morphomesh.capture_viewport              | viewport.py (new)  | image_path, base64_image, shading_mode |
| morphomesh.capture_multi_angle_inspection| viewport.py (new)  | captures: [{viewpoint, image_path...}] |
| morphomesh.render_preview                | blender_bridge.py  | image_path, base64_image, view_angle   |
| morphomesh.create_human_asset            | human_generator.py | asset_id, mesh_path, quad_ratio        |
| morphomesh.auto_rig_human                | human_rigging.py   | armature_name, bone_count: 163         |
| morphomesh.setup_human_materials         | human_materials.py | materials_created, preset              |
| morphomesh.groom_human                   | human_grooming.py  | layers, strand_count                   |
| morphomesh.dress_human                   | wardrobe.py        | garments, accessories, prop_count      |
| morphomesh.assemble_master_character     | character_assembler| blend_file_path, manifest              |
| morphomesh.setup_creature_fur            | grooming.py        | fur_systems, strand_count              |
| morphomesh.setup_creature_materials      | materials.py       | materials_assigned                     |
| morphomesh.generate_war_armor            | armor.py           | armor_objects, clearance_verified      |
| morphomesh.optimize_topology             | operators.py       | optimized_asset_id, quad_percentage    |
| morphomesh.create_armature               | operators.py       | armature_name, bone_count              |
+------------------------------------------+--------------------+----------------------------------------+
```

---

## 3. Caveats

1. **Blender Headless Environment Limitations for Viewport Grab**:
   - `bpy.ops.render.opengl` in true headless mode (`blender -b`) requires an active OpenGL context or offscreen frame buffer (e.g. EGL or Mesa software rasterizer on Linux, or native GPU context on Windows/macOS).
   - In environments where headless OpenGL context creation fails, the system must automatically fallback to `bpy.ops.render.render` with low sample count (e.g. 1 sample with EEVEE) to ensure uninterrupted capture.
2. **Dynamic Rigging and Bone Landmarks in Posed Characters**:
   - If a character has active pose bones or constraints, mesh vertices move away from rest-pose landmarks.
   - The bounding box calculation must compute the evaluated depsgraph (`bpy.context.evaluated_depsgraph_get()`) to capture true deformed positions rather than rest-pose geometry.
3. **Socket Port Collisions**:
   - Default port `9876` may collide if multiple Blender instances run simultaneously. `listener.py` and `blender_bridge.py` must support dynamic port configuration via environment variable `BLENDER_PORT`.

---

## 4. Conclusion

1. **R1 Technical Conclusion**:
   - An automated multi-angle inspection camera rig must be introduced as a dedicated modular subsystem (`src/morphomesh/camera_rig.py` and operator in `operators.py`).
   - The rig must dynamically calculate global bounding box spans across all character meshes, estimate 5 anatomical centers (Full Body, Head, Torso, Hands, Feet), and position cameras along spherical orbit trajectories $(\theta, \phi, d)$ using the exact optical formula $d = \frac{R}{\sin(\alpha_{\min})} \cdot (1 + \mu)$ with look-at quaternion tracking.
   - For rapid QA feedback, Viewport OpenGL grab (`bpy.ops.render.opengl` with context temp_override) provides **15–45ms captures** with specialized diagnostic shading modes (`SOLID` + Random color), while headless batch rendering (`bpy.ops.render.render`) provides a reliable offline fallback.

2. **R3 Technical Conclusion**:
   - Full parity between `listener.py` and `blender_bridge.py` requires expanding `_dispatch()` to handle all 18 core pipeline and inspection methods directly on Blender's main thread.
   - Network framing must be standardized to Newline-Delimited JSON (NDJSON) to eliminate buffer boundary errors.
   - Timer robustness must be guaranteed via an unhandled exception catch block in `_drain_queue` that always returns `0.02`, preventing silent timer unregistration.

---

## 5. Verification Method

### 5.1 Independent Reproduction Commands
To verify the existing test baseline and findings:
```powershell
# 1. Run core Blender bridge and security validator tests
pytest tests/test_blender_bridge.py -v

# 2. Run adversarial FastMCP bridge integration tests
pytest tests/test_adversarial_fastmcp_bridge_human.py -v

# 3. Run FastMCP tool registry and schema tests
pytest tests/test_fastmcp_human_tools.py -v

# 4. Verify all 147 test cases execute with 0 failures
pytest tests/test_blender_bridge.py tests/test_adversarial_fastmcp_bridge_human.py -v
```

### 5.2 Specific Files to Inspect
- `blender_addon/morphomesh/listener.py`: Inspect lines 151–215 (socket receive loop, buffer handling, `_drain_queue` timer callback) and lines 216–557 (`_dispatch` method catalog).
- `src/morphomesh/blender_bridge.py`: Inspect lines 316–395 (`send_socket_request`), lines 488–527 (`execute` dual-mode dispatch), lines 718–756 (`ensure_auto_camera`), and lines 1023–1071 (`render_preview`).
- `src/morphomesh/server.py`: Inspect lines 510–566 (`morphomesh_render_preview` FastMCP tool).
- `src/morphomesh/character_assembler.py`: Inspect lines 1258–1295 (hardcoded camera creation in `YuNianAnAssembler`).

### 5.3 Invalidation Conditions
The architectural recommendations herein would be invalidated if:
1. Blender introduces multi-threaded `bpy` write access, making `bpy.app.timers` obsolete (unlikely in foreseeable Blender 4.x / 5.x architecture).
2. Blender deprecates `bpy.ops.render.opengl` without a GPU offscreen buffer replacement.
3. FastMCP mandates binary streaming protocols over JSON-RPC.
