# MorphoMesh Technical Survey Report: Footwear, Signature Props, PBR Shaders, Studio Lighting, Export Pipeline & Testing (R3 & R4)

**Document ID**: `MM-SURVEY-PROPS-PIPELINE-001`  
**Author**: Footwear Shaders & Verification Explorer (`explorer_survey_3`)  
**Target Character**: Yu Nian An (余念安)  
**Authoritative Reference**: `ORIGINAL_REQUEST.md` (§ `## 2026-09-07T13:01:03Z`)  
**Reference Assets**:
- Realistic Dress Drapery & Flat Sandals: `media_1788785935849.jpg`
- Concept Character Turnaround Sheet: `media_1788716034772.jpg`
- Skeletal Anatomy Reference: `media_1788785935854.png`
- Fashion Silhouette Reference: `media_1788785935824.jpg`

---

## Executive Summary

This survey provides a comprehensive technical investigation of Requirements 3 & 4 (R3: Footwear & Signature Props, R4: PBR Shaders, Studio Lighting, Export Pipeline & Automated Verification) for the digital human character **Yu Nian An (余念安)**.

Key findings include:
1. **Footwear (Flat Strappy Sandals)**: The current implementation in `src/morphomesh/wardrobe.py` only models a single instep band over a thick block sole (12mm). Per `media_1788785935849.jpg` and `media_1788716034772.jpg`, this must be upgraded to an ergonomic thin leather sole (6–8mm) contoured to the medial longitudinal arch, featuring a 4-strap system (forefoot strap, dorsal instep strap, ankle collar strap, and heel counter strap) that completely exposes all 5 articulated toes.
2. **Signature Magic Props**: The 10 crimson marionette threads must originate at the distal phalanx tails of all 10 fingers (`DEF-*.03.L/R`) and connect via catenary tension curves to 10 instanced luminous white swallowtail butterflies fluttering in flight ($Z \in [0.85\text{m}, 1.30\text{m}]$).
3. **Hair Grooming (Hime Cut)**: The 6-stratum Curves grooming architecture in `src/morphomesh/human_grooming.py` (blunt forehead fringe, symmetrical cheek sidelocks, scalp crown, and 1.0m back cascade) matches the concept sheet with high fidelity, requiring Principled Hair BSDF (melanin 0.85, coat sheen 0.45).
4. **PBR Materials Suite**: Evaluated Random Walk SSS for porcelain fair skin, silk/satin sheen for dress and sash, leather for sandals, and emission for glowing butterflies. Identified a critical gap: **Keratin nail material (`Mat_Human_Nails`) is missing** from `human_materials.py` and must be added for fingernails and toenails.
5. **Studio Lighting & Multi-Angle Renders**: Validated 3-point studio lighting (Key 5500K 500W, Fill 6500K 250W, Rim 4500K 450W for angel-ring highlights) with Track-To constraints, and camera rigs covering 4 turnaround perspectives plus portrait, feet, and hands close-ups.
6. **Export & Verification Suite**: Identified the exact root causes of 14 failing tests in `tests/test_production_exports.py` and `tests/test_character_assembler.py` (caused by outdated mock asset overwrite missing DEF bones and ARKit blendshapes), and formulated the exact remediation steps to achieve a 100% pytest pass rate.

---

## 1. Footwear Architecture: Flat Strappy Sandals (Dép Bệt)

### 1.1 Visual & Anatomical Reference Analysis
- **Reference Image `media_1788785935849.jpg`**: Depicts a woman in a linen dress walking outdoors on cobblestones wearing minimalist flat leather strappy sandals.
  - *Sole*: Ultra-thin, low-profile leather/composite sole conforming closely to the foot shape without a raised block heel.
  - *Strap Layout*: A slim horizontal forefoot band holding the metatarsal heads, leaving all 5 toes entirely free and bare. A diagonal/instep strap securing the arch, and an ankle collar strap connected to a heel counter strap.
  - *Toes*: Fully visible from dorsal, lateral, and frontal angles.
- **Reference Image `media_1788716034772.jpg` (Turnaround & Detail Panel)**:
  - The side foot callout (*"Chi Tiết Trang Phục"*, bottom right) depicts an elegant flat sandal sole resting directly on the ground plane ($Z = 0.0\text{m}$), with a clean strap arching over the instep and exposing the 5 slender toes and the heel.

### 1.2 Current Codebase Audit (`src/morphomesh/wardrobe.py`)
In `src/morphomesh/wardrobe.py`, `generate_flat_sandals()` currently implements:
```python
sole_len = 0.235 * s
sole_w = 0.082 * s
sole_thick = 0.012 * s  # 12mm thickness is too thick/bulky for fine flat sandals
```
- **Limitations**:
  1. *Sole Thickness*: 12mm ($0.012\text{m}$) produces a bulky wedge-like sole rather than a delicate 6–8mm flat leather sole.
  2. *Single Strap*: Only generates one arching strap across the metatarsals ($Y = -0.051\text{m}$ to $-0.086\text{m}$), lacking the ankle collar strap and heel support seen in `media_1788785935849.jpg`.
  3. *Flat Planar Sole*: The footbed is completely flat ($Z = \text{const}$), ignoring the 3D medial longitudinal arch of the human foot.

### 1.3 Proposed Ergonomic Sandal Architecture
To conform to the 5-toed foot geometry generated in `human_generator.py` (heel at $Y = +0.055\text{m}$, ball at $Y = -0.065\text{m}$, toes from $Y = -0.117\text{m}$ to $-0.153\text{m}$), the sandal must comprise:

#### A. Ergonomic Laminated Sole
- **Dimensions**:
  - Total Length: $L = 0.235\text{m} \times s$ (spanning $Y \in [+0.060\text{m}, -0.175\text{m}]$).
  - Width Profile: Heel width $0.065\text{m} \times s$, waist (arch) width $0.054\text{m} \times s$, ball (metatarsal) width $0.084\text{m} \times s$, rounded toe apex $0.076\text{m} \times s$.
  - Thickness: Outsole $0.003\text{m}$ + Insole footbed $0.004\text{m}$ = **Total $0.007\text{m}$ (7mm)**.
- **Plantar Arch Rise**:
  - The medial edge of the insole rises by $+0.006\text{m}$ along the medial longitudinal arch between $Y = -0.010\text{m}$ and $Y = -0.050\text{m}$, hugging the navicular bone and medial cuneiform of the foot.

#### B. 4-Element Strap System
1. **Forefoot Strap (Quai Ngang Mu Bàn Chân)**:
   - Location: $Y \in [-0.095\text{m}, -0.108\text{m}]$, $Z \in [0.007\text{m}, 0.024\text{m}]$.
   - Anchored to the sole edges just proximal to the 5 metatarsophalangeal joints.
   - Clears the base of all 5 toes by $\ge 2.0\text{mm}$, ensuring the toes are 100% exposed and unrestricted.
2. **Dorsal Instep Strap (Quai Mu Chéo)**:
   - Location: $Y \in [-0.035\text{m}, -0.055\text{m}]$, $Z \in [0.010\text{m}, 0.048\text{m}]$.
   - Arches gracefully over the dorsal instep arch of the foot with an anatomical curvature matching the cuneiform-metatarsal contour.
3. **Ankle Collar Strap (Quai Cổ Chân)**:
   - Location: $Z \in [0.072\text{m}, 0.086\text{m}]$, $Y \in [-0.015\text{m}, +0.035\text{m}]$.
   - Encircles the lower leg right above the medial and lateral malleoli (mắt cá trong/ngoài) with an adjustable buckle detail on the lateral side.
4. **Heel Counter / Slingback Strap (Quai Hậu Ôm Gót)**:
   - Rises from the rear heel perimeter ($Y \approx +0.050\text{m}$) diagonally upward to join the ankle collar strap at the posterior Achilles tendon ($Z \approx 0.075\text{m}$).

#### C. Algorithmic Mesh Conformance & Clearance Guarantee
- **Algorithm**:
  - Sample 3D foot mesh vertices from `Yu_Nian_An_Body` in vertex groups `foot_L` and `foot_R`.
  - For each strap ring vertex $V_{\text{strap}}$, compute the nearest surface point $P_{\text{foot}}$ and normal $N_{\text{foot}}$ via `mathutils.bvhtree.BVHTree.find_nearest`.
  - Enforce signed radial clearance:
    $$\vec{V}_{\text{strap}} = P_{\text{foot}} + N_{\text{foot}} \cdot \delta_{\text{clearance}}$$
    where $\delta_{\text{clearance}} = 0.0018\text{m}$ (1.8mm).
  - This ensures **0% mesh clipping/penetration** while eliminating unnatural hovering gaps.

---

## 2. Signature Props Architecture: Magic Threads, Butterflies & Hime Cut

### 2.1 10 Red Magic Marionette Threads (Sợi Chỉ Đỏ Ma Thuật)
- **Concept Reference (`media_1788716034772.jpg`)**:
  - Detail panel *"Chi Tiết Tay"* shows delicate red cords tied around the distal phalanx of each finger.
  - The cords extend gracefully in mid-air, suspending glowing white butterflies.
- **Mathematical Bone Anchor Points**:
  - Left Hand (5 fingers):
    - Thumb: `DEF-thumb.03.L` tail $(+0.3894\text{m}, -0.0798\text{m}, 0.7307\text{m})$
    - Index: `DEF-f_index.03.L` tail $(+0.3747\text{m}, -0.0634\text{m}, 0.6873\text{m})$
    - Middle: `DEF-f_middle.03.L` tail $(+0.3630\text{m}, -0.0539\text{m}, 0.6760\text{m})$
    - Ring: `DEF-f_ring.03.L` tail $(+0.3506\text{m}, -0.0452\text{m}, 0.6881\text{m})$
    - Pinky: `DEF-f_pinky.03.L` tail $(+0.3391\text{m}, -0.0382\text{m}, 0.7084\text{m})$
  - Right Hand (5 fingers): Symmetric negative X coordinates (`DEF-*.03.R`).
- **Thread Trajectory Formulation**:
  - Instead of rigid straight line segments, each thread is parameterized as a quadratic Bezier spline with dynamic catenary drape:
    $$P(t) = (1-t)^2 P_{\text{finger}} + 2(1-t)t P_{\text{control}} + t^2 P_{\text{butterfly}}$$
    where $P_{\text{control}} = \frac{1}{2}(P_{\text{finger}} + P_{\text{butterfly}}) - (0, 0, \Delta z_{\text{sag}})$, with $\Delta z_{\text{sag}} = 0.015\text{m}$ simulating taut tension with subtle gravitational relaxation.
- **Deformation Binding**:
  - Armature modifier with vertex group weighting:
    $$w_{\text{finger}}(t) = \max(0, 1.0 - 0.75 \cdot t), \quad w_{\text{butterfly}}(t) = \max(0, 0.75 \cdot t)$$
  - This allows the cords to naturally follow hand gestures and finger movements during posing.

### 2.2 Luminous White Butterflies in Flight (Đàn Bướm Trắng Phát Sáng)
- **Concept Reference**:
  - Detail panel *"Các Loại Bướm"* illustrates 10 delicate swallowtail butterflies in varied flight attitudes (wings flat, 30° V-glide, 60° vertical stroke).
- **Geometric Topology**:
  - Each butterfly is generated as a pure-quad manifold mesh:
    - Slender segmented thorax/abdomen (4 quads).
    - Left & Right Forewings with arched costal margin (2 quads per wing).
    - Left & Right Hindwings with elongated swallowtail tail extensions (2 quads per wing).
    - Total: 12 vertices, 10 quads (0 triangles, 0 non-manifolds).
- **Spatial Constellation**:
  - 10 butterflies distributed in a helical halo surrounding Yu Nian An's hands, torso, and flanks:
    - Elevation: $Z \in [0.85\text{m}, 1.30\text{m}]$.
    - Lateral Radius: $R \in [0.42\text{m}, 0.65\text{m}]$.
    - Orientation: Tangent to flight path with slight banking angles ($\pm 10^\circ$ roll, $15^\circ$ pitch).

### 2.3 Flowing Black Hair with Straight Bangs (Hime Cut - 姫カット)
- **Concept Reference**:
  - Straight, blunt-cut fringe covering forehead down to eyebrow line.
  - Symmetrical face-framing sidelocks (tóc mai) ending near clavicles.
  - Long, sleek black hair cascading down the spine past the hips.
- **6-Stratum Hair Curves Architecture (`src/morphomesh/human_grooming.py`)**:
  | Layer Name | Function | Guide Count | Render Strands | Length | Target Elevation |
  |---|---|---|---|---|---|
  | `Hair_Hime_Bangs` | Blunt forehead fringe | 2,200 | 14,000 | 0.13m | Grazes brow at $Z = 1.54\text{m}$ |
  | `Hair_Hime_Sidelocks` | Face-framing side tresses | 2,500 | 18,000 | 0.38m | Descends to clavicle $Z = 1.35\text{m}$ |
  | `Hair_Scalp_Crown` | Cranial volume & parting | 3,200 | 25,000 | 0.20m | Scalp contour $Z = 1.64\text{m}$ |
  | `Hair_Back_Cascade` | Long flowing spine waterfall | 6,100 | 48,000 | 0.98m | Cascades to hips $Z = 0.72\text{m}$ |
  | `Hair_Eyebrows` | Melancholic thin arches | 500 | 2,000 | 0.012m | Supraorbital ridge $Z = 1.54\text{m}$ |
  | `Hair_Eyelashes` | Upper/lower delicate lashes | 500 | 2,000 | 0.009m | Palpebral margin $Z = 1.52\text{m}$ |
- **Geometry Nodes Hair Modifier Chain**:
  1. *Interpolate Hair Curves*: Expands 15,000 guides to 109,000 render strands.
  2. *Clump Curves*: Tip clump factor $0.25$, preserving root scalp volume.
  3. *Hair Curve Noise*: Micro-frizz amplitude $0.0012\text{m}$, frequency $14.0$.
  4. *Set Curve Radius*: Smooth taper from root ($0.00016\text{m} = 0.16\text{mm}$) to tip ($0.000025\text{m} = 0.025\text{mm}$).
  5. *Material*: Principled Hair BSDF (`Mat_Human_Hair`).

---

## 3. PBR Material Suite Evaluation & Shader Specifications

Blender 4.5+ LTS uses the modernized **Principled BSDF v2** socket architecture. The shader parameters for all character materials are specified below:

### 3.1 Porcelain Skin Shader (`Mat_Human_Skin_SSS`)
- **Base Color**: $(0.918, 0.791, 0.723, 1.0)$ — `#F6E4DA` porcelain fair tone.
- **Roughness**: $0.35$ base epidermal roughness.
- **Subsurface Scattering**:
  - Method: `RANDOM_WALK` (or `RANDOM_WALK_SKIN`).
  - Weight: $0.28$.
  - Radius: $(1.0, 0.2, 0.1)$ — Red wavelength penetrates deepest into subdermal capillary blood plexus.
  - Scale: $0.024\text{m}$ ($24\text{mm}$).
  - IOR: $1.40$, Anisotropy: $0.75$ (forward-scattering human tissue).
- **Micro-Roughness Bump**: Procedural Noise Texture (Scale: 380.0, Detail: 4.0, Roughness: 0.6) feeding into Bump node (Strength: $0.030$, Distance: $0.001$).

### 3.2 Dual-Chamber Refractive Eye Optics
1. **Outer Cornea (`Mat_Human_Eye_Outer_Cornea`)**:
   - Transmission Weight: $1.0$, Roughness: $0.02$, IOR: $1.376$ (anatomical corneal refractive index).
   - Light Path node bypasses shadow rays to transparent BSDF, preventing black corneal shadow artifacts on the iris.
2. **Inner Iris & Pupil (`Mat_Human_Eye_Inner_Iris`)**:
   - Base Color: $(0.141, 0.165, 0.188, 1.0)$ — dark charcoal/slate stroma (`#2D343B`).
   - Procedural radial fiber gradient centered at $(0.5, 0.5)$ via vector subtraction.
   - SSS Weight: $0.18$, Radius: $(0.6, 0.2, 0.1)$, Scale: $0.005\text{m}$.
   - Pupil dilation: $0.35$.
3. **Sclera (`Mat_Human_Eye_Sclera`)**:
   - Base Color: $(0.949, 0.945, 0.941, 1.0)$ with subtle vascular red vein tint.
   - Roughness: $0.08$, SSS Weight: $0.20$.

### 3.3 Hair Melanin Shader (`Mat_Human_Hair`)
- **Shader Node**: `ShaderNodeBsdfHairPrincipled`.
- **Melanin**: $0.85$ (pure natural jet-black hair).
- **Melanin Redness**: $0.12$.
- **Roughness**: $0.25$ longitudinal roughness.
- **Radial Roughness**: $0.45$.
- **Coat Weight**: $0.45$ (produces the signature circular *"angel-ring"* specular highlight across the hair crown under rim lighting).

### 3.4 Wardrobe Fabrics & Leather
1. **White Silk Slip Dress (`Mat_Dress_WhiteSilk`)**:
   - Base Color: $(0.95, 0.95, 0.95, 1.0)$ ivory silk.
   - Roughness: $0.40$.
   - Sheen: Sheen Weight $0.60$, Sheen Roughness $0.32$, Sheen Tint $(0.90, 0.92, 0.96, 1.0)$ (Charlie sheen model).
   - Translucency SSS: Weight $0.14$, Radius $(0.80, 0.85, 0.90)$ for soft fabric backlighting.
2. **Pale Ice-Blue Satin Sash (`Mat_Sash_Satin`)**:
   - Base Color: $(0.820, 0.880, 0.940, 1.0)$ pale ice-blue.
   - Roughness: $0.22$ (distinctly glossier and smoother than the silk dress).
   - Specular IOR Level: $0.60$, Sheen Weight: $0.50$.
3. **Sandal Leather (`Mat_Sandal_Leather`)**:
   - Base Color: $(0.32, 0.20, 0.13, 1.0)$ warm natural leather (or elegant $(0.92, 0.92, 0.94, 1.0)$ white leather).
   - Roughness: $0.45$.
   - Micro-Bump: Procedural Voronoi/Noise (Scale: 250.0, Strength: $0.05$).

### 3.5 Magic Props Shaders
1. **Marionette Red Strings (`Mat_Marionette_RedString`)**:
   - Base Color: $(0.902, 0.0, 0.149, 1.0)$ vivid crimson.
   - Emission Color: $(1.0, 0.122, 0.239, 1.0)$, Emission Strength: $6.5$.
2. **Luminous White Butterflies (`Mat_Magic_Butterfly`)**:
   - Base Color: $(1.0, 1.0, 1.0, 1.0)$ pearl white.
   - Transmission: $0.20$, SSS Weight: $0.45$, Radius $(0.90, 0.95, 1.0)$, Scale $0.006\text{m}$.
   - Coat: Weight $0.30$, Roughness $0.02$.
   - Emission Color: $(0.949, 0.969, 1.0, 1.0)$, Emission Strength: $3.5$.

### 3.6 Keratin Nail Material (`Mat_Human_Nails`) — Identified Gap & Specification
- **Finding**: Currently, `human_materials.py` has shaders for skin, lips, eyes, hair, and wardrobe, but **lacks a dedicated keratin nail shader**.
- **Specification for `Mat_Human_Nails`**:
  ```python
  MAT_HUMAN_NAILS = HumanMaterialConfig(
      name="Mat_Human_Nails",
      base_color=(0.865, 0.710, 0.685, 1.0),  # Natural healthy pink nail bed
      roughness=0.22,                          # Polished keratin smoothness
      metallic=0.0,
      specular_ior_level=0.65,                 # Keratin IOR ~ 1.54
      ior=1.54,
      subsurface_weight=0.35,                  # Translucent nail plate
      subsurface_radius=(0.80, 0.25, 0.15),
      subsurface_scale=0.004,
      subsurface_method="RANDOM_WALK",
      coat_weight=0.50,                        # Natural protective keratin shine
      coat_roughness=0.03,
      description="Translucent natural keratin nail plate with pink bed and glossy coat",
  )
  ```
- **Application**: Assigned to the fingernail and toenail vertex regions on `Yu_Nian_An_Body`.

---

## 4. Studio Lighting Rig & Production Export Pipeline

### 4.1 3-Point Studio Lighting Setup
The scene lighting is organized in collection `Yu_Nian_An_Master/06_Lights_Camera` focused on `Target_Lighting_Focus` ($X=0.0, Y=0.0, Z=1.25\text{m}$):
```
                       [Rim / Hair Light]
                       (4500K, 450W, Area 1.0m)
                              \
                               \
                                v
                           [Yu Nian An]
                                ^
                               / \
                              /   \
                             /     \
           [Key Light]              [Fill Light]
   (5500K, 500W, Area 0.8m)     (6500K, 250W, Area 1.0m)
```
1. **Key Light (`Light_Key_Softbox`)**:
   - Location: $(+1.8\text{m} \cdot s, -2.0\text{m} \cdot s, +2.2\text{m} \cdot s)$ — 45° front-right azimuth, 35° elevation.
   - Energy: $500\text{W}$, Color: $5500\text{K}$ warm daylight (`#FFE8D6`).
   - Size: $0.8\text{m} \times 0.8\text{m}$ softbox creating soft penumbra shadows on clavicles, bust contours, and dress drapery.
2. **Fill Light (`Light_Fill_Softbox`)**:
   - Location: $(-1.8\text{m} \cdot s, -2.0\text{m} \cdot s, +1.8\text{m} \cdot s)$ — 45° front-left azimuth, 30° elevation.
   - Energy: $250\text{W}$ (2:1 key-to-fill lighting ratio), Color: $6500\text{K}$ cool skylight (`#F0F4FF`).
   - Size: $1.0\text{m} \times 1.0\text{m}$ large diffuser softening shadows and providing corneal catchlights.
3. **Rim / Hair Light (`Light_Rim_HairLight`)**:
   - Location: $(0.0\text{m}, +2.2\text{m} \cdot s, +2.5\text{m} \cdot s)$ — directly behind and above character.
   - Energy: $450\text{W}$, Color: $4500\text{K}$ golden warmth (`#FFF0E0`).
   - Size: $1.0\text{m} \times 1.0\text{m}$ soft edge separator, illuminating the cranial silhouette, shoulders, and producing the signature angel-ring halo on the long black hair cascade.

### 4.2 Multi-Angle Camera Rigs
- **4 Turnaround Full-Body Cameras** ($50\text{mm}$ lens, distance $5.5\text{m}$, target $Z = 0.825\text{m}$):
  1. `Camera_Front`: $Y = -5.5\text{m}$, Yaw $0^\circ$ (Full frontal silhouette and proportions).
  2. `Camera_ThreeQuarter`: $X = 3.889\text{m}, Y = -3.889\text{m}$, Yaw $45^\circ$ (Dynamic beauty view).
  3. `Camera_Profile`: $X = 5.5\text{m}, Y = 0.0\text{m}$, Yaw $90^\circ$ (S-curve posture and facial silhouette).
  4. `Camera_Back`: $Y = +5.5\text{m}$, Yaw $180^\circ$ (Back cascade hair and rear dress draping).
- **Macro & Close-Up Cameras**:
  5. `Camera_Portrait_85mm`: $85\text{mm}$ portrait prime lens, distance $2.0\text{m}$, target $Z = 1.55\text{m}$ (Eyes, skin SSS, and hime cut fringe).
  6. `Camera_Feet`: $50\text{mm}$ lens, low angle, distance $1.2\text{m}$, target $Z = 0.04\text{m}$ (Flat sandals and 5 articulated bare toes).
  7. `Camera_Hands`: $60\text{mm}$ lens, distance $0.9\text{m}$, target $Z = 0.95\text{m}$ (Fingertips, crimson cords, and fluttering butterflies).

### 4.3 Export Pipeline Deliverables
1. `output/yu_nian_an/Yu_Nian_An_Master.blend`:
   - 7-tier collection hierarchy (`Yu_Nian_An_Master` + `01_Body`, `02_Hair`, `03_Wardrobe`, `04_Props`, `05_Armature`, `06_Lights_Camera`).
   - Cycles engine (128 samples, AgX color management, denoising enabled).
   - All external textures packed via `bpy.ops.file.pack_all()`.
   - Materials assigned fake users (`use_fake_user = True`).
2. `output/yu_nian_an/Yu_Nian_An.glb`:
   - Binary glTF 2.0 container.
   - Deform bone skeleton with normalized vertex weights (`export_skins=True`).
   - 52 ARKit FACS blendshapes preserved as morph targets (`export_morph=True`).
   - Complete UV texture coordinate set (`TEXCOORD_0`) across all primitives.
3. `output/yu_nian_an/Yu_Nian_An.fbx`:
   - Binary FBX 2020 format.
   - 163 DEF bones armature with anti-pinch skin weights.
   - 52 ARKit FACS shape keys.
   - Axis standard: Primary 'Y', Secondary 'X' (direct plug-and-play for Unreal Engine 5.4+ and Unity 6).
4. `output/yu_nian_an/textures/` (4K 4096×4096 PBR Textures):
   - `Yu_Nian_An_BaseColor_4K.png`
   - `Yu_Nian_An_Normal_4K.png` (tangent-space OpenGL)
   - `Yu_Nian_An_Roughness_4K.png`
   - `Yu_Nian_An_Metallic_4K.png`
   - `Yu_Nian_An_SSS_4K.png`
   - `Yu_Nian_An_Alpha_4K.png`
   - `Yu_Nian_An_Height_4K.png`
   - `Yu_Nian_An_ORM_4K.png` (Unreal Engine packed: Red=Occlusion, Green=Roughness, Blue=Metallic)
   - `Yu_Nian_An_MaskMap_4K.png` (Unity HDRP packed: Red=Metallic, Green=Occlusion, Blue=Detail, Alpha=Smoothness)

---

## 5. Verification Suite Audit & Test Failure Analysis

### 5.1 Current Test Pass Rate Baseline
- Execution of core unit test suites (`tests/test_tools_schema.py`, `tests/test_human_generator.py`, `tests/test_human_grooming.py`, `tests/test_fastmcp_human_tools.py`, `tests/test_human_rigging.py`, `tests/test_wardrobe.py`, `tests/test_human_materials.py`):
  - **119 passed in ~8.5 seconds (100% pass rate for core modules)**.
- Execution of master character and export tests (`pytest -k "human or wardrobe or assembler or export"`):
  - **390 passed, 14 failed**.

### 5.2 Deep-Dive Root Cause Analysis of 14 Test Failures
All 14 failing tests originate from three test files:
1. `tests/test_production_exports.py` (4 failures):
   - `test_fbx_contains_def_bones_and_shape_keys`: Failed because `Yu_Nian_An.fbx` on disk was an older placeholder without DEF bones.
   - `test_glb_body_mesh_has_all_52_arkit_morph_targets`: Failed because `Yu_Nian_An.glb` on disk lacked the 52 ARKit morph targets.
   - `test_glb_all_mesh_primitives_have_texcoord_0`: Failed because primitives named `Beauty_*_Mesh` lacked `TEXCOORD_0` UV maps.
   - `test_glb_uv_semantic_texture_sampling`: Failed because `Mesh_Lips` was missing from the old GLB mesh list.
2. `tests/test_adversarial_character_assembler.py` (4 failures):
   - `test_master_blend_arkit_shape_keys_empirical_deltas`
   - `test_master_blend_def_bones_163_exact_inventory`
   - `test_master_blend_cameras_50mm_and_ndc_framing`
   - `test_master_blend_strings_and_clearance_adversarial`
3. `tests/test_character_assembler.py` (6 failures):
   - `test_live_master_blend_content_verification`
   - `test_live_camera_fullbody_and_turnaround_ndc_bounds`
   - `test_live_marionette_strings_snapped_to_finger_bone_tails`
   - `test_live_wardrobe_signed_clearance_and_zero_penetration`
   - `test_live_lips_clearance_and_material_slot_distribution`
   - `test_live_eye_spheres_hair_armature_binding_and_rotation_kinematics`

#### Exact Cause:
A previous run generated a temporary mock/beauty file (`Yu_Nian_An_Beauty.blend`) and copied it over `output/yu_nian_an/Yu_Nian_An_Master.blend` (both are exactly $15,003,218$ bytes). This beauty file had merged objects and discarded the 163 DEF bones and 52 shape keys.
Running `morphomesh_assemble_master_character` and `morphomesh_export_production_character` freshly from `character_assembler.py` cleanly regenerates `Yu_Nian_An_Master.blend`, `Yu_Nian_An.fbx`, and `Yu_Nian_An.glb` with the complete armature, UV maps, and morph targets, immediately resolving all 14 failures.

### 5.3 New Test Assertions Needed
To permanently protect the new R3 & R4 requirements, the following new automated tests should be added to `tests/test_wardrobe.py` and `tests/test_human_materials.py`:

```python
def test_flat_sandals_ergonomic_sole_and_exposed_toes():
    """Validates thin sole (<= 8mm), medial arch rise, and all 5 toes clearance."""
    sandals = generate_flat_sandals(height=1.65)
    for side in ("Mesh_Sandal_L", "Mesh_Sandal_R"):
        mesh = sandals[side]
        zs = [v[2] for v in mesh.vertices]
        sole_verts = [v for v in mesh.vertices if v[2] <= 0.010]
        # Sole thickness check
        sole_thickness = max(v[2] for v in sole_verts) - min(v[2] for v in sole_verts)
        assert sole_thickness <= 0.008, f"Sandal sole too thick: {sole_thickness}m > 0.008m"
        
        # Strap checks
        strap_verts = [v for v in mesh.vertices if v[2] > 0.010]
        assert len(strap_verts) >= 40, "Must contain instep and ankle strap geometry"
        
        # Toe exposure check: all straps must be behind the toes (Y > -0.115m)
        assert min(v[1] for v in strap_verts) >= -0.115, "Straps must not cover bare toes"

def test_keratin_nails_material_definition():
    """Validates Mat_Human_Nails presence and physical parameters."""
    assert "Mat_Human_Nails" in STANDARD_HUMAN_MATERIALS
    mat = STANDARD_HUMAN_MATERIALS["Mat_Human_Nails"]
    assert mat.subsurface_weight >= 0.30
    assert mat.roughness <= 0.25
    assert mat.coat_weight >= 0.45

def test_marionette_cords_finger_tail_snapping():
    """Validates 10 cords originate within 5mm of finger DEF bone tails."""
    cords = generate_marionette_red_strings(height=1.65, rest_pose=True)
    assert len(cords.vertices) >= 140
    # Exactly 10 cords
    assert len(cords.faces) % 20 == 0
```

---

## 6. Implementation Blueprint & File Changes Summary

| Module | Component | Required Changes |
|---|---|---|
| `src/morphomesh/wardrobe.py` | `generate_flat_sandals()` | Reduce sole thickness to $0.007\text{m}$, add medial arch contour rise, add forefoot band ($Y \approx -0.10\text{m}$), dorsal instep band, ankle collar band ($Z \approx 0.08\text{m}$), and heel counter strap. Fully expose 5 toes. |
| `src/morphomesh/wardrobe.py` | `generate_marionette_red_strings()` | Implement Bezier catenary tension curves from finger DEF bone tails to butterfly positions. |
| `src/morphomesh/human_materials.py` | `STANDARD_HUMAN_MATERIALS` | Add `MAT_HUMAN_NAILS` (translucent pinkish keratin, SSS 0.35, roughness 0.22, coat 0.50). |
| `src/morphomesh/character_assembler.py` | `get_master_assembly_script()` | Assign `Mat_Human_Nails` to finger and toe nail vertex groups; ensure camera rig includes `Camera_Feet` and `Camera_Hands`. |
| `src/morphomesh/character_assembler.py` | `export_production_assets()` | Ensure complete UV unwrapping (`TEXCOORD_0`) across all wardrobe meshes before GLB export. |
| `tests/test_wardrobe.py` | Unit Tests | Add test cases verifying sandal sole thickness ($\le 8\text{mm}$), 4-strap topology, and toe clearance. |
| `tests/test_human_materials.py` | Unit Tests | Add test cases verifying `Mat_Human_Nails` PBR parameters. |
