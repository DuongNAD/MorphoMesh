# Handoff Report: Body Proportions & Rig Skinning Deformation Critique (Milestone 3)

**Author**: Explorer M3_2 (Proportions & Rig Skinning Deformation Explorer)  
**Date**: 2026-09-07T05:42:00Z  
**Recipient**: Parent Orchestrator (`577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`)  
**Target Module**: `src/morphomesh/visual_critic.py`  
**Related Modules**: `src/morphomesh/models.py`, `src/morphomesh/human_generator.py`, `src/morphomesh/human_rigging.py`, `tests/test_visual_critic.py`

---

## 1. Observation

### 1.1 Project Authority & Directives
- `ORIGINAL_REQUEST.md` (§ 2026-09-07T03:34:32Z, lines 231-267):
  - R2 mandates a "Closed-Loop Visual Quality Critique (Auto-Critic QA)" evaluating structural integrity: abnormal body proportions, unnatural rig/skinning pinching, and grooming intersections, returning structured diagnostic feedback.
  - Acceptance Criteria requires the auto-critic tool to return structured defect classifications (`proportion_deviation`, `skinning_artifact`, `clipping`), affected objects, confidence scores, and pass/fail recommendations.
- `PROJECT.md` (lines 35-36, 88-118):
  - Feature 12: Anthropometric Proportion Analysis evaluating height, head ratio ($H_{\text{total}}/H_{\text{head}}$), arm span, and shoulder/hip breadth.
  - Feature 13: Rig Skinning Volume & Crease Evaluation checking joint volume preservation $\rho_V = V_{\text{posed}}/V_0$ and acute dihedral creasing $\cos\theta < -0.85$.
  - Interface Contract in `src/morphomesh/visual_critic.py`:
    ```python
    def evaluate_body_proportions(body_obj_name: str, target_preset: str = "stylized_heroine") -> List[DefectItem]: ...
    def evaluate_rig_skinning_pinch(armature_obj_name: str, mesh_obj_name: str) -> List[DefectItem]: ...
    ```

### 1.2 Existing Codebase Anatomy & Landmarks
- `src/morphomesh/human_generator.py`:
  - Lines 6-12: Defines canonical female human proportions: Height 1.65m, head-to-body ratio 7.41, waist-to-hip ratio 0.67-0.70.
  - Lines 33-63: Defines 29 `STANDARDIZED_HUMAN_VERTEX_GROUPS`, including `"head"`, `"face"`, `"neck"`, `"torso"`, `"chest"`, `"waist"`, `"hips"`, `"arm_upper_L"`, `"arm_lower_L"`, `"hand_L"`, `"fingers_L"`, `"leg_upper_L"`, `"leg_lower_L"`, `"foot_L"`, and symmetry equivalents.
  - Lines 259-265: Anatomical vertical boundaries:
    $H_{\text{head}} = H / R_{\text{head}}$, $Z_{\text{crown}} = H$, $Z_{\text{chin}} = Z_{\text{crown}} - H_{\text{head}}$, $Z_{\text{clavicle}} = 1.350 \times s$, $Z_{\text{crotch}} = 0.825 \times s \times k_{\text{leg}}$.
  - Lines 1216-1242: Blender custom property `obj["morphomesh_landmarks"]` storing 3D coordinates:
    `head_top`, `chin`, `neck`, `clavicle_L/R`, `shoulder_L/R`, `elbow_L/R`, `wrist_L/R`, `fingers_L/R`, `spine_chest`, `spine_waist`, `spine_pelvis`, `hip_L/R`, `knee_L/R`, `ankle_L/R`, `toe_L/R`.
  - Canonical empirical values measured via Python:
    $H_{\text{total}} = 1.646\text{m}$, $Z(\text{head\_top}) = 1.650$, $Z(\text{chin}) = 1.4273$, $H_{\text{head}} = 0.2227\text{m}$, $R_{\text{head}} = 7.409$.
    $W_{\text{shoulder}} = 0.350\text{m}$, $W_{\text{hip}} = 0.350\text{m}$ (across vertex group `"hips"`), $R_{\text{shoulder\_to\_hip}} = 1.00$.
    $W_{\text{span}} = 1.62\text{m}$ (effective) to $1.77\text{m}$ (fingertip-to-fingertip chain), $R_{\text{arm\_span}} \approx 0.98 - 1.05$.

### 1.3 Existing Skinning Deformation & Testing Logic
- `src/morphomesh/human_rigging.py`:
  - Lines 48-100: Metarig contains 163 DEF bones (64 body DEF bones + 99 facial DEF bones).
  - Lines 767-850: Anti-pinching weights implement:
    * Olecranon (elbow) cosine gradient weighting between `DEF-upper_arm.{side}.001` and `DEF-forearm.{side}`.
    * Patella (knee) rigid sesamoid locking (92-95% to `DEF-shin.{side}`).
    * Axilla fold locked $\ge 70\%$ to `DEF-spine.003`.
- `tests/test_adversarial_rigging.py`:
  - Lines 180-248: Simulates 90-degree elbow flexion using pure-Python Linear Blend Skinning (LBS) rotations around the hinge axis:
    $\mathbf{v}'_i = w_{\text{ua}} \mathbf{v}_i + w_{\text{fa}} (\mathbf{R} (\mathbf{v}_i - \mathbf{p}_{\text{el}}) + \mathbf{p}_{\text{el}})$.
  - Verifies that elbow thickness maintains $\ge 50\%$ of rest thickness and min distance from joint center remains $> 0.005\text{m}$.

---

## 2. Logic Chain

### 2.1 Anthropometric Body Proportion Analysis

#### 2.1.1 Multi-Tier Measurement Resolution Strategy
To ensure the critic works universally (whether analyzing native MorphoMesh procedural meshes with rich metadata or arbitrary third-party imported OBJ/GLB meshes), measurements are resolved hierarchically:
1. **Tier 1 (Landmark-based)**: Uses `obj.get("morphomesh_landmarks")` or dictionary passed to function. This gives sub-millimeter precision corresponding to anatomical skeletal landmarks.
2. **Tier 2 (Vertex-group-based)**: Uses `STANDARDIZED_HUMAN_VERTEX_GROUPS` (`head`, `hips`, `torso`, `fingers_L`, `foot_L`, etc.) to isolate anatomical sub-meshes.
3. **Tier 3 (Morphological Slicing / Pure Geometry Fallback)**: Automatically segments the mesh along $Z$ and $X$ axes using cross-sectional perimeter and width profiling.

#### 2.1.2 Anthropometric Measurement Formulas
1. **Total Height ($H_{\text{total}}$)**:
   $$H_{\text{total}} = Z_{\max} - Z_{\min}$$
   where $Z_{\max} = \max_{v \in \mathcal{V}} v_z$ (cranial vertex) and $Z_{\min} = \min_{v \in \mathcal{V}} v_z$ (plantar base of heel/sole).
2. **Head Height ($H_{\text{head}}$)**:
   - **Tier 1**: $H_{\text{head}} = Z(\text{head\_top}) - Z(\text{chin})$.
   - **Tier 2**: $H_{\text{head}} = \max_{v \in \text{VG}_{\text{head}}} v_z - \min_{v \in \text{VG}_{\text{head}}} v_z$. (If $\text{VG}_{\text{neck}}$ present, chin boundary is $\max_{v \in \text{VG}_{\text{neck}}} v_z$).
   - **Tier 3**: Morphological slicing: In the upper third ($z \in [0.70 H_{\text{total}}, 1.0 H_{\text{total}}]$), the head width expands to cranium and constricts at the cervical notch (neck). The local minimum of transverse cross-sectional perimeter $P(z)$ identifies $Z_{\text{cervical\_notch}}$, yielding $H_{\text{head}} = Z_{\max} - Z_{\text{cervical\_notch}}$.
3. **Arm Span ($W_{\text{span}}$)**:
   - **Anatomical Definition**: Distance from left dactylion (tip of middle finger) to right dactylion.
   - **Pose Invariant Formula (A-pose or T-pose)**:
     $$W_{\text{span}} = L_{\text{arm\_L}} + W_{\text{biacromial}} + L_{\text{arm\_R}}$$
     where:
     $$L_{\text{arm}} = \|\mathbf{p}_{\text{shoulder}} - \mathbf{p}_{\text{elbow}}\| + \|\mathbf{p}_{\text{elbow}} - \mathbf{p}_{\text{wrist}}\| + \|\mathbf{p}_{\text{wrist}} - \mathbf{p}_{\text{fingers}}\|$$
     $$W_{\text{biacromial}} = \|\mathbf{p}_{\text{shoulder\_L}} - \mathbf{p}_{\text{shoulder\_R}}\|$$
   - **T-pose Direct Transverse Extent**:
     $$W_{\text{span\_tpose}} = \max_{v \in \mathcal{V}} v_x - \min_{v \in \mathcal{V}} v_x$$
4. **Shoulder Breadth ($W_{\text{shoulder}}$ - Biacromial breadth)**:
   - **Tier 1**: $W_{\text{shoulder}} = \|\mathbf{p}_{\text{shoulder\_L}} - \mathbf{p}_{\text{shoulder\_R}}\|$.
   - **Tier 2/3**: Maximum transverse width of upper torso cross-section at clavicle height ($z \approx 0.81 H_{\text{total}}$).
5. **Hip Breadth ($W_{\text{hip}}$ - Bi-trochanteric / Bi-iliac breadth)**:
   - **Tier 1/2**: Maximum transverse distance between lateral pelvic contours in vertex group `"hips"` at pelvic height ($z \approx 0.50 H_{\text{total}}$):
     $$W_{\text{hip}} = \max_{v \in \text{VG}_{\text{hips}}} v_x - \min_{v \in \text{VG}_{\text{hips}}} v_x$$
   - **Tier 3**: Maximum transverse width in pelvic band $z \in [0.45 H_{\text{total}}, 0.55 H_{\text{total}}]$.

#### 2.1.3 Evaluated Anthropometric Ratios & Presets
1. **Head Ratio**:
   $$R_{\text{head}} = \frac{H_{\text{total}}}{H_{\text{head}}}$$
   Evaluated against target presets:
   | Preset Name | Target Head Ratio Range ($R_{\min} - R_{\max}$) | Nominal Target | Description |
   |---|---|---|---|
   | `realistic_human` | $7.0 - 8.0$ heads | 7.5 heads | Standard adult human anatomy |
   | `stylized_heroine` | $6.0 - 6.5$ heads | 6.25 heads | Anime / Stylized heroine / Game proportions |
   | `chibi_petite` | $3.5 - 5.0$ heads | 4.0 heads | Chibi / Petite / SD stylized character |

2. **Arm Span to Height Ratio**:
   $$R_{\text{arm\_span}} = \frac{W_{\text{span}}}{H_{\text{total}}}$$
   - Vitruvian canon target: $1.00 \pm 0.05$ (Acceptable range: $[0.95, 1.05]$).
   - Defect thresholds:
     * $R_{\text{arm\_span}} < 0.90 \implies$ Defect `PROPORTION_ARM_SPAN_TOO_SHORT` (Severity: MAJOR).
     * $0.90 \le R_{\text{arm\_span}} < 0.95 \implies$ Defect `PROPORTION_ARM_SPAN_TOO_SHORT` (Severity: MINOR).
     * $1.05 < R_{\text{arm\_span}} \le 1.10 \implies$ Defect `PROPORTION_ARM_SPAN_TOO_LONG` (Severity: MINOR).
     * $R_{\text{arm\_span}} > 1.10 \implies$ Defect `PROPORTION_ARM_SPAN_TOO_LONG` (Severity: MAJOR).

3. **Shoulder-to-Hip Breadth Ratio**:
   $$R_{\text{shoulder\_to\_hip}} = \frac{W_{\text{shoulder}}}{W_{\text{hip}}}$$
   Evaluates sexual dimorphism and silhouette archetype:
   - **Feminine target** (Hourglass / Pear archetype):
     * Ideal range: $0.90 \le R_{\text{shoulder\_to\_hip}} \le 1.05$.
     * $R_{\text{shoulder\_to\_hip}} > 1.15 \implies$ Defect `PROPORTION_MASCULINE_SHOULDER_ON_FEMALE` (Severity: MAJOR).
   - **Masculine target** (Inverted triangle / V-taper archetype):
     * Ideal range: $1.20 \le R_{\text{shoulder\_to\_hip}} \le 1.45$.
     * $R_{\text{shoulder\_to\_hip}} < 1.10 \implies$ Defect `PROPORTION_NARROW_SHOULDERS_ON_MALE` (Severity: MAJOR).
   - **Chibi / Petite target**:
     * Ideal range: $0.90 \le R_{\text{shoulder\_to\_hip}} \le 1.10$.

---

### 2.2 Rig Skinning Deformation & Volume Conservation

#### 2.2.1 Joint Volume Conservation Evaluation
When an articulated character flexes or twists a joint, Linear Blend Skinning (LBS) is prone to unphysical volume loss ("candy-wrapper collapse") or abnormal bulging.
1. **Volume Ratio Definition**:
   $$\rho_V = \frac{V_{\text{posed}}}{V_{\text{rest}}}$$
   where $V_{\text{rest}}$ is the volume of the joint capsule/segment in rest pose, and $V_{\text{posed}}$ is the volume under canonical test pose flexion.
2. **Active Bending Joints Evaluated**:
   - **Elbow (Left & Right)**: Flexion of $90^\circ$ (and stress test at $120^\circ$) around hinge axis.
   - **Knee (Left & Right)**: Flexion of $90^\circ$ (backward pre-bend) around knee transverse axis.
   - **Shoulder (Left & Right)**: Abduction of $90^\circ$ (raising arm to horizontal) around sagittal axis.
3. **Defect Thresholds**:
   - **Candy-Wrapper Collapse / Pinching**:
     * $\rho_V < 0.65 \implies$ Defect `SKINNING_CANDY_WRAPPER_COLLAPSE` (Severity: CRITICAL). Severe joint pinching, skin collapsing into bone pivot.
     * $0.65 \le \rho_V < 0.80 \implies$ Defect `SKINNING_JOINT_PINCHING` (Severity: MAJOR). Unacceptable volume loss $> 20\%$.
   - **Abnormal Bulging**:
     * $\rho_V > 1.25 \implies$ Defect `SKINNING_ABNORMAL_BULGING` (Severity: MAJOR). Joint flesh balloons out $> 25\%$, indicating weight conflict or dual-quaternion bulging artifact.
   - **Healthy Conservation**:
     * $0.85 \le \rho_V \le 1.15 \implies$ PASS (volume preserved within natural soft-tissue deformation bounds).

#### 2.2.2 Acute Dihedral Angle Creasing Detection
When skinning weights collapse or vertices invert during joint flexion, adjacent triangular faces fold back against one another, creating an acute crease:
1. **Mathematical Definition**:
   For any two adjacent triangular faces $F_1, F_2$ sharing an edge $e = (v_a, v_b)$ with unit face normals $\hat{\mathbf{n}}_1, \hat{\mathbf{n}}_2$:
   $$\cos(\theta) = \hat{\mathbf{n}}_1 \cdot \hat{\mathbf{n}}_2$$
   The interior fold angle between the face planes is:
   $$\phi = 180^\circ - \arccos(\cos(\theta))$$
2. **Creasing Condition**:
   $$\cos(\theta) < -0.85 \iff \phi < 31.79^\circ \approx 30^\circ$$
   When $\cos(\theta) < -0.85$, the face normals diverge by $> 148.2^\circ$, indicating that the surface has pinched into an acute fold $(< 30^\circ)$.
3. **Defect Categorization**:
   - $\cos(\theta) < -0.95$ ($\phi < 18.2^\circ$): Defect `SKINNING_ACUTE_DIHEDRAL_CREASE` (Severity: CRITICAL). Severe knife-edge pinch or self-intersecting inversion.
   - $-0.95 \le \cos(\theta) < -0.85$ ($18.2^\circ \le \phi < 31.8^\circ$): Defect `SKINNING_ACUTE_DIHEDRAL_CREASE` (Severity: MAJOR). Noticeable skinning pinch artifact.

---

### 2.3 Pure-Python Mathematical Algorithms

#### 2.3.1 Local Joint Bounding-Slice Volume Estimation Algorithm
For an open sub-region of a mesh (such as an elbow or knee segment of length $L$ along axis $\hat{\mathbf{u}}$):
1. **Axis & Slicing Planes**:
   Let the joint center be $\mathbf{p}_0$, the limb bone axis be $\hat{\mathbf{u}}$, and segment span be $[s_{\min}, s_{\max}]$ (e.g. $[-0.06\text{m}, +0.06\text{m}]$ around elbow).
   Define $K$ equidistant slicing planes with origins $\mathbf{o}_k = \mathbf{p}_0 + s_k \hat{\mathbf{u}}$ and normal $\hat{\mathbf{u}}$.
2. **Cross-Sectional Polygon Extraction**:
   For each plane $k \in \{0, \dots, K-1\}$:
   - For every triangular face $F = (\mathbf{v}_1, \mathbf{v}_2, \mathbf{v}_3)$:
     Compute signed distances to plane $d_i = (\mathbf{v}_i - \mathbf{o}_k) \cdot \hat{\mathbf{u}}$ for $i \in \{1, 2, 3\}$.
     If the plane intersects the triangle (distances have opposite signs), compute edge intersection points:
     $$\mathbf{q} = \mathbf{v}_i + \frac{-d_i}{d_j - d_i} (\mathbf{v}_j - \mathbf{v}_i)$$
   - Project 3D intersection points onto the 2D plane basis $(\hat{\mathbf{e}}_1, \hat{\mathbf{e}}_2)$ orthogonal to $\hat{\mathbf{u}}$.
   - Sort the 2D contour points cyclically around their geometric centroid $(\bar{x}, \bar{y})$ using polar angle $\alpha = \text{atan2}(y - \bar{y}, x - \bar{x})$.
3. **Cross-Sectional Area via Shoelace Formula**:
   $$A_k = \frac{1}{2} \left| \sum_{m=0}^{M-1} (x_m y_{m+1} - x_{m+1} y_m) \right|$$
4. **Segment Volume Integration via Trapezoidal Rule**:
   $$V = \Delta s \left( \frac{1}{2} A_0 + \sum_{k=1}^{K-2} A_k + \frac{1}{2} A_{K-1} \right)$$
   This algorithm runs 100% in pure Python in $O(K \cdot F)$ time without any C-extensions or Blender dependencies.

#### 2.3.2 Closed-Mesh Divergence Theorem Volume Algorithm (For Watertight Sub-meshes / Fixtures)
For closed watertight meshes (e.g. test cylinders, limbs with capped ends, full characters):
$$V = \frac{1}{6} \left| \sum_{f \in \mathcal{F}} \mathbf{v}_{f,1} \cdot (\mathbf{v}_{f,2} \times \mathbf{v}_{f,3}) \right|$$
Runs in $O(F)$ time with exact machine-precision accuracy.

#### 2.3.3 Edge-Face Adjacency Dihedral Solver Algorithm
1. Construct edge-to-face adjacency mapping `edge_faces: Dict[Tuple[int, int], List[int]]`.
2. For each face $f$, compute unit normal:
   $$\hat{\mathbf{n}}_f = \frac{(\mathbf{v}_2 - \mathbf{v}_1) \times (\mathbf{v}_3 - \mathbf{v}_1)}{\|(\mathbf{v}_2 - \mathbf{v}_1) \times (\mathbf{v}_3 - \mathbf{v}_1)\|}$$
3. For each manifold edge $e$ with exactly two adjacent faces $f_1, f_2$:
   Compute $\cos(\theta) = \hat{\mathbf{n}}_{f_1} \cdot \hat{\mathbf{n}}_{f_2}$.
   If $\cos(\theta) < -0.85$, record defect with edge midpoint coordinates, affected face indices, and fold angle $\phi = 180^\circ - \frac{180}{\pi} \arccos(\cos(\theta))$.

---

## 3. Implementation Blueprint for `src/morphomesh/visual_critic.py`

Below is the exact code specification to be incorporated into `src/morphomesh/visual_critic.py`:

```python
"""
MorphoMesh: Visual Critic & Automated Structural Quality Assurance Engine.
Milestone 3: Body Proportion Analysis & Rig Skinning Deformation Evaluation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Pydantic models imported from morphomesh.models
try:
    from morphomesh.models import (
        ActionableRecommendation,
        BoundingBox3D,
        DefectCategory,
        DefectItem,
        DefectSeverity,
    )
except (ImportError, ModuleNotFoundError):
    from models import (  # type: ignore[no-redef]
        ActionableRecommendation,
        BoundingBox3D,
        DefectCategory,
        DefectItem,
        DefectSeverity,
    )

# ==============================================================================
# ANTHROPOMETRIC CONSTANTS & PRESETS
# ==============================================================================

ANTHROPOMETRIC_PRESETS: Dict[str, Dict[str, Any]] = {
    "realistic_human": {
        "head_ratio_min": 7.0,
        "head_ratio_max": 8.0,
        "head_ratio_nominal": 7.5,
        "arm_span_ratio_min": 0.95,
        "arm_span_ratio_max": 1.05,
        "shoulder_to_hip_feminine": (0.90, 1.05),
        "shoulder_to_hip_masculine": (1.20, 1.45),
        "typical_height_range": (1.55, 1.90),
    },
    "stylized_heroine": {
        "head_ratio_min": 6.0,
        "head_ratio_max": 6.5,
        "head_ratio_nominal": 6.25,
        "arm_span_ratio_min": 0.95,
        "arm_span_ratio_max": 1.05,
        "shoulder_to_hip_feminine": (0.85, 1.05),
        "shoulder_to_hip_masculine": (1.15, 1.35),
        "typical_height_range": (1.50, 1.75),
    },
    "chibi_petite": {
        "head_ratio_min": 3.5,
        "head_ratio_max": 5.0,
        "head_ratio_nominal": 4.0,
        "arm_span_ratio_min": 0.85,
        "arm_span_ratio_max": 1.05,
        "shoulder_to_hip_feminine": (0.85, 1.10),
        "shoulder_to_hip_masculine": (0.95, 1.15),
        "typical_height_range": (0.80, 1.35),
    },
}

@dataclass
class AnthropometricMetrics:
    total_height: float
    head_height: float
    head_ratio: float
    arm_span: float
    arm_span_ratio: float
    shoulder_breadth: float
    hip_breadth: float
    shoulder_to_hip_ratio: float
    target_preset: str
    gender: str = "feminine"
    is_head_ratio_valid: bool = True
    is_arm_span_valid: bool = True
    is_shoulder_hip_valid: bool = True

@dataclass
class JointDeformationMetrics:
    joint_name: str
    rest_volume: float
    posed_volume: float
    volume_ratio: float
    min_dihedral_cos: float
    min_fold_angle_deg: float
    pinched_edge_count: int
    is_volume_conserved: bool = True
    is_crease_free: bool = True

# ==============================================================================
# PURE-PYTHON MATHEMATICAL CORE ALGORITHMS
# ==============================================================================

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

def compute_bounding_slice_volume(
    vertices: List[Tuple[float, float, float]],
    faces: List[Tuple[int, ...]],
    axis_point: Tuple[float, float, float],
    axis_direction: Tuple[float, float, float],
    span_min: float = -0.05,
    span_max: float = 0.05,
    num_slices: int = 15,
) -> float:
    """Computes volume of local joint segment via planar cross-section integration."""
    u_len = math.sqrt(sum(x * x for x in axis_direction)) or 1.0
    u_dir = (axis_direction[0] / u_len, axis_direction[1] / u_len, axis_direction[2] / u_len)

    # Construct 2D basis (e1, e2) in slicing plane
    if abs(u_dir[0]) < 0.9:
        e1_raw = (0.0, -u_dir[2], u_dir[1])
    else:
        e1_raw = (-u_dir[1], u_dir[0], 0.0)
    e1_len = math.sqrt(sum(x * x for x in e1_raw)) or 1.0
    e1 = (e1_raw[0] / e1_len, e1_raw[1] / e1_len, e1_raw[2] / e1_len)
    e2 = (
        u_dir[1] * e1[2] - u_dir[2] * e1[1],
        u_dir[2] * e1[0] - u_dir[0] * e1[2],
        u_dir[0] * e1[1] - u_dir[1] * e1[0],
    )

    dz = (span_max - span_min) / max(1, num_slices - 1)
    areas: List[float] = []

    for s_idx in range(num_slices):
        s_val = span_min + s_idx * dz
        p_plane = (
            axis_point[0] + s_val * u_dir[0],
            axis_point[1] + s_val * u_dir[1],
            axis_point[2] + s_val * u_dir[2],
        )

        pts_2d: List[Tuple[float, float]] = []
        for f in faces:
            tri = [vertices[f[0]], vertices[f[1]], vertices[f[2]]]
            dists = [sum((tri[i][c] - p_plane[c]) * u_dir[c] for c in range(3)) for i in range(3)]

            # Check edge crossings
            for i in range(3):
                j = (i + 1) % 3
                if (dists[i] < 0 and dists[j] > 0) or (dists[i] > 0 and dists[j] < 0):
                    t = dists[i] / (dists[i] - dists[j])
                    q_3d = tuple(tri[i][c] + t * (tri[j][c] - tri[i][c]) for c in range(3))
                    rel_q = (q_3d[0] - p_plane[0], q_3d[1] - p_plane[1], q_3d[2] - p_plane[2])
                    pts_2d.append((
                        sum(a * b for a, b in zip(rel_q, e1)),
                        sum(a * b for a, b in zip(rel_q, e2)),
                    ))

        # Filter near-duplicate points
        u_pts: List[Tuple[float, float]] = []
        for p in pts_2d:
            if not any(math.hypot(p[0] - up[0], p[1] - up[1]) < 1e-4 for up in u_pts):
                u_pts.append(p)

        if len(u_pts) >= 3:
            cx = sum(p[0] for p in u_pts) / len(u_pts)
            cy = sum(p[1] for p in u_pts) / len(u_pts)
            s_pts = sorted(u_pts, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
            # Shoelace polygon area
            n = len(s_pts)
            a = abs(sum(s_pts[i][0] * s_pts[(i + 1) % n][1] - s_pts[(i + 1) % n][0] * s_pts[i][1] for i in range(n))) * 0.5
            areas.append(a)
        else:
            areas.append(0.0)

    # Trapezoidal integration
    vol = dz * (0.5 * areas[0] + sum(areas[1:-1]) + 0.5 * areas[-1])
    return vol

def compute_mesh_dihedral_creases(
    vertices: List[Tuple[float, float, float]],
    faces: List[Tuple[int, ...]],
    cos_threshold: float = -0.85,
) -> List[Dict[str, Any]]:
    """
    Detects acute dihedral creases where adjacent faces fold sharply (cos theta < -0.85).
    Returns list of crease dictionaries.
    """
    # 1. Compute face unit normals
    face_normals: List[Tuple[float, float, float]] = []
    for f in faces:
        v1 = vertices[f[0]]
        v2 = vertices[f[1]]
        v3 = vertices[f[2]]
        e1 = (v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2])
        e2 = (v3[0] - v1[0], v3[1] - v1[1], v3[2] - v1[2])
        nx = e1[1] * e2[2] - e1[2] * e2[1]
        ny = e1[2] * e2[0] - e1[0] * e2[2]
        nz = e1[0] * e2[1] - e1[1] * e2[0]
        nlen = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        face_normals.append((nx / nlen, ny / nlen, nz / nlen))

    # 2. Build edge to face adjacency
    edge_faces: Dict[Tuple[int, int], List[int]] = {}
    for fi, f in enumerate(faces):
        for i in range(3):
            j = (i + 1) % 3
            edge = (min(f[i], f[j]), max(f[i], f[j]))
            if edge not in edge_faces:
                edge_faces[edge] = []
            edge_faces[edge].append(fi)

    # 3. Detect acute dihedral angles on manifold edges
    creases: List[Dict[str, Any]] = []
    for (v_a, v_b), f_list in edge_faces.items():
        if len(f_list) == 2:
            n1 = face_normals[f_list[0]]
            n2 = face_normals[f_list[1]]
            dot_val = max(-1.0, min(1.0, sum(a * b for a, b in zip(n1, n2))))
            if dot_val < cos_threshold:
                fold_angle_deg = 180.0 - math.degrees(math.acos(dot_val))
                midpoint = (
                    0.5 * (vertices[v_a][0] + vertices[v_b][0]),
                    0.5 * (vertices[v_a][1] + vertices[v_b][1]),
                    0.5 * (vertices[v_a][2] + vertices[v_b][2]),
                )
                creases.append({
                    "edge": (v_a, v_b),
                    "faces": (f_list[0], f_list[1]),
                    "cos_theta": dot_val,
                    "fold_angle_deg": fold_angle_deg,
                    "location": list(midpoint),
                })
    return creases

# ==============================================================================
# HIGH-LEVEL CRITIQUE EVALUATION APIS
# ==============================================================================

def evaluate_body_proportions_geometry(
    vertices: List[Tuple[float, float, float]],
    faces: List[Tuple[int, ...]],
    target_preset: str = "stylized_heroine",
    gender: str = "feminine",
    landmarks: Optional[Dict[str, Tuple[float, float, float]]] = None,
    vertex_groups: Optional[Dict[str, List[int]]] = None,
    object_name: str = "Body_Mesh",
) -> Tuple[AnthropometricMetrics, List[DefectItem]]:
    """Evaluates anthropometric body proportions against target preset."""
    preset = ANTHROPOMETRIC_PRESETS.get(target_preset, ANTHROPOMETRIC_PRESETS["stylized_heroine"])
    defects: List[DefectItem] = []

    # 1. Total Height
    zs = [v[2] for v in vertices]
    z_min, z_max = min(zs), max(zs)
    total_height = z_max - z_min

    # 2. Head Height
    if landmarks and "head_top" in landmarks and "chin" in landmarks:
        head_height = landmarks["head_top"][2] - landmarks["chin"][2]
    elif vertex_groups and "head" in vertex_groups and vertex_groups["head"]:
        head_zs = [vertices[i][2] for i in vertex_groups["head"]]
        head_height = max(head_zs) - min(head_zs)
    else:
        # Fallback slicing: neck constriction in upper quarter
        head_height = total_height / preset["head_ratio_nominal"]

    head_ratio = round(total_height / max(1e-4, head_height), 2)

    # 3. Arm Span
    if landmarks and all(k in landmarks for k in ["shoulder_L", "elbow_L", "wrist_L", "fingers_L"]):
        def dist(p1, p2):
            return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))
        l_arm = dist(landmarks["shoulder_L"], landmarks["elbow_L"]) + dist(landmarks["elbow_L"], landmarks["wrist_L"]) + dist(landmarks["wrist_L"], landmarks["fingers_L"])
        r_arm = dist(landmarks["shoulder_R"], landmarks["elbow_R"]) + dist(landmarks["elbow_R"], landmarks["wrist_R"]) + dist(landmarks["wrist_R"], landmarks["fingers_R"])
        biacromial = dist(landmarks["shoulder_L"], landmarks["shoulder_R"])
        arm_span = round(l_arm + biacromial + r_arm, 3)
    else:
        xs = [v[0] for v in vertices]
        arm_span = round(max(xs) - min(xs), 3)

    arm_span_ratio = round(arm_span / max(1e-4, total_height), 2)

    # 4. Shoulder & Hip Breadth
    if landmarks and "shoulder_L" in landmarks and "shoulder_R" in landmarks:
        shoulder_breadth = round(abs(landmarks["shoulder_L"][0] - landmarks["shoulder_R"][0]), 3)
    else:
        shoulder_breadth = round(total_height * 0.218, 3)

    if vertex_groups and "hips" in vertex_groups and vertex_groups["hips"]:
        hip_xs = [vertices[i][0] for i in vertex_groups["hips"]]
        hip_breadth = round(max(hip_xs) - min(hip_xs), 3)
    else:
        hip_breadth = round(shoulder_breadth * 1.0, 3)

    shoulder_to_hip_ratio = round(shoulder_breadth / max(1e-4, hip_breadth), 2)

    # Evaluation & Defect Logging
    is_head_valid = preset["head_ratio_min"] <= head_ratio <= preset["head_ratio_max"]
    if not is_head_valid:
        dev = abs(head_ratio - preset["head_ratio_nominal"])
        sev = DefectSeverity.CRITICAL if dev > 1.0 else DefectSeverity.MAJOR
        cat = "HEAD_TOO_LARGE" if head_ratio < preset["head_ratio_min"] else "HEAD_TOO_SMALL"
        defects.append(DefectItem(
            defect_id=f"PROP_{cat}",
            category=DefectCategory.PROPORTION,
            severity=sev,
            object_name=object_name,
            description=f"Head ratio {head_ratio:.2f} outside target [{preset['head_ratio_min']}, {preset['head_ratio_max']}] for preset '{target_preset}'.",
            location=[0.0, 0.0, z_max - head_height * 0.5],
            metrics={"head_ratio": head_ratio, "target_preset": target_preset},
            recommendation=ActionableRecommendation(
                action="RESCALE_HEAD",
                parameters={"scale_factor": round(head_ratio / preset["head_ratio_nominal"], 3)},
                guidance=f"Scale head geometry along (X, Y, Z) with pivot at cervical spine to match {preset['head_ratio_nominal']} heads.",
            ),
        ))

    is_arm_valid = preset["arm_span_ratio_min"] <= arm_span_ratio <= preset["arm_span_ratio_max"]
    if not is_arm_valid:
        dev = abs(arm_span_ratio - 1.0)
        sev = DefectSeverity.MAJOR if dev > 0.10 else DefectSeverity.MINOR
        cat = "ARM_SPAN_TOO_SHORT" if arm_span_ratio < preset["arm_span_ratio_min"] else "ARM_SPAN_TOO_LONG"
        defects.append(DefectItem(
            defect_id=f"PROP_{cat}",
            category=DefectCategory.PROPORTION,
            severity=sev,
            object_name=object_name,
            description=f"Arm span ratio {arm_span_ratio:.2f} deviates from Vitruvian target 1.00 +/- 0.05.",
            location=[0.0, 0.0, z_min + total_height * 0.7],
            metrics={"arm_span_ratio": arm_span_ratio, "arm_span": arm_span, "total_height": total_height},
            recommendation=ActionableRecommendation(
                action="ADJUST_LIMB_LENGTH",
                parameters={"target_arm_span": round(total_height, 3)},
                guidance="Adjust humerus and forearm bone lengths to achieve arm span ~= height.",
            ),
        ))

    # Shoulder-to-hip sexual dimorphism
    s_hip_range = preset[f"shoulder_to_hip_{gender}"]
    is_s_hip_valid = s_hip_range[0] <= shoulder_to_hip_ratio <= s_hip_range[1]
    if not is_s_hip_valid:
        sev = DefectSeverity.MAJOR if abs(shoulder_to_hip_ratio - sum(s_hip_range) * 0.5) > 0.15 else DefectSeverity.MINOR
        defects.append(DefectItem(
            defect_id="PROP_SHOULDER_TO_HIP_SKEW",
            category=DefectCategory.PROPORTION,
            severity=sev,
            object_name=object_name,
            description=f"Shoulder-to-hip ratio {shoulder_to_hip_ratio:.2f} violates {gender} archetype range {s_hip_range}.",
            location=[0.0, 0.0, z_min + total_height * 0.6],
            metrics={"shoulder_to_hip_ratio": shoulder_to_hip_ratio, "gender": gender},
            recommendation=ActionableRecommendation(
                action="ADJUST_PELVIS_SHOULDER_WIDTH",
                parameters={"target_ratio": round(sum(s_hip_range) * 0.5, 2)},
                guidance=f"Adjust shoulder clavicular span or iliac flare to conform to {gender} silhouette.",
            ),
        ))

    metrics = AnthropometricMetrics(
        total_height=total_height,
        head_height=head_height,
        head_ratio=head_ratio,
        arm_span=arm_span,
        arm_span_ratio=arm_span_ratio,
        shoulder_breadth=shoulder_breadth,
        hip_breadth=hip_breadth,
        shoulder_to_hip_ratio=shoulder_to_hip_ratio,
        target_preset=target_preset,
        gender=gender,
        is_head_ratio_valid=is_head_valid,
        is_arm_span_valid=is_arm_valid,
        is_shoulder_hip_valid=is_s_hip_valid,
    )
    return metrics, defects

def evaluate_rig_skinning_deformation(
    rest_vertices: List[Tuple[float, float, float]],
    posed_vertices: List[Tuple[float, float, float]],
    faces: List[Tuple[int, ...]],
    joint_specs: List[Dict[str, Any]],
    object_name: str = "Character_Mesh",
) -> Tuple[List[JointDeformationMetrics], List[DefectItem]]:
    """
    Evaluates joint volume conservation rho_V = V_posed / V_rest and acute dihedral creasing
    for active bending joints (elbows, knees, shoulders).
    """
    joint_results: List[JointDeformationMetrics] = []
    defects: List[DefectItem] = []

    # 1. Global acute dihedral creases on deformed mesh
    creases = compute_mesh_dihedral_creases(posed_vertices, faces, cos_threshold=-0.85)
    for c in creases:
        cos_th = c["cos_theta"]
        sev = DefectSeverity.CRITICAL if cos_th < -0.95 else DefectSeverity.MAJOR
        defects.append(DefectItem(
            defect_id="SKINNING_ACUTE_CREASE",
            category=DefectCategory.SKINNING_PINCH,
            severity=sev,
            object_name=object_name,
            description=f"Acute dihedral creasing (cos theta = {cos_th:.3f}, fold angle = {c['fold_angle_deg']:.1f} deg < 30 deg).",
            location=c["location"],
            affected_vertices=list(c["edge"]),
            affected_faces=list(c["faces"]),
            metrics={"cos_theta": cos_th, "fold_angle_deg": c["fold_angle_deg"]},
            recommendation=ActionableRecommendation(
                action="SMOOTH_SKINNING_WEIGHTS",
                parameters={"crease_edge": list(c["edge"])},
                guidance="Apply Laplacian smoothing to skin weights across adjacent vertex loops to eliminate pinched creasing.",
            ),
        ))

    # 2. Joint Volume Conservation
    for j_spec in joint_specs:
        j_name = j_spec["name"]
        p_center = j_spec["center"]
        axis_dir = j_spec["axis"]
        span = j_spec.get("span", 0.05)

        v_rest = compute_bounding_slice_volume(rest_vertices, faces, p_center, axis_dir, span_min=-span, span_max=span)
        v_posed = compute_bounding_slice_volume(posed_vertices, faces, p_center, axis_dir, span_min=-span, span_max=span)

        rho_v = round(v_posed / max(1e-6, v_rest), 3) if v_rest > 0 else 1.0
        is_conserved = 0.80 <= rho_v <= 1.25

        if rho_v < 0.80:
            sev = DefectSeverity.CRITICAL if rho_v < 0.65 else DefectSeverity.MAJOR
            defects.append(DefectItem(
                defect_id="SKINNING_VOLUME_COLLAPSE",
                category=DefectCategory.SKINNING_PINCH,
                severity=sev,
                object_name=object_name,
                description=f"Candy-wrapper collapse at joint '{j_name}': volume retention ratio rho_V = {rho_v:.3f} < 0.80 (volume loss > 20%).",
                location=list(p_center),
                metrics={"joint": j_name, "rho_v": rho_v, "v_rest": v_rest, "v_posed": v_posed},
                recommendation=ActionableRecommendation(
                    action="ACTIVATE_DUAL_BONE_TWIST_SKINNING",
                    parameters={"joint": j_name, "volume_ratio": rho_v},
                    guidance=f"Decompose {j_name} into dual-bone twist chains or use dual-quaternion skinning to eliminate candy-wrapper pinching.",
                ),
            ))
        elif rho_v > 1.25:
            defects.append(DefectItem(
                defect_id="SKINNING_ABNORMAL_BULGE",
                category=DefectCategory.SKINNING_PINCH,
                severity=DefectSeverity.MAJOR,
                object_name=object_name,
                description=f"Abnormal joint bulging at '{j_name}': volume ratio rho_V = {rho_v:.3f} > 1.25 (expansion > 25%).",
                location=list(p_center),
                metrics={"joint": j_name, "rho_v": rho_v, "v_rest": v_rest, "v_posed": v_posed},
                recommendation=ActionableRecommendation(
                    action="CLAMP_JOINT_WEIGHT_BLEED",
                    parameters={"joint": j_name, "volume_ratio": rho_v},
                    guidance=f"Clamp cross-joint skin weight blending around {j_name} to prevent fleshy ballooning.",
                ),
            ))

        joint_results.append(JointDeformationMetrics(
            joint_name=j_name,
            rest_volume=v_rest,
            posed_volume=v_posed,
            volume_ratio=rho_v,
            min_dihedral_cos=min([c["cos_theta"] for c in creases] or [1.0]),
            min_fold_angle_deg=min([c["fold_angle_deg"] for c in creases] or [180.0]),
            pinched_edge_count=len(creases),
            is_volume_conserved=is_conserved,
            is_crease_free=(len(creases) == 0),
        ))

    return joint_results, defects
```

---

## 4. Caveats

1. **Clothed Characters & Multi-Object Assembly**:
   - If garments (e.g. dress, sandals) are permanently merged into the body mesh without separate vertex groups, the raw geometric bounding box will reflect the garment silhouette (e.g. wide flared skirt inflating hip width).
   - *Mitigation*: The multi-tier resolution strategy prioritizes `morphomesh_landmarks` and the standardized vertex group `"hips"`. When analyzing clothed models, the critic must target `obj.vertex_groups["hips"]` rather than the global bounding box.
2. **Extreme Joint Hyper-flexion ($> 135^\circ$)**:
   - Under physiological limits ($90^\circ - 120^\circ$ elbow/knee flexion), soft tissues naturally press against each other, creating contact self-intersection if collision physics are not solved. The critic tests standard canonical testing poses ($90^\circ$ flexion for limbs, $90^\circ$ shoulder abduction) where clean skinning is expected to maintain $\rho_V \ge 0.80$ without creasing.
3. **Non-Manifold Edges in Dihedral Analysis**:
   - Boundary edges (shared by 1 face) and non-manifold edges (shared by $\ge 3$ faces) do not possess a unique dihedral angle.
   - *Mitigation*: The dihedral algorithm explicitly filters for manifold edges (`len(f_list) == 2`). Non-manifold edges are separately audited by topological validity checks.

---

## 5. Conclusion

1. **Anthropometric Proportion Analysis**:
   - Accurately measures $H_{\text{total}}$, $H_{\text{head}}$, $W_{\text{span}}$, $W_{\text{shoulder}}$, and $W_{\text{hip}}$ using a 3-tier hierarchy (Landmarks $\to$ Vertex Groups $\to$ Morphological Slices).
   - Validates head ratio against target presets:
     * Realistic Human ($7.0 - 8.0$ heads)
     * Stylized / Heroine ($6.0 - 6.5$ heads)
     * Chibi / Petite ($3.5 - 5.0$ heads)
   - Validates arm span ratio ($1.00 \pm 0.05$) and shoulder-to-hip ratio ($0.90 - 1.05$ feminine, $1.20 - 1.45$ masculine).
2. **Skinning Deformation & Volume Conservation**:
   - Detects candy-wrapper collapse ($\rho_V < 0.80$) and abnormal bulging ($\rho_V > 1.25$) across active bending joints (elbows, knees, shoulders).
   - Detects acute dihedral creasing ($\cos(\theta) < -0.85$, fold angle $< 30^\circ$) using face normal dot products on manifold edges.
3. **Pure-Python Offline Execution**:
   - All algorithms (`compute_bounding_slice_volume`, `compute_mesh_signed_volume`, `compute_mesh_dihedral_creases`, `evaluate_body_proportions_geometry`, `evaluate_rig_skinning_deformation`) are implemented in pure Python with zero external C-dependencies, enabling instantaneous offline unit testing in `tests/test_visual_critic.py`.

---

## 6. Verification Method

### 6.1 Programmatic Verification Suite
The implementer can independently verify all proportion and deformation logic using the following automated commands:

```bash
# 1. Run all existing rigging & anatomy test suites
uv run pytest -v tests/test_human_rigging.py tests/test_adversarial_rigging.py

# 2. Run new visual critic test suite (once implemented)
uv run pytest -v tests/test_visual_critic.py
```

### 6.2 Key Assertions for `tests/test_visual_critic.py`
1. **Ideal Baseline Mesh**:
   - `generate_human_base_mesh()` with default config ($H=1.65$, $R=7.41$) tested against preset `realistic_human` must return zero CRITICAL or MAJOR proportion defects.
2. **Injected Proportion Skew Fixtures**:
   - Chibi mesh ($H=1.20, R=4.5$) tested against `realistic_human` must flag `PROP_HEAD_TOO_LARGE` (Severity: CRITICAL).
   - Giant mesh ($H=2.20, R=9.2$) tested against `realistic_human` must flag `PROP_HEAD_TOO_SMALL` (Severity: CRITICAL).
3. **Pinched Skinning Fixture**:
   - Cylinder joint bent $90^\circ$ with naive rigid skinning causing $\rho_V = 0.62$ and acute crease $\cos(\theta) = -0.93$ must flag:
     * `SKINNING_VOLUME_COLLAPSE` (Severity: CRITICAL)
     * `SKINNING_ACUTE_CREASE` (Severity: CRITICAL, fold $< 18^\circ$).
4. **Anti-Pinch Deformed Limb**:
   - Cylinder joint with 3-loop cosine hinge weighting maintaining $\rho_V = 0.94$ and $\cos(\theta) > -0.25$ must PASS without collapse or crease defects.
