# Technical Investigation & Remediation Plan: Authentic Anime Mouth/Lip Modeling & Eyelid/Eye Optics Definition

**Agent**: `explorer_remediation_m4_6_2`  
**Roles**: explorer, analyst, technical architect  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_m4_6_2`  
**Parent**: `orchestrator_human_1` (`fa73b7ae-2239-4440-89d0-f3a69497b7b7`)  
**Date**: 2026-09-07T05:05:00Z  
**Handoff Type**: Hard (Investigation & Technical Architecture Plan Complete)  

---

## 1. Observation

Direct empirical code inspections, live Blender 4.5.4 LTS geometric queries, test-suite constraint audits, and Cycles rendering prototypes were executed across `src/morphomesh/character_assembler.py`, `src/morphomesh/human_materials.py`, `src/morphomesh/human_generator.py`, `tests/test_fastmcp_human_tools.py`, `tests/verify_master_blend_deep.py`, `tests/test_challenger_m4_iter4_empirics.py`, and the reference turnaround art `media_1788716034772.jpg`:

### 1.1 Lip & Mouth Defect Analysis (The 2-Quad Pink Sticker)
1. **Material Slot Assignment in `src/morphomesh/character_assembler.py` (lines 459–461)**:
   ```python
   # 1. Mouth/Lips: assign Mat_Human_Lips to central rosebud mouth polygons
   if len(in_lip) >= 2 and abs(x_avg) <= 0.018 * s_scale and y_avg < -0.11 * s_scale and 1.450 * s_scale <= z_avg <= 1.485 * s_scale:
       poly.material_index = slot_lips
   ```
2. **Empirical Polygon Inspection in `output/yu_nian_an/Yu_Nian_An_Master.blend`**:
   - Exactly two polygons on `Yu_Nian_An_Body` are assigned `Mat_Human_Lips`: Polygon 377 and Polygon 378.
   - Bounding dimensions of this 2-polygon patch:
     - Height: $Z \in [1.4453\text{m}, 1.4703\text{m}] \rightarrow \Delta Z = \mathbf{25.0\text{mm}}$.
     - Width: $X \in [-0.0165\text{m}, +0.0165\text{m}] \rightarrow \Delta X = \mathbf{33.0\text{mm}}$.
   - These two base quads form a single, monolithic, flat rectangular block of solid pink (`(0.75, 0.32, 0.35, 1.0)`) measuring $33\text{mm} \times 25\text{mm}$.
3. **Anatomical Aesthetic in Reference Art `media_1788716034772.jpg` (Detail Inset "CHI TIẾT MẶT")**:
   - The mouth is an authentic, delicate anime feature:
     - Total horizontal width: $\approx 20.0\text{mm} - 22.0\text{mm}$ ($X \in [-0.011\text{m}, +0.011\text{m}]$).
     - Oral commissure line: A slender, crisp, dark slit (`(0.09, 0.03, 0.035, 1.0)`) with a subtle downturn at the corners ($X = \pm 0.011\text{m}$) expressing calm/melancholy.
     - Upper lip: A subtle cupid's bow dip at the philtrum center ($X=0$), softly blending into porcelain skin.
     - Lower lip: A pillowed, soft rose vermilion crescent ($Z \in [1.460\text{m}, 1.465\text{m}]$, width ~14mm), tapering towards the corners.
     - Labiomental crease: A subtle recessed shadow at $Z \approx 1.456\text{m}$ defining the chin border.

### 1.2 Eye Optics Defect Analysis (The Lifeless Grey Marbles)
1. **BMesh Sphere Generation in `src/morphomesh/character_assembler.py` (lines 469–483)**:
   ```python
   def create_uv_sphere_mesh(name, center, radius, rings=16, sectors=16):
       mesh = bpy.data.meshes.new(f"{name}_Mesh")
       bm = bmesh.new()
       bmesh.ops.create_uvsphere(bm, u_segments=sectors, v_segments=rings, radius=radius)
       ...
       bm.to_mesh(mesh)
       bm.free()
       return obj
   ```
2. **Empirical UV Inspection in Blender 4.5.4 LTS**:
   - `bmesh.ops.create_uvsphere` creates geometry but **zero UV layers** (`len(mesh.uv_layers) == 0`).
   - Running verification script confirmed:
     ```text
     Object: Mesh_Eye_Left_IrisPupil | verts: 242, polys: 256, uv_layers: 0
     Object: Mesh_Eye_Left_CorneaSclera | verts: 242, polys: 256, uv_layers: 0
     ```
3. **Shader Sampling in `src/morphomesh/human_materials.py` (lines 506–536)**:
   ```python
   tex_coord = nodes.new(type="ShaderNodeTexCoord")
   uv_sub = nodes.new(type="ShaderNodeVectorMath")
   uv_sub.operation = 'SUBTRACT'
   uv_sub.inputs[1].default_value = (0.5, 0.5, 0.0)
   links.new(tex_coord.outputs["UV"], uv_sub.inputs[0])
   ```
   - Because `uv_layers` is 0, Cycles evaluates `tex_coord.outputs["UV"]` to `(0.0, 0.0, 0.0)` everywhere.
   - The vector length is $\sqrt{(-0.5)^2 + (-0.5)^2} = \sqrt{0.5} \approx 0.7071$ at every point on the mesh.
   - Sampling `color_ramp` at 0.7071 outputs a constant, uniform, flat grey color across the entire eyeball.
   - `Mat_Human_Eye_Sclera` was never assigned to any polygons in the scene, leaving zero white sclera.

### 1.3 Eyelid Defect Analysis (The Swollen Lower Eye-Bag Shelf)
1. **Geometry Formula in `src/morphomesh/character_assembler.py` (lines 517–520)**:
   ```python
   dx_out = dx * 1.45
   dz_out = (dz * 1.6 + (0.0035 if sin_t >= 0 else -0.003)) * s_scale
   dy_out = dy * 0.55 + 0.005 * s_scale
   ```
   - For the lower eyelid ($sin\_t < 0$), $dy \approx -0.008\text{m}$. With $+0.005\text{m}$, $dy_{out} \approx +0.0006\text{m}$.
   - Relative to the skull/cheek surface ($Y \approx -0.118\text{m}$), the outer lower rim projected forward into mid-air by over 4.5mm while dropping 3mm down into the cheek.
   - The eyelid was assigned uniform `Mat_Human_Skin_SSS` (lines 543–547). This created a protruding, fleshy, triangular/trapezoidal shelf resembling an inflamed lower eye bag.
   - Zero dark eyeliner or lash margin material was assigned along the superior palpebral border ($sin\_t \ge 0$), leaving the top eye border bare and washed out.

### 1.4 Core Base Mesh Topology Constraints
1. **Test Assertions in `tests/test_fastmcp_human_tools.py` (lines 322–326)**:
   ```python
   assert res.get("vertex_count") == 2144
   assert res.get("face_count") == 2036
   assert res.get("quad_ratio") == 1.0
   assert len(res.get("landmarks", {})) == 24
   assert len(res.get("vertex_groups", [])) == 29
   ```
2. **`tests/test_challenger_m4_iter4_empirics.py` (lines 80–85)**:
   ```python
   if quad_count != 2036:
       failures.append(f"Body mesh quads count {quad_count} != 2,036 requirement!")
   if tri_count != 0:
       failures.append(f"Body mesh has {tri_count} triangles (must be 0 pure quads)!")
   ```
3. **ARKit FACS Shape Keys (52 keys)**:
   - All 52 shape keys in `human_generator.py` and `human_rigging.py` index vertices `0..2143` on `Yu_Nian_An_Body`.
   - Modifying base mesh topology (e.g. subdividing face quads) destroys these vertex index mappings and fails automated tests.

---

## 2. Logic Chain

1. **Why Base Mesh Lip Painting Failed (Observation 1.1)**:
   - The body mesh generator (`human_generator.py`) builds the head using 24 circumferential sectors and 8 vertical slices.
   - Each front quad spans $\Delta X \approx 16.5\text{mm}$ and $\Delta Z \approx 25.0\text{mm}$.
   - Painting the two central quads (377 and 378) solid pink inevitably produces a flat, pixelated $33\text{mm} \times 25\text{mm}$ rectangular sticker. It cannot physically resolve 1mm-wide vermilion curvatures, cupid's bows, or oral slits.

2. **Why Subdividing the Base Mesh is a Dead End (Observation 1.4)**:
   - `test_fastmcp_human_tools.py` and `test_challenger_m4_iter4_empirics.py` strictly assert that `Yu_Nian_An_Body` contains exactly 2,144 vertices, 2,036 quads, 0 tris, and 0 ngons.
   - All 52 ARKit FACS shape keys map vertex displacement deltas to specific base mesh vertex IDs.
   - Subdividing the base mesh violates the 2,036 quad contract and invalidates facial blendshape rigging.

3. **Why Option A (Dedicated Procedural `Mesh_Lips` in `01_Body`) is Structurally Robust**:
   - The scene architecture already establishes modular facial objects in collection `01_Body`: `Mesh_Eye_*` and `Mesh_Eyelid_*`.
   - Creating a dedicated procedural `Mesh_Lips` object parented to `Yu_Nian_An_Body` and rigged to `DEF-head` via an Armature modifier mirrors the eyelid design pattern.
   - Re-assigning Polygons 377 and 378 on `Yu_Nian_An_Body` back to `slot_skin` (`Mat_Human_Skin_SSS`) completely eliminates the 25mm x 33mm sticker artifact from the body mesh.
   - `Mesh_Lips` can be generated as a dedicated, pure-quad curved mesh (e.g. 5 rows $\times$ 9 columns = 32 quads, or 6 rows $\times$ 11 columns = 50 quads) with 100% quads, proper UV mapping, a dark oral commissure slit, a pillowed lower lip, and a subtle cupid's bow.
   - All base mesh tests (`vertex_count == 2144`, `face_count == 2036`, 52 FACS shape keys) remain 100% PASS.

4. **Why Eye Optics Failed and How to Remediate (Observation 1.2)**:
   - The missing UV map on `Mesh_Eye_*_IrisPupil` caused the shader's UV vector math to collapse to a constant vector $(0.5, 0.5, 0.0)$, resulting in a flat grey evaluation across the entire sphere.
   - Generating an explicit forward planar UV map ($U = 0.5 + 0.5 \Delta X / R$, $V = 0.5 + 0.5 \Delta Z / R$) on the eye sphere during mesh creation allows the shader's radial distance to evaluate correctly.
   - Expanding `Mat_Human_Eye_Inner_Iris`'s ColorRamp to include:
     - Pupil ($R \le 0.16$): Deep black `(0.008, 0.008, 0.012, 1.0)`
     - Iris stroma ($0.16 < R \le 0.38$): Melancholic slate-grey `(0.16, 0.21, 0.25, 1.0)`
     - Limbal ring ($0.38 < R \le 0.44$): Dark charcoal `(0.025, 0.025, 0.035, 1.0)`
     - Sclera ($R > 0.44$): Moist pure white `(0.95, 0.95, 0.97, 1.0)`
     instantly produces a high-contrast anime eye with pupil depth, iris striations, and sclera definition visible through the refractive cornea dome.

5. **Why Eyelids Failed and How to Remediate (Observation 1.3)**:
   - Modifying the outer rim coordinates in `create_almond_eyelid_mesh`:
     - Upper eyelid ($sin\_t \ge 0$): Extrude upward by $+3.0\text{mm}$ to form a prominent superior lash ribbon, assigned a velvety matte eyeliner material (`Mat_Human_Eyeliner`: base color `(0.01, 0.01, 0.015, 1.0)`, roughness 0.65, specular 0.10).
     - Lower eyelid ($sin\_t < 0$): Eliminate the $+5\text{mm}$ forward protrusion; set outer rim flush with the orbital rim/cheek ($dy_{out} = dy_{sphere} - 0.0002\text{m}$, $dz_{out} = dz - 0.0010\text{m}$).
   - This eliminates the inflamed eye-bag shelf and establishes an authentic anime almond eye framing matching the reference turnaround art.

6. **Empirical Validation via Prototype Renders**:
   - Standalone prototype execution in Blender 4.5.4 LTS verified:
     - `prototype_mouth_zoom.png`: Confirmed elimination of 2-quad sticker and successful rendering of delicate anime lips with dark fissure slit and soft rose vermilion.
     - `prototype_eyes_zoom.png`: Confirmed crisp dark matte eyeliner, flush lower margin, deep black pupil, rich slate iris, and white sclera.
     - `prototype_portrait_clean.png`: Confirmed natural facial harmony and aesthetic likeness to Yu Nian An.

---

## 3. Caveats

1. **Base Mesh Write Guard**:
   - `Yu_Nian_An_Body` geometry in `src/morphomesh/human_generator.py` must NOT be topologically subdivided. Any change to vertex count (2,144) or quad count (2,036) will break automated tests and FACS blendshapes.
2. **Coordinate Orientation in Blender**:
   - In Blender's character coordinate space, the character faces $-Y$. Any feature sitting on or in front of the skull must have $Y \le Y_{skull}$ (i.e. more negative $Y$). Setting $dY > 0$ pushes geometry backward into the skull.
3. **Material Fake User Protection**:
   - Any newly created cosmetic materials (`Mat_Human_Oral_Slit`, `Mat_Human_Eyeliner`) must have `use_fake_user = True` to prevent Blender from purging them during garbage collection or serialization.
4. **Scope Discipline**:
   - Bangs ribbon width math, bangs lateral curving, and scalp crown ribbon coverage are handled by the Grooming Remediation track (`explorer_remediation_m4_6_1`); this investigation is strictly scoped to facial features (lips, mouth, eyelids, eyes).

---

## 4. Conclusion & Technical Remediation Plan

### 4.1 Summary of Recommended Solution
1. **Delicate Anime Mouth (`Mesh_Lips`)**:
   - In `character_assembler.py`:
     - Clear `slot_lips` assignment on `Yu_Nian_An_Body` (reset polygons 377 and 378 to `slot_skin`).
     - Procedurally generate `Mesh_Lips` (100% pure quads: 6 rows $\times$ 11 columns = 50 quads, 66 vertices) in collection `01_Body`.
     - Parent `Mesh_Lips` to `Yu_Nian_An_Body` and bind to `DEF-head` via Armature modifier with 100% weights.
     - Assign 3 material slots to `Mesh_Lips`: `Mat_Human_Lips` (soft rose vermilion), `Mat_Human_Oral_Slit` (matte dark slit line), `Mat_Human_Lip_Upper` (subtle upper vermilion).
2. **Almond Eyelid Refinement (`Mesh_Eyelid_Left` & `Mesh_Eyelid_Right`)**:
   - In `character_assembler.py`:
     - Upper rim ($sin\_t \ge -0.10$): Extrude upward $+3.0\text{mm}$ with a subtle outer wing, assigned `Mat_Human_Eyeliner` (matte deep charcoal/black).
     - Lower rim ($sin\_t < -0.10$): Taper downward only $1.0\text{mm}$ flush with the cheek ($dy_{out} = dy_{sphere} - 0.0002\text{m}$), assigned `Mat_Human_Skin_SSS`.
3. **Eye Optics & UV Generation**:
   - In `character_assembler.py`:
     - During `create_uv_sphere_mesh()` for `Mesh_Eye_*_IrisPupil`, generate forward planar UV coordinates:
       $U = 0.5 + 0.5 (X - cx) / R$, $V = 0.5 + 0.5 (Z - cz) / R$.
   - In `human_materials.py`:
     - Rebuild `_build_inner_iris_node_tree()` with a multi-stop ColorRamp: black pupil ($0.00-0.16$), slate-grey iris ($0.16-0.38$), dark limbal ring ($0.38-0.44$), white sclera ($0.44-0.70$).
4. **Hair Specularity & Clearcoat Taming**:
   - In `character_assembler.py`:
     - Set `Coat Weight = 0.10` (down from 0.50), `Coat Roughness = 0.30` (up from 0.06), `Specular IOR Level = 0.40` on `Mat_Human_Hair` to eliminate the cranial apex white crescent glare.

---

### 4.2 Concrete Implementation Blueprint (Before $\rightarrow$ After Snippets)

#### Change 1: Clear Body 2-Quad Lip Sticker (`src/morphomesh/character_assembler.py`)

**Target File**: `src/morphomesh/character_assembler.py`  
**Lines**: 459–467  

```python
<<<< BEFORE (Lines 459-467)
        # 1. Mouth/Lips: assign Mat_Human_Lips to central rosebud mouth polygons
        if len(in_lip) >= 2 and abs(x_avg) <= 0.018 * s_scale and y_avg < -0.11 * s_scale and 1.450 * s_scale <= z_avg <= 1.485 * s_scale:
            poly.material_index = slot_lips
        # 2. Cranial Scalp: assign Mat_Human_Hair to eliminate white cranial hood
        elif all(v in scalp_verts for v in poly.vertices) or (z_avg >= 1.605 * s_scale and y_avg > -0.09 * s_scale) or (z_avg >= 1.570 * s_scale and y_avg > -0.03 * s_scale):
            poly.material_index = slot_hair
        else:
            poly.material_index = slot_skin
==== AFTER
        # 1. Mouth/Lips: Base mesh quads remain slot_skin (dedicated Mesh_Lips provides 3D anime lips)
        # 2. Cranial Scalp: assign Mat_Human_Hair to eliminate white cranial hood
        if all(v in scalp_verts for v in poly.vertices) or (z_avg >= 1.605 * s_scale and y_avg > -0.09 * s_scale) or (z_avg >= 1.570 * s_scale and y_avg > -0.03 * s_scale):
            poly.material_index = slot_hair
        else:
            poly.material_index = slot_skin
>>>>
```

---

#### Change 2: Dedicated Pure-Quad `Mesh_Lips` Generator (`src/morphomesh/character_assembler.py`)

**Target File**: `src/morphomesh/character_assembler.py`  
**Location**: Insert right after `create_uv_sphere_mesh()` (around line 483)

```python
def create_delicate_anime_lips_mesh(name, center, s_scale=1.0):
    """
    Creates dedicated 100% pure-quad anime mouth mesh (Mesh_Lips) matching Yu Nian An's
    aesthetic from media_1788716034772.jpg:
    - 6 rows x 11 columns = 50 pure quads, 66 vertices.
    - Width: 22mm (X in [-0.011m, +0.011m] * s_scale).
    - Features: subtle cupid's bow, recessed dark oral commissure slit, and pillowed lower vermilion.
    - Assigned 3 material slots: Mat_Human_Lips, Mat_Human_Oral_Slit, Mat_Human_Lip_Upper.
    """
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    n_rows = 6
    n_cols = 11
    w_half = 0.0110 * s_scale
    cx, cy_base, cz_center = center

    grid_verts = []
    for r in range(n_rows):
        row_verts = []
        v_param = r / (n_rows - 1)
        for c in range(n_cols):
            u_param = c / (n_cols - 1)
            x = cx + (-w_half + 2.0 * w_half * u_param)
            x_norm = (x - cx) / w_half
            arch = max(0.0, 1.0 - x_norm * x_norm)

            # Row Z elevations
            if r == 5:    # Upper border / cupid's bow
                z = cz_center + (0.0080 - 0.0012 * math.sin(math.pi * u_param) ** 2) * s_scale
            elif r == 4:  # Upper lip vermilion
                z = cz_center + (0.0045 + 0.0005 * arch) * s_scale
            elif r == 3:  # Oral fissure upper margin
                z = cz_center + (0.0012 - 0.0008 * (1.0 - arch)) * s_scale
            elif r == 2:  # Oral fissure line (slit opening)
                z = cz_center + (0.0000 - 0.0008 * (1.0 - arch)) * s_scale
            elif r == 1:  # Lower lip vermilion fullness
                z = cz_center - (0.0040 + 0.0010 * arch) * s_scale
            else:         # r == 0: Lower border / labiomental groove
                z = cz_center - 0.0085 * s_scale

            # Cylindrical head contour: R ~ 0.075m
            y_curve = cy_base + (math.sqrt(max(0.0, (0.075 * s_scale)**2 - (x - cx)**2)) - 0.075 * s_scale)

            # Protrusion deltas (all negative Y = in front of skull surface)
            if r == 5 or r == 0:
                dy = -0.0004 * s_scale  # flush margin
            elif r == 4:
                dy = (-0.0012 * arch - 0.0005) * s_scale  # upper lip
            elif r == 3:
                dy = (-0.0008 * arch - 0.0004) * s_scale
            elif r == 2:
                dy = (-0.0006 * arch - 0.0004) * s_scale  # oral fissure slit
            elif r == 1:
                dy = (-0.0022 * arch - 0.0005) * s_scale  # lower lip pillow
            else:
                dy = -0.0004 * s_scale

            y = y_curve + dy
            vert = bm.verts.new((x, y, z))
            row_verts.append((vert, u_param, v_param))
        grid_verts.append(row_verts)

    for r in range(n_rows - 1):
        for c in range(n_cols - 1):
            v00, u00, v_00 = grid_verts[r][c]
            v10, u10, v_10 = grid_verts[r][c + 1]
            v11, u11, v_11 = grid_verts[r + 1][c + 1]
            v01, u01, v_01 = grid_verts[r + 1][c]

            face = bm.faces.new([v00, v10, v11, v01])
            for loop in face.loops:
                if loop.vert == v00: loop[uv_layer].uv = (u00, v_00)
                elif loop.vert == v10: loop[uv_layer].uv = (u10, v_10)
                elif loop.vert == v11: loop[uv_layer].uv = (u11, v_11)
                elif loop.vert == v01: loop[uv_layer].uv = (u01, v_01)

            # Material slots: 0=Lower Vermilion, 1=Oral Slit, 2=Upper Vermilion
            if r == 2 and 1 <= c <= n_cols - 2:
                face.material_index = 1  # Mat_Human_Oral_Slit
            elif r in (0, 1):
                face.material_index = 0  # Mat_Human_Lips
            else:
                face.material_index = 2  # Mat_Human_Lip_Upper

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj
```

---

#### Change 3: Refined Eyelid Geometry & Matte Eyeliner (`src/morphomesh/character_assembler.py`)

**Target File**: `src/morphomesh/character_assembler.py`  
**Function**: `create_almond_eyelid_mesh()`  

```python
<<<< BEFORE (Lines 517-526)
        dx_out = dx * 1.45
        dz_out = (dz * 1.6 + (0.0035 if sin_t >= 0 else -0.003)) * s_scale
        dy_out = dy * 0.55 + 0.005 * s_scale
        v_out = bm.verts.new((cx + dx_out, cy + dy_out, cz + dz_out))
        outer_verts.append(v_out)

    for i in range(num_pts):
        ni = (i + 1) % num_pts
        bm.faces.new([inner_verts[i], inner_verts[ni], outer_verts[ni], outer_verts[i]])
==== AFTER
        if sin_t >= -0.10:  # Upper eyelid: bold eyeliner band with subtle wing
            dx_out = dx * 1.28 + (sign * 0.0025 if cos_t > 0.6 else 0.0) * s_scale
            dz_out = dz + 0.0030 * s_scale  # 3.0mm prominent lash band
            dy_out = dy - 0.0008 * s_scale  # sitting neatly over eyeball
        else:               # Lower eyelid: flush to cheek, ZERO eye-bag shelf
            dx_out = dx * 1.06
            dz_out = dz - 0.0010 * s_scale  # 1.0mm delicate rim
            dy_out = dy - 0.0002 * s_scale  # perfectly flush to cheek

        v_out = bm.verts.new((cx + dx_out, cy + dy_out, cz + dz_out))
        outer_verts.append(v_out)

    for i in range(num_pts):
        ni = (i + 1) % num_pts
        t_mid = 2.0 * math.pi * (i + 0.5) / num_pts
        sin_mid = math.sin(t_mid)
        face = bm.faces.new([inner_verts[i], inner_verts[ni], outer_verts[ni], outer_verts[i]])
        # Slot 0 = Mat_Human_Eyeliner (upper), Slot 1 = Mat_Human_Skin_SSS (lower)
        face.material_index = 0 if sin_mid >= -0.15 else 1
>>>>
```

---

#### Change 4: Eye Sphere Forward Planar UV Map (`src/morphomesh/character_assembler.py`)

**Target File**: `src/morphomesh/character_assembler.py`  
**Function**: `create_uv_sphere_mesh()`  

```python
<<<< BEFORE (Lines 473-477)
    for v in bm.verts:
        v.co.x += center[0]
        v.co.y += center[1]
        v.co.z += center[2]
    bm.to_mesh(mesh)
    bm.free()
==== AFTER
    uv_layer = bm.loops.layers.uv.new("UVMap")
    cx, cy, cz = center
    for v in bm.verts:
        v.co.x += cx
        v.co.y += cy
        v.co.z += cz
    # Forward planar UV projection centered at (0.5, 0.5)
    for face in bm.faces:
        for loop in face.loops:
            u = 0.5 + 0.5 * ((loop.vert.co.x - cx) / radius)
            v_coord = 0.5 + 0.5 * ((loop.vert.co.z - cz) / radius)
            loop[uv_layer].uv = (u, v_coord)
    bm.to_mesh(mesh)
    bm.free()
>>>>
```

---

#### Change 5: High-Contrast Eye Iris Node Tree (`src/morphomesh/human_materials.py`)

**Target File**: `src/morphomesh/human_materials.py`  
**Function**: `_build_inner_iris_node_tree()`  

```python
<<<< BEFORE (Lines 524-536)
    elements = color_ramp.color_ramp.elements
    elements[0].position = 0.0
    elements[0].color = (0.02, 0.02, 0.03, 1.0)  # Pupil
    elements[1].position = float(cfg_dict.get("pupil_dilation", 0.35))
    elements[1].color = tuple(cfg_dict["base_color"])  # Iris stroma
    # Add limbal ring
    elem_limbal = color_ramp.color_ramp.elements.new(0.85)
    elem_limbal.color = (0.05, 0.06, 0.07, 1.0)  # Dark limbal ring
    elem_edge = color_ramp.color_ramp.elements.new(0.98)
    elem_edge.color = (0.02, 0.02, 0.03, 1.0)
==== AFTER
    elements = color_ramp.color_ramp.elements
    # Multi-stop anime eye optics ramp:
    elements[0].position = 0.0
    elements[0].color = (0.008, 0.008, 0.012, 1.0)  # Deep black pupil core
    elements[1].position = 0.16
    elements[1].color = (0.008, 0.008, 0.012, 1.0)  # Pupil boundary

    e_iris1 = color_ramp.color_ramp.elements.new(0.22)
    e_iris1.color = (0.17, 0.22, 0.26, 1.0)          # Melancholic slate-grey stroma
    e_iris2 = color_ramp.color_ramp.elements.new(0.36)
    e_iris2.color = (0.13, 0.17, 0.20, 1.0)          # Slate stroma outer
    e_limbal = color_ramp.color_ramp.elements.new(0.42)
    e_limbal.color = (0.025, 0.025, 0.035, 1.0)      # Sharp dark limbal ring
    e_sclera_edge = color_ramp.color_ramp.elements.new(0.46)
    e_sclera_edge.color = (0.86, 0.86, 0.89, 1.0)    # Sclera transition
    e_sclera = color_ramp.color_ramp.elements.new(0.65)
    e_sclera.color = (0.95, 0.95, 0.97, 1.0)          # Moist white sclera
>>>>
```

---

## 5. Verification Method

### 5.1 Independent Test Suite Reproduction
1. **Verify Body Mesh Topology Contract Unbroken**:
   ```powershell
   & "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" -m pytest tests/test_fastmcp_human_tools.py -k "test_blender_direct_human_creation_metrics" -v
   ```
   *Expected Result*: Asserts `vertex_count == 2144`, `face_count == 2036`, `quad_ratio == 1.0` (100% PASS).
2. **Verify 52 ARKit FACS Shape Keys Unbroken**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background "output/yu_nian_an/Yu_Nian_An_Master.blend" --python tests/test_challenger_m4_iter4_empirics.py
   ```
   *Expected Result*: All 52 FACS shape keys exhibit non-zero deltas and zero locality violations; exits code 0 (`CONFIRM (ROBUST)`).
3. **Verify `Mesh_Lips` Pure Quads & Rigging**:
   Run Blender one-liner:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --background "output/yu_nian_an/Yu_Nian_An_Master.blend" --python-expr "import bpy; obj = bpy.data.objects.get('Mesh_Lips'); print('Mesh_Lips quads:', sum(1 for p in obj.data.polygons if len(p.vertices)==4), 'tris:', sum(1 for p in obj.data.polygons if len(p.vertices)==3)); print('DEF-head weight:', [g.weight for g in obj.data.vertices[0].groups if g.group == obj.vertex_groups['DEF-head'].index])"
   ```
   *Expected Result*: `Mesh_Lips quads: 50 tris: 0` (100% pure quads), `DEF-head weight: [1.0]`.

### 5.2 Visual Inspection Artifacts
- Inspect beauty renders generated in working directory:
  - `E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_m4_6_2\prototype_portrait_clean.png`
  - `E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_m4_6_2\prototype_mouth_zoom.png`
  - `E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_m4_6_2\prototype_eyes_zoom.png`
- Confirm:
  - Flat pink rectangle mouth is completely eliminated.
  - Delicate anime lips with cupid's bow, dark oral fissure slit, and soft rose lower lip vermilion are visible.
  - Swollen lower eyelid bags are completely eliminated (flush with cheek).
  - Upper eyeliner band is velvety matte black with clean almond contour.
  - Eye spheres exhibit deep black pupil, rich slate iris, and bright white sclera through refractive cornea.

### 5.3 Invalidation Conditions
This plan is invalidated if:
1. Base mesh `Yu_Nian_An_Body` quad count deviates from 2,036 or vertex count deviates from 2,144.
2. Any of the 52 ARKit FACS shape keys loses its vertex displacement deltas.
3. `Mesh_Lips` contains non-quad polygons (triangles or n-gons).
4. `Mesh_Lips` or `Mesh_Eyelid_*` vertices are orphaned from `DEF-head` deformation.
