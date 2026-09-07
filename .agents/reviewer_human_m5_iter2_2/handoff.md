# Milestone 5 Iteration 2 Review & Adversarial Challenge Report

**Reviewer**: `reviewer_human_m5_iter2_2`  
**Parent Agent**: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Scope**: Milestone 5 Iteration 2 Remediation Review (UV Atlas Mapping, UE5 Normal Map Inversion, Three.js Sample, Pre-Packed ORM & MaskMap, GLB/FBX Exports)  
**Verdict**: **`REQUEST_CHANGES`**  

---

## Review Summary

While three of the four findings from Iteration 1 have been successfully remediated (`README_EXPORT.md` Section 5.A UE5 normal map instructions, Section 5.C Three.js sample code, and the creation of $4096 \times 4096$ pre-packed `Yu_Nian_An_ORM_4K.png` and `Yu_Nian_An_MaskMap_4K.png`), independent adversarial verification of the 3D meshes (`Yu_Nian_An.glb`, `Yu_Nian_An.fbx`, `Yu_Nian_An_Master.blend`) revealed a **Critical Integrity / Facade Flaw** in Finding 1:

The vertical coordinate ($V$) in the UV unwrapping generator is **completely inverted** relative to the 2D texture atlas layout:
- In `Yu_Nian_An.glb`, `Mesh_Dress_PleatedSkirt_Mesh` UV coordinates map into the upper quadrant ($V \in [0.2056, 0.4889]$), sampling pixel `(998, 1422)` with RGB `[208, 105, 122]` (**Rose Lips & Face Skin**).
- Conversely, `Mesh_Lips_Mesh` UV coordinates map into the lower quadrant ($V \in [0.8000, 0.9200]$), sampling pixel `(1024, 3522)` with RGB `[248, 246, 242]` (**Ivory Silk Dress**).
- Primary head mesh `Yu_Nian_An_Body` prim 1 maps to $V \in [0.5000, 0.7247]$, sampling pixel `(976, 2390)` with RGB `[251, 249, 245]` (**Ivory Silk Dress**).
- The unit test suite `tests/test_production_exports.py` passed because it merely checked that the dictionary key `'TEXCOORD_0'` exists on primitives and tested static 2D image coordinates (`arr[1475, 1024]`), without performing semantic texture sampling via the mesh UV attributes.

---

## 1. Observation

Direct empirical observations, commands, verbatim logs, and numeric outputs:

### 1.1 Automated Test Suites Execution
1. Executed `pytest tests/test_production_exports.py -v`:
   ```
   tests/test_production_exports.py::TestProductionFileExistence::test_master_blend_exists_and_size PASSED [  3%]
   tests/test_production_exports.py::TestProductionFileExistence::test_fbx_export_exists_and_size PASSED [  6%]
   tests/test_production_exports.py::TestProductionFileExistence::test_glb_export_exists_and_size PASSED [  9%]
   tests/test_production_exports.py::TestProductionFileExistence::test_all_seven_4k_textures_exist PASSED [ 12%]
   tests/test_production_exports.py::TestProductionFileExistence::test_readme_export_documentation_exists PASSED [ 16%]
   tests/test_production_exports.py::TestTextureSpecifications::test_texture_resolution_is_strictly_4096[Yu_Nian_An_ORM_4K.png] PASSED [ 41%]
   tests/test_production_exports.py::TestTextureSpecifications::test_texture_resolution_is_strictly_4096[Yu_Nian_An_MaskMap_4K.png] PASSED [ 45%]
   tests/test_production_exports.py::TestTextureSpecifications::test_orm_and_maskmap_packed_textures PASSED [ 61%]
   tests/test_production_exports.py::TestFBXBinaryIntegrity::test_fbx_uv_layer_presence PASSED [ 70%]
   tests/test_production_exports.py::TestGLBContainerAndMorphTargets::test_glb_all_mesh_primitives_have_texcoord_0 PASSED [ 83%]
   ============================= 31 passed in 0.72s ==============================
   ```
2. Executed full repository regression test suite `pytest tests/`:
   ```
   ================== 742 passed, 6 skipped in 91.53s (0:01:31) ==================
   ```

### 1.2 Verification of Documentation (Findings 2 & 3)
- `output/yu_nian_an/README_EXPORT.md` Section 5.A (lines 121-123):
  ```markdown
    - **Normal Map Configuration (CRITICAL for Unreal Engine 5)**:
      * Double-click `Yu_Nian_An_Normal_4K.png` in Content Browser to open the Texture Editor.
      * Under **Texture** -> **Advanced**, check **Flip Green Channel** (converts OpenGL +Y normal map coordinates to Unreal Engine / DirectX -Y tangent space so facial creases and pores shade outward rather than inverted).
  ```
  Verified: Present, technically accurate, and explicitly addresses DirectX tangent space inversion.
- `output/yu_nian_an/README_EXPORT.md` Section 5.C (lines 169-238):
  ```javascript
  // 1. Load 4K PBR Texture Suite via THREE.TextureLoader
  const textureLoader = new THREE.TextureLoader();
  const baseColorMap = textureLoader.load('output/yu_nian_an/textures/Yu_Nian_An_BaseColor_4K.png');
  baseColorMap.colorSpace = THREE.SRGBColorSpace;
  baseColorMap.flipY = false;
  const normalMap = textureLoader.load('output/yu_nian_an/textures/Yu_Nian_An_Normal_4K.png');
  normalMap.flipY = false;
  const roughnessMap = textureLoader.load('output/yu_nian_an/textures/Yu_Nian_An_Roughness_4K.png');
  roughnessMap.flipY = false;
  const ormMap = textureLoader.load('output/yu_nian_an/textures/Yu_Nian_An_ORM_4K.png');
  ormMap.flipY = false;
  ```
  Verified: Present, valid Three.js loader syntax, assigns `SRGBColorSpace` and `flipY = false`.

### 1.3 Verification of Pre-Packed Texture Maps (Finding 4)
Inspected `Yu_Nian_An_ORM_4K.png` and `Yu_Nian_An_MaskMap_4K.png` via Pillow and NumPy:
- `Yu_Nian_An_ORM_4K.png`: Dimensions $4096 \times 4096$, mode `RGBA`, 32-bit:
  * Channel R (AO): $\min=63, \max=255, \mu=239.65, \sigma=26.20$
  * Channel G (Roughness): $\min=12, \max=178, \mu=104.47, \sigma=28.40$. Exactly identical to `Yu_Nian_An_Roughness_4K.png` (`np.array_equal == True`).
  * Channel B (Metallic): $\min=0, \max=255, \mu=6.68, \sigma=40.73$. Exactly identical to `Yu_Nian_An_Metallic_4K.png` (`np.array_equal == True`).
  * Channel A (SSS): $\min=0, \max=216, \mu=46.61, \sigma=53.11$. Exactly identical to `Yu_Nian_An_SSS_4K.png` (`np.array_equal == True`).
- `Yu_Nian_An_MaskMap_4K.png`: Dimensions $4096 \times 4096$, mode `RGBA`, 32-bit:
  * Channel R (Metallic): Exactly matches `Yu_Nian_An_Metallic_4K.png`.
  * Channel G (AO): Exactly matches cavity Ambient Occlusion.
  * Channel B (Detail/SSS): Exactly matches `Yu_Nian_An_SSS_4K.png`.
  * Channel A (Smoothness): Matches $255 - \text{Roughness}$ ($\max |\Delta| = 1$ due to float rounding).

### 1.4 Adversarial Audit of 3D Mesh UV Coordinates & Semantic Texture Sampling (Finding 1)
Direct extraction of vertex UV coordinates from `output/yu_nian_an/Yu_Nian_An.glb` and sampling against `output/yu_nian_an/textures/Yu_Nian_An_BaseColor_4K.png` (using the glTF standard texture mapping: $\text{col} = U \times W$, $\text{row} = V \times H$):

```
Mesh_Dress_Bodice_Mesh         prim 0: UV mean=(0.240, 0.137) -> pixel(984, 559)  -> RGB=[244, 228, 220] (Scalp/Skin)
Mesh_Dress_PleatedSkirt_Mesh   prim 0: UV mean=(0.244, 0.347) -> pixel(998, 1422) -> RGB=[208, 105, 122] (ROSE LIPS!)
Mesh_Dress_WaistSash_Mesh      prim 0: UV mean=(0.741, 0.323) -> pixel(3037, 1322)-> RGB=[245, 229, 222] (Body Skin)
Mesh_Lips_Mesh                 prim 0: UV mean=(0.250, 0.860) -> pixel(1024, 3522)-> RGB=[248, 246, 242] (WHITE SILK DRESS!)
Mesh_Lips_Mesh                 prim 1: UV mean=(0.257, 0.860) -> pixel(1052, 3522)-> RGB=[249, 247, 243] (WHITE SILK DRESS!)
Mesh_Sandal_L_Mesh             prim 0: UV mean=(0.662, 0.139) -> pixel(2713, 570) -> RGB=[245, 229, 222] (Body Skin)
Mesh_Sandal_R_Mesh             prim 0: UV mean=(0.662, 0.139) -> pixel(2713, 570) -> RGB=[245, 229, 222] (Body Skin)
Yu_Nian_An_Body                prim 0: UV mean=(0.699, 0.784) -> pixel(2863, 3210)-> RGB=[242, 240, 236] (Sandals/Sash)
Yu_Nian_An_Body                prim 1: UV mean=(0.239, 0.583) -> pixel(976, 2390) -> RGB=[251, 249, 245] (WHITE SILK DRESS!)
```

Blender scene sampling verification (`Yu_Nian_An_Master.blend`):
In Blender UV space, $(U, V) = (0, 0)$ is at the bottom-left of the image ($y=0$ in Blender pixel storage). Sampling `Yu_Nian_An_BaseColor_4K.png` at the UV coordinates assigned to `Mesh_Lips` ($U=0.25, V=0.14$):
- Pixel at $x=1024, V=0.14$: RGB = `[248, 246, 242]` (Ivory Silk Dress).
- Pixel at $x=1024, V=0.64$: RGB = `[195, 85, 105]` (Rose Lips).

---

## 2. Logic Chain

1. **Premise 1 (Texture Layout Generation)**: In `generate_yu_nian_an_pbr_textures()` (`src/morphomesh/character_assembler.py` lines 1883-1891):
   `y_coords, x_coords = np.mgrid[0:H, 0:W]`
   `u = x_coords / float(W)`
   `v = y_coords / float(H)`
   `mask_q1 = (u < 0.5) & (v < 0.5)` (Head & Face)
   `mask_q3 = (u < 0.5) & (v >= 0.5)` (Silk Dress)
   In NumPy array coordinates, `y_coords = 0` corresponds to the **top row** of the exported image. Therefore:
   - Rows $0$ to $H/2$ ($v < 0.5$) constitute the **top half** of the PNG file (Head, Face, Scalp, Lips).
   - Rows $H/2$ to $H$ ($v \ge 0.5$) constitute the **bottom half** of the PNG file (Silk Dress, Pleats, Sash).

2. **Premise 2 (Blender UV Coordinate Convention)**: In Blender's UV coordinate system (and OpenGL standard), the origin $(0, 0)$ is located at the **bottom-left** of the image:
   - $V \in [0.0, 0.5]$ maps to the **bottom half** of the image file (rows $H/2$ to $H$).
   - $V \in [0.5, 1.0]$ maps to the **top half** of the image file (rows $0$ to $H/2$).

3. **Observation Reference (Code Mismatch)**: In `_get_uv_unwrapping_script_snippet()` (`character_assembler.py` lines 248-254, 273-274, 319-320):
   - The worker mapped `Yu_Nian_An_Body` (head) to $V \in [0.0, 0.5]$.
   - The worker mapped `Mesh_Lips` to $V \in [0.08, 0.20]$.
   - The worker mapped `Mesh_Dress_Bodice` & `Mesh_Dress_PleatedSkirt` to $V \in [0.5, 1.0]$.

4. **Deduction 1 (Blender Inversion)**: By setting $V \in [0.0, 0.5]$ for the Head/Lips and $V \in [0.5, 1.0]$ for the Dress, the worker assigned the Head to the bottom half of UV space (where the Dress resides in the texture) and the Dress to the top half of UV space (where the Head resides in the texture).

5. **Deduction 2 (glTF / External Engine Inversion)**: When Blender exports glTF (`bpy.ops.export_scene.gltf`), it converts UV coordinates according to the glTF specification ($V_{\text{glTF}} = 1.0 - V_{\text{Blender}}$). Consequently:
   - `Mesh_Dress_PleatedSkirt` receives $V_{\text{glTF}} = 1.0 - [0.51, 0.79] = [0.21, 0.49]$ (top half of image), directly sampling the facial features and rose lips (`[208, 105, 122]`).
   - `Mesh_Lips` receives $V_{\text{glTF}} = 1.0 - [0.08, 0.20] = [0.80, 0.92]$ (bottom half of image), directly sampling the ivory silk dress (`[248, 246, 242]`).

6. **Deduction 3 (Self-Certifying Test Failure)**: `tests/test_production_exports.py` passed with 31/31 items because:
   - `test_base_color_texture_distribution` tested hardcoded array indices `arr[1475, 1024]` in the 2D image directly.
   - `test_glb_all_mesh_primitives_have_texcoord_0` only asserted that the string key `'TEXCOORD_0'` was present in primitive attribute dictionaries.
   - No test verified semantic sampling of the texture maps via the mesh UV attributes.

7. **Conclusion**: While the textures and geometry exist, the UV coordinate mapping is functionally broken across all target environments (Blender, Three.js, Unreal Engine, Unity), resulting in garbled rendering.

---

## 3. Detailed Findings

### Critical Finding 1: [INTEGRITY VIOLATION / FACADE IMPLEMENTATION] Inverted Vertical UV Mapping Between 3D Meshes and 4K Texture Atlas
- **What**: The vertical axis ($V$) in procedural UV unwrapping is inverted relative to the 2D texture generation coordinate system.
- **Where**:
  * `src/morphomesh/character_assembler.py`: `_get_uv_unwrapping_script_snippet()` (lines 248-254, 273-274, 295-296, 310-311, 319-321)
  * `output/yu_nian_an/Yu_Nian_An_Master.blend`
  * `output/yu_nian_an/Yu_Nian_An.glb`
  * `output/yu_nian_an/Yu_Nian_An.fbx`
  * `tests/test_production_exports.py`
- **Why**: 
  1. In the texture generation routine, $y=0$ is the top row of the image (Head/Face in rows $0 \dots H/2$).
  2. In Blender UV space, $V=0$ is the bottom of the image (rows $H/2 \dots H$).
  3. The UV assigner placed the Head in $V \in [0.0, 0.5]$ (bottom of image = Dress) and the Dress in $V \in [0.5, 1.0]$ (top of image = Head).
  4. In `Yu_Nian_An.glb` and external engines, the pleated skirt renders with rose lips/face skin, the lips render with white silk dress, and the head renders with white silk dress.
  5. The test suite failed to detect this because it only tested attribute dictionary keys (`"TEXCOORD_0" in attrs`) rather than testing the actual visual sampling of the asset.
- **Remediation**:
  1. **Option A (Preferred: Correct UV Unwrapping in `character_assembler.py`)**:
     Update `_get_uv_unwrapping_script_snippet()` so that the vertical UV coordinates align with Blender's texture space:
     - For `Yu_Nian_An_Body` (head/face): map $V \in [0.5, 1.0]$ (top half of image), with chin near $V=0.5$ and scalp near $V=1.0$:
       `V = 0.5 + 0.5 * (1.0 - v_norm)` (or matching the texture's $v1$).
     - For `Yu_Nian_An_Body` (body/limbs): map $V \in [0.5, 1.0]$ and $U \in [0.5, 1.0]$.
     - For `Mesh_Dress_*`: map $V \in [0.0, 0.5]$ (bottom half of image).
     - For `Mesh_Dress_WaistSash` & `Mesh_Sandal_*`: map $V \in [0.0, 0.5]$ and $U \in [0.5, 1.0]$.
     - For `Mesh_Lips`: map to the exact mouth coordinate in Blender UV space ($U \in [0.18, 0.32]$, $V \in [0.50 + 0.50 \times (1.0 - 0.72) \pm \dots]$).
     *OR*
  2. **Option B (Alternative: Flip Texture Atlas in `generate_yu_nian_an_pbr_textures`)**:
     Ensure $v = 0.0$ at the bottom of the image array ($v = 1.0 - y_{\text{coords}} / H$), aligning the 2D pixel generation with Blender's bottom-up UV origin.
  3. **Re-export All Production Assets**:
     Regenerate `Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, and `Yu_Nian_An.fbx`.
  4. **Add Semantic Texture Sampling Test in `tests/test_production_exports.py`**:
     Add an automated test that extracts the UV coordinates of `Mesh_Lips_Mesh` and `Mesh_Dress_PleatedSkirt_Mesh` from `Yu_Nian_An.glb`, samples `Yu_Nian_An_BaseColor_4K.png` at those coordinates, and asserts:
     - `Mesh_Lips_Mesh` sampled color has $R > G + 30$ and $R > B + 30$ (Rose lips).
     - `Mesh_Dress_PleatedSkirt_Mesh` sampled color is ivory silk ($R, G, B > 230$ and $|R - G| < 10$).

---

## 4. Verified Claims & Remediation Status Matrix

| Finding from Iteration 1 | Description | Iteration 2 Status | Verification Evidence |
|---|---|---|---|
| **Finding 1** | UV Coordinates & Atlas Quadrant Mapping on 3D Meshes | **REJECTED (CRITICAL INTEGRITY DEFECT)** | Meshes possess `TEXCOORD_0`, but $V$-axis is inverted relative to texture atlas. Skirt samples lips `[208, 105, 122]`; lips sample dress `[248, 246, 242]`. |
| **Finding 2** | UE5 Normal Map "Flip Green Channel" Instruction | **APPROVED** | Verified in `README_EXPORT.md` Section 5.A lines 121-123. Clear, accurate, covers Texture Editor -> Advanced -> Flip Green Channel. |
| **Finding 3** | Three.js PBR Texture Loading Sample Code | **APPROVED** | Verified in `README_EXPORT.md` Section 5.C lines 169-238. Complete `THREE.TextureLoader` integration with `SRGBColorSpace` and `flipY = false`. |
| **Finding 4** | Pre-Packed ORM and MaskMap 4K Textures on Disk | **APPROVED** | Verified on disk: `Yu_Nian_An_ORM_4K.png` and `Yu_Nian_An_MaskMap_4K.png` exist, strictly $4096 \times 4096$, 32-bit RGBA, packing AO, Roughness, Metallic, SSS, and Smoothness. |

---

## 5. Adversarial Challenge & Stress Test Results

| # | Stress Test Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| 1 | Full repository regression test suite (`pytest tests/`) | 100% pass across all test modules | 742 passed, 6 skipped in 91.53s | **PASS** |
| 2 | Pre-packed texture dimension & channel integrity | Strictly $4096 \times 4096$, 32-bit RGBA | Verified: $4096 \times 4096$, mode RGBA across both maps | **PASS** |
| 3 | ORM channel data source fidelity | G=Roughness, B=Metallic, A=SSS | `np.array_equal` confirms 100% exact match against source maps | **PASS** |
| 4 | MaskMap Smoothness channel fidelity | A = 1.0 - Roughness | Smoothness matches $255 - \text{Roughness}$ with $\max |\Delta| = 1$ | **PASS** |
| 5 | Three.js code sample syntax & options | `flipY = false`, `colorSpace = SRGBColorSpace` | Confirmed present in `README_EXPORT.md` Section 5.C | **PASS** |
| 6 | UE5 normal map tangent space documentation | Clear DirectX -Y inversion instruction | Confirmed present in `README_EXPORT.md` Section 5.A | **PASS** |
| 7 | **Semantic Texture Sampling of GLB via UV Coordinates** | Mesh UVs sample their respective atlas features | **FAIL: Skirt samples lips RGB=[208, 105, 122]; Lips sample dress RGB=[248, 246, 242]** | **FAIL (CRITICAL)** |
| 8 | **Blender Scene UV Alignment with Texture** | Mesh UVs sample correct colors in Blender | **FAIL: Mesh_Lips samples ivory silk at V=0.14; lips located at V=0.64 in Blender** | **FAIL (CRITICAL)** |

---

## 6. Caveats

No caveats. All findings are empirically demonstrated through binary glTF accessor parsing, image pixel array analysis, and headless Blender 4.5.4 LTS execution.

---

## 7. Conclusion & Required Action Items

Milestone 5 Iteration 2 has successfully resolved Findings 2, 3, and 4. However, Finding 1 contains a critical coordinate inversion defect that invalidates the visual output in all rendering engines.

**Verdict: `REQUEST_CHANGES`**

### Required Action Items for Worker M5:
1. **Fix UV Coordinate $V$-Axis Inversion**:
   In `src/morphomesh/character_assembler.py` (`_get_uv_unwrapping_script_snippet()` or `generate_yu_nian_an_pbr_textures()`), synchronize the vertical coordinate system so that meshes sample their corresponding texture features.
2. **Re-export Production Assets**:
   Re-export `Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, and `Yu_Nian_An.fbx`.
3. **Upgrade Unit Tests with Semantic Sampling Assertions**:
   In `tests/test_production_exports.py`, add assertions that sample `Yu_Nian_An_BaseColor_4K.png` using the actual UV coordinates of `Mesh_Lips` and `Mesh_Dress_PleatedSkirt` to prevent regression.

---

## 8. Verification Method

To independently verify the fix:

```powershell
# 1. Verify semantic UV texture sampling on GLB:
& 'E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe' -c "
import json, struct
from PIL import Image
import numpy as np

with open('output/yu_nian_an/Yu_Nian_An.glb', 'rb') as f:
    f.seek(12)
    cl, _ = struct.unpack('<II', f.read(8))
    d = json.loads(f.read(cl).decode('utf-8'))
    bl, _ = struct.unpack('<II', f.read(8))
    bd = f.read(bl)

def get_uvs(prim):
    acc = d['accessors'][prim['attributes']['TEXCOORD_0']]
    bv = d['bufferViews'][acc['bufferView']]
    off = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
    return np.frombuffer(bd, dtype=np.float32, count=acc['count']*2, offset=off).reshape((acc['count'], 2))

img = np.array(Image.open('output/yu_nian_an/textures/Yu_Nian_An_BaseColor_4K.png'))
h, w, _ = img.shape

for m in d.get('meshes', []):
    name = m.get('name', '')
    if 'Lips' in name:
        uv = get_uvs(m['primitives'][0]).mean(axis=0)
        c = img[int(uv[1]*h), int(uv[0]*w)]
        assert c[0] > c[1] + 30, f'Lips sampled wrong color: {c}'
        print('Lips correctly sampled rose vermilion:', c)
    elif 'PleatedSkirt' in name:
        uv = get_uvs(m['primitives'][0]).mean(axis=0)
        c = img[int(uv[1]*h), int(uv[0]*w)]
        assert c[0] > 230 and c[1] > 230 and c[2] > 230, f'Dress sampled wrong color: {c}'
        print('Dress correctly sampled ivory silk:', c)
"

# 2. Run dedicated production tests:
& 'E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe' -m pytest tests/test_production_exports.py -v
```
