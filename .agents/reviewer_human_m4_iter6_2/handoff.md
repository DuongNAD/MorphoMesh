# Handoff Report: Milestone 4 Iteration 6 Aesthetic Likeness, Lips, Eyes, Bangs & Shading Review

**Agent**: `reviewer_human_m4_iter6_2`  
**Roles**: reviewer, critic  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter6_2`  
**Parent**: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Date**: 2026-09-07T05:26:30+07:00  
**Verdict**: **REQUEST_CHANGES**  
**Handoff Type**: Hard (Adversarial Quality Review Complete)

---

## 1. Observation

Direct empirical observations, live Blender 4.5.4 LTS BVH geometric analyses, shader inspections, and forensic renders (`master_portrait_clean.png`, `master_fullbody_clean.png`, and a newly rendered 135mm high-magnification face plate `audit_face_closeup.png`) were conducted across `output/yu_nian_an/Yu_Nian_An_Master.blend`, `src/morphomesh/character_assembler.py`, `src/morphomesh/human_grooming.py`, `src/morphomesh/human_materials.py`, and reference turnaround art `media_1788716034772.jpg`:

### 1.1 Mouth & Lip Likeness (Defect 1)
1. **Base Mesh Polygons 377 and 378**:
   - In `output/yu_nian_an/Yu_Nian_An_Master.blend`, `Yu_Nian_An_Body.data.polygons[377].material_index == 0` (`Mat_Human_Skin_SSS`) and `polygons[378].material_index == 0` (`Mat_Human_Skin_SSS`).
   - The flat 25mm x 33mm bright pink rectangular tape block from Iteration 5 has been completely removed from `Yu_Nian_An_Body`.
2. **`Mesh_Lips` Severe Submersion & Penetration**:
   - `Mesh_Lips` exists as a dedicated 6-row x 11-column pure quad submesh (50 quads, 66 vertices, pure quads 100%, 0 triangles) parented to `Yu_Nian_An_Body` in collection `01_Body` and bound 100% to vertex group `DEF-head`.
   - **Empirical BVH Distance & Penetration Measurement against `Yu_Nian_An_Body`**:
     ```text
     Mesh_Lips total vertices: 66
     Mesh_Lips vertices penetrating inside body (dot < 0): 52 / 66 (78.8%)
     Normal penetration offset: min = -6.47mm, avg = -2.48mm, max = +1.68mm
     Mesh_Lips center Y: -0.1169m to -0.1194m
     Yu_Nian_An_Body face surface Y at (X=0, Z=1.4703m): -0.1238m
     ```
   - Because negative Y is forward in Blender, $Y = -0.1169\text{m}$ is **6.9mm behind** the anterior facial skin surface ($Y = -0.1238\text{m}$).
   - **78.8% of `Mesh_Lips` vertices are buried inside the solid opaque head**.
   - In both `master_portrait_clean.png` and high-magnification `audit_face_closeup.png`, the lips are almost completely invisible. Only an accidental 1.68mm corner peeks out through the cheek surface, rendering as a tiny, broken, faint, asymmetrical pale pink smudge with an amputated right corner. There is **zero visible cupid's bow, zero visible lower lip fullness, and zero visible oral fissure**.
3. **`materials.clear()` Index Reset Bug (Zero Oral Slit Polygons)**:
   - In `src/morphomesh/character_assembler.py` (lines 578–583), `create_delicate_anime_lips_mesh` assigns `face.material_index = 1` (`Mat_Human_Oral_Slit`) for row $r=2$:
     ```python
     if r == 2 and 1 <= c <= n_cols - 2:
         face.material_index = 1  # Mat_Human_Oral_Slit
     else:
         face.material_index = 0  # Mat_Human_Lips
     ```
   - However, at lines 705–708 of `character_assembler.py`:
     ```python
     for e_obj, e_mats in [..., (lip_mesh, [mat_lips, mat_oral_slit])]:
         if hasattr(e_obj.data, "materials"):
             e_obj.data.materials.clear()
             for m in e_mats:
                 if m:
                     e_obj.data.materials.append(m)
     ```
   - In Blender Python, calling `mesh.materials.clear()` clamps all polygon `material_index` attributes to 0.
   - **Empirical Polygon Material Distribution in `Yu_Nian_An_Master.blend`**:
     ```text
     Mesh_Lips materials: ['Mat_Human_Lips', 'Mat_Human_Oral_Slit']
     Polygon material distribution: {0: 50}
     Polygons assigned to Slot 0 (Mat_Human_Lips): 50 / 50 (100%)
     Polygons assigned to Slot 1 (Mat_Human_Oral_Slit): 0 / 50 (0.0%)
     ```
   - **Not a single polygon in `Mesh_Lips` is assigned to `Mat_Human_Oral_Slit`**. The dark oral fissure slit claimed in the worker handoff does not exist in the 3D asset.

### 1.2 Forehead Bangs Coverage & Silhouette (Defect 2)
1. **Vector Math Invariance in `src/morphomesh/human_grooming.py`**:
   - In `src/morphomesh/human_grooming.py` (lines 392–405), the side vector normal is now computed strictly using horizontal length `xy_len = math.sqrt(xy_sq)` rather than 3D tangent length `dlen`:
     ```python
     xy_sq = dx * dx + dy * dy
     if xy_sq < 1e-12:
         sx = half_w; sy = 0.0; sz = 0.0
     else:
         xy_len = math.sqrt(xy_sq)
         sx = -dy / xy_len * half_w
         sy = dx / xy_len * half_w
     ```
   - **Empirical Measurement in Live Blender**:
     ```text
     Hair_Hime_Bangs: 2,640 vertices, 2,420 quads (100% quads)
     3D ribbon edge width: min = 7.49mm, avg = 7.50mm, max = 7.51mm (invariant)
     Projected Quad X-widths: min = 5.66mm, avg = 7.45mm, max = 7.76mm
     ```
   - The Iteration 5 ribbon width collapse bug (where quad width shrank to 2.25mm) is **fully resolved**.
2. **Forehead Bangs Overlap & Zero Gaps**:
   - `Hair_Hime_Bangs` comprises 110 ribbon islands across $X \in [-83.8\text{mm}, +83.8\text{mm}]$.
   - Consecutive adjacent ribbon pairs: **109 pairs**.
   - Overlap between adjacent ribbons: **min = 6.06mm, avg = 7.29mm, max = 8.16mm**.
   - Gaps ($gap > 0$): **0 gaps**.
   - Forehead skin is completely covered by an opaque, dense hair curtain with zero barcode comb gaps.
3. **Temple Curvature**:
   - Central bangs ($X = 0$): root $Y = -98.0\text{mm}$, tip $Y = -130.0\text{mm}, Z \in [1.530\text{m}, 1.640\text{m}]$.
   - Lateral bangs ($X = \pm 79.0\text{mm}$): root $Y = -52.7\text{mm}$, tip $Y = -77.5\text{mm}, Z \in [1.5117\text{m}, 1.628\text{m}]$.
   - Roots recede backward by 45.3mm and tips sweep backward by 52.5mm, following the parietal/temporal cranial contour.

### 1.3 Eyelids & Eye Optics (Defect 3)
1. **Eyelid Material Assignment Defect (Raccoon Eyeliner Artifact)**:
   - In `character_assembler.py` (lines 643–644), `create_almond_eyelid_mesh` attempts to assign Slot 0 (`Mat_Human_Eyeliner`) to the upper lid and Slot 1 (`Mat_Human_Skin_SSS`) to the lower lid:
     ```python
     face.material_index = 0 if sin_mid >= -0.15 else 1
     ```
   - However, due to `e_obj.data.materials.clear()` on line 705, Blender reset all face indices to 0.
   - **Empirical Polygon Material Distribution in `Yu_Nian_An_Master.blend`**:
     ```text
     Mesh_Eyelid_Left materials: ['Mat_Human_Eyeliner', 'Mat_Human_Skin_SSS']
     Mesh_Eyelid_Left poly mat distribution: {0: 16}
     Mesh_Eyelid_Right materials: ['Mat_Human_Eyeliner', 'Mat_Human_Skin_SSS']
     Mesh_Eyelid_Right poly mat distribution: {0: 16}
     ```
   - Exactly **0 out of 16 polygons** are assigned to `Mat_Human_Skin_SSS`.
   - **100% of the eyelid mesh is solid black eyeliner**, wrapping all the way around the lower orbital margin. In `audit_face_closeup.png`, this manifests as an unnatural dark black ring around the entire lower eye.
2. **Eye Optics & Cornea Setup**:
   - `Mesh_Eye_Left_IrisPupil` and `Mesh_Eye_Right_IrisPupil` possess forward planar UV coordinates in $[0.0, 1.0]$.
   - `Mat_Human_Eye_Inner_Iris` features a 7-stop radial color ramp for pupil, slate iris, and limbal ring.
   - However, in beauty renders, the cornea's transmission/reflection together with the black lower eyeliner ring produces a dull, milky gaze that still lacks the sharp, lively contrast of the reference art.

### 1.4 Cranial Apex Glare & Hair Sheen (Defect 4)
1. **Matte Scalp Assignment**:
   - Exactly **73 polygons** on `Yu_Nian_An_Body` ($Z \ge 1.60\text{m}$) are assigned to `Mat_Human_Scalp`.
   - `Mat_Human_Scalp` parameters: `Roughness = 0.70`, `Specular IOR Level = 0.25`, `Coat Weight = 0.0`.
2. **Hair Material & Rim Lighting**:
   - `Mat_Human_Hair` parameters: `Roughness = 0.32`, `Specular IOR Level = 0.48`, `Coat Weight = 0.08`, `Coat Roughness = 0.30`, `Anisotropic = 0.70`, `Anisotropic Rotation = 0.25`, `Sheen Weight = 0.35`, `Sheen Roughness = 0.40`.
   - `Light_Rim_HairLight`: `Energy = 450.0W`, `Size = 1.0m`, `Type = AREA`.
   - In `master_portrait_clean.png` and `audit_face_closeup.png`, the blinding white crescent reflection on the top of the skull dome has been completely eliminated.

---

## 2. Logic Chain

1. **Premise**: In Iteration 5, Reviewer 2 flagged:
   - Defect 1: Flat pink sticker mouth on body quads 377/378.
   - Defect 2: Bangs quad X-width collapsed to 2.25mm leaving 3.52mm empty barcode gaps (61% open).
   - Defect 3: Eyelids bulging without eyeliner distinction; dull grey marble eyes.
   - Defect 4: Glaring white crescent reflection on cranial apex under 750W rim light.
2. **Observation**:
   - In Iteration 6, worker successfully removed the pink sticker from body quads 377/378 (`slot_skin`).
   - Worker created `Mesh_Lips` (50 quads, 66 verts) to provide 3D anime lips, but positioned it at $Y \in [-0.1194\text{m}, -0.1169\text{m}]$ while the facial skin in that region is at $Y = -0.1238\text{m}$.
   - 52 of 66 vertices (78.8%) of `Mesh_Lips` are submerged inside the head by up to -6.47mm.
   - Furthermore, `character_assembler.py` called `materials.clear()` after setting face material indices, which clamped 100% of `Mesh_Lips` polygons to Slot 0 (`Mat_Human_Lips`), leaving 0 polygons on Slot 1 (`Mat_Human_Oral_Slit`).
   - The same `materials.clear()` bug wiped `Mesh_Eyelid_Left` and `Mesh_Eyelid_Right`, leaving 100% of eyelid quads on `Mat_Human_Eyeliner` and 0 quads on `Mat_Human_Skin_SSS`, encircling the lower eye with a black loop.
3. **Inference**:
   - A mouth mesh that is 78.8% submerged inside the head is non-functional and fails aesthetic character likeness. The character in `master_portrait_clean.png` and `audit_face_closeup.png` has no discernible mouth, only a broken, accidental pink smudge.
   - Claiming that `Mesh_Lips` displays a "dark oral fissure slit (`Mat_Human_Oral_Slit`)" and that `Mesh_Eyelid` displays a "flush lower cheek margin assigned `Mat_Human_Skin_SSS`" when both materials have **0 polygons assigned in the actual asset** represents an unverified defect / facade condition.
4. **Conclusion**:
   - While Defect 2 (Bangs vector math and coverage) and Defect 4 (Cranial apex glare elimination) are fully resolved and verified, Defects 1 and 3 remain broken due to geometry submersion and the `materials.clear()` index-erasure bug.
   - Therefore, the work product cannot be approved and requires changes.

---

## 3. Caveats

- **Mechanical Integrity**: Core Rigify metarig (163 DEF bones), ARKit FACS shape keys (52 keys), pure quad body topology (2,036 quads), wardrobe clearance (+6.48mm to +8.30mm, 0 penetrations), and magic props (strings and butterflies) remain solid and pass all unit tests.
- **Hair Bangs**: The hair bangs vector math and dense curtain coverage are thoroughly verified and completely clean.
- No other caveats.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

### Findings Breakdown:

#### [Critical] Finding 1: `Mesh_Lips` Submerged Inside Cranium (78.8% Penetration) & Zero Oral Slit Polygons
- **What**: 
  1. `Mesh_Lips` is submerged 6.5mm inside the body head mesh; 52 out of 66 vertices (78.8%) have negative normal offset (penetration) into `Yu_Nian_An_Body`, leaving only a mangled 1.68mm pink sliver peeking out as an accidental smudge in beauty renders.
  2. Exactly 0 polygons in `Mesh_Lips` are assigned to `Mat_Human_Oral_Slit` (100% assigned to Slot 0).
- **Where**: `src/morphomesh/character_assembler.py` (lines 500–590, lines 705–708) and `output/yu_nian_an/Yu_Nian_An_Master.blend`.
- **Why**: 
  1. `create_delicate_anime_lips_mesh` places lips at center $Y = -0.1165\text{m}$, while the body mesh mouth surface is at $Y = -0.1238\text{m}$.
  2. Calling `e_obj.data.materials.clear()` in Blender clears material slots and automatically resets all polygon `material_index` attributes to 0.
- **Remediation**:
  1. Offset `Mesh_Lips` center in $Y$ so that it sits flush and slightly proud of the body mesh surface: set `center_y = -0.1245 * s` (or compute local face surface Y) so that all 66 vertices have positive normal offset ($+0.3\text{mm} \le \text{offset} \le +1.5\text{mm}$, 0 penetrations).
  2. Assign materials to `e_obj` **BEFORE** running BMesh or populate slots without calling `materials.clear()` after setting face indices, ensuring polygons in row $r=2$ retain `material_index = 1` (`Mat_Human_Oral_Slit`).

#### [Major] Finding 2: Lower Eyelids Painted Black (Zero Skin SSS Polygons on Lower Rim)
- **What**: 100% of polygons in `Mesh_Eyelid_Left` and `Mesh_Eyelid_Right` are assigned to `Mat_Human_Eyeliner`; exactly 0 polygons are assigned to `Mat_Human_Skin_SSS`, creating a dark, harsh black eyeliner loop around the bottom of the eyes.
- **Where**: `src/morphomesh/character_assembler.py` (lines 643–644, lines 705–708) and `output/yu_nian_an/Yu_Nian_An_Master.blend`.
- **Why**: Calling `e_obj.data.materials.clear()` wiped out `face.material_index = 1` for the lower rim quads.
- **Remediation**:
  - Ensure `e_obj.data.materials` are assigned prior to or during mesh construction so that upper quads (`sin_mid >= -0.15`) have `material_index = 0` (`Mat_Human_Eyeliner`) and lower quads have `material_index = 1` (`Mat_Human_Skin_SSS`).

#### [Verified & Approved] Item 3: Forehead Bangs Coverage & Silhouette
- Bangs quad X-widths average 7.45mm (~7.5mm), adjacent ribbons overlap by 7.29mm with 0 barcode gaps, and lateral edges recede naturally along the temple profile.

#### [Verified & Approved] Item 4: Cranial Apex Glare Elimination & Silky Hair Sheen
- 73 scalp polygons assigned matte `Mat_Human_Scalp` (Roughness 0.70, Specular 0.25, Coat 0.0), hair BSDF tuned with Coat 0.08 and Anisotropic 0.70, rim light softened to 450W. White crescent reflection completely eliminated.

---

## 5. Verification Method

1. **Verify `Mesh_Lips` Submersion & Penetration**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background "E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend" --python-expr "
   import bpy; from mathutils.bvhtree import BVHTree
   body = bpy.data.objects['Yu_Nian_An_Body']; lips = bpy.data.objects['Mesh_Lips']
   bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
   pens = sum(1 for v in lips.data.vertices if (lips.matrix_world @ v.co - bvh.find_nearest(lips.matrix_world @ v.co)[0]).dot(bvh.find_nearest(lips.matrix_world @ v.co)[1]) < -0.0001)
   print(f'Penetrating lip verts: {pens} / {len(lips.data.vertices)} ({pens/len(lips.data.vertices)*100:.1f}%)')
   "
   ```
   *Expected Result*: Proves 52 / 66 vertices (78.8%) are penetrating inside the head mesh.

2. **Verify `materials.clear()` Index Reset Bug on Lips & Eyelids**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background "E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend" --python-expr "
   import bpy
   for name in ['Mesh_Lips', 'Mesh_Eyelid_Left', 'Mesh_Eyelid_Right']:
       m = bpy.data.objects[name].data
       dist = {}
       for p in m.polygons: dist[p.material_index] = dist.get(p.material_index, 0) + 1
       print(name, 'materials:', [mat.name for mat in m.materials], 'poly dist:', dist)
   "
   ```
   *Expected Result*: Proves `Mesh_Lips` has `{0: 50}` (0 polygons for `Mat_Human_Oral_Slit`), and `Mesh_Eyelid` has `{0: 16}` (0 polygons for `Mat_Human_Skin_SSS`).

3. **Visual Inspection**:
   Inspect `E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter6_2\audit_face_closeup.png` and `output/yu_nian_an/master_portrait_clean.png`.

4. **Invalidation Condition**:
   This verdict is invalidated only when:
   - `Mesh_Lips` is positioned outside `Yu_Nian_An_Body` (0 penetrating vertices, positive surface clearance) and properly displays a defined cupid's bow, dark oral fissure slit (`Mat_Human_Oral_Slit` on row 2), and soft rose lower vermilion in beauty renders.
   - `Mesh_Eyelid_Left/Right` correctly retains `Mat_Human_Skin_SSS` on its lower rim polygons.
