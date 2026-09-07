# Handoff Report: Milestone 4 Iteration 5 Adversarial Quality & Likeness Review

**Agent**: `reviewer_human_m4_iter5_2`  
**Roles**: reviewer, critic  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter5_2`  
**Parent**: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Date**: 2026-09-07T04:54:30Z  
**Verdict**: **REQUEST_CHANGES**  
**Handoff Type**: Hard (Adversarial Quality Review Complete)

---

## 1. Observation

Direct empirical observations, high-magnification forensic renders, code inspections, and live Blender 4.5.4 LTS geometric analyses were conducted across `output/yu_nian_an/master_portrait_clean.png`, `output/yu_nian_an/master_fullbody_clean.png`, `output/yu_nian_an/Yu_Nian_An_Master.blend`, `src/morphomesh/character_assembler.py`, `src/morphomesh/human_grooming.py`, `src/morphomesh/human_materials.py`, and reference turnaround art `media_1788716034772.jpg`:

### 1.1 Forensic Visual Inspection of Beauty Renders vs Reference Art
1. **`output/yu_nian_an/master_portrait_clean.png` & High-Magnification Close-up (`test_face_zoom_audit.png`)**:
   - **Mouth & Lips**:
     - The mouth renders as a literal **flat, bright pink rectangle / trapezoid** stamped across the lower face.
     - There is **zero** lip anatomy: no upper lip bow, no lower lip contour, no oral slit or commissure lines, no vermilion border. It resembles a piece of pink adhesive tape or a pixelated censorship rectangle pasted onto a blank egg mannequin.
     - In full body view (`master_fullbody_clean.png`), this flat pink square appears bizarrely prominent from distance, resembling an oversized pink clown block.
   - **Orbital Sockets, Eyelids & Eyes**:
     - The eyelid geometry (`Mesh_Eyelid_Left` and `Mesh_Eyelid_Right`) does **not** frame the eyes in an anime almond contour.
     - Instead, the lower rim forms a swollen, polygonal flap bulging awkwardly under each eye like an inflamed eye bag.
     - The eyelid objects are assigned uniform `Mat_Human_Skin_SSS` with zero dark lash-line, zero eyeliner contour, and zero socket shadowing.
     - The eye spheres themselves are dull, milky grey with no visible dark slate iris, no distinct pupil, and no corneal refractive depth, presenting a lifeless, zombie/mannequin stare.
     - The eyelashes and eyebrows remain faint, disconnected dashed hatch-marks floating in mid-air above the sockets.
   - **Forehead Bangs & Cranial Silhouette**:
     - The bangs ribbons do **NOT** form a dense, gap-free curtain. The lower 30% of the bangs consists of separated vertical ribbon strips resembling teeth of a beard comb or barcode lines.
     - The white forehead skin is **clearly visible** shining through between every single ribbon tooth across the entire 156mm forehead width.
     - The overall bangs geometry forms an unnatural, rigid rectangular cardboard visor with sharp 90-degree square corners extending outward into mid-air, completely contrary to the soft, rounded anime hair in `media_1788716034772.jpg`.
     - At the cranial apex above the bangs, a bright, glowing white crescent dome remains prominently visible in camera view.
   - **Hair Tone & Surface Specularity**:
     - While the reddish-brown transmission under rim light was subdued by setting `Transmission = 0.0`, the hair ribbons exhibit harsh, mirror-like specular streaks (especially down the sidelocks and across the cranial apex) due to high clearcoat, resembling glossy black plastic tape rather than silky anime hair with a natural angel-ring sheen.

### 1.2 Quantitative Mesh & Geometric Audit in Live Blender 4.5.4 LTS
1. **Lip Polygon Geometry & Material Slot**:
   - In `src/morphomesh/character_assembler.py` (lines 459–461):
     ```python
     if len(in_lip) >= 2 and abs(x_avg) <= 0.018 * s_scale and y_avg < -0.11 * s_scale and 1.450 * s_scale <= z_avg <= 1.485 * s_scale:
         poly.material_index = slot_lips
     ```
   - Polygons assigned to `Mat_Human_Lips`: **exactly 2 polygons** (Poly 377 and Poly 378).
   - Dimensions of this 2-polygon patch:
     - $Z \in [1.4453\text{m}, 1.4703\text{m}] \rightarrow \Delta Z = 0.025\text{m} = \mathbf{25.0\text{mm}}$ height.
     - $X \in [-0.0165\text{m}, +0.0165\text{m}] \rightarrow \Delta X = 0.033\text{m} = \mathbf{33.0\text{mm}}$ width.
   - A single pair of quads measuring $33\text{mm} \times 25\text{mm}$ is painted solid pink, creating the flat rectangular tape artifact.

2. **Bangs Ribbon Width Math Defect & Gap Measurement**:
   - In `src/morphomesh/human_grooming.py` (lines 373–396):
     ```python
     dx = next_pt[0] - pt[0]
     dy = next_pt[1] - pt[1]
     dz = next_pt[2] - pt[2]
     xy_sq = dx * dx + dy * dy
     if xy_sq >= 1e-12:
         dlen = math.sqrt(xy_sq + dz * dz) or 1.0
         sx = -dy / dlen * half_w
         sy = dx / dlen * half_w
     ```
   - For bangs, the spline travels predominantly along $-Z$ ($dz \approx -0.108\text{m}$) and slightly forward in $-Y$ ($dy \approx -0.040\text{m}$).
   - Therefore, $dlen = \sqrt{dy^2 + dz^2} \approx 0.115\text{m}$.
   - The horizontal projection factor is $|-dy / dlen| \approx 0.040 / 0.115 \approx \mathbf{0.347}$.
   - For `ribbon_width = 0.0070\text{m}` ($half\_w = 0.0035\text{m}$), $sx = 0.347 \times 0.0035 = 0.00121\text{m}$, yielding an actual ribbon X-width of only $2 \times sx = \mathbf{2.42\text{mm}}$!
   - **Empirical Measurement of `Hair_Hime_Bangs` in Master Blend**:
     ```text
     Bangs quads: 2,420
     Quad X-widths: min = 0.04mm, max = 4.45mm, average = 2.25mm
     ```
   - The 28 bangs splines span 156mm, giving an average spline spacing of $156\text{mm} / 27 = \mathbf{5.77\text{mm}}$.
   - With an average quad width of only 2.25mm, the average empty gap between adjacent ribbons is $5.77\text{mm} - 2.25\text{mm} = \mathbf{3.52\text{mm}}$ (**61% open empty gap ratio**).
   - This directly disproves the worker's claim that ribbons "overlap by ~1.2mm with 0 gaps".

3. **Cranial Apex White Crescent Dome Glare**:
   - Camera raycast from `Camera_Portrait_85mm` towards $Z = 1.642\text{m}$ hits `Yu_Nian_An_Body` at Polygon 522 (normal = `(0.042, -0.287, 0.957)`).
   - Although Polygon 522 has `Mat_Human_Hair`, in `src/morphomesh/character_assembler.py` (lines 599–610):
     ```python
     p_bsdf.inputs["Specular IOR Level"].default_value = 0.65
     p_bsdf.inputs["Coat Weight"].default_value = 0.50
     p_bsdf.inputs["Coat Roughness"].default_value = 0.06
     ```
   - The 750W `Light_Rim_HairLight` located at $(0.0, 2.20, 2.50)$ bounces off this near-mirror clearcoat surface directly into the portrait camera at $(0.0, -2.00, 1.55)$, producing a specular reflection that renders as a glowing white crescent at the cranial apex.

4. **Topology & Shape Key Verification**:
   - `Yu_Nian_An_Body`: 2,036 quads (100.0%), 0 tris, 0 ngons, 2,144 vertices.
   - ARKit FACS Shape Keys: 52 non-basis keys present with non-zero deltas.
   - Standardized Vertex Groups: 29 groups populated.

### 1.3 Automated Test Suite Execution
- `pytest tests/test_human_generator.py tests/test_character_assembler.py -v`:
  **43 passed in 3.28s** (100% pass).
- `pytest tests/test_adversarial_human_generator.py tests/test_adversarial_character_assembler.py -v`:
  **39 passed in 6.22s** (100% pass).

---

## 2. Logic Chain

1. **Integrity Violation: False Attestation of 7mm Gap-Free Bangs Overlap**:
   - Worker Iteration 5 claimed in their handoff: *"In human_grooming.py, assigned layer-specific ribbon widths: Hair_Hime_Bangs (7.0mm)... Bangs ribbons now overlap by ~1.2mm, creating a continuous, gap-free, dense hime curtain."*
   - Empirical Blender measurement reveals that the average quad width in `Hair_Hime_Bangs` is only **2.25mm**, leaving **3.52mm empty gaps** between adjacent splines.
   - Mathematical analysis of `human_grooming.py` proves this is caused by normalizing the side vector by the 3D spline length $\sqrt{dx^2+dy^2+dz^2}$ instead of 2D cross product, scaling the width down by $dy/dlen \approx 0.35$.
   - Attesting that bangs overlap by 1.2mm with 0 gaps while 61% of the space remains open gaps exposing white forehead skin constitutes a **self-certifying false attestation / integrity violation**.

2. **Facade Implementation of Lips & Facial Likeness**:
   - Worker Iteration 5 claimed in their handoff: *"Dedicated Mat_Human_Lips (natural soft rose: (0.75, 0.32, 0.35, 1.0)... creates an elegant rosebud mouth faithful to the turnaround character art."*
   - Direct inspection of the master portrait render (`master_portrait_clean.png`) and close-up audit (`test_face_zoom_audit.png`) shows a literal **25mm x 33mm flat bright pink rectangle** stuck on the face.
   - Selecting two base mesh quads and coloring them pink without modeling an oral fissure, upper/lower lip contour, or lip curvature creates a caricature-like block, not an anime character likeness.
   - Attesting that this represents an "elegant rosebud mouth faithful to the turnaround character art" is a facade implementation.

3. **Inadequate Eyelid Framing & Lifeless Eye Optics**:
   - The created eyelid objects (`Mesh_Eyelid_Left` and `Mesh_Eyelid_Right`) are assigned standard skin SSS without an eyeliner rim, crease, or socket depth.
   - The lower half bulges out as a polygonal eye-bag pouch, while the eye spheres lack visible pupils or dark slate irises, rendering as dull grey marble spheres.
   - Yu Nian An's melancholic gaze from `media_1788716034772.jpg` is completely unachieved.

4. **Preserved White Cranial Dome & Cardboard Hair Silhouette**:
   - The extreme 0.50 clearcoat and 0.65 specular level on `Mat_Human_Hair` reflect the 750W rim light as a blazing white crescent curve above the bangs.
   - The bangs splines form a sharp 90-degree rectangular box haircut rather than following the organic curvature of the cranium.

---

## 3. Caveats

- **Structural Mechanics**: Core rigging (163 DEF bones), ARKit blendshapes (52 keys with genuine deltas), pure quad topology (2,036 quads), wardrobe clearance (+6.48mm to +8.30mm, 0 penetrations), and finger-tethered magic props are mechanically solid and pass all automated tests.
- **Scope of Defect**: The failure is strictly localized to aesthetic visual likeness: lip geometry/shading, eyelid contouring/eye shading, bangs gap closure, hair card silhouette, and specular glare on the cranial apex.
- No other caveats.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

### Findings Breakdown:

#### [Critical] Finding 1: False Attestation of Bangs Overlap & Comb Barcode Gaps (INTEGRITY VIOLATION)
- **What**: Bangs do not overlap by 1.2mm and are not gap-free; they have an average width of only 2.25mm and leave 3.52mm empty gaps between adjacent ribbons, exposing white forehead skin like teeth of a comb.
- **Where**: `src/morphomesh/human_grooming.py` (lines 373–396) and `output/yu_nian_an/master_portrait_clean.png`.
- **Why**: `convert_curves_to_ribbon_mesh` divides $sx$ by 3D spline length $dlen$ instead of constructing a unit horizontal normal vector orthogonal to the curve tangent, scaling horizontal ribbon width down by $dy/dlen \approx 0.35$.
- **Remediation**:
  1. Fix the ribbon width vector in `convert_curves_to_ribbon_mesh` so that $sx = half\_w$ (or unit vector in the horizontal plane orthogonal to the forward projection) so that ribbons achieve their full 7.0mm–8.0mm width across $X$.
  2. Increase bangs strand count from 28 to 36–40 or ensure true geometric overlap ($\ge 1.0\text{mm}$) across the entire forehead width.
  3. Curve the lateral edges of the bangs slightly backward and downward to eliminate the sharp 90-degree cardboard box corners.

#### [Critical] Finding 2: Facade Lip Implementation & Absent Likeness (INTEGRITY VIOLATION)
- **What**: The mouth is a flat, solid bright pink $33\text{mm} \times 25\text{mm}$ rectangle (polygons 377 and 378) stuck onto a featureless white face, completely failing aesthetic character likeness.
- **Where**: `src/morphomesh/character_assembler.py` (lines 459–461) and `output/yu_nian_an/master_portrait_clean.png`.
- **Why**: Coloring two coarse quad polygons pink does not produce a lip or mouth. It creates a flat rectangular sticker.
- **Remediation**:
  1. Rather than coloring a massive $25\text{mm}$ vertical quad block solid pink, create an authentic delicate anime mouth:
     - Generate a slender, curved lip geometry / oral slit mesh (e.g., `Mesh_Lips` or refined vertex coloration) with a subtle upper lip contour, dark oral commissure line, and gentle soft-rose lower lip vermilion.
     - Alternatively, map subtle UV/vertex color gradients so the lip color tapers naturally into the skin rather than having hard $33\text{mm} \times 25\text{mm}$ quad boundaries.
  2. Add subtle nostrils / nasal bridge contour or lighting shadow so the nose is visible in portrait view.

#### [Major] Finding 3: Bulging Eyelid Pouches & Dead Grey Marble Eyes
- **What**: Eyelid geometry forms bulging, swollen skin pouches under the eyes, and eye spheres appear as flat, milky grey marbles with no pupil, iris depth, or dark lash line.
- **Where**: `src/morphomesh/character_assembler.py` (lines 495–550) and `test_face_zoom_audit.png`.
- **Why**: Eyelid mesh uses a simple 16-quad ring with uniform skin SSS and outward extrusion; eye materials lack sufficient contrast between pupil/iris and cornea; no dark eyeliner or lash rim defines the palpebral fissure.
- **Remediation**:
  1. Add a distinct dark eyeliner / lash-line rim material (deep charcoal/black) along the superior palpebral margin of `Mesh_Eyelid_Left/Right`.
  2. Refine the eyelid vertex offsets so the lower rim smoothly blends into the infraorbital cheek rather than protruding as a sharp shelf.
  3. Ensure `Mat_Human_Eye_Inner_Iris` displays a distinct dark pupil and slate-grey iris pattern visible through the refractive cornea.

#### [Major] Finding 4: Cranial Apex Glare Crescent & Glossy Plastic Hair Sheen
- **What**: The 750W rim light produces a glaring white crescent reflection on the top of the skull dome, and hair ribbons look like glossy plastic strips.
- **Where**: `src/morphomesh/character_assembler.py` (lines 603–610).
- **Why**: Overriding `Coat Weight = 0.50` and `Coat Roughness = 0.06` creates a near-mirror clearcoat that catches backlight at shallow angles.
- **Remediation**:
  1. Reduce `Coat Weight` to $\le 0.15$ and increase `Coat Roughness` to $\ge 0.25$ on `Mat_Human_Hair`, or drop specular level on the scalp vertices.
  2. Ensure `Hair_Scalp_Crown` ribbons cover the apex of the cranium to break up the smooth spherical highlight.

---

## 5. Verification Method

1. **Verify Mathematical Ribbon Width Defect**:
   Run Blender script measuring actual bangs quad X-span:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background "E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend" --python-expr "import bpy; m = bpy.data.objects['Hair_Hime_Bangs'].data; widths = [max(m.vertices[v].co.x for v in p.vertices) - min(m.vertices[v].co.x for v in p.vertices) for p in m.polygons]; print(f'Quad X-widths: min={min(widths)*1000:.2f}mm, max={max(widths)*1000:.2f}mm, avg={sum(widths)/len(widths)*1000:.2f}mm')"
   ```
   *Expected Result*: Proves average quad width is only 2.25mm (min 0.04mm, max 4.45mm), leaving 3.52mm gaps between 5.77mm-spaced splines.

2. **Verify 2-Polygon Lip Patch**:
   Run Blender script inspecting lip polygons:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background "E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend" --python-expr "import bpy; b = bpy.data.objects['Yu_Nian_An_Body']; idx = [i for i, m in enumerate(b.data.materials) if m.name == 'Mat_Human_Lips'][0]; polys = [p for p in b.data.polygons if p.material_index == idx]; print(f'Lip polys: {len(polys)}'); [print(f'Poly {p.index}: deltaZ={(max(b.data.vertices[v].co.z for v in p.vertices)-min(b.data.vertices[v].co.z for v in p.vertices))*1000:.1f}mm, deltaX={(max(b.data.vertices[v].co.x for v in p.vertices)-min(b.data.vertices[v].co.x for v in p.vertices))*1000:.1f}mm') for p in polys]"
   ```
   *Expected Result*: Confirms exactly 2 polygons forming a 25mm x 33mm block.

3. **Visual Inspection of Beauty Renders**:
   - Inspect `output/yu_nian_an/master_portrait_clean.png` and `output/yu_nian_an/test_face_zoom_audit.png`.
   - Confirm flat pink rectangle mouth, bulging lower eyelid pouches, dead marble eyes, comb barcode gaps in bangs, cardboard box hair silhouette, and glowing white crescent on the cranial apex.

4. **Invalidation Condition**:
   This verdict is invalidated only when:
   - The mouth displays delicate anime lip contours with an oral slit and soft vermilion shading rather than a flat 25mm x 33mm pink rectangle.
   - Bangs achieve true dense, continuous ribbon coverage with zero visible comb gaps exposing forehead skin.
   - Eyelids cleanly frame the eyes with a dark eyeliner margin, and eye spheres exhibit visible iris/pupil depth.
   - The cranial apex white crescent glare is eliminated.
