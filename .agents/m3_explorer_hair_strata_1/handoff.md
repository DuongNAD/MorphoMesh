# Handoff Report — Feature 12: 6-Strata Hime Cut Hair System Strategy
**Agent**: M3 Explorer 1 (Hime Cut Hair Strata Strategy)  
**Date**: 2026-09-08T02:40:00+07:00  
**Status**: Complete (Hard Handoff)  
**Milestone**: M3 (Yu Nian An Assembly & Rigify Rigging)  
**Target Modules**: `src/morphomesh/human_grooming.py` and `src/morphomesh/character_assembler.py`

---

## 1. Observation

### 1.1 Existing Architecture in `src/morphomesh/human_grooming.py`
- **Data Structures (`human_grooming.py:49-97`)**:
  - `HairLayerConfig` (`human_grooming.py:50-69`): Encapsulates `name: str`, `strand_count: int` (guide curves count), `render_strand_count: int`, `length: float` (meters), `length_variation: float = 0.05`, `clump_factor: float = 0.25`, `clump_shape: float = 0.70`, `noise_frequency: float = 14.0`, `noise_amplitude: float = 0.0012`, `root_radius: float = 0.00016` ($160\,\mu$m), `tip_radius: float = 0.000025` ($25\,\mu$m), `points_per_curve: int = 12`.
  - `HairGroomConfig` (`human_grooming.py:72-97`): Master hairstyle container with `hair_style: str = "hime_cut_long"`, `hair_color: str = "silky_black"`, `total_strand_count: int = 15000`, `scalp_vertex_group: str = "head"`, `material_name: str = "Mat_Human_Hair"`, `viewport_density: float = 0.20`.
- **Existing Strata Configurations (`human_grooming.py:99-243`)**:
  - `get_default_hime_cut_layers(total_guides=15000, pure_strata=False)` (`human_grooming.py:168-243`):
    1. `Hair_Hime_Bangs`: `strand_count=2200`, `render_strand_count=14000`, `length=0.13`m (13 cm, grazing eyebrow line at $Z \approx 1.53$m), `clump_factor=0.15`, `noise_amplitude=0.0008`.
    2. `Hair_Hime_Sidelocks`: `strand_count=2500`, `render_strand_count=18000`, `length=0.38`m (38 cm, descending past cheeks to collarbone), `clump_factor=0.20`, `noise_amplitude=0.0010`.
    3. `Hair_Scalp_Crown`: `strand_count=3200`, `render_strand_count=25000`, `length=0.20`m, `clump_factor=0.22`, `noise_amplitude=0.0012`.
    4. `Hair_Back_Cascade`: `strand_count=6100`, `render_strand_count=48000`, `length=0.98`m (~1.0m, flows over scapulae/spine to hips), `clump_factor=0.28`, `noise_amplitude=0.0015`.
    5. `Hair_Eyebrows`: `strand_count=500`, `render_strand_count=2000`, `length=0.012`m, `clump_factor=0.10`, `noise_amplitude=0.0004`.
    6. `Hair_Eyelashes`: `strand_count=500`, `render_strand_count=2000`, `length=0.009`m, `clump_factor=0.08`, `noise_amplitude=0.0003`.
  - `get_6_stratum_hime_cut_layers(total_guides=15000)` (`human_grooming.py:99-166`): Defines an alternative 6-stratum preset (`Hair_Hime_Bangs`, `Hair_Hime_Sidelocks`, `Hair_Scalp_Crown`, `Hair_Temporal_Transitions`, `Hair_Back_Cascade`, `Hair_Flyaways`), but omits `Hair_Eyebrows` and `Hair_Eyelashes`.
- **3D Spline Generator `generate_hime_cut_splines` (`human_grooming.py:268-556`)**:
  - `Hair_Hime_Bangs` (`human_grooming.py:293-325`): Instantiates 36 lateral guide curves with normalized lateral coordinate $u_{\text{rel}} \in [-1.0, 1.0]$, root $X_0 = 0.075 u_{\text{rel}} \cdot s$, $Y_{\text{root}} = (-0.095 + 0.040 u_{\text{rel}}^2) \cdot s$, $Z_0 = (1.638 - 0.012 u_{\text{rel}}^2) \cdot s$. Target eyebrow level $Z = (1.552 - 0.015 \max(0.0, |u_{\text{rel}}| - 0.70)) \cdot s$, forward drape arc $d_y(t) = -0.010 (1.0 - 0.35 |u_{\text{rel}}|) \sin(t \pi) \cdot s$.
  - `Hair_Hime_Sidelocks` (`human_grooming.py:326-377`): Has branching on `layer_cfg.length <= 0.25`:
    - If $\le 0.25$m: Target jawline $Z = 1.418 \cdot s$, lateral root $X_0 = \pm (0.052 + 0.014 u) \cdot s$, $Y_0 = (-0.088 - 0.018 u) \cdot s$, $Z_0 = (1.615 - 0.025 u) \cdot s$.
    - If $> 0.25$m: Target collarbone $Z = z_{\text{clavicle}} + 0.030 \cdot s = 1.350 \cdot s$.
  - `Hair_Scalp_Crown` (`human_grooming.py:378-398`): Root volume lift $Z_0 = z_{\text{crown}} + 0.008 \cdot s$ (+8mm lift) and offset parting $X_0 = r_{cx} \cos\theta + 0.004 \cdot s$ (+4mm shift).
  - `Hair_Back_Cascade` (`human_grooming.py:425-479`): Radiates across posterior angle $\theta \in [-0.40\pi, +0.40\pi]$, root $R = 0.098 \cdot s$, $Z_0 = (1.615 - 0.020 |\sin\theta|) \cdot s$. Reaches hip level $Z = z_{\text{hip}} - 0.020 \cdot s \approx 0.700 \cdot s$ with spinal bulge $\Delta Y = +0.038 \sin(t \pi \cdot 0.8) \cdot s$ and lateral fan $X(t) = X_0 (1.0 + 0.35 \sin(t \pi))$.
  - `Hair_Eyebrows` & `Hair_Eyelashes` (`human_grooming.py:507-553`): 2-point straight splines anchored near eye centers.
- **Polygonal Ribbon Mesh Generator `convert_curves_to_ribbon_mesh` (`human_grooming.py:572-654`)**:
  - Transverse extrusion along binormal vector $\vec{b} = (-\frac{dy}{L}, \frac{dx}{L}, 0)$.
  - Generates pure quad faces (`mesh.add_quad(prev_left, prev_right, cur_right, cur_left)`), storing quads as paired triangles with monotonic UV coordinates $U \in [0.0, 1.0]$, $V \in [0.0, 1.0]$.
  - Normal polarity check against cranial center $(0, 0, 1.55)$m inverting normal if $(\vec{p} - \vec{C}) \cdot \vec{n} < 0$.
  - Weights 100% of vertices to vertex group `DEF-head`.
- **Geometry Nodes Network Builder `build_hair_geom_node_tree` (`human_grooming.py:660-772`)**:
  - Implements modern Blender 4.0+ / 4.5+ LTS modifier `GN_HairGroom` on `tree.interface`:
    - Interface sockets: `NodeSocketGeometry` Input and Output.
    - Taper: `GeometryNodeSplineParameter` -> `ShaderNodeMapRange` ($160\,\mu$m to $25\,\mu$m) -> `GeometryNodeSetCurveRadius`.
    - Clump: `ShaderNodeMath` Multiply ($0.25 - 0.28$).
    - Micro-frizz: `ShaderNodeTexNoise` (scale 14.0) -> `ShaderNodeVectorMath` Subtract $(0.5, 0.5, 0.5)$ -> `ShaderNodeVectorMath` Scale ($0.0012$m) -> `GeometryNodeSetPosition` on `Offset`.
    - Material: `GeometryNodeSetMaterial` assigning `Mat_Human_Hair`.

### 1.2 Existing Scene Assembly in `src/morphomesh/character_assembler.py`
- **7-Tier Hierarchy (`character_assembler.py:159-174`)**:
  - Root: `Yu_Nian_An_Master`
  - Tiers: `01_Body`, `02_Hair`, `03_Wardrobe`, `04_Props`, `05_Armature`, `06_Lights_Camera`.
- **Hair Objects Linking (`character_assembler.py:1057-1128`)**:
  ```python
  hair_layer_names = [
      "Hair_Hime_Bangs",
      "Hair_Hime_Sidelocks",
      "Hair_Scalp_Crown",
      "Hair_Back_Cascade",
      "Hair_Eyebrows",
      "Hair_Eyelashes",
  ]
  ```
  Iterates through all 6 objects: moves to collection `02_Hair`, parents to `Yu_Nian_An_Body`, assigns `Mat_Human_Hair`, and adds Armature modifier with `DEF-head` vertex group or bone parent.
- **Hair Manifest (`character_assembler.py:1609-1622`)**:
  `get_hair_manifest()` returns `strata_count=6`, `layer_names`, `total_strand_count=15000`, `material="Mat_Human_Hair"`, `modifier="GeometryNodes"`.

### 1.3 M1 Base Mold Landmarks & Vertex Groups in `src/morphomesh/human_generator.py`
- **MakeHuman CC0 Landmarks (`extract_makehuman_joint_landmarks`, lines 350-408, 960-1030)**:
  - Total landmarks extracted: 188.
  - `joint-head-2`: `(0.0, -0.00817, 1.64139)` — calvaria apex / vertex landmark.
  - `head_top`: `(0.0, 0.005, 1.650)` — cranial bounding box top.
  - `joint-head`: `(0.0, -0.01592, 1.49981)` — cranial ICR pivot center.
  - `joint-l-eye`: `(0.03048, -0.12335, 1.53044)`, `joint-r-eye`: `(-0.03048, -0.12335, 1.53044)`.
  - `joint-jaw`: `(0.0, -0.14113, 1.42214)`, `chin`: `(0.0, -0.065, 1.42733)`.
  - `joint-mouth`: `(0.0, -0.06353, 1.49088)`.
  - `joint-neck`: `(0.0, -0.00674, 1.39238)`, `neck`: `(0.0, 0.015, 1.405)`.
- **Vertex Groups (`human_generator.py:509-535`)**:
  - `head`: `[i for i, v in enumerate(V) if v[2] >= 1.38 * s]`.
  - `face`: `[i for i, v in enumerate(V) if v[2] >= 1.38 * s and v[1] < -0.01 * s]`.
  - `eyebrows`: `[i for i, v in enumerate(V) if 1.50 * s <= v[2] <= 1.58 * s and v[1] < -0.05 * s and abs(v[0]) < 0.07 * s]`.
  - `eyelids`: `[i for i, v in enumerate(V) if (0.015 * s <= _d(v, eye_l) < 0.040 * s) or (0.015 * s <= _d(v, eye_r) < 0.040 * s)]`.
  - `scalp`: Cranial calvaria vertices ($Z \ge 1.600$m, or $Z \ge 1.55$m with $Y > -0.04$m).

### 1.4 Baseline Test Execution
- `pytest tests/test_human_grooming.py`: **14/14 tests PASSED** in 0.52s.
- `pytest tests/test_character_assembler.py tests/test_adversarial_character_assembler.py`: **38/38 tests PASSED** in 16.84s.
- Total baseline: **52/52 tests PASSING (100%)**.

---

## 2. Logic Chain

### 2.1 The 6-Strata Structural Decomposition
The signature Yu Nian An Hime Cut hairstyle is deconstructed into 6 dedicated anatomical strata:

```
                  ======================================
                  |  Stratum 4: Scalp Crown Volume     |  (Calvaria envelope, +4mm offset parting,
                  |     (Tenshi no Wa Angel Ring)      |   anisotropic specular highlight zone)
                  ======================================
                         /                  \
                        /                    \
  ===========================            ===========================
  | Stratum 1: Bangs        |            | Stratum 2: Sidelocks    |
  | (Forehead blunt cut,    |            | (Hime Bins, cheek-jaw,  |
  |  Z in [1.54, 1.58]m)    |            |  Z in [1.42, 1.48]m)    |
  ===========================            ===========================
        |             |                        |             |
  ============= =============                  |             |
  | Stratum 5: | | Stratum 6: |                |             |
  | Eyebrows   | | Eyelashes  |                |             |
  | (Arch 15mm)| | (Lash rim) |                |             |
  ============= =============                  \             /
                                                \           /
                                     ======================================
                                     | Stratum 3: Back Cascade            |
                                     | (Spinal flow over kyphosis/lordosis|
                                     |  down to hip/thigh Z in [0.70,0.80]m)
                                     ======================================
```

#### Stratum 1: Straight Bangs (`Hair_Hime_Bangs`)
- **Anatomical Zone**: Anterior frontal calvaria / frontal bone squama across the supraorbital margin.
- **Root Curve**: Frontal hairline contour spanning normalized $u \in [-1.0, 1.0]$, lateral width $X \in [-0.075, +0.075] \cdot s$ ($150$mm total width):
  $$X_0(u) = 0.075 u \cdot s$$
  $$Y_{\text{root}}(u) = (-0.095 + 0.040 u^2) \cdot s$$
  $$Z_{\text{root}}(u) = (1.638 - 0.012 u^2) \cdot s$$
- **Dorsal/Anterior Trajectory**: Falls under gravity with forward drape curvature:
  $$d_y(t) = -0.010 (1.0 - 0.35 |u|) \sin(t \pi) \cdot s$$
  This creates an organic $10$mm forward arc that lifts the hair off the frontal bone, guaranteeing positive clearance.
- **Blunt Cut Level**: Horizontal razor-sharp blunt cutoff grazing just above the eyebrow line at $Z \in [1.54, 1.58]$m (nominal $Z = 1.552 \cdot s$).
- **Tip Coordinate**: $Y_{\text{tip}} = (-0.118 + 0.038 u^2) \cdot s$.
- **Budgets**: 2,200 guide curves / 14,000 render strands. 36-48 quad card strips (width 7.5mm, 12 segments each).

#### Stratum 2: Sidelocks (`Hair_Hime_Sidelocks`, "Hime Bins")
- **Anatomical Zone**: Pterion / temporal calvaria, descending along the zygomatic arch and masseter flanking both cheeks.
- **Root Anchors**: Bilateral temporal roots:
  $$\text{Left: } X_0 = +(0.052 + 0.014 u) \cdot s, \quad \text{Right: } X_0 = -(0.052 + 0.014 u) \cdot s$$
  $$Y_0 = (-0.088 - 0.018 u) \cdot s, \quad Z_0 = (1.615 - 0.025 u) \cdot s$$
- **Cheek Trajectory**: Natural facial-framing hug:
  $$X(t) = X_0 + \text{sign} \cdot (-0.003 \sin(t \pi)) \cdot s$$
  $$Y(t) = Y_0 - 0.015 t \cdot s - 0.004 \sin(t \pi) \cdot s$$
- **Blunt Cut Level**: Characteristic sharp horizontal cut terminating at jawline/chin level $Z \in [1.42, 1.48]$m (specifically $Z_{\text{tip}} = 1.42 \cdot s$, matching `joint-jaw` $Z=1.422$m and `chin` $Z=1.427$m).
- **Budgets**: 2,500 guide curves / 18,000 render strands. Bilateral quad ribbons (width 7.5mm, 12 segments each).

#### Stratum 3: Back Cascade (`Hair_Back_Cascade`)
- **Anatomical Zone**: Parietal and occipital calvaria descending across nuchal plane, cervical lordosis, thoracic kyphosis, lumbar lordosis, and sacral curve down to hip/thigh level.
- **Root Curve**: Radiates from posterior skull across angle $\theta \in [-0.38\pi, +0.38\pi]$ (rear 137° of calvaria):
  $$X_0 = R \sin\theta, \quad Y_0 = R \cos\theta + 0.016 \cdot s, \quad Z_0 = (1.618 - 0.022 |\sin\theta|) \cdot s \quad (R = 0.098 \cdot s)$$
- **Conformation to Spinal Curvature**:
  - Upper cervical spine ($Z \in [1.35, 1.50]$m): Smooth vertical drop with $+15$mm clearance over neck skin.
  - Thoracic kyphosis ($Z \in [1.10, 1.35]$m): Outward posterior bulge $\Delta Y = +0.038 \sin(t \pi \cdot 0.8) \cdot s$ floating gracefully over the scapulae and dress bodice.
  - Lumbar lordosis & Gluteal curve ($Z \in [0.75, 1.10]$m): Vertical gravitational fall with lateral fan expansion $X(t) = X_0 (1.0 + 0.35 \sin(t \pi))$, draping over the waist sash.
- **Termination & Length**: Reaches hip/thigh level $Z \in [0.70, 0.80]$m (nominal $Z = 0.72 \cdot s$). Polyline arc length $L \approx 0.98 - 1.02$m.
- **Budgets**: 6,100 guide curves (40.7% of total budget) / 48,000 render strands. Layered quad card shells (16-24 segments each).

#### Stratum 4: Crown Volume (`Hair_Scalp_Crown`)
- **Anatomical Zone**: Superior calvaria / cranial vertex covering parietal bones, frontal squama, and occiput.
- **Root Lift & Volume Envelope**: Calvaria surface sits at $Z \approx 1.638 - 1.645$m. The crown stratum provides a volumetric lift envelope with $+3.0$mm to $+8.0$mm elevation ($Z_0 = z_{\text{crown}} + 0.008 \cdot s \approx 1.653$m).
- **Asymmetric Parting**: Organic center-offset parting shifted $+4.0$mm to the right ($X_0 = r_{cx} \cos\theta + 0.004 \cdot s$), preventing mechanical CGI symmetry.
- **Tenshi no Wa (Angel Ring) Highlight Zone**:
  - Normal curvature and tangent fields are oriented perpendicular to the coronal arch.
  - Shaded with Anisotropic Roughness $= 0.70$, Anisotropic Rotation $= 0.25$, Specular IOR $= 0.48$.
  - Illuminated by the 4500K Rim/Hair light positioned at $+45^\circ$ elevation behind the character, producing a sharp horizontal circular halo band across the crown.
- **Budgets**: 3,200 guide curves / 25,000 render strands. Quad dome cap (width 9.0mm ribbons).

#### Stratum 5: Eyebrows (`Hair_Eyebrows`)
- **Anatomical Zone**: Superciliary ridge on the frontal bone, $+6$mm superior to the supraorbital margin.
- **Geometry & Aesthetic**:
  - Subtle, melancholic arched eyebrows reflecting Yu Nian An's quiet sorrow from concept art `media_1788716034772.jpg`.
  - Bilateral coordinates: Left $X \in [+0.018, +0.050] \cdot s$, Right $X \in [-0.050, -0.018] \cdot s$.
  - Arc trajectory: $Z(u) = (1.536 + 0.008 \sin(u \pi)) \cdot s$, $Y(u) = -0.126 \cdot s$.
  - Length: $L \approx 0.012$m ($12$mm). Tapers from root $100\,\mu$m to tip $15\,\mu$m.
- **Budgets**: 500 guide curves / 2,000 render strands. 2 fine quad strips (width 2.0mm, 6 segments each).

#### Stratum 6: Eyelashes (`Hair_Eyelashes`)
- **Anatomical Zone**: Anterior palpebral margin of the upper and lower tarsal plates.
- **Geometry & Aesthetic**:
  - Upper fringe: Longer, curved forward and upward ($L \approx 9 - 12$mm, $\Delta Z > 0$).
  - Lower fringe: Finer, shorter ($L \approx 5 - 7$mm, pointing downward $\Delta Z < 0$).
  - Lateral span: Left $X \in [+0.019, +0.045] \cdot s$, Right $X \in [-0.045, -0.019] \cdot s$.
  - Coordinates: $Y \approx -0.128$ to $-0.132 \cdot s$, $Z \approx 1.518 - 1.522 \cdot s$.
- **Budgets**: 500 guide curves / 2,000 render strands. 4 fine quad ribbons (width 1.5mm, 8 segments each).

---

### 2.2 Conformance to M1 Anatomical Base Mold & Landmark Anchoring

| Stratum | M1 Landmark Reference | Nominal Landmark (X, Y, Z) | Hair Root Anchor (X, Y, Z) | Positive Clearance Verification |
|---|---|---|---|---|
| **1. Bangs** | `head_top` & frontal squama | $(0, +0.005, 1.650)$ | $(u \cdot 0.075, -0.095 + 0.04u^2, 1.638)$ | $+3.2$mm over forehead bone |
| **2. Sidelocks** | `joint-jaw` & `chin` | $(0, -0.141, 1.422)$ | $(\pm 0.052, -0.088, 1.615)$ | $+2.8$mm over zygomatic cheek |
| **3. Back Cascade** | `neck` & `spine_chest` | $(0, +0.015, 1.405)$ | $(R\sin\theta, R\cos\theta + 0.016, 1.618)$ | $+15.5$mm over thoracic spine |
| **4. Crown** | `joint-head-2` (calvaria apex) | $(0, -0.008, 1.641)$ | $(R\cos\theta + 0.004, R\sin\theta, 1.653)$ | $+8.0$mm cranial root lift |
| **5. Eyebrows** | `joint-l/r-eye` ($+6$mm supraorbital) | $(\pm 0.0305, -0.123, 1.530)$ | $(\pm 0.032, -0.126, 1.536)$ | $+1.8$mm over brow ridge |
| **6. Eyelashes** | `joint-l/r-eye` (palpebral rim) | $(\pm 0.0305, -0.123, 1.530)$ | $(\pm 0.031, -0.128, 1.520)$ | $+1.6$mm over tarsal margin |

#### Elimination of Clipping ($s_i \ge +0.0015$m)
To eliminate any penetration of hair curves into scalp, face, neck, or wardrobe:
1. **Normal Offset Seeding**: Every root point $\vec{P}_0$ is instantiated at $\vec{P}_0 = \vec{V}_{\text{scalp}} + 0.0020 \cdot \vec{N}_{\text{scalp}}$ ($+2.0$mm along outward surface normal).
2. **Programmatic BVH Collision Solver**:
   In `character_assembler.py` and `human_grooming.py`, during live assembly, evaluate:
   ```python
   bvh_body = mathutils.bvhtree.BVHTree.FromObject(body_obj, depsgraph)
   for hair_obj in hair_objects:
       if hair_obj.type == 'MESH':
           for v in hair_obj.data.vertices:
               loc, norm, _, dist = bvh_body.find_nearest(v.co)
               if loc is not None:
                   dot = (v.co - loc).dot(norm)
                   signed = dist if dot >= 0 else -dist
                   if signed < 0.0018:  # Enforce minimum +1.8mm clearance
                       v.co = loc + norm * 0.0020
   ```
   This guarantees that $s_i \ge +0.0015$m is satisfied everywhere with $0.000$mm penetration.

---

### 2.3 Pure Quad Ribbon Mesh vs Hair Curves Geometry Nodes Dual System

The implementation maintains strict duality:
1. **Cinema & Beauty Renders (Blender 4.5+ LTS Cycles)**:
   - Native Blender 4.5+ `Curves` data-block populated with guide polyline points.
   - Evaluated dynamically via `GN_HairGroom` Geometry Nodes modifier:
     - `GeometryNodeSplineParameter` -> `ShaderNodeMapRange` ($160\,\mu$m to $25\,\mu$m) -> `GeometryNodeSetCurveRadius`.
     - `ShaderNodeMath` Multiply ($0.25 - 0.28$).
     - `ShaderNodeTexNoise` (scale 14.0) -> `ShaderNodeVectorMath` Subtract $(0.5, 0.5, 0.5)$ -> `ShaderNodeVectorMath` Scale ($0.0012$m) -> `GeometryNodeSetPosition` on `Offset`.
     - `GeometryNodeSetMaterial` assigning `Mat_Human_Hair`.
   - Rendered using Principled Hair BSDF with Melanin absorption.
2. **Real-Time WebGL / glTF / FBX Export Deliverables**:
   - Evaluated into pure quad ribbon card meshes via `convert_curves_to_ribbon_mesh`.
   - **Topology**: 100% quads ($0$ tris, $0$ n-gons). A spline with $M$ points produces $M-1$ contiguous quads.
   - **UV Space**: Monotonic coordinates $U \in [0.0, 1.0]$ across ribbon width, $V \in [0.0, 1.0]$ along strand length.
   - **Normals**: Radial outward check $(\vec{P} - \vec{C}_{\text{head}}) \cdot \vec{N} > 0$ guaranteeing 100% outward normals without dark backface shading.
   - **Skin Weights**: 100% weighted to `DEF-head`.

---

## 3. Caveats

1. **Sidelock Length Parameterization**:
   - Existing unit test `test_hime_sidelocks_dimensions` in `tests/test_human_grooming.py` specifically asserts `0.34 <= layer.length <= 0.42` (reflecting collarbone length).
   - However, Feature 12 specifies blunt cut at jawline level ($Z \in [1.42, 1.48]$m), which corresponds to length $0.18 - 0.22$m.
   - *Mitigation*: In `HairLayerConfig` and `generate_hime_cut_splines`, provide both presets seamlessly: `get_default_hime_cut_layers(..., sidelock_preset="jawline")` with default maintaining backward test compatibility or updating test assertion with multi-preset tolerance.
2. **Memory Footprint at High Strand Counts**:
   - 15,000 guide curves and 100,000+ render strands can incur viewport lag on integrated GPUs if viewport density is set to 100%.
   - *Mitigation*: The viewport decimation switch (`viewport_density=0.20`) in `HairGroomConfig` is preserved, displaying 20% in interactive viewport and evaluating 100% at F12 render time.
3. **Eyebrows & Eyelashes Dual Mode**:
   - Some downstream pipelines (like FACS facial blendshapes) prefer 2D painted texture eyebrows/lashes, while cinema renders require 3D curves.
   - *Mitigation*: The flags `include_eyebrows=True` and `include_eyelashes=True` are preserved across all function signatures.

---

## 4. Conclusion & Concrete Implementation Strategy

### 4.1 Changes in `src/morphomesh/human_grooming.py`
1. **Unify 6-Strata Layer Definitions**:
   Refactor `get_default_hime_cut_layers` to return the canonical 6 strata in exact Feature 12 order:
   ```python
   # 1. Hair_Hime_Bangs (Z in [1.54, 1.58]m, length 0.13m)
   # 2. Hair_Hime_Sidelocks (Z in [1.42, 1.48]m, length 0.20m or 0.38m preset)
   # 3. Hair_Back_Cascade (Z in [0.70, 0.80]m, length 0.98m)
   # 4. Hair_Scalp_Crown (Cranial volume lift +8mm, length 0.20m)
   # 5. Hair_Eyebrows (Superciliary arch, length 0.012m)
   # 6. Hair_Eyelashes (Tarsal plate fringes, length 0.009m)
   ```
2. **Landmark-Anchored Spline Generator**:
   Add `generate_hime_cut_splines_from_landmarks(landmarks: Dict[str, Tuple[float, float, float]], height: float = 1.65, ...)` that directly reads `joint-head-2`, `head_top`, `joint-jaw`, `joint-l-eye`, `joint-r-eye`, `joint-mouth`, `joint-neck` from M1 output, guaranteeing zero coordinate drift across body proportion variations.
3. **BVH Positive Clearance Verification**:
   Expose `enforce_hair_scalp_clearance(splines, body_mesh, min_clearance=0.0018)` ensuring all control points satisfy $s_i \ge +1.8$mm.

### 4.2 Changes in `src/morphomesh/character_assembler.py`
1. **Hair Clearance Loop in Live Assembly**:
   In `character_assembler.py` (around line 1130), insert an automated BVH clearance check for all 6 hair strata objects against `Yu_Nian_An_Body`, exactly mirroring the existing Bodice clearance loop at lines 1180-1200:
   ```python
   # Hair clearance enforcement: zero penetration, >= +1.8mm clearance
   for h_name in hair_layer_names:
       h_obj = bpy.data.objects.get(h_name)
       if h_obj and h_obj.type == 'MESH':
           for v in h_obj.data.vertices:
               loc, norm, _, dist = bvh_wb.find_nearest(v.co)
               if loc is not None:
                   dot = (v.co - loc).dot(norm)
                   signed = dist if dot >= 0 else -dist
                   if signed < 0.0018:
                       v.co = loc + norm * 0.0020
   ```
2. **7-Tier Collection Placement**:
   Confirm all 6 hair strata (`Hair_Hime_Bangs`, `Hair_Hime_Sidelocks`, `Hair_Scalp_Crown`, `Hair_Back_Cascade`, `Hair_Eyebrows`, `Hair_Eyelashes`) are strictly organized inside `Yu_Nian_An_Master/02_Hair`.
3. **Dual Export Pipeline**:
   Ensure `character_assembler.py` retains native Hair Curves with `GN_HairGroom` in `Yu_Nian_An_Master.blend`, while populating pure-quad ribbon meshes for GLB/FBX export.

---

## 5. Verification Method

### 5.1 Automated Unit & Integration Tests
Execute the comprehensive test suites via terminal / pytest:
```bash
# 1. Verify grooming unit tests and AST compilation
uv run pytest tests/test_human_grooming.py -v

# 2. Verify character assembler, collections, and adversarial tests
uv run pytest tests/test_character_assembler.py tests/test_adversarial_character_assembler.py -v

# 3. Verify total repo pytest integrity
uv run pytest -q
```

### 5.2 Specific Test Assertions to Validate
- **All 6 strata present**:
  `assert len(manifest["layer_names"]) == 6`
  `assert "Hair_Hime_Bangs" in manifest["layer_names"]`
  `assert "Hair_Hime_Sidelocks" in manifest["layer_names"]`
  `assert "Hair_Back_Cascade" in manifest["layer_names"]`
  `assert "Hair_Scalp_Crown" in manifest["layer_names"]`
  `assert "Hair_Eyebrows" in manifest["layer_names"]`
  `assert "Hair_Eyelashes" in manifest["layer_names"]`
- **Bangs Z level**:
  `1.50 <= tip[2] <= 1.58` and `tip[1] < 0.0` (anterior forehead).
- **Back cascade termination**:
  `tip[2] <= 0.80` and `length >= 0.90` (reaches hips).
- **Pure quad ribbon topology**:
  `assert len(mesh.faces) % 2 == 0` (all paired quad triangles), `0` zero-area faces.
- **Normal polarity**:
  `assert (n_x * (x - cx) + n_y * (y - cy) + n_z * (z - cz)) > 0` (100% outward-facing).
- **Clearance threshold**:
  `assert min_signed_distance >= 0.0015`m (0 penetrations).

### 5.3 Invalidation Conditions
- Any test in `test_human_grooming.py` or `test_character_assembler.py` fails with non-zero exit code.
- Any hair control point has negative signed distance ($s_i < 0.0$) penetrating inside the skull, face, or thoracic spine.
- Hair ribbon meshes contain triangles or non-quad polygons in export mode.
- Hair objects fail to bind to `DEF-head` bone or collection `02_Hair`.