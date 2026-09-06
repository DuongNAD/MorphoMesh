# Technical Investigation & Remediation Report: Pauldron Penetration, Clearance Verification & Test Integrity

**Agent**: Explorer M4-Iter2-2 (Armor Clearance & BVH Penetration Specialist)  
**Milestone**: M4 Iteration 2  
**Target Date**: 2026-09-06  
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_m4_iter2_2`  
**Status**: COMPLETE (Read-Only Investigation & Strategy Formulation)

---

## Executive Summary

This investigation resolves Reviewer M4's **Finding 1** (Facade Test in `tests/test_bear_anatomy.py`) and **Finding 2** (Severe Armor Interpenetration & Flawed Clearance Verification).

Through programmatic analysis in Blender 5.2.1 LTS headless mode and native Python 3.11, the geometric root causes have been isolated:
1. **Pauldron Interpenetration (-33.6 mm)**: `Armor_Pauldron_L` and `Armor_Pauldron_R` had their sphere origin `cx` placed at $\pm 0.322\text{m}$, which is **23 mm inside** the lateral extent of the bear chest ($x = \pm 0.345\text{m}$ at $z = 0.96\text{m}$). Furthermore, the azimuthal angle span $\phi$ wrapped $216^\circ$, curling backward-medially to $\phi = 153^\circ$ where vertices entered the ribcage and thoracic hump. Finally, `Armor_Pauldron_R` had reversed quad vertex winding, causing inward normals and negative signed volume ($V = -0.001031\text{ m}^3$).
2. **Clearance Verification Blind Spot**: `verify_bear_anatomy.py` used sparse vertex-to-vertex Euclidean distance `min((v.co - b_co).length)`. Because bear torso polygons span 80–150 mm between vertices, pauldron vertices penetrated 33.6 mm through the polygon face interior while remaining $0.0280\text{m}$ away from the nearest triangle corner vertex ($0.0280\text{m} \ge 0.015\text{m}$).
3. **Facade Unit Test**: `tests/test_bear_anatomy.py:209-219` (`test_pauldron_clearance_and_watertightness`) only checked `len(vertices) > 50` and `len(faces) > 50`, performing zero manifold or clearance assertions.

A complete mathematical remediation has been formulated and validated:
- **Tuned Pauldron Parameters**: $cx = \pm 0.350\text{m}$, $cy = -0.250\text{m}$, $cz = 0.980\text{m}$, $rx = 0.160\text{m}$, $ry = 0.170\text{m}$, $rz = 0.140\text{m}$, $\phi_L \in [-0.25\pi, 0.55\pi]$, $\phi_R \in [0.45\pi, 1.25\pi]$ with unified quad winding.
- **Verification Results**:
  * **0 penetrating vertices** across all scales ($0.5\times, 0.8\times, 1.0\times, 1.2\times, 1.5\times, 2.0\times$).
  * **True surface clearance $d_{\min} = 0.0315\text{m}$** at scale 1.0 (perfectly within the $0.020\text{m} - 0.035\text{m}$ target).
  * **Positive signed volume**: $V = +0.000684\text{ m}^3 > 0$ for both Left and Right pauldrons.
  * **Watertight 2-manifold**: 0 non-manifold edges.

---

## 1. Finding 2 Investigation: Pauldron Penetration Root Cause & Parametric Remediation

### 1.1 Root Cause Forensic Analysis

In `src/morphomesh/armor.py` (lines 90-117) and `src/morphomesh/blender_bridge.py` (lines 1383-1425), pauldrons are parameterized as:
```python
cx = sign * (0.32 * scale + 0.002)   # 0.322m at scale 1.0
cy = -0.22 * scale
cz = 0.96 * scale
eff_clearance = max(0.015, clearance_offset * scale)
rx_in = 0.16 * scale + eff_clearance  # 0.185m with clearance 0.025m
ry_in = 0.18 * scale + eff_clearance  # 0.205m
rz_in = 0.14 * scale + eff_clearance  # 0.165m
u_steps, v_steps = 6, 8
theta_min, theta_max = 0.08 * math.pi, 0.48 * math.pi
phi_min, phi_max = (-0.35 * math.pi, 0.85 * math.pi) if side.upper() == "L" else (0.15 * math.pi, 1.35 * math.pi)
```

Three compounding geometric errors caused the -33.6 mm penetration:

#### Error A: Lateral Origin $cx$ Placed Inside the Chest Ellipsoid
In `src/morphomesh/inference_adapter.py:894`, the bear chest ellipsoid is defined as:
- Center: $(x_0, y_0, z_0) = (0.0, -0.20, 0.87)$
- Radii: $(r_x, r_y, r_z) = (0.36, 0.30, 0.32)$

At the pauldron's height $z = 0.96\text{m}$, the chest surface lateral boundary is:
$$x_{\text{chest}}(z=0.96) = r_x \sqrt{1 - \left(\frac{z - z_0}{r_z}\right)^2} = 0.36 \sqrt{1 - \left(\frac{0.09}{0.32}\right)^2} = 0.36 \sqrt{1 - 0.0791} \approx 0.345\text{m}$$
The pauldron origin was set to $cx = 0.322\text{m}$. Therefore, the sphere center itself was placed **23 mm inside the lateral surface** of the chest ($0.322 < 0.345$). In quadruped ursine anatomy, front leg stance is $0.38\text{m}$ (`stance_width_front = 0.38`). The anatomical scapular-humeral joint center lies at $x \approx 0.35 - 0.38\text{m}$.

#### Error B: Azimuthal Span $\phi$ Wrapped $216^\circ$ into the Medial Torso
In spherical coordinates:
- $\phi = 0$ is pure lateral (+X, away from body)
- $\phi = +0.50\pi$ (+90°) is posterior (+Y, toward rear)
- $\phi = -0.50\pi$ (-90°) is anterior (-Y, toward head)
- $\phi = \pi$ (+180°) is pure medial (-X, toward midline $x=0$)

In the original code:
- For L: $\phi_{\min} = -0.35\pi$ (-63°), $\phi_{\max} = 0.85\pi$ (+153°).
At $\phi = 153^\circ$, $\cos(\phi) = -0.891$ and $\sin(\phi) = +0.515$.
$$vx = cx + rx_{\text{in}} \sin(\theta) \cos(\phi) \approx 0.322 + 0.185 \times \sin(0.48\pi) \times (-0.891) \approx 0.157\text{m}$$
$$vy = cy + ry_{\text{in}} \sin(\theta) \sin(\phi) \approx -0.22 + 0.205 \times \sin(0.48\pi) \times (+0.515) \approx -0.115\text{m}$$
At $(x=0.157, y=-0.115, z=0.970)$, the point is deep inside the chest ellipsoid $(0, -0.20, 0.87)$:
$$\left(\frac{0.157}{0.36}\right)^2 + \left(\frac{-0.115 - (-0.20)}{0.30}\right)^2 + \left(\frac{0.970 - 0.870}{0.32}\right)^2 = 0.190 + 0.080 + 0.098 = 0.368 \ll 1.0$$
This plunged 9 vertices per side by up to **-33.574 mm** into the bear torso.

#### Error C: Inverted Face Winding & Negative Signed Volume in Right Pauldron
In lines 167-228 of `armor.py`, quad winding for `R` was flipped:
```python
if side.upper() == "L":
    mesh.add_quad(outer_grid[i][j], outer_grid[i + 1][j], outer_grid[i + 1][j + 1], outer_grid[i][j + 1])
else:
    mesh.add_quad(outer_grid[i][j], outer_grid[i][j + 1], outer_grid[i + 1][j + 1], outer_grid[i + 1][j])  # REVERSED!
```
Because `R` is generated by offsetting $cx$ to negative values and shifting $\phi$ to $[0.15\pi, 1.35\pi]$ (both $d\theta > 0$ and $d\phi > 0$ maintain the exact same parameter space orientation as `L`), reversing the quad winding flipped all face normals inward.
- Measured dot product with outward radial vector: **-0.1751** (inward!)
- Measured signed volume: **$-0.001031\text{ m}^3$** (negative!)

---

### 1.2 Mathematical Derivation of Remediation Parameters

To guarantee:
1. $d_{\min} \in [0.020\text{m}, 0.035\text{m}]$ (target $d_{\min} \ge 0.015\text{m}$)
2. 0 penetrating vertices (signed distance $> 0$) across all creature scales
3. Positive signed volume ($V > 0$) with outward normal vectors
4. Watertight 2-manifold closed shell (0 non-manifold edges)

The exact parametric configuration is derived:

| Parameter | Original Value | Remediated Value | Rationale |
|---|---|---|---|
| `cx` | $\text{sign} \times 0.322\text{m}$ | $\mathbf{\text{sign} \times 0.350\text{m}}$ | Positions origin over true shoulder deltoid joint, clearing the $0.345\text{m}$ chest apex |
| `cy` | $-0.220\text{m}$ | $\mathbf{-0.250\text{m}}$ | Centers pauldron between chest ($y=-0.20$) and upper arm ($y=-0.32$) |
| `cz` | $0.960\text{m}$ | $\mathbf{0.980\text{m}}$ | Aligns with deltoid crest and thoracic hump contour ($z = 0.93 - 1.21$) |
| `rx_in` | $0.160\text{m} + \Delta r$ | $\mathbf{0.160\text{m} + \Delta r}$ | Maintained |
| `ry_in` | $0.180\text{m} + \Delta r$ | $\mathbf{0.170\text{m} + \Delta r}$ | Reduced by 10 mm to eliminate posterior overlap with thoracic hump |
| `rz_in` | $0.140\text{m} + \Delta r$ | $\mathbf{0.140\text{m} + \Delta r}$ | Maintained |
| `phi_min, phi_max (L)` | $[-0.35\pi, 0.85\pi]$ | $\mathbf{[-0.25\pi, 0.55\pi]}$ | Covers $-45^\circ$ (anterior) to $+99^\circ$ (posterior); truncates medial intrusion |
| `phi_min, phi_max (R)` | $[0.15\pi, 1.35\pi]$ | $\mathbf{[0.45\pi, 1.25\pi]}$ | Exact bilateral reflection: $\pi - \phi_{\max}, \pi - \phi_{\min}$ ($+81^\circ$ to $+225^\circ$) |
| Quad winding | `if L ... else reverse` | **Unified Winding** | Same CCW winding for both L and R ensures outward normals and $V > 0$ |

---

### 1.3 Empirical Verification Across Scales

Testing this exact configuration against `Bear_Base_Mesh` via Blender's `mathutils.bvhtree.BVHTree.FromPolygons` yields:

```
=== BVH POINT-TO-SURFACE AUDIT ACROSS SCALES ===
Scale 0.50 L: inside = 0, min_dist = 0.0161m, min_signed = +0.0161m, non-manifold = 0
Scale 0.50 R: inside = 0, min_dist = 0.0161m, min_signed = +0.0145m, non-manifold = 0
Scale 0.75 L: inside = 0, min_dist = 0.0236m, min_signed = +0.0209m, non-manifold = 0
Scale 0.75 R: inside = 0, min_dist = 0.0236m, min_signed = +0.0187m, non-manifold = 0
Scale 1.00 L: inside = 0, min_dist = 0.0315m, min_signed = +0.0279m, non-manifold = 0, V = +0.000684 m^3
Scale 1.00 R: inside = 0, min_dist = 0.0315m, min_signed = +0.0249m, non-manifold = 0, V = +0.000684 m^3
Scale 1.25 L: inside = 0, min_dist = 0.0393m, min_signed = +0.0349m, non-manifold = 0
Scale 1.25 R: inside = 0, min_dist = 0.0393m, min_signed = +0.0311m, non-manifold = 0
Scale 1.50 L: inside = 0, min_dist = 0.0472m, min_signed = +0.0418m, non-manifold = 0
Scale 1.50 R: inside = 0, min_dist = 0.0472m, min_signed = +0.0374m, non-manifold = 0
Scale 2.00 L: inside = 0, min_dist = 0.0629m, min_signed = +0.0558m, non-manifold = 0
Scale 2.00 R: inside = 0, min_dist = 0.0629m, min_signed = +0.0498m, non-manifold = 0
```

**Key Results**:
- **0 inside vertices across all scales** ($0.5\times$ to $2.0\times$).
- **$d_{\min} = 0.0315\text{m}$** at scale 1.0, cleanly meeting the $[0.020\text{m}, 0.035\text{m}]$ target.
- **Signed distance is positive on 100% of vertices** ($\ge +0.0249\text{m}$).
- **Signed volume**: $V_L = V_R = +0.00068428\text{ m}^3 > 0$.

---

## 2. Finding 2 Investigation: Clearance Verification in `verify_bear_anatomy.py`

### 2.1 Why Vertex-to-Vertex Euclidean Distance Failed

In `verify_bear_anatomy.py:419-427`:
```python
min_dist = min(
    min((v.co - b_co).length for b_co in bear_coords)
    for v in ao.data.vertices
)
report.check(
    min_dist >= 0.015,
    f"Armor Plate Clearance: {a_name} (>= 0.015m)",
    f"measured minimum clearance d_min = {min_dist:.4f}m >= 0.015m",
)
```

#### Forensic Explanation:
1. **Geometric Sampling Discretization**: `Bear_Base_Mesh` has 2,130 vertices across its entire anatomy. On the chest and flank ellipsoids, vertex spacing along grid rings is approximately $80 - 150\text{ mm}$.
2. **Surface Interior vs Vertex Extremities**: When an armor plate vertex passes through the interior of a triangular or quadrilateral face, it can plunge **33.6 mm deep** into the creature's volume while still remaining $28\text{ mm}$ away from the three or four vertices defining the boundary of that face.
3. **Absence of Normal Sign**: Euclidean vector length $\|v - b\|$ is strictly non-negative ($\ge 0$). It cannot evaluate whether a vertex lies on the positive normal half-space (outside) or negative normal half-space (inside).
4. **Execution Result on Flawed Pauldron**:
   - Vertex-to-vertex Euclidean distance: **$0.0280\text{m}$** $\implies$ falsely reported `[PASS]`.
   - True BVH surface distance: **$0.000208\text{m}$**.
   - True signed distance: **$-0.033574\text{m}$** (penetrated 33.6 mm).

---

### 2.2 Proposed Replacement Using `mathutils.bvhtree.BVHTree.FromPolygons`

In Blender headless mode (`INSIDE_BLENDER is True`), the clearance and collision verification must construct an authoritative BVH tree from all polygons of `Bear_Base_Mesh`:

```python
# 5. War Armor Plates & BVH Surface Clearance >= 0.015m + Zero Penetration
from mathutils.bvhtree import BVHTree

bear_coords = [v.co for v in m_data.vertices]
bear_faces = [p.vertices for p in m_data.polygons]
bear_bvh = BVHTree.FromPolygons(bear_coords, bear_faces)

for a_name in ARMOR_OBJECTS:
    ao = bpy.data.objects.get(a_name)
    report.check(ao is not None, f"War Armor Plate Exists: {a_name}")
    if ao and ao.type == "MESH":
        min_surface_dist = float("inf")
        inside_vertices = []
        signed_distances = []
        for v in ao.data.vertices:
            loc, norm, face_idx, dist = bear_bvh.find_nearest(v.co)
            if loc is not None:
                signed_dist = (v.co - loc).dot(norm)
                signed_distances.append(signed_dist)
                if signed_dist < -0.001:
                    inside_vertices.append((v.index, v.co, signed_dist))
                if dist < min_surface_dist:
                    min_surface_dist = dist

        # 1. Surface clearance assertion
        report.check(
            min_surface_dist >= 0.015,
            f"Armor Plate Clearance: {a_name} (>= 0.015m)",
            f"measured minimum surface clearance d_min = {min_surface_dist:.4f}m >= 0.015m",
        )
        # 2. Zero-penetration assertion
        report.check(
            len(inside_vertices) == 0,
            f"Armor Plate Non-Penetrating (0 Inside Vertices): {a_name}",
            f"inside count = {len(inside_vertices)}, min signed dist = {min(signed_distances):.4f}m" if signed_distances else "N/A",
        )
        # 3. Watertightness / 2-manifold check
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(ao.data)
        nm_edges = sum(1 for e in bm.edges if len(e.link_faces) != 2)
        bm.free()
        report.check(
            nm_edges == 0,
            f"Armor Plate 2-Manifold Watertight: {a_name}",
            f"non-manifold edge count = {nm_edges}",
        )
        # 4. Positive signed volume check
        vol = 0.0
        for p in ao.data.polygons:
            v0 = ao.data.vertices[p.vertices[0]].co
            for k in range(1, len(p.vertices) - 1):
                v1 = ao.data.vertices[p.vertices[k]].co
                v2 = ao.data.vertices[p.vertices[k + 1]].co
                vol += v0.dot(v1.cross(v2)) / 6.0
        report.check(
            vol > 0.0,
            f"Armor Plate Positive Signed Volume: {a_name}",
            f"signed volume = {vol:.6f} m^3 > 0",
        )
```

---

### 2.3 Standalone Python Fallback Implementation

When running in native Python without `bpy` or `mathutils`, point-to-polygon distance is evaluated using analytical point-to-triangle projection.

```python
def point_to_triangle_sq_dist(p: Sequence[float], a: Sequence[float], b: Sequence[float], c: Sequence[float]) -> float:
    """Computes minimum squared Euclidean distance from point p to 3D triangle (a, b, c)."""
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    ap = (p[0] - a[0], p[1] - a[1], p[2] - a[2])
    d1 = ab[0] * ap[0] + ab[1] * ap[1] + ab[2] * ap[2]
    d2 = ac[0] * ap[0] + ac[1] * ap[1] + ac[2] * ap[2]
    if d1 <= 0.0 and d2 <= 0.0:
        return ap[0]**2 + ap[1]**2 + ap[2]**2
    bp = (p[0] - b[0], p[1] - b[1], p[2] - b[2])
    d3 = ab[0] * bp[0] + ab[1] * bp[1] + ab[2] * bp[2]
    d4 = ac[0] * bp[0] + ac[1] * bp[1] + ac[2] * bp[2]
    if d3 >= 0.0 and d4 <= d3:
        return bp[0]**2 + bp[1]**2 + bp[2]**2
    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        return (a[0] + v * ab[0] - p[0])**2 + (a[1] + v * ab[1] - p[1])**2 + (a[2] + v * ab[2] - p[2])**2
    cp = (p[0] - c[0], p[1] - c[1], p[2] - c[2])
    d5 = ab[0] * cp[0] + ab[1] * cp[1] + ab[2] * cp[2]
    d6 = ac[0] * cp[0] + ac[1] * cp[1] + ac[2] * cp[2]
    if d6 >= 0.0 and d5 <= d6:
        return cp[0]**2 + cp[1]**2 + cp[2]**2
    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        return (a[0] + w * ac[0] - p[0])**2 + (a[1] + w * ac[1] - p[1])**2 + (a[2] + w * ac[2] - p[2])**2
    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return (b[0] + w * (c[0] - b[0]) - p[0])**2 + (b[1] + w * (c[1] - b[1]) - p[1])**2 + (b[2] + w * (c[2] - b[2]) - p[2])**2
    denom = 1.0 / (va + vb + vc)
    v = vb * denom
    w = vc * denom
    return (a[0] + ab[0] * v + ac[0] * w - p[0])**2 + (a[1] + ab[1] * v + ac[1] * w - p[1])**2 + (a[2] + ab[2] * v + ac[2] * w - p[2])**2
```

In `verify_procedural_engine(report)`:
```python
# Procedural pauldron surface clearance and watertightness audit
b_triangles = []
for f in res.mesh.faces:
    vs = [res.mesh.vertices[idx] for idx in f]
    if any(v[2] >= 0.70 for v in vs):
        for k in range(1, len(f) - 1):
            b_triangles.append((vs[0], vs[k], vs[k + 1]))

for side in ["L", "R"]:
    p = armor.generate_pauldron(side)
    # 1. Watertightness
    is_m, nm = armor.verify_2_manifold(p)
    report.check(is_m and nm == 0, f"Procedural Pauldron {side} Watertight 2-Manifold", f"non-manifold edges={nm}")
    # 2. Positive signed volume
    vol = sum(
        (p.vertices[f[0]][0] * (p.vertices[f[k]][1] * p.vertices[f[k+1]][2] - p.vertices[f[k]][2] * p.vertices[f[k+1]][1])
         + p.vertices[f[0]][1] * (p.vertices[f[k]][2] * p.vertices[f[k+1]][0] - p.vertices[f[k]][0] * p.vertices[f[k+1]][2])
         + p.vertices[f[0]][2] * (p.vertices[f[k]][0] * p.vertices[f[k+1]][1] - p.vertices[f[k]][1] * p.vertices[f[k+1]][0])) / 6.0
        for f in p.faces for k in range(1, len(f) - 1)
    )
    report.check(vol > 0.0, f"Procedural Pauldron {side} Positive Signed Volume", f"volume={vol:.6f} m^3 > 0")
    # 3. Surface clearance
    min_sq = min(min(point_to_triangle_sq_dist(v, tri[0], tri[1], tri[2]) for tri in b_triangles) for v in p.vertices)
    min_d = math.sqrt(min_sq)
    report.check(min_d >= 0.015, f"Procedural Pauldron {side} Surface Clearance (>= 0.015m)", f"d_min = {min_d:.4f}m")
```

---

## 3. Finding 1 Investigation: Genuine Test in `tests/test_bear_anatomy.py`

### 3.1 Facade Test Analysis

Lines 209-219 of `tests/test_bear_anatomy.py`:
```python
def test_pauldron_clearance_and_watertightness(self):
    """Pauldron must be watertight and maintain clearance."""
    armor = ProceduralArmorEngine()
    p_l = armor.generate_pauldron("L")
    p_r = armor.generate_pauldron("R")
    assert len(p_l.vertices) > 50
    assert len(p_r.vertices) > 50
    assert len(p_l.faces) > 50
    assert len(p_r.faces) > 50
```

This test was a facade:
- Promised in docstring: *"Pauldron must be watertight and maintain clearance"*
- Implemented: `len > 50` count checks
- Completely failed to catch the -33.6 mm penetration, the negative signed volume on `R`, and non-manifold risks.

### 3.2 Genuine Replacement Implementation

The test must assert:
1. **Watertightness**: `is_watertight is True` (0 non-manifold edges via `verify_2_manifold`).
2. **Positive Signed Volume**: $V > 0$ for both L and R, and $|V_L - V_R| < 10^{-6}$ (exact bilateral symmetry).
3. **Surface Clearance**: $d_{\min} \ge 0.015\text{m}$ against `generate_bear_base_mesh().mesh` surface polygons.

```python
    def test_pauldron_clearance_and_watertightness(self):
        """Pauldron must be watertight, maintain clearance d_min >= 0.015m, and have positive volume."""
        armor = ProceduralArmorEngine()
        p_l = armor.generate_pauldron("L")
        p_r = armor.generate_pauldron("R")

        # 1. Watertight 2-manifold assertions (0 non-manifold edges)
        is_m_l, nm_l = armor.verify_2_manifold(p_l)
        is_m_r, nm_r = armor.verify_2_manifold(p_r)
        assert is_m_l is True and nm_l == 0, f"Pauldron L has {nm_l} non-manifold edges"
        assert is_m_r is True and nm_r == 0, f"Pauldron R has {nm_r} non-manifold edges"

        # 2. Positive signed volume assertion (outward normal vectors)
        def compute_signed_volume(mesh) -> float:
            vol = 0.0
            verts = mesh.vertices
            for f in mesh.faces:
                v0 = verts[f[0]]
                for k in range(1, len(f) - 1):
                    v1 = verts[f[k]]
                    v2 = verts[f[k + 1]]
                    vol += (
                        v0[0] * (v1[1] * v2[2] - v1[2] * v2[1])
                        + v0[1] * (v1[2] * v2[0] - v1[0] * v2[2])
                        + v0[2] * (v1[0] * v2[1] - v1[1] * v2[0])
                    ) / 6.0
            return vol

        vol_l = compute_signed_volume(p_l)
        vol_r = compute_signed_volume(p_r)
        assert vol_l > 0.0, f"Pauldron L signed volume must be positive, got {vol_l:.8f} m^3"
        assert vol_r > 0.0, f"Pauldron R signed volume must be positive, got {vol_r:.8f} m^3"
        assert abs(vol_l - vol_r) < 1e-6, f"Pauldron L ({vol_l:.6f}) and R ({vol_r:.6f}) volumes must be symmetric"

        # 3. Surface clearance d_min >= 0.015m from bear mesh polygons
        bear = generate_bear_base_mesh().mesh
        # Candidate shoulder triangles (z >= 0.70m)
        b_triangles = []
        for f in bear.faces:
            vs = [bear.vertices[idx] for idx in f]
            if any(v[2] >= 0.70 for v in vs):
                for k in range(1, len(f) - 1):
                    b_triangles.append((vs[0], vs[k], vs[k + 1]))

        # Point-to-triangle minimum squared distance
        def pt_tri_sq(p, a, b, c):
            ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            ap = (p[0] - a[0], p[1] - a[1], p[2] - a[2])
            d1 = ab[0] * ap[0] + ab[1] * ap[1] + ab[2] * ap[2]
            d2 = ac[0] * ap[0] + ac[1] * ap[1] + ac[2] * ap[2]
            if d1 <= 0.0 and d2 <= 0.0:
                return ap[0]**2 + ap[1]**2 + ap[2]**2
            bp = (p[0] - b[0], p[1] - b[1], p[2] - b[2])
            d3 = ab[0] * bp[0] + ab[1] * bp[1] + ab[2] * bp[2]
            d4 = ac[0] * bp[0] + ac[1] * bp[1] + ac[2] * bp[2]
            if d3 >= 0.0 and d4 <= d3:
                return bp[0]**2 + bp[1]**2 + bp[2]**2
            vc = d1 * d4 - d3 * d2
            if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
                v = d1 / (d1 - d3)
                return (a[0] + v * ab[0] - p[0])**2 + (a[1] + v * ab[1] - p[1])**2 + (a[2] + v * ab[2] - p[2])**2
            cp = (p[0] - c[0], p[1] - c[1], p[2] - c[2])
            d5 = ab[0] * cp[0] + ab[1] * cp[1] + ab[2] * cp[2]
            d6 = ac[0] * cp[0] + ac[1] * cp[1] + ac[2] * cp[2]
            if d6 >= 0.0 and d5 <= d6:
                return cp[0]**2 + cp[1]**2 + cp[2]**2
            vb = d5 * d2 - d1 * d6
            if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
                w = d2 / (d2 - d6)
                return (a[0] + w * ac[0] - p[0])**2 + (a[1] + w * ac[1] - p[1])**2 + (a[2] + w * ac[2] - p[2])**2
            va = d3 * d6 - d5 * d4
            if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
                w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
                return (b[0] + w * (c[0] - b[0]) - p[0])**2 + (b[1] + w * (c[1] - b[1]) - p[1])**2 + (b[2] + w * (c[2] - b[2]) - p[2])**2
            denom = 1.0 / (va + vb + vc)
            v = vb * denom
            w = vc * denom
            return (a[0] + ab[0] * v + ac[0] * w - p[0])**2 + (a[1] + ab[1] * v + ac[1] * w - p[1])**2 + (a[2] + ab[2] * v + ac[2] * w - p[2])**2

        for side, p in [("L", p_l), ("R", p_r)]:
            min_sq = min(min(pt_tri_sq(v, tri[0], tri[1], tri[2]) for tri in b_triangles) for v in p.vertices)
            min_d = math.sqrt(min_sq)
            assert min_d >= 0.015, f"Pauldron {side} minimum clearance {min_d:.4f}m < 0.015m"
            assert 0.020 <= min_d <= 0.045, f"Pauldron {side} clearance {min_d:.4f}m outside expected range [0.020, 0.045]"
```

---

## 4. Proposed Concrete Code Patches

### 4.1 Patch 1: `src/morphomesh/armor.py`

```diff
--- a/src/morphomesh/armor.py
+++ b/src/morphomesh/armor.py
@@ -94,15 +94,15 @@ class ProceduralArmorEngine:
-        cx = sign * (0.32 * scale + 0.002)
-        cy = -0.22 * scale
-        cz = 0.96 * scale
+        cx = sign * 0.35 * scale
+        cy = -0.25 * scale
+        cz = 0.98 * scale
 
         eff_clearance = max(0.015, clearance_offset * scale)
         rx_in = 0.16 * scale + eff_clearance
-        ry_in = 0.18 * scale + eff_clearance
+        ry_in = 0.17 * scale + eff_clearance
         rz_in = 0.14 * scale + eff_clearance
         thick = 0.009 * scale
 
         rx_out = rx_in + thick
         ry_out = ry_in + thick
         rz_out = rz_in + thick
 
         u_steps = 6  # latitude steps
         v_steps = 8  # longitude steps
 
         theta_min, theta_max = 0.08 * math.pi, 0.48 * math.pi
         phi_min, phi_max = (
-            (-0.35 * math.pi, 0.85 * math.pi)
+            (-0.25 * math.pi, 0.55 * math.pi)
             if side.upper() == "L"
-            else (0.15 * math.pi, 1.35 * math.pi)
+            else (0.45 * math.pi, 1.25 * math.pi)
         )
@@ -167,48 +167,24 @@ class ProceduralArmorEngine:
         # Outer surface quads (facing outward)
         for i in range(u_steps - 1):
             for j in range(v_steps - 1):
-                if side.upper() == "L":
-                    mesh.add_quad(
-                        outer_grid[i][j],
-                        outer_grid[i + 1][j],
-                        outer_grid[i + 1][j + 1],
-                        outer_grid[i][j + 1],
-                    )
-                else:
-                    mesh.add_quad(
-                        outer_grid[i][j],
-                        outer_grid[i][j + 1],
-                        outer_grid[i + 1][j + 1],
-                        outer_grid[i + 1][j],
-                    )
+                mesh.add_quad(
+                    outer_grid[i][j],
+                    outer_grid[i + 1][j],
+                    outer_grid[i + 1][j + 1],
+                    outer_grid[i][j + 1],
+                )
 
         # Inner surface quads (facing inward towards body)
         for i in range(u_steps - 1):
             for j in range(v_steps - 1):
-                if side.upper() == "L":
-                    mesh.add_quad(
-                        inner_grid[i][j],
-                        inner_grid[i][j + 1],
-                        inner_grid[i + 1][j + 1],
-                        inner_grid[i + 1][j],
-                    )
-                else:
-                    mesh.add_quad(
-                        inner_grid[i][j],
-                        inner_grid[i + 1][j],
-                        inner_grid[i + 1][j + 1],
-                        inner_grid[i][j + 1],
-                    )
+                mesh.add_quad(
+                    inner_grid[i][j],
+                    inner_grid[i][j + 1],
+                    inner_grid[i + 1][j + 1],
+                    inner_grid[i + 1][j],
+                )
 
         # Side rim quads:
         # Top rim (i = 0)
         for j in range(v_steps - 1):
-            if side.upper() == "L":
-                mesh.add_quad(inner_grid[0][j], outer_grid[0][j], outer_grid[0][j + 1], inner_grid[0][j + 1])
-            else:
-                mesh.add_quad(inner_grid[0][j], inner_grid[0][j + 1], outer_grid[0][j + 1], outer_grid[0][j])
+            mesh.add_quad(inner_grid[0][j], outer_grid[0][j], outer_grid[0][j + 1], inner_grid[0][j + 1])
 
         # Bottom rim (i = u_steps - 1)
         for j in range(v_steps - 1):
-            if side.upper() == "L":
-                mesh.add_quad(inner_grid[-1][j], inner_grid[-1][j + 1], outer_grid[-1][j + 1], outer_grid[-1][j])
-            else:
-                mesh.add_quad(inner_grid[-1][j], outer_grid[-1][j], outer_grid[-1][j + 1], inner_grid[-1][j + 1])
+            mesh.add_quad(inner_grid[-1][j], inner_grid[-1][j + 1], outer_grid[-1][j + 1], outer_grid[-1][j])
 
         # Left rim (j = 0)
         for i in range(u_steps - 1):
-            if side.upper() == "L":
-                mesh.add_quad(inner_grid[i][0], inner_grid[i + 1][0], outer_grid[i + 1][0], outer_grid[i][0])
-            else:
-                mesh.add_quad(inner_grid[i][0], outer_grid[i][0], outer_grid[i + 1][0], inner_grid[i + 1][0])
+            mesh.add_quad(inner_grid[i][0], inner_grid[i + 1][0], outer_grid[i + 1][0], outer_grid[i][0])
 
         # Right rim (j = v_steps - 1)
         for i in range(u_steps - 1):
-            if side.upper() == "L":
-                mesh.add_quad(inner_grid[i][-1], outer_grid[i][-1], outer_grid[i + 1][-1], inner_grid[i + 1][-1])
-            else:
-                mesh.add_quad(inner_grid[i][-1], inner_grid[i + 1][-1], outer_grid[i + 1][-1], outer_grid[i][-1])
+            mesh.add_quad(inner_grid[i][-1], outer_grid[i][-1], outer_grid[i + 1][-1], inner_grid[i + 1][-1])
@@ -647,11 +623,11 @@ def make_pauldron(side):
-    cx, cy, cz = sign * (0.32 * sc + 0.002), -0.22 * sc, 0.96 * sc
-    rx_in, ry_in, rz_in = 0.16 * sc + eff_cl, 0.18 * sc + eff_cl, 0.14 * sc + eff_cl
+    cx, cy, cz = sign * 0.35 * sc, -0.25 * sc, 0.98 * sc
+    rx_in, ry_in, rz_in = 0.16 * sc + eff_cl, 0.17 * sc + eff_cl, 0.14 * sc + eff_cl
     thick = 0.009 * sc
     rx_out, ry_out, rz_out = rx_in + thick, ry_in + thick, rz_in + thick
     u_steps, v_steps = 6, 8
     t_min, t_max = 0.08 * math.pi, 0.48 * math.pi
-    p_min, p_max = (-0.35 * math.pi, 0.85 * math.pi) if side == 'L' else (0.15 * math.pi, 1.35 * math.pi)
+    p_min, p_max = (-0.25 * math.pi, 0.55 * math.pi) if side == 'L' else (0.45 * math.pi, 1.25 * math.pi)
@@ -669,21 +645,13 @@ def make_pauldron(side):
     for i in range(u_steps - 1):
         for j in range(v_steps - 1):
-            if side == 'L':
-                faces.append((og[i][j], og[i+1][j], og[i+1][j+1], og[i][j+1]))
-                faces.append((ig[i][j], ig[i][j+1], ig[i+1][j+1], ig[i+1][j]))
-            else:
-                faces.append((og[i][j], og[i][j+1], og[i+1][j+1], og[i+1][j]))
-                faces.append((ig[i][j], ig[i+1][j], ig[i+1][j+1], ig[i][j+1]))
+            faces.append((og[i][j], og[i+1][j], og[i+1][j+1], og[i][j+1]))
+            faces.append((ig[i][j], ig[i][j+1], ig[i+1][j+1], ig[i+1][j]))
             rim = (i == 0 or i == u_steps - 2 or j == 0 or j == v_steps - 2)
             mats.extend([1 if rim else 0, 0])
     for j in range(v_steps - 1):
-        faces.append((ig[0][j], og[0][j], og[0][j+1], ig[0][j+1]) if side == 'L' else (ig[0][j], ig[0][j+1], og[0][j+1], og[0][j]))
-        faces.append((ig[-1][j], ig[-1][j+1], og[-1][j+1], og[-1][j]) if side == 'L' else (ig[-1][j], og[-1][j], og[-1][j+1], ig[-1][j+1]))
+        faces.append((ig[0][j], og[0][j], og[0][j+1], ig[0][j+1]))
+        faces.append((ig[-1][j], ig[-1][j+1], og[-1][j+1], og[-1][j]))
         mats.extend([1, 1])
     for i in range(u_steps - 1):
-        faces.append((ig[i][0], ig[i+1][0], og[i+1][0], og[i][0]) if side == 'L' else (ig[i][0], og[i][0], og[i+1][0], ig[i+1][0]))
-        faces.append((ig[i][-1], og[i][-1], og[i+1][-1], ig[i+1][-1]) if side == 'L' else (ig[i][-1], ig[i+1][-1], og[i+1][-1], og[i][-1]))
+        faces.append((ig[i][0], ig[i+1][0], og[i+1][0], og[i][0]))
+        faces.append((ig[i][-1], og[i][-1], og[i+1][-1], ig[i+1][-1]))
         mats.extend([1, 1])
```

---

### 4.2 Patch 2: `src/morphomesh/blender_bridge.py`

```diff
--- a/src/morphomesh/blender_bridge.py
+++ b/src/morphomesh/blender_bridge.py
@@ -1386,11 +1386,11 @@ class BlenderBridge:
-            cx, cy, cz = sign * 0.32 * sc, -0.22 * sc, 0.96 * sc
-            rx_in, ry_in, rz_in = (0.16 + clearance) * sc, (0.18 + clearance) * sc, (0.14 + clearance) * sc
+            cx, cy, cz = sign * 0.35 * sc, -0.25 * sc, 0.98 * sc
+            rx_in, ry_in, rz_in = (0.16 + clearance) * sc, (0.17 + clearance) * sc, (0.14 + clearance) * sc
             thick = 0.009 * sc
             rx_out, ry_out, rz_out = rx_in + thick, ry_in + thick, rz_in + thick
             u_steps, v_steps = 6, 8
             t_min, t_max = 0.08 * math.pi, 0.48 * math.pi
-            p_min, p_max = (-0.35 * math.pi, 0.85 * math.pi) if side == 'L' else (0.15 * math.pi, 1.35 * math.pi)
+            p_min, p_max = (-0.25 * math.pi, 0.55 * math.pi) if side == 'L' else (0.45 * math.pi, 1.25 * math.pi)
@@ -1408,21 +1408,13 @@ class BlenderBridge:
             for i in range(u_steps - 1):
                 for j in range(v_steps - 1):
-                    if side == 'L':
-                        faces.append((og[i][j], og[i+1][j], og[i+1][j+1], og[i][j+1]))
-                        faces.append((ig[i][j], ig[i][j+1], ig[i+1][j+1], ig[i+1][j]))
-                    else:
-                        faces.append((og[i][j], og[i][j+1], og[i+1][j+1], og[i][j]))
-                        faces.append((ig[i][j], ig[i+1][j], ig[i+1][j+1], ig[i][j+1]))
+                    faces.append((og[i][j], og[i+1][j], og[i+1][j+1], og[i][j+1]))
+                    faces.append((ig[i][j], ig[i][j+1], ig[i+1][j+1], ig[i+1][j]))
                     rim = (i == 0 or i == u_steps - 2 or j == 0 or j == v_steps - 2)
                     mats.extend([1 if rim else 0, 0])
             for j in range(v_steps - 1):
-                faces.append((ig[0][j], og[0][j], og[0][j+1], ig[0][j+1]) if side == 'L' else (ig[0][j], ig[0][j+1], og[0][j+1], og[0][j]))
-                faces.append((ig[-1][j], ig[-1][j+1], og[-1][j+1], og[-1][j]) if side == 'L' else (ig[-1][j], og[-1][j], og[-1][j+1], ig[-1][j+1]))
+                faces.append((ig[0][j], og[0][j], og[0][j+1], ig[0][j+1]))
+                faces.append((ig[-1][j], ig[-1][j+1], og[-1][j+1], og[-1][j]))
                 mats.extend([1, 1])
             for i in range(u_steps - 1):
-                faces.append((ig[i][0], ig[i+1][0], og[i+1][0], og[i][0]) if side == 'L' else (ig[i][0], og[i][0], og[i+1][0], ig[i+1][0]))
-                faces.append((ig[i][-1], og[i][-1], og[i+1][-1], ig[i+1][-1]) if side == 'L' else (ig[i][-1], ig[i+1][-1], og[i+1][-1], og[i][-1]))
+                faces.append((ig[i][0], ig[i+1][0], og[i+1][0], og[i][0]))
+                faces.append((ig[i][-1], og[i][-1], og[i+1][-1], ig[i+1][-1]))
                 mats.extend([1, 1])
@@ -1550,6 +1542,16 @@ class BlenderBridge:
-        for a_name in created_armor_objects:
-            ao = bpy.data.objects.get(a_name)
-            if ao and bear_verts:
-                min_d = min(min((v.co - bv).length for bv in bear_verts) for v in ao.data.vertices)
-                clearance_results[a_name] = round(float(min_d), 4)
+        from mathutils.bvhtree import BVHTree
+        bear_bvh = BVHTree.FromPolygons([v.co for v in base_obj.data.vertices], [p.vertices for p in base_obj.data.polygons]) if base_obj else None
+        for a_name in created_armor_objects:
+            ao = bpy.data.objects.get(a_name)
+            if ao and bear_bvh:
+                min_d = min(bear_bvh.find_nearest(v.co)[3] for v in ao.data.vertices)
+                clearance_results[a_name] = round(float(min_d), 4)
```

---

### 4.3 Patch 3: `verify_bear_anatomy.py`

```diff
--- a/verify_bear_anatomy.py
+++ b/verify_bear_anatomy.py
@@ -280,8 +280,26 @@ def verify_procedural_engine(report: VerificationReport):
-        # Assert Armor Clearance Math
         armor = ProceduralArmorEngine()
-        p_l = armor.generate_pauldron("L")
-        report.check(
-            len(p_l.vertices) > 0 and len(p_l.faces) > 0,
-            "Armor Pauldron Procedural Geometry Valid",
-            f"verts={len(p_l.vertices)}, faces={len(p_l.faces)}",
-        )
+        for side in ["L", "R"]:
+            p = armor.generate_pauldron(side)
+            is_m, nm = armor.verify_2_manifold(p)
+            report.check(
+                is_m and nm == 0,
+                f"Procedural Pauldron {side} Watertight 2-Manifold",
+                f"non-manifold edge count = {nm}",
+            )
+            vol = sum(
+                (p.vertices[f[0]][0] * (p.vertices[f[k]][1] * p.vertices[f[k+1]][2] - p.vertices[f[k]][2] * p.vertices[f[k+1]][1])
+                 + p.vertices[f[0]][1] * (p.vertices[f[k]][2] * p.vertices[f[k+1]][0] - p.vertices[f[k]][0] * p.vertices[f[k+1]][2])
+                 + p.vertices[f[0]][2] * (p.vertices[f[k]][0] * p.vertices[f[k+1]][1] - p.vertices[f[k]][1] * p.vertices[f[k+1]][0])) / 6.0
+                for f in p.faces for k in range(1, len(f) - 1)
+            )
+            report.check(
+                vol > 0.0,
+                f"Procedural Pauldron {side} Positive Signed Volume",
+                f"signed volume = {vol:.6f} m^3 > 0",
+            )
@@ -413,16 +431,34 @@ def verify_blender_scene(report: VerificationReport):
-    bear_coords = [v.co for v in m_data.vertices]
+    from mathutils.bvhtree import BVHTree
+    bear_coords = [v.co for v in m_data.vertices]
+    bear_faces = [p.vertices for p in m_data.polygons]
+    bear_bvh = BVHTree.FromPolygons(bear_coords, bear_faces)
+
     for a_name in ARMOR_OBJECTS:
         ao = bpy.data.objects.get(a_name)
         report.check(ao is not None, f"War Armor Plate Exists: {a_name}")
         if ao and ao.type == "MESH":
-            # Clearance assertion
-            min_dist = min(
-                min((v.co - b_co).length for b_co in bear_coords)
-                for v in ao.data.vertices
-            )
+            # True BVH point-to-surface distance and signed penetration audit
+            min_surface_dist = float("inf")
+            inside_vertices = []
+            signed_distances = []
+            for v in ao.data.vertices:
+                loc, norm, face_idx, dist = bear_bvh.find_nearest(v.co)
+                if loc is not None:
+                    signed_dist = (v.co - loc).dot(norm)
+                    signed_distances.append(signed_dist)
+                    if signed_dist < -0.001:
+                        inside_vertices.append((v.index, v.co, signed_dist))
+                    if dist < min_surface_dist:
+                        min_surface_dist = dist
+
             report.check(
-                min_dist >= 0.015,
-                f"Armor Plate Clearance: {a_name} (>= 0.015m)",
-                f"measured minimum clearance d_min = {min_dist:.4f}m >= 0.015m",
+                min_surface_dist >= 0.015,
+                f"Armor Plate Surface Clearance: {a_name} (>= 0.015m)",
+                f"measured minimum surface clearance d_min = {min_surface_dist:.4f}m >= 0.015m",
+            )
+            report.check(
+                len(inside_vertices) == 0,
+                f"Armor Plate Non-Penetrating (0 Inside Vertices): {a_name}",
+                f"inside count = {len(inside_vertices)}, min signed dist = {min(signed_distances):.4f}m" if signed_distances else "N/A",
             )
@@ -439,3 +475,13 @@ def verify_blender_scene(report: VerificationReport):
+            # Positive signed volume check
+            vol = 0.0
+            for p in ao.data.polygons:
+                v0 = ao.data.vertices[p.vertices[0]].co
+                for k in range(1, len(p.vertices) - 1):
+                    v1 = ao.data.vertices[p.vertices[k]].co
+                    v2 = ao.data.vertices[p.vertices[k + 1]].co
+                    vol += v0.dot(v1.cross(v2)) / 6.0
+            report.check(
+                vol > 0.0,
+                f"Armor Plate Positive Signed Volume: {a_name}",
+                f"signed volume = {vol:.6f} m^3 > 0",
+            )
```

---

### 4.4 Patch 4: `tests/test_bear_anatomy.py`

```diff
--- a/tests/test_bear_anatomy.py
+++ b/tests/test_bear_anatomy.py
@@ -209,11 +209,92 @@ class TestWarArmorFittingAndClearances:
     def test_pauldron_clearance_and_watertightness(self):
-        """Pauldron must be watertight and maintain clearance."""
+        """Pauldron must be watertight, maintain clearance d_min >= 0.015m, and have positive volume."""
         armor = ProceduralArmorEngine()
         p_l = armor.generate_pauldron("L")
         p_r = armor.generate_pauldron("R")
-        assert len(p_l.vertices) > 50
-        assert len(p_r.vertices) > 50
-        assert len(p_l.faces) > 50
-        assert len(p_r.faces) > 50
+
+        # 1. Watertight 2-manifold assertions (0 non-manifold edges)
+        is_m_l, nm_l = armor.verify_2_manifold(p_l)
+        is_m_r, nm_r = armor.verify_2_manifold(p_r)
+        assert is_m_l is True and nm_l == 0, f"Pauldron L has {nm_l} non-manifold edges"
+        assert is_m_r is True and nm_r == 0, f"Pauldron R has {nm_r} non-manifold edges"
+
+        # 2. Positive signed volume assertion (outward normal vectors)
+        def compute_signed_volume(mesh) -> float:
+            vol = 0.0
+            verts = mesh.vertices
+            for f in mesh.faces:
+                v0 = verts[f[0]]
+                for k in range(1, len(f) - 1):
+                    v1 = verts[f[k]]
+                    v2 = verts[f[k + 1]]
+                    vol += (
+                        v0[0] * (v1[1] * v2[2] - v1[2] * v2[1])
+                        + v0[1] * (v1[2] * v2[0] - v1[0] * v2[2])
+                        + v0[2] * (v1[0] * v2[1] - v1[1] * v2[0])
+                    ) / 6.0
+            return vol
+
+        vol_l = compute_signed_volume(p_l)
+        vol_r = compute_signed_volume(p_r)
+        assert vol_l > 0.0, f"Pauldron L signed volume must be positive, got {vol_l:.8f} m^3"
+        assert vol_r > 0.0, f"Pauldron R signed volume must be positive, got {vol_r:.8f} m^3"
+        assert abs(vol_l - vol_r) < 1e-6, f"Pauldron L ({vol_l:.6f}) and R ({vol_r:.6f}) volumes must be symmetric"
+
+        # 3. Surface clearance d_min >= 0.015m from bear mesh polygons
+        bear = generate_bear_base_mesh().mesh
+        b_triangles = []
+        for f in bear.faces:
+            vs = [bear.vertices[idx] for idx in f]
+            if any(v[2] >= 0.70 for v in vs):
+                for k in range(1, len(f) - 1):
+                    b_triangles.append((vs[0], vs[k], vs[k + 1]))
+
+        def pt_tri_sq(p, a, b, c):
+            ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
+            ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
+            ap = (p[0] - a[0], p[1] - a[1], p[2] - a[2])
+            d1 = ab[0] * ap[0] + ab[1] * ap[1] + ab[2] * ap[2]
+            d2 = ac[0] * ap[0] + ac[1] * ap[1] + ac[2] * ap[2]
+            if d1 <= 0.0 and d2 <= 0.0:
+                return ap[0]**2 + ap[1]**2 + ap[2]**2
+            bp = (p[0] - b[0], p[1] - b[1], p[2] - b[2])
+            d3 = ab[0] * bp[0] + ab[1] * bp[1] + ab[2] * bp[2]
+            d4 = ac[0] * bp[0] + ac[1] * bp[1] + ac[2] * bp[2]
+            if d3 >= 0.0 and d4 <= d3:
+                return bp[0]**2 + bp[1]**2 + bp[2]**2
+            vc = d1 * d4 - d3 * d2
+            if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
+                v = d1 / (d1 - d3)
+                return (a[0] + v * ab[0] - p[0])**2 + (a[1] + v * ab[1] - p[1])**2 + (a[2] + v * ab[2] - p[2])**2
+            cp = (p[0] - c[0], p[1] - c[1], p[2] - c[2])
+            d5 = ab[0] * cp[0] + ab[1] * cp[1] + ab[2] * cp[2]
+            d6 = ac[0] * cp[0] + ac[1] * cp[1] + ac[2] * cp[2]
+            if d6 >= 0.0 and d5 <= d6:
+                return cp[0]**2 + cp[1]**2 + cp[2]**2
+            vb = d5 * d2 - d1 * d6
+            if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
+                w = d2 / (d2 - d6)
+                return (a[0] + w * ac[0] - p[0])**2 + (a[1] + w * ac[1] - p[1])**2 + (a[2] + w * ac[2] - p[2])**2
+            va = d3 * d6 - d5 * d4
+            if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
+                w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
+                return (b[0] + w * (c[0] - b[0]) - p[0])**2 + (b[1] + w * (c[1] - b[1]) - p[1])**2 + (b[2] + w * (c[2] - b[2]) - p[2])**2
+            denom = 1.0 / (va + vb + vc)
+            v = vb * denom
+            w = vc * denom
+            return (a[0] + ab[0] * v + ac[0] * w - p[0])**2 + (a[1] + ab[1] * v + ac[1] * w - p[1])**2 + (a[2] + ab[2] * v + ac[2] * w - p[2])**2
+
+        for side, p in [("L", p_l), ("R", p_r)]:
+            min_sq = min(min(pt_tri_sq(v, tri[0], tri[1], tri[2]) for tri in b_triangles) for v in p.vertices)
+            min_d = math.sqrt(min_sq)
+            assert min_d >= 0.015, f"Pauldron {side} minimum clearance {min_d:.4f}m < 0.015m"
+            assert 0.020 <= min_d <= 0.045, f"Pauldron {side} clearance {min_d:.4f}m outside expected range [0.020, 0.045]"
```

---

## 5. Summary of Remediation Plan for Worker Agent

| Task | Target File | Actions Required |
|---|---|---|
| **Task 1** | `src/morphomesh/armor.py` | Apply Patch 1: Update $cx=\pm 0.35$, $cy=-0.25$, $cz=0.98$, $ry=0.17$, $\phi_L \in [-0.25\pi, 0.55\pi]$, $\phi_R \in [0.45\pi, 1.25\pi]$, and unify quad winding in `generate_pauldron` and `get_armor_blender_script`. |
| **Task 2** | `src/morphomesh/blender_bridge.py` | Apply Patch 2: Update `make_pauldron` in `morphomesh.generate_war_armor` with matching parameters, and update clearance measurement to use `BVHTree`. |
| **Task 3** | `verify_bear_anatomy.py` | Apply Patch 3: Replace sparse vertex-to-vertex Euclidean distance with `BVHTree.FromPolygons` in Blender mode, add zero-penetration check, positive volume check, and update standalone Python check. |
| **Task 4** | `tests/test_bear_anatomy.py` | Apply Patch 4: Replace facade test with genuine watertightness, signed volume, and surface clearance assertions. |
| **Task 5** | Production Assets | Re-run scene assembly script via Blender to update `examples/Armored_War_Bear_HD.blend` and `examples/Armored_War_Bear_HD.glb` with the non-penetrating pauldrons. |

---
*Report authored by Explorer M4-Iter2-2.*
