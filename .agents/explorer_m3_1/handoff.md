# Handoff Report: Penetration & Collision Geometry Subsystem (Milestone 3)
**Agent**: Explorer M3_1 (Penetration & Collision Geometry Explorer)
**Target Milestone**: Milestone 3 — Closed-Loop Visual Quality Critique Engine
**Target Module**: `src/morphomesh/visual_critic.py` (with schema support in `src/morphomesh/models.py`)
**Timestamp**: 2026-09-07T05:42:00Z

---

## 1. Observation

Direct observations from the MorphoMesh repository:

1. **Missing Module & Existing RPC Wire Hooks**:
   - `src/morphomesh/visual_critic.py` does not yet exist on disk (`list_dir` on `src/morphomesh` shows 17 files, with `camera_rig.py` and `wardrobe.py` present, but no `visual_critic.py`).
   - However, wire hooks already exist in both `blender_addon/morphomesh/listener.py` (lines 1317–1321) and `src/morphomesh/blender_bridge.py` (lines 2241–2244), attempting:
     ```python
     from morphomesh.visual_critic import run_visual_critique
     from morphomesh.models import VisualCritiqueInput
     inp = VisualCritiqueInput(**params)
     out = run_visual_critique(inp)
     ```
   - In `listener.py` (lines 1351–1377), an initial in-addon fallback was drafted for mesh penetration using `mathutils.bvhtree.BVHTree.FromPolygons` and `find_nearest`, but lacks reverse penetration (skin burst), face-face overlap detection, grooming curve intersection audits, and offline execution capability.

2. **Existing Historical Penetration Scripts**:
   - In `tests/inspect_penetration.py` (lines 15–24):
     ```python
     bodice_verts = [bodice_obj.matrix_world @ v.co for v in bodice_obj.data.vertices]
     for idx, v in enumerate(bodice_verts):
         loc, normal, f_idx, dist = bvh.find_nearest(v)
         if loc is not None:
             offset = v - loc
             dot = offset.dot(normal)
             if dot < 0:
                 penetrations.append((idx, v, loc, normal, dist, dot))
     ```
   - In `tests/inspect_eval_bodice.py` (lines 10–22), evaluated meshes are retrieved using Blender's dependency graph:
     ```python
     depsgraph = bpy.context.evaluated_depsgraph_get()
     eval_bodice = bodice_obj.evaluated_get(depsgraph)
     eval_body = body_obj.evaluated_get(depsgraph)
     bm_body = bmesh.new()
     bm_body.from_mesh(eval_body.to_mesh())
     bm_body.transform(eval_body.matrix_world)
     bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)
     m = eval_bodice.to_mesh()
     eval_bodice_verts = [eval_bodice.matrix_world @ v.co for v in m.vertices]
     eval_bodice.to_mesh_clear()
     eval_body.to_mesh_clear()
     ```
     This confirms that when modifiers (Subdivision, Solidify, Armature) are active, `evaluated_get(depsgraph).to_mesh()` is mandatory for accurate visual critique, followed by `to_mesh_clear()` to avoid GPU memory leaks.

3. **Hair Grooming Representation**:
   - In `src/morphomesh/human_grooming.py` (lines 172–180), hair splines are structured as:
     ```python
     @dataclass
     class HairCurveSpline:
         points: List[Tuple[float, float, float]]
         radii: List[float]
         layer_name: str
         length: float
     ```
   - In Blender (lines 848–862), hair is instantiated as `CURVES` with `POLY` splines or ribbon quad meshes (`convert_curves_to_ribbon_mesh`).
   - Hair roots sit at index 0 (`points[0]`) and tips sit at index -1 (`points[-1]`).

4. **Pure-Python Offline Math Architecture**:
   - In `src/morphomesh/camera_rig.py` (lines 58–140), headless/offline execution without Blender is enabled via custom fallback classes (`Vector`, `Matrix`, `Quaternion`, `Euler`).
   - For `visual_critic.py`, no spatial tree fallback currently exists, which would cause offline unit tests in `pytest tests/` to fail when importing or running collision tests outside Blender unless a pure-Python spatial index is provided.

---

## 2. Logic Chain

From the observations and project requirements, we deduce the following structural blueprint:

### 2.1 Pillar 1: BVH Signed Distance Penetration Detection

#### Mathematical Foundation
Let $\mathcal{M}_{\text{body}}$ be the body mesh and $\mathcal{M}_{\text{garm}}$ be a garment or armor mesh.
All computations must occur in unified world space:
$$w_i = M_{\text{world, garm}} \cdot \begin{pmatrix} v_i \\ 1 \end{pmatrix}$$

For each garment vertex $w_i \in \mathbb{R}^3$, query the body BVH tree for its nearest surface projection:
$$(p_i, \hat{n}_i, f_i, d_i) = \text{BVH}_{\text{body}}.\text{find\_nearest}(w_i)$$
where $p_i$ is the closest point on $\mathcal{M}_{\text{body}}$, $\hat{n}_i$ is the outward unit surface normal at $p_i$, $f_i$ is the face index, and $d_i = \|w_i - p_i\|$.

The signed distance $s_i$ is defined as:
$$s_i = (w_i - p_i) \cdot \hat{n}_i$$

- **Clearance Condition**: $s_i \ge 0$.
- **Penetration Condition**: Given tolerance threshold $\epsilon_{\text{tol}} = 0.0005\,\text{m}$ ($0.5\,\text{mm}$):
  $$s_i < -\epsilon_{\text{tol}}$$
  The penetration depth is:
  $$\delta_i = -s_i = -(w_i - p_i) \cdot \hat{n}_i > \epsilon_{\text{tol}}$$

#### Proximity Search Radius & Normal Alignment Filter
To prevent false-positive intersections in concave regions (such as axilla/armpits, groin, or between adjacent fingers):
1. **Search Radius Filter**: If $d_i > R_{\text{max}}$ (where $R_{\text{max}} = 0.05\,\text{m}$ default), the garment vertex is outside the local fit zone and is discarded from body penetration checks.
2. **Normal Alignment Filter**: For clothing shells conforming to the body, outward normals should be generally co-directional:
   $$\hat{n}_{\text{garm}, i} \cdot \hat{n}_i > -0.2$$
   If $\hat{n}_{\text{garm}, i} \cdot \hat{n}_i \le -0.2$, the vertex is facing an opposite anatomical surface (e.g. inner arm vertex near chest) rather than penetrating its underlying skin.

#### Reverse Penetration ("Skin Burst")
When garment topology is coarse or body muscles flex, body vertices may protrude outward through the garment without garment vertices being submerged.
To catch skin bursts:
1. Build $\text{BVH}_{\text{garm}}$.
2. For each body vertex $b_j$ within the AABB of the garment:
   $$(p_{g, j}, \hat{n}_{g, j}, f_j, d_j) = \text{BVH}_{\text{garm}}.\text{find\_nearest}(b_j)$$
   If $d_j \le R_{\text{max}}$:
   $$s_j^{\text{burst}} = (b_j - p_{g, j}) \cdot \hat{n}_{g, j}$$
   If $s_j^{\text{burst}} > \epsilon_{\text{tol}}$, vertex $b_j$ is poking out through the exterior surface of the garment (skin burst defect).

#### Triangle-Triangle Face Overlap
Vertex-only testing can miss thin edge-edge or triangle-triangle intersections where no vertices cross the opposing boundary.
Blender's `BVHTree.overlap(other_bvh)` returns pairs of overlapping triangle indices:
$$[(f_{\text{body}, k}, f_{\text{garm}, k}), \dots]$$
For each pair, Tomas Möller's 3D triangle-triangle intersection algorithm is used to confirm true surface piercing and extract the 3D line segment of intersection.

---

### 2.2 Pillar 2: Hair Grooming Curve Intersection Audit

A character's hair system comprises multiple layers (e.g. Bangs, Sidelocks, Scalp Crown, Back Cascade, Eyebrows, Eyelashes). Each strand is represented as a sequence of control points $S = [p_0, p_1, \dots, p_{K-1}]$ with associated radii $r_k$.

#### 1. Submerged Root Audit ($p_0$)
- Query root $p_0$ against $\text{BVH}_{\text{body}}$:
  $$(p_{\text{scalp}}, \hat{n}_{\text{scalp}}, f, d) = \text{BVH}_{\text{body}}.\text{find\_nearest}(p_0)$$
- Root signed distance:
  $$s_{\text{root}} = (p_0 - p_{\text{scalp}}) \cdot \hat{n}_{\text{scalp}}$$
- Submerged Root Criterion:
  $$s_{\text{root}} < -\epsilon_{\text{root\_submerged}} \quad (\text{where } \epsilon_{\text{root\_submerged}} = 0.001\,\text{m} = 1.0\,\text{mm})$$
  Roots submerged deeper than $1\,\text{mm}$ are flagged as `GROOMING_ROOT_SUBMERGED`.
- Floating Root Criterion:
  $$s_{\text{root}} > +0.004\,\text{m} \quad (4\,\text{mm})$$
  Roots detached from the cranium are flagged as `GROOMING_ROOT_DETACHED`.

#### 2. Hair Shaft Body Collision Audit ($p_k, k \ge 1$)
- Sample the spline along its arc length. For control point pairs $(p_k, p_{k+1})$, sample $M$ equidistant points:
  $$q(u) = (1 - u) p_k + u p_{k+1}, \quad u \in [0, 1]$$
- Query against $\text{BVH}_{\text{body}}$:
  $$(p_{\text{body}}, \hat{n}_{\text{body}}, f, d) = \text{BVH}_{\text{body}}.\text{find\_nearest}(q(u))$$
- Incorporate physical strand radius $r(u)$ (tapered from root to tip):
  $$s_{\text{eff}} = (q(u) - p_{\text{body}}) \cdot \hat{n}_{\text{body}} - r(u)$$
- If $s_{\text{eff}} < -\epsilon_{\text{hair\_body}}$ ($0.5\,\text{mm}$):
  Flag `GROOMING_BODY_COLLISION` with exact penetration depth $\delta = -s_{\text{eff}}$ and 3D location $q(u)$.
- **Segment Raycast Validation**:
  To confirm surface piercing, shoot a ray from $p_k$ to $p_{k+1}$ using `BVH.ray_cast(p_k, (p_{k+1} - p_k).normalized(), \|p_{k+1} - p_k\|)`. If hit normal points opposite to ray direction ($\vec{d} \cdot \hat{n}_{\text{hit}} < 0$), the hair strand physically pierces through the cranium or neck.

#### 3. Hair Garment Collision Audit
- Hair strands draping over clothing (e.g. Back Cascade over Bodice/Sash, Sidelocks over shoulder straps) must not clip inside garments.
- Query sampled points $q(u)$ against garment BVH trees:
  $$(p_{\text{garm}}, \hat{n}_{\text{garm}}, f, d) = \text{BVH}_{\text{garm}}.\text{find\_nearest}(q(u))$$
- If $d \le 0.03\,\text{m}$ and $(q(u) - p_{\text{garm}}) \cdot \hat{n}_{\text{garm}} - r(u) < -\epsilon_{\text{hair\_garm}}$:
  Flag `GROOMING_GARMENT_COLLISION`.

---

### 2.3 Pillar 3: Pure-Python Spatial Index Fallback (`PurePythonBVHTree`)

To ensure MorphoMesh unit tests, CI test harnesses, and client inspection can run without a live Blender installation, a pure-Python spatial hierarchy is designed.

#### Core Geometric Engines
1. **David Eberly's Point-to-Triangle 3D Distance Algorithm**:
   - Computes the exact Euclidean projection $Q$ of point $P$ onto triangle $T = (V_0, V_1, V_2)$.
   - Parametric triangle: $T(s, t) = V_0 + s E_0 + t E_1$ with $E_0 = V_1 - V_0, E_1 = V_2 - V_0$.
   - Objective: minimize $F(s, t) = \|T(s, t) - P\|^2$ subject to $s \ge 0, t \ge 0, s + t \le 1$.
   - Evaluates the 7 Voronoi regions (interior, 3 edge segments, 3 vertices) via quadratic equation root bounding.
   - Returns $(Q, \hat{n}, d)$ where $\hat{n} = \frac{E_0 \times E_1}{\|E_0 \times E_1\|}$ and $d = \|P - Q\|$.
2. **Möller–Trumbore Ray-Triangle Intersection**:
   - Evaluates ray $R(t) = O + t \vec{D}$ against triangle $(V_0, V_1, V_2)$ using Cramer's rule.
   - Returns $(hit, t, Q, \hat{n})$.
3. **Tomas Möller Triangle-Triangle Intersection**:
   - Evaluates signed distances of vertices to opposing triangle planes.
   - Calculates 1D overlap intervals along the line of plane-plane intersection.
   - Returns `True` if triangles intersect, `False` otherwise.

#### Spatial Index Data Structure: `PurePythonBVHTree`
- **Node Structure**:
  ```python
  class PurePythonBVHNode:
      bbox: AABB  # min_pt, max_pt
      triangle_indices: List[int]  # Non-empty only for leaf nodes (size <= 4)
      left: Optional[PurePythonBVHNode]
      right: Optional[PurePythonBVHNode]
      is_leaf: bool
  ```
- **Construction**:
  - Top-down recursive construction with Median Centroid Partitioning along the axis of maximum bounding box extent ($X, Y, \text{ or } Z$).
  - Max leaf size: 4 triangles; max recursion depth: 22.
- **Priority-Queue Branch-and-Bound `find_nearest`**:
  - Maintains `best_dist = max_dist` and a min-heap ordered by lower-bound distance from query point $P$ to node bounding box.
  - If a node's AABB distance $\ge best_dist$, the entire subtree is pruned.
  - Leaves evaluate Eberly's algorithm for their triangles, updating `best_dist`.
  - Average complexity: $O(\log N)$ instead of $O(N)$.
- **Dual-Tree Simultaneous Descent `overlap`**:
  - Prunes subtree pairs if their AABBs do not intersect.
  - At leaf-leaf pairs, runs Möller triangle-triangle intersection.
- **API Parity**:
  Exposes the exact method signatures of Blender's `mathutils.bvhtree.BVHTree`:
  - `FromPolygons(vertices, polygons, all_triangles=True, epsilon=0.0)`
  - `find_nearest(co, max_dist=1e9) -> (location, normal, index, distance)`
  - `ray_cast(origin, direction, distance=1e9) -> (location, normal, index, distance)`
  - `overlap(other_tree) -> List[Tuple[int, int]]`

---

### 2.4 Pillar 4: Defect Structuring & Pydantic Feedback Schemas

The output must conform to Pydantic v2 schemas in `src/morphomesh/models.py`.

#### Schema Definitions
1. `DefectSeverity` Enum:
   - `CRITICAL`: Severe structural clipping ($> 5\,\text{mm}$ or $> 50$ vertices), submerged roots ($> 2\,\text{mm}$).
   - `MAJOR`: Visible clipping ($1\,\text{mm} - 5\,\text{mm}$ or $10 - 50$ vertices), hair strand penetrating skin.
   - `MINOR`: Micro-penetration ($0.5\,\text{mm} - 1\,\text{mm}$, $< 10$ vertices).
   - `INFO`: Clean clearance metrics and verified spacing ($> 0.5\,\text{mm}$).

2. `DefectCategory` Enum:
   - `PENETRATION`: Garment or armor vertex penetrating body mesh.
   - `SKIN_BURST`: Body vertex bursting outward through clothing.
   - `FACE_OVERLAP`: Triangle-triangle intersection between two meshes.
   - `GROOMING_ROOT_SUBMERGED`: Hair strand root submerged beneath scalp.
   - `GROOMING_BODY_COLLISION`: Hair strand intersecting cranium, neck, or torso.
   - `GROOMING_GARMENT_COLLISION`: Hair strand clipping through garments.

3. `DefectItem` Model:
   ```python
   class DefectItem(BaseModel):
       id: str
       category: Union[DefectCategory, str]
       severity: Union[DefectSeverity, str]
       affected_objects: List[str]
       source_object: Optional[str] = None
       target_object: Optional[str] = None
       description: str
       location: List[float]  # [x, y, z] in world space
       sample_locations: List[List[float]] = Field(default_factory=list)
       penetration_depth_mm: float = 0.0
       penetration_count: int = 0
       penetrated_triangles: List[int] = Field(default_factory=list)
       confidence: float = 0.95
       actionable_recommendation: str = ""
   ```

4. `VisualCritiqueOutput` Model:
   ```python
   class VisualCritiqueOutput(BaseModel):
       status: str = "success"
       passed: bool
       quality_score: float  # 0.0 to 100.0
       defect_count: int
       defects: List[DefectItem]
       recommendations: List[str]
       inspected_objects: List[str]
       scene_stats: Dict[str, Any]
   ```

---

## 3. Caveats

1. **Self-Collision within a Single Mesh**:
   - The primary scope is inter-object penetration (garment vs body, hair vs body, hair vs garment). Intra-mesh self-intersection (e.g. self-intersecting skirt pleats) is partially covered by `BVHTree.overlap()` if enabled, but requires adjacent face filtering to avoid flagging shared edges.
2. **Coarse Topology Discretization**:
   - If garment meshes are extremely low poly (e.g. < 50 vertices), vertex signed distance tests may underestimate peak penetration between vertices. In such cases, triangle-triangle overlap provides essential secondary detection.
3. **Hair Splines vs Rendered Hair Thickness**:
   - Geometry Nodes generates interpolated render strands around guide splines. The collision audit evaluates guide splines augmented with their configured clump radius and strand thickness. Micro-frizz noise is checked at its bounding envelope.
4. **Armature Deformed State**:
   - When inspecting posed characters, `evaluated_get(depsgraph)` must be used inside Blender so that bone deformations are taken into account. In offline pure-Python mode without a posing engine, the evaluation defaults to the rest pose / current coordinates of the provided mesh geometry.

---

## 4. Conclusion

The architecture for penetration and collision geometry in `src/morphomesh/visual_critic.py` is fully specified with:
1. **Mathematical Rigor**: Outward normal signed distance $s_i = (w_i - p_i) \cdot \hat{n}_i$, search radius gating, reverse penetration skin burst checks, and `BVHTree.overlap()`.
2. **Hair Grooming Intersections**: Root submergence testing, shaft body collisions with strand radius offsetting, and garment clipping detection.
3. **Full Pure-Python Parity**: `PurePythonBVHTree` with David Eberly's point-triangle distance, Möller–Trumbore ray-triangle, and Tomas Möller triangle-triangle intersection, operating identically whether inside Blender or in offline pytest environments.
4. **Structured Actionable Defect Output**: Typed Pydantic v2 feedback schemas providing world 3D coordinates, affected objects, penetrated triangle indices, penetration depth metrics, and concrete remedy advice.

---

## 5. Verification Method

To independently verify the implementation once coded:

1. **Offline Pure-Python Pytest Suite**:
   Execute standard pytest command in terminal:
   ```powershell
   pytest tests/test_visual_critic.py -v
   ```
   **Assertions to test**:
   - `test_pure_python_bvh_accuracy`: Point-to-triangle distance matches analytical ground truth to within $10^{-6}\,\text{m}$.
   - `test_garment_penetration_detected`: Procedural cube/sphere with intentionally submerged vertices ($z < 0$) flags `DefectCategory.PENETRATION` with depth matching injection offset $\pm 0.01\,\text{mm}$.
   - `test_clean_mesh_zero_false_positives`: Baseline Yu Nian An body + dress with $15\,\text{mm}$ clearance yields 0 penetration defects and `passed=True`.
   - `test_submerged_hair_root_detected`: Hair spline with root placed at $z = 1.63\,\text{m}$ (inside cranium $z_{\text{scalp}} = 1.645\,\text{m}$) flags `GROOMING_ROOT_SUBMERGED` with depth $\approx 15\,\text{mm}$.
   - `test_hair_garment_clipping_detected`: Hair spline cutting through dress bodice flags `GROOMING_GARMENT_COLLISION`.

2. **In-Blender Headless Verification**:
   Run Blender headless script testing `run_visual_critique`:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python-expr "from morphomesh.visual_critic import run_visual_critique; from morphomesh.models import VisualCritiqueInput; res = run_visual_critique(VisualCritiqueInput()); print('CRITIQUE_RESULT:', res.passed, res.defect_count)"
   ```
   Must exit with code 0 and output valid JSON report.
