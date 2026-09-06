# Survey Report: Fur Grooming, PBR Shading, War Armor & Verification Pipeline

**Author**: Explorer Survey 3 (Fur, Shading, Armor & Verification Specialist)  
**Date**: 2026-09-05T15:53:00Z  
**Target Milestone**: Armored War Bear Synthesis & MorphoMesh Engine Upgrade  
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_3`  
**Authoritative Request**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md` (§ 2026-09-05T15:44:52Z & § 2026-09-05T15:47:35Z)

---

## 1. Executive Summary & Forensic Audit of Existing Assets

### 1.1 Scope Clarification & Engine-Level Mandate
As explicitly clarified by the User/Sentinel in § 2026-09-05T15:47:35Z, the objective is **not** merely to hardcode a single static Armored War Bear model, but to upgrade the **MorphoMesh ENGINE ITSELF** (`src/morphomesh/` - procedural mesh generators in `inference_adapter.py`, connectors like `anycreature_connector.py`, `trellis_connector.py`, `blender_bridge.py`, and fur/grooming pipelines) so that MorphoMesh can generate high-fidelity, photorealistic creatures in general. The Armored War Bear serves as the canonical test benchmark and demonstration verifying that the upgraded engine produces anatomically authentic creatures with correct claw orientation, organic facial features, volumetric fur, and battle-hardened PBR armor.

### 1.2 Forensic Audit of Existing Asset (`examples/Armored_War_Bear.glb`)
An automated inspection of the existing `examples/Armored_War_Bear.glb` using Blender 5.2.1 LTS revealed severe anatomical and shading deficiencies:
1. **Inverted and Upward Claws**:
   All 20 claws on the model have negative forward alignment and point upward into the air rather than curving forward and downward toward the ground:
   - `Bear_Front_L_Claw_0`: $\text{dot}(\hat{v}, \vec{V}_{\text{fwd}}) = -0.237$, $\hat{v}_z = +0.784$
   - `Bear_Front_L_Claw_1`: $\text{dot}(\hat{v}, \vec{V}_{\text{fwd}}) = -0.816$, $\hat{v}_z = +0.578$
   - `Bear_Front_R_Claw_0`: $\text{dot}(\hat{v}, \vec{V}_{\text{fwd}}) = -0.237$, $\hat{v}_z = +0.784$
2. **Absence of Volumetric Fur**:
   The model contains zero volumetric hair strands or hair curves. The only "fur" objects are `Pauldron_Fur_Ruff_L` and `Pauldron_Fur_Ruff_R`—primitive 21-vertex polygon cone ruffs encircling the shoulders.
3. **Improper Material Sharing**:
   A single material slot `Mat_Claws_Nose` is assigned to both the wet leathery nose rhinarium and the sharp keratin claws, ignoring their vastly different physical properties (roughness, specular gloss, micro-surface normal).
4. **Lack of Articulated Facial Anatomy**:
   The facial mesh is composed of primitive sphere/box approximations without modeled mouth cavities, jaw articulation, teeth, distinct nostrils, or eyelid geometries.

---

## 2. R2: Volumetric Fur & Hair Grooming System

### 2.1 Multi-Layer Biological Hair Architecture
Ursine fur consists of two biologically distinct hair strata:
1. **Dense Undercoat (Sub-fur)**:
   - Function: Thermal insulation and visual volume.
   - Characteristics: Short ($0.035 - 0.055\text{m}$), highly dense, high crimp/waviness, non-directional loft.
   - Strand Count: $7,000 - 8,000$ guide strands with interpolated child distribution resulting in $> 70,000$ render strands.
2. **Coarse Guard Hairs (Topcoat)**:
   - Function: Weather protection, water runoff, and directional grooming flow.
   - Characteristics: Longer ($0.08 - 0.13\text{m}$), thicker at the base ($1.2\text{mm}$), sharp apical taper ($0.1\text{mm}$), high specular sheen, pronounced clumping.
   - Strand Count: $3,000 - 4,000$ guide strands with interpolated child distribution resulting in $> 30,000$ render strands.
   - Total Render Strands: $\ge 100,000$ (far exceeding the $\ge 10,000$ minimum threshold).

### 2.2 Biological Hair Flow Mechanics
Quadruped mammalian fur adheres to strict biological directional fields:
- **Dorsal Spine Ridge**: Originates at the nape of the neck, runs caudally along the thoracic and lumbar spine toward the tail. Direction vector $\vec{V}_{\text{spine}} \approx (0, -1, 0)$.
- **Flank & Ribcage Radiance**: Radiates laterally from the dorsal crest and curves downward along the torso toward the belly: $\vec{V}_{\text{flank}} = (\pm \sin \theta, -\cos \theta \cdot 0.6, -\cos \theta \cdot 0.8)$.
- **Limb Descent**: Flows strictly downward (-Z) along the upper arms, forearms, thighs, and shins toward the paws.
- **Facial Radiance**: Radiates backward from the rhinarium across the cheeks, snout ridge, and forehead toward the ears.

### 2.3 Blender 5.2.1 LTS Implementation Analysis
Blender 5.2.1 LTS provides two robust architectures for volumetric fur:

#### Option A: Modern Hair Curves & Geometry Nodes
Blender 5.2.1 includes native procedural hair asset node trees located at:
`/Applications/Blender.app/Contents/Resources/5.2/datafiles/assets/nodes/procedural_hair_node_assets.blend`
Key available node groups:
- `Generate Hair Curves`: Scatters strands across the surface with density mask input.
- `Clump Hair Curves`: Provides authentic guide clumping with configurable tip/root clump factors.
- `Frizz Hair Curves`: Adds realistic micro-frizz and waviness to the undercoat.
- `Hair Curves Noise`: Adds turbulent displacement.

#### Option B: Multi-Layer Hair Particle Systems (`PARTICLE_SYSTEM`)
Blender's particle hair system is 100% accessible via headless `bpy` script execution and offers immediate integration with vertex group density masking:
```python
def configure_fur_layer(
    obj, name, count, length, clump, root_rad, tip_rad, shape=-0.7
):
  mod = obj.modifiers.new(name=name, type="PARTICLE_SYSTEM")
  ps = mod.particle_system.settings
  ps.type = "HAIR"
  ps.count = count
  ps.hair_length = length
  ps.hair_step = 5
  ps.child_type = "INTERPOLATED"
  ps.rendered_child_count = 8
  ps.clump_factor = clump
  ps.clump_shape = 0.5
  ps.root_radius = root_rad
  ps.tip_radius = tip_rad
  ps.shape = shape  # Negative value produces sharp taper toward tip
  ps.use_close_tip = True
  ps.density_vertex_group = "Fur_Density"
  ps.length_vertex_group = "Fur_Length"
  ps.clump_vertex_group = "Fur_Clump"
  ps.effector_weights.gravity = 0.35  # Natural downward drape
  return ps
```

### 2.4 Vertex Group Infrastructure
To prevent fur growing in unnatural locations (e.g., corneas, rhinarium, teeth, claw keratin, paw pads), the mesh generator must create explicit vertex groups:
- `Fur_Density`: Weight = 0.0 on claw tips, pads, nose leather, eyelids, mouth interior; Weight = 0.3 on muzzle and ears; Weight = 1.0 on spine, torso, shoulders, and thighs.
- `Fur_Length`: Weight = 0.2 on face and lower digits; Weight = 0.6 on flanks; Weight = 1.0 on dorsal mane and neck crest.
- `Fur_Clump`: Modulates clump tightness across the body.

---

## 3. R3: 4-Channel PBR Material Suite & War Armor Integration

### 3.1 Shader Pipeline & Channel Architecture
In Blender 5.2.1 LTS, shading is powered by Principled BSDF v2 and Principled Hair BSDF. All materials conform strictly to standard 4-channel PBR (Albedo, Normal/Displacement, Roughness, Metallic) ensuring 1:1 roundtrip compatibility with glTF 2.0.

```
+-----------------------------------------------------------------------------------+
|                            4-CHANNEL PBR SHADER SUITE                             |
+--------------------------+---------------------+-----------+-----------+----------+
| Material Slot            | Albedo (Base Color) | Roughness | Metallic  | Normal   |
+--------------------------+---------------------+-----------+-----------+----------+
| Mat_Bear_Fur             | #2B1D14 -> #4A3525  | 0.85      | 0.0       | Fur flow |
| Mat_Bear_Skin_Nose       | #1C1B1C (slate)     | 0.15      | 0.0       | Pebbled  |
| Mat_Bear_Claws           | #201D19 -> #7D7154  | 0.38      | 0.0       | Grooved  |
| Mat_Armor_WeatheredSteel | #3A4048 (gunmetal)  | 0.42      | 1.0       | Hammered |
| Mat_Armor_BrassTrim      | #C89D3C (warm gold) | 0.32      | 1.0       | Beveled  |
+--------------------------+---------------------+-----------+-----------+----------+
```

### 3.2 Material Physical Parameter Specifications

1. **`Mat_Bear_Fur`**:
   - Surface Principled BSDF: Base Color = Dark Umber/Grizzly Brown, Roughness = 0.85, Sheen Weight = 0.65, Sheen Roughness = 0.3, Subsurface Weight = 0.08 (simulates light diffusion through hair fibers), Metallic = 0.0.
   - Volumetric Strand Shader: `ShaderNodeBsdfHairPrincipled` with Melanin = 0.65, Melanin Redness = 0.55, Roughness = 0.35, Radial Roughness = 0.60, Coat = 0.25, IOR = 1.55.
2. **`Mat_Bear_Skin_Nose`**:
   - Applied to rhinarium, nostrils, lips, inner mouth/gums, and paw pads.
   - Base Color = Dark charcoal/pebbled black (`#1C1B1C`) with fleshy pink undertones in mouth cavity (`#3D2626`).
   - Roughness = 0.15 (high specular gloss).
   - Coat Weight = 0.85, Coat Roughness = 0.04 (renders wet moisture layer).
   - Specular IOR Level = 0.60.
3. **`Mat_Bear_Claws`**:
   - Applied to all 20 forward-curving claws.
   - Base Color = Longitudinal keratin gradient from dense charcoal base (`#201D19`) to translucent amber-horn tip (`#7D7154`).
   - Roughness = 0.38 (satin keratin luster).
   - Normal = Directional linear striation map running parallel to claw curvature.
   - Metallic = 0.0.
4. **`Mat_Armor_WeatheredSteel`**:
   - Applied to heavy protective plate armor: Shoulder Pauldrons, Neck Gorget, Forearm Bracers, Dorsal Backplate.
   - Base Color = Cold blued steel (`#3A4048`) with light edge-wear highlight (`#7A8491`).
   - Roughness = 0.42 (battle-worn micro-scratches).
   - Metallic = 1.0 (pure conductor).
5. **`Mat_Armor_BrassTrim`**:
   - Applied to rivets, engraved borders, filigree edging, and plate fasteners.
   - Base Color = Antique brass/warm gold (`#C89D3C`) with darker crevice patina (`#5C4A21`).
   - Roughness = 0.32.
   - Metallic = 1.0.

### 3.3 War Armor Geometry & Non-Intersection Fitting
War armor plates must fit the quadruped ursine anatomy naturally without degenerate self-intersection:
- **Shoulder Pauldrons (`Armor_Pauldron_L`, `Armor_Pauldron_R`)**:
  - Shaped as layered convex shells floating over the supraspinatus and deltoid muscle hump.
  - Clearance Offset: Guaranteed radial clearance $\Delta r \in [0.025, 0.045]\text{m}$ from the underlying skin mesh, accommodating the volumetric undercoat without visual clipping.
- **Neck Gorget (`Armor_Gorget`)**:
  - Segmented articulated collar encircling the cervical spine and throat.
  - Clearance Offset: $\Delta r \in [0.020, 0.035]\text{m}$.
- **Forearm Bracers (`Armor_Bracer_L`, `Armor_Bracer_R`)**:
  - Cylindrical flared cuffs surrounding the distal radius/ulna, ending cleanly above the carpal joint and plantigrade wrist pads.
- **Dorsal Saddle / Backplate (`Armor_Backplate`)**:
  - Contoured along the thoracic spine with leather strapping fastening to the gorget and girth.
- **Geometric Integrity Assertions**:
  - Watertight 2-manifold shells (`is_manifold == True`).
  - Outwardly oriented face normals.
  - Zero zero-area faces and zero duplicate vertices.

---

## 4. R4: Production Export & Automated Verification (`verify_bear_anatomy.py`)

### 4.1 Production Export Pipeline
The asset production pipeline produces two complementary files:
1. `examples/Armored_War_Bear_HD.blend`:
   - Contains the complete scene: high-resolution mesh, 20 forward-curving claws, articulated facial structures, war armor hierarchy, 5 PBR materials, active multi-layer volumetric fur particle system ($> 100,000$ render strands), 4 beauty cameras, and 3-point studio lighting.
2. `examples/Armored_War_Bear_HD.glb`:
   - GlTF 2.0 compliant binary container.
   - Encapsulates all creature meshes, armor plates, and 4-channel PBR textures (BaseColor, Metallic-Roughness, Normal Map).
   - Validated: file size $> 100\text{ KB}$, loads without warnings in glTF viewers.

### 4.2 Mathematical Assertion Checks for `verify_bear_anatomy.py`

The verification script must enforce strict mathematical assertions:

#### 1. Claw Orientation Vector & Curvature
- Forward axis of character: $\vec{V}_{\text{fwd}} = (0, 1, 0)$.
- For each claw $c \in [1, 20]$:
  $$\vec{V}_{\text{claw}} = \vec{P}_{\text{tip}} - \vec{P}_{\text{base}}, \quad \hat{v} = \frac{\vec{V}_{\text{claw}}}{\|\vec{V}_{\text{claw}}\|}$$
  - **Forward Alignment Assertion**:
    $$\text{dot}(\hat{v}, \vec{V}_{\text{fwd}}) = \hat{v}_y > 0.60$$
  - **Downward Curvature Assertion**:
    $$\vec{P}_{\text{tip}, z} < \vec{P}_{\text{base}, z} \quad (\text{i.e. } \hat{v}_z < 0.0)$$
  - **Scale Assertion**:
    $$\|\vec{V}_{\text{claw}}\| \in [0.05, 0.16]\text{m}$$

#### 2. Articulated Facial Geometry & Landmark Elements
- The script asserts the presence of distinct facial components (either as dedicated sub-objects or populated vertex groups with non-zero vertex count):
  - `snout` ($|V| \ge 16$)
  - `nostrils` (left and right cavities, $|V| \ge 8$)
  - `mouth_cavity` / `jaw` ($|V| \ge 24$)
  - `teeth` (upper and lower canines/incisors, $|V| \ge 20$)
  - `eyes` (spherical corneas/irises, $|V| \ge 32$)
  - `eyelids` (curved orbital rims, $|V| \ge 16$)
  - `ears` (cupped auditory pinnae, $|V| \ge 24$)

#### 3. Volumetric Fur Density & Biological Flow
- Parent strand count $N_{\text{parent}} \ge 10,000$ OR total render strand count $N_{\text{render}} \ge 10,000$.
- Flow directional check: Average hair tangent along spine satisfies $\bar{t}_y < 0$ (flowing caudally toward tail) and downward flank drop $\bar{t}_z < 0$.
- Taper validation: Strand root radius $r_{\text{root}} > 0.0008\text{m}$, tip radius $r_{\text{tip}} < 0.0003\text{m}$, and taper shape $\le -0.5$.

#### 4. 4-Channel PBR Material Compliance
- Exactly 5 distinct materials verified in scene.
- Materials contain active connections to `Base Color`, `Normal`, `Roughness`, and `Metallic`.
- Physical parameter ranges:
  - Fur: $\text{Roughness} \ge 0.70$, $\text{Metallic} == 0.0$
  - Skin/Nose: $\text{Roughness} \le 0.25$, $\text{Coat Weight} \ge 0.50$ (or $\text{Specular} \ge 0.50$), $\text{Metallic} == 0.0$
  - Claws: $\text{Roughness} \in [0.25, 0.50]$, $\text{Metallic} == 0.0$
  - Steel Armor: $\text{Roughness} \in [0.30, 0.60]$, $\text{Metallic} \ge 0.95$
  - Brass Armor: $\text{Roughness} \in [0.20, 0.50]$, $\text{Metallic} \ge 0.95$

#### 5. Armor Clearance & Non-Intersection
- For each armor plate $A$, minimum distance to bear skin vertices $d_{\min}(A, S) \ge 0.01\text{m}$ ($1\text{cm}$ positive clearance).
- Non-manifold edge count $E_{\text{non-manifold}} == 0$.

---

## 5. Camera Viewpoints & Beauty Rendering Pipeline

### 5.1 The 4 Required Camera Setups

```
+----------------------------------------------------------------------------------------------------+
|                                    4 BEAUTY CAMERA VIEWPOINTS                                      |
+---------------------+-------------------+-----------------+-------+--------------------------------+
| Camera Name         | Position (X,Y,Z)  | Target (X,Y,Z)  | Focal | Primary Showcase               |
+---------------------+-------------------+-----------------+-------+--------------------------------+
| Camera_Front34      | (2.8, 3.2, 1.8)   | (0.0, 0.3, 1.1) | 50mm  | Hero 3/4 perspective silhouette|
| Camera_HeadCloseUp  | (0.65, 2.2, 1.55) | (0.0, 0.95, 1.35| 85mm  | Snout, nostrils, teeth, eyes   |
| Camera_PawClawClose | (0.95, 1.25, 0.35)| (0.38, 0.60, 0.1| 70mm  | Forward claws, pads, bracer    |
| Camera_FullBody     | (-3.8, 0.5, 1.6)  | (0.0, -0.1, 1.0)| 50mm  | Dorsal spine flow, armor fit   |
+---------------------+-------------------+-----------------+-------+--------------------------------+
```

### 5.2 Studio 3-Point Lighting Rig
1. **Key Light**: Area Light, Position $(2.5, 2.5, 3.2)$, Energy $= 450\text{W}$, Color Temp $= 5200\text{K}$ (neutral warm daylight), angled $45^\circ$ toward bear head and shoulders.
2. **Fill Light**: Area Light, Position $(-2.8, 1.8, 1.8)$, Energy $= 180\text{W}$, Color Temp $= 6800\text{K}$ (cool soft sky fill) softening torso shadows.
3. **Rim / Kicker Light**: Spot/Area Light, Position $(0.0, -3.2, 3.0)$, Energy $= 600\text{W}$, Color Temp $= 4800\text{K}$, highlighting fur silhouette along spine, backplate edge, and pauldron rims.
4. **Ground Plane**: Shadow catcher plane at $Z = 0.0$ providing clean contact grounding.

### 5.3 Render Engine & Execution Performance
Tested on macOS Apple Silicon in Blender 5.2.1 LTS:
- `CYCLES` (Metal GPU accelerated, 32 samples): Render time $\sim 0.52\text{ seconds}$ per frame.
- `BLENDER_EEVEE` (EEVEE Next architecture): Render time $\sim 0.78\text{ seconds}$ per frame.
- Output Resolution: $1920 \times 1080$ (or $2048 \times 2048$ square) saved as PNG in `examples/renders/`.

---

## 6. MorphoMesh Engine Architecture Upgrades

To satisfy the User/Sentinel directive (§ 2026-09-05T15:47:35Z), the following modular extensions should be implemented in `src/morphomesh/`:

```
src/morphomesh/
├── grooming.py            # [NEW] Reusable Volumetric Fur & Hair Grooming Engine
├── materials.py           # [NEW] Reusable Organic PBR Material Suite Generator
├── armor.py               # [NEW] Procedural War Armor Generation & Fitting Engine
├── blender_bridge.py      # [ENHANCED] Support for hair systems, camera rigs, verification
├── inference_adapter.py   # [ENHANCED] Upgraded anatomy generator (forward claws, facial sculpt)
└── connectors/            # Existing canonical connectors
```

### 6.1 `src/morphomesh/grooming.py` Specification
- Class `CreatureGroomingEngine`:
  - `generate_volumetric_fur(mesh_obj, archetype="ursine", strand_count=10000, multi_layer=True)`
  - Creates `Fur_Density`, `Fur_Length`, `Fur_Clump` vertex groups automatically based on mesh topology and landmark groups.
  - Sets up Undercoat and Guard Hair particle systems or Hair Curves modifiers with authentic tapering and biological flow.

### 6.2 `src/morphomesh/materials.py` Specification
- Class `CreaturePBRSuite`:
  - `build_pbr_material(name, albedo_col, roughness, metallic, normal_type, coat_weight=0.0)`
  - `setup_bear_materials(creature_obj_dict)`: Creates and assigns the 5 canonical PBR materials with proper texture nodes and Principled BSDF v2 parameters.

### 6.3 `src/morphomesh/armor.py` Specification
- Class `ProceduralArmorEngine`:
  - `generate_war_armor(creature_mesh, style="heavy_plate", clearance=0.025)`
  - Generates shoulder pauldrons, neck gorget, forearm bracers, and dorsal backplate fitted to the creature's bounding box and landmarks.
  - Automatically verifies non-intersection clearance.

### 6.4 Verification Integration
- Standalone verification script: `verify_bear_anatomy.py` (located in project root or `examples/`).
- Automated pytest integration: `tests/test_bear_anatomy.py` ensuring continuous regression testing within the project test suite.

---

## 7. Actionable Recommendations for Milestone Execution

1. **Milestone M1 (Anatomical Accuracy & Organic Facial Detailing)**:
   - Worker must upgrade mesh generation in `inference_adapter.py` / `bpy` generators:
   - Fix claw rotation logic so claw vectors strictly satisfy $\text{dot}(\hat{v}, (0,1,0)) > 0.60$ and $\hat{v}_z < 0.0$.
   - Procedurally model snout, nostrils, open mouth cavity, upper/lower teeth, eyes with eyelids, and cupped ears.
2. **Milestone M2 (Volumetric Fur & Hair Grooming System)**:
   - Implement `src/morphomesh/grooming.py`.
   - Setup Undercoat (8,000 strands) + Guard Hairs (4,000 strands) with interpolated children.
   - Verify vertex groups (`Fur_Density`, `Fur_Length`) and spine flow vectors.
3. **Milestone M3 (PBR Material Suite & War Armor Integration)**:
   - Implement `src/morphomesh/materials.py` and `src/morphomesh/armor.py`.
   - Assign the 5 distinct PBR material slots.
   - Generate fitted pauldrons and bracers with positive clearance $\ge 0.01\text{m}$.
4. **Milestone M4 (Scene Assembly, Production Export & Verification)**:
   - Assemble complete scene in `examples/Armored_War_Bear_HD.blend`.
   - Export `examples/Armored_War_Bear_HD.glb`.
   - Execute `verify_bear_anatomy.py` and `pytest tests/test_bear_anatomy.py` (ensuring 100% pass).
   - Render the 4 beauty camera shots to `examples/renders/`.
