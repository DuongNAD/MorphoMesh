# Handoff Report: Milestone 4 Iteration 3 Adversarial Quality Review

**Agent**: `reviewer_human_m4_iter3_2`  
**Roles**: reviewer, critic  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\reviewer_human_m4_iter3_2`  
**Parent**: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Date**: 2026-09-07T03:52:00Z  
**Verdict**: **REQUEST_CHANGES**  
**Handoff Type**: Hard (Adversarial Quality Review Complete)

---

## 1. Observation

Direct empirical observations conducted in `output/yu_nian_an/Yu_Nian_An_Master.blend`, `output/yu_nian_an/master_fullbody_clean.png`, `output/yu_nian_an/master_portrait_clean.png`, `src/morphomesh/human_grooming.py`, `src/morphomesh/human_generator.py`, and reference artwork `media_1788716034772.jpg` using Blender 4.5.4 LTS and Python 3.11:

### 1.1 Visual Inspection of Beauty Verification Renders
- In `output/yu_nian_an/master_fullbody_clean.png`:
  - Camera: `Camera_FullBody` (50.0mm focal length, location `[0.0, -5.5, 0.825]`).
  - Full-body framing: Top margin is ~12.8% (137 px), bottom margin is ~11.7% (125 px).
  - Character vertices map to $\text{NDC } Y \in [0.1171, 0.8717]$. Head, sash, skirt, and sandals are fully visible with zero cropping across all 5 turnaround cameras.
  - Framing criteria: **PASS**.
- In `output/yu_nian_an/master_portrait_clean.png`:
  - **Head & Facial Anatomy**: The face is rendered as a completely flat, featureless, smooth white egg/balloon. There is **NO nose**, **NO mouth**, **NO lips**, **NO chin contour**, and **NO eye sockets**.
  - **Eyes & Melancholic Gaze**: The eyes appear as two stark, unblinking black button spheres with two tiny white specular dots, resting flat on the cranial surface with zero eyelids, zero double-eyelid crease, zero visible sclera, and zero eyelashes. It completely fails the tranquil, melancholic gaze portrayed in `media_1788716034772.jpg`.
  - **Hime Cut Bangs & Hair Grooming**: The head is rendered virtually **BALD**. Only a faint, rectangular patch of thin vertical scratch lines is visible on the upper forehead. There are no flowing hime bangs, no sidelocks framing the face, no crown volume, and no eyebrows or eyelashes visible.
  - Visual aesthetics & portrait render criteria: **CRITICAL FAILURE**.

### 1.2 Quantitative Audit of Hair Occlusion & Burial inside Cranium Mesh
Executed an independent BVH containment and raycast audit from `Camera_Portrait_85mm` to the evaluated hair strata in Blender 4.5.4 LTS:
```python
# Raycast and BVH normal-dot containment test against Yu_Nian_An_Body
Hair_Eyebrows:      Total verts: 100  | Inside cranium: 100/100 (100.0%) | Camera Occluded: 100/100 (100.0%)
Hair_Eyelashes:     Total verts: 100  | Inside cranium: 100/100 (100.0%) | Camera Occluded: 100/100 (100.0%)
Hair_Scalp_Crown:   Total verts: 640  | Inside cranium: 582/640 (90.9%)  | Camera Occluded: 587/640 (91.7%)
Hair_Hime_Sidelocks:Total verts: 2976 | Inside cranium: 1918/2976 (64.4%)| Camera Occluded: 1966/2976 (66.1%)
Hair_Hime_Bangs:    Total verts: 2640 | Inside cranium: 1427/2640 (54.1%)| Camera Occluded: 1340/2640 (50.8%)
Hair_Back_Cascade:  Total verts: 7320 | Inside cranium: 1953/7320 (26.7%)| Camera Occluded: 6888/7320 (94.1%)
```
- Root Cause in `src/morphomesh/human_grooming.py`:
  - In `generate_hime_cut_splines()`:
    - Bangs: `y0 = (-0.065 - 0.015 * math.cos((u - 0.5) * math.pi)) * s` with curve extending forward to `Y = -0.092m`.
    - Eyebrows: `y0 = (-0.078 + ...) * s` (spanning `Y \in [-0.083m, -0.071m]`).
    - Eyelashes: `y0 = (-0.075 - ...) * s` (spanning `Y \in [-0.083m, -0.074m]`).
    - Scalp crown: radius `r_c = 0.065 * s` (spanning `Y \in [-0.068m, +0.068m]`).
  - In `src/morphomesh/human_generator.py`:
    - Head slices at $Z \in [1.50\text{m}, 1.60\text{m}]$ have $r_y \in [0.092\text{m}, 0.096\text{m}]$ and $y_o \in [-0.005\text{m}, -0.030\text{m}]$, establishing the anterior forehead and brow surface at $Y = y_o - r_y \in [-0.101\text{m}, -0.1258\text{m}]$.
    - Because the forehead front surface is at $Y = -0.101\text{m}$ to $-0.1258\text{m}$, generating hair at $Y \in [-0.065\text{m}, -0.092\text{m}]$ places the root and guide splines **$1.5\text{cm}$ to $5.0\text{cm}$ deep INSIDE the cranium volume**, completely buried beneath the opaque skull mesh.

### 1.3 Garment Clearance & Zero Penetration
- Empirical BVH signed distance measurement against `Yu_Nian_An_Body`:
  - Raw Geometry:
    - `Mesh_Dress_Bodice`: Min signed clearance = **$+6.48\text{mm}$**, Average = $+17.73\text{mm}$, Penetrations = **$0 / 140$**.
    - `Mesh_Dress_WaistSash`: Min signed clearance = **$+6.82\text{mm}$**, Average = $+28.44\text{mm}$, Penetrations = **$0 / 112$**.
    - `Mesh_Dress_PleatedSkirt`: Min signed clearance = **$+8.30\text{mm}$**, Average = $+86.99\text{mm}$, Penetrations = **$0 / 400$**.
  - Evaluated Geometry (with active Solidify modifier, thickness 2mm, offset -1.0):
    - `Mesh_Dress_Bodice`: Min signed clearance = **$+4.71\text{mm}$**, Penetrations = **$0 / 280$**.
    - `Mesh_Dress_WaistSash`: Min signed clearance = **$+4.98\text{mm}$**, Penetrations = **$0 / 224$**.
    - `Mesh_Dress_PleatedSkirt`: Min signed clearance = **$+8.30\text{mm}$**, Penetrations = **$0 / 800$**.
  - Garment clearance criteria: **PASS** (strictly $\ge +4.0\text{mm}$ with 0 vertex penetrations).

### 1.4 Magic Props & Marionette Kinematics
- Butterflies (`Prop_Butterfly_00` to `Prop_Butterfly_09`):
  - Exactly 10 butterflies fluttering in mid-air with $Z \in [0.880\text{m}, 1.280\text{m}]$.
  - Pairwise separation is $\ge 107.70\text{mm}$ ($> 50\text{mm}$ threshold). Zero butterflies at origin.
- Marionette Strings (`Prop_Marionette_Strings`):
  - 10 ribbon cords connect 10 fingertips to 10 butterflies.
  - Proximal root center error to `DEF-*.03.L/R` bone tails is **$0.0000\text{mm}$** ($1.000\text{mm}$ to ribbon lateral edge matching ribbon width $2\text{mm}$).
  - Distal ends connect smoothly to butterflies ($0.0000\text{mm}$ center error).
  - Dynamic bone rotation ($45^\circ / 60^\circ$) propagates live deformation to strings (up to $668\text{mm}$) and butterflies (up to $723\text{mm}$).
  - Magic props criteria: **PASS**.

---

## 2. Logic Chain

1. **Self-Certifying Test Masking vs Visual Reality**:
   - `tests/test_adversarial_m4_empirical.py` asserts `Test 1: len(eval_mesh.vertices) > 0` for all 6 hair layers and passed with `13,776 eval verts`.
   - However, vertex counting alone fails to evaluate spatial visibility. Our independent BVH raycasting and normal containment audit revealed that **100% of eyebrows, 100% of eyelashes, 90.9% of crown hair, 64.4% of sidelocks, and 54.1% of bangs are completely submerged inside the opaque body mesh**.
   - As a result, the rendered image `master_portrait_clean.png` presents a virtually bald figure. This constitutes an integrity gap: passing a unit test while presenting a broken visual artifact.

2. **Facial Feature Absence**:
   - The original project prompt (`ORIGINAL_REQUEST.md`) and assignment mandate:
     *"giữ trọn vẹn nét thanh tú thuần khiết, đôi mắt có hồn và biểu cảm tĩnh lặng/u buồn từ bản vẽ 4 góc nhìn"* and *"Verify facial features (eyes unburied and visible, melancholic gaze, hime cut bangs)"*.
   - In `human_generator.py`, the head is generated strictly as an 8-slice cross-sectional quad cylinder lofted into an ellipse. There are zero geometric vertices or topology representing a nose ridge, nostrils, lips, mouth slit, or eye orbits.
   - Simply placing eye spheres at $Y = -0.118\text{m}$ without modeled eyelids or orbital sockets leaves them as unblinking black button spheres. Combined with the buried hair, the character renders as an unsettling white mannequin dummy rather than Yu Nian An.

3. **Approved Engineering Deliverables vs Unresolved Aesthetic Scope**:
   - Camera framing (50.0mm lens, $\text{NDC } Y \in [0.1171, 0.8717]$) is completely solved.
   - String bone-snapping ($0.000\text{mm}$) and rig deformation are completely solved.
   - Garment clearance ($\ge +4.71\text{mm}$ evaluated, 0 penetrations) is completely solved.
   - However, because the visual beauty verification render (`master_portrait_clean.png`) fails the explicit acceptance criteria for facial features and hime cut bangs, the deliverable cannot be certified for final victory without remediating the hair projection and facial contours.

---

## 3. Caveats

- **Remediation Feasibility**: Fixing the hair does not require rebuilding the entire pipeline. Offsetting the splines in `human_grooming.py` forward along $+Y$ (e.g. subtracting $0.035\text{m}$ to $0.050\text{m}$ in Blender's coordinate system where $-Y$ is forward) will instantly bring the bangs, eyebrows, eyelashes, and crown out of the cranium and make them fully visible.
- **Back Cascade**: `Hair_Back_Cascade` is 73.3% external and renders well from the rear, but frontal layers are severely occluded.
- No other caveats.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

### Findings Breakdown:

#### [Critical] Finding 1: Buried Frontal Hair System Facade (Integrity Gap)
- **What**: 100% of eyebrows, 100% of eyelashes, 90.9% of crown hair, 64.4% of sidelocks, and 54.1% of bangs are buried inside the cranium mesh. In `master_portrait_clean.png`, the character appears virtually bald.
- **Where**: `src/morphomesh/human_grooming.py` (lines 215–330).
- **Why**: Hair generation coordinates were hardcoded with $Y \in [-0.065\text{m}, -0.092\text{m}]$, while the head mesh surface in `human_generator.py` extends forward to $Y = -0.110\text{m}$ to $-0.1258\text{m}$.
- **Remediation**: Adjust `human_grooming.py` splines so that bangs, eyebrows, eyelashes, and crown project anteriorly beyond the head surface (e.g., bangs $Y \in [-0.120\text{m}, -0.135\text{m}]$, eyebrows $Y \approx -0.128\text{m}$, eyelashes $Y \approx -0.130\text{m}$, crown radius expanded to $0.088\text{m}$).

#### [Major] Finding 2: Unsculpted Mannequin Face & Button Eye Appearance
- **What**: Face lacks anatomical facial features (no nose, no mouth slit, no lips, no eyelids/sockets), resulting in two black button eyes on a featureless egg head.
- **Where**: `src/morphomesh/human_generator.py` (head slice lofting) and `output/yu_nian_an/master_portrait_clean.png`.
- **Why**: Head slices are purely elliptical without nasal or oral anterior protrusion or orbital cavities.
- **Remediation**: In `human_generator.py` (or through vertex displacement in `character_assembler.py`), add nose bridge/tip protrusion ($+1.2\text{cm}$ forward at $Z \approx 1.51\text{m}$), mouth line depression, and eyelid rim / eye socket framing around the eye spheres.

---

## 5. Verification Method

To independently verify these findings:

1. **Verify Hair Occlusion & Containment**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background output/yu_nian_an/Yu_Nian_An_Master.blend --python-expr "import bpy, bmesh, mathutils; body = bpy.data.objects['Yu_Nian_An_Body']; bm = bmesh.new(); bm.from_mesh(body.data); bm.transform(body.matrix_world); bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm); cam = bpy.data.objects['Camera_Portrait_85mm']; cp = cam.matrix_world.translation; [print(h, 'Inside:', sum(1 for v in bpy.data.objects[h].data.vertices if (bpy.data.objects[h].matrix_world @ v.co - bvh.find_nearest(bpy.data.objects[h].matrix_world @ v.co)[0]).dot(bvh.find_nearest(bpy.data.objects[h].matrix_world @ v.co)[1]) < 0), '/', len(bpy.data.objects[h].data.vertices)) for h in ['Hair_Hime_Bangs', 'Hair_Eyebrows', 'Hair_Eyelashes', 'Hair_Scalp_Crown', 'Hair_Hime_Sidelocks']]"
   ```
   *Expected Result*: Demonstrates $>50\%$ of bangs, $100\%$ of eyebrows, $100\%$ of eyelashes, and $>90\%$ of crown vertices have negative dot products (submerged inside body).

2. **Inspect Beauty Renders**:
   - Inspect `output/yu_nian_an/master_portrait_clean.png` to confirm baldness and featureless egg head with button eyes.
   - Inspect `output/yu_nian_an/master_fullbody_clean.png` to confirm camera framing pass but identical facial blankness.

3. **Invalidation Condition**:
   This verdict is invalidated only if:
   - `Hair_Hime_Bangs`, `Hair_Eyebrows`, `Hair_Eyelashes`, and `Hair_Scalp_Crown` are verified to be $\ge 90\%$ exterior to the body mesh and fully visible from `Camera_Portrait_85mm`.
   - `master_portrait_clean.png` renders visible bangs, defined eyebrows/eyelashes, and articulated facial features matching Yu Nian An's reference art.
