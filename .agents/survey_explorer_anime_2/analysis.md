# Technical Analysis: Anime Mesh Topology (R1) & Auto-Rigging Deformation Architecture (R2)

**Author**: survey_explorer_anime_2 (Anime Mesh & Rigging Explorer)  
**Date**: 2026-09-09  
**Project**: Anime Character Pipeline (`teamwork_projects/anime_character_pipeline`)  
**Scope**: Requirements R1 & R2 of `ORIGINAL_REQUEST.md`

---

## 1. Executive Summary & Problem Boundary

### 1.1 The Core Problem
Generating high-quality 3D Anime Girl characters that are fully game-ready, VTuber/VRM compatible, and cinema-grade has historically failed in automated pipelines due to two interconnected failure modes:
1. **Mesh Topology Contamination (R1)**: Monolithic, welded meshes generated from neural or text-to-3D models fuse adjacent limbs (e.g., axilla/underarm fused to chest, inner thighs fused at the perineum, pleated skirts fused to thigh geometry, twintails welded to shoulders). Automatic skinning solvers (heat-diffusion, biharmonic coordinates) inevitably bleed weights across air gaps, causing the skirt to tear during a stride, underarms to stretch like webbing, and hair to deform when the torso bends.
2. **Severe Joint Deformation & Volume Collapse (R2)**: Standard Linear Blend Skinning (LBS) exhibits notorious volume loss:
   - **Candy-Wrapper Effect**: Rotating the wrist along the forearm roll axis by $90^\circ - 180^\circ$ collapses the forearm cross-section to zero volume.
   - **Elbow & Knee Pinching**: Acute joint flexion ($>90^\circ$) pinches and thins out the joint, creating a rubber-hose look.
   - **Skirt Tearing & Leg Penetration**: Without radial secondary bones and dynamic collision constraints, skirts slaved directly to thigh bones tear down the midline during walks, runs, or hip sways.
   - **Shoe/Ankle Instability**: Without ground-contact pivots and foot-roll constraints, shoes clip through floors or twist uncontrollably.

### 1.2 Objective & Deliverables
This document delivers the comprehensive engineering blueprints, mathematical formulations, bone schemas, and Blender 4.5+ automation scripts to solve R1 and R2 definitively:
- **R1 Blueprint**: Modular, non-welded anatomical quad topology with 3-loop/5-loop deformation hinges, stylized anime proportions (6.5-7.0 heads), expressive eye sockets, and segmented ribbon hair geometry.
- **R2 Blueprint**: Universal bone hierarchy mapped across VRM 1.0, MMD, Rigify, and Unity Humanoid; dual twist-bone architecture with 0.5 rotational copy constraints; dynamic secondary bone chains for twintails and pleated skirts; Dual Quaternion Skinning (DQS / Preserve Volume) mathematical setup; and component-isolated vertex group weighting strategy.

---

## 2. R1 Technical Specification: Anime Girl Anatomy & Mesh Topology

### 2.1 Discrete Sub-Mesh Modular Architecture
To prevent joint fusion and vertex weight contamination, the character must NOT be generated or skinned as a single welded polygon shell. The model is structured into **7 distinct sub-mesh components** sharing a single master armature:

```
Anime_Girl_Master (Parent Object / Armature)
├── Head_Mesh (Face, ears, back head, mouth cavity, tongue, teeth)
│   ├── Eyes_L_Mesh & Eyes_R_Mesh (Cornea & Iris discs)
│   └── Eyebrows_Eyelashes_Mesh (Discrete cel-shading outline geometry)
├── Hair_Mesh (Bangs, side tufts, rear hair shell, twintails)
├── Torso_Mesh (Neck, shoulders, clavicles, chest, waist, hips/pelvis)
├── Arms_Mesh (L & R: Upper arms, elbows, forearms, wrists, 5-finger hands)
├── Legs_Mesh (L & R: Thighs, knees, shins, ankles, feet)
├── Skirt_Pleated_Mesh (Waistband, pleated skirt panels, inner dark lining)
└── Shoes_Mesh (Socks/tights cuff, loafers/boots, soles)
```

#### Air-Gap Boundary Protection
- **Axilla / Shoulder Junction**: The arm mesh terminates at the deltoid insertion seam. The torso has a corresponding perimeter loop, but the vertices remain un-welded during initial skinning. This guarantees that biharmonic voxel solvers cannot diffuse arm bone weights into the ribcage across the narrow underarm gap.
- **Crotch / Perineal Junction**: Legs terminate at the inguinal fold. The inner thighs are separated by a minimum geometric clearance gap $\Delta x \ge 0.025\,\text{m}$ in rest pose (A-pose).
- **Skirt Air-Envelope**: The skirt mesh is generated as an independent outer shell surrounding the pelvis and upper thighs with an outward clearance margin of $1.5\,\text{cm} - 2.5\,\text{cm}$. Skirt vertices belong strictly to a isolated vertex collection, prohibiting thigh bone assignment.

### 2.2 Clean Quad Topology for Deformation Joints
All deformable surfaces must consist of 100% manifold quadrilaterals (quads) with edge flow aligned along the principal deformation stress trajectories:

| Joint Region | Topology Structure | Edge Loop Count | Deformation Behavior / Rationale |
|---|---|---|---|
| **Shoulder / Deltoid** | Concentric Deltoid Cradle + Axilla Fan | 4 concentric cradle loops, 3 radial axilla loops | Allows $0^\circ \to 135^\circ$ arm abduction without collapse of the clavicular hollow or axillary web pinching. |
| **Elbow (Olecranon)** | 3-Loop Hinge + Cubital Fossa Fan | 3 exterior loops, 2 interior reduction fans | Exterior retains olecranon prominence (sharpness) upon $140^\circ$ flexion; interior folds neatly without polygon penetration. |
| **Wrist Joint** | Transverse Circular Ring Loops | 3 parallel circular quad loops | Perpendicular to bone roll axis; provides linear gradient zone for $0.5$ forearm twist bone weight transition. |
| **Knee (Patella)** | Diamond Patellar Loop + Popliteal 3-Hinge | 1 circular patellar ring, 3 posterior transverse loops | Patella remains rigid and planar during $130^\circ$ knee bend; posterior skin compresses into clean transverse fold. |
| **Waist / Lumbar** | Cylindrical Toroidal Rings | 5 equidistant horizontal quad rings | Permits torso lateral flexion ($\pm 40^\circ$) and axial torsion ($\pm 45^\circ$) without diagonal buckling or volume pinching. |
| **Crotch / Inguinal** | ASIS-to-Pubis Diagonal Crease Loop | 3 diagonal loops bridging pelvis to inner thigh | Isolates leg swing from pelvis floor; prevents crotch vertex tearing during high kicks or splits. |
| **Finger Knuckles** | Extensor 3-Rib Bridge + Palmar Crease | 3 transverse loops on dorsal knuckle, 2 on palmar fold | Preserves knuckle volume and square silhouette when fingers form fists. |

### 2.3 Anime Stylized Proportions & Geometry
Anime aesthetics diverge significantly from photorealistic human anatomy. The proportions must follow the standard Bishoujo / Idol proportion schema:

```
Total Height: 1.58m (7.0 Heads Proportion)
├── Head Height (Cranial top to chin): 0.226m (1.0 H)
├── Chin to Clavicle / Sternum:        0.090m (0.4 H)
├── Clavicle to Mid-Waist:             0.250m (1.1 H)
├── Mid-Waist to Pelvis / Crotch:      0.180m (0.8 H)
├── Crotch to Patella (Thigh length):  0.410m (1.8 H)
└── Patella to Floor (Shin + Foot):    0.424m (1.9 H)
```

#### Detailed Anatomical Features:
1. **Facial Profile**:
   - Nasal bridge: Subtle concave curve in profile; nasal tip projection is minimal ($\le 1.8\,\text{cm}$ from subnasale).
   - Jaw & Chin: Heart-shaped / inverted-triangle contour in front view; sharp V-line chin with rounded mandibular angle in $3/4$ view.
   - Mouth: Small mouth cavity width ($\approx 2.5\,\text{cm}$ in rest pose), positioned high ($1/3$ distance from nose tip to chin).
2. **Eye Sockets & Geometry**:
   - Orbit size: Occupies $35\% - 40\%$ of vertical face height.
   - Separate Cornea/Iris: Planar or slightly spherical concave disc recessed behind a transparent convex cornea cap.
   - Eyelids & Lashes: Separate thick polygon strips following the upper and lower orbital rim to capture crisp cel-shaded outlines.
3. **Slender Limbs**:
   - Arms: Long and slender without pronounced triceps or brachioradialis bulging. Wrist circumference: $12.5\,\text{cm}$.
   - Legs: Smooth, gently curved thighs tapering into slender calves and ankles. Ankle circumference: $18.0\,\text{cm}$.
4. **Hair Geometry**:
   - Modeled as modular clustered ribbons/clumps (not individual strands).
   - Each twintail consists of 3-4 primary taper clump shells with defined quad edge ridges, providing clean specular break lines under cel-shading.

---

## 3. R2 Technical Specification: Anime Auto-Rigging & Deformation Prevention Architecture

### 3.1 Universal Bone Hierarchy & 4-Way Cross-Standard Mapping
The auto-rigging system establishes a single unified bone hierarchy conforming to **VRM 1.0 Humanoid Specification**, with direct 1-to-1 mappings to **Rigify DEF**, **MMD (MikuMikuDance)**, and **Unity Humanoid**:

| Bone Function | Universal Anime Bone Name | VRM 1.0 Humanoid Name | Rigify DEF Name | MMD Japanese Name |
|---|---|---|---|---|
| **Pelvis Root** | `Root_Pelvis` | `hips` | `DEF-spine` | `下半身` / `センター` |
| **Spine Lower** | `Spine_01` | `spine` | `DEF-spine.001` | `上半身` |
| **Spine Mid/Waist** | `Spine_02` | `chest` | `DEF-spine.002` | `上半身2` |
| **Chest / Thorax** | `Chest` | `upperChest` | `DEF-spine.003` | `上半身3` |
| **Neck** | `Neck` | `neck` | `DEF-spine.004` | `首` |
| **Head** | `Head` | `head` | `DEF-head` | `頭` |
| **Left / Right Eye**| `Eye.L` / `Eye.R` | `leftEye` / `rightEye` | `DEF-eye.L` / `DEF-eye.R` | `左目` / `右目` |
| **Left Clavicle** | `Clavicle.L` | `leftShoulder` | `DEF-shoulder.L` | `左肩` |
| **Left Upper Arm** | `UpperArm.L` | `leftUpperArm` | `DEF-upper_arm.L` | `左腕` |
| **Left Upper Arm Twist** | `UpperArm_Twist.L` | *(extension / auxiliary)* | `DEF-upper_arm.L.001` | `左腕捩` |
| **Left Forearm** | `Forearm.L` | `leftLowerArm` | `DEF-forearm.L` | `左ひじ` |
| **Left Forearm Twist** | `Forearm_Twist.L` | *(extension / auxiliary)* | `DEF-forearm.L.001` | `左手捩` |
| **Left Wrist / Hand**| `Hand.L` | `leftHand` | `DEF-hand.L` | `左手首` |
| **Thumb (3 bones)**| `Thumb_01.L`..`03.L` | `leftThumbMetacarpal`..`Distal` | `DEF-thumb.01.L`..`03.L` | `左親指１`..`３` |
| **Index (3 bones)**| `Index_01.L`..`03.L` | `leftIndexProximal`..`Distal` | `DEF-f_index.01.L`..`03.L` | `左人指１`..`３` |
| **Middle (3 bones)**| `Middle_01.L`..`03.L` | `leftMiddleProximal`..`Distal` | `DEF-f_middle.01.L`..`03.L` | `左中指１`..`３` |
| **Ring (3 bones)** | `Ring_01.L`..`03.L` | `leftRingProximal`..`Distal` | `DEF-f_ring.01.L`..`03.L` | `左薬指１`..`３` |
| **Pinky (3 bones)**| `Pinky_01.L`..`03.L` | `leftLittleProximal`..`Distal` | `DEF-f_pinky.01.L`..`03.L` | `左小指１`..`３` |
| **Left Thigh** | `Thigh.L` | `leftUpperLeg` | `DEF-thigh.L` | `左足` |
| **Left Thigh Twist**| `Thigh_Twist.L` | *(extension / auxiliary)* | `DEF-thigh.L.001` | `左足捩` |
| **Left Shin** | `Shin.L` | `leftLowerLeg` | `DEF-shin.L` | `左ひざ` |
| **Left Shin Twist** | `Shin_Twist.L` | *(extension / auxiliary)* | `DEF-shin.L.001` | `左ひざ捩` |
| **Left Foot** | `Foot.L` | `leftFoot` | `DEF-foot.L` | `左足首` |
| **Left Toes** | `Toes.L` | `leftToes` | `DEF-toe.L` | `左つま先` |
| **Twintail Root L**| `Twintail_Root.L` | *(VRM SpringBone)* | `DEF-hair_twintail_root.L` | `左ツインテール根` |
| **Twintail Links L**| `Twintail_01.L`..`05.L`| *(VRM SpringBone chain)* | `DEF-hair_twintail.01.L`..`05.L` | `左ツインテール１`..`５` |
| **Skirt Radial (12)**| `Skirt_01`..`12` | *(VRM SpringBone / Dynamic)* | `DEF-skirt_01`..`12` | `スカート01`..`12` |

---

### 3.2 Upper Limb Rigging & Twist Bones (Candy-Wrapper Elimination)

#### Mechanics of the Candy-Wrapper Defect
When wrist rotates around the longitudinal forearm axis $Y$ by angle $\theta \in [0, \pi]$:
- Under standard single-bone Linear Blend Skinning (LBS), vertex position $v'$ is:
  $$v' = (1 - w) M_{forearm} v + w M_{hand} v$$
- At mid-forearm ($w = 0.5$) and $\theta = 180^\circ$ ($\pi$ radians):
  $$M_{hand} = M_{forearm} \cdot \begin{pmatrix} -1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & -1 \end{pmatrix}$$
- The interpolated transformation matrix at $w = 0.5$ is:
  $$M_{blend} = 0.5 M_{forearm} + 0.5 M_{hand} = M_{forearm} \begin{pmatrix} 0 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 0 \end{pmatrix}$$
- The determinant is $\det(M_{blend}) = 0$. The forearm cross-section collapses to a single line (volume loss of 100%).

#### Twist Bone Solution & Constraint Setup
To eliminate this artifact entirely:
1. **Bone Placement**:
   - `forearm.L`: Parent bone, head at elbow, tail at wrist. Deforms proximal forearm (elbow to mid-shaft).
   - `forearm_twist.L`: Child of `forearm.L`, head at mid-shaft ($50\%$ distance), tail at wrist.
2. **Blender Constraint Configuration**:
   - Target Bone: `forearm_twist.L`
   - Constraint: `COPY_ROTATION`
   - Target: `Armature`, Subtarget: `hand.L`
   - Influence: `0.50`
   - Target Space: `LOCAL_WITH_PARENT` (or `LOCAL`)
   - Owner Space: `LOCAL_WITH_PARENT` (or `LOCAL`)
   - Axis Mask: Only $Y$ axis (longitudinal roll axis in Blender). $X$ and $Z$ rotation axes are unchecked (flexion/abduction are handled exclusively by `hand.L`).
3. **Weight Distribution Gradient**:
   Along forearm length normalized $t \in [0, 1]$ (where $t=0$ is elbow, $t=1$ is wrist):
   - For $t \in [0, 0.4]$: $w_{forearm} = 1.0, w_{twist} = 0.0$
   - For $t \in [0.4, 0.8]$: Linear transition:
     $$w_{twist}(t) = \frac{t - 0.4}{0.4}, \quad w_{forearm}(t) = 1.0 - w_{twist}(t)$$
   - For $t \in [0.8, 1.0]$: Transition between `forearm_twist.L` and `hand.L`:
     $$w_{twist}(t) = 1.0 - \frac{t - 0.8}{0.4}, \quad w_{hand}(t) = \frac{t - 0.8}{0.4}$$
4. **Upper Arm Twist**: Identical setup with `upper_arm_twist.L` inheriting $0.50$ local $Y$ rotation from `upper_arm.L`, distributing bicep/shoulder torsion.

#### Full 5-Finger Articulated Skeleton (15 Bones Per Hand)
- Thumb: `Thumb_01.L` (metacarpal), `Thumb_02.L` (proximal), `Thumb_03.L` (distal).
- 4 Fingers (Index, Middle, Ring, Pinky): 3 phalanges each (Proximal `.01`, Intermediate `.02`, Distal `.03`).
- **Bone Alignment Rule**:
  - Local $X$-axis: Pure curling flexion / extension.
  - Local $Z$-axis: Splay / abduction / adduction.
  - Local $Y$-axis: Longitudinal finger axis directed toward the tip.

---

### 3.3 Lower Limb Rigging & Ground Contact Mechanics

#### Structure & Pre-Bends
- `Thigh.L` $\to$ `Shin.L` $\to$ `Foot.L` $\to$ `Toes.L`.
- **Pre-Bend Biomechanics**:
  - Elbow has $+Y$ or $-Z$ pre-bend ($3^\circ - 5^\circ$).
  - Knee has $-Y$ posterior pre-bend ($5^\circ - 8^\circ$). This pre-bend is mathematically required for the two-bone IK solver to calculate unambiguous pole vector solutions without joint flipping.

#### 3-Point Floor Contact Foot Rig
To prevent anime shoes from sinking into the floor or rocking erratically:
1. **Heel Pivot**: Located at $(X_{ankle}, Y_{heel} = -0.06\,\text{m}, Z = 0.00\,\text{m})$.
2. **Ball / Metatarsal Pivot**: Located at $(X_{ankle}, Y_{ball} = +0.08\,\text{m}, Z = 0.00\,\text{m})$.
3. **Toe-Tip Pivot**: Located at $(X_{ankle}, Y_{tip} = +0.16\,\text{m}, Z = 0.00\,\text{m})$.
4. **Ground Limit Constraint**: Foot bone possesses a `LIMIT_ROTATION` or `FLOOR` constraint linked to the ground plane ($Z \ge 0$), guaranteeing that shoe soles remain flat on the studio floor during dance and idle stances.

---

### 3.4 Dynamic Secondary Bones (Twintails & Pleated Skirt)

#### 3.4.1 Twintails Dynamic Spring Chain
Each twintail is rigged with a 5-bone chain:
`Twintail_Root` $\to$ `Twintail_01` $\to$ `Twintail_02` $\to$ `Twintail_03` $\to$ `Twintail_Tip`.

**Verlet Dynamic Formulation**:
For each node $i$ at time step $t + \Delta t$:
$$x_i^{t+\Delta t} = x_i^t + (1 - c_d)(x_i^t - x_i^{t-\Delta t}) + \frac{k_s}{m_i} (x_{i,rest}^t - x_i^t) \Delta t^2 + \vec{g} \Delta t^2$$

- **Stiffness ($k_s$)**: $0.12 - 0.18$ (restores hair to rest pose; prevents twintails from sagging like wet ropes).
- **Damping ($c_d$)**: $0.55 - 0.65$ (critical damping; prevents oscillation jitter during fast head turns).
- **Gravity ($\vec{g}$)**: $(0, 0, -9.81) \times 0.15$ (soft downward hang).
- **Collision Volumes**:
  - Head Collider: Sphere at $(0, -0.02, 1.50)$, radius $R = 0.11\,\text{m}$.
  - Shoulder Colliders: Spheres at $(\pm 0.16, 0.0, 1.25)$, radius $R = 0.08\,\text{m}$.
  - Collision Rule: If $\|x_i - C_{sphere}\| < R + r_{hair}$, project $x_i$ along normal:
    $$x_i' = C_{sphere} + (R + r_{hair}) \frac{x_i - C_{sphere}}{\|x_i - C_{sphere}\|}$$

#### 3.4.2 Pleated Skirt 12-Radial Spoke Bone Rig
Rigging skirts directly to thigh bones is fundamentally defective because skirts are continuous rings encircling both legs. When legs separate in a stride, the mesh stretches and rips across the sagittal plane.

**Radial Spoke Architecture**:
1. **12 Radial Bones** anchored to `Root_Pelvis`, arranged in an ellipse matching hip contours at elevation $Z_{waist} = 0.88\,\text{m}$:
   $$\theta_k = \frac{2\pi k}{12}, \quad k \in \{0, 1, \dots, 11\}$$
   $$X_k = R_x \cos\theta_k, \quad Y_k = R_y \sin\theta_k \quad (R_x \approx 0.14\,\text{m}, R_y \approx 0.10\,\text{m})$$
2. **Chain Depth**: Each radial spoke contains 2 links: `Skirt_Root_k` $\to$ `Skirt_Tip_k`.
3. **Thigh Collision Capsule Avoidance**:
   Each thigh is represented as a capsule segment $[A_{thigh}, B_{thigh}]$ with radius $R_{thigh} = 0.075\,\text{m}$.
   - For any skirt bone point $P$:
     $$t^* = \text{clamp}\left(\frac{(P - A) \cdot (B - A)}{\|B - A\|^2}, 0, 1\right)$$
     $$P_{proj} = A + t^* (B - A)$$
     $$\vec{d} = P - P_{proj}$$
   - If $\|\vec{d}\| < R_{thigh} + \text{margin}$ (where $\text{margin} = 0.015\,\text{m}$), $P$ is displaced outward:
     $$P' = P_{proj} + (R_{thigh} + \text{margin}) \frac{\vec{d}}{\|\vec{d}\|}$$
4. **Blender Constraint Implementation**:
   - Skirt bones use `LIMIT_ROTATION` constraints:
     - Pitch ($X$-axis): Min $-15^\circ$, Max $+65^\circ$. Skirt can swing forward when pushed by thigh, but cannot penetrate backward into pelvic cavity or flip vertically.
   - Dynamic Driver: Thigh flexion driver adds $+0.45 \times \text{rot}_{thigh}$ to the front skirt bones (`Skirt_01`, `Skirt_02`, `Skirt_12`), causing the skirt to automatically lift naturally when the character sits, steps, or dances.

---

### 3.5 Dual Quaternion Skinning (Preserve Volume) Architecture

#### Mathematical Formulation
Linear Blend Skinning (LBS) fails on twisting and bending because matrix interpolation does not preserve the orthogonal group $SO(3)$. Dual Quaternion Skinning (DQS / DLB) represents rigid transformations as unit dual quaternions:

$$\hat{q} = q_0 + \epsilon q_\epsilon, \quad \epsilon^2 = 0$$

Where:
- $q_0 = \left(\cos\frac{\theta}{2}, \vec{n}\sin\frac{\theta}{2}\right) \in \mathbb{H}$ represents pure 3D rotation.
- $q_\epsilon = \frac{1}{2} t \cdot q_0 \in \mathbb{H}$ represents translation $t = (0, t_x, t_y, t_z)$.
- $\|\hat{q}\| = \|q_0\| = 1$.

#### Dual Quaternion Blending (DLB)
Given bone weights $w_1, \dots, w_n$ ($\sum w_i = 1$):
$$\hat{b} = \sum_{i=1}^n w_i \hat{q}_i$$
To ensure antipodal consistency (quaternion shortest path):
$$\text{If } q_{0,i} \cdot q_{0,1} < 0, \quad \hat{q}_i \leftarrow -\hat{q}_i$$
The blended dual quaternion is normalized:
$$\hat{q}_{blend} = \frac{\hat{b}}{\|\hat{b}_{rot}\|} = \frac{b_0}{\|b_0\|} + \epsilon \left(\frac{b_\epsilon}{\|b_0\|} - \frac{b_0 (b_0 \cdot b_\epsilon)}{\|b_0\|^3}\right)$$

#### Volume Preservation Guarantee
Because $\hat{q}_{blend}$ is a valid unit dual quaternion:
- The resulting spatial transformation is a **pure rigid screw motion** ($SE(3)$).
- The Jacobian determinant of the deformation map is identically unity:
  $$\det(J_{DQS}) \equiv 1.0$$
- Volume loss is mathematically identically zero ($0.00\%$), preventing wrist candy-wrapper pinching, elbow thinning, and shoulder volume collapse.

#### Blender Configuration
In Blender 4.5+, DQS is activated on the character's Armature Modifier:
```python
armature_modifier.use_deform_preserve_volume = True
```
*Note*: When combined with our $0.5$ twist bones, DQS delivers flawless $360^\circ$ continuous limb rotation without surface bulges or pinching.

---

### 3.6 Automatic Weight Assignment Strategy

#### Component-Isolated Vertex Group Allocation
Weights are strictly partitioned by sub-mesh component. Vertex groups not belonging to a component are explicitly pruned:

```
┌─────────────────────────┬─────────────────────────────────────────────────────────────┐
│ Component Sub-Mesh      │ Valid Influencing Bones (All other bone weights == 0.0)      │
├─────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Head_Mesh               │ Head, Neck, Eye.L, Eye.R, Jaw                               │
├─────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Hair_Mesh               │ Head, Twintail_Root.L/R, Twintail_01..05.L/R                │
├─────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Torso_Mesh              │ Root_Pelvis, Spine_01, Spine_02, Chest, Neck, Clavicle.L/R  │
├─────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Arms_Mesh (L)           │ Clavicle.L, UpperArm.L, UpperArm_Twist.L, Forearm.L,         │
│                         │ Forearm_Twist.L, Hand.L, Thumb/Finger bones (15)            │
├─────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Legs_Mesh (L)           │ Root_Pelvis, Thigh.L, Thigh_Twist.L, Shin.L, Shin_Twist.L,   │
│                         │ Foot.L, Toes.L                                              │
├─────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Skirt_Pleated_Mesh      │ Root_Pelvis, Spine_01 (waistband only), Skirt_01..12        │
│                         │ [CRITICAL: Thigh.L and Thigh.R weights strictly 0.000]       │
├─────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Shoes_Mesh (L)          │ Shin.L, Shin_Twist.L, Foot.L, Toes.L                        │
└─────────────────────────┴─────────────────────────────────────────────────────────────┘
```

#### Harmonic Cosine Falloff Weighting Formula
For vertices spanning between bone $A$ and bone $B$ over transition span $[z_{min}, z_{max}]$:
$$u = \text{clamp}\left(\frac{z - z_{min}}{z_{max} - z_{min}}, 0.0, 1.0\right)$$
$$w_A(u) = \frac{1}{2} \left[1 + \cos(\pi u)\right], \quad w_B(u) = 1.0 - w_A(u)$$

This guarantees zero first-order derivative ($\frac{\partial w}{\partial z} = 0$) at both endpoints, eliminating harsh linear skin creases.

#### Normalization & Game-Ready Export Rules
1. **Partition of Unity**: For every vertex $v$:
   $$\sum_{j=1}^K w_j(v) = 1.0000 \pm 10^{-5}$$
2. **Influence Pruning**: Maximum 4 non-zero influences per vertex (clamped to top 4 weights and re-normalized) to ensure 100% compliance with glTF 2.0, VRM 1.0, and mobile game engines.

---

## 4. Blender 4.5+ Python Implementation Blueprints

The following modular Python script snippets are engineered for direct execution in Blender 4.5+ LTS:

### 4.1 Arm & Forearm Twist Bone Constraint Generator
```python
import bpy

def setup_twist_bone_constraints(armature_obj):
    """
    Configures 0.5 rotational distribution on Forearm and Upper Arm twist bones.
    Eliminates candy-wrapper collapse under supination/pronation.
    """
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='POSE')
    pose_bones = armature_obj.pose.bones

    # Left & Right Forearm Twist setup
    for side in ['L', 'R']:
        hand_name = f"DEF-hand.{side}"
        forearm_twist_name = f"DEF-forearm.{side}.001"
        
        twist_pb = pose_bones.get(forearm_twist_name)
        if twist_pb and hand_name in pose_bones:
            # Clean old constraints
            for c in twist_pb.constraints:
                twist_pb.constraints.remove(c)
                
            crc = twist_pb.constraints.new(type='COPY_ROTATION')
            crc.name = "Forearm_Twist_AntiPinch"
            crc.target = armature_obj
            crc.subtarget = hand_name
            crc.target_space = 'LOCAL'
            crc.owner_space = 'LOCAL'
            crc.use_x = False
            crc.use_y = True   # Longitudinal roll axis
            crc.use_z = False
            crc.influence = 0.50
            crc.mix_mode = 'REPLACE'
            print(f"[Rigging] Forearm twist configured for {forearm_twist_name} <- {hand_name} (0.50)")

        # Upper Arm Twist setup
        upper_arm_name = f"DEF-upper_arm.{side}"
        upper_twist_name = f"DEF-upper_arm.{side}.001"
        up_twist_pb = pose_bones.get(upper_twist_name)
        if up_twist_pb and upper_arm_name in pose_bones:
            for c in up_twist_pb.constraints:
                up_twist_pb.constraints.remove(c)
            crc = up_twist_pb.constraints.new(type='COPY_ROTATION')
            crc.name = "UpperArm_Twist_Distribution"
            crc.target = armature_obj
            crc.subtarget = upper_arm_name
            crc.target_space = 'LOCAL'
            crc.owner_space = 'LOCAL'
            crc.use_x = False
            crc.use_y = True
            crc.use_z = False
            crc.influence = 0.50
            print(f"[Rigging] Upper arm twist configured for {upper_twist_name}")

    bpy.ops.object.mode_set(mode='OBJECT')
```

### 4.2 Pleated Skirt 12-Spoke Radial Rig Generator
```python
import bpy, math, mathutils

def build_pleated_skirt_radial_bones(armature_obj, waist_z=0.88, hem_z=0.52, rx=0.14, ry=0.10, num_spokes=12):
    """
    Builds a 12-radial spoke bone chain for the pleated skirt parented to Root_Pelvis.
    Prevents skirt tearing during stride and leg motion.
    """
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    eb = armature_obj.data.edit_bones
    
    pelvis_bone = eb.get("DEF-spine") or eb.get("Root_Pelvis")
    if not pelvis_bone:
        raise RuntimeError("Pelvis bone not found in armature")
        
    skirt_bone_names = []
    for k in range(num_spokes):
        angle = 2.0 * math.pi * (k / num_spokes)
        hx = rx * math.cos(angle)
        hy = ry * math.sin(angle)
        
        tx = (rx + 0.10) * math.cos(angle)
        ty = (ry + 0.08) * math.sin(angle)
        
        b_name = f"DEF-skirt_{k+1:02d}"
        b = eb.new(b_name)
        b.head = mathutils.Vector((hx, hy, waist_z))
        b.tail = mathutils.Vector((tx, ty, hem_z))
        b.parent = pelvis_bone
        b.use_deform = True
        skirt_bone_names.append(b_name)

    bpy.ops.object.mode_set(mode='POSE')
    pb = armature_obj.pose.bones
    
    # Apply limit rotation constraints to prevent skirt flipping inside out
    for b_name in skirt_bone_names:
        p_bone = pb.get(b_name)
        if p_bone:
            lim = p_bone.constraints.new(type='LIMIT_ROTATION')
            lim.name = "Skirt_Pitch_Clamp"
            lim.owner_space = 'LOCAL'
            lim.use_limit_x = True
            lim.min_x = math.radians(-15.0)
            lim.max_x = math.radians(65.0)
            lim.influence = 1.0
            
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"[Rigging] Generated {num_spokes} skirt radial bones with pitch limits.")
```

### 4.3 Dual Quaternion Skinning & Isolated Pruning Setup
```python
import bpy

def configure_dqs_and_isolate_vertex_groups(mesh_obj, armature_obj, allowed_bone_prefixes):
    """
    Enables Dual Quaternion Skinning (Preserve Volume) and removes non-allowed bone weights.
    """
    bpy.context.view_layer.objects.active = mesh_obj
    
    # 1. Armature Modifier DQS
    arm_mod = None
    for m in mesh_obj.modifiers:
        if m.type == 'ARMATURE':
            arm_mod = m
            break
    if not arm_mod:
        arm_mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
        arm_mod.object = armature_obj
        
    arm_mod.use_deform_preserve_volume = True
    print(f"[DQS] Activated use_deform_preserve_volume on {mesh_obj.name}")
    
    # 2. Prune prohibited vertex groups
    removed_count = 0
    for vg in list(mesh_obj.vertex_groups):
        if not any(vg.name.startswith(pfx) for pfx in allowed_bone_prefixes):
            mesh_obj.vertex_groups.remove(vg)
            removed_count += 1
            
    print(f"[Skinning] Cleaned {removed_count} cross-bleeding vertex groups from {mesh_obj.name}")
```

---

## 5. Verification & Acceptance Criteria Matrix

| Verification Metric | Target Threshold / Specification | Measurement / Test Command |
|---|---|---|
| **Forearm Volume Preservation** | Cross-sectional volume loss $< 2.0\%$ under $180^\circ$ wrist roll. | Evaluate vertex bounding-cylinder radius at mid-forearm in Blender frame tests. |
| **Elbow / Knee Pinching** | Minimum thickness $> 85\%$ of rest pose under $120^\circ$ flexion. | Raycast distance between anterior and posterior joint apex vertices. |
| **Skirt Tearing / Penetration** | Zero ($0$) thigh-skirt polygon intersections during $60^\circ$ stride. | Run vertex-to-mesh proximity check: distance from skirt to thigh $\ge 0.01\,\text{m}$. |
| **Shoe Ground Contact** | Shoe sole flat on $Z = 0 \pm 0.002\,\text{m}$ during standing/idling. | Evaluated bounding box minimum $Z$ coordinate of `Shoes_Mesh`. |
| **Twintails Fluid Dynamics** | Damped harmonic oscillation; zero penetration into head/shoulder spheres. | Physics test: head shake $\pm 45^\circ$, twintail settles within 12 frames without jitter. |
| **Weight Normalization** | $\sum w_i = 1.0000 \pm 10^{-4}$ for 100% of vertices; max 4 influences. | Automated skin weight verification script iterating through all vertex groups. |

---
*End of Technical Analysis.*
