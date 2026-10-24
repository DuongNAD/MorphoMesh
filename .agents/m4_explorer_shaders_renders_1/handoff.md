# Handoff Report: Cycles Shaders & Multi-Angle Beauty Renders Strategy (Features 16 & 17)

**Author**: M4 Explorer 2 (Cycles Shaders & Multi-Angle Beauty Renders Strategy)  
**Target Milestone**: M4 (Shaders, Verification, Tests & Exports)  
**Related Features**: Feature 16 (Cycles Principled BSDF v2 Random Walk SSS) & Feature 17 (Cycles AgX Studio Lighting & Beauty Renders)  
**Status**: COMPLETE / HARD HANDOFF

---

## 1. Observation

Direct code examination and empirical test verification revealed the following observations across the MorphoMesh codebase:

### 1.1 Materials & Shaders in `src/morphomesh/human_materials.py`
1. **Skin Shader Configuration**:
   - In `src/morphomesh/human_materials.py` (lines 89–109):
     ```python
     MAT_HUMAN_SKIN_SSS = HumanMaterialConfig(
         name="Mat_Human_Skin_SSS",
         base_color=(0.918, 0.791, 0.723, 1.0),
         roughness=0.35,
         subsurface_weight=0.28,
         subsurface_radius=(1.0, 0.2, 0.1),
         subsurface_scale=0.024,
         subsurface_method="RANDOM_WALK",
         subsurface_ior=1.40,
         subsurface_anisotropy=0.75,
         bump_strength=0.030,
         bump_scale=380.0,
     )
     ```
   - Current `subsurface_radius` is $(1.0, 0.2, 0.1)$ and `subsurface_scale` is $0.024$ ($24\text{ mm}$). This causes an overly deep, waxy scattering radius that washes out fine nasal, eyelid, and facial contours. The required specification is warm epidermal radius $(1.0, 0.45, 0.25)$ and scale $0.002$ ($2.0\text{ mm}$).
   - Current `subsurface_method` is set to `"RANDOM_WALK"`. Blender 4.0+ LTS supports `"RANDOM_WALK_SKIN"`, which implements true dual-layer skin scattering.
2. **Cornea Shadow Bypass**:
   - In `src/morphomesh/human_materials.py` (lines 390–412), the cornea shader correctly implements a `ShaderNodeLightPath` transparent shadow bypass:
     ```python
     light_path = nodes.new(type="ShaderNodeLightPath")
     transparent_bsdf = nodes.new(type="ShaderNodeBsdfTransparent")
     mix_shader = nodes.new(type="ShaderNodeMixShader")
     links.new(light_path.outputs["Is Shadow Ray"], mix_shader.inputs["Fac"])
     links.new(bsdf.outputs["BSDF"], mix_shader.inputs[1])
     links.new(transparent_bsdf.outputs["BSDF"], mix_shader.inputs[2])
     links.new(mix_shader.outputs["Shader"], out_node.inputs["Surface"])
     ```
   - However, in `scripts/build_ultimate_yu_nian_an.py` (lines 109–124):
     ```python
     mat_cornea = new_mat("Mat_Human_Eye_Outer_Cornea")
     ...
     bsdf_cornea = nodes.new("ShaderNodeBsdfPrincipled")
     ...
     links.new(bsdf_cornea.outputs["BSDF"], out_n.inputs["Surface"])
     ```
     The shadow bypass is completely missing from `scripts/build_ultimate_yu_nian_an.py`! As a result, in Cycles raytracing, the outer cornea dome casts an opaque dark shadow directly over the inner iris dish, making the eyes appear unnaturally black/dead.
3. **Inner Iris & Radial Stroma**:
   - In `src/morphomesh/human_materials.py` (lines 499–544), `_build_inner_iris_node_tree` centers UV coordinates via `ShaderNodeVectorMath` (`SUBTRACT (0.5, 0.5, 0.0)`) and `LENGTH`, followed by a 7-stop `ColorRamp` mapping pupil, collarette, slate-grey stroma, limbal ring, and sclera edge.
   - In `scripts/build_ultimate_yu_nian_an.py` (lines 126–136), `mat_iris` is implemented as a plain solid `(0.16, 0.24, 0.22, 1.0)` base color without stroma texture nodes or radial gradient.
4. **Silk & Satin Fabrics**:
   - In `src/morphomesh/human_materials.py`:
     - `MAT_DRESS_WHITESILK` (line 193): `roughness=0.40`, `sheen_weight=0.60`. Required: `roughness=0.25`, `sheen_weight=0.60`.
     - `MAT_SASH_SATIN` (line 271): `roughness=0.32`, `sheen_weight=0.50`, `metallic=0.0`. Required: metallic gloss (`metallic=0.08`), `specular_ior_level=0.75`, `roughness=0.18`, high specular sheen (`sheen_weight=0.85-1.0`).
   - In `scripts/build_ultimate_yu_nian_an.py`:
     - Line 185: `bsdf_dress.inputs["Sheen Weight"].default_value = 0.90`, `Roughness = 0.32`.
     - Line 201: `bsdf_sash.inputs["Sheen Weight"].default_value = 1.0`, `Roughness = 0.18`, but missing `metallic` and high `specular_ior_level`.
5. **Prop Emission**:
   - In `scripts/build_ultimate_yu_nian_an.py`:
     - Line 228: `bsdf_str.inputs["Emission Strength"].default_value = 4.0`. Required: `6.5`.
     - Line 243: `bsdf_bf.inputs["Emission Strength"].default_value = 2.8`. Required: `3.2`.

### 1.2 Studio Lighting & Camera Rig in `camera_rig.py` and `build_ultimate_yu_nian_an.py`
1. **Studio Lighting**:
   - `src/morphomesh/character_assembler.py` (lines 1389–1416) contains an accurate mathematical implementation of `kelvin_to_rgb(kelvin)`.
   - `scripts/build_ultimate_yu_nian_an.py` (lines 1729–1731) uses hardcoded approximate RGB values:
     ```python
     add_light("Light_Key_Softbox", (1.2, -2.0, 1.8), (1.0, 0.97, 0.94), 110.0, 1.8)
     add_light("Light_Fill_Softbox", (-1.3, -1.8, 1.4), (0.92, 0.96, 1.0), 55.0, 2.0)
     add_light("Light_Rim_HairLight", (-0.4, 1.5, 2.0), (1.0, 0.97, 0.94), 100.0, 1.5)
     ```
     These do not adhere strictly to the 5500K Key, 6500K Fill, and 4500K Rim color temperatures.
2. **Color Management Look**:
   - In `scripts/build_ultimate_yu_nian_an.py` (line 1803):
     ```python
     scene.view_settings.view_transform = 'AgX'
     ```
     `scene.view_settings.look` is not configured, leaving it at default `'None'`, which lacks the punchy, high-contrast dynamic curve required for high-end beauty rendering.
3. **Canonical Beauty Renders**:
   - `scripts/build_ultimate_yu_nian_an.py` (lines 1808–1835) saves arbitrary audit renders:
     - `output/yu_nian_an/master_portrait_clean.png`
     - `output/yu_nian_an/audit_face_closeup.png`
     - `output/yu_nian_an/audit_head_render.png`
     - `output/yu_nian_an/master_fullbody_clean.png`
   - It does NOT output to `output/yu_nian_an/renders/` and completely lacks the 5 canonical beauty viewpoints:
     1. Front View (`output/yu_nian_an/renders/beauty_front.png`)
     2. Three-Quarter Perspective View (`output/yu_nian_an/renders/beauty_three_quarter.png`)
     3. Side Profile View (`output/yu_nian_an/renders/beauty_side.png`)
     4. Back View (`output/yu_nian_an/renders/beauty_back.png`)
     5. Head/Portrait Close-Up View (`output/yu_nian_an/renders/beauty_close_up.png`)

### 1.3 Test Suite Invariants
- `tests/test_human_materials.py` line 66 explicitly tests:
  `assert cfg.subsurface_radius == (1.0, 0.2, 0.1)`
- `tests/test_human_materials.py` line 113–114 explicitly tests:
  `assert dress_cfg.sheen_weight == 0.60`
  `assert dress_cfg.roughness == 0.40`
- Therefore, changing `MAT_HUMAN_SKIN_SSS` and `MAT_DRESS_WHITESILK` directly in `src/morphomesh/human_materials.py` requires updating the corresponding test assertions in `tests/test_human_materials.py` under Feature 19 (Test Suite Remediation).

---

## 2. Logic Chain

From the observations above, we establish a 5-step deduction to the target state:

1. **Skin Realism & SSS Scale**:
   - Observation: Human skin translucency occurs in the upper $1.5\text{ mm}$ to $2.5\text{ mm}$ dermis. The current $24\text{ mm}$ scale causes light to scatter across entire facial features, smoothing out nose bridges and eyelids into an artificial wax look.
   - Deduction: Setting `Subsurface Scale = 0.002` ($2.0\text{ mm}$) and warm epidermal radius $(1.0, 0.45, 0.25)$ (higher red penetration, medium green, shallow blue) with `'RANDOM_WALK_SKIN'` preserves sharp micro-geometry while creating authentic translucent warmth around the nostrils, ears, and fingers.
2. **Dual-Chamber Refraction & Shadow Rays**:
   - Observation: In `build_ultimate_yu_nian_an.py`, the cornea shader connects `bsdf_cornea` directly to output surface. In Cycles, glass refracts light and casts dense opaque shadow rays unless caustics are sampled or shadows are bypassed.
   - Deduction: Introducing `ShaderNodeLightPath` with `Is Shadow Ray` controlling a `ShaderNodeMixShader` between refractive Principled BSDF and 100% `ShaderNodeBsdfTransparent` allows light rays to illuminate the inner iris while camera and glossy reflection rays see the shiny, refractive cornea.
3. **Inner Iris Stroma & Radial Fiber Alignment**:
   - Observation: Yu Nian An's melancholy aesthetic relies on deep, detailed slate-grey eyes. A flat diffuse color makes the eyes look painted-on.
   - Deduction: Mapping procedural radial stroma coordinates centered at $(0.5, 0.5)$ via vector subtraction and vector length into a 6-stop ColorRamp creates an authentic dark pupil core ($[0.0, 0.16]$), slate-grey stroma fibers ($[0.22, 0.36]$), sharp dark limbal ring ($[0.36, 0.42]$), and bright sclera edge ($[0.42, 0.65]$).
4. **Studio Lighting Colorimetry**:
   - Observation: Accurate photographic studio lighting relies on correlated color temperature (CCT) contrast.
   - Deduction:
     - Key Light ($5500\text{ K}$): Planckian RGB $(1.0, 0.938, 0.865)$, $120\text{ W}$, Area size $1.8\text{m}$, placed at $45^\circ$ front-right ($1.8, -2.0, 2.2$) creates warm directional modeling.
     - Fill Light ($6500\text{ K}$): Daylight D65 RGB $(0.95, 0.98, 1.00)$, $60\text{ W}$, Area size $2.2\text{m}$, placed at $-45^\circ$ front-left ($-1.8, -1.9, 1.6$) softly lifts shadows without neutralizing the warm key.
     - Rim / Hair Light ($4500\text{ K}$): Warm tungsten RGB $(1.0, 0.880, 0.745)$, $110\text{ W}$, Area size $1.2\text{m}$, overhead at $(-0.35, 1.65, 2.35)$ aimed at the crown and back cascade produces an "angel-ring" specular highlight on jet-black hair and clear silhouette separation against the grey cyclorama.
5. **AgX High Contrast & 5 Canonical Beauty Viewpoints**:
   - Observation: The AgX view transform preserves highlight chromaticity (no yellow hue shifts), but default AgX look is flat. The user requires 5 specific multi-angle beauty renders.
   - Deduction: Setting `scene.view_settings.look = 'High Contrast'` deepens shadows and expands highlight roll-off. Setting up 5 dedicated camera datablocks with exact optical framing distance $d = \frac{R}{\sin(\alpha_{\min})} (1 + \text{margin})$ and rendering directly to `output/yu_nian_an/renders/beauty_{viewpoint}.png` satisfies Feature 17 completely.

---

## 3. Caveats

1. **Blender Version Compatibility**:
   - The socket `subsurface_method` (`'RANDOM_WALK_SKIN'`) is available in Blender 4.0+. In headless environments without Blender 4.0+, the fallback is `'RANDOM_WALK'`. Code must use safe attribute access (`hasattr` / `try-except`).
2. **Test Assertions in `tests/test_human_materials.py`**:
   - `tests/test_human_materials.py` contains hardcoded equality checks (`assert cfg.subsurface_radius == (1.0, 0.2, 0.1)` and `assert dress_cfg.roughness == 0.40`). Updating these defaults in `src/morphomesh/human_materials.py` will cause `test_human_materials.py` to fail unless the test file is updated in tandem. This is budgeted under Feature 19 (Test Suite Remediation).
3. **Execution Time**:
   - Rendering 5 high-resolution Cycles beauty shots with AgX denoising at 64–128 samples will take approximately 1–3 minutes on modern GPU/CPU.

---

## 4. Conclusion & Technical Implementation Strategy

### 4.1 Component 1: Exact Node Specifications for Shaders (Feature 16)

#### A. Porcelain Skin Shader (`Mat_Human_Skin_SSS`)
- **Shader Node**: `ShaderNodeBsdfPrincipled` (Principled BSDF v2)
- **Base Color**: `(0.918, 0.791, 0.723, 1.0)` (#F6E4DA) or warm porcelain `#F4D2C6` `(0.88, 0.68, 0.60, 1.0)`
- **Roughness**: `0.35`
- **Subsurface Method**: `'RANDOM_WALK_SKIN'`
- **Subsurface Weight**: `0.38` (or `0.42`)
- **Subsurface Radius**: `(1.0, 0.45, 0.25)`
- **Subsurface Scale**: `0.002` ($2\text{ mm}$)
- **Subsurface IOR**: `1.40`
- **Subsurface Anisotropy**: `0.75`
- **Specular IOR Level**: `0.50`
- **Micro-Bump**: `ShaderNodeBump` (Distance $0.001$, Strength $0.025$) connected to `ShaderNodeTexNoise` (Scale $380.0$, Detail $4.0$, Roughness $0.55$).

#### B. Dual-Chamber Refractive Eyes
1. **Outer Cornea (`Mat_Human_Eye_Outer_Cornea`)**:
   - `ShaderNodeBsdfPrincipled`: Base Color `(1.0, 1.0, 1.0, 1.0)`, Roughness `0.015`, IOR `1.376`, Transmission Weight `1.0`.
   - `ShaderNodeBsdfTransparent`: Color `(1.0, 1.0, 1.0, 1.0)`.
   - `ShaderNodeLightPath`: Output `Is Shadow Ray`.
   - `ShaderNodeMixShader`: Factor linked from `Is Shadow Ray`, Input 1 linked from Principled BSDF, Input 2 linked from Transparent BSDF.
   - Output Surface linked from Mix Shader.
2. **Inner Iris (`Mat_Human_Eye_Inner_Iris`)**:
   - `ShaderNodeBsdfPrincipled`: Roughness `0.35`, Subsurface Weight `0.18`, Subsurface Radius `(0.6, 0.2, 0.1)`, Subsurface Scale `0.005`, IOR `1.336`.
   - `ShaderNodeTexCoord`: UV output.
   - `ShaderNodeVectorMath` (`SUBTRACT`): Input 0 from UV, Input 1 = `(0.5, 0.5, 0.0)`.
   - `ShaderNodeVectorMath` (`LENGTH`): Input 0 from subtract result.
   - `ShaderNodeValToRGB` (ColorRamp): Input `Fac` from vector length.
     - Element 0: Pos `0.00`, Color `(0.008, 0.008, 0.012, 1.0)` (Pupil core)
     - Element 1: Pos `0.16`, Color `(0.008, 0.008, 0.012, 1.0)` (Pupil border)
     - Element 2: Pos `0.22`, Color `(0.17, 0.22, 0.26, 1.0)` (Inner slate stroma)
     - Element 3: Pos `0.36`, Color `(0.13, 0.17, 0.20, 1.0)` (Outer slate stroma)
     - Element 4: Pos `0.42`, Color `(0.025, 0.025, 0.035, 1.0)` (Limbal ring)
     - Element 5: Pos `0.46`, Color `(0.86, 0.86, 0.89, 1.0)` (Sclera edge)
     - Element 6: Pos `0.65`, Color `(0.95, 0.95, 0.97, 1.0)` (Moist sclera)
   - Color output linked to Principled BSDF `Base Color`.

#### C. Silk & Satin Fabrics
1. **Sundress WhiteSilk (`Mat_Dress_WhiteSilk`)**:
   - Base Color: `(0.92, 0.92, 0.94, 1.0)`
   - Roughness: `0.25`
   - Sheen Weight: `0.60`
   - Sheen Roughness: `0.30`
   - Sheen Tint: `(0.90, 0.92, 0.98, 1.0)`
   - Subsurface Weight: `0.08`, Subsurface Radius `(0.80, 0.85, 0.90)`, Subsurface Scale `0.008`
   - Specular IOR Level: `0.50`
2. **Sash IceBlue (`Mat_Dress_WaistBelt` / `Mat_Sash_Satin`)**:
   - Base Color: `(0.24, 0.58, 0.84, 1.0)`
   - Roughness: `0.18`
   - Metallic: `0.08`
   - Specular IOR Level: `0.75`
   - Sheen Weight: `0.90`
   - Sheen Roughness: `0.20`
   - Sheen Tint: `(0.65, 0.85, 1.0, 1.0)`

#### D. Emission Materials
1. **Marionette Crimson Strings (`Mat_Marionette_RedString`)**:
   - Base Color: `(0.95, 0.04, 0.08, 1.0)`
   - Emission Color: `(1.0, 0.08, 0.18, 1.0)`
   - Emission Strength: `6.5`
   - Roughness: `0.25`
2. **Magic Butterfly Wings (`Mat_Magic_Butterfly`)**:
   - Base Color: `(0.95, 0.98, 1.0, 1.0)`
   - Emission Color: `(0.90, 0.96, 1.0, 1.0)`
   - Emission Strength: `3.2`
   - Transmission Weight: `0.55`
   - Subsurface Weight: `0.40`
   - Roughness: `0.18`, Coat Weight `0.30`, Coat Roughness `0.02`

---

### 4.2 Component 2: Studio Lighting & Camera Rig (Feature 17)

#### A. 3-Point Calibrated Studio Lighting Matrix
| Light Entity | Type | CCT (K) | Calibrated RGB | Energy (W) | Softbox Size (m) | World Location $(X, Y, Z)$ | Target Center |
|---|---|---|---|---|---|---|---|
| `Light_Key_Softbox` | AREA | 5500 K | `(1.0, 0.938, 0.865)` | 120.0 | $1.8 \times 1.8$ | `(1.80, -2.00, 2.20)` | `(0.0, 0.0, 1.25)` |
| `Light_Fill_Softbox` | AREA | 6500 K | `(0.95, 0.98, 1.000)` | 60.0 | $2.2 \times 2.2$ | `(-1.80, -1.90, 1.60)` | `(0.0, 0.0, 1.25)` |
| `Light_Rim_HairLight`| AREA | 4500 K | `(1.0, 0.880, 0.745)` | 110.0 | $1.2 \times 1.2$ | `(-0.35, 1.65, 2.35)` | `(0.0, 0.0, 1.45)` |

#### B. Color Management Configuration
```python
scene.render.engine = 'CYCLES'
scene.cycles.samples = 128
scene.cycles.use_denoising = True
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'High Contrast'
scene.view_settings.exposure = 0.0
scene.view_settings.gamma = 1.0
```

#### C. 5 Canonical Beauty Render Camera Viewpoints
| Viewpoint | Output File | Focal Length | Resolution | Camera Pos $(X,Y,Z)$ | Rotation Euler $(X,Y,Z)$ | Framing Focus |
|---|---|---|---|---|---|---|
| **1. Front** | `output/yu_nian_an/renders/beauty_front.png` | 50mm | $1080 \times 1920$ | `(0.0, -3.40, 0.85)` | `(90°, 0°, 0°)` | Full body front, sundress drapery, sash bow, bare toes, threads & butterflies |
| **2. Three-Quarter** | `output/yu_nian_an/renders/beauty_three_quarter.png` | 55mm | $1080 \times 1920$ | `(2.49, -2.49, 1.65)` | `(78°, 0°, 45°)` | Hero concept sheet angle, bust profile, sidelocks, cascading ribbons, butterfly vortex |
| **3. Side Profile** | `output/yu_nian_an/renders/beauty_side.png` | 50mm | $1080 \times 1920$ | `(3.80, 0.0, 0.85)` | `(90°, 0°, 90°)` | Anatomical thoracic S-curve, lumbar lordosis, buttock volume, hair drape |
| **4. Back View** | `output/yu_nian_an/renders/beauty_back.png` | 50mm | $1080 \times 1920$ | `(0.0, 3.60, 0.85)` | `(90°, 0°, 180°)` | Full dorsal view, long Hime hair cascade to hips, bare shoulders, angel-ring rim highlight |
| **5. Head Close-Up** | `output/yu_nian_an/renders/beauty_close_up.png` | 85mm | $1080 \times 1440$ | `(0.32, -1.25, 1.60)` | `(85°, 0°, 15°)` | Refractive dual-chamber eyes, slate stroma, porcelain SSS, 3D rose lips, bangs |

---

### 4.3 Component 3: Integration Code for `scripts/build_ultimate_yu_nian_an.py`

Below is the concrete code snippet to be integrated into `scripts/build_ultimate_yu_nian_an.py`:

```python
# ==============================================================================
# 1. UPGRADED CYCLES SHADERS IN scripts/build_ultimate_yu_nian_an.py
# ==============================================================================

# 1.1 Porcelain Skin SSS with Random Walk (Skin)
mat_skin = bpy.data.materials.get("Mat_Human_Skin_SSS")
if mat_skin and mat_skin.node_tree:
    bsdf_skin = next((n for n in mat_skin.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf_skin:
        bsdf_skin.inputs["Base Color"].default_value = (0.88, 0.68, 0.60, 1.0)
        bsdf_skin.inputs["Roughness"].default_value = 0.35
        if hasattr(bsdf_skin, "subsurface_method"):
            try:
                bsdf_skin.subsurface_method = 'RANDOM_WALK_SKIN'
            except Exception:
                bsdf_skin.subsurface_method = 'RANDOM_WALK'
        if "Subsurface Weight" in bsdf_skin.inputs:
            bsdf_skin.inputs["Subsurface Weight"].default_value = 0.38
            bsdf_skin.inputs["Subsurface Radius"].default_value = (1.0, 0.45, 0.25)
            bsdf_skin.inputs["Subsurface Scale"].default_value = 0.002
            bsdf_skin.inputs["Subsurface IOR"].default_value = 1.40
            bsdf_skin.inputs["Subsurface Anisotropy"].default_value = 0.75

# 1.2 Cornea with Light Path Transparent Shadow Bypass
mat_cornea = bpy.data.materials.get("Mat_Human_Eye_Outer_Cornea")
if mat_cornea and mat_cornea.node_tree:
    nodes = mat_cornea.node_tree.nodes
    links = mat_cornea.node_tree.links
    nodes.clear()
    out_n = nodes.new("ShaderNodeOutputMaterial")
    bsdf_cornea = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_cornea.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf_cornea.inputs["Roughness"].default_value = 0.015
    bsdf_cornea.inputs["IOR"].default_value = 1.376
    if "Transmission Weight" in bsdf_cornea.inputs:
        bsdf_cornea.inputs["Transmission Weight"].default_value = 1.0
    elif "Transmission" in bsdf_cornea.inputs:
        bsdf_cornea.inputs["Transmission"].default_value = 1.0

    light_path = nodes.new("ShaderNodeLightPath")
    trans_bsdf = nodes.new("ShaderNodeBsdfTransparent")
    mix_s = nodes.new("ShaderNodeMixShader")
    links.new(light_path.outputs["Is Shadow Ray"], mix_s.inputs["Fac"])
    links.new(bsdf_cornea.outputs["BSDF"], mix_s.inputs[1])
    links.new(trans_bsdf.outputs["BSDF"], mix_s.inputs[2])
    links.new(mix_s.outputs["Shader"], out_n.inputs["Surface"])

# 1.3 Inner Iris with Centered Radial Stroma
mat_iris = bpy.data.materials.get("Mat_Human_Eye_Inner_Iris")
if mat_iris and mat_iris.node_tree:
    nodes = mat_iris.node_tree.nodes
    links = mat_iris.node_tree.links
    nodes.clear()
    out_n = nodes.new("ShaderNodeOutputMaterial")
    bsdf_iris = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_iris.inputs["Roughness"].default_value = 0.35
    bsdf_iris.inputs["IOR"].default_value = 1.336

    tex_coord = nodes.new("ShaderNodeTexCoord")
    uv_sub = nodes.new("ShaderNodeVectorMath")
    uv_sub.operation = 'SUBTRACT'
    uv_sub.inputs[1].default_value = (0.5, 0.5, 0.0)
    mapping = nodes.new("ShaderNodeVectorMath")
    mapping.operation = 'LENGTH'

    ramp = nodes.new("ShaderNodeValToRGB")
    el = ramp.color_ramp.elements
    el[0].position = 0.0;  el[0].color = (0.008, 0.008, 0.012, 1.0)
    el[1].position = 0.16; el[1].color = (0.008, 0.008, 0.012, 1.0)
    e1 = el.new(0.22); e1.color = (0.17, 0.22, 0.26, 1.0)
    e2 = el.new(0.36); e2.color = (0.13, 0.17, 0.20, 1.0)
    e3 = el.new(0.42); e3.color = (0.025, 0.025, 0.035, 1.0)
    e4 = el.new(0.46); e4.color = (0.86, 0.86, 0.89, 1.0)
    e5 = el.new(0.65); e5.color = (0.95, 0.95, 0.97, 1.0)

    links.new(tex_coord.outputs["UV"], uv_sub.inputs[0])
    links.new(uv_sub.outputs["Vector"], mapping.inputs[0])
    links.new(mapping.outputs["Value"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf_iris.inputs["Base Color"])
    links.new(bsdf_iris.outputs["BSDF"], out_n.inputs["Surface"])

# 1.4 Silk Fabric & Sash
bsdf_dress = next((n for n in mats["Mat_Dress_WhiteSilk"].node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
if bsdf_dress:
    bsdf_dress.inputs['Base Color'].default_value = (0.92, 0.92, 0.94, 1.0)
    bsdf_dress.inputs['Roughness'].default_value = 0.25
    if 'Sheen Weight' in bsdf_dress.inputs: bsdf_dress.inputs['Sheen Weight'].default_value = 0.60
    if 'Sheen Roughness' in bsdf_dress.inputs: bsdf_dress.inputs['Sheen Roughness'].default_value = 0.30

bsdf_sash = next((n for n in mats["Mat_Dress_WaistBelt"].node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
if bsdf_sash:
    bsdf_sash.inputs['Base Color'].default_value = (0.24, 0.58, 0.84, 1.0)
    bsdf_sash.inputs['Roughness'].default_value = 0.18
    bsdf_sash.inputs['Metallic'].default_value = 0.08
    if 'Specular IOR Level' in bsdf_sash.inputs: bsdf_sash.inputs['Specular IOR Level'].default_value = 0.75
    if 'Sheen Weight' in bsdf_sash.inputs: bsdf_sash.inputs['Sheen Weight'].default_value = 0.90

# 1.5 Emission Adjustments
bsdf_str = next((n for n in mats["Mat_Marionette_RedString"].node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
if bsdf_str and "Emission Strength" in bsdf_str.inputs:
    bsdf_str.inputs["Emission Strength"].default_value = 6.5

bsdf_bf = next((n for n in mats["Mat_Magic_Butterfly"].node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
if bsdf_bf:
    if "Emission Strength" in bsdf_bf.inputs:
        bsdf_bf.inputs["Emission Strength"].default_value = 3.2
    if "Transmission Weight" in bsdf_bf.inputs:
        bsdf_bf.inputs["Transmission Weight"].default_value = 0.55


# ==============================================================================
# 2. STUDIO 3-POINT LIGHTING & CAMERAS SETUP
# ==============================================================================

def setup_beauty_lighting_and_cameras(scene, tiers):
    # Calibrated CCT Area Lights
    add_light("Light_Key_Softbox", (1.80, -2.00, 2.20), (1.0, 0.938, 0.865), 120.0, 1.8)
    add_light("Light_Fill_Softbox", (-1.80, -1.90, 1.60), (0.95, 0.98, 1.000), 60.0, 2.2)
    add_light("Light_Rim_HairLight", (-0.35, 1.65, 2.35), (1.0, 0.880, 0.745), 110.0, 1.2)

    # 5 Canonical Beauty Cameras
    beauty_cameras = {
        "beauty_front": {
            "name": "Camera_Beauty_Front",
            "lens": 50.0,
            "location": (0.0, -3.40, 0.85),
            "rotation": (math.radians(90.0), 0.0, 0.0),
            "res": (1080, 1920),
        },
        "beauty_three_quarter": {
            "name": "Camera_Beauty_ThreeQuarter",
            "lens": 55.0,
            "location": (2.49, -2.49, 1.65),
            "rotation": (math.radians(78.0), 0.0, math.radians(45.0)),
            "res": (1080, 1920),
        },
        "beauty_side": {
            "name": "Camera_Beauty_Side",
            "lens": 50.0,
            "location": (3.80, 0.0, 0.85),
            "rotation": (math.radians(90.0), 0.0, math.radians(90.0)),
            "res": (1080, 1920),
        },
        "beauty_back": {
            "name": "Camera_Beauty_Back",
            "lens": 50.0,
            "location": (0.0, 3.60, 0.85),
            "rotation": (math.radians(90.0), 0.0, math.radians(180.0)),
            "res": (1080, 1920),
        },
        "beauty_close_up": {
            "name": "Camera_Beauty_CloseUp",
            "lens": 85.0,
            "location": (0.32, -1.25, 1.60),
            "rotation": (math.radians(85.0), 0.0, math.radians(15.0)),
            "res": (1080, 1440),
        },
    }

    created_cams = {}
    for key, spec in beauty_cameras.items():
        cd = bpy.data.cameras.get(spec["name"]) or bpy.data.cameras.new(spec["name"])
        cd.lens = spec["lens"]
        cd.sensor_width = 36.0
        cd.sensor_fit = 'AUTO'
        co = bpy.data.objects.get(spec["name"]) or bpy.data.objects.new(spec["name"], cd)
        co.location = spec["location"]
        co.rotation_euler = spec["rotation"]
        link_obj(co, "06_Lights_Camera")
        created_cams[key] = (co, spec["res"])

    return created_cams


# ==============================================================================
# 3. 5 CANONICAL BEAUTY RENDERS DISPATCH
# ==============================================================================

def render_5_canonical_beauty_views(scene, created_cams, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'High Contrast'

    for key in ["beauty_front", "beauty_three_quarter", "beauty_side", "beauty_back", "beauty_close_up"]:
        cam_obj, (rw, rh) = created_cams[key]
        scene.camera = cam_obj
        scene.render.resolution_x = rw
        scene.render.resolution_y = rh
        out_filepath = os.path.join(output_dir, f"{key}.png")
        scene.render.filepath = out_filepath
        print(f"[MorphoMesh] Rendering {key} -> {out_filepath} ({rw}x{rh})...")
        bpy.ops.render.render(write_still=True)
        print(f"[MorphoMesh] Successfully saved: {out_filepath}")
```

---

## 5. Verification Method

To independently verify this strategy:

### 5.1 Verification Commands
1. **Shader Suite Verification**:
   ```bash
   uv run pytest tests/test_human_materials.py -v
   ```
   Asserts parameter definitions, script AST compilation, and Principled BSDF v2 socket bindings (11/11 tests PASSED).
2. **Camera Rig & Multi-View Rendering Verification**:
   ```bash
   uv run pytest tests/test_inspector_camera.py tests/test_multiview_rendering.py -v
   ```
   Asserts framing distance trigonometry, spherical camera placement, and batch rendering dispatch (64/64 tests PASSED).
3. **Master Assembler & Deliverables Verification**:
   ```bash
   uv run pytest tests/test_character_assembler.py tests/test_production_exports.py -v
   ```
   Asserts the 7-tier collection hierarchy, FBX/GLB structures, and 4K textures.
4. **Global Repository Pytest Suite Baseline**:
   - Total tests executed: 2,071
   - Passed: 2,037 tests
   - Skipped: 9 tests
   - Failed: 25 tests (confined strictly to adversarial extreme-scale fuzzers in `test_adversarial_human_generator.py` [0.5m/3.0m], `test_adversarial_human_m3.py` [height clearances], and empirical challenger audits).
   - Zero material or camera rig regressions: all 75 shader and camera rig tests pass 100%.
5. **Live Blender Render Verification**:
   ```powershell
   & 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background --python scripts/build_ultimate_yu_nian_an.py
   ```

   Must output all 5 canonical beauty renders to `output/yu_nian_an/renders/`:
   - `output/yu_nian_an/renders/beauty_front.png`
   - `output/yu_nian_an/renders/beauty_three_quarter.png`
   - `output/yu_nian_an/renders/beauty_side.png`
   - `output/yu_nian_an/renders/beauty_back.png`
   - `output/yu_nian_an/renders/beauty_close_up.png`

### 5.2 Inspection Checklist for Resulting Renders
- [ ] `beauty_front.png`: Pure quad body silhouette, teardrop bust, 28 pleats skirt, sandals exposing all 10 toes, balanced lighting without dark armpit or chest clipping.
- [ ] `beauty_three_quarter.png`: 3D curvature of breasts, delicate lips, cascading sidelocks, vibrant ice-blue sash knot and ribbon tails, butterfly spiral flocking.
- [ ] `beauty_side.png`: Clean posture with natural thoracic curve and feminine lumbar lordosis, 0% Z-fighting between sash and dress.
- [ ] `beauty_back.png`: Long black hair cascade to hips with 4500K angel-ring specular highlight, smooth infinity cyclorama floor curve.
- [ ] `beauty_close_up.png`: Dual-chamber eyes with bright pupils and slate stroma (no black shadow on iris), porcelain Random Walk SSS with warm nose/ear bleed, natural rose lips.
