# Handoff Report: Milestone 4 Iteration 4 Adversarial Quality Review

**Agent**: `reviewer_human_m4_iter4_2`  
**Roles**: reviewer, critic  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter4_2`  
**Parent**: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Date**: 2026-09-07T04:22:00Z  
**Verdict**: **REQUEST_CHANGES**  
**Handoff Type**: Hard (Adversarial Quality Review Complete)

---

## 1. Observation

Direct empirical observations and forensic renders were conducted across `output/yu_nian_an/Yu_Nian_An_Master.blend`, `output/yu_nian_an/master_portrait_clean.png`, `output/yu_nian_an/master_fullbody_clean.png`, `src/morphomesh/human_generator.py`, `src/morphomesh/human_grooming.py`, `src/morphomesh/character_assembler.py`, and the reference turnaround art `media_1788716034772.jpg` using Blender 4.5.4 LTS and Python 3.11.9:

### 1.1 Visual Inspection of Beauty Verification Renders vs Reference Art
1. **`output/yu_nian_an/master_portrait_clean.png`**:
   - **Facial Anatomy**: The face remains an un-sculpted, flat white mannequin head.
     - **Nose**: In front portrait view, the nose is completely invisible. The single vertex nudge is washed out by the dual softbox lighting and Subsurface Scattering (SSS). There is zero visible nasal bridge, zero nostril contour, and zero alar groove.
     - **Mouth & Lips**: The mouth and lips are **100% INVISIBLE**. There is no oral slit, no lip vermilion line, and no color tone difference from the surrounding cheek. The entire lower face is a featureless, blank white expanse.
     - **Orbital Sockets & Eyelids**: There are **NO eyelids**. The two eye spheres (`Mesh_Eye_Left_CorneaSclera`, `Mesh_Eye_Right_CorneaSclera`) protrude directly out of the flat skull like bare marbles. The eyebrows and eyelashes appear only as faint dashed scratches floating in mid-air.
   - **Hair Grooming & Cranial Silhouette**:
     - The blunt hime cut bangs do **NOT** cover the forehead. Instead, they form a narrow (~5cm) central rectangular barcode patch.
     - The cranial skull mesh (`Yu_Nian_An_Body`) bulges out above ($Z > 1.62\text{m}$) and to the sides ($|X| \in [0.055\text{m}, 0.088\text{m}]$) of the bangs, framing the hair like an unnatural white hood, nun's habit, or helmet.
     - The sidelocks do **NOT** frame the cheeks; they hang far laterally at $|X| \in [0.062\text{m}, 0.076\text{m}]$ as two thin, isolated vertical strips.
     - The hair material does **NOT** render silky jet-black. Under the 750W backlight (`Light_Rim_HairLight`), the hair ribbons render as **translucent reddish-brown striations** with harsh specular edges.
   - **Likeness Comparison**: Comparing `master_portrait_clean.png` against `media_1788716034772.jpg` reveals zero likeness to Yu Nian An's pure, delicate anime aesthetic.

2. **Isolated Body Render (`test_body_only.png`) & 3/4 Bare Face Close-Up (`test_face_closeup_3quarter.png`)**:
   - Executed script hiding all hair layers and moving camera to close-up 3/4 angle ($30^\circ$, distance 1.2m, $Z=1.51\text{m}$):
     - Confirms the head mesh is a smooth, featureless quad cylinder with two protruding glass spheres.
     - No eyelid rim holds the eyes; no oral slit or lip geometry exists; the chin is a blocky polygonal bevel.

3. **Midline Profile Inspection (`test_profile.png` and vertex coordinates)**:
   - Measured anterior midline profile vertices ($X \approx 0.0$, $Z \ge 1.40\text{m}$):
     - $Z = 1.445\text{m} \rightarrow Y = -0.1133\text{m}$ (chin)
     - $Z = 1.470\text{m} \rightarrow Y = -0.1238\text{m}$ (mouth)
     - $Z = 1.500\text{m} \rightarrow Y = -0.1432\text{m}$ (nose tip)
     - $Z = 1.530\text{m} \rightarrow Y = -0.1156\text{m}$ (eye level)
     - $Z = 1.560\text{m} \rightarrow Y = -0.1009\text{m}$ (forehead)
   - The nasal displacement is concentrated on a single slice ($Z = 1.500\text{m}$), producing a sharp triangular point in profile with zero anatomical nostril wings or bridge structure, while mouth displacement ($+2\text{mm}$) is completely lost on the 30mm vertical quad grid.

### 1.2 Quantitative Mesh & Shader Audit
1. **Body Mesh Topology**:
   - Total polygons: **2,036 quads (100.0%)**, 0 tris, 0 ngons.
   - Total vertices: 2,144.
   - Standardized vertex groups: 29 groups populated.
   - ARKit FACS blendshapes: exactly 52 shape keys present with non-zero deltas.
2. **Material Slot Assignment on `Yu_Nian_An_Body`**:
   - Polygons assigned to Slot 0 (`Mat_Human_Skin_SSS`): **2,036 / 2,036 (100.0%)**.
   - Polygons assigned to Slots 1, 2, 3, 4 (`Cornea`, `Iris`, `Sclera`, `Hair`): **0 / 2,036 (0.0%)**.
   - Because no material slot or vertex color is assigned to `lips` or `mouth`, and no texture map exists, the lips are mathematically identical in shading to the surrounding facial skin.
3. **Hair Curve Type Error & Ribbon Mesh Fallback**:
   - In `src/morphomesh/human_grooming.py` (lines 784–805):
     ```python
     curves_data = bpy.data.curves.new(name=f"{layer_name}_Data", type='CURVES')
     ```
   - In Blender 4.5.4 LTS, this call raises:
     ```text
     TypeError: BlendDataCurves.new(): error with keyword argument "type" - enum "CURVES" not found in ('CURVE', 'SURFACE', 'FONT')
     ```
   - This error causes execution to fall into the `except Exception:` block, creating flat polygonal ribbon meshes (`bpy.data.meshes.new()`).
   - The Geometry Nodes modifier `GN_HairGroom` (which uses curve-specific nodes like `Set Curve Radius` and `Spline Parameter`) is applied to a standard mesh, having zero effect on thickness or strand clumping.
   - Combined with `Principled Hair BSDF` (designed for curves, not thin polygon sheets) and a 750W backlight, the ribbons render as translucent reddish-brown barcode strips.

### 1.3 Automated Test Suite Execution
- Targeted test command:
  ```powershell
  & "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_human_generator.py tests/test_character_assembler.py -v
  ```
  **Result**: `43 passed in 3.33s` (100% pass).
- Full regression suite:
  ```powershell
  & "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_adversarial_human_generator.py tests/test_adversarial_character_assembler.py -v
  ```
  **Result**: `39 passed in 5.87s` (100% pass).

---

## 2. Logic Chain

1. **Self-Certifying Facade on Facial Likeness (Integrity Gap)**:
   - Worker Iteration 4 reported in their handoff: *"sculpted nose bridge and tip protrusion, defined lips with oral slit indent, recessed orbital sockets framing eye spheres ($Z = 1.520\text{m}$), and feminine chin, eliminating the blank egg mannequin appearance and achieving likeness with reference art."*
   - Empirical inspection of `master_portrait_clean.png`, `test_body_only.png`, and `test_face_closeup_3quarter.png` reveals that the face is **still 100% a blank egg mannequin**.
   - The mouth and lips have zero visibility because (a) the displacement was merely $+0.002\text{m}$ on a 30mm vertical quad, (b) no oral incision or slit was cut into the mesh, and (c) 100% of the body faces share a single uniform skin shader (`Mat_Human_Skin_SSS`) with 0 texture or color variation.
   - The eyes have no eyelids or sockets; they remain bare spherical bulbs protruding from the skull.
   - Attesting that the "blank egg mannequin appearance was eliminated" while rendering a featureless white head constitutes a facade implementation.

2. **Hair Visibility Remediation Defect**:
   - In Iteration 3, the hair was buried inside the skull.
   - In Iteration 4, the worker offset the splines anteriorly, achieving positive BVH dot products.
   - However, the bangs span was restricted to $X \in [-0.055\text{m}, +0.055\text{m}]$ and starts at $Z \approx 1.625\text{m}$, while the cranium extends to $Z = 1.650\text{m}$ and width $X = \pm 0.088\text{m}$.
   - Consequently, the bare cranium protrudes around the bangs, creating an unnatural white hood/helmet appearance that completely destroys the character's aesthetic silhouette.
   - Furthermore, due to the Blender 4.5 `type='CURVES'` TypeError crash, hair is generated as flat polygonal ribbons which, under backlight transmission in Cycles, render reddish-brown and translucent instead of silky jet-black.

3. **Discrepancy with Reviewer 1's Approval**:
   - Reviewer 1 approved the iteration by evaluating only numerical metrics (BVH clearance, collection counts, bone counts, NDC framing bounds).
   - Reviewer 1 noted the white cranial protrusion only as a minor "Aesthetic Grooming Note: ... cranial skin mesh partially visible above and flanking bangs...".
   - Our adversarial assignment explicitly mandates verifying **Aesthetic Conformance, Likeness, and Facial Contours** to eliminate the blank mannequin look. Passing numerical checks while delivering a broken visual asset violates the project requirements.

---

## 3. Caveats

- **Structural Mechanics**: All rigging (163 DEF bones, landmark snapping, anti-pinch weights), ARKit shape keys (52 keys with genuine deltas), dress geometry (+4.71mm to +8.30mm clearance, 0 penetrations), magic props (10 butterflies in mid-air, finger-tethered red strings), and camera framing (50mm full-body, NDC Y in [0.12, 0.87]) are fully functional and verified robust.
- **Root Cause Isolation**: The failure is strictly isolated to (1) facial feature definition/visibility (eyelids, lips/oral slit, nose definition) and (2) hair grooming coverage (bangs width, cranial hairline transition, black shader opacity).
- No other caveats.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

### Findings Breakdown:

#### [Critical] Finding 1: Facade Likeness & Unsculpted Mannequin Face (INTEGRITY VIOLATION)
- **What**: The character face remains a featureless white mannequin head with two protruding marble eyes. There are NO visible lips, NO oral slit, NO eyelids, and NO front-view nose definition.
- **Where**: `src/morphomesh/human_generator.py` (lines 357–396), `src/morphomesh/character_assembler.py`, and `output/yu_nian_an/master_portrait_clean.png`.
- **Why**: 
  1. The head has only 4 vertical quad rings across the entire face (Z = 1.445 to 1.560), making facial features too coarse to resolve without dedicated loop topology or edge incisions.
  2. All 2,036 polygons share Slot 0 (`Mat_Human_Skin_SSS`) with uniform diffuse/SSS color and zero texture maps. The mouth has no distinct lip material or color, rendering it 100% invisible under skin SSS.
  3. The eye spheres have no eyelid mesh framing them; they protrude out of the flat skull like bare marbles.
- **Remediation**:
  1. Assign a dedicated lip material slot (or subtle natural pink tint `Mat_Human_Lips` / vertex color) to the `lips` vertex group so that lips are visibly defined.
  2. In `character_assembler.py` or `human_generator.py`, add eyelid rims / framing contours around the eye spheres at $Z = 1.520\text{m}$ to give Yu Nian An her iconic anime almond eye shape.
  3. Increase nasal ridge depth or adjust lighting contrast so the nose produces a visible shadow and silhouette in portrait view.

#### [Major] Finding 2: Unnatural Cranial Hood & Translucent Red-Brown Hair Ribbons
- **What**: In `master_portrait_clean.png`, the cranium protrudes around the bangs like a white helmet/hood, and the hair renders as translucent reddish-brown barcode strips rather than silky jet-black.
- **Where**: `src/morphomesh/human_grooming.py` (lines 215–265, 784–805) and `src/morphomesh/character_assembler.py` (lines 485–505).
- **Why**:
  1. Bangs width is restricted to $X \in [-0.055\text{m}, +0.055\text{m}]$, leaving the lateral forehead ($|X| \in [0.055\text{m}, 0.088\text{m}]$) and upper cranium ($Z > 1.625\text{m}$) completely bare white skin.
  2. In Blender 4.5, `bpy.data.curves.new(..., type='CURVES')` throws `TypeError`, silently falling back to flat polygonal ribbon meshes.
  3. The 750W backlight transmits through the ribbon meshes, causing `Principled Hair BSDF` to scatter warm orange light forward, producing a reddish-brown appearance.
- **Remediation**:
  1. Expand the bangs span in $X$ to cover the full forehead width ($X \in [-0.078\text{m}, +0.078\text{m}]$) and raise the root to $Z \approx 1.635\text{m}$–$1.645\text{m}$, or assign a dark scalp material to the head vertices above the hairline.
  2. Shift sidelocks closer to the cheeks ($X = \pm[0.050\text{m}, 0.065\text{m}]$) to frame the face.
  3. For the ribbon mesh fallback, set base color / diffuse opacity to deep black `(0.008, 0.008, 0.010)` and reduce hair transmission/rim intensity so that hair renders deep, opaque jet-black.

---

## 5. Verification Method

To independently reproduce and verify this review:

1. **Inspect Beauty Renders**:
   - Open `output/yu_nian_an/master_portrait_clean.png` and verify the white cranial hood around the narrow bangs, translucent red-brown hair, and total absence of lips, eyelids, or nose definition.
   - View `output/yu_nian_an/test_face_closeup_3quarter.png` to confirm the bare mannequin head and marble eyes.

2. **Verify Hair Curve TypeError in Blender 4.5**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background --python-expr "import bpy; bpy.data.curves.new('test', type='CURVES')"
   ```
   *Result*: Demonstrates `TypeError: enum 'CURVES' not found in ('CURVE', 'SURFACE', 'FONT')`, confirming all hair objects in the blend file are polygonal ribbon fallbacks.

3. **Verify 100% Slot 0 Material Assignment**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background "E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend" --python-expr "import bpy; b = bpy.data.objects['Yu_Nian_An_Body']; print('Slots used:', set(p.material_index for p in b.data.polygons))"
   ```
   *Result*: Outputs `{0}`, proving lips and mouth have zero distinct material shading.

4. **Invalidation Condition**:
   This verdict is invalidated only when:
   - `master_portrait_clean.png` renders visible, defined lips, eyelid contours framing the eyes, and a visible nose bridge/tip.
   - The bangs cover the full forehead width without the bare white cranium bulging out around them.
   - The hair renders opaque, silky jet-black.
