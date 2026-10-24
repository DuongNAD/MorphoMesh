# E2E Test Infra: MorphoMesh Human Anatomy & Character Realism Upgrade

## Test Philosophy
- **Opaque-Box & Requirement-Driven**: Tests interact exclusively through public APIs and observable contracts (`src/morphomesh/human_generator.py`, `src/morphomesh/human_rigging.py`, `src/morphomesh/wardrobe.py`, `src/morphomesh/human_grooming.py`, `src/morphomesh/human_materials.py`, `src/morphomesh/camera_rig.py`, `src/morphomesh/character_assembler.py`).
- **Zero Mock Hacks**: Tests evaluate genuine 3D geometric meshes, vertex positions, normal vectors, bone structures, vertex groups, and physical material parameters.
- **Mathematical Invariants**: Hard requirements enforced via geometric and physical formulas (volume preservation ratios $\ge 0.90$, 0% Z-fighting / 0 penetrations, UV bounds $[0.0, 1.0]$, 163 DEF bones invariant, 5 distinct toes with phalanges).
- **Authoritative Source of Truth**: All expected outputs and tolerances derived from `ORIGINAL_REQUEST.md` (timestamp `## 2026-09-07T13:01:03Z`), `PROJECT.md`, and anatomical reference specifications.

---

## 4-Tier Test Methodology

### Tier 1: Feature Coverage (Category-Partition)
- **Rule**: Minimum 5 distinct test cases / assertions per feature in scope.
- **Scope**:
  - Clavicle S-curve and suprasternal (jugular) notch existence.
  - Pelvic crest, ASIS, and ribcage arch presence.
  - Patella knee joint facet and condylar contours.
  - Asymmetric ankle malleoli heights (medial higher/anterior, lateral lower/posterior).
  - 5 distinct articulated toes with phalangeal proportions, convex toenails, and interdigital clefts.
  - Triple plantar arches (medial longitudinal arch, lateral balance arch, transverse arch).
  - Rigify 163 DEF bones metarig invariant with biological joint pivots.
  - Patella and malleoli skin weight rigid anchoring.
  - Multi-harmonic organic dress gravity folds and scalloped hemline.
  - Bilateral teardrop breast cups, cleavage indent, sweetheart scoop neckline, and 3D straps.
  - 100% conforming ice-blue sash envelope (+2.5mm clearance) and 3D bow knot with ribbons.
  - Thin 7mm laminated leather flat sandals leaving all 5 toes 100% exposed.
  - 10 crimson magic marionette threads linked to finger distal phalanx bones.
  - 10 glowing white butterflies with emission and flutter.
  - 6-stratum hime cut hair curves system.
  - PBR Random Walk SSS skin shader, Charlie sheen silk dress, satin sash, and translucent keratin nail shader (`Mat_Human_Nails`).
  - 3-point studio lighting rig and multi-angle turnaround cameras.
  - Master production export validation (`Yu_Nian_An_Master.blend`, `.glb`, `.fbx`).

### Tier 2: Boundary & Corner Cases (Boundary Value Analysis - BVA)
- **Rule**: Minimum 5 boundary tests per feature.
- **Scope**:
  - Extreme character scaling boundaries: height $1.40\text{m}$ (petite) to $1.95\text{m}$ (heroic stature), head ratios $6.0$ to $9.0$.
  - Extreme body morphing: bust scale ($0.5\times$ to $2.0\times$), waist-to-hip ratio ($0.60$ to $0.85$).
  - 90-degree extreme joint flexions (thigh flexion, knee flexion, ankle dorsiflexion/plantarflexion) asserting volume preservation ratio $\ge 0.90$ and zero NaN/Inf vertex coordinates.
  - Garment clearance tolerance boundaries: bodice clearance $[0.005\text{m}, 0.030\text{m}]$, sash outer envelope $+0.0025\text{m}$ asserting 0 penetrations and 0% Z-fighting.
  - UV coordinate bounds strictly clamped inside $[0.0, 1.0]$ without continuous wrap seam distortion.

### Tier 3: Cross-Feature Combinations (Pairwise Combinatorial)
- **Rule**: Minimum 4 integrated interaction suites across subsystems.
- **Scope**:
  - **Subsystem Pair 1**: 5-toed articulated foot + flat strappy sandals + ankle rig flexion (no clipping between straps and toes during motion).
  - **Subsystem Pair 2**: Organic dress + ice-blue sash + Rigify spine and hip pose deformation (outer sash maintains positive radial clearance over dress).
  - **Subsystem Pair 3**: 10 crimson threads + distal finger phalanx DEF bones + butterfly emissive flight positions.
  - **Subsystem Pair 4**: Random Walk SSS skin + translucent nail keratin shader + 3-point studio lighting (energy conservation and BSDF consistency).

### Tier 4: Real-World Application Scenarios (Full Pipeline Workload)
- **Rule**: Minimum 5 complete end-to-end production scenarios.
- **Scope**:
  - Scenario 1: Default canonical Yu Nian An full generation and assembly.
  - Scenario 2: Parametric custom heroine generation, rigging, dressing, and export.
  - Scenario 3: Beauty render turnaround framing across 4 inspection cameras.
  - Scenario 4: Master asset disk serialization and manifest integrity check.
  - Scenario 5: MCP server and Blender Bridge end-to-end execution simulation.

---

## Anatomical Assertion Specifications (User Guidance)

In accordance with direct user guidance, the following anatomical criteria are strictly evaluated:
1. **Nét ngực (Breast Contours)**:
   - Bilateral teardrop breast profile curvature with natural anterior convexity ($Y < -0.09\text{m}$).
   - Medial cleavage cleft presence ($X \in [-0.015, 0.015]\text{m}$ indented relative to apexes).
   - Gentle anatomical slope descending continuously from clavicle ($Z=1.35\text{m}$) into upper breast poles ($Z=1.22\text{m}$).
2. **Xương quai xanh & Hõm ức (Clavicles & Suprasternal Notch)**:
   - Bilateral clavicular S-curve ridges extending laterally between $X=\pm 0.045\text{m}$ and $X=\pm 0.175\text{m}$ along $Z \in [1.340, 1.365]\text{m}$.
   - Suprasternal (jugular) notch depth forming a distinct central recess at $X=0.0\text{m}, Z \approx 1.350\text{m}-1.365\text{m}$.
3. **Nét khớp chân tay (Limb Joint Contours)**:
   - **Khớp gối (Knee)**: Sculpted patella anterior facet ($Y \le -0.020\text{m}$) and lateral/medial condylar joint recesses.
   - **Khớp khuỷu tay (Elbow)**: Posterior olecranon protrusion ($Y > 0.010\text{m}$) and natural anterior cubital fossa fold.
   - **Cổ chân & Cổ tay (Ankle & Wrist)**: Asymmetric bimalleolar heights (medial malleolus higher/anterior, lateral malleolus lower/posterior) and radial/ulnar styloid processes at wrist boundaries.
4. **Nét hàm & Cằm (Mandibular Contour & Chin)**:
   - Mandibular jawline contour sweeping cleanly toward the gonial angle.
   - Feminine V-line chin sharpness with distinct anterior projection ($Y \approx -0.065\text{m}$).
   - Clear submental angle separating jawline from the cervical neck column ($Z=1.40\text{m}-1.44\text{m}$).

---

## Feature Inventory & Test Coverage Matrix

| # | Feature | Requirement | Milestone | Tier 1 (Coverage) | Tier 2 (BVA) | Tier 3 (Pairwise) | Tier 4 (E2E Scenario) |
|---|---------|-------------|:---------:|:-----------------:|:------------:|:-----------------:|:---------------------:|
| 1 | Clavicle S-Curve & Suprasternal Notch | R1 §Anatomy | M1 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 2 | Ribcage & Flared Pelvic Crest / ASIS | R1 §Anatomy | M1 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 3 | Patella Knee Joint & Condylar Contour | R1 §Anatomy | M1 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 4 | Asymmetric Ankle Malleoli | R1 §Anatomy | M1 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 5 | Anatomical 5 Articulated Toes & Nails | R1 §Anatomy | M1 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 6 | Triple Plantar Arch Architecture | R1 §Anatomy | M1 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 7 | Rigify 163 DEF Biological Pivots | R1 §Rigging | M1 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 8 | Patella & Malleoli Skin Weight Anchoring | R1 §Rigging | M1 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 9 | Multi-Harmonic Skirt Gravity Folds | R2 §Dress | M2 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 10 | Undulating Scalloped Skirt Hemline | R2 §Dress | M2 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 11 | Bilateral Teardrop Breast Cups & Cleavage | R2 §Bodice | M2 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 12 | Sweetheart Scoop Neckline & 3D Straps | R2 §Bodice | M2 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 13 | 100% Conforming Ice-Blue Sash Envelope | R2 §Sash | M2 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 14 | 3D Volumetric Bow Knot & Ribbons | R2 §Sash | M2 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 15 | Rigify Vertex Groups on Dress Meshes | R2 §Deformation | M2 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 16 | UV Seam Wrap Continuous Mapping | R2 §Texture | M2 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 17 | Flat Strappy Sandals 7mm Sole & Arch | R3 §Footwear | M3 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 18 | 4-Band Sandal Straps Exposing 5 Toes | R3 §Footwear | M3 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 19 | 10 Crimson Magic Threads | R3 §Props | M3 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 20 | 10 Glowing White Butterflies in Flight | R3 §Props | M3 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 21 | 6-Stratum Hime Cut Hair System | R3 §Hair | M3 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 22 | Random Walk SSS Skin Material | R4 §PBR | M4 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 23 | Silk Sheen Dress & Ice-Blue Satin Sash | R4 §PBR | M4 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 24 | Translucent Keratin Nail Shader | R4 §PBR | M4 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 25 | 3-Point Studio Lighting Rig | R4 §Studio | M4 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 26 | Multi-Angle Cameras & Beauty Renders | R4 §Cameras | M4 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 27 | Master Asset Packaging & Regeneration | R4 §Export | M4 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 28 | Comprehensive Pytest Suite & E2E Validation | Acceptance | M4 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |
| 29 | E2E Testing Suite (Tiers 1-4) & Audit | Acceptance | M5 | $\ge 5$ | $\ge 5$ | ✓ | ✓ |

---

## Test Architecture & Invocation

### Directory Layout
```
MorphoMesh/
├── src/morphomesh/
│   ├── human_generator.py      # Female anatomy, skeletal landmarks, 5-toed articulated foot
│   ├── human_rigging.py        # 163 DEF Rigify metarig & biological pivots
│   ├── wardrobe.py             # Organic dress, ice-blue sash, flat sandals, props
│   ├── human_grooming.py       # 6-stratum hime cut hair curves
│   ├── human_materials.py      # Principled BSDF v2 PBR shaders
│   ├── camera_rig.py           # 3-point studio lighting & multi-angle cameras
│   └── character_assembler.py  # Master collection hierarchy & export pipeline
├── tests/
│   ├── test_e2e_human_anatomy.py # Authoritative E2E opaque-box test suite (Tiers 1-4)
│   ├── test_human_generator.py
│   ├── test_human_rigging.py
│   ├── test_wardrobe.py
│   ├── test_human_materials.py
│   ├── test_human_grooming.py
│   └── test_character_assembler.py
├── TEST_INFRA.md               # This document
└── TEST_READY.md              # Test execution report and coverage audit
```

### Execution Commands
```powershell
# Run the complete authoritative E2E suite
pytest tests/test_e2e_human_anatomy.py -v

# Run individual tiers
pytest tests/test_e2e_human_anatomy.py -k "TestTier1" -v
pytest tests/test_e2e_human_anatomy.py -k "TestTier2" -v
pytest tests/test_e2e_human_anatomy.py -k "TestTier3" -v
pytest tests/test_e2e_human_anatomy.py -k "TestTier4" -v
```
