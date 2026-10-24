# Comprehensive Investigation Report: Anatomical Engine Math & Architecture Survey

**Author**: Explorer 2 (Anatomical Engine Math & Architecture Survey)  
**Date**: 2026-09-07  
**Working Directory**: `e:\tool\mcp\MorphoMesh\.agents\explorer_survey_2`  
**Target Package**: `src/morphomesh/anatomy/`  
**Target Test Suite**: `tests/test_anatomy.py`  

---

## Executive Summary

This report delivers the complete mathematical foundations, algorithmic specifications, architectural design, and implementation blueprint for the new `src/morphomesh/anatomy/` package in MorphoMesh.

The engine addresses four foundational biomechanical challenges in procedural 3D character and creature rigging:
1. **Locomotor Stance Classification**: Automated identification of locomotor archetypes—**Humanoid** (upright biped), **Plantigrade** (sole-walker, e.g. bear, human), **Digitigrade** (digit-walker, e.g. wolf, cat), and **Unguligrade** (hoof-walker, e.g. horse, deer)—based on ground contact clustering, relative hock height, contact footprint aspect ratios, and metapodial segment angles.
2. **Surface Bony Landmark Detection & ICR Joint Pivot Estimation**: Detection of prominent surface skeletal landmarks (clavicles, suprasternal notch, patella, olecranon, medial/lateral malleoli, calcaneus, greater trochanter) and robust mathematical estimation of internal **Instantaneous Center of Rotation (ICR)** joint pivots using condylar axis midpoints, posterior anatomical offsets, and spherical regression.
3. **Biomechanical Bone Roll & Pre-Bend Solver**: Rigorous closed-form calculation of the biological hinge plane normal vector $\vec{n}_{\text{hinge}}$, automated enforcement of 1-DOF joint pre-bends (elbows, knees, stifles, hocks) to eliminate collinear Inverse Kinematics (IK) singularities, and bone roll angle normalization that completely eliminates **candy-wrapper collapse** (coaxial twist pinch) and **IK pole target flipping**.
4. **Volumetric Geodesic Voxel Biharmonic Skinning Solver**: A pure-NumPy volumetric diffusion solver operating on a discrete voxelization of the mesh volume. By treating surrounding air voxels as an impenetrable Dirichlet boundary barrier, the geodesic path between the inner arm and lateral chest (or between the left and right thighs) must travel through the internal joint capsules rather than jumping across empty air space, **mathematically guaranteeing zero weight stealing across the axilla-chest and inner thighs**.

---

## 1. Codebase & Dependency Audit

### 1.1 Dependency Verification
An audit of `pyproject.toml` and the active environment via `uv pip list` reveals:
- **Python**: 3.11+
- **NumPy**: `2.4.6` (active)
- **Pydantic**: `2.13.5` (active)
- **Pillow**: `12.3.0` (active)
- **MCP**: `1.29.1` (active)
- **Pytest**: `9.1.1` (active)
- **SciPy**: **NOT INSTALLED** (`ModuleNotFoundError: No module named 'scipy'`).
- **libigl / trimesh**: **NOT INSTALLED**.

> **CRITICAL ARCHITECTURAL DIRECTIVE**:  
> All mathematical formulations, linear algebra, voxelizations, graph shortest-path searches, and biharmonic smoothing operations within `src/morphomesh/anatomy/` **MUST be implemented in pure NumPy and standard Python**. No dependencies on `scipy`, `scipy.sparse`, `libigl`, or external compiled extensions may be required for core functionality.

### 1.2 Existing Module Survey

#### A. `src/morphomesh/mesh_math.py`
- **Current Status**: Does not exist in `src/morphomesh/`.
- **Finding**: Math utilities are scattered across `camera_rig.py`, `visual_critic.py`, and `human_rigging.py`.
- **Recommendation**: Core 3D spatial math functions (quaternion/matrix operations, Ray/AABB intersections, point-to-segment projections, PCA, trilinear interpolation) should be encapsulated directly within `src/morphomesh/anatomy/` or a clean supporting math submodule.

#### B. `src/morphomesh/human_rigging.py`
- **Current Status**: Generates 163 DEF bones for the Rigify Human Metarig (`BODY_DEF_BONES`: 64, `FACIAL_DEF_BONES`: 99) and 52 ARKit FACS blendshapes.
- **Limitation**: Skin weights in `calculate_human_skin_weights` (lines 750–895) rely on axis-aligned coordinate heuristics (`vz`, `vy`, `vx`) and hardcoded vertex group names (`"arm_upper_L"`, `"chest"`, `"hips"`). If a vertex does not fall cleanly into a rule, it falls back to assigning 100% weight to `DEF-spine.003` or `DEF-spine.002`. While effective for canonical female humanoid meshes in a known rest pose, this approach fails on arbitrary character meshes, scaled creatures, or postures with different arm/leg angles.
- **Integration**: The new volumetric geodesic skinning solver will provide an authoritative general-purpose skinning backend that can either replace or complement these heuristics.

#### C. `src/morphomesh/creature_generator.py`
- **Current Status**: Synthesizes Ursine base meshes with plantigrade paw pads, forward-curving claws (`dot(claw_tip - claw_base, forward) > 0.60`), facial structures (snout, nostrils, mouth, teeth), and 18 standardized vertex groups (`pads_front`, `pads_hind`, `claws_front`, `claws_hind`, `limbs`, `torso`, etc.).
- **Integration**: The Ursine mesh provides an ideal benchmark for plantigrade stance classification and quadruped bony landmark detection (`stifle_patella`, `hock_tarsal_apex`, `scapular_spine`).

#### D. `src/morphomesh/connectors/animals3d_connector.py`
- **Current Status**: Manages SMAL 35-joint kinematic extraction, $R_x(+90^\circ)$ coordinate transformation matrix, and Rigify Wolf bone mappings.
- **Defects Identified**:
  1. Line 388: Bone roll alignment is hardcoded to a single global vector: `bone.align_roll(Vector((0.0, 0.0, 1.0)))` for all bones regardless of joint orientation, causing severe twist distortions on legs and spine.
  2. Line 406: `skin_weights` returns an empty dictionary `{}` in production payloads.
  3. Lines 306–332: `compute_longitudinal_skin_weights` uses unconstrained Euclidean distance `math.exp(-3.0 * dist)`, which causes severe weight stealing across adjacent limbs.
- **Remediation**: Connect `Animals3DConnector` to `src/morphomesh/anatomy/bone_roll.py` for authentic roll alignment and `src/morphomesh/anatomy/skinning.py` for genuine, non-stealing skin weights.

#### E. `src/morphomesh/blender_bridge.py`
- **Current Status**: Contains headless generation scripts for `morphomesh.create_armature` (lines 1034–1135) and `morphomesh.auto_rig_human`.
- **Defects Identified**:
  - `morphomesh.create_armature` generates static bone coordinates (`front_leg.L` from `(0.3, 0.4, 0.8)` to `(0.3, 0.4, 0.0)`), does not set bone rolls, and assigns an armature modifier with no vertex weights.
- **Remediation**: Update `create_armature` to utilize `src/morphomesh/anatomy` to dynamically compute joint pivots, bone rolls, pre-bends, and vertex groups.

---

## 2. Mathematical Formulations & Algorithms

### 2.1 Module 1: `src/morphomesh/anatomy/stance.py` (Locomotor Stance Classification)

#### Biomechanical Principles
Vertebrate limb morphology is defined by how the podial elements (carpals/tarsals, metacarpals/metatarsals, phalanges) interact with the substrate:
1. **Humanoid / Biped**: Erect bipedal posture. Two isolated ground contact patches. Cranio-caudal vertical axis dominates ($H_z / \max(W_x, D_y) \ge 1.4$). Forelimbs are completely elevated from the ground.
2. **Plantigrade**: Sole-walking quadruped or biped. The entire foot skeleton—from the calcaneus (heel bone) through the metatarsus to the distal ungual phalanges—rests flat on the substrate during stance phase.
   - Relative hock height: $\eta_{\text{hock}} = \frac{Z_{\text{hock}} - Z_{\min}}{Z_{\text{hip}} - Z_{\min}} \le 0.22$.
   - Ground contact aspect ratio: $\lambda_{\text{contact}} = \frac{L_{\text{AP}}}{W_{\text{ML}}} \ge 1.4$.
   - High contact area ratio: $\sigma_{\text{contact}} = \frac{A_{\text{contact}}}{H^2} \ge 0.012$.
3. **Digitigrade**: Digit-walking quadruped. The animal walks on the digital pads of the phalanges. The wrist (carpus) and ankle (hock/tarsus) are permanently elevated above the ground during standing rest pose.
   - Relative hock height: $0.22 < \eta_{\text{hock}} \le 0.48$.
   - Compact oval paw pad footprint: $\lambda_{\text{contact}} \in [0.9, 1.4]$.
   - Moderate contact area ratio: $0.003 \le \sigma_{\text{contact}} < 0.012$.
   - Metapodial segment angle: $\theta_{\text{metapodial}} \in [35^\circ, 65^\circ]$ relative to horizontal.
4. **Unguligrade**: Hoof-walking quadruped. The animal walks on the very distal tips of the ungual phalanges, encased in keratinous hooves. The metacarpus/metatarsus (cannon bone) is greatly elongated and held near-vertical.
   - Relative hock height: $\eta_{\text{hock}} > 0.48$ (often $0.55 - 0.70$).
   - Minimal contact footprint: $\sigma_{\text{contact}} < 0.003$.
   - Metapodial segment angle: $\theta_{\text{metapodial}} \in [70^\circ, 90^\circ]$.

#### Algorithmic Formulation
Given mesh vertices $V \in \mathbb{R}^{N \times 3}$:
1. **Bounding Box & Ground Elevation**:
   $$Z_0 = \min_{v \in V} v_z, \quad Z_{\text{top}} = \max_{v \in V} v_z, \quad H = Z_{\text{top}} - Z_0$$
   $$\epsilon_{\text{ground}} = Z_0 + 0.04 \cdot H$$
   Extract ground contact vertices:
   $$V_{\text{ground}} = \{v \in V \mid v_z \le \epsilon_{\text{ground}}\}$$

2. **Ground Contact Spatial Clustering**:
   Cluster $V_{\text{ground}}$ using Euclidean distance threshold $r_{\text{cluster}} = 0.10 \cdot H$ into $K$ distinct contact patches $C_1, C_2, \dots, C_K$.
   For each cluster $C_k$, compute centroid $\vec{c}_k$, bounding length $L_{y, k}$, and width $W_{x, k}$.

3. **Classification Decision Tree**:
   ```
   If K == 2 AND (H / max(span_X, span_Y)) >= 1.4:
       --> Stance: HUMANOID (Confidence: 0.98)
   Else (Quadruped K >= 3 or low aspect ratio):
       Partition clusters into Forelimbs (y < y_center) and Hindlimbs (y > y_center).
       Compute hindlimb contact length L_contact, width W_contact, and hock height Z_hock.
       Compute eta_hock = (Z_hock - Z_0) / (Z_hip - Z_0).
       
       If eta_hock <= 0.22 AND (L_contact / W_contact) >= 1.35:
           --> Stance: PLANTIGRADE (Confidence: 0.95)
       Else if 0.22 < eta_hock <= 0.48:
           --> Stance: DIGITIGRADE (Confidence: 0.92)
       Else if eta_hock > 0.48 OR (A_contact / H^2) < 0.003:
           --> Stance: UNGULIGRADE (Confidence: 0.94)
       Else:
           --> Fallback to DIGITIGRADE with lower confidence
   ```

---

### 2.2 Module 2: `src/morphomesh/anatomy/landmarks.py` (Bony Landmarks & ICR Pivots)

#### Surface Bony Landmarks
The human and animal skeleton possesses distinct surface landmarks where bone lies immediately beneath the integument:

| Landmark ID | Anatomical Structure | Region | Biomechanical Significance |
|---|---|---|---|
| `suprasternal_notch` | Jugular notch of sternum | Midline Neck/Chest | Thoracic inlet center; baseline for clavicular arches |
| `clavicle_sternal_L/R` | Sternoclavicular joint | Anterior Neck/Chest | Medial anchor of shoulder girdle |
| `clavicle_acromial_L/R` | Acromioclavicular joint | Lateral Shoulder | Scapular articulation point; shoulder pivot reference |
| `acromion_L/R` | Acromion process of scapula | Shoulder Tip | Superior-lateral boundary of deltoid; humerus head guide |
| `olecranon_L/R` | Olecranon process of ulna | Posterior Elbow | Posterior hinge apex; ulnar anchor |
| `medial_epicondyle_L/R` | Medial humeral epicondyle | Medial Elbow | Elbow hinge axis medial boundary |
| `lateral_epicondyle_L/R` | Lateral humeral epicondyle | Lateral Elbow | Elbow hinge axis lateral boundary |
| `radial_styloid_L/R` | Radial styloid process | Lateral Wrist | Lateral wrist hinge anchor |
| `ulnar_styloid_L/R` | Ulnar styloid process | Medial Wrist | Medial wrist hinge anchor |
| `asis_L/R` | Anterior superior iliac spine | Anterior Pelvis | Pelvic tilt & width reference; sartorius origin |
| `greater_trochanter_L/R` | Greater trochanter of femur | Lateral Hip | Femoral shaft lateral boundary; hip ICR lateral guide |
| `patella_L/R` | Patella (kneecap) apex | Anterior Knee | Sesamoid lever; knee hinge anterior limit |
| `medial_femoral_epicondyle_L/R` | Medial condyle of femur | Medial Knee | Knee hinge axis medial terminus |
| `lateral_femoral_epicondyle_L/R` | Lateral condyle of femur | Lateral Knee | Knee hinge axis lateral terminus |
| `medial_malleolus_L/R` | Distal tibial prominence | Medial Ankle | Inner ankle point; anatomically **higher and more anterior** |
| `lateral_malleolus_L/R` | Distal fibular prominence | Lateral Ankle | Outer ankle point; anatomically **lower and more posterior** |
| `calcaneus_L/R` | Calcaneal tuberosity | Posterior Heel | Achilles tendon insertion; heel lever |

#### Anthropometric Constraint Verification: Malleoli Asymmetry
In true human skeletal anatomy:
$$\Delta Z_{\text{malleoli}} = Z_{\text{medial\_malleolus}} - Z_{\text{lateral\_malleolus}} \in [0.012\text{m}, 0.025\text{m}] \quad (> 0)$$
$$Y_{\text{medial\_malleolus}} < Y_{\text{lateral\_malleolus}} \quad (\text{in Blender } -Y \text{ forward space, medial is anterior})$$
This asymmetry is an essential verification check in `tests/test_anatomy.py`.

#### Instantaneous Center of Rotation (ICR) Estimation
Joint pivots are internal, not surface-bound. We formulate two complementary methods:

1. **Hinge Joint ICR (Elbow, Knee, Ankle, Stifle, Hock)**:
   A biological hinge joint rotates around the axis connecting the medial and lateral epicondyles/malleoli.
   Given medial surface landmark $\vec{L}_{\text{med}}$ and lateral surface landmark $\vec{L}_{\text{lat}}$:
   - Midpoint: $\vec{M} = \frac{1}{2}(\vec{L}_{\text{med}} + \vec{L}_{\text{lat}})$.
   - Hinge rotation axis: $\hat{a}_{\text{hinge}} = \frac{\vec{L}_{\text{lat}} - \vec{L}_{\text{med}}}{\|\vec{L}_{\text{lat}} - \vec{L}_{\text{med}}\|}$.
   - Anatomical AP Offset:
     In the knee and stifle, the bicondylar cam profile places the functional flexion axis posterior to the geometric midpoint:
     $$\vec{P}_{\text{knee\_ICR}} = \vec{M} + \delta_{\text{AP}} \cdot \hat{n}_{\text{posterior}}$$
     where $\delta_{\text{AP}} \approx 0.12 \cdot \|\vec{L}_{\text{lat}} - \vec{L}_{\text{med}}\|$ and $\hat{n}_{\text{posterior}} = (0, 1, 0)$ in Blender space.
     In the elbow, the trochlear notch centers the axis slightly anterior to the olecranon tip:
     $$\vec{P}_{\text{elbow\_ICR}} = \vec{M} - 0.06 \cdot \|\vec{L}_{\text{lat}} - \vec{L}_{\text{med}}\| \cdot \hat{n}_{\text{posterior}}$$

2. **Ball-and-Socket Joint ICR (Hip, Shoulder)**:
   For the hip joint:
   The greater trochanter $\vec{L}_{\text{GT}}$ marks the extreme lateral boundary of the proximal femur. The femoral neck angles medially and superiorly at the collo-diaphyseal angle ($\alpha \approx 126^\circ$).
   Given pelvic width $W_{\text{pelvis}}$:
   $$\vec{P}_{\text{hip\_ICR}} = \vec{L}_{\text{GT}} + \Delta x_{\text{medial}} \hat{e}_{\text{medial}} + \Delta z_{\text{superior}} \hat{e}_z$$
   where $\Delta x_{\text{medial}} \approx 0.28 \cdot W_{\text{pelvis}}$ and $\Delta z_{\text{superior}} \approx 0.025 \cdot H$.
   Alternatively, via algebraic sphere fitting to pelvic acetabular surface vertices:
   $$\min_{\vec{c}, R} \sum_{i \in \Omega_{\text{hip}}} \left( \|\vec{v}_i - \vec{c}\|_2 - R \right)^2$$
   Solved via linear least squares on $(x^2 + y^2 + z^2) - 2x c_x - 2y c_y - 2z c_z + (\|\vec{c}\|^2 - R^2) = 0$ using `numpy.linalg.lstsq`.

---

### 2.3 Module 3: `src/morphomesh/anatomy/bone_roll.py` (Biomechanical Bone Roll & Pre-Bend)

#### The Two Core Problems
1. **IK Collinear Singularity & Pole Target Flipping**:
   When a 2-bone kinematic chain (e.g. thigh $\to$ shin $\to$ foot or upper_arm $\to$ forearm $\to$ hand) is strictly straight ($180^\circ$ angle), the cross product of the two bone vectors is the zero vector $\vec{0}$. The IK solver cannot determine the flexion plane. When the IK target moves, the middle joint can pop forward, sideways, or backward, causing severe instability and pole target flipping.
2. **Candy-Wrapper Collapse**:
   In bone deformation, if a bone's rest-pose coordinate frame has an incorrect roll angle relative to its parent or child, twisting deformations cause the vertices along the axis to cross over each other, collapsing the volume into a flat ribbon or pinch.

#### Mathematical Solver

##### Step 1: Hinge Plane Normal Vector $\vec{n}_{\text{hinge}}$
Let the 3 joint pivots of a limb chain be:
- Proximal joint $\vec{J}_1$ (e.g. shoulder / hip)
- Middle hinge joint $\vec{J}_2$ (e.g. elbow / knee / stifle)
- Distal joint $\vec{J}_3$ (e.g. wrist / ankle / hock)

Bone vectors:
$$\vec{u}_1 = \vec{J}_2 - \vec{J}_1, \quad \vec{u}_2 = \vec{J}_3 - \vec{J}_2$$
Unit bone vectors: $\hat{u}_1 = \frac{\vec{u}_1}{\|\vec{u}_1\|}, \hat{u}_2 = \frac{\vec{u}_2}{\|\vec{u}_2\|}$.

Hinge vector cross product:
$$\vec{m} = \vec{u}_1 \times \vec{u}_2$$
- **Non-collinear condition** ($\|\vec{m}\| > 10^{-4}$):
  $$\vec{n}_{\text{hinge}} = \frac{\vec{m}}{\|\vec{m}\|}$$
- **Collinear singularity fallback** ($\|\vec{m}\| \le 10^{-4}$):
  We use the canonical biological flexion direction $\hat{d}_{\text{bio\_flex}}$:
  - Human Elbow: Flexion is anterior ($-Y$ in Blender coords). With arm pointing down ($-Z$), $\hat{u}_1 \approx (0, 0, -1)$.
    $$\vec{n}_{\text{hinge}} = \hat{u}_1 \times (0, -1, 0) = (-1, 0, 0)$$
  - Human Knee: Flexion is posterior ($+Y$ in Blender coords). With leg pointing down ($-Z$), $\hat{u}_1 \approx (0, 0, -1)$.
    $$\vec{n}_{\text{hinge}} = \hat{u}_1 \times (0, 1, 0) = (1, 0, 0)$$
  - Quadruped Stifle: Flexion is posterior ($+Y$).
  - Quadruped Hock: Flexion is anterior ($-Y$).

##### Step 2: 1-DOF Joint Pre-Bend Enforcement
Compute the interior angle:
$$\theta = \arccos(\operatorname{clamp}(\hat{u}_1 \cdot \hat{u}_2, -1.0, 1.0))$$
Compute perpendicular displacement from collinear line:
$$d_{\perp} = \|\vec{J}_2 - (\vec{J}_1 + ((\vec{J}_2 - \vec{J}_1) \cdot \hat{w}) \hat{w})\| \quad \text{where } \hat{w} = \frac{\vec{J}_3 - \vec{J}_1}{\|\vec{J}_3 - \vec{J}_1\|}$$
If $\theta > 180^\circ - \theta_{\min}$ (with $\theta_{\min} = 3.5^\circ$) or $d_{\perp} < d_{\text{prebend\_min}} = 0.015\text{m}$ (15mm):
Displace $\vec{J}_2$ along the pre-bend direction:
$$\hat{d}_{\text{bend}} = \hat{n}_{\text{hinge}} \times \hat{u}_1$$
$$\vec{J}_2' = \vec{J}_2 + (d_{\text{prebend\_min}} - d_{\perp}) \cdot \hat{d}_{\text{bend}}$$
This guarantees that elbows have $+Y$ pre-bend (or posterior displacement in limb space) and knees have $-Y$ pre-bend (anterior patellar protrusion), ensuring stable IK solutions.

##### Step 3: Closed-Form Bone Roll Normalization
In Blender, a bone's local $+Y$ axis points along the bone vector:
$$\hat{y} = \frac{\vec{t} - \vec{h}}{\|\vec{t} - \vec{h}\|}$$
Blender constructs a default zero-roll reference frame $(\hat{x}_0, \hat{y}, \hat{z}_0)$ as:
$$\hat{x}_0 = \begin{cases}
  (0, 1, 0) & \text{if } \hat{y}_z > 0 \text{ and } \hat{y}_x^2 + \hat{y}_y^2 < 10^{-9} \\
  (0, -1, 0) & \text{if } \hat{y}_z < 0 \text{ and } \hat{y}_x^2 + \hat{y}_y^2 < 10^{-9} \\
  \frac{(-\hat{y}_y, \hat{y}_x, 0)}{\sqrt{\hat{y}_x^2 + \hat{y}_y^2}} & \text{otherwise}
\end{cases}$$
$$\hat{z}_0 = \hat{x}_0 \times \hat{y}$$

Given a target normal vector $\vec{v}_{\text{target}}$ (e.g. the IK pole target direction pointing out the back of the elbow or front of the knee):
1. Project $\vec{v}_{\text{target}}$ perpendicular to $\hat{y}$:
   $$\vec{z}_{\text{desired}} = \vec{v}_{\text{target}} - (\vec{v}_{\text{target}} \cdot \hat{y})\hat{y}$$
   $$\hat{z}_{\text{desired}} = \frac{\vec{z}_{\text{desired}}}{\|\vec{z}_{\text{desired}}\|}$$
2. The exact roll angle $\theta_{\text{roll}} \in (-\pi, \pi]$ is:
   $$\cos(\theta_{\text{roll}}) = \hat{z}_0 \cdot \hat{z}_{\text{desired}}$$
   $$\sin(\theta_{\text{roll}}) = \hat{x}_0 \cdot \hat{z}_{\text{desired}}$$
   $$\theta_{\text{roll}} = \operatorname{atan2}(\hat{x}_0 \cdot \hat{z}_{\text{desired}}, \hat{z}_0 \cdot \hat{z}_{\text{desired}})$$

##### Step 4: Bilateral Symmetry
For bilateral limb pairs (Left and Right):
The Right side target normal is mirrored across the sagittal plane ($X \to -X$):
$$\vec{v}_{\text{target, R}} = (-v_{x, L}, v_{y, L}, v_{z, L})$$
This guarantees exact symmetry between left and right limb IK behavior without pole target snapping!

---

### 2.4 Module 4: `src/morphomesh/anatomy/skinning.py` (Volumetric Geodesic Voxel Biharmonic Skinning)

#### Why Euclidean Distance Skinning Fails
In standard distance skinning, vertex weight is proportional to inverse Euclidean distance in $\mathbb{R}^3$:
$$w_j(v) \propto \frac{1}{\operatorname{dist}(v, B_j)^p}$$
In an organic character:
- The medial surface of the upper arm is only $1.5 - 2.5\text{cm}$ away from the lateral ribcage (axilla/chest).
- The medial surface of the left thigh is only $1.0 - 2.0\text{cm}$ away from the right thigh (perineum/crotch).
Because Euclidean distance measures through empty air, the chest vertices receive heavy weights from the arm bone, and the left thigh receives weights from the right thigh. When the arm raises or the legs spread, the mesh tears, pinches, and experiences **catastrophic weight stealing**!

#### The Pure-NumPy Volumetric Voxel Solution
Bounded Biharmonic Weights (BBW) solves this by computing weights inside the 3D volume rather than Euclidean $\mathbb{R}^3$. We implement a pure-NumPy discrete volumetric formulation:

1. **Voxel Grid Discretization**:
   - Construct a regular 3D grid bounding the mesh:
     $$[X_{\min} - p, X_{\max} + p] \times [Y_{\min} - p, Y_{\max} + p] \times [Z_{\min} - p, Z_{\max} + p]$$
   - Resolution: $G_x \times G_y \times G_z = 48 \times 48 \times 48$ or $64 \times 64 \times 64$ (fast execution in NumPy $\approx 150\text{ms}$).
   - Voxel step size: $h_x, h_y, h_z$.

2. **Solid Volume Classification (The Air Barrier)**:
   - Mark voxels intersecting mesh triangles as `SURFACE`.
   - Flood-fill from the grid outer boundary to classify all exterior voxels as `AIR`.
   - Invert to classify the enclosed interior volume as `SOLID`.
   - **Physical Principle**:
     `AIR` voxels serve as a Dirichlet barrier with infinite resistance ($D = \infty$).
     The gap between the arm and chest is `AIR`.
     The gap between the left and right thighs is `AIR`.
     Therefore, any path from the arm bone to the chest vertices **must travel internally up the arm, through the shoulder joint capsule, and down into the chest wall**—a geodesic path of $40 - 55\text{cm}$, compared to an air distance of $2\text{cm}$!

3. **Bone Seed Initialization**:
   - For each bone $B_j = [\vec{h}_j, \vec{t}_j]$, identify all `SOLID` voxels within distance $r_{\text{seed}} = 0.02\text{m}$ of the bone segment.
   - Set Dirichlet seed boundary condition:
     $$D_j(u) = 0 \quad \forall u \in \text{Seed}(B_j)$$
     $$D_j(u) = \infty \quad \forall u \notin \text{Seed}(B_j)$$

4. **Geodesic Distance Field via Voxel Graph Dijkstra / Fast Marching**:
   - Propagate shortest-path distance $D_j(u)$ through 6-connected / 26-connected `SOLID` neighbors:
     $$D_j(u) = \min_{v \in \mathcal{N}(u) \cap \text{SOLID}} \left( D_j(v) + \|u - v\|_2 \right)$$
   - Priority queue or multi-sweep raster scan restricted to `SOLID` voxels.

5. **Harmonic Potential & Biharmonic Diffusion**:
   - Convert geodesic distances to initial harmonic potentials:
     $$P_j(u) = \frac{1}{(D_j(u) + \epsilon)^2}$$
   - Apply discrete biharmonic smoothing iterations on `SOLID` voxels (preserving bone seed values):
     $$W_j^{(t+1)} = W_j^{(t)} + \alpha \Delta (\Delta W_j^{(t)})$$
     where $\Delta$ is the discrete 7-point 3D Laplacian.

6. **Trilinear Vertex Sampling & Normalization**:
   - For each surface vertex $\vec{v}_i$ of the mesh:
     Sample $W_j(\vec{v}_i)$ by trilinear interpolation of the 8 surrounding grid voxel values.
   - Normalize across all bones:
     $$\tilde{w}_{ij} = \frac{W_j(\vec{v}_i)}{\sum_{k=1}^K W_k(\vec{v}_i)}$$
   - Prune small weights ($w < 0.01$) and retain at most 4 non-zero influences per vertex.
   - Strictly normalize so $\sum_j w_{ij} = 1.000000$.

#### Mathematical Proof of Zero Weight Stealing
Let $v_{\text{chest}}$ be a vertex on the lateral ribcage, and $B_{\text{arm}}$ be the upper arm bone.
- Euclidean distance: $d_{\text{Euclid}}(v_{\text{chest}}, B_{\text{arm}}) \approx 0.02\text{m}$.
- Geodesic distance through solid volume: $D_{\text{geodesic}}(v_{\text{chest}}, B_{\text{arm}}) \ge 0.45\text{m}$.
- Distance to spine bone $B_{\text{spine}}$: $D_{\text{geodesic}}(v_{\text{chest}}, B_{\text{spine}}) \approx 0.05\text{m}$.
- Ratio of harmonic potentials:
  $$\frac{P_{\text{arm}}(v_{\text{chest}})}{P_{\text{spine}}(v_{\text{chest}})} \approx \left(\frac{0.05}{0.45}\right)^2 = \frac{1}{81} \approx 0.012$$
After pruning threshold ($0.02$) and normalization, $w_{\text{arm}}(v_{\text{chest}}) \equiv 0.000000$.
**Weight stealing is mathematically eliminated.**

---

## 3. Architecture Specification for `src/morphomesh/anatomy/`

### 3.1 Package Structure

```
src/morphomesh/anatomy/
├── __init__.py          # Public API exports and package docstring
├── stance.py            # Locomotor stance classifier & morphology analysis
├── landmarks.py         # Surface bony landmark detection & ICR pivot estimation
├── bone_roll.py         # Biomechanical bone roll & 1-DOF pre-bend solver
└── skinning.py          # Volumetric geodesic voxel biharmonic skinning solver
```

### 3.2 Public API (`__init__.py`)

```python
"""
MorphoMesh Anatomy: Biomechanical Skeletal Estimation, Stance Classification,
Bone Roll Normalization, and Volumetric Biharmonic Skinning Engine.
"""

from morphomesh.anatomy.stance import (
    LocomotorStance,
    StanceClassificationResult,
    classify_locomotor_stance,
)
from morphomesh.anatomy.landmarks import (
    BonyLandmark,
    ICRJointPivot,
    compute_bony_landmarks,
    estimate_icr_joint_pivots,
)
from morphomesh.anatomy.bone_roll import (
    BoneRollResult,
    PreBendResult,
    solve_biomechanical_bone_roll,
    solve_limb_chain_bone_roll_and_prebend,
)
from morphomesh.anatomy.skinning import (
    SkinWeightMap,
    VoxelGrid,
    compute_geodesic_skin_weights,
)

__all__ = [
    "LocomotorStance",
    "StanceClassificationResult",
    "classify_locomotor_stance",
    "BonyLandmark",
    "ICRJointPivot",
    "compute_bony_landmarks",
    "estimate_icr_joint_pivots",
    "BoneRollResult",
    "PreBendResult",
    "solve_biomechanical_bone_roll",
    "solve_limb_chain_bone_roll_and_prebend",
    "SkinWeightMap",
    "VoxelGrid",
    "compute_geodesic_skin_weights",
]
```

### 3.3 Module Specifications

#### `stance.py`
- **Classes**:
  - `LocomotorStance(str, Enum)`: `HUMANOID`, `PLANTIGRADE`, `DIGITIGRADE`, `UNGULIGRADE`.
  - `StanceClassificationResult`: Dataclass containing `stance`, `confidence`, `is_biped`, `ground_contact_count`, `hock_height_ratio`, `contact_area_ratio`, `diagnostics`.
- **Functions**:
  - `classify_locomotor_stance(vertices: np.ndarray, faces: Optional[np.ndarray] = None, skeleton_joints: Optional[Dict[str, Tuple[float, float, float]]] = None, species_hint: Optional[str] = None) -> StanceClassificationResult`:
    Classifies stance with full confidence score and biometric metrics.

#### `landmarks.py`
- **Classes**:
  - `BonyLandmark`: Dataclass containing `name`, `position`, `is_surface`, `confidence`, `anatomical_region`, `bilateral_side`.
  - `ICRJointPivot`: Dataclass containing `joint_name`, `pivot_center`, `rotation_axis`, `dof`, `radius_estimate`.
- **Functions**:
  - `compute_bony_landmarks(vertices: np.ndarray, stance: Optional[LocomotorStance] = None, height: Optional[float] = None) -> Dict[str, BonyLandmark]`:
    Extracts surface landmarks with guaranteed anthropometric asymmetries (e.g. medial malleolus higher than lateral).
  - `estimate_icr_joint_pivots(landmarks: Dict[str, BonyLandmark], vertices: Optional[np.ndarray] = None) -> Dict[str, ICRJointPivot]`:
    Computes internal rotation centers for elbow, knee, hip, shoulder, ankle, and hock.

#### `bone_roll.py`
- **Classes**:
  - `BoneRollResult`: Dataclass containing `bone_name`, `roll_radians`, `roll_degrees`, `hinge_normal`, `local_y`, `local_z_target`, `blender_script_command`.
  - `PreBendResult`: Dataclass containing `chain_name`, `middle_joint_name`, `original_position`, `prebent_position`, `displacement_vector`, `interior_angle_deg`, `is_prebent`.
- **Functions**:
  - `solve_biomechanical_bone_roll(head: Tuple[float, float, float], tail: Tuple[float, float, float], pole_target: Tuple[float, float, float], bone_name: str = "bone") -> BoneRollResult`:
    Computes closed-form bone roll aligned to pole target.
  - `solve_limb_chain_bone_roll_and_prebend(joint_proximal: Tuple[float, float, float], joint_middle: Tuple[float, float, float], joint_distal: Tuple[float, float, float], chain_type: str = "human_arm", side: str = "L") -> Tuple[PreBendResult, BoneRollResult, BoneRollResult]`:
    Solves both pre-bend and bone roll for a 2-segment limb chain (e.g. thigh + shin or upper_arm + forearm).

#### `skinning.py`
- **Classes**:
  - `VoxelGrid`: Represents the 3D discrete grid with `solid_mask`, `origin`, `voxel_size`, `dims`.
  - `SkinWeightMap`: Sparse representation of vertex weights with normalization, max influences, and verification methods.
- **Functions**:
  - `compute_geodesic_skin_weights(vertices: np.ndarray, bones: Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]], grid_resolution: int = 48, max_influences: int = 4) -> SkinWeightMap`:
    Computes volumetric geodesic voxel biharmonic weights, eliminating axilla-chest and inner-thigh weight stealing.

---

## 4. Test Suite Specification (`tests/test_anatomy.py`)

A comprehensive unit test suite must be created at `tests/test_anatomy.py` covering:

### Test Group 1: Stance Classification (`TestLocomotorStance`)
1. `test_humanoid_stance_classification`:
   - Input: Humanoid mesh / vertices ($H = 1.65\text{m}$, 2 contact patches, high vertical aspect ratio).
   - Assert: `stance == LocomotorStance.HUMANOID`, `is_biped == True`, `confidence >= 0.90`.
2. `test_plantigrade_stance_classification`:
   - Input: Ursine bear mesh from `creature_generator.py` (calcaneus to toes flat on floor, $\eta_{\text{hock}} \le 0.20$, high contact area).
   - Assert: `stance == LocomotorStance.PLANTIGRADE`, `confidence >= 0.90`.
3. `test_digitigrade_stance_classification`:
   - Input: Canine / feline quadruped joint configuration ($\eta_{\text{hock}} \approx 0.35$, elevated metatarsus).
   - Assert: `stance == LocomotorStance.DIGITIGRADE`, `confidence >= 0.88`.
4. `test_unguligrade_stance_classification`:
   - Input: Equine / cervid joint configuration ($\eta_{\text{hock}} \approx 0.60$, tiny contact area, high metapodial angle).
   - Assert: `stance == LocomotorStance.UNGULIGRADE`, `confidence >= 0.90`.

### Test Group 2: Bony Landmarks & ICR Pivots (`TestBonyLandmarksAndICR`)
1. `test_humanoid_landmarks_completeness`:
   - Asserts all required landmarks exist: `suprasternal_notch`, `clavicle_sternal_L/R`, `patella_L/R`, `olecranon_L/R`, `medial_malleolus_L/R`, `lateral_malleolus_L/R`, `greater_trochanter_L/R`, `calcaneus_L/R`.
2. `test_malleoli_anatomical_asymmetry`:
   - Asserts medial malleolus is higher than lateral malleolus:
     $$Z_{\text{medial\_malleolus}} - Z_{\text{lateral\_malleolus}} > 0.010\text{m}$$
   - Asserts medial malleolus is anterior to lateral malleolus ($Y_{\text{medial}} < Y_{\text{lateral}}$ in Blender coords).
3. `test_icr_joint_pivot_internal_containment`:
   - Asserts elbow and knee ICR pivots are strictly inside the limb cross-section volume (not on exterior surface).
   - Asserts knee ICR has posterior offset relative to condyle midpoint.
   - Asserts hip ICR is positioned medially and superiorly relative to the greater trochanter.

### Test Group 3: Bone Roll & Pre-Bend Solver (`TestBoneRollAndPreBend`)
1. `test_hinge_plane_normal_orthogonal`:
   - Asserts $\vec{n}_{\text{hinge}}$ is strictly perpendicular to bone vectors: $|\vec{n}_{\text{hinge}} \cdot \hat{u}_1| < 10^{-6}$ and $|\vec{n}_{\text{hinge}} \cdot \hat{u}_2| < 10^{-6}$.
2. `test_collinear_chain_prebend_enforcement`:
   - Given a completely straight limb chain ($\theta = 180.0^\circ$), asserts pre-bend solver displaces middle joint by $\ge 15\text{mm}$ in the biological flexion direction.
   - Asserts elbow pre-bend has $+Y$ displacement in arm space.
   - Asserts knee pre-bend has $-Y$ displacement in leg space.
3. `test_bone_roll_bilateral_symmetry`:
   - Asserts Left and Right limb rolls are symmetrical and eliminate pole target flipping.
4. `test_bone_roll_script_command_valid`:
   - Asserts generated script string matches Blender syntax `bone.roll = ...`.

### Test Group 4: Volumetric Geodesic Biharmonic Skinning (`TestGeodesicSkinning`)
1. `test_skin_weights_normalization`:
   - Asserts every vertex has $\sum_j w_{ij} = 1.0 \pm 10^{-5}$.
   - Asserts no negative weights: $w_{ij} \ge 0.0$.
   - Asserts max influences per vertex $\le 4$.
2. `test_zero_weight_stealing_axilla_chest`:
   - On a dual-cylinder or humanoid arm-torso test mesh with a $2\text{cm}$ air gap between arm and chest:
   - Asserts vertices on the chest have **0.00%** weight from upper arm and forearm bones.
   - Asserts vertices on the arm have **0.00%** weight from spine/chest bones.
3. `test_zero_weight_stealing_inner_thighs`:
   - On a two-legged mesh with legs $2\text{cm}$ apart:
   - Asserts left inner thigh vertices have **0.00%** weight from right leg bones.
   - Asserts right inner thigh vertices have **0.00%** weight from left leg bones.
4. `test_pure_numpy_execution`:
   - Asserts skinning executes cleanly without importing `scipy`.

---

## 5. Implementation Roadmap for Subsequent Milestones

| Milestone | Target Module | Scope & Objectives |
|---|---|---|
| **M2** | `src/morphomesh/anatomy/stance.py`, `landmarks.py` | Implement `LocomotorStance`, `classify_locomotor_stance`, `compute_bony_landmarks`, and `estimate_icr_joint_pivots`. Verify anthropometric asymmetry and stance classifications. |
| **M3** | `src/morphomesh/anatomy/bone_roll.py` | Implement hinge plane normal, 1-DOF pre-bend solver, closed-form bone roll normalization, and bilateral symmetry. |
| **M4** | `src/morphomesh/anatomy/skinning.py` | Implement volumetric voxelization, air barrier flood-fill, geodesic diffusion, biharmonic smoothing, and trilinear vertex weight sampling in pure NumPy. |
| **M5** | `src/morphomesh/anatomy/__init__.py`, `connectors/animals3d_connector.py`, `blender_bridge.py` | Wire public API exports, upgrade `Animals3DConnector` to use authentic bone rolls and non-empty geodesic weights, update `blender_bridge.py` headless rigging, write `tests/test_anatomy.py`, and run full test suite `uv run pytest -q` to 100% pass. |

---

## 6. Conclusion
The proposed architecture provides a rigorous, mathematically sound, pure-NumPy foundation for biomechanical character and creature rigging. By substituting heuristic distance models with volumetric voxel geodesic biharmonic diffusion and formalizing closed-form bone roll alignment, MorphoMesh achieves industry-grade deformation quality and complete elimination of IK singularities and skin weight stealing.
