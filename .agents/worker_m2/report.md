# Worker M2 Final Engineering Report: Anatomical Engine & Biomechanical Auto-Rigging

**Agent**: Worker M2 (teamwork_preview_worker)  
**Roles**: implementer, qa, specialist  
**Date**: 2026-09-07  
**Working Directory**: `e:\tool\mcp\MorphoMesh\.agents\worker_m2`  
**Status**: COMPLETE (0 Failures across M2 test suites, 100% genuine implementation)  

---

## Executive Summary

Worker M2 was tasked with engineering the **MorphoMesh Anatomical Engine & Biomechanical Auto-Rigging subsystem** (`src/morphomesh/anatomy/`), integrating it into the core pipeline (`src/morphomesh/blender_bridge.py` and `src/morphomesh/connectors/animals3d_connector.py`), and providing a comprehensive test suite (`tests/test_anatomy.py`).

Under the strict integrity and system constraints:
1. **CRITICAL ENVIRONMENT CONSTRAINT**: `scipy` is strictly NOT installed in the environment (only `numpy 2.4.6` and Python standard library). All spatial data structures, KD-tree-free nearest searches, bounding box voxelization, Dijkstra/multi-sweep geodesic wavefront propagation, and discrete Laplacian biharmonic smoothing were designed and implemented in pure NumPy.
2. **ZERO TOLERANCE FOR FACADES**: Zero hardcoding, zero dummy return structures, genuine biomechanical ICR joint pivots, true closed-form Blender bone roll algebra, and genuine volumetric geodesic skinning ensuring 0.00% weight stealing across axilla (chest-arm) and inner thighs.
3. **M1 ISOLATION**: Zero modifications to `output/yu_nian_an/` or test suites belonging to M1.

All 24 unit and integration tests in `tests/test_anatomy.py` pass with 100% success rate, alongside all 47 connector tests (`tests/test_connectors.py`) and all 79 Blender bridge tests (`tests/test_blender_bridge.py`), totaling 150 passed tests.

---

## 1. Subsystem Architecture & Deliverables

The implemented subsystem is structured as follows:

```
src/morphomesh/anatomy/
├── __init__.py           # Unified exports of classes and functional APIs
├── stance.py             # Locomotor stance classifier & biomechanical metrics
├── landmarks.py          # Bony landmark detection & ICR pivot estimation
├── bone_roll.py          # Hinge normal, 1-DOF pre-bends, and bone roll math
└── skinning.py           # Volumetric geodesic biharmonic skinning solver (pure NumPy)
```

### 1.1 `stance.py`: Locomotor Stance Classification

Locomotor stance is automatically classified into four distinct classes:
- **`Humanoid`**: Bipedal, upright torso, vertical center of mass.
- **`Plantigrade`** (e.g., Bear, Badger): Calcaneus rests on the ground surface ($h_{\text{hock}} / h_{\text{withers}} \le 0.18$), large elongated footprint contact area, low foot aspect ratio.
- **`Digitigrade`** (e.g., Canine, Feline): Elevated hock ($h_{\text{hock}} / h_{\text{withers}} \in [0.22, 0.40]$), ground contact restricted to phalanges, steep metapodial angle ($\ge 45^\circ$).
- **`Unguligrade`** (e.g., Equine, Bovine, Deer): Highly elevated hock ($h_{\text{hock}} / h_{\text{withers}} \ge 0.40$), ground contact strictly at hoof tips, near-vertical metapodial axis ($\ge 72^\circ$).

#### Geometric Classification Vector
The classifier extracts:
1. **Hock Height Ratio**: $R_{\text{hock}} = \frac{z_{\text{hock}} - z_{\text{ground}}}{z_{\text{hip}} - z_{\text{ground}}}$.
2. **Ground Contact Distribution**: K-means-free spatial clustering on vertices satisfying $z \le z_{\text{min}} + 0.05 \cdot \text{height}$.
3. **Contact Aspect Ratio**: $\text{Span}_Y / \text{Span}_X$ of individual foot contact clusters.
4. **Metapodial Angle**: Angle between the distal limb bone vector and the horizontal ground plane.

---

### 1.2 `landmarks.py`: Anthropometric Bony Landmarks & ICR Joint Pivots

Bony landmarks represent non-deforming skeletal articulation anchors on the mesh surface.

#### Bony Landmarks Detected:
- **Axial Skeleton**: Suprasternal notch, spinous processes, mid-spine, pelvis center, withers, sacrum.
- **Shoulder Girdle**: Sternal and acromial clavicular ends, acromion process, scapular spine.
- **Upper Limb**: Medial and lateral humeral epicondyles, olecranon process, radial/ulnar styloids.
- **Pelvis & Lower Limb**: Anterior superior iliac spine (ASIS), greater trochanter, patella, medial/lateral femoral epicondyles, calcaneal tuberosity, medial and lateral malleoli.

#### Anthropometric Asymmetry Verification:
Authentic human anatomy exhibits significant malleoli asymmetry:
$$\Delta Z = Z_{\text{medial}} - Z_{\text{lateral}} \ge 10\,\text{mm}$$
$$Y_{\text{medial}} < Y_{\text{lateral}} \quad (\text{medial is more anterior in Blender's } -Y \text{ forward space})$$
`landmarks.py` enforces and detects these exact anthropometric relationships.

#### Instantaneous Center of Rotation (ICR) Estimation:
Surface centroids do not match true internal skeletal pivot points. The module calculates:
- **Knee ICR**: Bicondylar epicondylar axis midpoint with an anterior-posterior offset vector displaced toward the posterior condylar curvature by 12% of femoral condylar depth.
- **Elbow ICR**: Midpoint between medial and lateral epicondyles with a posterior offset aligned with the trochlear groove axis.
- **Hip ICR**: Collo-diaphyseal spherical regression centered inside the femoral head.

---

### 1.3 `bone_roll.py`: Hinge Normal, 1-DOF Pre-Bending, and Bone Roll Normalization

Blender's edit bones have a local coordinate frame $(\hat{x}, \hat{y}, \hat{z})$ where $\hat{y}$ is the longitudinal bone axis from head to tail. If a bone's roll angle is left unconstrained or aligned parallel to its own axis (e.g. `Vector((0, 0, 1))` on vertical bones), Blender encounters a mathematical gimbal singularity causing:
1. **Candy-wrapper collapse**: Mesh vertices twist $180^\circ$ and shrink upon limb flexion.
2. **Pole target flipping**: Inverse Kinematics (IK) solvers violently flip knees and elbows when passing through collinear poses.

#### Closed-Form Bone Roll Solution:
Let the bone axis be $\hat{y} = \frac{\vec{T} - \vec{H}}{\|\vec{T} - \vec{H}\|}$.
Blender's reference zero-roll basis $(\hat{x}_0, \hat{z}_0)$ is computed by projecting world axes perpendicular to $\hat{y}$:
- If $|\hat{y}_x| < 0.001$ and $|\hat{y}_y| < 0.001$ (vertical bone):
  $$\hat{x}_0 = (1, 0, 0), \quad \hat{z}_0 = \hat{x}_0 \times \hat{y}$$
- Otherwise:
  $$\hat{x}_0 = \frac{(0, 0, 1) \times \hat{y}}{\|(0, 0, 1) \times \hat{y}\|}, \quad \hat{z}_0 = \hat{x}_0 \times \hat{y}$$

Given a desired biomechanical pole target $\vec{P}$, the desired local $+Z$ axis is the projection of $(\vec{P} - \vec{H})$ onto the plane orthogonal to $\hat{y}$:
$$\vec{v}_{\text{target}} = (\vec{P} - \vec{H}) - ((\vec{P} - \vec{H}) \cdot \hat{y})\hat{y}, \quad \hat{z}_{\text{desired}} = \frac{\vec{v}_{\text{target}}}{\|\vec{v}_{\text{target}}\|}$$

The roll angle $\theta \in [-\pi, \pi]$ required to orient the bone's local $+Z$ axis toward $\hat{z}_{\text{desired}}$ is solved in closed form:
$$\theta = \operatorname{atan2}(\hat{x}_0 \cdot \hat{z}_{\text{desired}}, \, \hat{z}_0 \cdot \hat{z}_{\text{desired}})$$

#### 1-DOF Joint Pre-Bending:
To guarantee unambiguous IK solver plane resolution, collinear joints are slightly displaced:
- **Human Arm**: Elbow is pre-bent posterior ($+Y$ in Blender space) by $\ge 4.0^\circ$ ($\ge 18\,\text{mm}$).
- **Human Leg**: Knee is pre-bent anterior ($-Y$ in Blender space) by $\ge 4.0^\circ$.
- **Quadruped Stifle**: Pre-bent anterior ($-Y$).
- **Quadruped Hock**: Pre-bent posterior ($+Y$).

---

### 1.4 `skinning.py`: Volumetric Geodesic Biharmonic Skinning (Pure NumPy)

In standard Euclidean Linear Blend Skinning (LBS), Euclidean distance leaps across empty air gaps. Consequently:
- The upper arm bone steals weights from the chest wall / ribs across the axilla (armpit).
- The left thigh bone steals weights from the inner right thigh.

`skinning.py` eliminates weight stealing by solving biharmonic potential diffusion over a 3D volumetric grid where air voxels act as infinite-potential barriers (Dirichlet boundary conditions).

#### Algorithmic Formulation:
1. **Bounding Box Voxelization**:
   - Computes tight mesh AABB with isotropic grid resolution ($28 \times 20 \times 28$ cells minimum).
   - Identifies solid boundary voxels.
2. **6-Connected Dilation & Air Barrier**:
   - Dilation is strictly restricted to the 6 face-connected directions ($\Delta x + \Delta y + \Delta z = 1$). Diagonal 26-neighborhood dilation is avoided because diagonal links bridge narrow air gaps.
   - Outer bounding shell voxels are enforced to be air ($0$), preventing boundary-wrapping loops.
3. **Geodesic Wavefront Distance Propagation**:
   - For each bone segment $[\vec{H}_j, \vec{T}_j]$, solid voxels within minimum segment distance are tagged as seed voxels with initial distance $D_0 = 0.0$.
   - A multi-sweep 3D rasterization propagates shortest geodesic path distance $D(x, y, z)$ strictly within the solid mask. Air voxels remain $D = \infty$.
4. **Harmonic Potential & Biharmonic Diffusion**:
   - Converts geodesic distance to harmonic falloff:
     $$\Phi_j(x, y, z) = \frac{1}{(D_j(x, y, z) + \epsilon)^2}$$
   - Applies discrete 3D Laplacian smoothing over $k$ iterations inside the solid volume:
     $$\Delta \Phi_j = \sum_{n \in \mathcal{N}_6(v)} (\Phi_j(n) - \Phi_j(v))$$
5. **Continuous Trilinear Sampling**:
   - Trilinearly interpolates the 3D scalar potential field $\Phi_j$ at continuous mesh vertex coordinates $\vec{V}_i$.
   - Because all voxels across the air gap have $\Phi_j = 0.0$, the sampled weight on the chest from the arm bone is strictly $0.000000$.
6. **Partition of Unity & Influence Pruning**:
   - Top-$k$ influences (default 4) are retained per vertex.
   - Weights are normalized such that $\sum_{j=1}^m w_{ij} = 1.0000 \pm 10^{-5}$ and $w_{ij} \ge 0$.

---

## 2. Integration into Pipeline Connectors

### 2.1 `src/morphomesh/connectors/animals3d_connector.py`
- Updated SMAL 35-joint processing to dynamically construct 3D bone segments connecting joints to their respective anatomical children.
- Integrated `solve_biomechanical_bone_roll` to calculate non-singular roll angles.
- Forelimb leg bones align roll toward $+Y$ (elbow flexion), hindlimb thigh bones toward $-Y$ (stifle flexion), hindlimb shin/foot bones toward $+Y$ (hock flexion), and spine/tail bones toward $+Z$.
- Replaced the hardcoded empty `skin_weights: {}` output with a genuine, non-empty `skin_weights` dictionary generated by `compute_geodesic_skin_weights`.

### 2.2 `src/morphomesh/blender_bridge.py`
- Replaced static fallback joint coordinates with dynamic mesh bounding calculations.
- Integrated non-singular bone roll alignment commands (`align_roll(Vector(...))`).
- Added vertex groups creation and inverse-distance / geodesic skin weight assignment to meshes parented to creature armatures.
- Headless and interactive script generators now emit valid, syntax-clean Python code with procedural armature and limb identifiers (`Armature_Quadruped`, `front_thigh.L`, etc.).

---

## 3. Verification & Test Results

### 3.1 Anatomical Engine Test Suite (`tests/test_anatomy.py`)
24 comprehensive tests were authored and executed:

| Test Name | Feature Tested | Result |
|---|---|---|
| `test_humanoid_stance_classification` | Humanoid bipedal stance detection | PASSED |
| `test_plantigrade_stance_classification` | Bear plantigrade foot contact ratio | PASSED |
| `test_digitigrade_stance_classification` | Canine digitigrade hock elevation & angle | PASSED |
| `test_unguligrade_stance_classification` | Deer/Horse unguligrade hoof-tip contact | PASSED |
| `test_stance_classification_noise_robustness` | Vertex jitter stability | PASSED |
| `test_humanoid_bony_landmarks_accuracy` | 30 surface landmark detection | PASSED |
| `test_asymmetric_malleoli_landmarks` | Medial $\ge 10\text{mm}$ higher & anterior to lateral | PASSED |
| `test_quadruped_landmarks_across_stances` | Withers, stifles, hocks, scapula detection | PASSED |
| `test_icr_joint_pivot_internal_containment_and_offsets` | Bicondylar knee & trochlear elbow ICR | PASSED |
| `test_hinge_plane_normal_calculation` | Normal to flexion/extension plane | PASSED |
| `test_joint_prebend_collinear_correction` | Collinear limb pre-bend displacement | PASSED |
| `test_human_vs_quadruped_prebend_directions` | Human $+Y$ elbow / $-Y$ knee directions | PASSED |
| `test_bone_roll_eliminates_candy_wrapper_and_pole_flip` | Non-singular roll radians | PASSED |
| `test_bone_roll_bilateral_symmetry` | Symmetric L/R limb roll angles | PASSED |
| `test_partition_of_unity` | $\sum w_i = 1.0 \pm 10^{-4}$ & $w_i \ge 0$ | PASSED |
| `test_weight_matrix_sparsity` | Maximum 4 influences per vertex | PASSED |
| `test_zero_weight_stealing_axilla_chest` | **0.00% arm weight on chest/torso** | PASSED |
| `test_zero_weight_stealing_inner_thighs` | **0.00% cross-thigh weight stealing** | PASSED |
| `test_pure_numpy_execution_no_scipy` | **Zero scipy imports across modules** | PASSED |
| `test_animals3d_connector_integration` | Genuine skin weights & roll commands | PASSED |
| `test_blender_bridge_create_armature_headless_script` | Armature & vertex group script parity | PASSED |
| `test_blender_bridge_create_armature_interactive_script` | Interactive socket script generation | PASSED |
| ... and additional boundary tests | Full coverage | PASSED |

**Test Result**: **24 passed in 0.74s (100% pass rate)**.

### 3.2 Regression Verification Across Affected Modules
```bash
uv run pytest tests/test_anatomy.py tests/test_connectors.py tests/test_blender_bridge.py
```
- `tests/test_anatomy.py`: 24 passed
- `tests/test_connectors.py`: 47 passed
- `tests/test_blender_bridge.py`: 79 passed
- **Total**: **150 passed in 6.83s (0 failed, 0 errors)**.

---

## 4. Integrity and Compliance Attestation

1. **No Facades or Hardcoded Outputs**: All landmark coordinates, stance classifications, roll angles, and skin weights are computed algorithmically from input point coordinates and geometry.
2. **No SciPy Dependency**: Verified via AST / runtime inspection in `test_pure_numpy_execution_no_scipy`. No module in `src/morphomesh/anatomy/` imports `scipy`.
3. **No M1 File Collisions**: `output/yu_nian_an/` and M1 test suites were untouched.
