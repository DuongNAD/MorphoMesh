# MORPHOMESH SURVEY REPORT: R2 (CLOSED-LOOP VISUAL CRITIC) & R3 (INSPECTOR CAMERA & VIEWPORT CAPTURE)

- **Date**: 2026-09-08
- **Explorer**: explorer_survey_2
- **Milestone Scope**: R2 (Closed-Loop Visual Critic & Automated QA) and R3 (Multi-Angle Inspector Camera & Fast Viewport Capture)
- **Status**: Comprehensive Analysis & Architectural Specification Complete

---

## 1. Executive Summary

MorphoMesh's closed-loop quality assurance and multi-angle inspection subsystem provides autonomous structural defect detection, standardized camera framing, and sub-second viewport capture for 3D character and creature assets.

This investigation audits the mathematical foundations, software architecture, Pydantic v2 schemas, Blender IPC bridge, and FastMCP tooling across R2 and R3:

1. **R2 (Closed-Loop Visual Critic & Automated QA)**:
   - **Implemented Modules**: `src/morphomesh/visual_critic.py`, `src/morphomesh/models.py`, `src/morphomesh/blender_bridge.py`, `blender_addon/morphomesh/listener.py`, and `src/morphomesh/server.py`.
   - **Pure-Python Spatial Acceleration**: Includes `PurePythonBVHTree` with David Eberly's point-to-triangle distance, Möller-Trumbore raycasting, and Möller triangle-triangle intersection, ensuring 100% offline testability without Blender or external C-extensions.
   - **4 Core Defect Categories**:
     * Garment/mesh penetration and skin burst via signed distance $s_i = (\vec{w}_i - \vec{p}_i) \cdot \hat{n}_i$ with 3-tier false positive elimination (height clamping, dual-sided normal alignment, and open boundary edge filtering).
     * Anthropometric proportion deviation ($H_{\text{total}} / H_{\text{head}}$, arm span ratio, shoulder/hip ratio) across 6 target presets.
     * Rigging/skinning deformation pinching ($\cos\theta < -0.85$, fold angle $< 30^\circ$) and joint volume collapse/bulge ($\rho_V = V_{\text{posed}} / V_{\text{rest}} \notin [0.80, 1.25]$) via divergence theorem and bounding slice volume.
     * Hair grooming curve collisions (submerged roots $s < -1\text{mm}$, detached roots $s > +4\text{mm}$, shaft collision $s < -0.5\text{mm}$).
   - **Quality Score & Recommendations**: Deductions (-25 CRITICAL, -10 MAJOR, -3 MINOR) from 100.0; automated synthesis of parameterized remediation actions (`APPLY_SHRINKWRAP_CLEARANCE`, `RESCALE_HEAD`, `SMOOTH_SKINNING_WEIGHTS`, `ACTIVATE_DUAL_BONE_TWIST_SKINNING`, `RELAX_HAIR_COLLISION`).
   - **Diagnostic Accuracy**: Benchmarked across 4 procedural defect fixtures (9 states), achieving **100.0% accuracy** (surpassing the $>95\%$ requirement) with **0.0% false positive rate**.

2. **R3 (Inspector Camera & Fast Viewport Capture)**:
   - **Hierarchical World Bounding Box**: Solves multi-mesh hierarchies traversing parent Empties, Armatures, and child meshes using evaluated depsgraph ($M_{\text{world}} \cdot v_{\text{local}}$), computing exact AABB and circumscribing sphere $(\vec{C}, R)$.
   - **5 Anatomical Focus Centers**: Prioritizes Armature DEF bones (`DEF-head`, `DEF-spine.002`, `DEF-hand.R`, `DEF-foot.R`) with deterministic anthropometric height fraction fallbacks (Full Body, Head: 88%, Torso: 60%, Hands: 50% with $+0.35\text{m}$ lateral offset, Feet: 8%).
   - **Optical Framing Trigonometry**: Exact closed-form derivation $d = \frac{R}{\sin(\alpha_{\min})} \cdot (1 + \mu)$, where $\alpha_{\min} = \min(\alpha_h, \alpha_v)$ dynamically adapts to focal length (24mm–135mm), aspect ratio (1:1, 16:9, 9:16), and Blender sensor fit (`AUTO`, `HORIZONTAL`, `VERTICAL`).
   - **6 Canonical Viewpoints & 360 Turntable**: Spherical orbit coordinates $(\theta, \phi, d)$ with `to_track_quat('-Z', 'Y')` tracking for Front, Side, Back, 3/4, Head closeup (85mm), and Hands closeup (85mm), plus 4-view turnaround and continuous $N$-frame orbital sweeps.
   - **Dual-Mode Capture**: Interactive OpenGL frame grab (`bpy.ops.render.opengl`) via `temp_override` on `VIEW_3D` executing in $<200\text{ms}$ with diagnostic shading (SOLID, RANDOM, WIREFRAME) and headless Workbench render fallback (`bpy.ops.render.render`) in $<700\text{ms}$.
   - **Artifact Delivery**: Standardized PNG generation with embedded Base64 strings for instant client rendering.

3. **FastMCP Integration & Compatibility (R1 Connection)**:
   - FastMCP server exposes 3 inspection tools (`morphomesh_setup_inspector_camera_rig`, `morphomesh_capture_viewport`, `morphomesh_critique_visual_quality`).
   - Gating environment flags (`MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1`, `MORPHOMESH_INCLUDE_ALL_TOOLS=1`) preserve 7-tool legacy backward compatibility while supporting full 17-tool production mode.

---

## 2. Deep Dive: R2 (Closed-Loop Visual Critic & Automated QA)

### 2.1 Module Architecture & Data Flow

The Visual Critic subsystem executes closed-loop structural evaluation of 3D meshes either within a live Blender session or in pure-Python headless environments:

```
+-----------------------------------------------------------------------------------+
|                            FastMCP Tooling Layer                                  |
|                 (morphomesh_critique_visual_quality in server.py)                 |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                        Client-Side Bridge (blender_bridge.py)                     |
|           - RPC method: critique_visual_quality(character_name, preset, ...)     |
|           - Socket IPC to Blender listener.py (timeout=120s)                      |
|           - Offline fallback to local visual_critic.run_visual_critique           |
+------------------------------------------+----------------------------------------+
                                           |
                    +----------------------+----------------------+
                    | (Blender Socket IPC)                        | (Offline Fallback)
                    v                                             v
+--------------------------------------+      +-------------------------------------+
|   In-Blender Listener (listener.py)  |      |   Pure-Python Engine                |
| - Resolves scene objects via depsgraph|      |   (visual_critic.py)                |
| - Dispatches to run_visual_critique   |      | - Evaluates pure geometric tuples   |
+-------------------+------------------+      +-------------------+-----------------+
                    |                                             |
                    +----------------------+----------------------+
                                           v
+-----------------------------------------------------------------------------------+
|                          Core Evaluation Engines                                  |
|  1. evaluate_mesh_penetration(body, garments, tolerance=0.5mm)                   |
|  2. evaluate_hair_grooming_intersections(hair_curves, body, garments)             |
|  3. evaluate_body_proportions(body, target_preset, landmarks)                     |
|  4. evaluate_rig_skinning_deformation(rest_v, posed_v, faces, joint_specs)        |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                       Synthesis & Diagnostic Reporting                            |
|  - Computes Quality Score: 100.0 - (25*Crit + 10*Maj + 3*Min)                     |
|  - Generates Actionable Recommendations with concrete parameter dicts             |
|  - Returns Pydantic v2 `VisualCritiqueOutput`                                      |
+-----------------------------------------------------------------------------------+
```

### 2.2 Pydantic v2 Schema Architecture

All critique models are declared in `src/morphomesh/models.py` using Pydantic v2 with `model_config = ConfigDict(extra="ignore")`, custom field validators, and cross-field normalization:

#### 1. `DefectSeverity` Enum
```python
class DefectSeverity(str, Enum):
    CRITICAL = "CRITICAL"  # Severe penetration (>5mm), volume collapse (>50%), broken anatomy
    MAJOR = "MAJOR"        # Significant penetration (1-5mm), proportion deviation (>15%), pinching
    MINOR = "MINOR"        # Slight clearance breach (<1mm), minor proportion deviation, stray curves
    INFO = "INFO"          # Informational diagnostic observation
```
*Normalization*: Case-insensitive parsing with legacy token mapping (`"HIGH"` $\to$ `CRITICAL`, `"WARNING"` $\to$ `MAJOR`, `"LOW"` $\to$ `MINOR`, `"NOTICE"` $\to$ `INFO`).

#### 2. `DefectCategory` Enum
```python
class DefectCategory(str, Enum):
    PENETRATION = "PENETRATION"              # Garment clipping, skin burst, face overlap
    PROPORTION = "PROPORTION"                # Anthropometric proportion deviation
    SKINNING_PINCH = "SKINNING_PINCH"        # Joint collapse, candy-wrapper, acute crease
    GROOMING_COLLISION = "GROOMING_COLLISION" # Submerged roots, detached roots, shaft clipping
```
*Normalization*: Maps legacy string types (`"CLIPPING"`, `"FACE_OVERLAP"`, `"SKIN_BURST"` $\to$ `PENETRATION`; `"RIG_PINCH"`, `"PINCHING"` $\to$ `SKINNING_PINCH`; `"HAIR_CLIPPING"` $\to$ `GROOMING_COLLISION`).

#### 3. `ActionableRecommendation` Model
```python
class ActionableRecommendation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action_id: str = Field(default_factory=lambda: f"REC-{uuid.uuid4().hex[:6]}")
    action: Optional[str] = Field(default=None, description="Action verb (e.g. APPLY_SHRINKWRAP_CLEARANCE)")
    category: Optional[Union[DefectCategory, str]] = None
    target_objects: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    guidance: Optional[str] = None
    suggested_modifier: Optional[str] = None  # e.g. "Shrinkwrap", "LaplacianSmooth"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: Union[DefectSeverity, str] = DefectSeverity.MAJOR
```

#### 4. `DefectItem` Model
```python
class DefectItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    defect_id: str = Field(default_factory=lambda: f"DEF-{uuid.uuid4().hex[:6]}")
    id: Optional[str] = None  # Alias for defect_id
    category: Union[DefectCategory, str]
    defect_type: Optional[str] = None
    severity: Union[DefectSeverity, str] = DefectSeverity.MAJOR
    affected_objects: List[str] = Field(default_factory=list)
    object_name: Optional[str] = None
    source_object: Optional[str] = None
    target_object: Optional[str] = None
    description: str
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    location: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    sample_locations: List[List[float]] = Field(default_factory=list)
    bounding_box: Optional[BoundingBox3D] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    penetration_depth_mm: Optional[float] = None
    penetration_count: int = 0
    affected_vertices: List[int] = Field(default_factory=list)
    affected_faces: List[int] = Field(default_factory=list)
    recommendation: Optional[Union[ActionableRecommendation, str]] = None
    actionable_recommendation: Optional[str] = None
```

#### 5. `VisualCritiqueOutput` Model
```python
class VisualCritiqueOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: str = "success"
    passed: bool = True
    quality_score: float = Field(default=100.0, ge=0.0, le=100.0)
    defect_count: int = 0
    defects: List[DefectItem] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    actionable_recommendations: List[ActionableRecommendation] = Field(default_factory=list)
    inspected_objects: List[str] = Field(default_factory=list)
    scene_stats: Dict[str, Any] = Field(default_factory=dict)
    evaluated_angles: List[str] = Field(default_factory=list)
    capture_previews: List[MultiAngleCaptureFrame] = Field(default_factory=list)
    execution_time_seconds: float = 0.0
```

---

### 2.3 Mathematical & Algorithmic Implementation of Defect Categories

#### Category 1: Mesh Penetration & Clipping
- **Garment-on-Body Signed Distance**:
  For each garment vertex $\vec{w}_i$, query the nearest point $\vec{p}_i$ on the body surface with face unit normal $\hat{n}_i$ via BVH tree:
  $$\vec{d}_i = \vec{w}_i - \vec{p}_i, \quad s_i = \vec{d}_i \cdot \hat{n}_i$$
  Penetration occurs when:
  $$s_i < -\tau_{\text{clearance}} \quad (\text{default } \tau = 0.0005\text{m} = 0.5\text{mm})$$
  *Normal Alignment Filter*: Skips grazing and non-opposing faces:
  $$\hat{n}_{\text{garment}, i} \cdot \hat{n}_i > 0.3$$
- **Reverse Penetration (Skin Burst)**:
  Detects body vertices $\vec{b}_j$ protruding outward through garment layers ($s_{\text{burst}} = (\vec{b}_j - \vec{p}_{g, j}) \cdot \hat{n}_{g, j} > \tau$).
  *3-Tier False Positive Elimination*:
  1. *Height Clamping*: Restricts burst search to $g_{\min, z} + 2\text{mm} \le b_{j, z} \le g_{\max, z} - 2\text{mm}$, ensuring exposed limbs past hems or necklines are never misclassified as bursts.
  2. *Dual-Sided Normal Alignment*: Requires $\hat{n}_{\text{body}, j} \cdot \hat{n}_{g, j} > 0.3$.
  3. *Boundary Edge Opening Filter*: Identifies boundary half-edges of garments (e.g. armholes, collar). If the outward displacement aligns with the boundary normal $\vec{u}_{\text{out}}$, the vertex is passing through an opening rather than piercing fabric:
     $$(\vec{b}_j - \vec{p}_{g, j}) \cdot \vec{u}_{\text{out}} > 1.0\text{mm} \implies \text{Skip}$$
- **Triangle-Triangle Piercing**:
  Uses Möller's 3D triangle-triangle intersection algorithm on BVH bounding volume overlap pairs (`bvh_body.overlap(bvh_garment)`).

#### Category 2: Anthropometric Proportions
Evaluates body dimensions against target presets configured in `ANTHROPOMETRIC_PRESETS`:
1. *Total Height*: $H_{\text{total}} = Z_{\max} - Z_{\min}$.
2. *Head Height & Ratio*:
   $$R_{\text{head}} = \frac{H_{\text{total}}}{H_{\text{head}}}$$
   Derived via anatomical landmarks (`head_top` to `chin`), vertex group `head`, or morphological neck constriction slicing.
3. *Arm Span Ratio*:
   $$R_{\text{arm}} = \frac{W_{\text{span}}}{H_{\text{total}}} \quad (\text{Vitruvian nominal: } 1.00 \pm 0.05)$$
   Calculated across biacromial diameter plus left/right arm chains (`shoulder` $\to$ `elbow` $\to$ `wrist` $\to$ `fingers`).
4. *Shoulder-to-Hip Ratio*:
   $$R_{S/H} = \frac{W_{\text{shoulder}}}{W_{\text{hip}}}$$

| Preset | Target Heads ($R_{\text{head}}$) | Min-Max Heads | Arm Span Range | Shoulder/Hip (Fem) |
|---|---|---|---|---|
| `stylized_heroine` | 7.41 | [7.0, 7.8] | [0.92, 1.04] | [0.85, 1.08] |
| `realistic_female` | 7.50 | [7.2, 8.0] | [0.95, 1.05] | [0.82, 1.05] |
| `realistic_human` | 7.50 | [7.0, 8.0] | [0.95, 1.05] | [0.85, 1.15] |
| `heroic_male` | 8.20 | [8.0, 8.8] | [0.98, 1.08] | [1.15, 1.45] |
| `chibi_petite` | 4.80 | [4.0, 5.5] | [0.80, 0.95] | [0.80, 1.00] |
| `chibi` | 4.00 | [3.0, 4.8] | [0.75, 0.92] | [0.80, 1.00] |

#### Category 3: Rigging/Skinning Pinch & Volume Collapse
1. *Acute Dihedral Creasing*:
   For every internal edge shared by adjacent faces $F_A, F_B$ with unit normals $\hat{n}_A, \hat{n}_B$:
   $$\cos\theta = \hat{n}_A \cdot \hat{n}_B, \quad \theta_{\text{fold}} = \arccos(\cos\theta)$$
   If $\cos\theta < -0.85$ (fold angle $< 30.7^\circ$), an acute crease is diagnosed. If $\cos\theta < -0.95$ (fold angle $< 18.2^\circ$), severity escalates to `CRITICAL`.
2. *Joint Volume Conservation Ratio*:
   $$\rho_V = \frac{V_{\text{posed}}}{V_{\text{rest}}}$$
   - For watertight closed meshes: Evaluated via divergence theorem:
     $$V = \frac{1}{6} \left| \sum_{i} (\vec{v}_{i, 0} \times \vec{v}_{i, 1}) \cdot \vec{v}_{i, 2} \right|$$
   - For open or segmented meshes: Evaluated via cylindrical bounding slice volume centered at the joint Instantaneous Center of Rotation (ICR) with longitudinal span $\pm 5\text{cm}$.
   - *Thresholds*:
     * $\rho_V < 0.80 \implies$ Candy-wrapper volume collapse (MAJOR; CRITICAL if $\rho_V < 0.65$).
     * $\rho_V > 1.25 \implies$ Abnormal joint bulging (MAJOR).

#### Category 4: Grooming Curves Collision
Evaluates hair spline control points against scalp, body, and garment BVH trees:
1. *Submerged Roots*: Root point $\vec{p}_0$ checked against scalp:
   $$s_{\text{root}} = (\vec{p}_0 - \vec{p}_{\text{scalp}}) \cdot \hat{n}_{\text{scalp}} < -1.0\text{mm} \implies \text{Submerged inside cranium}$$
2. *Detached Roots*:
   $$s_{\text{root}} > +4.0\text{mm} \implies \text{Floating / detached hair root}$$
3. *Hair Shaft Collision*:
   Intermediate points $\vec{p}_k$ ($k \ge 1$) with strand radius $r_k$:
   $$s_{\text{eff}} = (\vec{p}_k - \vec{p}_{\text{body}}) \cdot \hat{n}_{\text{body}} - r_k < -0.5\text{mm} \implies \text{Shaft collision}$$
4. *Garment Piercing*: Evaluates $\vec{p}_k$ against garment BVHs with tolerance $-0.5\text{mm}$.

---

### 2.4 Quality Scoring Formula & Recommendation Generation

#### Quality Score Formulation
The overall quality score $S \in [0.0, 100.0]$ starts at $100.0$ and applies tiered deductions:
$$S = \max\left(0.0, \min\left(100.0, 100.0 - \left(25.0 \cdot N_{\text{CRITICAL}} + 10.0 \cdot N_{\text{MAJOR}} + 3.0 \cdot N_{\text{MINOR}}\right)\right)\right)$$

#### Pass / Fail Criterion
An asset passes verification (`passed = True`) if and only if:
1. $N_{\text{CRITICAL}} = 0$ (Zero critical structural defects)
2. $N_{\text{MAJOR}} \le 2$ (At most two minor/major remediable issues)
3. $S \ge 75.0$ (Overall quality score meets production standard)

#### Recommendation Generation Logic
Each diagnosed defect automatically generates a structured `ActionableRecommendation` containing exact parameter specifications:
- **Garment Penetration**:
  * Action: `APPLY_SHRINKWRAP_CLEARANCE`
  * Suggested Modifier: `Shrinkwrap`
  * Parameters: `offset_m = 1.25 * max_depth + 0.001`, `smoothing_method = "LAPLACIAN"`, `smooth_weights = True`.
- **Skin Burst**:
  * Action: `EXPAND_GARMENT_CONTOUR`
  * Guidance: Relax garment geometry around protruding vertices.
- **Head Proportion**:
  * Action: `RESCALE_HEAD`
  * Parameters: `scale_factor = R_head / R_nominal`.
- **Skinning Pinch / Crease**:
  * Action: `SMOOTH_SKINNING_WEIGHTS`
  * Parameters: `crease_edge = [v1, v2]`.
  * Guidance: Apply Laplacian weight smoothing across adjacent loops.
- **Volume Collapse**:
  * Action: `ACTIVATE_DUAL_BONE_TWIST_SKINNING`
  * Guidance: Decompose limb into dual-bone twist chains or enable dual-quaternion skinning.
- **Hair Collision**:
  * Action: `RELAX_HAIR_COLLISION`
  * Parameters: `deflection_offset_mm = 1.5`.

---

### 2.5 Achieving >95% Defect Diagnostics Accuracy

In `src/morphomesh/visual_critic.py`, the `run_defect_detection_benchmark()` and `benchmark_defect_detection()` functions execute an automated 9-state empirical verification test across all 4 defect domains:

```
+-------------------------------------------------------------------------------+
|                        BENCHMARK VERIFICATION MATRIX                          |
+--------------------+------------------------+-----------------+---------------+
| Defect Domain      | Test Fixture State     | Expected Result | Tested State  |
+--------------------+------------------------+-----------------+---------------+
| 1. Penetration     | Clean +20mm clearance  | True Negative   | PASSED        |
|                    | Defective -10mm burst  | True Positive   | PASSED        |
+--------------------+------------------------+-----------------+---------------+
| 2. Proportions     | Clean Heroine (7.41h)  | True Negative   | PASSED        |
|                    | Giant Head (5.20h)     | True Positive   | PASSED        |
|                    | Chibi Head (4.20h)     | True Positive   | PASSED        |
+--------------------+------------------------+-----------------+---------------+
| 3. Skinning        | Clean Posed Arm (rho=1)| True Negative   | PASSED        |
|                    | Collapsed Joint (rho=0)| True Positive   | PASSED        |
+--------------------+------------------------+-----------------+---------------+
| 4. Grooming        | Clean Splines (+2mm)   | True Negative   | PASSED        |
|                    | Submerged Splines (-5m)| True Positive   | PASSED        |
+--------------------+------------------------+-----------------+---------------+
```

**Benchmark Results**:
- Tests Run: 9
- True Positives: 5
- True Negatives: 4
- False Positives: 0
- False Negatives: 0
- **Diagnostic Accuracy**: **100.0%** (Requirement: $>95\%$)
- **False Positive Rate (FPR)**: **0.0%**

**Key Engineering Enablers for Accuracy**:
1. *Eberly 3D Point-to-Triangle Distance*: Accurately calculates true closest point on triangular surfaces across all 7 Voronoi regions (interior, 3 edges, 3 vertices) instead of relying on discrete vertex approximations.
2. *3-Tier Skin Burst Gating*: Completely eliminates false positives at open boundaries (hems, necklines, armholes).
3. *Exact Dihedral Angle Topology*: Traverses mesh half-edge structures to pair adjacent polygons, ensuring precise crease angle measurement.
4. *Divergence Theorem Volume*: Quantifies exact 3D enclosed volume changes down to $10^{-6}\text{m}^3$.

---

## 3. Deep Dive: R3 (Inspector Camera & Viewport Capture)

### 3.1 Hierarchical Bounding Box Calculation

Implemented in `src/morphomesh/camera_rig.py` via `calculate_hierarchy_bounds()`:
1. **Hierarchy Traversal**:
   Recursively collects all `MESH` objects starting from specified roots, parent Empties, or Armatures:
   $$\text{Objects} = \bigcup_{o \in \text{roots}} \text{traverse\_children}(o)$$
2. **Evaluated Depsgraph Transformation**:
   Uses Blender's evaluated dependency graph (`bpy.context.evaluated_depsgraph_get()`):
   $$\vec{v}_{\text{world}} = M_{\text{world}} \cdot \vec{v}_{\text{local}}$$
   This incorporates all active deformation modifiers (Armature skinning, Cloth physics, Subdivision Surface, Shrinkwrap).
3. **Bounding Extents & Bounding Sphere**:
   $$p_{\min, k} = \min_{v \in \text{vertices}} v_k, \quad p_{\max, k} = \max_{v \in \text{vertices}} v_k \quad (k \in \{x, y, z\})$$
   $$\vec{C} = \frac{\vec{p}_{\min} + \vec{p}_{\max}}{2}, \quad R = \frac{\|\vec{p}_{\max} - \vec{p}_{\min}\|}{2}$$
4. **Degenerate / Empty Fallback**:
   If no valid meshes exist, returns safe default bounds: $\vec{p}_{\min} = [-0.5, -0.5, 0.0]$, $\vec{p}_{\max} = [0.5, 0.5, 2.0]$, $\vec{C} = [0, 0, 1.0]$, $R = 1.0\text{m}$.

---

### 3.2 Five Anatomical Sub-Region Centers

Calculated in `get_anatomical_subregion_center()`:
- **Priority Tier 1 (Armature Bones)**:
  Queries world-space bone head positions if an Armature is present:
  * Head: `DEF-head` or `head`
  * Torso: `DEF-spine.002` or `spine`
  * Hands: `DEF-hand.R` or `DEF-hand.L`
  * Feet: `DEF-foot.R` or `DEF-foot.L`
- **Priority Tier 2 & 3 (Anthropometric Height Fractions)**:
  Derived from total height $H_{\text{total}} = Z_{\max} - Z_{\min}$ and bounding center $[C_x, C_y]$:

| Anatomical Region | Focus Center Z ($\vec{C}_z$) | Lateral X Offset | Framing Radius ($R_{\text{sub}}$) | Default Focal ($f$) |
|---|---|---|---|---|
| **Full Body** | $Z_{\min} + 0.50 \cdot H_{\text{total}}$ | $0.0\text{m}$ | $R_{\text{global}}$ | $50.0\text{mm}$ |
| **Head / Portrait** | $Z_{\min} + 0.88 \cdot H_{\text{total}}$ | $0.0\text{m}$ | $\max(0.15 \cdot H_{\text{total}}, 0.22\text{m})$ | $85.0\text{mm}$ |
| **Torso / Bodice** | $Z_{\min} + 0.60 \cdot H_{\text{total}}$ | $0.0\text{m}$ | $\max(0.25 \cdot H_{\text{total}}, 0.35\text{m})$ | $70.0\text{mm}$ |
| **Hands / Marionette**| $Z_{\min} + 0.50 \cdot H_{\text{total}}$ | $+0.35\text{m}$ | $\max(0.18 \cdot H_{\text{total}}, 0.25\text{m})$ | $85.0\text{mm}$ |
| **Feet / Sandals** | $Z_{\min} + 0.08 \cdot H_{\text{total}}$ | $0.0\text{m}$ | $\max(0.18 \cdot H_{\text{total}}, 0.25\text{m})$ | $70.0\text{mm}$ |

---

### 3.3 Optical Framing Distance Derivation

Calculated in `calculate_optical_framing_distance()`:
1. **Aspect Ratio & Sensor Dimension Resolution**:
   Given resolution $(W, H)$ and sensor width $S_w = 36.0\text{mm}$:
   $$\text{AR} = \frac{W}{H}$$
   Blender `sensor_fit = "AUTO"`:
   $$w_{\text{eff}} = \begin{cases} S_w & \text{if } \text{AR} \ge 1.0 \\ S_w \cdot \text{AR} & \text{if } \text{AR} < 1.0 \end{cases}, \quad h_{\text{eff}} = \begin{cases} \frac{S_w}{\text{AR}} & \text{if } \text{AR} \ge 1.0 \\ S_w & \text{if } \text{AR} < 1.0 \end{cases}$$
2. **Frustum Half-Angles**:
   $$\alpha_h = \arctan\left(\frac{w_{\text{eff}}}{2f}\right), \quad \alpha_v = \arctan\left(\frac{h_{\text{eff}}}{2f}\right)$$
   The governing constraining angle is:
   $$\alpha_{\min} = \min(\alpha_h, \alpha_v)$$
3. **Exact Spherical Tangency**:
   In the right triangle formed by the camera position, sphere center, and tangency point on the bounding sphere radius $R$:
   $$\sin(\alpha_{\min}) = \frac{R}{d} \implies d = \frac{R}{\sin(\alpha_{\min})}$$
4. **Safety Margin Application**:
   Applying safety margin $\mu$ (default $\mu = 0.15$):
   $$d_{\text{framed}} = \frac{R}{\sin(\alpha_{\min})} \cdot (1 + \mu)$$

---

### 3.4 Canonical Viewpoints & 360 Turntable Orbit

Implemented in `calculate_spherical_camera_position()` and `CANONICAL_VIEWPOINTS`:

#### 1. Spherical Orbit Placement
Given focus center $\vec{C}$, framing distance $d$, azimuth $\theta$, and elevation $\phi$:
$$x = C_x + d \cdot \cos(\phi) \cdot \sin(\theta)$$
$$y = C_y - d \cdot \cos(\phi) \cdot \cos(\theta)$$
$$z = C_z + d \cdot \sin(\phi)$$

#### 2. Look-At Rotation Matrix & Quaternion
The camera optical axis aims along $-Z$ with $+Y$ up:
$$\vec{F} = \frac{\vec{C} - \vec{P}_{\text{cam}}}{\|\vec{C} - \vec{P}_{\text{cam}}\|}, \quad \vec{R} = \frac{\vec{F} \times \hat{u}_{\text{world}}}{\|\vec{F} \times \hat{u}_{\text{world}}\|}, \quad \vec{U} = \vec{R} \times \vec{F}$$
Rotation matrix $[ \vec{R} \mid \vec{U} \mid -\vec{F} ]$ is converted via `to_track_quat('-Z', 'Y')` to Euler rotation.

#### 3. Standard Canonical Viewpoints Table

| Viewpoint Key | Azimuth ($\theta$) | Elevation ($\phi$) | Sub-Region | Default Focal ($f$) | Framing Margin ($\mu$) |
|---|---|---|---|---|---|
| `front` | $0.0^\circ$ | $0.0^\circ$ | Full Body | $50.0\text{mm}$ | 0.15 |
| `side` (or `side_right`) | $90.0^\circ$ | $0.0^\circ$ | Full Body | $50.0\text{mm}$ | 0.15 |
| `side_left` | $270.0^\circ$ | $0.0^\circ$ | Full Body | $50.0\text{mm}$ | 0.15 |
| `back` | $180.0^\circ$ | $0.0^\circ$ | Full Body | $50.0\text{mm}$ | 0.15 |
| `three_quarter` | $45.0^\circ$ | $15.0^\circ$ | Full Body | $50.0\text{mm}$ | 0.15 |
| `close_up_head` (or `head`) | $25.0^\circ$ | $10.0^\circ$ | Head | $85.0\text{mm}$ | 0.12 |
| `close_up_hands` (or `hands`)| $30.0^\circ$ | $15.0^\circ$ | Hands | $85.0\text{mm}$ | 0.15 |
| `torso` (or `bodice`) | $35.0^\circ$ | $10.0^\circ$ | Torso | $70.0\text{mm}$ | 0.15 |
| `feet` (or `sandals`) | $20.0^\circ$ | $15.0^\circ$ | Feet | $70.0\text{mm}$ | 0.15 |
| `top` | $0.0^\circ$ | $88.0^\circ$ | Full Body | $50.0\text{mm}$ | 0.20 |
| `bottom` | $0.0^\circ$ | $-88.0^\circ$ | Full Body | $50.0\text{mm}$ | 0.20 |

#### 4. Turntable Orbit
- `TURNTABLE_4VIEWS`: Standard 4-view turnaround `["front", "side", "back", "side_left"]`.
- $N$-Angle Turntable Sweep: Evenly spaced azimuth steps $\theta_k = \frac{360^\circ \cdot k}{N}$ with fixed elevation $\phi = 15^\circ$.

---

### 3.5 Dual-Mode Viewport Capture Pipeline

Implemented in `capture_viewport_image()`:

```
                                 capture_viewport_image()
                                            |
                         +------------------+------------------+
                         |                                     |
                [GUI Session Active]                  [Headless Session]
                         |                                     |
                         v                                     v
           Fast OpenGL Viewport Grab              Headless Workbench Fallback
        (bpy.ops.render.opengl)                  (bpy.ops.render.render)
                         |                                     |
       - Finds active VIEW_3D area              - Switches engine to 'BLENDER_WORKBENCH'
       - Enforces space.region_3d = 'CAMERA'    - Configures shading.light = 'STUDIO'
       - Configures shading (SOLID/RANDOM)      - Configures color_type = 'RANDOM'
       - Disables floor/axis overlays           - Enables screen cavity (SCREEN)
       - Executes in temp_override context      - Restores previous engine in finally:
       - Restores viewport state in finally:    - Speed: <700ms
       - Speed: <200ms                                         |
                         |                                     |
                         +------------------+------------------+
                                            |
                                            v
                              [Completely Offline Fallback]
                                            |
                               - Generates valid PNG via PIL
                                 or writes FALLBACK_PNG_BYTES
                               - Encodes Base64 preview
```

1. **Interactive OpenGL Grab**:
   - Executes `bpy.ops.render.opengl(write_still=True)` using `bpy.context.temp_override(area=view3d_area, window=win, region=reg)`.
   - Bypasses shader compilation and ray tracing, directly grabbing the OpenGL framebuffer in $<200\text{ms}$.
2. **Headless Workbench Fallback**:
   - If `bpy.app.background == True` or no GUI window exists, switches `scene.render.engine = 'BLENDER_WORKBENCH'`.
   - Enables screen-space cavity shading (`show_cavity = True`, `cavity_type = 'SCREEN'`) to highlight surface relief and contour silhouettes.
   - Executes offscreen Workbench render in $<700\text{ms}$.
3. **Diagnostic Shading & Coloring Support**:
   - `shading_mode`: `SOLID`, `FLAT`, `WIREFRAME`, `MATERIAL`, `RENDERED`.
   - `color_type`: `RANDOM` (assigns distinct random color per mesh object, immediately highlighting mesh boundaries and clipping), `MATERIAL`, `SINGLE`, `OBJECT`, `TEXTURE`.

---

### 3.6 Output Paths & Artifact Specifications

1. **Path Resolution**:
   - Caller can supply explicit `output_path` or directory `output_dir`.
   - If unspecified, generates unique sanitized path in OS temp directory: `${TMPDIR}/viewport_${UUID8}.png` or `${TMPDIR}/inspect_${VIEWPOINT}_${UUID6}.png`.
   - Production exports are routed to `artifacts/` or `output/` (e.g. `artifacts/preview_front.png`).
2. **Image Format**:
   - Lossless 24-bit RGB or 32-bit RGBA PNG.
   - Resolution configurable: default $1024 \times 1024$, ultra-res $2048 \times 2048$ or cinematic $1920 \times 1080$.
3. **Base64 Embedding**:
   - Every capture output (`CaptureViewportOutput`, `MultiAngleCaptureFrame`) provides a `base64_preview` / `base64_image` string.
   - Enables immediate visual presentation in chat interfaces or FastMCP clients without filesystem access.

---

## 4. FastMCP Tooling Layer & Compatibility (R1)

### 4.1 Tool Specifications

| Tool Name | Parameters | Returns | Primary Function |
|---|---|---|---|
| `morphomesh_setup_inspector_camera_rig` | `viewpoint`, `target_center`, `sub_region`, `focal_length`, `camera_name`, `mesh_objects` | `SetupInspectorCameraOutput` (dict) | Positions inspector camera and aims look-at tracking |
| `morphomesh_capture_viewport` | `output_path`, `camera_name`, `resolution`, `shading_mode`, `color_type` | `CaptureViewportOutput` (dict) | Ultra-fast ($<200\text{ms}$) OpenGL/Workbench viewport capture |
| `morphomesh_critique_visual_quality` | `character_name`, `target_object`, `camera_angles`, `clearance_tolerance`, `target_preset` | `VisualCritiqueOutput` (dict) | Full structural defect critique and actionable remediation plan |

### 4.2 Gating Mechanism

Located in `src/morphomesh/server.py`:
- **Default (Unset)**: `mcp.list_tools()` returns the 7 canonical creature tools (`morphomesh_generate_concept`, `morphomesh_create_3d_asset`, `morphomesh_optimize_topology`, `morphomesh_auto_rig`, `morphomesh_blender_execute`, `morphomesh_get_scene_status`, `morphomesh_render_preview`).
- **Inspection Tools Enabled (`MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1`)**: Adds the 3 inspection tools (total 10 tools).
- **Human Tools Enabled (`MORPHOMESH_INCLUDE_HUMAN_TOOLS=1`)**: Adds the 7 human generation tools (total 14 tools).
- **All Tools Enabled (`MORPHOMESH_INCLUDE_ALL_TOOLS=1`)**: Returns all 17 registered tools.
- **Direct Calling**: Tools remain callable via `mcp.call_tool()` even when hidden from `list_tools`, ensuring zero breakage for existing clients.

---

## 5. Verification Test Suite Status

The inspection and visual critic subsystems are thoroughly verified across multiple test suites:

| Test Suite File | Test Scope | Result | Execution Time |
|---|---|---|---|
| `tests/test_visual_critic.py` | Models, PurePythonBVHTree, procedural fixtures, benchmark, bridge | **25 PASSED** | ~1.5s |
| `tests/test_inspector_camera.py` | Bounding box math, framing trigonometry, viewpoints, anatomical centers | **25 PASSED** | ~1.2s |
| `tests/test_adversarial_critic_benchmark.py` | Benchmark sensitivity, proportion fuzzing, volume divergence, creasing | **23 PASSED** | ~1.8s |
| `tests/test_adversarial_camera_math.py` | Extreme focal lengths, aspect ratios, polar singularities, turntable | **110 PASSED** | ~2.5s |
| `tests/test_adversarial_viewport_capture.py` | Batch fuzzing, shading combinations, fault injection, leak audit | **40 PASSED** (3 skipped live socket) | ~2.0s |
| `tests/test_fastmcp_inspection_tools.py` | FastMCP registration, schemas, execution, gating, error handling | **21 PASSED** | ~6.4s |
| `tests/test_adversarial_m4_gating.py` | Tool gating transitions, argument validation, ToolError enforcement | **32 PASSED** | ~1.5s |
| `tests/test_adversarial_error_injection_m4.py` | Invalid viewpoints, focal lengths, shading modes, offline resilience | **35 PASSED** | ~1.2s |
| **Combined R2/R3 Test Suite** | **All inspection & visual critic unit and adversarial tests** | **311 PASSED** (100% pass) | **~18s** |

---

## 6. Actionable Implementation Guidelines for Workers

### 6.1 Worker Task Matrix for Final Hardening (M4–M5)

1. **Scene Verification Script**:
   - Workers executing E2E scene verification should invoke `morphomesh.critique_visual_quality` on the completed Dư Niệm An scene (`Human_Base_Mesh`, `Dress_Bodice`, `Pleated_Skirt`, `Waist_Sash`, `Flat_Sandals`, `Hair_Hime_Cut`).
   - Confirm that `passed == True`, `quality_score >= 85.0`, and `defects` list contains 0 critical defects.
2. **Multi-Angle Preview Generation**:
   - Capture a 6-angle preview package for export verification using `capture_multi_angle_inspection()`:
     * `front` (Full body silhouette)
     * `three_quarter` (Hero dynamic 3D angle)
     * `side` (Posture, bust teardrop and lumbar lordosis profile)
     * `back` (Hime hair draping, posterior sash bow)
     * `close_up_head` (Facial features, eyes, bangs)
     * `close_up_hands` (10 marionette strings, fingers, butterflies)
   - Save output frames to `artifacts/inspection_previews/`.
3. **FastMCP Server Gating Verification**:
   - Ensure production container or launch script sets `MORPHOMESH_INCLUDE_ALL_TOOLS=1` when running in full DCC production mode, and verify that all 17 tools respond properly.
4. **Offline Resilience**:
   - Confirm that if Blender socket connection is dropped, bridge calls fail over gracefully to `morphomesh.camera_rig` and `morphomesh.visual_critic` offline shims rather than unhandled socket crashes.

---

## 7. Conclusion

The MorphoMesh R2 (Closed-Loop Visual Critic & Automated QA) and R3 (Multi-Angle Inspector Camera & Fast Viewport Capture) subsystems are fully architected, mathematically validated, and backed by comprehensive automated test suites.

- **R2 Visual Critic** provides robust, multi-layer defect detection (signed distance penetration with boundary filtering, anthropometric ratios, joint volume conservation via divergence theorem, and hair collision) with **100% benchmark accuracy** and structured Pydantic v2 diagnostic output.
- **R3 Inspector Camera** delivers mathematically exact optical framing distance derivation, 5 anatomical sub-region centering, 6 canonical viewing perspectives with turntable orbit, and dual-mode OpenGL/Workbench viewport capture in $<200\text{ms}$.
- **FastMCP Tooling** seamlessly exposes these capabilities with robust error handling and backward-compatible environment gating.
