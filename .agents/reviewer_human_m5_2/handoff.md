# Milestone 5 Review & Adversarial Challenge Report: 4K PBR Textures & Engine Documentation

**Reviewer**: `reviewer_human_m5_2`  
**Parent Agent**: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Scope**: 4K PBR Texture Suite (`output/yu_nian_an/textures/`), Engine Integration Documentation (`output/yu_nian_an/README_EXPORT.md`), and Production Packaging Pipeline  
**Verdict**: **`REQUEST_CHANGES`**

---

## 1. Observation

Direct empirical observations, commands, and inspection outputs:

### 1.1 Test Suite Execution
- Executed `& 'E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe' -m pytest tests/test_production_exports.py -v`:
  ```
  tests/test_production_exports.py::TestProductionFileExistence::test_master_blend_exists_and_size PASSED [  3%]
  tests/test_production_exports.py::TestProductionFileExistence::test_fbx_export_exists_and_size PASSED [  7%]
  tests/test_production_exports.py::TestProductionFileExistence::test_glb_export_exists_and_size PASSED [ 11%]
  tests/test_production_exports.py::TestProductionFileExistence::test_all_seven_4k_textures_exist PASSED [ 15%]
  tests/test_production_exports.py::TestProductionFileExistence::test_readme_export_documentation_exists PASSED [ 19%]
  tests/test_production_exports.py::TestTextureSpecifications::test_texture_resolution_is_strictly_4096[...] PASSED [ 46%]
  tests/test_production_exports.py::TestTextureSpecifications::test_base_color_texture_distribution PASSED [ 50%]
  tests/test_production_exports.py::TestTextureSpecifications::test_normal_map_properties PASSED [ 53%]
  tests/test_production_exports.py::TestTextureSpecifications::test_roughness_map_dual_roughness PASSED [ 57%]
  tests/test_production_exports.py::TestTextureSpecifications::test_metallic_and_sss_maps PASSED [ 61%]
  tests/test_production_exports.py::TestFBXBinaryIntegrity::test_fbx_magic_header PASSED [ 65%]
  tests/test_production_exports.py::TestFBXBinaryIntegrity::test_fbx_contains_def_bones_and_shape_keys PASSED [ 69%]
  tests/test_production_exports.py::TestGLBContainerAndMorphTargets::test_glb_magic_and_version PASSED [ 73%]
  tests/test_production_exports.py::TestGLBContainerAndMorphTargets::test_glb_json_structure PASSED [ 76%]
  tests/test_production_exports.py::TestGLBContainerAndMorphTargets::test_glb_body_mesh_has_all_52_arkit_morph_targets PASSED [ 80%]
  tests/test_production_exports.py::TestExportAutomationPipeline::[...] PASSED [100%]
  ============================== 26 passed in 0.52s ==============================
  ```

### 1.2 Quantitative Audit of 4K PBR Texture Files
Audited all 7 texture maps in `output/yu_nian_an/textures/`:
- `Yu_Nian_An_BaseColor_4K.png`: Resolution $4096 \times 4096$, mode `RGB`, 8-bit. Porcelain skin `#F4E4DC` (RGB `[245, 229, 222]`), rose lips (RGB `[195, 85, 105]`), dark eyeliner (RGB `[12, 12, 14]`), ivory silk dress (RGB `[245, 243, 239]`), satin sash (RGB `[198, 222, 238]`), gold hardware (RGB `[225, 195, 110]`).
- `Yu_Nian_An_Normal_4K.png`: Resolution $4096 \times 4096$, mode `RGB`, 8-bit OpenGL tangent-space. Vector lengths across all 16,777,216 pixels: $\min = 0.9922$, $\max = 1.0009$, $\mu = 0.9958$, $\sigma = 0.0030$. $+Z$ dominant channel $\mu = 0.9926$, $\min = 0.9529$. Tangent pore perturbations and lip vermilion wrinkles present.
- `Yu_Nian_An_Roughness_4K.png`: Resolution $4096 \times 4096$, mode `L`, 8-bit. Scalp $0.698$ ($178$), face $0.380$ ($97$), lips $0.278$ ($71$, wet gloss), dress $0.447$ ($114$), sash $0.220$ ($56$, smooth satin), hardware $0.196$ ($50$).
- `Yu_Nian_An_Metallic_4K.png`: Resolution $4096 \times 4096$, mode `L`, 8-bit. Dielectric $0.0$ on skin, eyes, scalp, dress; metallic $1.0$ on hardware aglets and buckles.
- `Yu_Nian_An_SSS_4K.png`: Resolution $4096 \times 4096$, mode `L`, 8-bit. Ears $0.847$, nose $0.749$, lips $0.698$, body $0.349$, dress $0.0$.
- `Yu_Nian_An_Alpha_4K.png`: Resolution $4096 \times 4096$, mode `L`, 8-bit. Solid body $1.0$, feathered alpha fringe cutouts $[0.0, 0.576]$.
- `Yu_Nian_An_Height_4K.png`: Resolution $4096 \times 4096$, mode `L`, 8-bit. Neutral mid-gray $127$ ($0.498$), upper/lower lip fullness $144$ ($0.565$), oral slit depression $63$ ($0.247$), hardware $191$ ($0.749$).

### 1.3 Audit of 3D Export Meshes & UV Layers
Direct inspection via Blender 4.5.4 LTS and binary glTF/FBX parsers revealed:
- Headless Blender inspection of `output/yu_nian_an/Yu_Nian_An_Master.blend`:
  ```
  Yu_Nian_An_Body: NO UV LAYERS
  Mesh_Dress_Bodice: NO UV LAYERS
  Mesh_Dress_PleatedSkirt: NO UV LAYERS
  Mesh_Dress_WaistSash: NO UV LAYERS
  Mesh_Sandal_L: NO UV LAYERS
  Mesh_Sandal_R: NO UV LAYERS
  ```
- glTF inspection of `output/yu_nian_an/Yu_Nian_An.glb`:
  `Yu_Nian_An_Body` primitive attributes: `['POSITION', 'NORMAL', 'JOINTS_0', 'WEIGHTS_0']`. **Missing `TEXCOORD_0`**.
  `Mesh_Dress_Bodice_Mesh`, `Mesh_Dress_PleatedSkirt_Mesh`, `Mesh_Dress_WaistSash_Mesh`, `Mesh_Sandal_*` all lack `TEXCOORD_0`.
- FBX re-import inspection of `output/yu_nian_an/Yu_Nian_An.fbx`:
  `Yu_Nian_An_Body`: `UV layers=[]`.
  `Mesh_Dress_*`: `UV layers=[]`.
- Only hair cards (`Hair_*`), eyes (`Mesh_Eye_*`), and `Mesh_Lips` have `UVMap`. Furthermore, `Mesh_Lips` has a UV map spanning $[0, 1] \times [0, 1]$ rather than being mapped to its quadrant Q1 coordinate in the 4K texture atlas.

### 1.4 Engine Integration Documentation (`output/yu_nian_an/README_EXPORT.md`)
- Section 5.A (Unreal Engine 5.4+):
  Lines 118-121 instruct:
  ```markdown
  - Connect Yu_Nian_An_BaseColor_4K.png to Base Color.
  - Connect Yu_Nian_An_Normal_4K.png to Normal.
  - Connect Yu_Nian_An_Roughness_4K.png to Roughness.
  - Connect Yu_Nian_An_SSS_4K.png to Subsurface Color or opacity scalar multiplier.
  ```
  Omission: No mention of inverting or checking "Flip Green Channel" for the OpenGL tangent-space normal map in Unreal Engine 5.
- Section 5.C (Three.js WebGL):
  Lines 160-195 demonstrate loading `Yu_Nian_An.glb` and controlling morph targets (`mouthSmileLeft`, `eyeBlinkLeft`), but contain zero code for loading or binding the 4K PBR textures (`Yu_Nian_An_BaseColor_4K.png`, `Normal`, `Roughness`) to the mesh material.

---

## 2. Logic Chain

1. **Premise 1**: In 3D computer graphics and real-time game engines (Unreal Engine 5, Unity 6, Three.js WebGL), 2D texture maps (BaseColor, Normal, Roughness, Metallic, SSS) can only be mapped onto a 3D polygonal surface if the mesh geometry contains 2D texture coordinate attributes (`TEXCOORD_0` / UV layers).
2. **Premise 2**: Worker M5 authored a 4-quadrant 4K texture atlas (`generate_yu_nian_an_pbr_textures` in `src/morphomesh/character_assembler.py` lines 1675-1680) where:
   - Q1 $[0, 0.5] \times [0, 0.5]$ = Head & Face
   - Q2 $[0.5, 1.0] \times [0, 0.5]$ = Body & Limbs
   - Q3 $[0, 0.5] \times [0.5, 1.0]$ = Silk Dress
   - Q4 $[0.5, 1.0] \times [0.5, 1.0]$ = Sash, Sandals, Hardware
3. **Premise 3**: As directly observed in Observation 1.3, `Yu_Nian_An_Body`, `Mesh_Dress_Bodice`, `Mesh_Dress_PleatedSkirt`, and `Mesh_Dress_WaistSash` in `Yu_Nian_An_Master.blend`, `Yu_Nian_An.fbx`, and `Yu_Nian_An.glb` have **no UV layers** (`TEXCOORD_0` is absent).
4. **Deduction 1**: When an engineer follows `README_EXPORT.md` Section 5.A, 5.B, or 5.C and connects `Yu_Nian_An_BaseColor_4K.png`, `Yu_Nian_An_Normal_4K.png`, etc., to `Yu_Nian_An_Body` in UE5, Unity, or Three.js, the engine cannot map the texture. UE5 reports missing UV Channel 0, Unity displays a flat solid vertex color, and Three.js fails WebGL attribute binding or falls back to an untextured default.
5. **Deduction 2**: The test suite `tests/test_production_exports.py` only checked whether image files exist on disk, their resolutions, pixel values, and whether GLB morph targets exist. It failed to assert that the exported meshes actually possess valid UV layers matching the texture suite.
6. **Premise 4**: OpenGL normal maps use $+Y$ (up), whereas Unreal Engine 5's tangent space expects DirectX $-Y$ (down). Without instructing users to check "Flip Green Channel" in UE5's texture properties, all directional lighting on normal map details will be inverted.
7. **Conclusion**: While the 2D procedural texture generation code and mathematical properties of the 7 PNG files are high quality, the deliverables cannot function together in target game engines due to the missing UV coordinate layers on the exported meshes, coupled with omissions in the engine documentation.

---

## 3. Detailed Review Findings

### Critical Finding 1: Disconnect Between 4K PBR Texture Suite and Exported 3D Meshes (Missing UV Coordinates)
- **What**: `Yu_Nian_An_Body`, `Mesh_Dress_Bodice`, `Mesh_Dress_PleatedSkirt`, `Mesh_Dress_WaistSash`, and `Mesh_Sandal_*` lack UV coordinates (`UVMap` / `TEXCOORD_0`) in `Yu_Nian_An_Master.blend`, `Yu_Nian_An.fbx`, and `Yu_Nian_An.glb`.
- **Where**:
  * `output/yu_nian_an/Yu_Nian_An_Master.blend`
  * `output/yu_nian_an/Yu_Nian_An.fbx`
  * `output/yu_nian_an/Yu_Nian_An.glb`
  * `src/morphomesh/character_assembler.py` (`get_export_script` / `export_production_assets`)
  * `tests/test_production_exports.py`
- **Why**: The 4K PBR texture suite is designed as an atlas partitioned into 4 quadrants. Without UV layers on the meshes mapped into these respective quadrants, the textures cannot be rendered or sampled in Unreal Engine, Unity, or Three.js.
- **Suggestion**:
  1. In `src/morphomesh/character_assembler.py`, update `get_export_script` or the assembly process to unwrap or assign UV coordinates to all meshes prior to export:
     - For `Yu_Nian_An_Body`: assign UVs mapped to Q1 (head/face in $[0, 0.5] \times [0, 0.5]$) and Q2 (body/limbs in $[0.5, 1.0] \times [0, 0.5]$).
     - For `Mesh_Dress_*`: assign UVs mapped to Q3 ($[0, 0.5] \times [0.5, 1.0]$).
     - For `Mesh_Dress_WaistSash` and `Mesh_Sandal_*`: assign UVs mapped to Q4 ($[0.5, 1.0] \times [0.5, 1.0]$).
  2. Re-export `Yu_Nian_An.fbx` and `Yu_Nian_An.glb` ensuring `TEXCOORD_0` is present on all mesh primitives.
  3. Add explicit unit tests in `tests/test_production_exports.py` checking that every exported mesh primitive in GLB and FBX contains valid UV texture coordinates.

### Major Finding 2: Missing Normal Map Green Channel Convention Instruction in UE5 Documentation
- **What**: `Yu_Nian_An_Normal_4K.png` is an OpenGL tangent-space normal map ($+Y$ up), but `output/yu_nian_an/README_EXPORT.md` Section 5.A does not specify flipping the green channel for Unreal Engine 5 (DirectX $-Y$ down).
- **Where**: `output/yu_nian_an/README_EXPORT.md`, Section 5.A.
- **Why**: In UE5, importing an OpenGL normal map without checking "Flip Green Channel" causes vertical tangent perturbations (lip wrinkles, skin pores, fabric folds) to appear inverted under lighting (crevices appear as ridges and vice versa).
- **Suggestion**: Add a clear note in `README_EXPORT.md` Section 5.A under Texture Setup instructing users to double-click `Yu_Nian_An_Normal_4K.png` in the UE5 Content Browser and check **Flip Green Channel** under Texture Advanced Settings.

### Major Finding 3: Incomplete Three.js PBR Texture Loading Sample in Documentation
- **What**: The Three.js code sample in `README_EXPORT.md` Section 5.C demonstrates glTF loading and morph target iteration, but omits texture loading and material assignment.
- **Where**: `output/yu_nian_an/README_EXPORT.md`, Section 5.C.
- **Why**: The document is titled "Multi-Format Production Packaging & Export Guide" and section 5 is intended to guide engineers on setting up the asset and shaders in external engines.
- **Suggestion**: Enhance the Three.js sample code to demonstrate loading `Yu_Nian_An_BaseColor_4K.png`, `Normal`, and `Roughness` via `THREE.TextureLoader`, configuring `colorSpace = THREE.SRGBColorSpace`, and applying them to the character's mesh material.

### Minor Finding 4: Pre-Packed Engine Maps (ORM / HDRP Mask Map) Not Included on Disk
- **What**: Section 4 of `README_EXPORT.md` defines recommended channel packing (UE5 ORM: R=AO, G=Roughness, B=Metallic, A=SSS; Unity HDRP Mask Map: R=Metallic, G=AO, B=Detail/SSS, A=Smoothness), but `output/yu_nian_an/textures/` only contains the 7 individual maps.
- **Where**: `output/yu_nian_an/textures/`
- **Why**: Production game pipelines rely heavily on packed textures to reduce texture sampler overhead and GPU memory footprint.
- **Suggestion**: Optionally update `generate_yu_nian_an_pbr_textures()` to also bake `Yu_Nian_An_ORM_4K.png` and `Yu_Nian_An_MaskMap_4K.png` directly into `output/yu_nian_an/textures/`.

---

## 4. Adversarial Challenge & Stress Test Results

| # | Stress Test Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| 1 | Strict 4096x4096px resolution across all 7 texture maps | All maps strictly $4096 \times 4096$ | All 7 maps verified strictly $4096 \times 4096$ via PIL | **PASS** |
| 2 | Tangent space normal vector normalization | $\sqrt{nx^2+ny^2+nz^2} \approx 1.0$ across all pixels | Vector lengths in $[0.9922, 1.0009]$, $+Z$ dominant | **PASS** |
| 3 | Physical dual-roughness distributions | Scalp (0.70), Face (0.38), Lips (0.28), Sash (0.22) | Verified: Scalp 0.698, Face 0.380, Lips 0.278, Sash 0.220 | **PASS** |
| 4 | Dielectric vs metallic separation | Organics 0.0, Hardware 1.0 | Verified: Skin/Dress 0.000, Hardware 1.000 | **PASS** |
| 5 | Morph targets preserved in glTF GLB | Exactly 52 Apple ARKit blendshapes in `targetNames` | Verified: 52 targets present on `Yu_Nian_An_Body` | **PASS** |
| 6 | **Mesh UV layer existence for texture mapping in external engines** | All mesh primitives exported with `TEXCOORD_0` | **FAIL: `Yu_Nian_An_Body`, `Mesh_Dress_*`, and `Mesh_Sandal_*` have no UV layers** | **FAIL (CRITICAL)** |
| 7 | Normal map channel convention compatibility with UE5 | Documentation specifies OpenGL to DirectX green channel inversion | **FAIL: Omitted in `README_EXPORT.md` Section 5.A** | **FAIL (MAJOR)** |
| 8 | Three.js PBR texture binding code | Sample code demonstrates loading and binding 4K maps | **FAIL: Code sample only touches morph targets** | **FAIL (MAJOR)** |

---

## 5. Caveats

No caveats. All observations are based on direct execution of Python test harnesses, headless Blender 4.5.4 LTS scene parsing, binary FBX and glTF chunk inspection, and image array analysis.

---

## 6. Conclusion & Remediation Plan

Milestone 5 has made excellent progress:
- 7 high-resolution $4096 \times 4096$ textures with correct bit depth and mathematically verified PBR properties.
- Rigged FBX and GLB files preserving 163 DEF bones and 52 ARKit FACS shape keys.
- Comprehensive base documentation covering UE5, Unity 6, and Three.js.

However, the lack of UV coordinates on the primary body and wardrobe meshes prevents the 4K PBR textures from actually being applied in any external game engine. This creates an unbridgeable disconnect between the texture deliverables and the geometry deliverables.

**Verdict: `REQUEST_CHANGES`**

### Required Action Items for Worker M5:
1. **Add UV unwrapping in export pipeline**: Ensure `Yu_Nian_An_Body`, dress, sash, and sandal meshes have UV coordinates assigned to their corresponding atlas quadrants (Q1: Head, Q2: Body, Q3: Dress, Q4: Sash/Sandals) before exporting.
2. **Re-export FBX & GLB**: Generate updated `Yu_Nian_An.fbx` and `Yu_Nian_An.glb` containing `TEXCOORD_0` on all primitives.
3. **Update `tests/test_production_exports.py`**: Add tests asserting that `Yu_Nian_An_Body` and dress meshes have UV coordinates in both FBX and GLB.
4. **Update `README_EXPORT.md`**:
   - Add the UE5 "Flip Green Channel" normal map instruction in Section 5.A.
   - Add Three.js texture loading snippet in Section 5.C.
   - (Optional) Include pre-baked `Yu_Nian_An_ORM_4K.png` and `Yu_Nian_An_MaskMap_4K.png`.

---

## 7. Verification Method

To independently verify the remediation:

1. **Verify UV Layers in GLB and FBX**:
   ```powershell
   & 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' -b --python-expr "import bpy; bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.fbx(filepath='output/yu_nian_an/Yu_Nian_An.fbx'); print({o.name: [l.name for l in o.data.uv_layers] for o in bpy.data.objects if o.type == 'MESH'})"
   ```
   *Expected: Every mesh object, including `Yu_Nian_An_Body` and `Mesh_Dress_*`, must have at least one UV layer.*

2. **Verify Production Export Tests**:
   ```powershell
   & 'E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe' -m pytest tests/test_production_exports.py -v
   ```
   *Expected: All tests pass (including new UV assertion tests).*
