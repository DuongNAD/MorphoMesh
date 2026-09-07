# Handoff Report — Explorer M3 Iteration 2 - 2: Recommendations, Volume & Coplanar Intersections Remediation

**Agent**: Explorer M3 Iteration 2 - 2 (teamwork explorer)  
**Roles**: explorer  
**Working Directory**: `e:\tool\mcp\MorphoMesh\.agents\explorer_m3_iter2_2`  
**Parent Orchestrator Conversation ID**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Milestone**: Milestone 3 Iteration 2  
**Date**: 2026-09-07T06:10:00Z  

---

## 1. Observation

### 1.1 Inaccurate Actionable Recommendations in `src/morphomesh/visual_critic.py`
1. **Shrinkwrap Modifier Offset & Guidance**:
   - In `src/morphomesh/visual_critic.py` lines 754–761:
     ```python
     recommendation=ActionableRecommendation(
         action="APPLY_SHRINKWRAP_CLEARANCE",
         category=DefectCategory.PENETRATION,
         target_objects=[g_name],
         suggested_modifier="Shrinkwrap",
         parameters={"target": body_obj_name, "offset": round(max(0.002, max_depth_m * 1.5), 4)},
         guidance=f"Apply Shrinkwrap modifier to '{g_name}' targeting '{body_obj_name}' with offset >= {max_depth_mm + 0.5:.1f}mm.",
     )
     ```
   - *Observation*: The current offset parameter uses an ad-hoc formula `round(max(0.002, max_depth_m * 1.5), 4)` and the guidance string instructs `max_depth_mm + 0.5`. This directly violates the authoritative requirement for $d_{\text{rec}} = 1.25 \times d_{\text{pen}} + 1\text{mm}$ ($1.25 \times d_{\text{pen}} + 0.001\text{m}$). Furthermore, there is zero mention of vertex weight smoothing guidance (`"Apply vertex weight proximity or Laplacian smoothing to the penetration vertex group"`).

2. **Hair Grooming Curve Sculpt Comb Brush Omission**:
   - In `src/morphomesh/visual_critic.py` lines 965–972, 988–1009, and 1012–1025:
     ```python
     # Submerged roots recommendation:
     recommendation=ActionableRecommendation(
         action="PROJECT_HAIR_ROOTS_TO_SCALP",
         category=DefectCategory.GROOMING_COLLISION,
         target_objects=[h_name],
         parameters={"offset_mm": 1.0},
         guidance="Project hair curve root control points to scalp surface with +1.0mm normal clearance.",
     )
     # Shaft collisions recommendation:
     recommendation=ActionableRecommendation(
         action="ADD_SURFACE_COLLISION_DEFORMER",
         category=DefectCategory.GROOMING_COLLISION,
         target_objects=[h_name],
         guidance="Add Geometry Nodes hair curve collision deformer with scalp/torso pushout.",
     )
     # Garment collisions: NO recommendation attached
     ```
   - *Observation*: The string `"comb"` or `"Comb"` does not appear anywhere in `visual_critic.py`. The system omits Blender's Curves Sculpt mode Comb Brush workflow required for hair-body and hair-garment deflection.

### 1.2 Tomas Möller Coplanar Triangle-Triangle Intersection Bypass
1. **Immediate False Return on Coplanar Triangles**:
   - In `src/morphomesh/visual_critic.py` lines 272–277:
     ```python
     d_dir = _cross_product(n1, n2)
     max_d = max(abs(d_dir[0]), abs(d_dir[1]), abs(d_dir[2]))
     if max_d < 1e-8:
         # Triangles are coplanar or nearly parallel
         return False
     ```
   - *Observation*: When two triangles are coplanar, their surface normals $n_1$ and $n_2$ are parallel/anti-parallel, resulting in $|n_1 \times n_2| \approx 0$ (`max_d < 1e-8`). The function unconditionally returns `False`, bypassing the authentic 2D coplanar intersection logic specified in Tomas Möller's 1997 paper ("A Fast Triangle-Triangle Intersection Test", § 3).
2. **Existing Test Suite Masking**:
   - In `tests/test_adversarial_bvh_penetration.py` lines 266–273:
     ```python
     def test_coplanar_overlapping_triangles(self):
         """Coplanar triangles in standard Möller 3D test return False (handled by vertex signed distance)."""
         t1_v0, t1_v1, t1_v2 = (0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.0)
         t2_v0, t2_v1, t2_v2 = (0.5, 0.5, 0.0), (2.5, 0.5, 0.0), (0.5, 2.5, 0.0)
         # Möller returns False for coplanar triangles because cross product of identical normals is 0
         res = triangle_triangle_intersection_moller(t1_v0, t1_v1, t1_v2, t2_v0, t2_v1, t2_v2)
         assert res is False
     ```
   - *Observation*: This adversarial test was specifically coded to assert the *buggy* behavior (`assert res is False`). When authentic 2D coplanar intersection is implemented, this test will fail unless updated to `assert res is True`.

### 1.3 Quad Mesh Disregard in `compute_mesh_signed_volume`
1. **Omission of Second Quad Triangle**:
   - In `src/morphomesh/visual_critic.py` lines 1262–1277:
     ```python
     def compute_mesh_signed_volume(
         vertices: List[Tuple[float, float, float]],
         faces: List[Tuple[int, ...]],
     ) -> float:
         """Computes exact volume of watertight triangle mesh via divergence theorem."""
         vol = 0.0
         for f in faces:
             v1 = vertices[f[0]]
             v2 = vertices[f[1]]
             v3 = vertices[f[2]]
             cx = v2[1] * v3[2] - v2[2] * v3[1]
             cy = v2[2] * v3[0] - v2[0] * v3[2]
             cz = v2[0] * v3[1] - v2[1] * v3[0]
             vol += v1[0] * cx + v1[1] * cy + v1[2] * cz
         return abs(vol) / 6.0
     ```
   - *Observation*: For a quad face `(v0, v1, v2, v3)`, only `f[0], f[1], f[2]` are integrated. The second triangle `(f[0], f[2], f[3])` is silently dropped.
   - *Empirical Test Output*: On a unit cube $[-1, 1]^3$ defined with 6 quad faces, analytical volume is $8.0\text{m}^3$. `compute_mesh_signed_volume` evaluated to exactly $4.0000\text{m}^3$ (a 50% underestimation).

---

## 2. Logic Chain

1. **Issue 1 (Recommendations)**:
   - *Premise*: User prompt (§ 2026-09-07T03:34:32Z) and Reviewer M3_1 handoff mandate automated recommendations to provide exact actionable modifier offsets and brush guidance.
   - *Observation*: Line 759 sets `max(0.002, max_depth_m * 1.5)` without weight smoothing. Lines 965–1025 omit `"Curves Sculpt Comb Brush"`.
   - *Deduction*: Updating `parameters["offset"]` to `round(1.25 * max_depth_m + 0.001, 4)` and adding vertex weight Laplacian smoothing guidance directly satisfies the $d_{\text{rec}} = 1.25 \times d_{\text{pen}} + 1\text{mm}$ requirement. Adding `CURVE_SCULPT_COMB_DEFLECTION` with `"In Curves Sculpt Mode, use the Comb Brush with front/side projection to groom intersecting hair splines away from the scalp/garment surface"` provides the required human-in-the-loop and automation guidance.

2. **Issue 2 (Tomas Möller Coplanar Intersection)**:
   - *Premise*: Tomas Möller 1997 defines that two coplanar triangles intersect if and only if their 2D projections onto their dominant coordinate plane intersect.
   - *Observation*: If $|n_1 \times n_2| < 10^{-8}$, the triangles lie in parallel planes. Lines 255–270 have already verified that vertex plane distances $dv_i$ are not all $> 10^{-6}$ or all $< -10^{-6}$, meaning the planes are coincident (coplanar).
   - *Deduction*: Projecting onto the plane orthogonal to $\arg\max_i (|n_i|)$ preserves maximum 2D area. Testing 2D segment-segment intersection across the 9 edge pairs via 2D cross-product orientation (`ccw`), plus checking 2D point-in-triangle containment for vertices of $T_1$ in $T_2$ and $T_2$ in $T_1$, strictly detects all coplanar overlaps (partial overlap, edge touch, shared vertex, or full containment) while returning `False` for disjoint coplanar triangles.

3. **Issue 3 (Quad Mesh Signed Volume)**:
   - *Premise*: By Gauss's divergence theorem, the volume of any watertight closed polyhedron is the sum of signed pyramid volumes over all boundary faces: $V = \frac{1}{6} \left| \sum_f \vec{v}_0 \cdot (\vec{v}_1 \times \vec{v}_2) \right|$.
   - *Observation*: Any planar convex polygon $(v_0, v_1, \dots, v_{k-1})$ can be decomposed into $k-2$ triangles using fan triangulation: $(v_0, v_i, v_{i+1})$ for $i \in \{1, \dots, k-2\}$.
   - *Deduction*: Implementing `for i in range(1, len(f) - 1)` seamlessly handles triangles ($i=1$), quads ($i=1, 2$), and general n-gons. On a quad cube, this recovers the exact analytical volume $8.0000\text{m}^3$ (0.0% error) while preserving backward compatibility with existing triangle meshes.

---

## 3. Caveats

1. **Test Assertion Alignment in Peer Test Suite**:
   - `tests/test_adversarial_bvh_penetration.py:272` previously asserted `assert res is False` for coplanar triangles. When authentic 2D coplanar intersection is implemented, this assertion will rightfully fail. Worker M3 **must** update this assertion to `assert res is True` and add a disjoint coplanar test asserting `False`.
2. **Non-Planar Quads**:
   - Fan triangulation assumes character mesh quads are reasonably planar (standard for subdivision and game character meshes). Severely warped non-planar quads may have minor diagonal triangulation ambiguity, which is standard in all 3D DCC tools (Blender, Maya).
3. **Boundary Edges in Coplanar Intersection**:
   - Shared edges or shared vertices between coplanar triangles are evaluated as intersections. In BVH collision between two separate meshes (body vs garment), touching surface boundaries constitutes physical contact.

---

## 4. Conclusion & Complete Remediation Blueprints

### Blueprint 1: Actionable Recommendations in `src/morphomesh/visual_critic.py`

#### 1.1 In `evaluate_mesh_penetration` (Lines 754–761):
**Target Content**:
```python
                recommendation=ActionableRecommendation(
                    action="APPLY_SHRINKWRAP_CLEARANCE",
                    category=DefectCategory.PENETRATION,
                    target_objects=[g_name],
                    suggested_modifier="Shrinkwrap",
                    parameters={"target": body_obj_name, "offset": round(max(0.002, max_depth_m * 1.5), 4)},
                    guidance=f"Apply Shrinkwrap modifier to '{g_name}' targeting '{body_obj_name}' with offset >= {max_depth_mm + 0.5:.1f}mm.",
                ),
```
**Replacement Content**:
```python
                rec_offset_m = round(1.25 * max_depth_m + 0.001, 4)
                rec_offset_mm = round(1.25 * max_depth_mm + 1.0, 2)
                recommendation=ActionableRecommendation(
                    action="APPLY_SHRINKWRAP_CLEARANCE",
                    category=DefectCategory.PENETRATION,
                    target_objects=[g_name],
                    suggested_modifier="Shrinkwrap",
                    parameters={
                        "target": body_obj_name,
                        "offset": rec_offset_m,
                        "offset_m": rec_offset_m,
                        "offset_mm": rec_offset_mm,
                        "smooth_weights": True,
                        "smoothing_method": "LAPLACIAN",
                    },
                    guidance=(
                        f"Apply Shrinkwrap modifier to '{g_name}' targeting '{body_obj_name}' with offset >= {rec_offset_mm:.1f}mm "
                        f"(d_rec = 1.25 * d_pen + 1mm). Apply vertex weight proximity or Laplacian smoothing to the penetration vertex group."
                    ),
                ),
```

#### 1.2 In `evaluate_hair_grooming_intersections` (Lines 965–972, 1003–1009, 1012–1025):
**For Submerged Roots (Lines 965–972)**:
```python
                recommendation=ActionableRecommendation(
                    action="PROJECT_HAIR_ROOTS_TO_SCALP",
                    category=DefectCategory.GROOMING_COLLISION,
                    target_objects=[h_name],
                    parameters={"offset_mm": 1.0},
                    guidance=(
                        "Project hair curve root control points to scalp surface with +1.0mm normal clearance. "
                        "In Curves Sculpt Mode, use the Comb Brush with front/side projection to groom intersecting hair splines away from the scalp/garment surface."
                    ),
                ),
```
**For Shaft Collisions (Lines 1003–1009)**:
```python
                recommendation=ActionableRecommendation(
                    action="CURVE_SCULPT_COMB_DEFLECTION",
                    category=DefectCategory.GROOMING_COLLISION,
                    target_objects=[h_name, body_obj_name],
                    suggested_modifier="Curves Sculpt Comb",
                    parameters={"brush_mode": "COMB", "collision_distance_mm": 2.0, "falloff": "SMOOTH"},
                    guidance=(
                        f"In Curves Sculpt Mode, use the Comb Brush with front/side projection to groom intersecting hair splines "
                        f"away from the scalp/garment surface (enable surface collision with 2.0mm clearance against '{body_obj_name}')."
                    ),
                ),
```
**For Garment Collisions (Lines 1012–1025)**:
```python
                garm_target = garment_collisions[0]["garment"]
                recommendation=ActionableRecommendation(
                    action="CURVE_SCULPT_COMB_DEFLECTION",
                    category=DefectCategory.GROOMING_COLLISION,
                    target_objects=[h_name, garm_target],
                    suggested_modifier="Curves Sculpt Comb",
                    parameters={"brush_mode": "COMB", "collision_distance_mm": 2.0, "falloff": "SMOOTH"},
                    guidance=(
                        f"In Curves Sculpt Mode, use the Comb Brush with front/side projection to groom intersecting hair splines "
                        f"away from garment '{garm_target}' surface."
                    ),
                ),
```

---

### Blueprint 2: Tomas Möller 2D Coplanar Triangle Intersection in `src/morphomesh/visual_critic.py`

#### 2.1 Add 2D Geometric Helper Functions (Before Line 240):
```python
def _segments_intersect_2d(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
    d: Tuple[float, float],
    eps: float = 1e-8,
) -> bool:
    """Tests if 2D line segment ab intersects 2D line segment cd."""
    def ccw(p1, p2, p3):
        return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])

    def on_segment(p, q1, q2):
        return (
            min(q1[0], q2[0]) - eps <= p[0] <= max(q1[0], q2[0]) + eps and
            min(q1[1], q2[1]) - eps <= p[1] <= max(q1[1], q2[1]) + eps
        )

    d1 = ccw(a, b, c)
    d2 = ccw(a, b, d)
    d3 = ccw(c, d, a)
    d4 = ccw(c, d, b)

    # General crossing case (straddle)
    if ((d1 > eps and d2 < -eps) or (d1 < -eps and d2 > eps)) and \
       ((d3 > eps and d4 < -eps) or (d3 < -eps and d4 > eps)):
        return True

    # Collinear and endpoint cases
    if abs(d1) <= eps and on_segment(c, a, b):
        return True
    if abs(d2) <= eps and on_segment(d, a, b):
        return True
    if abs(d3) <= eps and on_segment(a, c, d):
        return True
    if abs(d4) <= eps and on_segment(b, c, d):
        return True

    return False


def _point_in_triangle_2d(
    p: Tuple[float, float],
    v0: Tuple[float, float],
    v1: Tuple[float, float],
    v2: Tuple[float, float],
    eps: float = 1e-8,
) -> bool:
    """Tests if 2D point p is inside or on the boundary of triangle (v0, v1, v2)."""
    def ccw(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    s0 = ccw(v0, v1, p)
    s1 = ccw(v1, v2, p)
    s2 = ccw(v2, v0, p)

    has_neg = (s0 < -eps) or (s1 < -eps) or (s2 < -eps)
    has_pos = (s0 > eps) or (s1 > eps) or (s2 > eps)

    return not (has_neg and has_pos)


def _coplanar_triangle_triangle_intersection_2d(
    t1_v0: Tuple[float, float, float],
    t1_v1: Tuple[float, float, float],
    t1_v2: Tuple[float, float, float],
    t2_v0: Tuple[float, float, float],
    t2_v1: Tuple[float, float, float],
    t2_v2: Tuple[float, float, float],
    normal: Tuple[float, float, float],
) -> bool:
    """
    Evaluates authentic 2D coplanar triangle-triangle intersection.
    Projects 3D coplanar triangles onto the dominant 2D coordinate plane
    (dropping the axis corresponding to the maximum normal component)
    and evaluates:
    1. 2D edge-edge intersection (9 edge pairs).
    2. Point-in-triangle containment (t1 vertices in t2, and t2 vertices in t1).
    """
    norm_sq = normal[0] * normal[0] + normal[1] * normal[1] + normal[2] * normal[2]
    if norm_sq < 1e-16:
        return False

    abs_x = abs(normal[0])
    abs_y = abs(normal[1])
    abs_z = abs(normal[2])

    if abs_x >= abs_y and abs_x >= abs_z:
        def proj(v): return (v[1], v[2])
    elif abs_y >= abs_x and abs_y >= abs_z:
        def proj(v): return (v[0], v[2])
    else:
        def proj(v): return (v[0], v[1])

    p0, p1, p2 = proj(t1_v0), proj(t1_v1), proj(t1_v2)
    q0, q1, q2 = proj(t2_v0), proj(t2_v1), proj(t2_v2)

    # 1. 2D edge-edge intersection testing (9 pairs)
    p_edges = ((p0, p1), (p1, p2), (p2, p0))
    q_edges = ((q0, q1), (q1, q2), (q2, q0))

    for ea in p_edges:
        for eb in q_edges:
            if _segments_intersect_2d(ea[0], ea[1], eb[0], eb[1]):
                return True

    # 2. Point-in-triangle containment testing
    for pt in (p0, p1, p2):
        if _point_in_triangle_2d(pt, q0, q1, q2):
            return True
    for pt in (q0, q1, q2):
        if _point_in_triangle_2d(pt, p0, p1, p2):
            return True

    return False
```

#### 2.2 In `triangle_triangle_intersection_moller` (Lines 272–277):
**Target Content**:
```python
    d_dir = _cross_product(n1, n2)
    max_d = max(abs(d_dir[0]), abs(d_dir[1]), abs(d_dir[2]))
    if max_d < 1e-8:
        # Triangles are coplanar or nearly parallel
        return False
```
**Replacement Content**:
```python
    d_dir = _cross_product(n1, n2)
    max_d = max(abs(d_dir[0]), abs(d_dir[1]), abs(d_dir[2]))
    if max_d < 1e-8:
        # Triangles are coplanar or nearly parallel
        return _coplanar_triangle_triangle_intersection_2d(
            t1_v0, t1_v1, t1_v2, t2_v0, t2_v1, t2_v2, n1
        )
```

#### 2.3 Update Adversarial Test in `tests/test_adversarial_bvh_penetration.py` (Line 272):
**Target Content**:
```python
        # Möller returns False for coplanar triangles because cross product of identical normals is 0
        res = triangle_triangle_intersection_moller(t1_v0, t1_v1, t1_v2, t2_v0, t2_v1, t2_v2)
        assert res is False
```
**Replacement Content**:
```python
        # Authentic Möller returns True for overlapping coplanar triangles via 2D dominant plane projection
        res = triangle_triangle_intersection_moller(t1_v0, t1_v1, t1_v2, t2_v0, t2_v1, t2_v2)
        assert res is True

        # Disjoint coplanar triangles return False
        t_dis_v0, t_dis_v1, t_dis_v2 = (5.0, 5.0, 0.0), (7.0, 5.0, 0.0), (5.0, 7.0, 0.0)
        res_dis = triangle_triangle_intersection_moller(t1_v0, t1_v1, t1_v2, t_dis_v0, t_dis_v1, t_dis_v2)
        assert res_dis is False
```

---

### Blueprint 3: Quad Mesh Support in `compute_mesh_signed_volume`

#### 3.1 In `src/morphomesh/visual_critic.py` (Lines 1262–1277):
**Target Content**:
```python
def compute_mesh_signed_volume(
    vertices: List[Tuple[float, float, float]],
    faces: List[Tuple[int, ...]],
) -> float:
    """Computes exact volume of watertight triangle mesh via divergence theorem."""
    vol = 0.0
    for f in faces:
        v1 = vertices[f[0]]
        v2 = vertices[f[1]]
        v3 = vertices[f[2]]
        cx = v2[1] * v3[2] - v2[2] * v3[1]
        cy = v2[2] * v3[0] - v2[0] * v3[2]
        cz = v2[0] * v3[1] - v2[1] * v3[0]
        vol += v1[0] * cx + v1[1] * cy + v1[2] * cz
    return abs(vol) / 6.0
```
**Replacement Content**:
```python
def compute_mesh_signed_volume(
    vertices: List[Tuple[float, float, float]],
    faces: List[Tuple[int, ...]],
) -> float:
    """
    Computes exact volume of watertight polygonal/triangle mesh via divergence theorem.
    Automatically decomposes quads (len(f) == 4) and planar n-gons into triangles via fan triangulation.
    """
    vol = 0.0
    for f in faces:
        n = len(f)
        if n < 3:
            continue
        # Fan triangulation: decomposes quads into (f[0], f[1], f[2]) and (f[0], f[2], f[3])
        for i in range(1, n - 1):
            v1 = vertices[f[0]]
            v2 = vertices[f[i]]
            v3 = vertices[f[i + 1]]
            cx = v2[1] * v3[2] - v2[2] * v3[1]
            cy = v2[2] * v3[0] - v2[0] * v3[2]
            cz = v2[0] * v3[1] - v2[1] * v3[0]
            vol += v1[0] * cx + v1[1] * cy + v1[2] * cz
    return abs(vol) / 6.0
```

---

## 5. Verification Method

The implementer (Worker M3) and reviewers can verify this implementation using the following commands:

### 5.1 Verify Actionable Recommendations Formula & Comb Brush
Run:
```powershell
.venv\Scripts\python.exe -c "
from morphomesh.visual_critic import evaluate_mesh_penetration, evaluate_hair_grooming_intersections, create_penetration_fixture, create_grooming_fixture
b_def, g_def = create_penetration_fixture(defective=True)
defs_pen = evaluate_mesh_penetration('Body', ['Skirt'], body_geo=b_def, garment_geos={'Skirt': g_def})
pen = defs_pen[0]
assert pen.recommendation is not None
print('Shrinkwrap parameters:', pen.recommendation.parameters)
print('Shrinkwrap guidance:', pen.recommendation.guidance)
# Verify exact formula: d_rec = 1.25 * d_pen + 1mm (in meters: 1.25 * d_pen_m + 0.001)
expected_offset = round(1.25 * (pen.penetration_depth_mm / 1000.0) + 0.001, 4)
assert pen.recommendation.parameters['offset'] == expected_offset
assert 'Laplacian smoothing' in pen.recommendation.guidance or 'smoothing' in pen.recommendation.guidance

# Verify hair grooming comb brush
b_g_def, h_g_def = create_grooming_fixture(defective=True)
defs_groom = evaluate_hair_grooming_intersections(['Hair'], 'Scalp', hair_splines=h_g_def, body_geo=b_g_def)
assert any('Comb Brush' in (d.recommendation.guidance if d.recommendation else '') for d in defs_groom)
print('Actionable recommendations successfully verified!')
"
```

### 5.2 Verify Authentic 2D Coplanar Triangle Intersection
Run:
```powershell
.venv\Scripts\python.exe -c "
from morphomesh.visual_critic import triangle_triangle_intersection_moller
# Overlapping coplanar triangles in Z=0
t1 = ((0, 0, 0), (2, 0, 0), (0, 2, 0))
t2 = ((0.5, 0.5, 0), (2.5, 0.5, 0), (0.5, 2.5, 0))
assert triangle_triangle_intersection_moller(*t1, *t2) is True, 'Overlap must return True'

# Contained coplanar triangle
t_in = ((0.2, 0.2, 0), (0.6, 0.2, 0), (0.2, 0.6, 0))
assert triangle_triangle_intersection_moller(*t1, *t_in) is True, 'Containment must return True'

# Disjoint coplanar triangles
t_dis = ((5.0, 5.0, 0), (7.0, 5.0, 0), (5.0, 7.0, 0))
assert triangle_triangle_intersection_moller(*t1, *t_dis) is False, 'Disjoint must return False'

# Parallel separated triangles (Z=0 vs Z=1)
t_sep = ((0, 0, 1.0), (2, 0, 1.0), (0, 2, 1.0))
assert triangle_triangle_intersection_moller(*t1, *t_sep) is False, 'Separated planes must return False'

print('Coplanar triangle intersection successfully verified!')
"
```

### 5.3 Verify Quad Mesh Signed Volume Calculation
Run:
```powershell
.venv\Scripts\python.exe -c "
from morphomesh.visual_critic import compute_mesh_signed_volume
import math

# Analytical Unit Cube [-1, 1]^3 with 6 quad faces
cube_verts = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
cube_faces_quad = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (0, 4, 7, 3), (1, 2, 6, 5)]

vol = compute_mesh_signed_volume(cube_verts, cube_faces_quad)
print(f'Quad cube volume: {vol:.6f} (Analytical: 8.000000)')
assert math.isclose(vol, 8.0, abs_tol=1e-6), 'Quad cube volume must equal 8.0 exactly'

print('Quad mesh signed volume calculation successfully verified!')
"
```

### 5.4 Full Milestone 3 Regression Suite Run
Run:
```powershell
.venv\Scripts\pytest.exe -v tests/test_visual_critic.py tests/test_adversarial_bvh_penetration.py tests/test_adversarial_critic_benchmark.py
```
*Expected output: All 92 tests pass with 0 failures.*
