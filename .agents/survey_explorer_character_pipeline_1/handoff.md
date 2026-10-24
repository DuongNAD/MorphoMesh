# Survey Report: Character Pipeline, Rigify 163 DEF Rig, Accessories, Shaders, Testing & Exports

**Agent**: Survey Explorer 3 (Character Pipeline & Verification)  
**Date**: 2026-09-08T00:34:00+07:00  
**Status**: Complete (Hard Handoff)  
**Target Milestone**: Survey / Digital Human Character Pipeline & Verification  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\survey_explorer_character_pipeline_1`  

---

## Executive Summary

This report delivers the authoritative survey and architectural blueprint for the full digital human character pipeline for **Yu Nian An (余念安)** within the MorphoMesh ecosystem. The analysis investigates six interrelated systems:
1. **Concept Turnaround & Anatomical Ground Truth**: Comprehensive multi-angle alignment against the official turnaround sheet (`media_1788716034772.jpg`), realistic reference dress & sandals (`media_1788785935849.jpg`), anatomical skeleton (`media_1788785935854.png`), and direct user defect reports (`media_1788801589498.png`, `media_1788801618516.png`).
2. **Rigify 163 DEF Armature Integration**: Exact mapping of all 163 deforming bones (64 body DEF + 99 facial DEF bones), biomechanical Instantaneous Center of Rotation (ICR) landmarks, obligatory joint pre-bends (elbow +Y, knee -Y), hinge bone roll solutions, and biharmonic volume-preserving skinning weights.
3. **High-Fidelity Character Accessories**: 6-stratum Hime Cut hair system with Geometry Nodes modifier networks; ergonomic flat leather strap sandals exposing 5 bare toes with metatarsophalangeal (MTP) skinning transitions; and 10 crimson marionette threads ($0.0\text{mm}$ snapping to fingertip bone tails) controlling 10 glowing swallowtail butterflies in bilateral vortex spirals.
4. **Photorealistic Cycles Shading & Studio Lighting**: Principled BSDF v2 Random Walk Subsurface Scattering (SSS) skin, dual-chamber refractive cornea/iris eyes, anisotropic silk sheen fabrics, and calibrated 3-point lighting (5500K Key, 6500K Fill, 4500K Rim) with AgX color management.
5. **Automated Verification Testing**: Mathematical formulas and pytest validation for zero penetrations ($s_i \ge -0.0005\text{m}$), 100% outward normals ($c_x n_x + c_y n_y > 0$), and 100% pure quad topology across deforming joints.
6. **Production Multi-Format Exports**: Automated export pipeline generating `Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, `Yu_Nian_An.fbx`, and a complete 9-channel uncompressed 4K PBR texture suite.

---

## 1. Observation

### 1.1 Direct Observation of Visual References and User Feedback

| Reference Image | Path | Observed Geometric & Stylistic Features |
|---|---|---|
| **Concept Sheet** | `C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg` | 4-view orthographic turnaround (Front, 3/4, Profile, Back); character height 1.65m; 7.41 head-to-body ratio; white sundress with sweetheart neckline and spaghetti straps; high-waisted ice-blue sash; flat sandals with bare toes; 10 crimson marionette threads wrapped around distal finger joints controlling glowing white swallowtail butterflies; jet-black hair in Hime cut with straight blunt forehead bangs and cheek-length sidelocks; calm, melancholic facial expression. |
| **Realistic Dress & Sandals** | `C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788785935849.jpg` | Real-world photograph of woman walking in sundress and flat leather sandals: dress exhibits organic gravity drape, natural waist gathering, tension folds radiating from hip movement; flat sandals have ultra-thin soles with an ankle collar and cross strap leaving all 5 toes completely bare and resting naturally. |
| **Skeletal Anatomy** | `C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788785935854.png` | Authentic anatomical diagram (anterior and posterior views): shows exact landmarks for clavicle S-curve, suprasternal notch, acromion, humerus, radius, ulna, pelvis, femur, patella, tibia, fibula, bimalleolar ankle asymmetry, calcaneus, and 5 separate phalanges on feet. |
| **Defect 1: Arm/Shoulder** | `C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788801589498.png` | Prior iteration failure: acromion/shoulder area severed into sharp knife-edge triangular spikes projecting upward; arm disconnected/pinched; flat hollow chest without teardrop volume; crude cylindrical sash with floating button. |
| **Defect 2: Conical Dress** | `C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788801618516.png` | Prior iteration failure: skirt rendered as a rigid geometric truncated cone ("lampshade" skirt / váy xếp ly nón cứng đơ dạng chụp đèn) with zero natural gravity folds or tension lines; origami-like low-poly butterflies and rigid lines. |

### 1.2 Direct Observation of Codebase Architecture

1. **Rigify 163 DEF Armature (`src/morphomesh/human_rigging.py`)**:
   - `BODY_DEF_BONES`: Lines 48–100 define exactly 64 body DEF bones:
     - Spine/Head/Eyes (10): `DEF-spine`, `DEF-spine.001` through `DEF-spine.006`, `DEF-head`, `DEF-eye.L`, `DEF-eye.R`.
     - Upper limbs (12): `DEF-shoulder.L/R`, `DEF-upper_arm.L/R`, `DEF-upper_arm.L/R.001`, `DEF-forearm.L/R`, `DEF-forearm.L/R.001`, `DEF-hand.L/R`.
     - 10 Fingers (30): 15 per hand across 5 digits (3 phalanges each: `DEF-thumb.01-03`, `DEF-f_index.01-03`, `DEF-f_middle.01-03`, `DEF-f_ring.01-03`, `DEF-f_pinky.01-03`).
     - Lower limbs (12): `DEF-thigh.L/R`, `DEF-thigh.L/R.001`, `DEF-shin.L/R`, `DEF-shin.L/R.001`, `DEF-foot.L/R`, `DEF-toe.L/R`.
   - `FACIAL_DEF_BONES`: Lines 102–146 define exactly 99 facial DEF bones:
     - Brows (16), Cheeks (8), Chin (4), Ears (10), Forehead (8), Jaw (4), Eyelids (16), Lips (16), Nose (8), Temple (2), Tongue (6), Midline Jaw (1: `DEF-jaw.center`).
   - Line 153: `assert len(ALL_163_DEF_BONES) == 163`.
   - Pre-bends enforced at lines 258–278: `elbow_L/R_y > 0.0` (+15mm) and `knee_L/R_y < 0.0` (-18mm).

2. **Anatomical Estimation & Biharmonic Skinning (`src/morphomesh/anatomy/`)**:
   - `classify_locomotor_stance` in `stance.py`: Classifies stances (Humanoid, Plantigrade, Digitigrade, Unguligrade).
   - `compute_bony_landmarks` and `estimate_icr_joint_pivots` in `landmarks.py`: Extracts Instantaneous Centers of Rotation for shoulder, elbow, wrist, hip, knee, ankle, and toes.
   - `compute_hinge_plane_normal` and `solve_biomechanical_bone_roll` in `bone_roll.py`: Calculates hinge normal $\vec{n}_{\text{hinge}}$ and sets bone roll to prevent candy-wrapper collapse.
   - `compute_geodesic_skin_weights` in `skinning.py`: Volumetric geodesic voxel diffusion preventing weight stealing between torso/limbs.

3. **Wardrobe & Magic Props (`src/morphomesh/wardrobe.py`)**:
   - Flat sandals (`generate_flat_strappy_sandals` at line 1472): Sole ($0.235\text{m} \times 0.082\text{m} \times 0.012\text{m}$), sub-malleolar ankle collar ($Z \le 0.0485\text{m}$), heel counter, arching metatarsal strap leaving all 5 toes exposed, MTP smoothstep transition weighting between `DEF-foot.L/R` and `DEF-toe.L/R`.
   - Marionette red cords (`generate_catenary_magic_strings` at line 1600): Exactly 14 vertices per cord (6 segments), catenary sag $s_{\max} = 0.08 \times \text{chord\_len}$, tethered to distal finger bone tails (`DEF-thumb.03.L/R`, `DEF-f_index.03.L/R`, etc.).
   - Swallowtail butterflies (`generate_swallowtail_quad_butterfly` at line 1673): 24 quads, 48 vertices, 100% quads, 3D segmented body (head, thorax, abdomen), antennae, forewings and hindwings with swallowtail spurs. Flocking arranged in bilateral vortex spiral ($Z \in [0.88\text{m}, 1.32\text{m}]$).

4. **Hair Grooming (`src/morphomesh/human_grooming.py`)**:
   - 6-stratum Hime Cut architecture:
     1. `Hair_Hime_Bangs`: Blunt straight forehead bangs trimmed at eyebrow line ($Z \approx 1.54 - 1.57\text{m}$, length $0.13\text{m}$).
     2. `Hair_Hime_Sidelocks`: Symmetrical cheek/jaw-length locks framing jawline down to $Z \approx 1.42\text{m}$ (length $0.20\text{m}$).
     3. `Hair_Scalp_Crown`: Cranial volume and natural offset parting (length $0.18\text{m}$).
     4. `Hair_Temporal_Transitions`: Transitional blend over temples (length $0.30\text{m}$).
     5. `Hair_Back_Cascade`: Flowing jet-black hair cascading down spine to mid-thigh ($0.95 - 1.05\text{m}$).
     6. `Hair_Facial_Details`: Melancholic eyebrows and delicate eyelash cards.
   - Geometry Nodes modifier pipeline: Interpolate Hair Curves, Clump (factor 0.25), micro-frizz noise (freq 14.0, amp 0.0012m), radius taper (root 0.00016m -> tip 0.000025m), and `Mat_Human_Hair`.

5. **PBR Materials & Shaders (`src/morphomesh/human_materials.py`)**:
   - `Mat_Human_Skin_SSS`: Random Walk SSS (`subsurface_weight=0.28`, `radius=(1.0, 0.2, 0.1)`, `scale=0.024`, `IOR=1.45`), porcelain fair tone `#F6E4DA` (`0.918, 0.791, 0.723, 1.0`), micro-roughness specular bump (`roughness=0.35`, scale 380, strength 0.03).
   - `Mat_Human_Eye_Outer_Cornea`: Outer dome with transmission 1.0, roughness 0.02, IOR 1.376.
   - `Mat_Human_Eye_Inner_Iris`: Concave dish with IOR 1.336, charcoal/slate `#2D343B` with procedural radial fibers and pupil dilation.
   - `Mat_Human_Eye_Sclera`: Moist off-white `#F2F1F0` with vascular red veins and SSS.
   - `Mat_Human_Hair`: Melanin 0.85, roughness 0.25, radial roughness 0.45, coat sheen 0.45 for silky angel-ring highlights.
   - `Mat_Dress_WhiteSilk`: Off-white, sheen weight 0.60, roughness 0.40, backlight SSS 0.14.
   - `Mat_Dress_WaistBelt` / `Mat_Sash_Satin`: Ice-blue satin `#C6DEEE`, roughness 0.22, anisotropy 0.78.
   - `Mat_Marionette_RedString`: Crimson emission `#FF1F3D`, strength 6.5.
   - `Mat_Magic_Butterfly`: Pearl white translucent SSS 0.45, luminescence emission 3.2.

6. **Master Assembler & Studio Lighting (`src/morphomesh/character_assembler.py`)**:
   - 7-tier collection hierarchy: `Yu_Nian_An_Master` root, `01_Body`, `02_Hair`, `03_Wardrobe`, `04_Props`, `05_Armature`, `06_Lights_Camera`.
   - 3-point softbox studio lighting: Key light (45° front-right, 5500K warm, 500W), Fill light (45° front-left, 6500K cool, 250W), Rim/Hair light (back-top, 4500K, 450W for angel-ring highlight).
   - Cameras: 85mm portrait camera (target $Z=1.55\text{m}$), 50mm full-body camera (distance $5.5\text{m}$, target $Z=0.825\text{m}$), 4 turnaround cameras (Front, Three-Quarter, Profile, Back).
   - Cycles render engine, 128 samples, denoising enabled, AgX View Transform.

7. **Production Exports & Documentation (`src/morphomesh/export_manager.py` & `output/yu_nian_an/`)**:
   - Production assets exist: `Yu_Nian_An_Master.blend` (6.06 MB), `Yu_Nian_An.fbx` (5.92 MB), `Yu_Nian_An.glb` (2.43 MB).
   - 9 4K uncompressed PBR texture maps in `output/yu_nian_an/textures/` (BaseColor, Normal, Roughness, Metallic, SSS, Alpha, Height, ORM, MaskMap).
   - `README_EXPORT.md`: Comprehensive 249-line manual for Unreal Engine 5.4+, Unity 6, and Three.js WebGL integration.

8. **Automated Verification Suite (`tests/`)**:
   - Command `uv run pytest --collect-only -q` collected 1,994 tests.
   - Command `uv run pytest -q tests/test_character_assembler.py tests/test_production_exports.py` yielded **63 passed in 5.87s**.
   - Command `uv run pytest -q tests/test_wardrobe_m2.py tests/test_wardrobe_m3.py tests/test_hime_cut_6_strata.py tests/test_anatomy.py` yielded **87 passed in 1.14s**.

---

## 2. Logic Chain

The step-by-step technical synthesis connecting the observations to actionable downstream requirements:

```
[Observation 1.1: Concept Sheet & Visual Defect Reports]
  │
  ├── 1. Concept requires 7.41 head ratio, white sundress with sweetheart neckline & ice-blue sash,
  │      bare-toed flat sandals, 10 marionette strings on fingertips, 10 glowing butterflies, Hime cut hair.
  │
  ├── 2. User feedback media_1788801589498.png & media_1788801618516.png shows previous catastrophic failures:
  │      spiky severed shoulders, pinched arms, hollow bust, and a conical "lampshade" skirt.
  │
  ▼
[Observation 1.2: Rigify 163 DEF Armature & Biomechanics]
  │
  ├── 3. Rigify Human Metarig requires exactly 163 DEF bones (64 body + 99 facial).
  │      Facial DEF bones enable 52 ARKit FACS morph targets; body DEF bones articulated with dual-bone twists.
  │
  ├── 4. Bony landmarks and ICR pivots must be placed at true anatomical axes (trochlea for elbow, condyles for knee,
  │      malleoli for ankle, MTP for toes) with pre-bends (elbow +Y 15mm, knee -Y 18mm) to prevent candy-wrapper collapse.
  │
  ▼
[Observation 1.2: Wardrobe & Accessories Formulation]
  │
  ├── 5. Skirt must be replaced with Cloth Simulation / organic drape (M2), completely eliminating conical shape.
  │      Bodice must conform to teardrop bust with sweetheart scoop neckline and spaghetti straps.
  │
  ├── 6. Sandals must leave all 5 toes exposed (M3), utilizing MTP smoothstep skin weight transition to toe bones.
  │
  ├── 7. Marionette strings must maintain exactly 14 vertices per cord, catenary sag curve, and 0mm anchor
  │      snapping to the 10 distal fingertip bone tails (DEF-thumb.03.L/R through DEF-f_pinky.03.L/R).
  │
  ├── 8. Butterflies must feature 100% pure quad topology (24 quads, 48 vertices), segmented bodies, swallowtail spurs,
  │      and bilateral upward vortex spiral distribution flanking the hands.
  │
  ▼
[Observation 1.2: Cycles AgX Shading & Studio Lighting]
  │
  ├── 9. Skin requires Random Walk SSS (porcelain fair tone, radius 1.0, 0.2, 0.1, scale 0.024) to emulate human epidermis.
  │      Eyes require dual-chamber optical separation (refractive cornea IOR 1.376 + concave iris dish IOR 1.336).
  │
  ├── 10. AgX View Transform and 3-point softbox lighting (5500K Key, 6500K Fill, 4500K Rim) are necessary
  │       to prevent highlight clipping on white silk and porcelain skin.
  │
  ▼
[Observation 1.2: Verification & Multi-Format Exports]
  │
  ├── 11. Automated verification criteria must be enforced:
  │       - 0 penetrations: Signed clearance s_i = (w_i - p_i) . n_i >= -0.0005m between all mesh pairs.
  │       - 100% outward normals: Radial test c_x n_x + c_y n_y > 0; 0 inverted faces.
  │       - 100% quads in deforming joints: 0 triangles and 0 n-gons at knees, elbows, shoulders, hips, fingers, toes.
  │
  └── 12. Final deliverables must be compiled into Yu_Nian_An_Master.blend, Yu_Nian_An.glb, Yu_Nian_An.fbx,
          9 4K PBR textures, and README_EXPORT.md.
```

---

## 3. Caveats

1. **Upstream Base Mold Dependency (Milestone M1)**:
   The master character assembler (`src/morphomesh/character_assembler.py`) currently imports `generate_human_base_mesh` from `src/morphomesh/human_generator.py`. When Milestone M1 replaces the base mesh with the MakeHuman CC0 anatomical female base mold (to permanently resolve the shoulder knife-edge and pinched arm defects in `media_1788801589498.png`), the vertex index mapping and vertex groups will be updated. The assembler and rigging pipeline must consume the updated base mold via standardized vertex groups (`STANDARDIZED_HUMAN_VERTEX_GROUPS`) and landmark keys (`get_default_human_landmarks`) rather than hardcoded vertex indices.

2. **Upstream Cloth Simulation Dependency (Milestone M2)**:
   The dress skirt in `src/morphomesh/wardrobe.py` currently features procedural organic folds (`generate_dress_organic_skirt`). In Milestone M2, the dress will be updated with Blender Cloth Simulation or simulated drape cache to completely eliminate the conical lampshade deformity seen in `media_1788801618516.png`. The assembler is already architected to bind any input wardrobe mesh via Armature modifier with `use_deform_preserve_volume = True` and positive clearance enforcement ($s_i \ge +0.0055\text{m}$).

3. **Blender Binary Availability**:
   Production binary generation and Cycles rendering require a local installation of Blender 4.5+ or 5.2+ LTS on Windows (`C:\Program Files\Blender Foundation\Blender 4.5\blender.exe` or `blender.exe` on `PATH`). In offline/CI environments without Blender, the pure Python fallback engine in `character_assembler.py` and `export_manager.py` generates syntactically valid Python AST scripts and verifies mathematical topology metrics.

---

## 4. Conclusion & Architectural Specification

### 4.1 Master Character Pipeline Map

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   YU NIAN AN MASTER PIPELINE                                       │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                  │
                 ┌────────────────────────────────┴────────────────────────────────┐
                 ▼                                                                 ▼
┌─────────────────────────────────┐                             ┌─────────────────────────────────┐
│       01_BODY & 05_ARMATURE     │                             │     03_WARDROBE & 02_HAIR       │
│  - MakeHuman Female Base Mold   │                             │  - Cloth Simulation Sundress    │
│  - 100% Pure Quad Topology      │                             │  - Ice-Blue Satin Waist Sash    │
│  - 163 DEF Rigify Armature      │                             │  - Flat Bare-Toe Sandals        │
│  - Biomechanical ICR Pivots     │                             │  - 6-Stratum Hime Cut Hair      │
│  - Pre-bends (+Y elbow, -Y knee)│                             │  - Solidify 0.002m & Clearance  │
└─────────────────────────────────┘                             └─────────────────────────────────┘
                 │                                                                 │
                 └────────────────────────────────┬────────────────────────────────┘
                                                  │
                                                  ▼
                               ┌─────────────────────────────────────┐
                               │              04_PROPS               │
                               │  - 10 Crimson Marionette Strings    │
                               │    * Snapped to Finger Bone Tails   │
                               │    * 14 Verts/Cord, Catenary Sag    │
                               │  - 10 Luminous White Butterflies    │
                               │    * 100% Quads (24 quads each)     │
                               │    * Bilateral Vortex Spiral Flock  │
                               └─────────────────────────────────────┘
                                                  │
                                                  ▼
                               ┌─────────────────────────────────────┐
                               │        SHADING, LIGHTS & AGX        │
                               │  - Mat_Human_Skin_SSS (Random Walk) │
                               │  - Dual-Chamber Cornea/Iris Eyes    │
                               │  - Mat_Dress_WhiteSilk (Sheen BSDF) │
                               │  - 3-Point Studio Softbox Lighting  │
                               │  - Cycles 128 spp + AgX Transform   │
                               └─────────────────────────────────────┘
                                                  │
                                                  ▼
                               ┌─────────────────────────────────────┐
                               │        VERIFICATION GATES           │
                               │  - Gate 1: 0 Penetrations (BVH)     │
                               │  - Gate 2: 100% Outward Normals     │
                               │  - Gate 3: 100% Quads at Joints     │
                               │  - Gate 4: 100% Pytest Pass (1994)  │
                               └─────────────────────────────────────┘
                                                  │
                                                  ▼
                               ┌─────────────────────────────────────┐
                               │         PRODUCTION EXPORTS          │
                               │  - Yu_Nian_An_Master.blend          │
                               │  - Yu_Nian_An.glb (glTF 2.0 Web)    │
                               │  - Yu_Nian_An.fbx (Rigged Engine)   │
                               │  - 9x 4K Uncompressed PBR Textures  │
                               │  - README_EXPORT.md Import Manual   │
                               └─────────────────────────────────────┘
```

### 4.2 Component Detail Matrix

| Component | Target File | Key Architectural Invariants & Parameters | Downstream Milestone Owner |
|---|---|---|---|
| **Rigify Armature** | `src/morphomesh/human_rigging.py` | Exactly 163 DEF bones (64 body, 99 facial); elbow pre-bend $+Y = +0.015\text{m}$; knee pre-bend $-Y = -0.018\text{m}$; biharmonic geodesic skin weights normalized to $\sum w_i = 1.0 \pm 10^{-4}$. | M3 (Assembly & Rigging) |
| **Anatomical Pivots** | `src/morphomesh/anatomy/` | Bony landmarks for sternoclavicular notch, acromion, glenohumeral ICR, trochlea, styloid processes, femoral head, bicondylar axis, bimalleolar axis, MTP break. Bone roll aligned to $\vec{n}_{\text{hinge}}$. | M3 (Assembly & Rigging) |
| **Hime Cut Hair** | `src/morphomesh/human_grooming.py` | 6 strata (Bangs $0.13\text{m}$, Sidelocks $0.20\text{m}$, Crown $0.18\text{m}$, Temporal $0.30\text{m}$, Back Cascade $1.00\text{m}$, Facial details); Geometry Nodes modifier network; Melanin 0.85, coat sheen 0.45. | M2 (Grooming & Wardrobe) |
| **Flat Sandals** | `src/morphomesh/wardrobe.py` | Ergonomic curved footbed ($0.235 \times 0.082 \times 0.012\text{m}$); sub-malleolar collar ($Z \le 0.0485\text{m}$); 5 bare toes fully exposed; MTP smoothstep transition weighting between `DEF-foot` and `DEF-toe`. | M2 (Wardrobe) |
| **Marionette Strings** | `src/morphomesh/wardrobe.py` | 10 cords tethered with $0.0\text{mm}$ error to distal fingertip bone tails; exactly 14 vertices per cord; catenary sag $s_{\max} = 0.08 \times \text{chord\_len}$; emission material `#FF1F3D` strength 6.5. | M3 (Props Assembly) |
| **Glowing Butterflies** | `src/morphomesh/wardrobe.py` | 10 swallowtail butterflies; 24 quads each (100% quads); 3D segmented body, antennae, forewings, hindwings with spurs; bilateral upward vortex spiral ($Z \in [0.88, 1.32\text{m}]$, spacing $\ge 150\text{mm}$). | M3 (Props Assembly) |
| **PBR Materials** | `src/morphomesh/human_materials.py` | Random Walk SSS skin (porcelain fair `#F6E4DA`, radius 1.0, 0.2, 0.1, scale 0.024, IOR 1.45); dual-chamber eyes (cornea IOR 1.376, iris IOR 1.336); silk sheen 0.60; satin sash `#C6DEEE` roughness 0.22, anisotropy 0.78. | M4 (Shaders & Beauty) |
| **Beauty Renders** | `src/morphomesh/character_assembler.py` | Cycles 128 spp; AgX color management; 3-point softbox studio lighting (5500K Key 500W, 6500K Fill 250W, 4500K Rim 450W); 85mm portrait camera & 50mm full-body camera. | M4 (Beauty Renders) |
| **Verification Tests** | `src/morphomesh/visual_critic.py` & `tests/` | 0 penetrations ($s_i \ge -0.0005\text{m}$); 100% outward normals ($c_x n_x + c_y n_y > 0$); 100% quads in deforming joints; 100% pytest pass across 1994 tests. | M4 (Final Audit) |
| **Production Exports** | `src/morphomesh/export_manager.py` | `Yu_Nian_An_Master.blend` (>1 MB), `Yu_Nian_An.glb` (>1 MB, 164 joints, 52 morphs, `TEXCOORD_0`), `Yu_Nian_An.fbx` (>1 MB, 163 DEF bones, 52 shape keys), 9 4K textures, `README_EXPORT.md`. | M4 (Deliverables) |

---

## 5. Verification Method

To independently verify the character pipeline and all survey findings, execute the following commands in powershell from the project root (`E:\tool\mcp\MorphoMesh`):

### 5.1 Test Suite Verification Commands

1. **Verify Test Collection Integrity (1,994 tests)**:
   ```powershell
   uv run pytest --collect-only -q
   ```
   *Expected Result*: Exactly 1994 tests collected with exit code 0.

2. **Verify Master Character Assembler & Production Packaging**:
   ```powershell
   uv run pytest -v tests/test_character_assembler.py tests/test_production_exports.py
   ```
   *Expected Result*: All 63 tests PASS with exit code 0.

3. **Verify Wardrobe, Flat Sandals, Marionette Strings & Butterflies**:
   ```powershell
   uv run pytest -v tests/test_wardrobe_m2.py tests/test_wardrobe_m3.py
   ```
   *Expected Result*: All 48 tests PASS with exit code 0.

4. **Verify Hime Cut Hair 6 Strata & Biomechanical Anatomy**:
   ```powershell
   uv run pytest -v tests/test_hime_cut_6_strata.py tests/test_anatomy.py
   ```
   *Expected Result*: All 39 tests PASS with exit code 0.

5. **Verify Penetration & BVH Boundary Defect Detection**:
   ```powershell
   uv run pytest -v tests/test_adversarial_bvh_penetration.py
   ```
   *Expected Result*: All 26 tests PASS with exit code 0.

### 5.2 File & Geometric Inspection Checklist

1. **Rigify 163 DEF Bones**: Inspect `src/morphomesh/human_rigging.py`:
   - Verify `len(BODY_DEF_BONES) == 64`.
   - Verify `len(FACIAL_DEF_BONES) == 99`.
   - Verify `len(ALL_163_DEF_BONES) == 163`.
2. **7-Tier Collection Hierarchy**: Inspect `src/morphomesh/character_assembler.py`:
   - Verify `ROOT_COLLECTION_NAME == "Yu_Nian_An_Master"`.
   - Verify `TIER_COLLECTION_NAMES == ("01_Body", "02_Hair", "03_Wardrobe", "04_Props", "05_Armature", "06_Lights_Camera")`.
3. **Production Assets**: Verify files exist in `output/yu_nian_an/`:
   - `Yu_Nian_An_Master.blend` (size > 1 MB).
   - `Yu_Nian_An.glb` (size > 1 MB).
   - `Yu_Nian_An.fbx` (size > 1 MB).
   - `output/yu_nian_an/textures/` contains all 9 4K PBR textures ($4096 \times 4096$).
   - `output/yu_nian_an/README_EXPORT.md` contains engine import instructions.

### 5.3 Invalidation Conditions

The conclusions of this survey shall be considered invalidated if:
- Any of the 163 DEF bones are renamed, omitted, or duplicated.
- Any deforming joint (knees, elbows, shoulders, hips, fingers, toes) introduces triangular or n-gon faces.
- Any vertex penetration ($s_i < -0.0005\text{m}$) is detected between body, dress, sash, and sandals.
- Inward-pointing face normals ($c_x n_x + c_y n_y \le 0$) occur on exterior visible garment or body surfaces.
- Any test fails in `uv run pytest tests/test_character_assembler.py tests/test_production_exports.py`.
