# Milestone M2 Iteration 2 - 2 Investigation & Remediation Blueprint
## Test De-Certification, Hierarchy Bounds & Fallback Remediation

**Explorer**: Explorer M2 Iteration 2 - 2 (Test De-Certification & Fallback Remediation Explorer)  
**Parent Orchestrator ID**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Date**: 2026-09-07T05:05:00Z  
**Target Files**:
- `tests/test_inspector_camera.py`
- `tests/test_multiview_rendering.py`
- `tests/test_adversarial_viewport_capture.py`
- `src/morphomesh/camera_rig.py`
**Handoff Type**: Hard  

---

## 1. Observation

### 1.1 Verbatim Code Audit: Self-Referential Tests in `tests/test_inspector_camera.py`

1. **Bypassing `cam_rot` in `test_look_at_forward_ray_hits_target_center` (Lines 322-341)**:
   ```python
   # tests/test_inspector_camera.py lines 334-341:
   for name, (azim, elev) in viewpoints.items():
       cam_pos, cam_rot = calculate_spherical_camera_position(target_center, d, azim, elev)
       R, dist = ref_compute_lookat_matrix(cam_pos, target_center)
       forward_ray = R @ np.array([0.0, 0.0, -1.0])
       reconstructed_target = np.array(cam_pos) + dist * forward_ray

       assert np.allclose(reconstructed_target, target_center, atol=1e-5), f"Ray missed target for {name}"
   ```
   - *Observation*: `cam_rot` returned by `calculate_spherical_camera_position` is completely discarded. Instead, the test invokes `ref_compute_lookat_matrix` (defined locally in the test file on lines 92-114).
   - *Empirical Verification of Current Implementation Failure*:
     Executing `calculate_spherical_camera_position` with `camera_rig.py`'s current pure-Python implementation reveals severe aiming errors when testing the ray derived from `cam_rot`:
     - Viewpoint `front`: Ray hits target center (diff: $0.0\text{m}$).
     - Viewpoint `side`: `cam_rot = [90.0°, 0.0°, 90.0°]`. Forward ray lands at `[4.5, 3.8, 1.1]`, missing target `[0.5, -0.2, 1.1]` by **$5.657\text{m}$**.
     - Viewpoint `back`: `cam_rot = [90.0°, 0.0°, 180.0°]`. Forward ray lands at `[0.5, 7.8, 1.1]`, pointing $180^\circ$ away into the void, missing target by **$8.000\text{m}$**.
     - Viewpoint `three_quarter`: `cam_rot = [105.0°, 0.0°, 45.0°]`. Forward ray misses target by **$3.610\text{m}$**.
   - *Conclusion on Finding*: The test passed with `exit code 0` only because it tested its own local `ref_compute_lookat_matrix` rather than the code under test.

2. **Self-Testing Mock in `test_rotation_matrix_orthonormality_and_up_vector` (Lines 343-356)**:
   ```python
   # tests/test_inspector_camera.py lines 343-356:
   def test_rotation_matrix_orthonormality_and_up_vector(self):
       cam_pos = (2.5, -2.5, 1.8)
       target = (0.0, 0.0, 0.9)
       R, _ = ref_compute_lookat_matrix(cam_pos, target)

       # Orthonormality: R^T * R = I
       ident = R.T @ R
       assert np.allclose(ident, np.eye(3), atol=1e-6)
       assert np.linalg.det(R) == pytest.approx(1.0, abs=1e-6)
       cam_up = R @ np.array([0.0, 1.0, 0.0])
       assert cam_up[2] > 0.0
   ```
   - *Observation*: This test does not import or execute any rotation matrix logic from `camera_rig.py`. It only asserts properties of `ref_compute_lookat_matrix`.

3. **Absence of Hierarchy Bounds Traversal in `camera_rig.py`**:
   - *Observation*: `calculate_hierarchy_bounds` does not exist in `src/morphomesh/camera_rig.py` (only `calculate_character_bounds` exists).
   - In `calculate_character_bounds` (lines 268-294 for mocks, lines 327-343 for Blender), objects of type `EMPTY` or `ARMATURE` are ignored (`getattr(obj, "type", "") == 'MESH'`). Passing an Empty or Armature root object causes `resolved_objs` to be empty, triggering the fallback box `[-0.5, 0.5] x [-0.5, 0.5] x [0.0, 2.0]`. Neither `obj.children` nor `obj.children_recursive` is traversed.

---

### 1.2 Verbatim Code Audit: Self-Referential Mocks in `tests/test_multiview_rendering.py`

1. **Self-Testing Mocks in `TestDualModeExecution` (Lines 220-265)**:
   ```python
   # tests/test_multiview_rendering.py lines 223-232:
   def test_interactive_opengl_path_simulation(self):
       mock_context = MagicMock()
       mock_context.temp_override = MagicMock()
       mock_ops = MagicMock()

       mock_ops.render.opengl = MagicMock(return_value={'FINISHED'})
       res = mock_ops.render.opengl(write_still=True)
       assert res == {'FINISHED'}
       mock_ops.render.opengl.assert_called_once_with(write_still=True)
   ```
   - *Observation*: Lines 223-265 instantiate `MagicMock` instances in the test function body, invoke methods directly on those local mocks, and assert that the mocks were called. Neither `capture_viewport_image()` nor any function in `morphomesh` is invoked.

2. **Self-Testing Condition in `test_missing_file_base64_grace` (Lines 302-310)**:
   ```python
   # tests/test_multiview_rendering.py lines 302-310:
   def test_missing_file_base64_grace(self):
       ghost_path = "/non_existent_dir/ghost_render.png"
       b64_str = None
       if os.path.isfile(ghost_path):
           with open(ghost_path, "rb") as f:
               b64_str = base64.b64encode(f.read()).decode("utf-8")
       assert b64_str is None
   ```
   - *Observation*: The test tests Python's built-in `os.path.isfile` and `if` statement. `camera_rig.py` had no standalone `encode_image_to_base64()` function, forcing the test to test inline logic.

---

### 1.3 Verbatim Code Audit: Corrupted Fallback PNG in `src/morphomesh/camera_rig.py`

1. **Truncated 29-Byte Header Fallback (Lines 703-704 and 838-839)**:
   ```python
   # src/morphomesh/camera_rig.py lines 703-704 & 838-839:
   except Exception:
       with open(clean_path, "wb") as f:
           f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x04\x00\x00\x00\x04\x00\x08\x02\x00\x00\x00")
   ```
   - *Observation*: The byte sequence length is exactly 29 bytes:
     - 8 bytes: PNG signature `\x89PNG\r\n\x1a\n`
     - 4 bytes: IHDR length `\x00\x00\x00\r` (13)
     - 4 bytes: Chunk type `IHDR`
     - 8 bytes: Dimensions 1024x1024 (`\x00\x00\x04\x00\x00\x00\x04\x00`)
     - 5 bytes: Bit depth, color type, compression, filter, interlace (`\x08\x02\x00\x00\x00`)
     - **Missing**: 4-byte IHDR CRC, IDAT chunk (compressed pixel payload + CRC), and IEND chunk (0-length chunk + CRC).
   - *Empirical Verification*: Reading this file with PIL raises `PIL.UnidentifiedImageError: cannot identify image file`.
   - *Adversarial Test*: `tests/test_adversarial_viewport_capture.py` line 344 (`test_corrupted_fallback_png_header_audit`) explicitly asserts that this file is 29 bytes and that PIL raises an exception.

---

## 2. Logic Chain

1. **Integrity & Rigor Mandate**:
   - In automated testing, a unit test must execute and assert properties of the target production codebase, not a local shadow implementation or a mock that only calls itself.
   - When tests bypass the target codebase, critical production bugs (such as an inverted camera pitch of $30^\circ$ to $176^\circ$, missing hierarchy resolution, or broken fallback files) remain hidden behind false-positive "100% PASS" test runs.

2. **Remediation of `test_look_at_forward_ray_hits_target_center`**:
   - `calculate_spherical_camera_position(center, d, azim, elev)` returns `(cam_pos, cam_rot)`.
   - The camera's local coordinate system defines optical forward as $-Z = [0, 0, -1]^\top$.
   - When the camera orientation is represented by rotation matrix $R(\text{cam\_rot})$, the world-space optical forward ray is $\vec{v}_{\text{fwd}} = R \cdot [0, 0, -1]^\top$.
   - The ray starting at $\vec{P}_{\text{cam}}$ and traversing distance $d$ reaches $\vec{P}_{\text{target\_rec}} = \vec{P}_{\text{cam}} + d \cdot \vec{v}_{\text{fwd}}$.
   - Testing that $\|\vec{P}_{\text{target\_rec}} - \vec{P}_{\text{target}}\| < 10^{-4}$ directly tests the mathematical accuracy of `cam_rot` produced by `camera_rig.py`.

3. **Remediation of `TestDualModeExecution`**:
   - `capture_viewport_image()` in `camera_rig.py` implements the dual-mode logic:
     - Branch 1: If `is_headless=False` and a `VIEW_3D` area is found, it uses `bpy.context.temp_override` and calls `bpy.ops.render.opengl(write_still=True)`.
     - Branch 2: If OpenGL fails or `is_headless=True`, it falls back to `bpy.ops.render.render(write_still=True)` using the Workbench engine.
   - By patching `camera_rig.HAS_BPY = True` and setting `camera_rig.bpy` with configured mock context, spaces, and ops, tests can call `capture_viewport_image()` directly.
   - This asserts that `capture_viewport_image()` actually executes the intended OpenGL or Workbench pathways and handles exceptions cleanly.

4. **Remediation of Base64 Grace & Missing File Handling**:
   - Extracting `encode_image_to_base64(image_path: Optional[str]) -> Optional[str]` as a first-class function in `camera_rig.py` centralizes base64 encoding across single-image capture, multi-angle batch inspection, and FastMCP server responses.
   - `test_missing_file_base64_grace` now calls `encode_image_to_base64("/non_existent/ghost.png")` directly, testing the actual function rather than a local Python `if` statement.

5. **Remediation of Corrupted 29-Byte PNG Fallback**:
   - A valid standard PNG requires: Signature (8 bytes) + IHDR chunk with CRC (25 bytes) + IDAT chunk with CRC (25 bytes) + IEND chunk with CRC (12 bytes) = 70 bytes.
   - A transparent 1x1 RGBA PNG has pixel value `(0, 0, 0, 0)`. Its zlib-deflated scanline (filter byte 0 + RGBA 0 0 0 0) compresses into an IDAT payload of 13 bytes.
   - Exact 70-byte stream:
     `b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x60\x60\x60\x60\x00\x00\x00\x05\x00\x01\xa5\xf6E@\x00\x00\x00\x00IEND\xaeB\x60\x82"`
   - This 70-byte stream is completely valid, opens cleanly in PIL without warnings, and satisfies image validation tools.

---

## 3. Caveats

1. **Dependency on Rotation Matrix Correction**:
   - The de-certified `test_look_at_forward_ray_hits_target_center` will fail if executed against the unpatched `camera_rig.py` because `camera_rig.py` currently has the $30^\circ - 176^\circ$ aiming error. Worker M2 must apply the companion mathematical fix for `Vector.to_track_quat`, `Euler.to_matrix`, and `calculate_spherical_camera_position` in tandem.
2. **Blender vs. Non-Blender Mathutils**:
   - In environments without `mathutils` (e.g. standard virtualenv running pytest), `cam_rot` is an instance of `camera_rig.Euler`. `camera_rig.Euler.to_matrix()` must implement the standard Blender XYZ convention $R = R_z(\theta_z) \cdot R_y(\theta_y) \cdot R_x(\theta_x)$.

---

## 4. Conclusion & Precise Blueprints

### Blueprint 1: De-Certifying `tests/test_inspector_camera.py`

#### 1.1 Replace `test_look_at_forward_ray_hits_target_center` (Lines 322-341)
Replace the self-referential test with:
```python
    def test_look_at_forward_ray_hits_target_center(self):
        """For all canonical viewpoints, forward ray R(cam_rot) * [0, 0, -1] hits target_center within 1e-4."""
        target_center = (0.5, -0.2, 1.1)
        d = 4.0

        viewpoints = {
            "front": (0.0, 0.0),
            "side": (90.0, 0.0),
            "back": (180.0, 0.0),
            "three_quarter": (45.0, 15.0),
            "top": (0.0, 88.0),
        }

        for name, (azim, elev) in viewpoints.items():
            cam_pos, cam_rot = calculate_spherical_camera_position(target_center, d, azim, elev)

            # Derive rotation matrix R directly from cam_rot returned by calculate_spherical_camera_position
            if hasattr(cam_rot, "to_matrix"):
                R = np.array(cam_rot.to_matrix())[:3, :3]
            else:
                rx, ry, rz = float(cam_rot[0]), float(cam_rot[1]), float(cam_rot[2])
                cx, sx = math.cos(rx), math.sin(rx)
                cy, sy = math.cos(ry), math.sin(ry)
                cz, sz = math.cos(rz), math.sin(rz)
                R = np.array([
                    [cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
                    [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
                    [-sy,     cy * sx,                cy * cx],
                ])

            # In camera frame, optical forward is (0, 0, -1)
            forward_ray = R @ np.array([0.0, 0.0, -1.0])
            reconstructed_target = np.array(cam_pos) + d * forward_ray

            assert np.allclose(reconstructed_target, target_center, atol=1e-4), (
                f"Forward ray from cam_rot missed target for {name}: "
                f"expected {target_center}, got {reconstructed_target.tolist()}"
            )
```

#### 1.2 Replace `test_rotation_matrix_orthonormality_and_up_vector` (Lines 343-356)
Replace with direct verification of the matrix produced by `camera_rig`:
```python
    def test_rotation_matrix_orthonormality_and_up_vector(self):
        """Rotation matrix produced by camera_rig must be orthonormal with positive camera up vector."""
        target_center = (0.0, 0.0, 0.9)
        d = 4.0

        for azim, elev in [(0.0, 0.0), (45.0, 15.0), (90.0, 0.0), (180.0, 0.0)]:
            cam_pos, cam_rot = calculate_spherical_camera_position(target_center, d, azim, elev)
            assert hasattr(cam_rot, "to_matrix"), "cam_rot must provide to_matrix()"
            R = np.array(cam_rot.to_matrix())[:3, :3]

            # Orthonormality: R^T * R = I
            ident = R.T @ R
            assert np.allclose(ident, np.eye(3), atol=1e-5), f"Matrix not orthonormal for ({azim}, {elev})"

            # Proper rotation: det(R) = +1 (special orthogonal SO(3))
            assert np.linalg.det(R) == pytest.approx(1.0, abs=1e-5), f"Matrix det != 1 for ({azim}, {elev})"

            # Camera up vector: in camera frame up is (0, 1, 0)
            cam_up = R @ np.array([0.0, 1.0, 0.0])
            # For non-inverted viewpoints (elev < 80), camera up vector must have positive Z component
            if elev < 80.0:
                assert cam_up[2] > 0.0, f"Camera up vector inverted for ({azim}, {elev}): Z={cam_up[2]}"
```

#### 1.3 Add Hierarchy Bounds Test Fixtures & Unit Tests
In `tests/test_inspector_camera.py`:
Add mock parent classes:
```python
class MockEmptyObject:
    """Simulates Blender Empty parent object."""
    def __init__(
        self,
        name: str = "Character_Root",
        children: Optional[List[Any]] = None,
        matrix_world: Optional[np.ndarray] = None,
    ):
        self.name = name
        self.type = 'EMPTY'
        self.children = children or []
        self.children_recursive = list(self.children)
        self.matrix_world = matrix_world if matrix_world is not None else np.eye(4)
        self.bound_box = None


class MockArmatureObject:
    """Simulates Blender Armature parent object."""
    def __init__(
        self,
        name: str = "Character_Rig",
        children: Optional[List[Any]] = None,
        matrix_world: Optional[np.ndarray] = None,
    ):
        self.name = name
        self.type = 'ARMATURE'
        self.children = children or []
        self.children_recursive = list(self.children)
        self.matrix_world = matrix_world if matrix_world is not None else np.eye(4)
        self.bound_box = None
```
Add new unit tests in `TestBoundingBoxAndSphereSolver`:
```python
    def test_calculate_hierarchy_bounds_empty_parent_with_child_meshes(self):
        """calculate_hierarchy_bounds must traverse Empty parent to aggregate child meshes."""
        head = MockMeshObject("Head", (-0.2, -0.2, 1.4), (0.2, 0.2, 1.8))
        torso = MockMeshObject("Torso", (-0.3, -0.2, 0.8), (0.3, 0.2, 1.4))
        legs = MockMeshObject("Legs", (-0.25, -0.15, 0.0), (0.25, 0.15, 0.8))

        root_empty = MockEmptyObject("Root_Empty", children=[head, torso, legs])

        center, radius, min_corner, max_corner = calculate_hierarchy_bounds([root_empty])

        assert min_corner[0] == pytest.approx(-0.3, abs=1e-4)
        assert min_corner[1] == pytest.approx(-0.2, abs=1e-4)
        assert min_corner[2] == pytest.approx(0.0, abs=1e-4)

        assert max_corner[0] == pytest.approx(0.3, abs=1e-4)
        assert max_corner[1] == pytest.approx(0.2, abs=1e-4)
        assert max_corner[2] == pytest.approx(1.8, abs=1e-4)

        assert center[0] == pytest.approx(0.0, abs=1e-4)
        assert center[1] == pytest.approx(0.0, abs=1e-4)
        assert center[2] == pytest.approx(0.9, abs=1e-4)

        expected_radius = math.sqrt(0.6**2 + 0.4**2 + 1.8**2) / 2.0
        assert radius == pytest.approx(expected_radius, rel=1e-4)

    def test_calculate_hierarchy_bounds_armature_parent_nested(self):
        """calculate_hierarchy_bounds must handle nested Armature -> Empty -> Mesh hierarchies."""
        mesh_a = MockMeshObject("Mesh_A", (-0.5, -0.5, 0.0), (0.0, 0.0, 1.0))
        mesh_b = MockMeshObject("Mesh_B", (0.0, 0.0, 1.0), (0.5, 0.5, 2.0))
        sub_empty = MockEmptyObject("Sub_Empty", children=[mesh_b])
        rig_parent = MockArmatureObject("Rig_Root", children=[mesh_a, sub_empty])

        center, radius, min_c, max_c = calculate_hierarchy_bounds([rig_parent])

        assert min_c[0] == pytest.approx(-0.5, abs=1e-4)
        assert max_c[0] == pytest.approx(0.5, abs=1e-4)
        assert min_c[2] == pytest.approx(0.0, abs=1e-4)
        assert max_c[2] == pytest.approx(2.0, abs=1e-4)
        assert center[2] == pytest.approx(1.0, abs=1e-4)

    def test_calculate_hierarchy_bounds_alias_compatibility(self):
        """calculate_character_bounds must be an alias of calculate_hierarchy_bounds."""
        assert calculate_character_bounds is calculate_hierarchy_bounds
```

---

### Blueprint 2: De-Certifying `tests/test_multiview_rendering.py`

#### 2.1 Replace `TestDualModeExecution` (Lines 220-265)
Replace the self-testing mock methods with direct calls to `capture_viewport_image()`:
```python
class TestDualModeExecution:
    """Validates interactive OpenGL grab vs headless Workbench render fallback."""

    def test_interactive_opengl_path_simulation(self, temp_render_dir):
        """Interactive mode utilizes VIEW_3D temp_override and opengl render."""
        import morphomesh.camera_rig as cr

        out_file = os.path.join(temp_render_dir, "opengl_live.png")
        mock_bpy = MagicMock()
        mock_bpy.app.background = False

        # Setup VIEW_3D area and window
        mock_area = MagicMock()
        mock_area.type = 'VIEW_3D'
        mock_region = MagicMock()
        mock_region.type = 'WINDOW'
        mock_area.regions = [mock_region]
        mock_space = MagicMock()
        mock_area.spaces.active = mock_space
        mock_window = MagicMock()
        mock_window.screen.areas = [mock_area]
        mock_bpy.context.window_manager.windows = [mock_window]

        mock_scene = MagicMock()
        mock_scene.render.engine = 'BLENDER_EEVEE'
        mock_bpy.context.scene = mock_scene
        mock_bpy.ops.render.opengl = MagicMock(return_value={'FINISHED'})
        mock_bpy.ops.render.render = MagicMock(return_value={'FINISHED'})

        with patch.object(cr, 'HAS_BPY', True), patch.object(cr, 'bpy', mock_bpy):
            res_path = cr.capture_viewport_image(output_path=out_file, scene=mock_scene)
            assert os.path.isfile(res_path)
            mock_bpy.ops.render.opengl.assert_called_once_with(write_still=True)
            mock_bpy.ops.render.render.assert_not_called()

    def test_headless_workbench_render_fallback(self, temp_render_dir):
        """Headless mode sets engine to BLENDER_WORKBENCH and renders still."""
        import morphomesh.camera_rig as cr

        out_file = os.path.join(temp_render_dir, "workbench_fallback.png")
        mock_bpy = MagicMock()
        mock_bpy.app.background = True  # Headless mode
        mock_scene = MagicMock()
        mock_scene.render.engine = 'CYCLES'
        mock_bpy.context.scene = mock_scene
        mock_bpy.ops.render.render = MagicMock(return_value={'FINISHED'})
        mock_bpy.ops.render.opengl = MagicMock()

        with patch.object(cr, 'HAS_BPY', True), patch.object(cr, 'bpy', mock_bpy):
            res_path = cr.capture_viewport_image(output_path=out_file, scene=mock_scene)
            assert os.path.isfile(res_path)
            mock_bpy.ops.render.render.assert_called_once_with(write_still=True)
            mock_bpy.ops.render.opengl.assert_not_called()
            assert mock_scene.render.engine == 'CYCLES'  # Restored

    def test_opengl_failure_triggers_workbench_fallback(self, temp_render_dir):
        """When OpenGL throws background context error, fallback to Workbench succeeds."""
        import morphomesh.camera_rig as cr

        out_file = os.path.join(temp_render_dir, "opengl_fail_recovery.png")
        mock_bpy = MagicMock()
        mock_bpy.app.background = False

        mock_area = MagicMock()
        mock_area.type = 'VIEW_3D'
        mock_region = MagicMock()
        mock_region.type = 'WINDOW'
        mock_area.regions = [mock_region]
        mock_area.spaces.active = MagicMock()
        mock_window = MagicMock()
        mock_window.screen.areas = [mock_area]
        mock_bpy.context.window_manager.windows = [mock_window]

        mock_scene = MagicMock()
        mock_scene.render.engine = 'BLENDER_EEVEE'
        mock_bpy.context.scene = mock_scene

        # OpenGL fails, Workbench succeeds
        mock_bpy.ops.render.opengl.side_effect = RuntimeError("Cannot use OpenGL in background mode")
        mock_bpy.ops.render.render = MagicMock(return_value={'FINISHED'})

        with patch.object(cr, 'HAS_BPY', True), patch.object(cr, 'bpy', mock_bpy):
            res_path = cr.capture_viewport_image(output_path=out_file, scene=mock_scene)
            assert os.path.isfile(res_path)
            mock_bpy.ops.render.opengl.assert_called_once_with(write_still=True)
            mock_bpy.ops.render.render.assert_called_once_with(write_still=True)
            assert mock_scene.render.engine == 'BLENDER_EEVEE'  # Restored
```

#### 2.2 Replace `test_missing_file_base64_grace` (Lines 302-310)
Replace the local `if` statement check with direct calls to `camera_rig.encode_image_to_base64`:
```python
    def test_missing_file_base64_grace(self):
        """Missing image file returns None for base64 without throwing FileNotFoundError."""
        from morphomesh.camera_rig import encode_image_to_base64
        ghost_path = "/non_existent_dir/ghost_render.png"
        b64_str = encode_image_to_base64(ghost_path)
        assert b64_str is None

    def test_valid_file_base64_encoding_utility(self, sample_test_png):
        """Valid image file returns base64 string matching file contents."""
        from morphomesh.camera_rig import encode_image_to_base64
        b64_str = encode_image_to_base64(sample_test_png)
        assert b64_str is not None
        with open(sample_test_png, "rb") as f:
            expected_bytes = f.read()
        assert base64.b64decode(b64_str) == expected_bytes
```

---

### Blueprint 3: Updates in `src/morphomesh/camera_rig.py`

#### 3.1 Expose `encode_image_to_base64` Utility Function
Add to `src/morphomesh/camera_rig.py`:
```python
def encode_image_to_base64(image_path: Optional[str]) -> Optional[str]:
    """
    Safely encode an image file to a base64 UTF-8 string.

    Args:
        image_path: Absolute or relative path to the image file.

    Returns:
        Base64-encoded string if file exists and is readable, None otherwise.
    """
    if not image_path or not os.path.isfile(image_path):
        return None
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to encode image {image_path} to base64: {e}")
        return None
```
In `capture_multi_angle_inspection` line 896-903, replace with:
```python
        b64_str = encode_image_to_base64(captured_path) if include_base64 else None
```

#### 3.2 Define `FALLBACK_PNG_BYTES` and Replace Lines 703-704 & 838-839
Add module constant:
```python
# Complete, valid 70-byte 1x1 RGBA transparent PNG byte stream (IHDR, IDAT, IEND with valid CRCs)
FALLBACK_PNG_BYTES: bytes = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\x60\x60\x60\x60\x00\x00\x00\x05\x00\x01\xa5\xf6E@"
    b"\x00\x00\x00\x00IEND\xaeB\x60\x82"
)
```
In `capture_viewport_image()` line 702-705:
```python
        except Exception:
            with open(clean_path, "wb") as f:
                f.write(FALLBACK_PNG_BYTES)
```
In `capture_viewport_image()` line 837-840:
```python
        except Exception:
            with open(clean_path, "wb") as f:
                f.write(FALLBACK_PNG_BYTES)
```

#### 3.3 Define `calculate_hierarchy_bounds` with Recursive Mesh Traversal
In `src/morphomesh/camera_rig.py`:
```python
def _collect_hierarchy_meshes(items: List[Any], scene: Optional[Any] = None) -> List[Any]:
    """Recursively collect all MESH objects from items and their children."""
    meshes = []
    visited = set()

    def _traverse(obj: Any):
        if obj is None or id(obj) in visited:
            return
        visited.add(id(obj))

        obj_type = getattr(obj, "type", "")
        if obj_type == 'MESH' and getattr(obj, "bound_box", None) is not None:
            meshes.append(obj)

        # Traverse direct children
        children = getattr(obj, "children", [])
        if callable(children):
            children = children()
        for child in children:
            _traverse(child)

        # Traverse children_recursive if present
        if hasattr(obj, "children_recursive"):
            rec_children = obj.children_recursive
            if callable(rec_children):
                rec_children = rec_children()
            for child in rec_children:
                _traverse(child)

    for item in items:
        if isinstance(item, str):
            if HAS_BPY and bpy and hasattr(bpy, "data"):
                bl_obj = bpy.data.objects.get(item)
                if bl_obj:
                    _traverse(bl_obj)
        else:
            _traverse(item)

    return meshes


def calculate_hierarchy_bounds(
    mesh_objects: Optional[List[Union[str, Any]]] = None,
    scene: Optional[Any] = None,
    use_evaluated_depsgraph: bool = True,
) -> Tuple[Any, float, Any, Any]:
    """
    Calculate world-space AABB and circumscribing bounding sphere across multi-mesh hierarchy.
    Recursively inspects parent Empties, Armatures, and collections to aggregate all child meshes.
    """
    VecClass = mathutils.Vector

    # Check if we have mock objects passed directly in non-Blender testing
    if mesh_objects and not (HAS_BPY and bpy is not None):
        resolved_mocks = _collect_hierarchy_meshes(mesh_objects)
        min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
        max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
        found_any = False

        for item in resolved_mocks:
            bbox = getattr(item, "bound_box", None)
            mat = getattr(item, "matrix_world", None)
            if bbox:
                found_any = True
                for corner in bbox:
                    c_vec = VecClass(corner)
                    if mat is not None:
                        try:
                            if hasattr(mat, "shape") and mat.shape == (4, 4):
                                v4 = [c_vec[0], c_vec[1], c_vec[2], 1.0]
                                wc = mat @ v4
                            else:
                                wc = mat @ c_vec
                        except Exception:
                            v4 = [c_vec[0], c_vec[1], c_vec[2], 1.0]
                            wc = mat @ v4
                    else:
                        wc = c_vec
                    min_x = min(min_x, float(wc[0]))
                    min_y = min(min_y, float(wc[1]))
                    min_z = min(min_z, float(wc[2]))
                    max_x = max(max_x, float(wc[0]))
                    max_y = max(max_y, float(wc[1]))
                    max_z = max(max_z, float(wc[2]))

        if found_any and min_x != float('inf'):
            min_pt = VecClass((min_x, min_y, min_z))
            max_pt = VecClass((max_x, max_y, max_z))
            center = (min_pt + max_pt) / 2.0
            radius = math.sqrt((max_x - min_x) ** 2 + (max_y - min_y) ** 2 + (max_z - min_z) ** 2) / 2.0
            return center, max(radius, 0.01), min_pt, max_pt

        # Degenerate empty fallback
        min_pt = VecClass((-0.5, -0.5, 0.0))
        max_pt = VecClass((0.5, 0.5, 2.0))
        center = VecClass((0.0, 0.0, 1.0))
        radius = 1.0
        return center, radius, min_pt, max_pt

    if not HAS_BPY or bpy is None:
        min_pt = VecClass((-0.5, -0.5, 0.0))
        max_pt = VecClass((0.5, 0.5, 2.0))
        center = VecClass((0.0, 0.0, 1.0))
        radius = 1.0
        return center, radius, min_pt, max_pt

    if scene is None:
        scene = getattr(bpy.context, "scene", None)

    depsgraph = None
    if use_evaluated_depsgraph and hasattr(bpy.context, "evaluated_depsgraph_get"):
        try:
            depsgraph = bpy.context.evaluated_depsgraph_get()
        except Exception as e:
            logger.warning(f"Could not acquire evaluated depsgraph: {e}")

    # Resolve target candidate mesh objects across hierarchies
    if mesh_objects:
        resolved_objs = _collect_hierarchy_meshes(mesh_objects, scene=scene)
    elif scene:
        # Ignore cameras, lights, empties, and helper inspection objects
        resolved_objs = [
            o for o in getattr(scene, "objects", [])
            if getattr(o, "type", "") == 'MESH'
            and not getattr(o, "name", "").startswith(("MorphoMesh_Inspector", "Studio_Light", "Camera_", "WGT-", "helper_"))
            and not getattr(o, "hide_viewport", False)
        ]
    else:
        resolved_objs = []

    min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
    max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')

    for o in resolved_objs:
        target_obj = o
        if depsgraph and hasattr(o, "evaluated_get"):
            try:
                target_obj = o.evaluated_get(depsgraph)
            except Exception:
                target_obj = o

        bbox = getattr(target_obj, "bound_box", None)
        mat = getattr(target_obj, "matrix_world", None)
        if bbox:
            for corner in bbox:
                try:
                    c_vec = VecClass(corner)
                    wc = mat @ c_vec if mat is not None else c_vec
                    min_x = min(min_x, wc[0])
                    min_y = min(min_y, wc[1])
                    min_z = min(min_z, wc[2])
                    max_x = max(max_x, wc[0])
                    max_y = max(max_y, wc[1])
                    max_z = max(max_z, wc[2])
                except Exception:
                    pass

    if min_x == float('inf'):
        # Empty scene fallback: default unit character at origin
        min_pt = VecClass((-0.5, -0.5, 0.0))
        max_pt = VecClass((0.5, 0.5, 2.0))
        center = VecClass((0.0, 0.0, 1.0))
        radius = 1.0
        return center, radius, min_pt, max_pt

    min_pt = VecClass((min_x, min_y, min_z))
    max_pt = VecClass((max_x, max_y, max_z))
    center = (min_pt + max_pt) / 2.0
    radius = math.sqrt((max_x - min_x) ** 2 + (max_y - min_y) ** 2 + (max_z - min_z) ** 2) / 2.0
    return center, max(radius, 0.01), min_pt, max_pt

# Maintain backwards compatibility
calculate_character_bounds = calculate_hierarchy_bounds
```

---

### Blueprint 4: Update `tests/test_adversarial_viewport_capture.py`

In `tests/test_adversarial_viewport_capture.py` lines 344-366, update the audit test to verify that the remediated fallback produces the valid 70-byte PNG passing PIL verification:
```python
    def test_valid_fallback_png_header(self, temp_capture_dir):
        """Verify fallback PNG bytes in camera_rig.py lines 703-704 and 838-839.
        
        When PIL encounters an exception (e.g. invalid resolution 0x0), camera_rig.py
        writes a valid transparent fallback PNG byte stream that passes PIL Image.open().
        """
        out_file = os.path.join(temp_capture_dir, "fallback_test.png")
        capture_viewport_image(
            output_path=out_file,
            resolution=(0, 0),  # Triggers PIL exception and executes raw bytes fallback
        )
        assert os.path.isfile(out_file)
        raw_size = os.path.getsize(out_file)
        assert raw_size == 70, f"Expected 70-byte fallback PNG, got {raw_size} bytes"

        # Verify that PIL successfully identifies and opens the fallback PNG
        with Image.open(out_file) as img:
            img.verify()
            assert img.format == "PNG"
```

---

## 5. Verification Method

### 5.1 Verification of 70-Byte Valid Fallback PNG
Run in PowerShell:
```powershell
.venv\Scripts\python.exe -c "
import io
from PIL import Image

FALLBACK_PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n'
    b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
    b'\x00\x00\x00\rIDATx\x9cc\x60\x60\x60\x60\x00\x00\x00\x05\x00\x01\xa5\xf6E@'
    b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
)
assert len(FALLBACK_PNG_BYTES) == 70
im = Image.open(io.BytesIO(FALLBACK_PNG_BYTES))
im.verify()
print('PASS: 70-byte PNG verified successfully by PIL!')
"
```
- **Pass condition**: Prints `PASS: 70-byte PNG verified successfully by PIL!` with zero errors.
- **Invalidation condition**: Any `UnidentifiedImageError` or `OSError`.

### 5.2 Verification of Look-At Forward Ray Target Intersection
Run in PowerShell:
```powershell
.venv\Scripts\python.exe -c "
import math, numpy as np
from morphomesh.camera_rig import calculate_spherical_camera_position

target = (0.5, -0.2, 1.1)
d = 4.0
for vp, (a, e) in {'front': (0.0, 0.0), 'side': (90.0, 0.0), 'back': (180.0, 0.0), 'three_quarter': (45.0, 15.0), 'top': (0.0, 88.0)}.items():
    pos, rot = calculate_spherical_camera_position(target, d, a, e)
    R = np.array(rot.to_matrix())[:3, :3]
    ray = R @ np.array([0.0, 0.0, -1.0])
    rec = np.array(pos) + d * ray
    diff = np.linalg.norm(rec - np.array(target))
    print(f'{vp}: ray diff = {diff:.8f}')
    assert diff < 1e-4, f'Ray missed for {vp}'
print('PASS: All forward rays from cam_rot strike target center within 1e-4!')
"
```
- **Pass condition**: Prints `PASS: All forward rays from cam_rot strike target center within 1e-4!` with `diff < 1e-4`.
- **Invalidation condition**: Any diff $> 1e-4$ (e.g. $5.65\text{m}$ for side or $8.0\text{m}$ for back).

### 5.3 Verification of Full Pytest Suites
Run in PowerShell:
```powershell
.venv\Scripts\pytest.exe -v tests/test_inspector_camera.py tests/test_multiview_rendering.py tests/test_adversarial_viewport_capture.py
```
- **Pass condition**: 100% passed (64+ tests in inspector & multiview, 42 tests in adversarial), exit code 0.
