# Project: MorphoMesh Anatomical Female Human Base Mold & Digital Human Engine (Yu Nian An)

## Architecture
MorphoMesh upgrades to an Anatomical Female Human Base Mold and Digital Human Engine:
1. **Anatomical Base Mold Engine (`src/morphomesh/human_generator.py`)**:
   - Integrates the authoritative CC0 MakeHuman clean female body template (`data/templates/makehuman_clean_body.obj`, 13,380 vertices, 13,378 pure quads, 100% 2-manifold).
   - Seamless organic shoulder-torso-arm topology (24.2° downward trapezius slope), completely replacing the disconnected, capped cylinders that caused the spiky shoulder and armpit gap defect in `media_1788701589498.png`.
   - Realistic teardrop bust with gravity sag, natural inframammary fold, deep cleavage, and gluteal curves with waist-to-hip ratio WHR ~0.697.
   - Articulated 5-toed feet with individual nails and elevated medial plantar arch.
   - Automatic extraction of 70+ anatomical joint landmark centers from `data/templates/makehuman_base.obj` for biomechanical ICR pivot placement.
   - Generates standardized 24+ vertex groups and 52 Apple ARKit FACS blendshapes.
2. **Cloth Simulation Wardrobe Engine (`src/morphomesh/wardrobe.py`)**:
   - Replaces the rigid harmonic sinusoidal cone (`media_1788801618516.png`) with true Blender Cloth Simulation or pre-draped organic cloth geometry.
   - White sundress with fitted sweetheart scoop neckline, double-sided 3D spaghetti straps, and natural gravity/tension draping over thighs and knees.
   - Ice-blue satin sash with barrel cuff knot, 3D hollow bow loops, and cascading ribbons with $+3.5$mm clearance and Surface Deform binding (0% Z-fighting).
   - Ergonomic flat leather strap sandals exposing all 10 bare toes with toenails per `media_1788785935849.jpg`.
3. **Character Assembler & Rigging Engine (`src/morphomesh/character_assembler.py`, `src/morphomesh/human_rigging.py`)**:
   - 7-tier Blender collection hierarchy (`Yu_Nian_An_Master`, `01_Body`, `02_Hair`, `03_Wardrobe`, `04_Props`, `05_Armature`, `06_Lights_Camera`).
   - 6-strata Hime Cut hair system (bangs, sidelocks, back cascade, crown, eyebrows, eyelashes).
   - 10 crimson marionette cords with 0.0mm finger-tail snapping and catenary sag controlling 10 glowing swallowtail butterflies in bilateral vortex spiral flocking.
   - Rigify 163 DEF bones metarig aligned to anatomical ICR landmarks, biological joint pre-bends (elbow +Y 15mm, knee -Y 18mm), and geodesic biharmonic skinning weights summing strictly to 1.0.
4. **Cycles AgX Shaders, Test Suite & Multi-Format Exports (`scripts/build_ultimate_yu_nian_an.py`)**:
   - Cycles Principled BSDF v2 Random Walk SSS skin, dual-chamber refractive eyes, and silk sheen fabric.
   - 3-point softbox studio lighting and AgX view transform.
   - 100% pass across all 1,994 tests in the repository pytest suite (remediating stale literal count assertions and sandal bounding box tolerances).
   - Automated quality verification: 0 penetrations ($s_i \ge -0.0005$m), 100% outward normals ($c_x n_x + c_y n_y > 0$), 100% quads in deforming joints.
   - Multi-format master deliverables: `Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, `Yu_Nian_An.fbx`, and 9 uncompressed 4K PBR textures.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | MakeHuman CC0 Base Mold Clean Extraction | Integrate `data/templates/makehuman_clean_body.obj` (13,380 verts, 13,378 quads, 100% quads, 100% 2-manifold) into `human_generator.py` | M1 | Survey E1, E2 |
| 2 | Organic Teardrop Bust & Inframammary Fold | Teardrop gravity sag, defined inframammary fold, bilateral symmetry, deep cleavage | M1 | Survey E2 |
| 3 | Gluteal Curves & Hourglass WHR ~0.70 | Gluteal projection, physiological lumbar lordosis, feminine waist-to-hip ratio WHR ~0.697 | M1 | Survey E2 |
| 4 | Relaxed Trapezius Shoulders & Soft Arms | 24.2° downward trapezius slope from neck to acromion; seamless arm-torso topology eliminating pauldron spikes in `media_1788701589498.png` | M1 | Survey E1, E2 |
| 5 | Articulated 5-Toed Feet & Plantar Arch | 5 individual ray toes with distinct toenails and elevated medial longitudinal arch | M1 | Survey E2 |
| 6 | 70+ Joint Landmark Extraction from Cubes | Centroid calculation of `joint-*` 8-vertex bounding boxes from `data/templates/makehuman_base.obj` for biomechanical ICR pivots | M1 | Survey E1 |
| 7 | Vertex Groups & ARKit 52 FACS Preservation | Standardized 24+ human vertex groups and ARKit 52 FACS shape keys on the anatomical base mold | M1 | Survey E1, E3 |
| 8 | Sundress Bodice & 3D Spaghetti Straps | Sweetheart scoop neckline bodice conforming to teardrop bust with double-sided slender spaghetti straps | M2 | Survey E2 |
| 9 | Blender Cloth Simulation Skirt Physics | Replace rigid harmonic sine cone (`media_1788801618516.png`) with Blender Cloth Simulation producing organic vertical pipe folds over thighs and knees | M2 | Survey E2 |
| 10 | Ice-Blue Satin Waist Sash & Draping Ribbons | Waist sash with barrel cuff knot, 3D bow loops, and cascading ribbons with $+3.5$mm clearance and Surface Deform binding (0% Z-fighting) | M2 | Survey E1, E2 |
| 11 | Minimalist Flat Strappy Sandals | Ergonomic slim sole following plantar arch, metatarsal strap, ankle wrap, leaving all 10 toes and toenails completely bare per `media_1788785935849.jpg` | M2 | Survey E1, E2 |
| 12 | 6-Strata Hime Cut Hair System | Straight bangs, sidelocks with blunt horizontal cut, flowing back cascade conforming to spine, crown, eyebrows, eyelashes | M3 | Survey E1, E3 |
| 13 | 10 Crimson Marionette Strings | Catenary parabolic curves with 0.0mm snapping to finger bone tips, connecting to 10 butterflies | M3 | Survey E1, E3 |
| 14 | 10 Glowing White Butterflies | Pure-quad swallowtail butterflies in bilateral vortex spiral flocking around the character | M3 | Survey E1, E3 |
| 15 | Rigify 163 DEF Metarig & Biological Pivots | 163 DEF bones aligned to template ICR landmarks, with anti-pinch pre-bends and geodesic biharmonic skinning weights summing strictly to 1.0 | M3 | Survey E1, E3 |
| 16 | Cycles Principled BSDF v2 Random Walk SSS | Realistic fair porcelain skin with subsurface scattering, dual-chamber refractive eyes (cornea IOR 1.376, iris IOR 1.336), silk sheen fabric (sheen weight 0.60) | M4 | Survey E3 |
| 17 | Cycles AgX Studio Lighting & Beauty Renders | 3-point softbox studio lighting (5500K Key, 6500K Fill, 4500K Rim) and AgX view transform for 5 canonical beauty shots | M4 | Survey E3 |
| 18 | Strict Quality Verification (0 Penetrations, Normals, Quads) | Automated checks: BVH signed distance penetration $s_i \ge -0.0005$m, outward normals $c_x n_x + c_y n_y > 0$, 100% quads in deforming joints | M4 | Survey E1, E3 |
| 19 | Test Suite Remediation (100% Pytest Pass) | Fix the 10 failing tests (update stale literal assertions expecting 2,144 vertices to refined base mold, fix sandal bounding box/toe clearance checks) | M4 | Survey E1, E3 |
| 20 | Multi-Format Production Exports | `output/yu_nian_an/Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, `Yu_Nian_An.fbx`, and 9 uncompressed 4K PBR textures | M4 | Survey E1, E3 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Anatomical Female Base Mold | Features 1, 2, 3, 4, 5, 6, 7 (`src/morphomesh/human_generator.py`) | None | DONE |
| M2 | Cloth Simulation Sundress & Wardrobe | Features 8, 9, 10, 11 (`src/morphomesh/wardrobe.py`) | M1 | DONE |
| M3 | Yu Nian An Assembly & Rigify Rigging | Features 12, 13, 14, 15 (`character_assembler.py`, `human_rigging.py`) | M1, M2 | DONE |
| M4 | Shaders, Verification, Tests & Exports | Features 16, 17, 18, 19, 20 (`scripts/build_ultimate_yu_nian_an.py`, tests) | M1, M2, M3 | IN_PROGRESS |

---

## Interface Contracts
### M1 (Base Mold) ↔ M2 (Wardrobe) & M3 (Character Assembler)
- `HumanAnatomyGenerator.generate_human_body(height=1.65, gender="female", proportion_preset="stylized_heroine") -> Tuple[MeshGeometry, Dict[str, Tuple[float, float, float]]]`
- `HumanMeshResult` dataclass:
  - `mesh`: `MeshGeometry` with 13,380 vertices, 13,378 quads, 100% quads, 100% 2-manifold.
  - `vertex_groups`: Mapping of group names (e.g. `"torso"`, `"breast.L"`, `"breast.R"`, `"foot.L"`, `"foot.R"`, etc.) to vertex index lists.
  - `landmarks`: Dictionary of 70+ anatomical pivot coordinates `(x, y, z)` in meters.
  - `shape_keys`: List of ARKit 52 blendshape names.

### M2 (Wardrobe) ↔ M3 (Character Assembler)
- `generate_dress_bodice(body_mesh, landmarks) -> MeshGeometry`: Sweetheart scoop neckline, spaghetti straps.
- `generate_dress_organic_skirt(body_mesh, landmarks, use_cloth_sim=True) -> MeshGeometry`: Naturally draped skirt with organic pipe folds, 0% Z-fighting.
- `generate_dress_waist_sash(body_mesh, landmarks) -> MeshGeometry`: Ice-blue sash with knot and cascading ribbons (+3.5mm clearance).
- `generate_flat_strappy_sandals(body_mesh, landmarks) -> MeshGeometry`: Flat sandals with bare exposed toes.

### M3 (Assembly & Rigging) ↔ M4 (Shaders & Exports)
- `build_ultimate_yu_nian_an.py`: Assembles all 7 collections, applies Rigify 163 DEF armature, configures Cycles Random Walk SSS skin, silk sheen, and exports master `.blend`, `.glb`, and `.fbx` files.

---

## Code Layout
- `src/morphomesh/human_generator.py`: Anatomical Female Base Mold engine.
- `src/morphomesh/wardrobe.py`: Sundress, cloth simulation, sash, sandals, butterflies, crimson strings.
- `src/morphomesh/human_rigging.py`: Rigify 163 DEF metarig, ICR pivot alignment, anti-pinch skinning weights.
- `src/morphomesh/character_assembler.py`: 7-tier scene collection hierarchy, scene builder.
- `scripts/build_ultimate_yu_nian_an.py`: Master generation, shader assignment, and export script.
- `tests/`: Pytest verification suite (unit and regression tests).
- `output/yu_nian_an/`: Final production delivery artifacts (`Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, `Yu_Nian_An.fbx`, render images).
