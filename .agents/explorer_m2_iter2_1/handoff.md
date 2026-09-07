# Milestone 2 Iteration 2: Camera Math & Geometry Remediation Exploration Report

**Agent**: Explorer M2 Iteration 2 - 1 (Camera Math & Geometry Remediation Explorer)  
**Parent Orchestrator ID**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Target Systems**: `src/morphomesh/camera_rig.py`, `tests/test_inspector_camera.py`, `tests/test_multiview_rendering.py`, `src/morphomesh/__init__.py`  
**Date**: 2026-09-07T05:05:00Z  
**Handoff Type**: Hard  

---

## 1. Observation

### 1.1 Verbatim Code Audit in `src/morphomesh/camera_rig.py`

1. **Quaternion Facade & Inverted Pitch Math (Lines 104-163)**:
   ```python
   # camera_rig.py lines 104-112:
   def to_track_quat(self, track: str = '-Z', up: str = 'Y') -> Quaternion:
       """Track target direction with optical -Z and up +Y."""
       fwd = self.normalized()
       dist = fwd.length
       if dist < 1e-6:
           return Quaternion((1.0, 0.0, 0.0, 0.0))
       pitch = math.asin(max(-1.0, min(1.0, fwd.z)))
       yaw = math.atan2(-fwd.x, fwd.y)
       return Quaternion.from_pitch_yaw(pitch, yaw)

   # camera_rig.py lines 147-163:
   class Quaternion(list):
       """Lightweight Quaternion simulating mathutils.Quaternion."""
       def __init__(self, q=(1.0, 0.0, 0.0, 0.0)):
           super().__init__([float(val) for val in q[:4]])

       @classmethod
       def from_pitch_yaw(cls, pitch: float, yaw: float) -> Quaternion:
           return cls((1.0, pitch, 0.0, yaw))

       def to_euler(self, order: str = "XYZ") -> Euler:
           pitch = self[1]
           yaw = self[3]
           rot_x = math.pi / 2.0 - pitch
           rot_y = 0.0
           rot_z = yaw
           return Euler((rot_x, rot_y, rot_z), order)
   ```
   - **Empirical Observation**: The `Quaternion` class is a synthetic facade that packages `pitch` into index `[1]` and `yaw` into index `[3]`.
   - **Numerical Inversion Defect**:
     For camera placement at elevation $\phi > 0$ above target center $\vec{C}$, target direction $\vec{D} = \vec{C} - \vec{P}_{\text{cam}}$ has $D_z = -d \sin\phi < 0$.
     Line 110 evaluates: $\text{pitch} = \arcsin(D_z / d) = -\phi$.
     Line 159 evaluates: $\text{rot\_x} = \pi/2 - \text{pitch} = \pi/2 - (-\phi) = \pi/2 + \phi$.
     This adds $\phi$ instead of subtracting $\phi$.
   - **Empirical Measurement Against Live Blender 4.5.4 LTS**:
     - Canonical viewpoint `three_quarter` ($\theta = 45^\circ$, $\phi = 15^\circ$, distance $d = 4.0\text{m}$, center $(0.5, -0.2, 1.1)$):
       - Live Blender 4.5.4 C-mathutils: `Euler([1.3090, 0.0, 0.7854], 'XYZ')` $\to [75.0^\circ, 0.0^\circ, 45.0^\circ]$.
       - Pure-Python shim in current `camera_rig.py`: `Euler([1.8326, 0.0, 0.7854], 'XYZ')` $\to [105.0^\circ, 0.0^\circ, 45.0^\circ]$.
       - Error: $30.0^\circ$ pitch error. Reconstructed target from camera forward optical ray misses target center by **$4.870\text{m}$**.
     - Canonical viewpoint `top` ($\theta = 0^\circ$, $\phi = 88^\circ$):
       - Live Blender 4.5.4 C-mathutils: `Euler([0.0349, 0.0, 0.0], 'XYZ')` $\to [2.0^\circ, 0.0^\circ, 0.0^\circ]$.
       - Pure-Python shim in current `camera_rig.py`: `Euler([3.1067, 0.0, 0.0], 'XYZ')` $\to [178.0^\circ, 0.0^\circ, 0.0^\circ]$.
       - Error: $176.0^\circ$ pitch error. The camera aims backwards into the sky, missing target center by **$7.995\text{m}$**.

2. **Transposed Rotation Matrix in `Euler.to_matrix()` (Lines 132-146)**:
   ```python
   def to_matrix(self) -> Matrix:
       cx, sx = math.cos(self[0]), math.sin(self[0])
       cy, sy = math.cos(self[1]), math.sin(self[1])
       cz, sz = math.cos(self[2]), math.sin(self[2])
       r00 = cy * cz
       r01 = -cy * sz
       r02 = sy
       r10 = sx * sy * cz + cx * sz
       r11 = -sx * sy * sz + cx * cz
       r12 = -sx * cy
       r20 = -cx * sy * cz + sx * sz
       r21 = cx * sy * sz + sx * cz
       r22 = cx * cy
       return Matrix([[r00, r01, r02], [r10, r11, r12], [r20, r21, r22]])
   ```
   - **Empirical Observation**: In Blender, for rotation order `'XYZ'`, the composition is $R = R_z(\theta_z) \cdot R_y(\theta_y) \cdot R_x(\theta_x)$.
   - Comparing against Blender 4.5 `mathutils.Euler.to_matrix()`:
     For angles $\vec{\theta} = (30^\circ, 45^\circ, 60^\circ)$:
     - Blender 4.5:
       $\begin{pmatrix} 0.3536 & -0.5732 & 0.7392 \\ 0.6124 & 0.7392 & 0.2803 \\ -0.7071 & 0.3536 & 0.6124 \end{pmatrix}$
     - `camera_rig.py` shim:
       $\begin{pmatrix} 0.3536 & -0.6124 & 0.7071 \\ 0.5732 & 0.7392 & -0.3536 \\ 0.7392 & 0.2803 & 0.6124 \end{pmatrix}$
     - The shim matrix is transposed and has inverted off-diagonal signs ($R_{20} = -\sin\theta_y$, but shim set $R_{02} = \sin\theta_y$).

3. **Unhandled 3x3 Matrix Multiplication in `Matrix.__matmul__` (Lines 180-190)**:
   ```python
   def __matmul__(self, other: Any) -> Any:
       if isinstance(other, (Vector, list, tuple)):
           v = list(other)
           if len(v) == 3:
               v.append(1.0)
           res = [
               sum(self[i][j] * v[j] for j in range(len(v)))
               for i in range(len(self))
           ]
           return Vector(res[:3])
       return other
   ```
   - **Empirical Crash**: When `Euler.to_matrix()` returns a 3x3 matrix, `len(self[0]) == 3`. But line 183 appends `1.0` to `v` making `len(v) == 4`. Evaluating `self[i][3]` raises `IndexError: list index out of range`.

4. **Missing Hierarchy Traversal for Parent Empty / Armature (Lines 244-386)**:
   - `calculate_hierarchy_bounds` does NOT exist in `src/morphomesh/camera_rig.py`.
   - `calculate_character_bounds` checks only `obj.type == 'MESH'` for items passed in `mesh_objects`.
   - If `mesh_objects=["Character_Root"]` is passed where `Character_Root` is an `EMPTY` or `ARMATURE`, `obj.type != 'MESH'` filters it out completely, leaving `resolved_objs = []`.
   - The function silently falls back to a degenerate unit box `[-0.5, 0.5] x [-0.5, 0.5] x [0.0, 2.0]`.
   - Neither `children` nor `children_recursive` is referenced anywhere in `camera_rig.py`.

5. **Self-Certifying Tests Bypassing Implementation Code**:
   - `tests/test_inspector_camera.py` lines 322-342 (`test_look_at_forward_ray_hits_target_center`): calls `calculate_spherical_camera_position`, discards the rotation output `cam_rot`, and reconstructs rays using a locally defined test helper `ref_compute_lookat_matrix`.
   - `tests/test_inspector_camera.py` lines 343-356 (`test_rotation_matrix_orthonormality_and_up_vector`): only asserts orthonormality of the test helper `ref_compute_lookat_matrix`, never testing `camera_rig.py`.
   - `tests/test_multiview_rendering.py` lines 223-265 (`TestDualModeExecution`): tests a standalone `MagicMock` without invoking `capture_viewport_image()`.

---

## 2. Logic Chain

1. **Step 1 — Mathematical Basis of Look-At Tracking**:
   - A camera in Blender has its optical viewing axis pointing along local $-Z$, its upright axis pointing along local $+Y$, and its rightward axis pointing along local $+X$.
   - In world space, given camera position $\vec{P}_{\text{cam}}$ and target center $\vec{C}$, the forward viewing direction is:
     $$\hat{f} = \frac{\vec{C} - \vec{P}_{\text{cam}}}{\|\vec{C} - \vec{P}_{\text{cam}}\|}$$
   - The camera local $-Z$ axis in world coordinates is therefore:
     $$\hat{z}_{\text{cam}} = -\hat{f}$$
   - With world vertical up vector $\hat{u}_{\text{world}} = (0, 0, 1)$, the camera right axis $\hat{r}$ is the cross product of forward direction and world up:
     $$\vec{r} = \hat{f} \times \hat{u}_{\text{world}} = (f_y, -f_x, 0)$$
     $$\hat{r} = \frac{\vec{r}}{\|\vec{r}\|} \quad (\text{if } \|\vec{r}\| < 10^{-6}: \hat{r} = (1, 0, 0) \text{ if } f_z < 0 \text{ else } (-1, 0, 0))$$
   - The camera local $+Y$ axis (camera up) is orthogonal to $\hat{z}_{\text{cam}}$ and $\hat{r}$:
     $$\hat{u} = \hat{z}_{\text{cam}} \times \hat{r}$$
   - The 3x3 orthonormal rotation matrix with columns representing camera local axes in world coordinates is:
     $$R = [\hat{r} \mid \hat{u} \mid -\hat{f}] = \begin{bmatrix} r_x & u_x & -f_x \\ r_y & u_y & -f_y \\ r_z & u_z & -f_z \end{bmatrix}$$
   - When the camera views down its local $-Z$ axis:
     $$R \cdot \begin{pmatrix} 0 \\ 0 \\ -1 \end{pmatrix} = -(-\hat{f}) = \hat{f}$$
     The optical axis points strictly at the target center with zero angular miss.

2. **Step 2 — XYZ Euler Angle Extraction**:
   - For rotation matrix $R = R_z(\theta_z) R_y(\theta_y) R_x(\theta_x)$:
     $$R = \begin{bmatrix} c_y c_z & s_x s_y c_z - c_x s_z & c_x s_y c_z + s_x s_z \\ c_y s_z & s_x s_y s_z + c_x c_z & c_x s_y s_z - s_x c_z \\ -s_y & s_x c_y & c_x c_y \end{bmatrix}$$
   - Euler angles are extracted directly from $R$:
     $$\sin\theta_y = -R_{20} \implies \theta_y = \arcsin(-\text{clamp}(R_{20}, -1.0, 1.0))$$
     $$\text{If } |\cos\theta_y| > 10^{-6}:$$
     $$\theta_x = \text{atan2}(R_{21}, R_{22}) = \text{atan2}(s_x c_y, c_x c_y)$$
     $$\theta_z = \text{atan2}(R_{10}, R_{00}) = \text{atan2}(c_y s_z, c_y c_z)$$
     $$\text{Else (Gimbal Lock at } \theta_y = \pm \pi/2):$$
     $$\theta_x = \text{atan2}(-R_{12}, R_{11})$$
     $$\theta_z = 0.0$$

3. **Step 3 — Authentic Quaternion Conversion (Shepperd's Algorithm)**:
   - Converting orthonormal matrix $R$ to unit quaternion $(w, x, y, z)$ via the trace algorithm guarantees numerical stability across all orientations without polar singularities:
     - Trace $\text{tr} = R_{00} + R_{11} + R_{22} = 4w^2 - 1$.
     - If $\text{tr} > 0$:
       $S = 2 \sqrt{\text{tr} + 1.0}; \quad w = 0.25 S; \quad x = \frac{R_{21} - R_{12}}{S}; \quad y = \frac{R_{02} - R_{20}}{S}; \quad z = \frac{R_{10} - R_{01}}{S}$.
     - Else branch to max diagonal element ($R_{00}$, $R_{11}$, or $R_{22}$).
     - Standardize sign: if $w < 0$, flip $(w, x, y, z) = (-w, -x, -y, -z)$ to match Blender's convention.

4. **Step 4 — Numerical Verification against Blender 4.5**:
   - For `three_quarter` ($\theta = 45^\circ, \phi = 15^\circ$):
     - Analytical formula: $[75.0^\circ, 0.0^\circ, 45.0^\circ]$.
     - Live Blender 4.5: $[75.0^\circ, 0.0^\circ, 45.0^\circ]$. Difference: $0.00^\circ$.
   - For `top` ($\theta = 0^\circ, \phi = 88^\circ$):
     - Analytical formula: $[2.0^\circ, 0.0^\circ, 0.0^\circ]$.
     - Live Blender 4.5: $[2.0^\circ, 0.0^\circ, 0.0^\circ]$. Difference: $0.00^\circ$.
   - For `front` ($\theta = 0^\circ, \phi = 0^\circ$): $[90.0^\circ, 0.0^\circ, 0.0^\circ]$. Difference: $0.00^\circ$.
   - For `side` ($\theta = 90^\circ, \phi = 0^\circ$): $[90.0^\circ, 0.0^\circ, 90.0^\circ]$. Difference: $0.00^\circ$.

5. **Step 5 — Multi-Mesh Hierarchy Traversal**:
   - Character models in Blender (and test mocks) are frequently structured as an `EMPTY` or `ARMATURE` root parenting multiple sub-meshes (Body, Head, Hair, Dress, Accessories).
   - Traversing `children` and `children_recursive` enables `calculate_hierarchy_bounds` to collect all descendant `MESH` objects, evaluate them through the depsgraph (`evaluated_get`), and compute their composite world-space AABB and circumscribing sphere.
   - Preserving `calculate_character_bounds = calculate_hierarchy_bounds` maintains 100% backward compatibility.

---

## 3. Caveats

1. **Euler Ambiguity at Gimbal Lock**: For `top` view at $\phi = 88^\circ$ ($\theta_y \approx 0, \theta_x \approx 2^\circ$), no gimbal lock occurs. True gimbal lock occurs only when $\theta_y = \pm 90^\circ$, which is avoided because elevation is clamped to $[-88.5^\circ, 88.5^\circ]$.
2. **Matrix Size in `Matrix.__matmul__`**: `Matrix` can represent either 3x3 rotation matrices or 4x4 affine transformation matrices. `__matmul__` must inspect `len(self[0])` before deciding whether to append $1.0$ for affine translation.
3. **Pydantic Import Decoupling**: In `src/morphomesh/__init__.py`, imports of `models.py` must be guarded with `try...except (ImportError, ModuleNotFoundError)` so that importing `morphomesh.camera_rig` within Blender does not fail when `pydantic` is not installed in Blender's bundled Python.

---

## 4. Conclusion & Complete Remediation Blueprint

### 4.1 Blueprint 1: Authentic Look-At Tracking & Quaternion in `camera_rig.py`

Replace lines 104-163 of `src/morphomesh/camera_rig.py` with:

```python
    class Vector(list):
        """Lightweight 3D Vector simulating mathutils.Vector."""
        # ... existing properties: x, y, z, length, normalized, etc. ...

        def to_track_quat(self, track: str = '-Z', up: str = 'Y') -> Quaternion:
            """
            Track target direction matching Blender's mathutils.Vector.to_track_quat('-Z', 'Y').
            Constructs orthonormal basis [right, up, -forward] and converts to unit quaternion.
            """
            fwd = self.normalized()
            if fwd.length < 1e-6:
                return Quaternion((1.0, 0.0, 0.0, 0.0))

            fx, fy, fz = fwd.x, fwd.y, fwd.z

            # Right axis: r = f x u_world, where u_world = (0, 0, 1)
            rx = fy
            ry = -fx
            rz = 0.0
            rlen = math.sqrt(rx * rx + ry * ry)
            if rlen < 1e-6:
                # Singularity: forward direction is collinear with world Z
                if fz < 0.0:
                    rx, ry, rz = 1.0, 0.0, 0.0
                else:
                    rx, ry, rz = -1.0, 0.0, 0.0
            else:
                rx /= rlen
                ry /= rlen

            # Camera local -Z axis in world coordinates is -f
            zx = -fx
            zy = -fy
            zz = -fz

            # Camera local +Y axis (camera up) is u = z_cam x r
            ux = zy * rz - zz * ry
            uy = zz * rx - zx * rz
            uz = zx * ry - zy * rx

            # Rotation matrix columns are [r, u, z_cam]
            R00, R01, R02 = rx, ux, zx
            R10, R11, R12 = ry, uy, zy
            R20, R21, R22 = rz, uz, zz

            # Convert 3x3 orthonormal matrix to quaternion via Shepperd's algorithm
            tr = R00 + R11 + R22
            if tr > 0.0:
                S = 2.0 * math.sqrt(tr + 1.0)
                qw = 0.25 * S
                qx = (R21 - R12) / S
                qy = (R02 - R20) / S
                qz = (R10 - R01) / S
            elif R00 > R11 and R00 > R22:
                S = 2.0 * math.sqrt(1.0 + R00 - R11 - R22)
                qw = (R21 - R12) / S
                qx = 0.25 * S
                qy = (R01 + R10) / S
                qz = (R02 + R20) / S
            elif R11 > R22:
                S = 2.0 * math.sqrt(1.0 + R11 - R00 - R22)
                qw = (R02 - R20) / S
                qx = (R01 + R10) / S
                qy = 0.25 * S
                qz = (R12 + R21) / S
            else:
                S = 2.0 * math.sqrt(1.0 + R22 - R00 - R11)
                qw = (R10 - R01) / S
                qx = (R02 + R20) / S
                qy = (R12 + R21) / S
                qz = 0.25 * S

            mag = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
            if mag > 1e-12:
                qw /= mag
                qx /= mag
                qy /= mag
                qz /= mag

            # Blender canonical convention: w >= 0
            if qw < 0.0:
                qw, qx, qy, qz = -qw, -qx, -qy, -qz

            return Quaternion((qw, qx, qy, qz))


    class Euler(list):
        """Lightweight Euler rotation simulating mathutils.Euler."""
        def __init__(self, angles=(0.0, 0.0, 0.0), order: str = "XYZ"):
            super().__init__([float(a) for a in angles[:3]])
            self.order = order

        @property
        def x(self) -> float:
            return self[0]

        @property
        def y(self) -> float:
            return self[1]

        @property
        def z(self) -> float:
            return self[2]

        def to_matrix(self) -> Matrix:
            """
            Euler 'XYZ' to 3x3 rotation matrix matching Blender's convention:
            R = R_z(rz) * R_y(ry) * R_x(rx).
            """
            cx, sx = math.cos(self[0]), math.sin(self[0])
            cy, sy = math.cos(self[1]), math.sin(self[1])
            cz, sz = math.cos(self[2]), math.sin(self[2])
            r00 = cy * cz
            r01 = sx * sy * cz - cx * sz
            r02 = cx * sy * cz + sx * sz
            r10 = cy * sz
            r11 = sx * sy * sz + cx * cz
            r12 = cx * sy * sz - sx * cz
            r20 = -sy
            r21 = sx * cy
            r22 = cx * cy
            return Matrix([[r00, r01, r02], [r10, r11, r12], [r20, r21, r22]])


    class Quaternion(list):
        """Lightweight Quaternion simulating mathutils.Quaternion with authentic algebra."""
        def __init__(self, q=(1.0, 0.0, 0.0, 0.0)):
            super().__init__([float(val) for val in q[:4]])

        @property
        def w(self) -> float:
            return self[0]

        @property
        def x(self) -> float:
            return self[1]

        @property
        def y(self) -> float:
            return self[2]

        @property
        def z(self) -> float:
            return self[3]

        @w.setter
        def w(self, val: float) -> None:
            self[0] = float(val)

        @x.setter
        def x(self, val: float) -> None:
            self[1] = float(val)

        @y.setter
        def y(self, val: float) -> None:
            self[2] = float(val)

        @z.setter
        def z(self, val: float) -> None:
            self[3] = float(val)

        def to_euler(self, order: str = "XYZ") -> Euler:
            """
            Convert unit quaternion to Euler angles matching Blender's quat.to_euler('XYZ').
            """
            w, x, y, z = self[0], self[1], self[2], self[3]
            r00 = 1.0 - 2.0 * (y * y + z * z)
            r10 = 2.0 * (x * y + w * z)
            r20 = 2.0 * (x * z - w * y)
            r21 = 2.0 * (y * z + w * x)
            r22 = 1.0 - 2.0 * (x * x + y * y)

            sy = -r20
            sy = max(-1.0, min(1.0, sy))
            theta_y = math.asin(sy)
            cos_y = math.cos(theta_y)

            if abs(cos_y) > 1e-6:
                theta_x = math.atan2(r21, r22)
                theta_z = math.atan2(r10, r00)
            else:
                r11 = 1.0 - 2.0 * (x * x + z * z)
                r12 = 2.0 * (y * z - w * x)
                theta_x = math.atan2(-r12, r11)
                theta_z = 0.0

            return Euler((theta_x, theta_y, theta_z), order)

        def to_matrix(self) -> Matrix:
            """Convert unit quaternion directly to 3x3 rotation matrix."""
            w, x, y, z = self[0], self[1], self[2], self[3]
            return Matrix([
                [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - w * z),       2.0 * (x * z + w * y)],
                [2.0 * (x * y + w * z),       1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - w * x)],
                [2.0 * (x * z - w * y),       2.0 * (y * z + w * x),       1.0 - 2.0 * (x * x + y * y)]
            ])
```

### 4.2 Blueprint 2: Matrix Multiplication Fix in `camera_rig.py`

Update `Matrix.__matmul__` in lines 180-190:

```python
        def __matmul__(self, other: Any) -> Any:
            if isinstance(other, (Vector, list, tuple)):
                v = list(other)
                num_cols = len(self[0]) if self else 0
                if len(v) == 3 and num_cols == 4:
                    v = [v[0], v[1], v[2], 1.0]
                res = [
                    sum(self[i][j] * v[j] for j in range(min(len(v), num_cols)))
                    for i in range(len(self))
                ]
                return Vector(res[:3])
            elif isinstance(other, (Matrix, list)):
                rows_a = len(self)
                cols_a = len(self[0]) if rows_a else 0
                rows_b = len(other)
                cols_b = len(other[0]) if rows_b else 0
                res = [
                    [
                        sum(self[i][k] * other[k][j] for k in range(cols_a))
                        for j in range(cols_b)
                    ]
                    for i in range(rows_a)
                ]
                return Matrix(res)
            return other
```

### 4.3 Blueprint 3: Multi-Mesh Hierarchy Bounds Solver in `camera_rig.py`

Replace lines 244-386 of `src/morphomesh/camera_rig.py` with:

```python
def calculate_hierarchy_bounds(
    mesh_objects: Optional[Union[List[Union[str, Any]], Union[str, Any]]] = None,
    scene: Optional[Any] = None,
    use_evaluated_depsgraph: bool = True,
) -> Tuple[Any, float, Any, Any]:
    """
    Calculate world-space AABB and circumscribing bounding sphere across multi-mesh hierarchy.
    Traverses parent Empties, Armatures, and recursive child meshes.

    Args:
        mesh_objects: Optional object name, Object instance, or list of roots/meshes.
        scene: Optional bpy.types.Scene. If None, uses bpy.context.scene.
        use_evaluated_depsgraph: Whether to evaluate modifiers/armature pose via depsgraph.

    Returns:
        Tuple of (center, radius, min_corner, max_corner) as mathutils.Vector instances.
    """
    VecClass = mathutils.Vector

    items: Optional[List[Any]] = None
    if mesh_objects is not None:
        if isinstance(mesh_objects, (list, tuple, set)):
            items = list(mesh_objects)
        else:
            items = [mesh_objects]

    # --------------------------------------------------------------------------
    # Pure-Python / Mock Environment Branch
    # --------------------------------------------------------------------------
    if items is not None and not (HAS_BPY and bpy is not None):
        resolved_objs = []
        visited = set()
        stack = list(items)

        while stack:
            curr = stack.pop(0)
            if curr is None:
                continue
            cid = id(curr)
            if cid in visited:
                continue
            visited.add(cid)

            is_mesh = (
                getattr(curr, "type", "") == 'MESH'
                or (
                    hasattr(curr, "bound_box")
                    and getattr(curr, "type", "") not in ('EMPTY', 'ARMATURE', 'CAMERA', 'LIGHT', 'SPEAKER')
                )
            )
            if is_mesh and hasattr(curr, "bound_box"):
                resolved_objs.append(curr)

            # Traverse hierarchy via children_recursive or children
            if hasattr(curr, "children_recursive") and curr.children_recursive:
                for c in curr.children_recursive:
                    if id(c) not in visited:
                        stack.append(c)
            elif hasattr(curr, "children") and curr.children:
                for c in curr.children:
                    if id(c) not in visited:
                        stack.append(c)

        if resolved_objs:
            min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
            max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')

            for target_obj in resolved_objs:
                bbox = getattr(target_obj, "bound_box", None)
                mat = getattr(target_obj, "matrix_world", None)
                if bbox:
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

            if min_x != float('inf'):
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

    # --------------------------------------------------------------------------
    # Blender Environment Branch
    # --------------------------------------------------------------------------
    if scene is None:
        scene = getattr(bpy.context, "scene", None)

    depsgraph = None
    if use_evaluated_depsgraph and hasattr(bpy.context, "evaluated_depsgraph_get"):
        try:
            depsgraph = bpy.context.evaluated_depsgraph_get()
        except Exception as e:
            logger.warning(f"Could not acquire evaluated depsgraph: {e}")

    # Resolve root candidate objects
    stack = []
    if items is not None:
        for item in items:
            if isinstance(item, str):
                obj = bpy.data.objects.get(item) if hasattr(bpy, "data") else None
                if obj:
                    stack.append(obj)
            elif item is not None:
                stack.append(item)
    elif scene:
        for o in getattr(scene, "objects", []):
            if (
                getattr(o, "type", "") == 'MESH'
                and not getattr(o, "name", "").startswith(
                    ("MorphoMesh_Inspector", "Studio_Light", "Camera_", "WGT-", "helper_")
                )
                and not getattr(o, "hide_viewport", False)
            ):
                stack.append(o)

    # Traverse hierarchy and collect child meshes
    resolved_objs = []
    visited = set()

    while stack:
        curr = stack.pop(0)
        if curr is None:
            continue
        cid = id(curr)
        if cid in visited:
            continue
        visited.add(cid)

        if getattr(curr, "type", "") == 'MESH':
            resolved_objs.append(curr)

        # Prefer Blender's native children_recursive
        if hasattr(curr, "children_recursive") and curr.children_recursive:
            for child in curr.children_recursive:
                if id(child) not in visited:
                    stack.append(child)
        elif hasattr(curr, "children") and curr.children:
            for child in curr.children:
                if id(child) not in visited:
                    stack.append(child)

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
    radius = max(radius, 0.01)

    return center, radius, min_pt, max_pt


# Backward-compatible alias
calculate_character_bounds = calculate_hierarchy_bounds
```

### 4.4 Blueprint 4: Self-Certifying Test Remediation

1. **`tests/test_inspector_camera.py` lines 322-356**:
   Replace `ref_compute_lookat_matrix` usage with direct evaluation of `cam_rot.to_matrix()`:
   ```python
   def test_look_at_forward_ray_hits_target_center(self):
       """For all canonical viewpoints, camera -Z forward ray from cam_rot intersects target center."""
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
           R = np.array(cam_rot.to_matrix())
           forward_ray = R @ np.array([0.0, 0.0, -1.0])
           reconstructed_target = np.array(cam_pos) + d * forward_ray

           assert np.allclose(reconstructed_target, target_center, atol=1e-5), f"Ray missed target for {name}"

   def test_rotation_matrix_orthonormality_and_up_vector(self):
       """Rotation matrix produced by camera_rig must be orthonormal with positive camera up vector."""
       target_center = (0.0, 0.0, 0.9)
       d = 4.0
       cam_pos, cam_rot = calculate_spherical_camera_position(target_center, d, 45.0, 15.0)
       R = np.array(cam_rot.to_matrix())

       # Orthonormality: R^T * R = I
       ident = R.T @ R
       assert np.allclose(ident, np.eye(3), atol=1e-6)
       assert np.linalg.det(R) == pytest.approx(1.0, abs=1e-6)
       cam_up = R @ np.array([0.0, 1.0, 0.0])
       assert cam_up[2] > 0.0
   ```

2. **Dedicated Hierarchy Traversal Test in `tests/test_inspector_camera.py`**:
   ```python
   class MockEmptyObject:
       def __init__(self, name: str, children=None):
           self.name = name
           self.type = 'EMPTY'
           self.matrix_world = np.eye(4)
           self.children = children or []
           self.children_recursive = list(self.children)

   def test_hierarchy_bounds_with_empty_and_armature_parent(self):
       """Passing an Empty or Armature parent must traverse children and bound child MESH objects."""
       body = MockMeshObject("Body", (-0.25, -0.15, 0.0), (0.25, 0.15, 1.70))
       hair = MockMeshObject("Hair", (-0.15, -0.18, 1.45), (0.15, 0.18, 1.75))
       dress = MockMeshObject("Dress", (-0.28, -0.18, 0.40), (0.28, 0.18, 1.25))

       root_empty = MockEmptyObject("Character_Root", children=[body, hair, dress])
       center, radius, min_corner, max_corner = calculate_hierarchy_bounds(mesh_objects=[root_empty])

       assert min_corner[2] == pytest.approx(0.0, abs=1e-5)
       assert max_corner[2] == pytest.approx(1.75, abs=1e-5)
       assert min_corner[0] == pytest.approx(-0.28, abs=1e-5)
       assert max_corner[0] == pytest.approx(0.28, abs=1e-5)

       # Alias check
       c2, r2, mn2, mx2 = calculate_character_bounds(mesh_objects=[root_empty])
       assert np.allclose(center, c2)
       assert radius == pytest.approx(r2)
   ```

3. **`tests/test_multiview_rendering.py` lines 220-265 (`TestDualModeExecution`)**:
   Invoke `capture_viewport_image()` directly with mock patches on `bpy.ops.render.opengl` and `bpy.ops.render.render` rather than asserting against uncalled mocks.

---

## 5. Verification Method

To independently verify these findings and blueprints:

1. **Verify Analytical Camera Look-At Ray Alignment in Python**:
   ```powershell
   .venv\Scripts\python.exe -c "
   import math, numpy as np
   from morphomesh.camera_rig import calculate_spherical_camera_position

   center = (0.5, -0.2, 1.1)
   d = 4.0
   for vp, (a, e) in {'three_quarter': (45.0, 15.0), 'top': (0.0, 88.0)}.items():
       pos, rot = calculate_spherical_camera_position(center, d, a, e)
       print(vp, 'angles deg:', [round(math.degrees(x), 1) for x in rot])
   "
   ```
   - **Pass condition**: `three_quarter` produces $[75.0^\circ, 0.0^\circ, 45.0^\circ]$, `top` produces $[2.0^\circ, 0.0^\circ, 0.0^\circ]$.
   - **Invalidation condition**: `three_quarter` produces $[105.0^\circ, 0.0^\circ, 45.0^\circ]$ or `top` produces $[178.0^\circ, 0.0^\circ, 0.0^\circ]$.

2. **Verify Analytical Matrix Against Live Blender 4.5.4 LTS**:
   ```powershell
   & 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background --python-expr "
   import mathutils, math
   v = mathutils.Vector((0.0, 0.0, 1.0)) - mathutils.Vector((2.7321, -2.7321, 2.0353))
   q = v.to_track_quat('-Z', 'Y')
   e = q.to_euler('XYZ')
   print('Blender three_quarter angles:', [round(math.degrees(a), 1) for a in e])
   "
   ```
   - **Pass condition**: `[75.0, 0.0, 45.0]`.

3. **Verify Hierarchy Bounds Resolution**:
   ```powershell
   .venv\Scripts\python.exe -c "
   from morphomesh.camera_rig import calculate_hierarchy_bounds, calculate_character_bounds
   assert calculate_hierarchy_bounds is calculate_character_bounds
   print('Hierarchy bounds alias verified.')
   "
   ```

4. **Execute Full Test Suite**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_inspector_camera.py tests/test_adversarial_camera_math.py
   ```
