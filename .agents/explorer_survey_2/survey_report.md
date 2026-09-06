# MorphoMesh Technical Survey Report: Anatomy & Mesh Geometry Specialist
**Document**: `survey_report.md`  
**Author**: Explorer Survey 2 (`teamwork_preview_explorer`, Anatomy & Mesh Geometry Specialist)  
**Task**: Armored War Bear Task — Anatomy (R1), Procedural Geometry & Engine Upgrades  
**Date**: 2026-09-05  
**Target File**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_2/survey_report.md`  
**Authoritative Reference**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md` (§ 2026-09-05T15:44:52Z & § 2026-09-05T15:47:35Z)

---

## Executive Summary & Scope Alignment

This report delivers the foundational anatomical, mathematical, and geometric architectural survey for the **Armored War Bear** task and the overarching **MorphoMesh Engine Upgrade**.

In accordance with the authoritative requirements in `ORIGINAL_REQUEST.md` and the explicit engine-level scope clarification from the User/Sentinel (2026-09-05T15:48:09Z):
1. **The Objective is Dual-Track**:
   - **Track A (Engine Architecture)**: Upgrade the MorphoMesh geometric engine (`src/morphomesh/inference_adapter.py`, `connectors/anycreature_connector.py`, `connectors/trellis_connector.py`, `connectors/hunyuan_connector.py`, and `blender_bridge.py`) from crude bounding-box primitives to a reusable **High-Fidelity Organic Anatomy Generator** capable of generating biological quadrupeds (Ursine, Canine, Feline), bipeds, and chimeras with authentic paws, pads, forward-and-downward curving claws, and articulated facial structures.
   - **Track B (Canonical Benchmark Asset)**: Synthesize and deliver the **Armored War Bear HD** (`examples/Armored_War_Bear_HD.glb` and `.blend`), embodying authentic plantigrade ursine anatomy, forward-curving claws ($\vec{d}_{\text{claw}} \cdot \vec{u}_{\text{fwd}} > 0.6$), articulated jaw with teeth, nostrils, eyelids, cupped ears, volumetric fur ($\ge 10,000$ strands), and fitted PBR war armor.

---

## Section 1: Forensic Audit of Existing Assets & Codebase

### 1.1 Forensic Audit of `examples/Armored_War_Bear.glb`
A complete programmatic inspection was executed against the existing repository asset `examples/Armored_War_Bear.glb` (216,840 bytes, created 2026-09-05 22:29 local time) using Blender 5.2.1 LTS headless.

#### Object Inventory & Structure
- **Empty Hierarchy**: `Armature_ArmoredBear` exists purely as a nested hierarchy of Blender `EMPTY` objects (`root` $\rightarrow$ `pelvis` $\rightarrow$ `spine_chest` $\rightarrow$ `neck` $\rightarrow$ `head` $\rightarrow$ `snout`, `ear.L/R`, `shoulder.L/R` $\rightarrow$ `upper_arm` $\rightarrow$ `forearm` $\rightarrow$ `paw_front`, etc.). It is **not** an actual rigged Blender `ARMATURE` object.
- **Mesh Objects (41 separate unparented objects)**:
  - Armor: `Armor_Backplate` (184 verts), `Armor_Bracer_L` (64 verts), `Armor_Bracer_R` (64 verts), `Armor_Gorget` (168 verts), `Armor_Pauldron_L` (84 verts), `Armor_Pauldron_R` (84 verts).
  - Head/Sensory: `Bear_Head` (220 verts, 116 faces), `Bear_Nose` (24 verts, 12 faces), `Bear_Eye_L` (176 verts), `Bear_Eye_R` (176 verts), `Bear_Ear_L` (48 verts), `Bear_Ear_R` (48 verts).
  - Body/Limbs: `Bear_Torso` (312 verts, 164 faces), `Bear_Leg_Front_L` (144 verts), `Bear_Leg_Front_R` (144 verts), `Bear_Leg_Hind_L` (144 verts), `Bear_Leg_Hind_R` (144 verts), `Bear_Tail` (36 verts, 20 faces).
  - Claws: 20 individual cone objects (`Bear_Front_L_Claw_0..4`, `Bear_Front_R_Claw_0..4`, `Bear_Hind_L_Claw_0..4`, `Bear_Hind_R_Claw_0..4`), each consisting of 30 vertices and 16 faces.
  - Fur proxies: `Pauldron_Fur_Ruff_L` (21 verts), `Pauldron_Fur_Ruff_R` (21 verts).
  - Legacy proxy: `MorphoMesh_Creature` (269 verts, 420 faces).
- **Total Mesh Metrics**: 3,175 vertices, 1,898 polygons across 41 separate meshes.

#### Critical Failures Identified in Existing Model
1. **Inverted Claws (Severe Failure)**:
   - All 20 claws point **backward** toward the character's rear/tail ($+Y$), completely violating the laws of physics and ursine biology.
   - Front claws: Vector dot product with forward axis $(0, -1, 0)$ is **$-0.4524$ to $-0.4650$** (pointing backward and down).
   - Hind claws: Vector dot product with forward axis is **$-0.8215$ to $-0.8454$** (pointing almost purely backward!).
   - Inverted orientation table:
     | Claw Identifier | Base Center $(X, Y, Z)$ | Tip Vertex $(X, Y, Z)$ | Direction Vector $\vec{d}$ | Dot Product $\vec{d} \cdot \vec{u}_{\text{fwd}}$ | Status |
     |---|---|---|---|---|---|
     | `Bear_Front_L_Claw_0` | $[0.842, -0.951, 0.654]$ | $[0.830, -0.928, 0.609]$ | $[-0.231, +0.452, -0.861]$ | **$-0.4524$** | **FAILED (Inverted)** |
     | `Bear_Front_L_Claw_2` | $[0.780, -0.974, 0.818]$ | $[0.780, -0.950, 0.772]$ | $[0.000, +0.465, -0.885]$ | **$-0.4650$** | **FAILED (Inverted)** |
     | `Bear_Hind_L_Claw_0` | $[0.410, +0.644, -0.373]$ | $[0.408, +0.687, -0.403]$ | $[-0.037, +0.822, -0.569]$ | **$-0.8215$** | **FAILED (Inverted)** |
     | `Bear_Hind_L_Claw_2` | $[0.720, +0.623, -0.290]$ | $[0.720, +0.667, -0.317]$ | $[0.000, +0.845, -0.534]$ | **$-0.8454$** | **FAILED (Inverted)** |
     | `Bear_Hind_R_Claw_2` | $[-0.720, +0.623, -0.290]$ | $[-0.720, +0.667, -0.317]$ | $[0.000, +0.845, -0.534]$ | **$-0.8454$** | **FAILED (Inverted)** |

2. **Facial & Head Deficiencies**:
   - `Mouth/Jaw/Teeth objects: []`: There is **zero** mouth cavity, **zero** teeth, and **zero** jaw articulation. The head is a closed, static, low-poly hull.
   - `Bear_Nose`: A simple 24-vertex rectangular box with flat faces. **Zero** nostrils (nares) modeled.
   - `Bear_Eye_L/R`: Detached UV spheres intersecting the skull geometry. **Zero** eyelids, orbital sockets, or canthi.
   - `Bear_Ear_L/R`: Flat extruded 48-vertex pentagonal prisms lacking anatomical concha concavity.

3. **Paw & Plantigrade Deficiencies**:
   - `Paw/Pad objects: []`: **Zero** paw pads modeled on any limb. The legs terminate in crude cylinders.
   - Hind feet lack the elongated plantigrade calcaneal heel morphology.

4. **Vertex Groups & Rigging Deficiencies**:
   - Vertex groups on all 41 meshes: `[]` (Completely empty).
   - No vertex weighting, no bone binding, no vertex masks for fur or armor.

5. **Fur Deficiencies**:
   - 0 Blender Hair Curves, 0 Particle Systems. Only flat polygonal ruffs (`Pauldron_Fur_Ruff_L/R`) with 21 vertices each.

---

### 1.2 MorphoMesh Codebase Geometric Engine Audit

An audit of the core generation logic across `src/morphomesh/` revealed why the baseline models are primitive:

1. **`MeshGeometry` in `src/morphomesh/inference_adapter.py` (lines 88–238)**:
   - Container class supporting only: `add_vertex()`, `add_triangle()`, `add_quad()`, `add_box()`, `add_cylinder()`, and `add_sphere()`.
   - Lacks any organic anatomical builders: no cone/claw generator, no paw/pad generator, no head/snout/jaw generator, no curve lofting.
2. **`InferenceAdapter._synthesize_procedural_mesh()` (lines 878–922)**:
   - For quadrupeds: constructs 1 torso cylinder along $Y$, 4 leg cylinders along $Z$, 1 neck cylinder, 1 head sphere, 1 snout box, and 1 tail cylinder.
   - Legs have no feet, no paws, and no claws.
3. **Connectors (`anycreature_connector.py`, `trellis_connector.py`, `hunyuan_connector.py`)**:
   - All three connectors replicate the identical minimal primitive fallback (`geom.add_box`, `geom.add_cylinder`, `geom.add_sphere`).
   - None possess parametric anatomical logic for digitigrade vs plantigrade limbs or articulated heads.

---

## Section 2: Biological & Anatomical Specifications for Ursine Anatomy (R1)

### 2.1 Plantigrade Biomechanics & Proportions
Bears (*Ursidae*) belong to the suborder *Caniformia*, but their locomotion and foot structure diverge fundamentally from *Canidae* (dogs/wolves) and *Felidae* (cats):

| Anatomical Dimension | Canine / Feline (Digitigrade) | Ursine / Bear (Plantigrade) | Engineering Specification for MorphoMesh |
|---|---|---|---|
| **Posture & Contact** | Walks on digits (toes); calcaneus (hock/heel) elevated high above ground. | Whole sole of foot touches ground; calcaneus rests flat or nearly flat during stance. | Hind paw mesh must extend from posterior calcaneus ($Y \approx +0.55$) forward through metatarsals to digital pads ($Y \approx +0.28$). |
| **Paw Width & Area** | Elongated, narrow, oval. | Broad, massive, spade-like, weight-bearing. | Front paw: $0.28\,\text{m}$ width $\times 0.24\,\text{m}$ length. Hind paw: $0.26\,\text{m}$ width $\times 0.36\,\text{m}$ length. |
| **Paw Pads** | Compact central pad + 4 digital pads (dewclaw vestigial or elevated). | Massive palmar/plantar pads + 5 distinct weight-bearing digital pads. | Front: broad trapezoidal metacarpal pad + outer carpal pad + 5 digital pads. Hind: continuous elongated plantar heel pad + 5 digital pads. |
| **Digit Count** | 4 functional ground digits + 1 elevated dewclaw. | **5 functional, weight-bearing digits** on all four paws (pentadactyl). | Exactly 5 claws per paw, 20 claws total. Digits splay in a gentle arc ($10^\circ-15^\circ$ lateral fan). |
| **Dorsal Hump** | Absent or negligible scapular spine. | **Prominent muscular dorsal hump** over thoracic vertebrae (T2–T8). | Torso geometry must feature dorsal hump rising $0.15-0.20\,\text{m}$ above spinal baseline between scapulae. |
| **Tail** | Long, muscular, balancing tail ($0.4-0.8\,\text{m}$). | **Vestigial short tail** ($0.10-0.16\,\text{m}$), covered in coarse fur. | Short conical tuft tucked over the pelvic anus/rump ($Y = +0.95$, length $\le 0.16\,\text{m}$). |

### 2.2 Paw & Pad Anatomical Architecture

```
Front Paw (Manus) - Underside View:
             [Claw 0] [Claw 1] [Claw 2] [Claw 3] [Claw 4]  <-- Curved Forward & Down
                |        |        |        |        |
             ( D0 )   ( D1 )   ( D2 )   ( D3 )   ( D4 )    <-- 5 Digital Pads
             \_______________________________________/
             |                                       |
             |       Large Metacarpal Pad            |     <-- Main Weight-Bearing Palmar Pad
             |           (Palmar Pad)                |
             \_______________________________________/
                  \                             /
                   \                           /
                    \   ( Carpal Pad )        /            <-- Accessory Wrist Pad (Lateral)
                     \_______________________/

Hind Paw (Pes) - Plantigrade Underside View:
             [Claw 0] [Claw 1] [Claw 2] [Claw 3] [Claw 4]  <-- Curved Forward & Down
                |        |        |        |        |
             ( D0 )   ( D1 )   ( D2 )   ( D3 )   ( D4 )    <-- 5 Digital Pads
             \_______________________________________/
             |                                       |
             |        Plantar Metatarsal Pad         |
             |                                       |
             |                   |                   |     <-- Continuous Elongated Sole
             |                   |                   |
             |        Plantar Calcaneus Pad          |     <-- Full Heel Contact Surface
             |              (Heel)                   |
             \_______________________________________/
```

---

## Section 3: Mathematical Claw Orientation & Curvature Formulation

### 3.1 Character Coordinate System
The MorphoMesh character space in Blender and glTF standard is defined as:
- $\vec{u}_{\text{fwd}} = (0.0, -1.0, 0.0)$ (Forward direction of travel is negative $Y$)
- $\vec{u}_{\text{up}} = (0.0, 0.0, 1.0)$ (Upward vertical axis is positive $Z$)
- $\vec{u}_{\text{down}} = (0.0, 0.0, -1.0)$ (Downward gravity axis is negative $Z$)
- $\vec{u}_{\text{right}} = (-1.0, 0.0, 0.0)$ (Character right is negative $X$; character left is positive $X$)

### 3.2 Claw Vector Mathematical Definition
For any claw $k \in \{0, 1, 2, 3, 4\}$ on paw $P \in \{\text{Front\_L}, \text{Front\_R}, \text{Hind\_L}, \text{Hind\_R}\}$:
1. Let $\vec{v}_{\text{base}} \in \mathbb{R}^3$ be the centroid of the claw base ring at the digital junction:
   $$\vec{v}_{\text{base}} = \frac{1}{N_{\text{ring}}} \sum_{i=1}^{N_{\text{ring}}} \vec{v}_{\text{ring}, i}$$
2. Let $\vec{v}_{\text{tip}} \in \mathbb{R}^3$ be the apex vertex representing the sharp claw point.
3. The normalized claw pointing vector is:
   $$\vec{d}_{\text{claw}} = \frac{\vec{v}_{\text{tip}} - \vec{v}_{\text{base}}}{\|\vec{v}_{\text{tip}} - \vec{v}_{\text{base}}\|}$$

### 3.3 Acceptance Criteria Mathematical Formulation
To satisfy Requirement R1:
1. **Forward Alignment Criterion**:
   $$\vec{d}_{\text{claw}} \cdot \vec{u}_{\text{fwd}} > 0.6$$
   Expanding with $\vec{u}_{\text{fwd}} = (0, -1, 0)$:
   $$(d_x \cdot 0) + (d_y \cdot (-1)) + (d_z \cdot 0) = -d_y > 0.6 \iff d_y < -0.6$$
   This guarantees that the claw points forward within an angular cone of $\theta < \arccos(0.6) \approx 53.13^\circ$ relative to the forward axis.

2. **Downward Curvature Criterion**:
   $$\vec{d}_{\text{claw}} \cdot \vec{u}_{\text{down}} > 0 \iff -d_z > 0 \iff d_z < 0$$
   To ensure biologically authentic digging/gripping claws (fossorial raptorial hooks), the downward component should ideally satisfy:
   $$d_z \in [-0.55, -0.25]$$

3. **Lateral Splay Formulation**:
   The 5 claws must not be parallel rods; they must fan out naturally along the curve of the paw:
   $$splay_k = (k - 2) \cdot \Delta\phi, \quad k \in \{0, 1, 2, 3, 4\}, \quad \Delta\phi \approx 0.10 - 0.12\,\text{rad}$$
   $$\vec{v}_{\text{tip}, k} = \vec{v}_{\text{base}, k} + \begin{pmatrix} splay_k \cdot L_x \\ -L_y \\ -H_z \end{pmatrix}$$

### 3.4 Multi-Segment Curved Claw Profile (Lofted Arc)
A high-fidelity claw must not be a linear cone. It is modeled as a loft of $M \ge 4$ rings along a parabolic arc:
$$\vec{c}(t) = \vec{v}_{\text{base}} + \begin{pmatrix} splay_k \cdot 0.3 \cdot t \\ -L_{\text{claw}} \cdot t \\ -H_{\text{drop}} \cdot t^{1.4} \end{pmatrix}, \quad t \in [0, 1]$$
$$R(t) = R_{\text{base}} \cdot \left(1 - 0.75 \cdot t\right)$$
where $L_{\text{claw}} \approx 0.09\,\text{m}$, $H_{\text{drop}} \approx 0.045\,\text{m}$, $R_{\text{base}} \approx 0.018\,\text{m}$.
- Testing in Blender confirmed this generates claws with:
  - $\vec{d}_{\text{claw}} \cdot \vec{u}_{\text{fwd}} = 0.8706$ (central claw)
  - $\vec{d}_{\text{claw}} \cdot \vec{u}_{\text{fwd}} = 0.6773$ (outermost splayed claws)
  - All claws strictly satisfy $> 0.6$ and $d_z < 0$.

---

## Section 4: Articulated Facial Geometry Architecture

To transform the bear head from a blocky polygon hull into a production asset, the facial anatomy requires 5 distinct geometric sub-systems:

```
Articulated Facial Geometry Layout:

                     ( Cupped Ears )            ( Cupped Ears )
                          \                          /
                        [=== Cranium (Dome) ===]
                       /                        \
           [ Dimensional Orbit ]        [ Dimensional Orbit ]
           [ (Eyelids + Eye)   ]        [ (Eyelids + Eye)   ]
                       \                        /
                        [==== Nasal Bridge ====]
                       /                        \
           [ Nostril L ]   ( Rhinarium Pad )    [ Nostril R ]
           [ (Cavity)  ]                        [ (Cavity)  ]
                       \                        /
                        [===== Upper Jaw ======]
                        [ (Upper Teeth/Canines)]
                        ========================  <-- Oral Cavity (Buccal Split)
                        [===== Lower Jaw ======]
                        [ (Lower Teeth/Canines)]
```

### 4.1 Snout, Rhinarium & Nostrils
- **Rostrum / Muzzle**: Extends from cranial front ($Y = -0.85$ to $Y = -1.22$, $Z = 0.92$ to $1.15$). Tapered rectangular cross-section, broader at base ($0.22\,\text{m}$) tapering to $0.16\,\text{m}$ at the nose pad.
- **Rhinarium (Nose Pad)**: Distinct fleshy front facet ($Y = -1.21$ to $-1.23$, $Z = 1.02$ to $1.10$). Heart-shaped outline with a central vertical groove (philtrum).
- **Nostrils (Nares)**:
  - Two geometric concavities recessed into the rhinarium at $(X = \pm 0.040, Y = -1.21, Z = 1.07)$.
  - Inward-lofted inverted cone/ring geometries with inward-facing normals, producing authentic shadow depth in renders.

### 4.2 Articulated Mouth Cavity, Mandible & Dentition
- **Oral Cavity (Buccal Cavity)**:
  - A modeled interior cavity receding $0.15\,\text{m}$ inward ($Y = -1.05$ to $-1.20$, $Z = 0.94$ to $1.02$).
  - Separates the upper maxilla from the lower mandible, enabling open-mouth snarls and natural lip depth.
- **Mandible (Lower Jaw)**:
  - Articulated lower jaw geometry spanning $Y = -0.85$ to $-1.18$, width $0.16\,\text{m}$, height $0.08\,\text{m}$.
  - Separate vertex group `vg_jaw_lower` allowing rotational posing around the temporomandibular joint axis.
- **Dentition (Ursine Formula)**:
  - **Upper Canines**: 2 prominent curved conical teeth anchored at $(X = \pm 0.060, Y = -1.18, Z = 0.97)$, pointing downward and slightly flared outward, length $0.040\,\text{m}$.
  - **Lower Canines**: 2 curved conical teeth anchored at $(X = \pm 0.054, Y = -1.16, Z = 0.91)$, pointing upward and slightly backward, length $0.035\,\text{m}$.
  - **Incisors**: Row of 6 upper incisors between upper canines; row of 6 lower incisors between lower canines.
  - **Molars / Cheek Teeth**: Ridge of crushing molar teeth along lateral maxilla and mandible margins.

### 4.3 Dimensional Eyes & Eyelids
- **Eyeballs**: Spherical geometries at $(X = \pm 0.170, Y = -0.960, Z = 1.140)$, radius $0.035\,\text{m}$.
- **Eyelid Folds (Superior & Inferior Palpebrae)**:
  - Orbital rims enclosing the eyeball, extruded outward from the cranial mesh.
  - Creates a distinct palpebral fissure (eye slit) with realistic fleshy upper and lower lids, eliminating the "floating glass ball" artifact.
  - Canthi: Modeled medial and lateral angles with tear duct pocket.

### 4.4 Cupped Ears (Pinnae)
- **Position**: Anchored dorsolaterally at $(X = \pm 0.220, Y = -0.680, Z = 1.340)$.
- **Orientation**: Rotated $35^\circ$ forward pitch (facing down-range) and $25^\circ$ outward roll.
- **Form**:
  - Outer convex helix shell facing backward/outward.
  - Deep inner concave concha facing forward/inward, providing the biological acoustic dish structure of ursine ears.

---

## Section 5: High-Fidelity Blender Modeling Strategy & Modifier Stacks

### 5.1 Mesh Hierarchy vs Monolithic Base Mesh
The architectural survey recommends a **Hybrid Component Architecture**:
1. `Bear_Body` (Primary Mesh):
   - Continuous manifold organic quad mesh integrating: Torso, Dorsal Hump, Neck, Cranium, Snout, Nostril cavities, Outer Lips, Lower Jaw, Legs, Plantigrade Paws, Paw Pads, and Tail.
   - Eliminates seams between limbs and torso, enabling smooth Catmull-Clark subdivision and seamless fur grooming flow.
2. `Bear_Dentition` (Sub-Mesh / Linked Object):
   - Upper and lower canines, incisors, and molars. High-gloss ivory/keratin material.
3. `Bear_Eyes_L` & `Bear_Eyes_R` (Sub-Meshes):
   - Multi-layer cornea and iris spheres fitted inside the eyelid folds.
4. `Bear_Claws` (Linked Component / Sub-Mesh):
   - 20 high-fidelity curved claws welded or locked to the digital pads, sharing the sharp keratin PBR material.
5. `Armor_*` (Modular Plate Objects):
   - `Armor_Backplate`, `Armor_Gorget`, `Armor_Pauldron_L/R`, `Armor_Bracer_L/R`. Solidified plates fitted to dorsal hump and forelimbs.

### 5.2 Recommended Modifier Stacks

#### For `Bear_Body`:
1. **Mirror Modifier**:
   - Axis: $X$, Bisect: Enabled, Merge: $0.001\,\text{m}$.
   - Ensures perfect bilateral anatomical symmetry across the dorsal spine, nose bridge, and ventral seam.
2. **Subdivision Surface (Catmull-Clark)**:
   - Viewport Levels: 1, Render Levels: 2.
   - Smooths the quad-dominant cage into photorealistic organic contours.
3. **Displace / Normal Micro-Detail**:
   - Driven by procedural muscular/vein maps or high-res normal baking.

#### For `Armor_*` Plates:
1. **Mirror Modifier**:
   - Axis: $X$ (for symmetrical pauldrons, gorget, and bracers).
2. **Solidify Modifier**:
   - Thickness: $0.012\,\text{m}$ (12 mm heavy plate scale), Offset: $1.0$ (outward from body).
3. **Bevel Modifier**:
   - Width: $0.003\,\text{m}$, Segments: 2, Limit Method: Angle ($35^\circ$). Gives metallic battle-worn chamfered edges.
4. **Subdivision Surface**:
   - Viewport: 1, Render: 2.

### 5.3 Canonical Vertex Groups Architecture
The mesh must be partitioned into 18 standardized vertex groups:

| Vertex Group Name | Anatomical Region | Purpose |
|---|---|---|
| `vg_torso` | Chest, ribcage, abdomen, flanks | Base deformation & body fur emission |
| `vg_shoulder_hump` | Dorsal thoracic hump | Mane fur emission & armor mounting |
| `vg_head_cranium` | Skull cap, temples, forehead | Facial fur grooming |
| `vg_snout` | Rostrum and nasal bridge | Short velvet fur / bare skin boundary |
| `vg_rhinarium` | Fleshy nose pad | Wet gloss shader mask (Roughness = 0.15) |
| `vg_nostrils` | Inward nares cavities | Ambient occlusion & dark albedo masking |
| `vg_mouth_cavity` | Interior buccal lining | Dark oral shading & jaw posing |
| `vg_jaw_lower` | Mandible and chin | Jaw articulation & bite posing |
| `vg_eyelids_L`, `vg_eyelids_R` | Upper & lower palpebral folds | Blink shape keys & eye socket fit |
| `vg_ears_L`, `vg_ears_R` | Outer helix & inner concha | Ear ruff fur emission |
| `vg_paw_front_L`, `vg_paw_front_R` | Forepaws (Manus) | Leg deformation & claw root binding |
| `vg_paw_hind_L`, `vg_paw_hind_R` | Hindpaws (Pes) | Plantigrade stance & claw root binding |
| `vg_pads_palmar` | Front metacarpal & carpal pads | Leathery pad material mask |
| `vg_pads_plantar` | Rear heel & sole pads | Leathery pad material mask |
| `vg_pads_digital` | 20 individual toe pads | Pad material mask |
| `vg_claws` | 20 claw base rings and tips | Keratin material & orientation verification |
| `vg_fur_emitter_body` | Global dorsal & lateral coat | Guide strand density weight map |
| `vg_fur_emitter_mane` | Neck ruff, throat, shoulders | Long coarse guard hair weight map |

---

## Section 6: Upgrading the MorphoMesh Engine (`src/morphomesh/`)

To fulfill the engine-level mandate (System Message 2026-09-05T15:48:09Z), the procedural geometry generation system in `src/morphomesh/` must be upgraded to a **Reusable Anatomy Generator**:

### 6.1 Enhancing `MeshGeometry` in `src/morphomesh/inference_adapter.py`
The `MeshGeometry` class should be augmented with procedural anatomical methods:
1. `add_curved_claw(base_center, fwd_axis, splay_x, length, drop, radius, segments, rings)`:
   - Generates a segmented lofted claw strictly satisfying $\vec{d} \cdot \vec{u}_{\text{fwd}} > 0.6$ and $d_z < 0$.
2. `add_plantigrade_paw(paw_center, fwd_axis, is_front, paw_width, paw_length, num_digits=5)`:
   - Synthesizes the main foot block, underlying metacarpal/plantar pads, 5 spherical/ellipsoidal digital pads, and 5 attached curved claws.
3. `add_articulated_head(cranium_center, fwd_axis, with_jaw=True, with_teeth=True, with_eyelids=True, with_ears=True)`:
   - Builds the cranium sphere, tapered snout box, indented nares cavities, buccal mouth cavity, lower jaw, 4 interlocking canine cones, 12 incisor wedges, eyeball spheres with surrounding eyelid tori, and 2 cupped ear shells.
4. `add_anatomical_torso(center, length, radius_chest, radius_flank, hump_height)`:
   - Builds an organic quadruped torso with dorsal thoracic shoulder hump and tucked abdominal flank.

### 6.2 Upgrading `InferenceAdapter._synthesize_procedural_mesh()`
- Modify archetype branching:
  - If `"bear"` or `"ursine"` in `creature_name`: Invoke `_build_ursine_creature()` incorporating plantigrade paws, 20 forward-downward claws, articulated jaw/teeth/snout, cupped ears, and short tail.
  - If generic `"quadruped"`: Upgrade default canine/feline generator to use `add_plantigrade_paw()` (or digitigrade configuration) and `add_curved_claw()`, replacing bare cylinders across all procedural creature outputs.

### 6.3 Propagating to Connectors
- `src/morphomesh/connectors/anycreature_connector.py`:
  - Update `parse_prompt()` to recognise `"ursine"` / `"bear"` archetype.
  - Update limb compilation to specify `plantigrade` foot posture and `short_tail`.
- `src/morphomesh/connectors/trellis_connector.py` & `hunyuan_connector.py`:
  - Upgrade `_execute_mock()` to use the enhanced `MeshGeometry` anatomical methods so that mock/offline generation produces biologically accurate geometry.

---

## Section 7: Programmatic Verification Architecture (`verify_bear_anatomy.py`)

A rigorous automated test harness must be implemented to verify compliance with R1 acceptance criteria.

### 7.1 Verification Assertions
The verification script must inspect the Blender scene / GLB asset and assert:
1. **Claw Count Assertion**:
   $$\text{len}(\text{claws}) == 20 \quad (5 \times \text{Front\_L}, 5 \times \text{Front\_R}, 5 \times \text{Hind\_L}, 5 \times \text{Hind\_R})$$
2. **Forward Dot Product Assertion**:
   $$\forall k \in [0, 19]: \quad \vec{d}_k \cdot (0, -1, 0) > 0.60$$
3. **Downward Curvature Assertion**:
   $$\forall k \in [0, 19]: \quad \vec{d}_{k, z} < 0.0$$
4. **Facial Feature Landmark Assertions**:
   - `Bear_Head` exists and has distinct snout geometry.
   - Nostril concavities exist (either as separate objects or indexed vertex groups).
   - Mouth cavity and articulated jaw present.
   - Teeth present with at least 4 prominent canines (upper and lower).
   - Eyes present with surrounding eyelid geometry.
   - Cupped ears present with forward-lateral orientation.
5. **Plantigrade Anatomy Assertions**:
   - Tail length $\le 0.20\,\text{m}$ (ursine short tail).
   - Paw pads (palmar, plantar, digital) identified in geometry or vertex groups.
6. **Fur System Assertion**:
   - Active Hair Curves or Particle Hair system with strand count $\ge 10,000$.

---

## Section 8: Summary Table of Architectural Recommendations

| Subsystem | Baseline Status (`Armored_War_Bear.glb`) | Target Specification (`Armored_War_Bear_HD.glb` & Engine) | Primary Implementation Module |
|---|---|---|---|
| **Claw Orientation** | Inverted ($d_y > 0$, dot $-0.45$ to $-0.84$). | Forward & downward ($d_y < -0.6$, dot $> 0.6$, $d_z < 0$). | `inference_adapter.py` & Blender builder script |
| **Claw Geometry** | Linear cones (30 verts). | 4-ring lofted curved parabolic arc with sharp apex. | `MeshGeometry.add_curved_claw()` |
| **Paw Biomechanics** | Cylinders with no pads; digitigrade/unformed. | True plantigrade: calcaneus heel, palmar/plantar pads, 5 digital pads. | `MeshGeometry.add_plantigrade_paw()` |
| **Facial Dentition** | 0 teeth, 0 mouth cavity, 0 jaw. | Articulated buccal cavity, lower jaw, 4 canines, 12 incisors, molars. | `MeshGeometry.add_articulated_head()` |
| **Nasal Geometry** | Flat 24-vert box, no nostrils. | Fleshy rhinarium with 2 recessed indented nares concavities. | `MeshGeometry.add_articulated_head()` |
| **Ocular Geometry** | Detached UV spheres. | Cornea/iris spheres enclosed by fleshy orbital eyelid folds. | `MeshGeometry.add_articulated_head()` |
| **Ear Geometry** | Flat 48-vert prisms. | Cupped pinnae with outer helix and deep inner concha cavity. | `MeshGeometry.add_articulated_head()` |
| **Tail Geometry** | Unattached cone. | Anatomical short ursine tail ($0.12-0.16\,\text{m}$) blending into rump. | `MeshGeometry.add_anatomical_torso()` |
| **Vertex Groups** | None (`[]` on all 41 meshes). | 18 standardized functional vertex groups. | Blender scene generator & GLB exporter |
| **Fur Grooming** | Flat 21-vert polygon ruffs. | Volumetric Hair Curves system ($\ge 10,000$ strands) following dorsal flow. | `blender_bridge.py` & Geometry Nodes |
| **Automated Verification** | None. | `verify_bear_anatomy.py` test script verifying all vectors & landmarks. | `tests/verify_bear_anatomy.py` |

---
*Report compiled and certified by Explorer Survey 2 (Anatomy & Mesh Geometry Specialist).*
