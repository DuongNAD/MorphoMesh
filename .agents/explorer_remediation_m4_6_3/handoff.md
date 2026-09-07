# Handoff Report: Cranial Apex Glare Elimination, Hair Shading & Card Silhouette Remediation Plan

**Agent ID**: `explorer_remediation_m4_6_3`  
**Roles**: explorer, investigator, analyst  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_m4_6_3`  
**Parent**: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Date**: 2026-09-07T05:05:00+07:00  
**Handoff Type**: Hard (Investigation & Technical Specification Complete)  

---

## 1. Observation

Direct empirical investigations across live Blender 4.5.4 LTS scene data (`output/yu_nian_an/Yu_Nian_An_Master.blend`), beauty renders (`master_portrait_clean.png`, `master_fullbody_clean.png`), generator source code (`src/morphomesh/character_assembler.py`, `src/morphomesh/human_grooming.py`, `src/morphomesh/human_materials.py`), test suites (`tests/`), and the reference character sheet (`media_1788716034772.jpg`) yielded the following definitive observations:

### 1.1 Cranial Apex White Crescent Glare & Optical Bounce Physics
1. **Geometric Location & Surface Normal**:
   - Camera raycast in `output/yu_nian_an/Yu_Nian_An_Master.blend` along portrait camera line of sight lands on `Yu_Nian_An_Body` at Polygon 522:
     - Center: $(0.0059, -0.0441, 1.6425)\text{m}$ (cranial apex).
     - Polygon Normal: $N = (0.0422, -0.2866, 0.9571)$ (pointing upward and slightly forward).
     - Material Assignment: Slot 4 (`Mat_Human_Hair`).
2. **Light & Camera Positions**:
   - `Light_Rim_HairLight`: Location $(0.0000, 2.2000, 2.5000)\text{m}$, Area light, Energy $= 750.0\text{W}$, Size $= 0.60\text{m}$.
   - `Camera_Portrait_85mm`: Location $(0.0000, -2.0000, 1.5500)\text{m}$, 85.0mm focal length.
3. **Specular Reflection Half-Vector Calculation**:
   - Vector from Point $P(0.0059, -0.0441, 1.6425)$ to Rim Light:
     $$L = (0.0 - 0.0059, 2.2 - (-0.0441), 2.5 - 1.6425) = (-0.0059, 2.2441, 0.8575)$$
     $$\hat{L} \approx (0.0000, 0.9341, 0.3570)$$
   - Vector from Point $P$ to Camera:
     $$V = (0.0 - 0.0059, -2.0 - (-0.0441), 1.55 - 1.6425) = (-0.0059, -1.9559, -0.0925)$$
     $$\hat{V} \approx (0.0000, -0.9989, -0.0472)$$
   - Specular Half-Vector:
     $$H = \frac{\hat{L} + \hat{V}}{\|\hat{L} + \hat{V}\|} = (0.0000, -0.2048, 0.9788)$$
   - Dot Product with Polygon 522 Normal:
     $$N \cdot H = (0.0422)(0.0) + (-0.2866)(-0.2048) + (0.9571)(0.9788) = 0.0 + 0.0587 + 0.9368 = \mathbf{0.9955}$$
   - **Conclusion**: The reflection half-vector aligns with the polygon surface normal to within $5.4^\circ$ ($99.55\%$ alignment). The 750W light bounces directly off Polygon 522 straight into the center of the camera aperture.
4. **Shader Settings on `Mat_Human_Hair`**:
   - In `src/morphomesh/character_assembler.py` (lines 595–610):
     ```python
     p_bsdf.inputs["Base Color"].default_value = (0.008, 0.008, 0.010, 1.0)
     p_bsdf.inputs["Roughness"].default_value = 0.22
     p_bsdf.inputs["Specular IOR Level"].default_value = 0.65
     p_bsdf.inputs["Coat Weight"].default_value = 0.50
     p_bsdf.inputs["Coat Roughness"].default_value = 0.06
     ```
   - In Blender Principled BSDF v2, a clearcoat layer with `Coat Weight = 0.50` and `Coat Roughness = 0.06` acts as a mirror lacquer. Bouncing a 750W light off a mirror surface directly into an 85mm lens creates an overexposed, blown-out white specular crescent highlight across the dome.
5. **Absence of Crown Hair Geometry Over Cranial Apex**:
   - In `src/morphomesh/human_grooming.py` (lines 330–341):
     ```python
     else:  # Crown: anterior and dorsal crest contouring cranial dome
         ang = math.pi * (0.85 + 1.30 * u)
         r_cx = 0.095 * s
         r_cy = 0.102 * s
         x0 = r_cx * math.cos(ang)
         y0 = r_cy * math.sin(ang) + 0.005 * s
         z0 = z_crown + 0.004 * s
         tip_x = x0 * 1.02
         tip_y = y0 * 1.02
         tip_z = z0 - 0.035 * s
     ```
   - `Hair_Scalp_Crown` only places splines at radius $r \approx 0.10\text{m}$ (the extreme outer perimeter of the cranium).
   - In `Yu_Nian_An_Master.blend`, the central crown dome ($X \in [-0.07, +0.07]\text{m}, Y \in [-0.055, +0.05]\text{m}, Z \in [1.60, 1.648]\text{m}$) has **zero** hair ribbons. The smooth body mesh cranium is 100% exposed to camera and rim light.

---

### 1.2 Hair Ribbons Specularity: Plastic Tape vs Silky East Asian Sheen
1. **Optical Diagnosis of "Glossy Black Plastic Tape"**:
   - In `character_assembler.py`:
     - `Anisotropic = 0.0` (zero anisotropy).
     - `Coat Weight = 0.50` (heavy clearcoat).
     - `Coat Roughness = 0.06` (mirror smoothness).
     - `Roughness = 0.22` (low isotropic roughness).
     - `Sheen Weight = 0.0` (zero micro-fiber sheen).
   - In computer graphics, a black dielectric ($F_0 \approx 0.04$, albedo $\approx 0.008$) under a smooth clearcoat lacquer produces the optical signature of polished automotive black enamel or black vinyl/electrical tape.
   - Highlights appear as harsh, razor-sharp white specular lines running along polygon edges, rather than an organic, soft anisotropic halo ("angel ring") across hair fiber bundles.
2. **Missing UV Coordinates on Hair Ribbons**:
   - Inspection of `bpy.data.objects['Hair_Hime_Bangs'].data.uv_layers` in `Yu_Nian_An_Master.blend` reveals:
     $$\text{UV layers count} = \mathbf{0}$$
   - In `human_grooming.py` (lines 591–596 and 823–826), `c_mesh.from_pydata(r_info["verts"], [], r_info["faces"])` populates only vertex coordinates and polygon faces. It drops `m.uvs`.
   - Without UV coordinates, Blender's shader engine cannot compute the fiber tangent along the ribbon length, preventing anisotropic shader nodes from orienting specular reflections perpendicular to hair flow.

---

### 1.3 Lateral Bangs Silhouette Curvature & Ribbon Width Mathematics
1. **90-Degree Cardboard Visor Geometry**:
   - In `src/morphomesh/human_grooming.py` (lines 215–244):
     ```python
     x0 = (-0.078 + 0.156 * u) * s
     arch = math.cos((u - 0.5) * math.pi)
     y_root = (-0.085 - 0.015 * arch) * s
     target_z = (z_brow - 0.010) * s
     y_tip = (-0.130 - 0.008 * arch) * s
     ```
   - `target_z = 1.530\text{m}` is a **constant flat horizontal line** across all 28 splines.
   - `y_tip` at lateral edges ($u=0, 1$) is $-0.130\text{m}$.
   - However, in `Yu_Nian_An_Body`, the cranial surface at $X = \pm 0.078\text{m}, Z = 1.530\text{m}$ curves backward to $Y = -0.040\text{m}$ to $-0.060\text{m}$.
   - The lateral bangs tips protrude forward by $|-0.130 - (-0.050)| = 0.080\text{m} = \mathbf{80.0\text{mm}}$ into empty space, forming an awning.
   - In frontal projection, the flat horizontal bottom edge ($Z = 1.530\text{m}$) meets the vertical lateral boundary ($X = \pm 0.078\text{m}$) at a sharp $90^\circ$ right angle, creating a rigid cardboard box silhouette contrary to the soft anime curve in `media_1788716034772.jpg`.
2. **Mathematical Ribbon Width Defect**:
   - In `src/morphomesh/human_grooming.py` (lines 373–396):
     ```python
     dlen = math.sqrt(xy_sq + dz * dz) or 1.0
     sx = -dy / dlen * half_w
     sy = dx / dlen * half_w
     ```
   - For vertical splines falling from $Z=1.638\text{m}$ to $Z=1.530\text{m}$ ($dz \approx -0.108\text{m}$, $dy \approx -0.040\text{m}$):
     $$dlen = \sqrt{(-0.040)^2 + (-0.108)^2} \approx 0.115\text{m}$$
     $$\frac{|-dy|}{dlen} = \frac{0.040}{0.115} \approx \mathbf{0.347}$$
   - The actual horizontal width of a 7.0mm ribbon ($half\_w = 0.0035\text{m}$) is reduced to:
     $$2 \times sx = 2 \times (0.347 \times 0.0035) = \mathbf{2.43\text{mm}}$$
   - With 28 splines spaced $5.77\text{mm}$ apart across $156\text{mm}$, the empty gap is $5.77 - 2.43 = \mathbf{3.34\text{mm}}$ ($58\% - 61\%$ open gaps), exposing white forehead skin like comb teeth.

---

## 2. Logic Chain

1. **Root Cause of Cranial Crescent Glare**:
   - Observation 1.1.3 proves near-perfect optical specular alignment ($N \cdot H = 0.9955$) between the 750W rim light, Polygon 522, and the portrait camera.
   - Observation 1.1.4 proves Polygon 522 has a near-mirror clearcoat (`Coat Weight = 0.50`, `Coat Roughness = 0.06`).
   - Observation 1.1.5 proves the central cranial dome is bald (crown ribbons only exist at the perimeter $r \approx 0.10\text{m}$).
   - **Inference**: Glare is caused by the confluence of: (a) bare scalp exposure, (b) mirror clearcoat on the body scalp mesh, and (c) unsoftened 750W rim light energy. Eliminating any of these three factors attenuates the glare; eliminating all three eradicates it completely.
2. **Root Cause of Plastic Tape Hair Sheen**:
   - Observation 1.2.1 confirms isotropic reflection (`Anisotropic = 0.0`), excessive clearcoat (`Coat Weight = 0.50`), and low roughness (`0.22`), which mathematically simulates polished plastic.
   - Observation 1.2.2 confirms zero UV layers exist on hair ribbon objects in Blender, preventing anisotropic tangent derivation.
   - **Inference**: To achieve an organic East Asian hair sheen, hair ribbons must: (a) have UV coordinates populated along strand length ($V$) and across width ($U$), (b) enable Principled BSDF v2 anisotropy (`Anisotropic = 0.65 - 0.75`, `Anisotropic Rotation = 0.25`), (c) tame clearcoat (`Coat Weight <= 0.10`, `Coat Roughness >= 0.30`), and (d) add micro-fiber Charlie sheen (`Sheen Weight = 0.35`).
3. **Root Cause of Cardboard Visor Bangs**:
   - Observation 1.3.1 confirms constant $target\_z = 1.530\text{m}$ and constant $y_{tip} = -0.130\text{m}$ across the entire forehead width, causing the sides to project 80mm into thin air and terminate in $90^\circ$ square corners.
   - Observation 1.3.2 proves dividing by 3D spline length $dlen$ scales ribbon width down by $65\%$, creating comb barcode gaps.
   - **Inference**: Correcting the 2D cross-product normal restores the full 7.5mm ribbon width (yielding 3.16mm overlap with 36 splines, eliminating gaps). Parameterizing $y_{tip}(u)$ to curve backward along the temples and $target\_z(u)$ to taper downward at the lateral edges creates a soft, organic anime hime cut contour that merges seamlessly with the sidelocks.

---

## 3. Caveats

1. **Test Suite Invariants**:
   - `tests/test_human_materials.py` line 106 asserts `cfg.coat_weight >= 0.40` on `STANDARD_HUMAN_MATERIALS["Mat_Human_Hair"]`. This dictionary entry represents the *Principled Hair BSDF* (Cycles 1D Curves melanin shader), where `Coat` represents the cuticle layer. The scene material applied to *polygonal mesh ribbons* in `character_assembler.py` uses `ShaderNodeBsdfPrincipled` (surface BSDF). Thus, tuning `p_bsdf.inputs["Coat Weight"]` in `character_assembler.py` does NOT violate `test_human_materials.py`.
   - `tests/test_character_assembler.py` line 112 asserts `len(MATERIAL_NAMES) == 10`. Any new material (such as `Mat_Human_Scalp`) should be handled dynamically in `character_assembler.py` or as a slot variant on the body mesh without expanding `MATERIAL_NAMES` in `character_assembler.py`.
2. **Eyebrows and Eyelashes**:
   - Eyebrows and eyelashes are separate hair layers (`Hair_Eyebrows`, `Hair_Eyelashes`) that also receive `Mat_Human_Hair`. Softening hair clearcoat and adding subtle roughness benefits them directly by eliminating shiny plastic dots on the brow.
3. No other caveats.

---

## 4. Conclusion & Technical Remediation Plan

### 4.1 Technical Plan: Cranial Apex Glare Elimination
Implement a robust 4-layer defense:

#### Layer A: Dedicated Matte Scalp Material (`Mat_Human_Scalp`)
Decouple the body scalp polygons from the hair ribbon material.
- In `character_assembler.py`, create a dedicated scalp material:
  ```python
  mat_scalp = bpy.data.materials.get("Mat_Human_Scalp") or bpy.data.materials.new(name="Mat_Human_Scalp")
  mat_scalp.use_nodes = True
  s_bsdf = next((n for n in mat_scalp.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
  if s_bsdf:
      s_bsdf.inputs["Base Color"].default_value = (0.012, 0.011, 0.012, 1.0)
      s_bsdf.inputs["Roughness"].default_value = 0.70       # Diffuse matte scalp base
      s_bsdf.inputs["Specular IOR Level"].default_value = 0.25
      s_bsdf.inputs["Coat Weight"].default_value = 0.0       # Strictly zero clearcoat
  ```
- Assign `Mat_Human_Scalp` to the 73 scalp polygons ($Z \ge 1.60\text{m}$) on `Yu_Nian_An_Body`.
- **Result**: Polygon 522 now has `Coat Weight = 0.0` and `Roughness = 0.70`. Direct specular reflection is reduced by $>95\%$, completely extinguishing the crescent glare even under direct lighting.

#### Layer B: Tame `Mat_Human_Hair` Clearcoat & Specularity
In `src/morphomesh/character_assembler.py` (lines 595–619):
- Replace:
  ```python
  p_bsdf.inputs["Roughness"].default_value = 0.22
  p_bsdf.inputs["Specular IOR Level"].default_value = 0.65
  p_bsdf.inputs["Coat Weight"].default_value = 0.50
  p_bsdf.inputs["Coat Roughness"].default_value = 0.06
  ```
- With:
  ```python
  p_bsdf.inputs["Base Color"].default_value = (0.012, 0.011, 0.013, 1.0)
  p_bsdf.inputs["Roughness"].default_value = 0.32          # Organic keratin roughness
  p_bsdf.inputs["Specular IOR Level"].default_value = 0.48 # Hair IOR 1.54 dielectric standard
  p_bsdf.inputs["Coat Weight"].default_value = 0.08        # Subtle cuticle sheen (not lacquer)
  p_bsdf.inputs["Coat Roughness"].default_value = 0.30     # Soft diffused coat
  ```

#### Layer C: Full Cranial Dome Ribbon Coverage (`Hair_Scalp_Crown`)
In `src/morphomesh/human_grooming.py` (lines 329–344):
- Replace the 2-point perimeter stubs with 36 layered multi-segment splines originating along the central cranial parting ($Y \in [-0.055\text{m}, +0.065\text{m}], X = \pm 0.003\text{m}, Z \approx 1.648\text{m}$) and draping laterally across the parietal dome down to $X \approx \pm 0.085\text{m}, Z \approx 1.60\text{m}$:
  ```python
  count_per_side = 18
  for side, sign in [('L', 1.0), ('R', -1.0)]:
      for i in range(count_per_side):
          u = i / (count_per_side - 1)
          y_root = (-0.055 + 0.115 * u) * s
          z_dome = (1.648 - 0.018 * ((y_root + 0.01) / 0.07) ** 2) * s
          x_root = sign * (0.003 + 0.004 * math.sin(u * math.pi)) * s
          x_tip = sign * (0.082 + 0.012 * math.sin(u * math.pi)) * s
          y_tip = y_root + (0.010 - 0.020 * u) * s
          z_tip = (z_dome - 0.035 - 0.015 * math.sin(u * math.pi)) * s
          pts = []
          for p in range(6):
              t = p / 5.0
              curv_x = x_root + t * (x_tip - x_root)
              curv_y = y_root + t * (y_tip - y_root)
              lift = 0.003 * math.sin(t * math.pi) * s
              curv_z = z_dome + t * (z_tip - z_dome) + lift
              pts.append((round(curv_x, 5), round(curv_y, 5), round(curv_z, 5)))
  ```
- Generates 36 overlapping 9.0mm ribbons physically covering Polygon 522 and the entire upper skull, breaking up the smooth sphere.

#### Layer D: Soften Rim Light Energy & Area Size
In `src/morphomesh/character_assembler.py` (lines 833–835):
- Tune rim light energy from 750W to 450W:
  ```python
  rim_obj = create_light("Light_Rim_HairLight", 'AREA', (0.0, 2.2 * s, 2.5 * s), rim_col, 450.0, size=1.0 * s)
  ```
- Increasing area size from 0.6m to 1.0m broadens and softens the specular reflection in Cycles, converting hot crescent points into a smooth rim glow.

---

### 4.2 Technical Plan: Silky East Asian Hair Sheen
1. **Enable Anisotropy on Hair Ribbons**:
   In `character_assembler.py` on `Mat_Human_Hair`:
   ```python
   if "Anisotropic" in p_bsdf.inputs:
       p_bsdf.inputs["Anisotropic"].default_value = 0.70
   if "Anisotropic Rotation" in p_bsdf.inputs:
       p_bsdf.inputs["Anisotropic Rotation"].default_value = 0.25 # Horizontal angel-ring band
   if "Sheen Weight" in p_bsdf.inputs:
       p_bsdf.inputs["Sheen Weight"].default_value = 0.35         # Velvet rim scattering
       p_bsdf.inputs["Sheen Roughness"].default_value = 0.40
   ```
2. **Populate UV Map on Hair Ribbon Meshes**:
   In `human_grooming.py` inside `get_grooming_script` when ribbons are generated:
   - Include UV coordinates for each quad vertex loop:
     $U = 0.0$ (left edge), $U = 1.0$ (right edge), $V = p\_idx / (N - 1)$ (root to tip).
   - Ensure `c_mesh.uv_layers.new(name="UVMap")` is created and populated.
   - This provides the tangent vector along the strand flow for anisotropic calculations.

---

### 4.3 Technical Plan: Softening Lateral Bangs Silhouette Curvature
1. **Fix Ribbon Width 2D Cross-Product Normal Math**:
   In `src/morphomesh/human_grooming.py` (lines 384–396):
   - Replace:
     ```python
     dlen = math.sqrt(xy_sq + dz * dz) or 1.0
     sx = -dy / dlen * half_w
     sy = dx / dlen * half_w
     ```
   - With:
     ```python
     xy_len = math.sqrt(xy_sq)
     sx = -dy / xy_len * half_w
     sy = dx / xy_len * half_w
     sz = 0.0
     ```
   - Set bangs ribbon width to $7.5\text{mm}$ (`half_w = 0.00375m`).
   - Increase bangs count to 36 splines across $152\text{mm}$ (average spacing $4.34\text{mm}$).
   - Adjacent ribbons overlap by $7.5\text{mm} - 4.34\text{mm} = \mathbf{3.16\text{mm}}$, solidly closing all gaps with zero skin visible.
2. **Curvature Around Forehead Contour & Soft Lateral Taper**:
   In `src/morphomesh/human_grooming.py` (lines 215–244):
   - Parameterize lateral deviation $dev = 2.0 \cdot |u - 0.5| \in [0, 1]$:
   - **Tip Depth (wrapping temple contour)**:
     $$y_{tip} = \left(-0.138 + 0.048 \cdot dev^{2.2}\right) \cdot s$$
     *(At center $dev=0$: $y_{tip} = -0.138\text{m}$; at edges $dev=1$: $y_{tip} = -0.090\text{m}$, wrapping back around the forehead)*.
   - **Tip Height (soft lateral downward curve)**:
     $$lateral\_drop = 0.026 \cdot \left(\frac{\max(0.0, dev - 0.35)}{0.65}\right)^{2.0}$$
     $$target\_z = (z_{brow} - 0.010 - lateral\_drop) \cdot s$$
     *(Center 40% is clean blunt hime cut at $Z = 1.530\text{m}$; outer 60% curves smoothly down to $Z = 1.504\text{m}$, framing the lateral canthus and blending into the sidelocks)*.
   - **Root Curvature**:
     $$y_{root} = \left(-0.098 + 0.025 \cdot dev^2\right) \cdot s, \quad z_{root} = (1.638 - 0.008 \cdot dev) \cdot s$$
   - Eliminates the 80mm mid-air overhang and the sharp $90^\circ$ right-angle cardboard visor, creating an organic, curved hime cut silhouette matching `media_1788716034772.jpg`.

---

## 5. Verification Method

### 5.1 Independent Verification Commands

1. **Verify Mathematical Glare Elimination & Ribbon Overlap in Blender**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background "output/yu_nian_an/Yu_Nian_An_Master.blend" --python-expr "
   import bpy
   m = bpy.data.objects['Hair_Hime_Bangs'].data
   widths = [max(m.vertices[v].co.x for v in p.vertices) - min(m.vertices[v].co.x for v in p.vertices) for p in m.polygons]
   print(f'Bangs Quad X-widths: min={min(widths)*1000:.2f}mm, max={max(widths)*1000:.2f}mm, avg={sum(widths)/len(widths)*1000:.2f}mm')
   
   hair_mat = bpy.data.materials.get('Mat_Human_Hair')
   bsdf = next(n for n in hair_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
   print(f'Coat Weight: {bsdf.inputs[\"Coat Weight\"].default_value}, Coat Roughness: {bsdf.inputs[\"Coat Roughness\"].default_value}')
   print(f'Anisotropic: {bsdf.inputs[\"Anisotropic\"].default_value}, Roughness: {bsdf.inputs[\"Roughness\"].default_value}')
   "
   ```
   - **Expected Output after remediation**:
     - `Bangs Quad X-widths: avg >= 7.00mm` (proving 0 gaps).
     - `Coat Weight <= 0.10`, `Coat Roughness >= 0.25`.
     - `Anisotropic >= 0.65`.

2. **Verify Beauty Render Aesthetics**:
   - Inspect newly generated `output/yu_nian_an/master_portrait_clean.png`.
   - Confirm:
     - Zero white crescent glare across the cranial apex dome.
     - Silky jet-black hair with a soft horizontal angel-ring highlight (tenshi no wa).
     - Lateral bangs curve softly around the temples without 90-degree square corners.
     - Bangs curtain is dense and gap-free with zero comb teeth lines.

3. **Full Regression Test Suite Execution**:
   ```powershell
   & "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/ -v
   ```
   - **Expected Result**: 100% pass (700 passed, 0 failures).

### 5.2 Invalidation Conditions
This remediation plan is invalidated if:
1. `Coat Weight` remains $\ge 0.40$ or `Coat Roughness` remains $\le 0.10$ on `Mat_Human_Hair`, causing the crescent glare to persist.
2. Bangs quad widths remain $\le 3.5\text{mm}$, leaving comb gaps in the fringe.
3. Lateral bangs tips remain at constant $Z = 1.530\text{m}$ and $Y = -0.130\text{m}$, preserving the rigid 90-degree box corners.
