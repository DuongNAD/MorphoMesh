# Project: MorphoMesh Human Anatomy & Yu Nian An Character Realism Upgrade

## Architecture
This project establishes a medical-grade anatomical reconstruction and high-fidelity photorealistic upgrade of the Yu Nian An 3D digital human character within MorphoMesh and Blender:
1. **Anatomical Body & Rigify DEF Rigging Subsystem**:
   - `src/morphomesh/human_generator.py`: Generates female body mesh with authentic skeletal landmarks (clavicle S-curve, jugular notch, ribcage arch, flared pelvic crest/ASIS, patella knee joint, asymmetric medial/lateral malleoli) and fully articulated 5-toed feet with convex toenails, triple plantar arches, and interdigital clefts.
   - `src/morphomesh/human_rigging.py`: Strict 163 DEF bone Rigify metarig with biologically realigned joint pivots (femoral head hip, condylar knee hinge, oblique bimalleolar ankle axis, oblique MTP break line) and zero-volume-loss skinning weights.
2. **Organic Wardrobe & Drapery Subsystem**:
   - `src/morphomesh/wardrobe.py`: Eliminates rigid 20-wave cosine pleats. Implements organic multi-harmonic gravity folds, scalloped hemline, anatomical upper bodice with bilateral teardrop breast cups, cleavage indent, sweetheart scoop neckline, 3D conforming spaghetti straps, and 100% conforming ice-blue sash envelope with 3D bow knot and ribbon streamers (0% Z-fighting). Adds normalized Rigify vertex groups for pose deformation.
3. **Footwear, Hair & Signature Props Subsystem**:
   - `src/morphomesh/wardrobe.py` & `src/morphomesh/character_assembler.py`: Thin 7mm laminated leather flat sandals with 4-band strap configuration leaving all 5 toes 100% exposed. 10 crimson magic threads linked from distal finger phalanx bones to 10 glowing white butterflies with emission and flutter.
   - `src/morphomesh/human_grooming.py`: 6-stratum hime cut hair curves (blunt bangs, sidelocks, cascading strands).
4. **PBR Shaders, Lighting & Master Production Packaging**:
   - `src/morphomesh/human_materials.py`: Principled BSDF with Random Walk SSS skin, Charlie sheen for silk dress, high sheen ice-blue satin for sash, and new `Mat_Human_Nails` translucent keratin shader.
   - `src/morphomesh/camera_rig.py` & `scripts/build_and_render_master.py`: 3-point studio lighting (Key, Fill, Rim) with tracking target, 4 canonical full-body turnaround cameras, portrait and close-up cameras.
   - Master export pipeline producing `Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, `Yu_Nian_An.fbx`, multi-angle beauty renders, and 100% passing test suites in `tests/`.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | Clavicle S-Curve & Suprasternal Notch | Prominent S-curve collarbone under neck and distinct jugular hollow along Z=1.350m-1.370m | M1 | Survey E1, User Guidance |
| 2 | Ribcage & Flared Pelvic Crest / ASIS | Sternal angle, costal margin, and flared iliac crest expansion at Z=0.825m-0.900m | M1 | Survey E1 |
| 3 | Patella Knee Joint & Bilateral Recesses | Sculpted anterior patellar facet and distinct medial/lateral knee hollows at Z=0.445m | M1 | Survey E1, User Guidance |
| 4 | Asymmetric Malleoli & Wrist Styloid | Medial/lateral ankle malleoli (asymmetric height) + radial/ulnar styloid processes at wrists | M1 | Survey E1, User Guidance |
| 5 | Elbow Olecranon & Cubital Fold | Sculpted olecranon elbow protrusion and natural anterior cubital crease | M1 | User Guidance |
| 6 | Mandible Jawline, V-Line Chin & Angle | Sculpted jawline, refined V-line chin, and defined mandibular angle separating neck | M1 | User Guidance |
| 7 | Teardrop Breast Profile & Cleavage | Bilateral teardrop breast cups with gentle clavicle slope and natural cleavage cleft | M1 | Survey E2, User Guidance |
| 8 | Anatomical 5 Articulated Toes & Nails | 5 distinct toes with phalangeal proportions, convex toenails, and interdigital cleft | M1 | Survey E1 |
| 9 | Triple Plantar Arch Architecture | Medial longitudinal high arch (+6mm), lateral balance arch, and transverse arch | M1 | Survey E1 |
| 10 | Rigify 163 DEF Biological Pivots | Calibrated pivots: hip (+0.038m), knee condylar axis, oblique bimalleolar ankle | M1 | Survey E1 |
| 11 | Patella & Malleoli Skin Weight Anchoring | Locking patella to shin (>=92%) and anchoring malleoli to shin (>=80%) | M1 | Survey E1 |
| 12 | Multi-Harmonic Skirt Gravity Folds | Organic folds (n=6,8,12) replacing rigid cosine pleats, anterior thigh flattening | M2 | Survey E2 |
| 13 | Undulating Scalloped Skirt Hemline | Variable gravity sag with amplitude ~14mm replacing flat planar hem | M2 | Survey E2 |
| 14 | Sweetheart Scoop Neckline & 3D Straps | Sculpted sweetheart rim curve (Z=1.185m-1.255m) and 3D shoulder-conforming straps | M2 | Survey E2 |
| 15 | 100% Conforming Ice-Blue Sash Envelope | Strict +2.5mm outer waist envelope eliminating Z-fighting and mesh clipping | M2 | Survey E2 |
| 16 | 3D Volumetric Bow Knot & Ribbons | Dimensional knot with left/right bow loops and cascading flowing ribbon streamers | M2 | Survey E2 |
| 17 | Rigify Vertex Groups on Dress Meshes | Normalized vertex groups mapped to DEF-spine.* and DEF-thigh.* for pose deformation | M2 | Survey E2 |
| 18 | UV Seam Wrap Continuous Mapping | Duplicate seam vertices at u=1.0 eliminating backward texture distortion | M2 | Survey E2 |
| 19 | Flat Strappy Sandals 7mm Sole & Arch | Thin laminated leather sole with +6mm medial arch rise conforming to foot bottom | M3 | Survey E3 |
| 20 | 4-Band Sandal Straps Exposing 5 Toes | Straps across instep, ankle collar, heel counter leaving toes 100% exposed | M3 | Survey E3 |
| 21 | 10 Crimson Magic Threads | Catenary Bezier curves snapped to distal finger phalanx DEF bones | M3 | Survey E3 |
| 22 | 10 Glowing White Butterflies in Flight | Procedural quad butterflies with wing flutter, 3.5 emission, and translucent SSS | M3 | Survey E3 |
| 23 | 6-Stratum Hime Cut Hair System | Blunt bangs, sidelocks, crown, and cascading strands with Melanin Hair BSDF | M3 | Survey E3 |
| 24 | Random Walk SSS Skin Material | Warm subcutaneous scattering (0.28 SSS radius, 0.48 roughness) | M4 | Survey E3 |
| 25 | Silk Sheen Dress & Ice-Blue Satin Sash | Charlie sheen (0.60) for dress, high sheen (0.90) ice-blue (0.65, 0.78, 0.90) for sash | M4 | Survey E2, E3 |
| 26 | Translucent Keratin Nail Shader | Mat_Human_Nails with SSS 0.35, roughness 0.22, coat 0.50 for finger/toenails | M4 | Survey E1, E3 |
| 27 | 3-Point Studio Lighting Rig | Key (5500K, 500W), Fill (6500K, 250W), Rim (4500K, 450W) with tracking constraint | M4 | Survey E3 |
| 28 | Multi-Angle Cameras & Beauty Renders | Front, 3/4, Side, Back, Portrait, Feet close-up, and Hands close-up | M4 | Survey E3 |
| 29 | Master Asset Packaging & Regeneration | Yu_Nian_An_Master.blend, .glb, .fbx with intact Rigify hierarchy and 100% tests pass | M4 | Survey E3 |
| 30 | Comprehensive Pytest Suite & E2E Validation | 100% passing tests across all test suites in tests/ | M4 | Survey E3 |
| 31 | E2E Testing Suite (Tiers 1-4) & Adversarial Audit | Systematic opaque-box test suite + Tier 5 white-box coverage hardening | M5 | Project Pattern |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Medical-Grade Human Anatomy & Rigify 163 DEF Rigging (R1) | Features 1-11: Clavicle, ribcage, pelvis, patella & recesses, malleoli & wrist styloid, elbow olecranon, mandible V-line, teardrop bust, 5 articulated toes & nails, triple arches, biological pivots, skinning weight anchoring | None | IN_PROGRESS |
| M2 | Realistic Organic Dress Drapery & Ice-Blue Sash (R2) | Features 12-18: Multi-harmonic gravity folds, scalloped hem, sweetheart scoop, 3D straps, conforming sash envelope, 3D bow & ribbons, dress DEF vertex groups, UV seam fix | M1 | PLANNED |
| M3 | Flat Strappy Sandals & Signature Props (R3) | Features 19-23: Flat strappy sandals (7mm sole, 4 bands, exposed toes), 10 red threads from fingers, 10 glowing butterflies, 6-stratum hime cut hair | M1 | PLANNED |
| M4 | PBR Cycles Shaders, Studio Lighting, Master Export & Verification (R4) | Features 22-28: Random Walk SSS skin, silk & ice-blue satin shaders, keratin nail shader, 3-point lighting, multi-angle renders, master export (.blend, .glb, .fbx), 100% pytest pass | M2, M3 | PLANNED |
| M5 | Final E2E Suite & Adversarial Hardening | Feature 29: Full E2E validation (Tiers 1-4) and Tier 5 white-box adversarial coverage hardening | M4 | PLANNED |

---

## Interface Contracts

### `src/morphomesh/human_generator.py` ↔ `src/morphomesh/human_rigging.py`
```python
def generate_human_body(
    height: float = 1.65,
    gender: str = "female",
    proportion_preset: str = "stylized_heroine",
) -> Tuple[Any, Dict[str, Any]]:
    """Generates female body with skeletal landmarks and 5 articulated toes.
    Returns:
        mesh: BMesh-compatible ProceduralMesh containing body vertices and quad faces.
        landmarks: Dict mapping anatomical landmark names to (x, y, z) coordinates:
            'clavicle_L/R', 'jugular_notch', 'pelvic_crest_L/R', 'patella_L/R',
            'malleolus_medial_L/R', 'malleolus_lateral_L/R', 'heel_L/R',
            'toe_big_L/R', 'toe_second_L/R', 'toe_third_L/R', 'toe_fourth_L/R', 'toe_fifth_L/R'.
    """

def align_rigify_metarig_pivots(
    armature_obj: Any,
    landmarks: Dict[str, Tuple[float, float, float]],
    scale: float = 1.0,
) -> None:
    """Realigns 163 DEF Rigify metarig joint pivots to anatomical positions:
    - Femoral head hip joint: Z = z_pelvic_crest - 0.082m, Y = -0.010m
    - Condylar knee hinge: Z = z_patella - 0.025m, Y = -0.008m (behind patella)
    - Oblique bimalleolar ankle: connecting medial and lateral malleoli landmarks
    - MTP break axis: oblique angle ~65 degrees across metatarsal heads
    """
```

### `src/morphomesh/wardrobe.py` ↔ `src/morphomesh/human_generator.py`
```python
def generate_organic_dress(
    scale: float = 1.0,
    k_waist: float = 1.0,
    k_chest: float = 1.0,
    k_leg: float = 1.0,
    bust_cup_scale: float = 1.0,
) -> Dict[str, Any]:
    """Generates one-piece organic dress with bilateral teardrop cups,
    sweetheart neckline, 3D straps, multi-harmonic gravity folds, and scalloped hem.
    Returns mesh components with Rigify DEF vertex groups.
    """

def generate_waist_sash_and_bow(
    dress_waist_bounds: Dict[str, float],
    scale: float = 1.0,
    k_waist: float = 1.0,
) -> Dict[str, Any]:
    """Generates 100% conforming outer sash envelope (+2.5mm clearance)
    with 3D bow knot, dual loops, and cascading ribbons.
    """

def generate_flat_strappy_sandals(
    foot_landmarks: Dict[str, Tuple[float, float, float]],
    scale: float = 1.0,
    k_leg: float = 1.0,
) -> Dict[str, Any]:
    """Generates thin 7mm laminated leather flat sandals with 4-band strap layout,
    leaving all 5 toes completely exposed.
    """
```

### `src/morphomesh/human_materials.py` ↔ `src/morphomesh/character_assembler.py`
```python
def get_yu_nian_an_material_palette() -> Dict[str, HumanMaterialConfig]:
    """Returns complete PBR material dictionary including:
    - 'Mat_Skin_Body': Random Walk SSS (0.28 radius, warm peach porcelain)
    - 'Mat_Dress_Silk': Charlie sheen silk (base_color=(0.95, 0.95, 0.96, 1.0), sheen=0.60)
    - 'Mat_Dress_WaistBelt': Ice-blue satin (base_color=(0.65, 0.78, 0.90, 1.0), sheen=0.90, roughness=0.20)
    - 'Mat_Human_Nails': Translucent keratin (base_color=(0.92, 0.80, 0.80, 1.0), SSS=0.35, roughness=0.22, coat=0.50)
    - 'Mat_Sandal_Leather': Supple leather (base_color=(0.35, 0.25, 0.20, 1.0), roughness=0.45)
    - 'Mat_Butterfly_Glow': Emissive white wings (emission_strength=3.5, SSS=0.45)
    - 'Mat_Red_Thread': Crimson thread (base_color=(0.85, 0.05, 0.05, 1.0), emission_strength=1.2)
    """
```

---

## Code Layout
- `src/morphomesh/human_generator.py`: Anatomical body generator, skeletal landmarks, 5-toed articulated foot sculpting.
- `src/morphomesh/human_rigging.py`: 163 DEF Rigify metarig, biological joint pivot alignment, skinning vertex weights.
- `src/morphomesh/wardrobe.py`: Organic dress drapery, bust sculpting, ice-blue sash & bow, flat strappy sandals, red threads, glowing butterflies.
- `src/morphomesh/human_grooming.py`: 6-stratum hime cut hair curves.
- `src/morphomesh/human_materials.py`: PBR shader configurations (SSS skin, silk, satin, keratin nails, emission).
- `src/morphomesh/camera_rig.py`: 3-point lighting rig and multi-angle production cameras.
- `src/morphomesh/character_assembler.py`: Scene assembly and export pipeline for `Yu_Nian_An_Master.blend`, `.glb`, `.fbx`.
- `tests/`: Pytest verification suites.
