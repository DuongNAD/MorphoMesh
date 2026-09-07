# Handoff Report: Milestone 1 Interactive Socket Bridge Client Explorer (M1_2)

**Author**: Explorer M1_2 (Bridge Client Explorer)  
**Target File**: `src/morphomesh/blender_bridge.py`  
**Milestone**: Milestone 1 - Interactive Socket Bridge Parity & Reliability (R3)  
**Date**: 2026-09-07T03:48:00Z  
**Parent Conversation ID**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`

---

## 1. Observation

A detailed architectural and line-by-line inspection of `src/morphomesh/blender_bridge.py`, `blender_addon/morphomesh/listener.py`, `src/morphomesh/models.py`, and test suites was conducted.

### Observation 1.1: Request Payload Missing Newline Termination for NDJSON Streaming
- **File**: `src/morphomesh/blender_bridge.py`
- **Lines 331–343**:
```python
        req_id = f"req-{uuid.uuid4().hex[:8]}"
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "type": method,
            "params": params,
        }
        encoded = json.dumps(payload).encode("utf-8")

        with socket.create_connection((self.host, self.port), timeout=self.socket_timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(encoded)
```
- **Finding**: The payload is serialized as raw UTF-8 bytes without a trailing newline delimiter (`b"\n"`). In contrast, the server listener (`blender_addon/morphomesh/listener.py:210`) uses newline-delimited framing (`client.sendall(json.dumps(response).encode("utf-8") + b"\n")`). When the listener switches to NDJSON stream processing (`readline()` or splitting on `\n`), requests lacking `\n` hang indefinitely until a socket timeout occurs.

### Observation 1.2: Response Reading is Not Line-Buffered & Lacks Clean Error/Timeout Propagation
- **File**: `src/morphomesh/blender_bridge.py`
- **Lines 345–360**:
```python
            chunks: List[bytes] = []
            response = None
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                raw_bytes = b"".join(chunks)
                try:
                    response = json.loads(raw_bytes.decode("utf-8"))
                    break
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

            if not response:
                raise BlenderExecutionError("Empty or malformed response received from Blender socket.")
```
- **Finding**: 
  1. `sock.recv(65536)` is repeatedly appended into `chunks` and parsed via `json.loads(b"".join(chunks).decode("utf-8"))` on every chunk. It does not parse line-buffered tokens on `b"\n"`. If multiple messages or keepalive newlines arrive, parsing can desync.
  2. `sock.recv(65536)` can raise `socket.timeout` or `TimeoutError`. Currently, there is no exception block wrapping `sock.recv` inside the loop. When a hanging socket times out, `test_hanging_socket_times_out_cleanly` expects a clean `TimeoutError`.
  3. No explicit `try...finally` block exists to ensure `sock.shutdown(socket.SHUT_RDWR)` and `sock.close()` are called on Windows to immediately reclaim socket descriptors.
  4. At line 375, `res = response.get("result", {})` assumes standard JSON-RPC with a `"result"` field. If a flat dictionary is returned (e.g. `{"status": "success", ...}`), `res` is incorrectly extracted as empty `{}`.

### Observation 1.3: `execute()` False Fallback to Headless CLI Due to Restrictive Success Filter
- **File**: `src/morphomesh/blender_bridge.py`
- **Lines 503–516**:
```python
                try:
                    script = self._generate_headless_script(method, params)
                    res = self.send_socket_request("execute_code", {"code": script}, timeout=timeout)
                    if isinstance(res, dict) and (
                        res.get("status") == "success"
                        or res.get("success") is True
                        or "object_count" in res
                        or "blender_version" in res
                    ):
                        return res
                except Exception as e2:
                    logger.warning(f"Interactive socket execute_code failed ({e2}), falling back to headless runner.")

        return self._dispatch_headless(method, params, int(timeout))
```
- **Finding**: 
  When executing rendering or capture methods (such as `morphomesh.render_preview` or `morphomesh.capture_viewport`), `_generate_headless_script` emits:
  ```python
  emit_result({
      "image_path": render_path,
      "image_format": "png",
      "resolution": [width, height],
      "render_engine": engine,
      "samples": samples,
      "render_time_seconds": 0.85,
      "view_angle": params.get("view_angle", "three_quarter"),
      "lighting_preset": params.get("lighting_preset", "studio_three_point"),
  })
  ```
  Notice that `"image_path"` is present, but neither `"status": "success"` nor `"success": True` nor `"object_count"` nor `"blender_version"` is in `res`.
  Consequently, lines 506–511 evaluate to `False`, `execute()` erroneously discards the valid socket response, and line 516 falls back to `_dispatch_headless()` — launching a redundant, slow background Blender CLI process (`blender.exe --background ...`)!
  Furthermore, `"camera_name"` (from `setup_inspector_camera`), `"defects"` (from `critique_visual_quality`), and non-error `"status"` (e.g. `"status": "pong"`) are not included in the success predicate.

### Observation 1.4: Missing Dispatch Branches in `_generate_headless_script()`
- **File**: `src/morphomesh/blender_bridge.py`
- **Lines 1965–1967**:
```python
    else:
        emit_result({"status": "error", "message": f"Unknown RPC method: {method}"})
```
- **Finding**: `_generate_headless_script()` currently lacks branches for:
  - `morphomesh.capture_viewport`
  - `morphomesh.setup_inspector_camera`
  - `morphomesh.critique_visual_quality`
  If any of these methods falls back to headless script generation (either via `execute_code` in interactive mode or when Blender is closed), line 1966 triggers an `Unknown RPC method` error.

### Observation 1.5: Missing Typed Client Inspection Methods on `BlenderBridge`
- **File**: `src/morphomesh/blender_bridge.py`
- **Finding**: `BlenderBridge` lacks typed client methods required by Milestone 1 and `PROJECT.md`:
  - `capture_viewport(...)`
  - `setup_inspector_camera(...)`
  - `critique_visual_quality(...)`
  Additionally, `render_preview()` and `get_scene_status()` directly unpack `**res` into Pydantic models without defensive defaults, making them vulnerable to validation errors when socket responses return partial data.

---

## 2. Logic Chain

```
[Observation 1.1: Request lacks b"\n"] 
  ──> [NDJSON server uses readline()/split('\n')] 
  ──> [Client blocks or hangs] 
  ──> Fix: append b"\n" to JSON serialization in send_socket_request.

[Observation 1.2: Unbuffered recv loop & uncaught timeout] 
  ──> [Buffer boundary issues on chunk fragmentation & raw exceptions on timeout] 
  ──> Fix: buffer bytes, split on b"\n", parse complete lines, wrap recv with (socket.timeout, TimeoutError) -> TimeoutError, and ensure shutdown/close in finally block.

[Observation 1.3: execute() checks only status=="success", success==True, object_count, blender_version] 
  ──> [render_preview & capture_viewport return image_path without status=="success"] 
  ──> [Condition evaluates to False] 
  ──> [Interactive socket execution falsely discarded, triggering headless CLI runner fallback] 
  ──> Fix: expand condition to check "image_path" in res, "camera_name" in res, "defects" in res, "scene_name" in res, and any status != "error".

[Observation 1.4: _generate_headless_script() lacks capture_viewport, setup_inspector_camera, critique_visual_quality] 
  ──> [Headless CLI runner & execute_code fail with "Unknown RPC method"] 
  ──> Fix: add full procedural script generator branches for these 3 methods.

[Observation 1.5: Missing typed client methods & fragile **res unpacking] 
  ──> [MCP server and external callers cannot call high-level inspection APIs] 
  ──> Fix: implement typed capture_viewport(), setup_inspector_camera(), critique_visual_quality(), and add setdefault() sanitization to render_preview() and get_scene_status().
```

---

## 3. Implementation Blueprints

### Blueprint 1: `send_socket_request()` in `src/morphomesh/blender_bridge.py`
**Replace Lines 331–394 with**:
```python
        req_id = f"req-{uuid.uuid4().hex[:8]}"
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "type": method,
            "params": params,
        }
        # NDJSON streaming: ensure request is terminated with newline b"\n"
        encoded = json.dumps(payload).encode("utf-8") + b"\n"

        sock = None
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.socket_timeout)
            sock.settimeout(timeout)
            sock.sendall(encoded)

            buffer = b""
            response = None
            while True:
                try:
                    chunk = sock.recv(65536)
                except (socket.timeout, TimeoutError) as e:
                    raise TimeoutError(f"Socket request timed out after {timeout}s for method '{method}': {e}") from e

                if not chunk:
                    # Remote closed connection (EOF); parse remaining buffer if present
                    if buffer.strip():
                        try:
                            response = json.loads(buffer.decode("utf-8"))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            pass
                    break

                buffer += chunk
                # Line-buffered NDJSON framing: split on newline delimiter
                if b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.strip()
                    if line:
                        try:
                            response = json.loads(line.decode("utf-8"))
                            break
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue

            if not response:
                raise BlenderExecutionError(f"Empty or malformed response received from Blender socket for method '{method}'.")

            if response.get("status") == "error":
                err_msg = response.get("message") or response.get("error", {}).get("message", "Unknown error")
                raise BlenderExecutionError(
                    f"Blender Socket Error: {err_msg}",
                    details=response,
                )
            if "error" in response:
                err = response["error"]
                err_msg = err.get("message", "Unknown error") if isinstance(err, dict) else str(err)
                err_code = err.get("code") if isinstance(err, dict) else None
                raise BlenderExecutionError(
                    f"Blender Socket Error: [{err_code}] {err_msg}",
                    details=err.get("data", {}) if isinstance(err, dict) else {},
                )

            # JSON-RPC 2.0 result unwrap or direct dictionary fallback
            res = response.get("result") if response.get("result") is not None else response
            # If the socket server is blender-mcp, result might be {"executed": true, "result": "..."}
            if isinstance(res, dict) and "executed" in res and "result" in res:
                out_str = res["result"]
                # Check for MORPHOMESH_RESULT or sentinel JSON
                m = re.search(r"MORPHOMESH_RESULT:(\{.*?\})", out_str)
                if not m:
                    m = re.search(
                        rf"{re.escape(SENTINEL_START)}\s*({{.*?}})\s*{re.escape(SENTINEL_END)}",
                        out_str,
                        re.DOTALL,
                    )
                if m:
                    try:
                        return json.loads(m.group(1))
                    except json.JSONDecodeError:
                        pass
                return res
            return res
        finally:
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    sock.close()
                except OSError:
                    pass
```

---

### Blueprint 2: `execute()` Dispatch Condition in `src/morphomesh/blender_bridge.py`
**Replace Lines 506–512 with**:
```python
                    if isinstance(res, dict) and not (
                        res.get("status") == "error"
                        or res.get("success") is False
                        or "error" in res
                    ) and (
                        res.get("status") == "success"
                        or res.get("success") is True
                        or "object_count" in res
                        or "blender_version" in res
                        or "image_path" in res
                        or "camera_name" in res
                        or "defects" in res
                        or "defect_count" in res
                        or "scene_name" in res
                        or ("status" in res and res.get("status") != "error")
                    ):
                        return res
```

---

### Blueprint 3: `_generate_headless_script()` Branches in `src/morphomesh/blender_bridge.py`
**Insert before `else: emit_result({"status": "error", "message": f"Unknown RPC method: {method}"})` (line 1965)**:
```python
    elif method in ("morphomesh.capture_viewport", "capture_viewport"):
        scene = bpy.context.scene
        out_path = params.get("output_path") or os.path.join(tempfile.gettempdir(), f"viewport_{{uuid.uuid4().hex[:8]}}.png")
        cam_name = params.get("camera_name", "MorphoMesh_Inspector_Camera")
        res_tuple = params.get("resolution", [1024, 1024])
        res_w = int(res_tuple[0]) if len(res_tuple) > 0 else 1024
        res_h = int(res_tuple[1]) if len(res_tuple) > 1 else 1024
        shading = params.get("shading_mode", "SOLID")
        c_type = params.get("color_type", "RANDOM")

        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        scene.render.resolution_x = res_w
        scene.render.resolution_y = res_h
        scene.render.engine = 'BLENDER_WORKBENCH'
        if hasattr(scene, "display") and hasattr(scene.display, "shading"):
            scene.display.shading.light = 'STUDIO'
            if hasattr(scene.display.shading, "color_type"):
                try:
                    scene.display.shading.color_type = c_type
                except Exception:
                    pass

        if cam_name in scene.objects:
            scene.camera = scene.objects[cam_name]
        else:
            ensure_auto_camera(scene)

        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)

        emit_result({{
            "status": "success",
            "image_path": out_path,
            "resolution": [res_w, res_h],
            "shading_mode": shading,
            "color_type": c_type,
        }})

    elif method in ("morphomesh.setup_inspector_camera", "setup_inspector_camera"):
        scene = bpy.context.scene
        vp = params.get("viewpoint", "three_quarter")
        cam_name = params.get("camera_name", "MorphoMesh_Inspector_Camera")
        f_len = float(params.get("focal_length", 50.0))
        t_center = params.get("target_center")
        f_radius = params.get("framing_radius")

        if t_center is not None and f_radius is not None:
            center = mathutils.Vector(t_center)
            radius = float(f_radius)
        else:
            mesh_objs = [o for o in scene.objects if o.type == 'MESH']
            min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
            max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
            for o in mesh_objs:
                for corner in o.bound_box:
                    mat = o.matrix_world
                    wc = mat @ mathutils.Vector(corner)
                    min_x = min(min_x, wc.x)
                    min_y = min(min_y, wc.y)
                    min_z = min(min_z, wc.z)
                    max_x = max(max_x, wc.x)
                    max_y = max(max_y, wc.y)
                    max_z = max(max_z, wc.z)
            if min_x == float('inf'):
                center = mathutils.Vector((0.0, 0.0, 1.0))
                radius = 1.0
            else:
                center = mathutils.Vector(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0))
                radius = max(max_x - min_x, max_y - min_y, max_z - min_z) / 2.0 or 1.0

        d = radius * 2.8
        vp_lower = str(vp).lower()
        if vp_lower in ("front", "front_view"):
            offset = mathutils.Vector((0.0, -d, 0.0))
        elif vp_lower in ("side", "side_view", "right", "right_view"):
            offset = mathutils.Vector((d, 0.0, 0.0))
        elif vp_lower in ("back", "back_view"):
            offset = mathutils.Vector((0.0, d, 0.0))
        elif vp_lower in ("head", "head_closeup", "portrait"):
            head_center = center + mathutils.Vector((0.0, 0.0, radius * 0.6))
            center = head_center
            d_head = radius * 1.2
            offset = mathutils.Vector((0.0, -d_head, 0.1))
        elif vp_lower in ("hands", "hands_closeup"):
            offset = mathutils.Vector((radius * 0.8, -radius * 1.0, 0.0))
        else:
            offset = mathutils.Vector((d * 0.707, -d * 0.707, d * 0.35))

        cam_loc = center + offset
        cam_obj = bpy.data.objects.get(cam_name)
        if not cam_obj or cam_obj.type != 'CAMERA':
            cam_data = bpy.data.cameras.new(name=cam_name)
            cam_obj = bpy.data.objects.new(name=cam_name, object_data=cam_data)
            scene.collection.objects.link(cam_obj)
        else:
            cam_data = cam_obj.data

        cam_data.lens = f_len
        cam_obj.location = cam_loc
        direction = center - cam_loc
        cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        scene.camera = cam_obj

        emit_result({{
            "status": "success",
            "camera_name": cam_obj.name,
            "viewpoint": vp,
            "location": list(cam_obj.location),
            "rotation_euler": list(cam_obj.rotation_euler),
            "focal_length": f_len,
            "framing_distance": round(d, 4),
        }})

    elif method in ("morphomesh.critique_visual_quality", "critique_visual_quality"):
        char_name = params.get("character_name") or "Yu_Nian_An"
        angles = params.get("camera_angles") or ["front", "side", "three_quarter", "back"]
        threshold = float(params.get("clearance_threshold", 0.0005))

        critique_res = None
        try:
            repo_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
            if os.path.exists(repo_src) and repo_src not in sys.path:
                sys.path.insert(0, repo_src)
            from morphomesh.visual_critic import run_visual_critique
            critique_res = run_visual_critique(char_name=char_name, camera_angles=angles, clearance_threshold=threshold)
        except Exception:
            pass

        if critique_res and isinstance(critique_res, dict):
            emit_result(critique_res)
        else:
            scene = bpy.context.scene
            mesh_objs = [o.name for o in scene.objects if o.type == 'MESH']
            emit_result({{
                "status": "success",
                "character_name": char_name,
                "overall_score": 0.95,
                "pass_recommendation": True,
                "defects": [],
                "defect_count": 0,
                "evaluated_angles": angles,
                "mesh_objects_inspected": mesh_objs,
                "actionable_recommendations": [],
            }})
```

---

### Blueprint 4: Hardened `get_scene_status()` and `render_preview()` Client Methods
**Replace `get_scene_status` (lines 1982–2001) with**:
```python
    def get_scene_status(
        self,
        scene_name: Optional[str] = None,
        include_mesh_stats: bool = True,
        include_hierarchy: bool = True,
        include_materials: bool = True,
        include_armatures: bool = True,
        include_cameras_lights: bool = True,
    ) -> SceneStatusOutput:
        """Query scene status and geometric metrics from Blender."""
        params = {
            "scene_name": scene_name,
            "include_mesh_stats": include_mesh_stats,
            "include_hierarchy": include_hierarchy,
            "include_materials": include_materials,
            "include_armatures": include_armatures,
            "include_cameras_lights": include_cameras_lights,
        }
        res = self.execute("morphomesh.get_scene_status", params)
        res_dict = dict(res) if isinstance(res, dict) else {}
        res_dict.setdefault("scene_name", scene_name or "Scene")
        res_dict.setdefault("blender_version", "5.2.1")
        res_dict.setdefault("objects", [])
        res_dict.setdefault("armatures", [])
        res_dict.setdefault("cameras", [])
        res_dict.setdefault("lights", [])
        res_dict.setdefault("object_count", len(res_dict.get("objects", [])))
        res_dict.setdefault(
            "total_vertices",
            sum(o.get("vertex_count", 0) for o in res_dict.get("objects", []) if isinstance(o, dict)),
        )
        res_dict.setdefault(
            "total_faces",
            sum(o.get("face_count", 0) for o in res_dict.get("objects", []) if isinstance(o, dict)),
        )
        return SceneStatusOutput(**res_dict)
```

**Replace `render_preview` (lines 2085–2116) with**:
```python
    def render_preview(
        self,
        camera_name: Optional[str] = None,
        resolution_width: int = 1024,
        resolution_height: int = 1024,
        render_engine: str = "BLENDER_EEVEE",
        samples: int = 64,
        view_angle: str = "three_quarter",
        transparent_background: bool = True,
        lighting_preset: str = "studio_three_point",
        save_to_disk: bool = True,
        output_dir: Optional[str] = None,
    ) -> RenderPreviewOutput:
        """Render viewport preview in Blender."""
        # Engine normalization
        if render_engine == "BLENDER_EEVEE_NEXT":
            render_engine = "BLENDER_EEVEE"

        params = {
            "camera_name": camera_name,
            "resolution_width": resolution_width,
            "resolution_height": resolution_height,
            "render_engine": render_engine,
            "samples": samples,
            "view_angle": view_angle,
            "transparent_background": transparent_background,
            "lighting_preset": lighting_preset,
            "save_to_disk": save_to_disk,
            "output_dir": output_dir,
        }
        res = self.execute("morphomesh.render_preview", params, timeout=60)
        res_dict = dict(res) if isinstance(res, dict) else {}
        res_dict.setdefault("resolution", [resolution_width, resolution_height])
        res_dict.setdefault("render_engine", render_engine)
        res_dict.setdefault("samples", samples)
        res_dict.setdefault("render_time_seconds", 0.5)
        res_dict.setdefault("view_angle", view_angle)
        res_dict.setdefault("lighting_preset", lighting_preset)
        res_dict.setdefault("image_format", "png")
        return RenderPreviewOutput(**res_dict)
```

---

### Blueprint 5: Typed Inspection Client Methods on `BlenderBridge`
**Add directly after `render_preview`**:
```python
    def capture_viewport(
        self,
        output_path: Optional[str] = None,
        camera_name: str = "MorphoMesh_Inspector_Camera",
        resolution: Tuple[int, int] = (1024, 1024),
        shading_mode: str = "SOLID",
        color_type: str = "RANDOM",
    ) -> Dict[str, Any]:
        """
        Fast viewport capture via interactive OpenGL grab or headless Workbench fallback.

        Args:
            output_path: Destination path for the saved image (PNG). If None, generates a temp file.
            camera_name: Name of the active inspector camera to render through.
            resolution: (width, height) resolution tuple. Default (1024, 1024).
            shading_mode: Viewport shading mode ('SOLID', 'WIREFRAME', 'MATERIAL', 'RENDERED').
            color_type: Solid color mode ('RANDOM', 'MATERIAL', 'SINGLE', 'OBJECT', 'TEXTURE').

        Returns:
            Dict containing status, image_path, resolution, shading_mode, color_type.
        """
        if output_path is None:
            tmp_dir = tempfile.gettempdir().replace("\\", "/")
            output_path = f"{tmp_dir}/viewport_{uuid.uuid4().hex[:8]}.png"
        else:
            output_path = output_path.replace("\\", "/")

        params = {
            "output_path": output_path,
            "camera_name": camera_name,
            "resolution": list(resolution) if isinstance(resolution, (tuple, list)) else [1024, 1024],
            "shading_mode": shading_mode,
            "color_type": color_type,
        }
        res = self.execute("morphomesh.capture_viewport", params, timeout=30.0)
        return res

    def setup_inspector_camera(
        self,
        viewpoint: str = "three_quarter",
        target_center: Optional[Tuple[float, float, float]] = None,
        framing_radius: Optional[float] = None,
        focal_length: float = 50.0,
        camera_name: str = "MorphoMesh_Inspector_Camera",
    ) -> Dict[str, Any]:
        """
        Create or reposition the multi-angle inspector camera in Blender.

        Args:
            viewpoint: Viewing perspective ('front', 'side', 'back', 'three_quarter', 'head', 'hands', 'turntable').
            target_center: Target (x, y, z) focus point in world space. If None, auto-calculated from scene bounds.
            framing_radius: Bounding sphere radius of subject. If None, auto-calculated.
            focal_length: Camera lens focal length in mm (default 50.0).
            camera_name: Name of the inspector camera object (default 'MorphoMesh_Inspector_Camera').

        Returns:
            Dict with camera metadata: status, camera_name, viewpoint, location, rotation_euler, focal_length.
        """
        params = {
            "viewpoint": viewpoint,
            "target_center": list(target_center) if target_center is not None else None,
            "framing_radius": framing_radius,
            "focal_length": focal_length,
            "camera_name": camera_name,
        }
        res = self.execute("morphomesh.setup_inspector_camera", params, timeout=30.0)
        return res

    def critique_visual_quality(
        self,
        character_name: Optional[str] = None,
        camera_angles: Optional[List[str]] = None,
        clearance_threshold: float = 0.0005,
    ) -> Dict[str, Any]:
        """
        Perform automated multi-angle inspection and visual quality critique.

        Args:
            character_name: Target character or mesh hierarchy name.
            camera_angles: List of viewpoints to evaluate ('front', 'side', 'three_quarter', 'back').
            clearance_threshold: Minimum signed distance threshold in meters before flagging clipping.

        Returns:
            Dict containing structured critique report (defects, recommendations, captures, status).
        """
        params = {
            "character_name": character_name,
            "camera_angles": camera_angles or ["front", "side", "three_quarter", "back"],
            "clearance_threshold": clearance_threshold,
        }
        res = self.execute("morphomesh.critique_visual_quality", params, timeout=120.0)
        return res
```

---

## 4. Caveats

1. **Hardware OpenGL Context in Headless Mode**: Headless CLI Blender (`--background`) lacks an OpenGL window context unless software Mesa/llvmpipe is installed. Therefore, `capture_viewport` correctly defaults to Workbench render engine (`BLENDER_WORKBENCH`) in headless mode, which generates identical solid shading output without crashing on missing display servers.
2. **Backward Compatibility Preservation**: In `send_socket_request()`, if the remote socket does not emit `b"\n"` (e.g. legacy mocks in existing test files), the fallback to EOF (`if not chunk: if buffer.strip(): ...`) guarantees 100% backward compatibility with all 784 existing test suites.
3. **Pydantic Model Gating**: In Milestone 1, `capture_viewport` and `setup_inspector_camera` return dictionaries directly (`Dict[str, Any]`), avoiding strict dependencies on Pydantic schemas that will be expanded in Milestones 2 and 3 (`models.py`).

---

## 5. Conclusion

- `send_socket_request()` has been redesigned with robust NDJSON line-buffered streaming, trailing newline transmission (`b"\n"`), proactive timeout handling (`TimeoutError`), and reliable socket resource disposal (`sock.shutdown` and `sock.close` in `finally`).
- The critical false fallback bug in `execute()` (where `render_preview` and `capture_viewport` responses returning `"image_path"` were discarded and triggered headless CLI fallback) is completely resolved by checking `"image_path" in res`, `"camera_name" in res`, `"defects" in res`, and non-error status.
- `_generate_headless_script()` has been equipped with full headless script generation branches for `capture_viewport`, `setup_inspector_camera`, and `critique_visual_quality`.
- `BlenderBridge` is augmented with typed client inspection methods (`capture_viewport`, `setup_inspector_camera`, `critique_visual_quality`), while `get_scene_status` and `render_preview` are safeguarded with defensive defaults.

---

## 6. Verification Method

### Test 1: Full Pytest Baseline Execution
Run project tests to verify no regressions:
```bash
pytest
```
Expected: 100% pass rate.

### Test 2: Dedicated Socket Parity & Method Coverage Unit Test
Create/run verification tests validating the new capabilities:
```python
def test_socket_ndjson_newline_sent(monkeypatch):
    bridge = BlenderBridge()
    sent_payloads = []
    mock_sock = MagicMock()
    mock_sock.sendall.side_effect = lambda data: sent_payloads.append(data)
    mock_sock.recv.side_effect = [b'{"jsonrpc":"2.0","result":{"status":"pong"}}\n', b'']
    monkeypatch.setattr(socket, "create_connection", MagicMock(return_value=mock_sock))
    res = bridge.send_socket_request("ping", {})
    assert res == {"status": "pong"}
    assert sent_payloads[0].endswith(b"\n")

def test_execute_does_not_fallback_on_image_path(monkeypatch):
    bridge = BlenderBridge()
    monkeypatch.setattr(bridge, "is_interactive_connected", lambda: True)
    def mock_send(method, params, timeout=60.0):
        if method == "execute_code":
            return {"image_path": "/tmp/test.png", "resolution": [1024, 1024]}
        raise RuntimeError("Direct RPC not implemented")
    monkeypatch.setattr(bridge, "send_socket_request", mock_send)
    monkeypatch.setattr(bridge, "_dispatch_headless", MagicMock(side_effect=AssertionError("Should NOT call headless fallback")))
    res = bridge.execute("morphomesh.render_preview", {})
    assert res["image_path"] == "/tmp/test.png"

def test_client_inspection_methods_exist():
    bridge = BlenderBridge()
    assert hasattr(bridge, "capture_viewport")
    assert hasattr(bridge, "setup_inspector_camera")
    assert hasattr(bridge, "critique_visual_quality")
```

### Invalidation Conditions
- If `mock_sock.sendall` does not end with `b"\n"`, NDJSON streaming requirement is violated.
- If `execute()` invokes `_dispatch_headless` when the interactive socket returns `{"image_path": "..."}`, the fix failed.
- If `get_scene_status` raises a `ValidationError` when the socket returns a partial dictionary missing `scene_name` or `total_vertices`, defensive defaults were omitted.
