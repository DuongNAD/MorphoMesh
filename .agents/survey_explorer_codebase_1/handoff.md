# Codebase Structure Survey & Architectural Assessment Report

**Agent**: Survey Explorer 1 (Codebase Structure)  
**Date**: 2026-09-08T00:35:00+07:00  
**Target Path**: `E:\tool\mcp\MorphoMesh\.agents\survey_explorer_codebase_1\handoff.md`  
**Parent Orchestrator**: `79a32aca-3f45-4f6c-ae9e-59087d07960a` (orchestrator_female_mold_1)

---

### Executive Summary
The MorphoMesh repository is a mature, production-grade codebase comprising ~20 Python modules in `src/morphomesh/`, an interactive Blender TCP socket bridge (port 9876) and headless CLI runner in `blender_bridge.py`, a 17-tool FastMCP server in `server.py`, and a rigorous 1,994-test pytest suite (currently 1,972 passing, 10 failing due to stale literal assertions). The primary structural cause of the user-reported defects (`media_1788701589498.png` angular shoulders/arms and `media_1788801618516.png` rigid lampshade skirt) stems from: (1) purely trigonometric procedural cross-sectional slicing in `human_generator.py` and ad-hoc material-slot polygon deletion in `build_ultimate_yu_nian_an.py`; and (2) harmonic sinusoidal ring expansion in `wardrobe.py` rather than physics-based cloth simulation. The repository already contains an authoritative MakeHuman base mesh (`data/templates/makehuman_base.obj`, 19,158 verts, 18,486 pure quads, 139 groups, 70+ joint landmark cubes) and its extracted clean naked female body (`data/templates/makehuman_clean_body.obj`, 13,380 verts, 13,378 quads, 100% quads), ready for seamless integration as the anatomical base mold.

---

## 1. Observation

### 1.1 Human & Mesh Generation Subsystem (`src/morphomesh/`)

#### A. `src/morphomesh/human_generator.py` (1,780 lines, 84.1 KB)
- **Primary Class**: `HumanAnatomyGenerator(config: Optional[HumanAnatomyConfig] = None)`
  - Uses vertical mathematical slicing along the Z-axis:
    - Pelvis/crotch: `z in [0.825, 0.900]`
    - Waist: `z in [0.940, 1.050]`
    - Chest/breasts: `z in [1.110, 1.270]`
    - Upper torso / clavicle: `z in [1.270, 1.350]`
    - Neck: `z in [1.350, 1.450]`
    - Head & cranium: `z in [1.450, 1.650]`
  - Upper limbs and digits are procedurally extruded in lines 834–957:
    - 5 digits per hand (thumb + 4 fingers, 3 phalanges each)
  - Lower limbs and articulated feet in lines 567–832:
    - 5 articulated toes per foot with plantar arch definition
  - Generates 24+ standardized vertex groups (`STANDARDIZED_HUMAN_VERTEX_GROUPS` in lines 33–68)
  - Generates 52 Apple ARKit FACS blendshapes (`ARKIT_52_BLENDSHAPES` in lines 70–84)
  - Output: `HumanMeshResult` dataclass (lines 88–106) containing `mesh: MeshGeometry`, `vertex_groups`, `landmarks`, `shape_keys`, and `shape_key_deltas`. Currently yields 2,736 vertices and 2,588 polygons (100% quads).
- **Blender Script Generator**: `get_human_generation_script(mesh_obj_name, config)` (lines 1108–1762)
  - Emits executable Blender Python (`bpy` + `bmesh`) script constructing the mesh inside Blender, attaching vertex groups, shape keys, and custom property `morphomesh_extended_landmarks`.
- **API Entrypoint**: `generate_human_body(height=1.65, gender="female", proportion_preset="stylized_heroine")` returning `(MeshGeometry, Dict[str, Tuple[float, float, float]])`.

#### B. `src/morphomesh/human_rigging.py` (1,643 lines, 72.4 KB)
- Implements Rigify Human Metarig with all 163 DEF bones (`ALL_163_DEF_BONES`):
  - Head/face: 82 DEF bones (jaw, chin, cheeks, brow, eyes, lips, tongue)
  - Spine & torso: 7 DEF bones (pelvis, spine, spine.001, spine.002, spine.003, breast.L, breast.R)
  - Upper limbs: 40 DEF bones (clavicle, shoulder, upper_arm, forearm, hand, 5 fingers × 3 phalanges × 2 sides)
  - Lower limbs: 34 DEF bones (thigh, shin, foot, toe, 5 toes × 2 phalanges × 2 sides)
- `align_rigify_metarig_pivots()` (lines 687–813): Biomechanical ICR pivot placement with anti-pinch pre-bends (elbows bend back, knees bend forward).
- `calculate_anti_pinch_weights()` (lines 814–1188): Dual quaternion geodesic biharmonic skinning weights across all 163 DEF vertex groups.
- `generate_arkit_52_blendshapes()` (lines 1189–1404): Displacements for all 52 FACS shape keys.

#### C. `src/morphomesh/wardrobe.py` (2,143 lines, 86.3 KB)
- Generates the complete Yu Nian An wardrobe components:
  - `generate_dress_bodice()` (lines 347–587): Sweetheart scoop neckline, 3D spaghetti straps, teardrop bust conforming profile.
  - `generate_dress_waist_sash()` (lines 588–882): Ice-blue satin waist sash with barrel-cuff knot, 3D hollow bow loops, and cascading ribbons.
  - `generate_dress_organic_skirt()` (lines 883–992): Flared skirt using harmonic sine formulas (`a1 * sin(6*theta)`, `a2 * sin(8*theta)`, `a3 * sin(12*theta)`).
  - `generate_flat_strappy_sandals()` (lines 1073–1490): Sole bed, instep strap, ankle wrap, heel counter.
  - `generate_catenary_magic_strings()` (lines 1545–1672): 10 parabolic catenary crimson strings connecting finger DEF tails to butterflies.
  - `generate_swallowtail_quad_butterfly()` (lines 1673–1795): 10 glowing swallowtail butterflies in vortex spiral flocking.

#### D. `src/morphomesh/character_assembler.py` (2,373 lines, 101.1 KB)
- Implements 7-Tier Collection Hierarchy (`ALL_SEVEN_COLLECTIONS`):
  1. `Yu_Nian_An_Master` (Root)
  2. `01_Body` (`Yu_Nian_An_Body`, eyes, eyelids, lips)
  3. `02_Hair` (6 strata: `Hair_Hime_Bangs`, `Hair_Hime_Sidelocks`, `Hair_Back_Cascade`, `Hair_Scalp_Crown`, `Hair_Eyebrows`, `Hair_Eyelashes`)
  4. `03_Wardrobe` (`Mesh_Dress_Bodice`, `Mesh_Dress_WaistSash`, `Mesh_Dress_PleatedSkirt`, sandals)
  5. `04_Props` (10 marionette strings, 10 butterflies)
  6. `05_Armature` (`Armature_Yu_Nian_An_Rigify`)
  7. `06_Lights_Camera` (3-point studio softboxes, rim lights, AgX cameras)
- `export_production_assets()`: Exports `.blend`, `.fbx`, `.glb`, and 4K PBR texture atlas.

---

### 1.2 Templates & Base Meshes Inventory (`data/templates/`)

Direct inspection via Python scripts and OBJ parser revealed:

| File Path | Size | Vertices | Polygons | Quad % | Groups | Description |
|---|---|---|---|---|---|---|
| `data/templates/makehuman_base.obj` | 1,749,303 B (1.75 MB) | 19,158 | 18,486 | **100.0%** (18,486 quads, 0 tris) | 139 | Complete MakeHuman female base mesh with helpers (`helper-tights`, `helper-skirt`, `helper-hair`, etc.) and 70+ joint landmark cubes (`joint-head`, `joint-l-finger-*`, `joint-l-toe-*`). |
| `data/templates/makehuman_clean_body.obj` | 689,633 B (690 KB) | 13,380 | 13,378 | **100.0%** (13,378 quads, 0 tris) | 1 (`body`) | Clean extracted naked female body mesh. 100% pure quads. No helpers, no clothes, no internal mouth/teeth geometry. |
| `output/yu_nian_an/Yu_Nian_An_tripo.glb` | 44,945,820 B (44.9 MB) | ~35,000 | ~70,000 | ~0% (Tris) | TripoSR | Dense scanned/AI mesh with PBR textures. |
| `output/yu_nian_an/AliciaSolid.vrm` | 7,878,712 B (7.88 MB) | ~22,000 | ~35,000 | Mixed | VRoid | Stylized reference character. |

#### Coordinate System Analysis of MakeHuman Assets:
- `makehuman_clean_body.obj` bounding box:
  - $X \in [-4.9627, +4.9627]$ (Lateral span = 9.9254 decimeters $\approx 0.992$ m)
  - $Y \in [-8.1676, +8.4913]$ (Vertical height = 16.6589 decimeters $\approx 1.666$ m)
  - $Z \in [-1.0154, +3.2147]$ (Sagittal depth = 4.2301 decimeters $\approx 0.423$ m)
- Transformation Matrix to Blender 4.5+ standard (Z-up, Y-forward/depth, X-lateral, meters, feet at $Z=0$):
  $$\begin{bmatrix} X_{\text{blender}} \\ Y_{\text{blender}} \\ Z_{\text{blender}} \end{bmatrix} = \begin{bmatrix} 0.1 \cdot X_{\text{mh}} \\ -0.1 \cdot Z_{\text{mh}} \\ 0.1 \cdot (Y_{\text{mh}} + 8.1676) \end{bmatrix}$$
- Joint Landmark Centroids in `makehuman_base.obj`:
  - Each `joint-<name>` group consists of exactly 8 vertices forming a rectangular cuboid bounding box whose centroid $\frac{1}{8}\sum_{i=1}^8 \vec{v}_i$ yields the exact anatomical joint pivot.
  - Verified centroids:
    - `joint-head`: `[0.0000, 6.9750, 0.1607]` dm $\rightarrow (0.000, -0.016, 1.514)$ m
    - `joint-l-upper-leg`: `[1.1036, 0.4862, 0.1229]` dm $\rightarrow (0.110, -0.012, 0.865)$ m
    - `joint-l-hand`: `[4.3118, 2.4518, 1.7566]` dm $\rightarrow (0.431, -0.176, 1.062)$ m
    - `joint-l-finger-1-1` (thumb base): `[4.1951, 2.3059, 2.1344]` dm
    - `joint-l-toe-1-1` (big toe base): `[1.8885, -8.0040, 1.3558]` dm

---

### 1.3 Test Suite Status & Failure Diagnostics (`tests/`)

Execution of `uv run pytest -q` across the full test repository:
- **Total Tests Collected**: 1,994 tests in 80 test files
- **Duration**: 209.51 seconds (~3 min 30 s)
- **Result Summary**: **1,972 PASSED, 10 FAILED, 9 SKIPPED, 3 XFAILED** (Pass Rate: **99.49%**)

#### Verbatim Log Analysis of the 10 Failing Tests:

1. `tests/test_adversarial_human_m3.py::test_extreme_waist_girth_penetration_analysis`
   - *Error*: `AssertionError: Canonical clearance is exactly +12.00mm. assert 18.54 == 12.0`
   - *Line*: `tests/test_adversarial_human_m3.py:343`
   - *Root Cause*: Sash clearance was increased from 12.00mm to 18.54mm to eliminate Z-fighting against the skirt waistband, but the test asserted hardcoded equality `== 12.00` instead of a minimum bound `assert clearance >= 12.0`.

2. `tests/test_adversarial_rigging.py::test_empirical_blender_vertex_weights_and_shape_keys_defect`
   - *Error*: `AssertionError: Expected 2144 weighted verts, got: RESULT: weighted_verts=2736, max_disp=0.369907, non_zero_keys=52`
   - *Line*: `tests/test_adversarial_rigging.py:519`
   - *Root Cause*: The Blender execution passed 100% of functional requirements: all 52 shape keys displaced, live bone rotation displacement = 0.3699m (> 0.05m required), and 100% of vertices weighted. The test failed solely on a regex check asserting the old vertex count `weighted_verts=2144`.

3. `tests/test_fastmcp_human_tools.py::test_blender_bridge_create_human_asset_non_fallback`
   - *Error*: `AssertionError: assert 2736 == 2144 where 2736 = res.get("vertex_count")`
   - *Line*: `tests/test_fastmcp_human_tools.py:322`
   - *Root Cause*: Stale literal assertion expecting old 2,144 vertex count instead of current 2,736.

4. `tests/test_challenger_m4_iter6_empirical.py::test_empirical_adversarial_audit_in_blender`
   - *Error*: `[FAIL] Body mesh quads count 2588 != 2,036 requirement! Yu_Nian_An_Body geometry mismatch: 2736 verts, 2588/2588 quads!`
   - *Line*: `tests/test_challenger_m4_iter6_empirical.py:522`
   - *Root Cause*: Stale quad count check asserting `== 2036` quads.

5. `tests/test_challenger_m4_iter4_empirics.py::test_live_master_blend_adversarial_empirical_audit`
   - *Error*: Same `2588 != 2036` quads mismatch on `Yu_Nian_An_Body`.

6. `tests/test_challenger_m3_sandals.py::test_sandals_height_bound_across_all_scales`
   - *Error*: `AssertionError: Scale dilation failure at H=1.8m: total height 52.66mm exceeds 50.0mm limit (assert 52.66 <= 50.0)`
   - *Line*: `tests/test_challenger_m3_sandals.py:141`
   - *Root Cause*: Footwear height scales linearly with $H/1.65$ without clamping upper bound.

7. `tests/test_challenger_m3_sandals.py::test_sandals_sole_length_bound_across_all_scales`
   - *Error*: `AssertionError: Sole length bounds failure at H=1.8m: sole length 0.2676m not in [0.22, 0.25]m`
   - *Line*: `tests/test_challenger_m3_sandals.py:154`
   - *Root Cause*: Sole length scales linearly with $H$ up to 0.2676m at $H=1.8$m.

8. `tests/test_challenger_m3_sandals.py::test_sandals_toes_and_toenails_exposure_and_clearance`
   - *Error*: `AssertionError: Big toe exposure clearance failure: clearance is 0.00mm < 7.0mm`
   - *Line*: `tests/test_challenger_m3_sandals.py:175`
   - *Root Cause*: Sole tip $Y = -0.138$m exactly aligns with the big toe landmark $Y = -0.138$m rather than leaving $\ge 7$mm of toe protruding past the sole.

9. `tests/test_challenger_m3_sandals.py::test_sandals_skin_clearance_buffer_canonical_scale`
   - *Error*: `AssertionError: Skin penetration / buffer failure: min signed distance is -0.132mm < +1.5mm. Penetrating vertices count: 1`
   - *Line*: `tests/test_challenger_m3_sandals.py:201`
   - *Root Cause*: Sub-malleolar ankle strap vertex 206 slightly clips the medial ankle skin by 0.13mm.

10. `tests/test_challenger_m3_sandals.py::test_sandals_skin_clearance_under_leg_girth_variations`
    - *Error*: `AssertionError: Leg variation clearance failure at k_leg=0.8: min signed clearance is -7.64mm < +1.5mm`
    - *Line*: `tests/test_challenger_m3_sandals.py:218`
    - *Root Cause*: Ankle cuff straps do not scale radius proportionally with `k_leg = leg_length / 0.88`.

---

### 1.4 Blender Integration & Bridge Subsystem

- **`src/morphomesh/blender_bridge.py`** (3,384 lines, 147.7 KB):
  - **Interactive Socket Mode**: Connects via TCP stream socket to `127.0.0.1:9876` (`send_socket_request()`).
  - **Headless Fallback Runner**: Resolves Blender binary via `_resolve_blender_binary()`:
    `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`.
    Executes scripts via `subprocess.run([blender_bin, "--background", "--factory-startup", "--python", script_path])`.
  - **Security**: `BpyCodeValidator` AST visitor blocks `os.system`, `subprocess`, socket manipulation, and file-write outside authorized directories.
  - **Inspection & QA**: Implements `setup_inspector_camera()`, `capture_viewport()`, `capture_multi_angle_inspection()`, and `critique_visual_quality()` using pure-Python BVH trees and raycasting.
- **`blender_addon/morphomesh/listener.py`** (2,024 lines, 101.0 KB):
  - Registers modal timer `bpy.app.timers.register(process_socket_queue)` running continuously on Blender's main GUI thread.
  - Implements 18 RPC handlers including `create_human_asset`, `auto_rig_human`, `dress_human`, `groom_human`, `assemble_master_character`, `render_preview`, and `critique_visual_quality`.
- **`src/morphomesh/server.py`** (1,504 lines, 65.2 KB):
  - Registers 17 tools under FastMCP protocol (`morphomesh_create_human_asset`, `morphomesh_auto_rig_human`, `morphomesh_dress_human`, `morphomesh_assemble_master_character`, `morphomesh_critique_visual_quality`, etc.).

---

### 1.5 Root Cause Analysis of User Feedback Screenshots

1. **Defect 1: Deformed & Angular Shoulders/Arms (`media_1788701589498.png`)**:
   - *Code Trace*: In `scripts/build_ultimate_yu_nian_an.py` lines 887–1040, the script imported `Liva.vrm` and attempted to strip its jacket by deleting polygon material slots:
     ```python
     # Keep slot 0 (skin), slot 1 (scalp hair base), and slot 6 (tops sleeves)
     # DELETE Island 0 (the jacket/bolero) and Island 3 (the collar)
     del_f = [f for f in bm_b.faces if f.material_index not in {0, 1, 6}]
     ```
   - This hacky face deletion created disconnected open seams at the deltoid/shoulder junction, inverted boundary normals, and mangled arm geometry. Furthermore, the procedural generator in `human_generator.py` uses trigonometric cross-sections that pinch at the axilla/underarm.
   - *Remediation*: Replace both the VRM stripping hack and procedural cross-sections with `data/templates/makehuman_clean_body.obj`. This provides a continuous, watertight, 100% quad mesh with organic shoulder curves, smooth trapezius slope, relaxed natural arms, and complete 5-digit hands and feet.

2. **Defect 2: Rigid Lampshade Skirt Folds (`media_1788801618516.png`)**:
   - *Code Trace*: In `src/morphomesh/wardrobe.py` lines 883–992 (`generate_dress_organic_skirt`), the skirt geometry is constructed as concentric circles with mathematical sine perturbations:
     ```python
     a1 = 0.052 * s * k_waist  # Primary drape (n=6)
     ...
     rx = rx_base * (1.0 + a1 * math.sin(6 * theta))
     ```
   - Concentric circles with radial sine expansion produce rigid conical ridges that flare outwards uniformly, resembling a pleated lampshade rather than fabric responding to gravity and body contact.
   - *Remediation*: Implement Blender Cloth Simulation (`CLOTH` modifier) on a quad grid dress pattern, configured with cotton/silk physical presets (mass 0.15 kg/m², bending 0.5, shear 5.0), collision against the anatomical base mold (`COLLISION` modifier, distance 0.005m), settling over 30–50 simulation frames under gravity ($g = -9.81$ m/s²), or bake the simulated draped vertex coordinates into the wardrobe generator.

---

### 1.6 Complete Codebase File Inventory

| Module / Path | File Type | Lines | Size (KB) | Functional Role |
|---|---|---|---|---|
| `src/morphomesh/__init__.py` | Python package | 139 | 3.6 | Version and top-level package exports |
| `src/morphomesh/human_generator.py` | Core engine | 1,780 | 84.1 | Parametric human base mesh synthesis, vertex groups, landmarks |
| `src/morphomesh/human_rigging.py` | Rigging engine | 1,643 | 72.4 | Rigify 163 DEF metarig, biomechanical pivots, skinning, ARKit FACS |
| `src/morphomesh/wardrobe.py` | Wardrobe engine | 2,143 | 86.3 | Bodice, sash, skirt, flat sandals, marionette strings, butterflies |
| `src/morphomesh/human_grooming.py` | Hair engine | 1,188 | 50.8 | 6-layer Hime cut hair strata, Geometry Nodes hair curves |
| `src/morphomesh/human_materials.py` | Material engine | 918 | 36.3 | Cycles Principled BSDF, Random Walk SSS skin, silk, satin, eyes |
| `src/morphomesh/character_assembler.py` | Assembly engine | 2,373 | 101.1 | 7-tier collection hierarchy, UV atlas, binary export manager |
| `src/morphomesh/blender_bridge.py` | Bridge client | 3,384 | 147.7 | Dual-mode TCP socket & headless CLI runner, AST validator |
| `src/morphomesh/server.py` | MCP server | 1,504 | 65.2 | FastMCP server exposing 17 tools to Antigravity 2.0 |
| `src/morphomesh/camera_rig.py` | Camera engine | 1,166 | 46.1 | Bounding box framing, turntable camera rig, viewport capture |
| `src/morphomesh/visual_critic.py` | QA / Critic | 2,295 | 93.1 | BVH raycasting, mesh penetration detection, defect scoring |
| `src/morphomesh/models.py` | Data models | 1,158 | 58.8 | Pydantic v2 schemas, tool request/response models, error codes |
| `src/morphomesh/export_manager.py` | Export utility | 744 | 31.3 | GLTF/GLB, FBX, OBJ, texture atlas baking pipelines |
| `src/morphomesh/inference_adapter.py` | AI / Geometry | 2,357 | 96.7 | MeshGeometry primitives, backend connectors, mesh math |
| `src/morphomesh/anatomy/stance.py` | Anatomy engine | 344 | 13.0 | Locomotor stance classification (biped, plantigrade, etc.) |
| `src/morphomesh/anatomy/landmarks.py` | Anatomy engine | 552 | 23.8 | Bony landmark extraction & ICR joint rotation centers |
| `src/morphomesh/anatomy/bone_roll.py` | Anatomy engine | 384 | 13.8 | Biomechanical hinge normal and bone roll solver |
| `src/morphomesh/anatomy/skinning.py` | Anatomy engine | 557 | 20.7 | Volumetric geodesic voxel diffusion skinning |
| `src/morphomesh/connectors/` (11 files) | Connectors | 5,929 | 248.0 | TRELLIS, Hunyuan3D, MeshAnything, 3DAnimals, Gemini connectors |
| `data/templates/makehuman_base.obj` | 3D Asset | — | 1,749.3 | MakeHuman base mesh with 139 helper and joint groups |
| `data/templates/makehuman_clean_body.obj` | 3D Asset | — | 689.6 | Clean naked female base mold (13,380 verts, 13,378 quads) |
| `blender_addon/morphomesh/listener.py` | Blender Addon | 2,024 | 101.0 | Interactive socket server inside Blender (port 9876) |
| `blender_addon/morphomesh/operators.py` | Blender Addon | 238 | 8.6 | Blender UI operators and viewport panels |
| `scripts/build_ultimate_yu_nian_an.py` | Pipeline Script | 1,870 | 84.4 | End-to-end master asset generation script |
| `scripts/build_and_render_master.py` | Pipeline Script | 1,002 | 43.3 | Master character scene builder and renderer |
| `scripts/render_ultimate_beauty.py` | Render Script | 792 | 33.5 | Multi-angle Cycles AgX beauty shot renderer |
| `tests/` (80 test files) | Test Suite | ~22,000 | ~1,200 | 1,994 unit, integration, adversarial, and empirical tests |

---

## 2. Logic Chain

1. **Premise 1 (User Problem)**: The user observed ugly, angular shoulder/arm artifacts in `media_1788701589498.png` and rigid conical lampshade folds in `media_1788801618516.png`, demanding an anatomical base mold (MakeHuman/CC0) and cloth physics simulation.
2. **Premise 2 (Direct Observation of Existing Code)**:
   - In `scripts/build_ultimate_yu_nian_an.py:1028–1040`, clothing was stripped from `Liva.vrm` by deleting material slots, leaving non-manifold edges at the shoulder/sleeves junction.
   - In `human_generator.py:270–450`, the procedural generator uses mathematical ellipses that lack realistic trapezius slopes and armpit muscle flow.
   - In `wardrobe.py:883–992`, the skirt is generated via harmonic radial sine waves (`a1 * sin(6*theta)`), which mathematically forces a conical lampshade structure.
3. **Premise 3 (Template Availability)**:
   - `data/templates/makehuman_clean_body.obj` already exists in the repository. It has 13,380 vertices and 13,378 quad faces (100% pure quads).
   - `data/templates/makehuman_base.obj` contains 70+ joint landmark cubes (`joint-head`, `joint-l-finger-*`, `joint-l-toe-*`) with exact 3D centroids.
4. **Premise 4 (Test Suite Resilience)**:
   - 1,972 of 1,994 tests (99.49%) pass.
   - All 10 failing tests are accounted for: 5 stem from sandals bounds/clearance scaling in `test_challenger_m3_sandals.py`, 4 stem from stale literal assertions on vertex/quad counts (`2144` vs `2736`, `2036` quads vs `2588`), and 1 stems from an exact equality check on waist sash gap (`12.00` vs `18.54`).
5. **Inference & Conclusion**:
   - The foundation of MorphoMesh is rock solid (Blender bridge, FastMCP server, Rigify rigging, material pipelines, test harness).
   - Integrating `makehuman_clean_body.obj` into `human_generator.py` (with coordinates transformed from decimeters to Blender meters) will immediately eliminate the angular shoulder/arm defects.
   - Replacing the sine-wave skirt generator with a Blender Cloth Simulation workflow (or baking a cloth-simulated quad mesh drape into `wardrobe.py`) will resolve the lampshade skirt defect.
   - Updating stale test assertions and calibrating sandals sole bounds will restore 100% test pass rate across the full 1,994-test suite.

---

## 3. Caveats

1. **Interactive Socket vs. Headless Mode**:
   - Port 9876 is currently not listening because Blender is not running interactively with the MorphoMesh addon active. All automated tests and CLI operations run in headless mode (`blender.exe --background --python <script>`), which works reliably.
2. **Coordinate Transformation**:
   - MakeHuman assets use decimeters with $Y$-up, $X$-lateral, and $Z$-sagittal. Integration into Blender standard (meters, $Z$-up) requires an explicit coordinate swizzle and scale ($X_b = 0.1 X_{mh}, Y_b = -0.1 Z_{mh}, Z_b = 0.1 (Y_{mh} + 8.1676)$).
3. **Cloth Simulation Execution Environment**:
   - Live cloth simulation requires Blender's physics cache (`bpy.ops.ptcache.bake_all` or frame stepping `bpy.context.scene.frame_set(f)`). In purely offline Python environments without Blender, a pre-simulated/baked quad mesh drape or compliant procedural representation must be available as fallback.

---

## 4. Conclusion & Technical Implementation Roadmap

### 4.1 R1: Anatomical Female Base Mold Integration (`human_generator.py`)
- Load `data/templates/makehuman_clean_body.obj` into `MeshGeometry`:
  - 13,380 vertices, 13,378 quads, 100% pure quad topology.
  - Scale to 1.65m height with canonical female proportions (WHR ~0.70).
  - Extract skeletal landmarks from the 70+ joint landmark cubes in `makehuman_base.obj`.
  - Assign standardized vertex groups (`torso`, `chest`, `waist`, `hips`, `arm_upper_*`, `foot_*`, etc.) using bounding boxes or topological region maps.
  - Retain 52 ARKit FACS facial blendshape deltas.

### 4.2 R2: Cloth Simulation One-Piece Sundress (`wardrobe.py`)
- Replace the rigid trigonometric pleated skirt with an organic one-piece sundress:
  - Bodice: Sweetheart scoop neckline, conforming teardrop bust, and 3D spaghetti straps.
  - Skirt: Quadratic/catenary fall from waist ($Z=1.03$m) to just above knee ($Z=0.52$m), simulated under gravity ($g = -9.81$ m/s²) with tension/shear resistance to create authentic vertical folds.
  - Sash: Ice-blue satin sash with barrel cuff knot and cascading ribbons conforming to the waist with $+3.5$mm clearance to eliminate Z-fighting.

### 4.3 R3: Full Yu Nian An Character Assembly
- Synchronize `character_assembler.py` and `scripts/build_ultimate_yu_nian_an.py`:
  - 7-tier collection hierarchy (`01_Body` through `06_Lights_Camera`).
  - Assemble base mold + cloth sundress + 6-strata Hime cut hair + flat strappy sandals + 10 crimson strings + 10 glowing swallowtail butterflies + Rigify 163 DEF metarig.

### 4.4 R4: Test Suite Remediation & Production Delivery
- Resolve the 10 failing tests:
  - Update stale literal assertions (`vertex_count == 2144` and `quads == 2036`) to reflect the refined base mesh topology.
  - Calibrate `generate_flat_strappy_sandals` parameters (clamp sole height $\le 50$mm, sole length $\le 0.25$m, big toe clearance $\ge 7$mm, and ankle wrap radius buffer $\ge +1.5$mm).
  - Assert 0 mesh penetrations via pure-Python BVH (`visual_critic.py`).
  - Re-export `Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, and `Yu_Nian_An.fbx` in `output/yu_nian_an/`.
  - Render beauty shots in Cycles AgX.

---

## 5. Verification Method

To independently verify all findings and assertions in this report:

1. **Verify Python & Dependencies**:
   ```powershell
   uv run python -V
   # Expected: Python 3.11.9
   ```

2. **Verify Blender Executable**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --version
   # Expected: Blender 4.5.4 LTS (hash b3efe983cc58)
   ```

3. **Verify MakeHuman Template Assets**:
   ```powershell
   uv run python -c "
   for path in ['data/templates/makehuman_base.obj', 'data/templates/makehuman_clean_body.obj']:
       v, f = 0, 0
       with open(path) as file:
           for l in file:
               if l.startswith('v '): v += 1
               elif l.startswith('f '): f += 1
       print(f'{path}: verts={v}, faces={f}')
   "
   # Expected:
   # makehuman_base.obj: verts=19158, faces=18486
   # makehuman_clean_body.obj: verts=13380, faces=13378
   ```

4. **Verify Test Suite Status**:
   ```powershell
   uv run pytest -q
   # Expected: 10 failed, 1972 passed, 9 skipped, 3 xfailed
   ```

5. **Verify Master Blend Collection Hierarchy**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background "output/yu_nian_an/Yu_Nian_An_Master.blend" --python-expr "import bpy; print('Collections:', [c.name for c in bpy.data.collections])"
   # Expected: ['01_Body', '02_Hair', '03_Wardrobe', '04_Props', '05_Armature', '06_Lights_Camera', 'Yu_Nian_An_Master']
   ```
