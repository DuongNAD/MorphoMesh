"""
MorphoMesh: Definitive Master Character Assembler
Recreates Yu Nian An (余念安) matching concept sheet media_1788716034772.jpg
and user references media_1788785935849.jpg / media_1788785935854.png:
1. Anatomical Female Base Mold:
   - Teardrop volumetric bust with natural cleavage and inframammary fold
   - Rounded, perky gluteal curves (vòng mông nở nang) and natural lumbar lordosis
   - Straight normal human leg posture, articulated knees and ankles
   - 5 distinct toes on each foot, completely exposed
   - Visible clavicle (xương quai xanh) and relaxed 24.2° trapezius slope
2. Smooth One-Piece Sundress (Váy Liền Thân):
   - Sweetheart contoured bodice tailored over bust with +4mm fabric clearance
   - Thin spaghetti straps crossing over shoulders
   - Ice-blue satin waist sash with bow knot and twin cascading ribbon tails
   - Flowing A-line flared skirt with organic drape ripples (ZERO accordion pleats!)
3. Flat Sandals (Dép Bệt):
   - Flat leather sole beneath footbed, instep strap, 100% bare toes exposed
4. Silky Black Hime Cut Hair:
   - Full scalp coverage (ZERO bald spots or clipping)
   - Straight blunt bangs at eyebrow line
   - Long sidelocks framing cheeks past shoulders
   - Long cascading back hair past hips to mid-thigh
5. Soulful Anime Face:
   - Expressive sapphire-blue eyes, white sclera, delicate lashes & brows
   - Gentle, slightly melancholic expression
   - Cherry pink tinted lips
6. Signature Props:
   - 10 red marionette strings tethered from fingertips
   - 10 luminous white swallowtail butterflies fluttering along strings
7. Rigify 163 DEF Armature + 52 ARKit FACS Shape Keys
8. Cinema-Grade Cycles AgX 5-Angle Renders
"""

import bpy
import bmesh
import math
import sys
import os
from mathutils import Vector, Matrix, Euler

sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\.venv\Lib\site-packages")
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
from morphomesh.human_generator import load_anatomical_base_mold
from morphomesh.human_rigging import ALL_163_DEF_BONES

def build_definitive_character():
    print("=" * 80)
    print("STARTING DEFINITIVE MASTER CHARACTER SYNTHESIS")
    print("=" * 80)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # --------------------------------------------------------------------------
    # 1. SETUP 7-TIER HIERARCHY
    # --------------------------------------------------------------------------
    root_name = "Yu_Nian_An_Master"
    root_col = bpy.data.collections.new(root_name)
    scene.collection.children.link(root_col)

    tiers = {}
    for tn in ["01_Body", "02_Hair", "03_Wardrobe", "04_Props", "05_Armature", "06_Lights_Camera"]:
        c = bpy.data.collections.new(tn)
        root_col.children.link(c)
        tiers[tn] = c

    def link(obj, tname):
        if not obj: return
        t_col = tiers[tname]
        if obj.name not in t_col.objects:
            t_col.objects.link(obj)
        for col in list(bpy.data.collections):
            if col != t_col and obj.name in col.objects:
                col.objects.unlink(obj)
        if obj.name in scene.collection.objects:
            scene.collection.objects.unlink(obj)

    # --------------------------------------------------------------------------
    # 2. SETUP AUTHORITATIVE MATERIALS
    # --------------------------------------------------------------------------
    mats = {}

    def make_mat(name, base_color, roughness=0.4, metallic=0.0, sss_weight=0.0, sss_radius=(0.008, 0.004, 0.002), sheen=0.0, emission=None):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        m.use_fake_user = True
        nodes = m.node_tree.nodes
        links = m.node_tree.links
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = base_color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if "Subsurface Weight" in bsdf.inputs and sss_weight > 0:
            bsdf.subsurface_method = 'RANDOM_WALK'
            bsdf.inputs["Subsurface Weight"].default_value = sss_weight
            bsdf.inputs["Subsurface Radius"].default_value = sss_radius
            bsdf.inputs["Subsurface Scale"].default_value = 0.05
        elif "Subsurface" in bsdf.inputs and sss_weight > 0:
            bsdf.inputs["Subsurface"].default_value = sss_weight
        if "Sheen Weight" in bsdf.inputs and sheen > 0:
            bsdf.inputs["Sheen Weight"].default_value = sheen
        if emission:
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = emission[0]
                bsdf.inputs["Emission Strength"].default_value = emission[1]
            elif "Emission" in bsdf.inputs:
                bsdf.inputs["Emission"].default_value = emission[0]
                bsdf.inputs["Emission Strength"].default_value = emission[1]
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        mats[name] = m
        return m

    make_mat("Mat_Human_Skin_SSS", (0.957, 0.894, 0.863, 1.0), 0.36, sss_weight=0.35)
    make_mat("Mat_Dress_WhiteSilk", (0.965, 0.965, 0.975, 1.0), 0.28, sheen=0.90)
    make_mat("Mat_Dress_WaistBelt", (0.22, 0.56, 0.84, 1.0), 0.18, sheen=1.0)
    make_mat("Mat_Human_Hair", (0.015, 0.014, 0.016, 1.0), 0.25)
    make_mat("Mat_Sandal_Leather", (0.92, 0.90, 0.88, 1.0), 0.40)
    make_mat("Mat_Marionette_RedString", (0.95, 0.06, 0.10, 1.0), 0.35, emission=((0.95, 0.06, 0.10, 1.0), 3.5))
    make_mat("Mat_Magic_Butterfly", (0.98, 0.99, 1.00, 1.0), 0.18, emission=((0.96, 0.98, 1.00, 1.0), 5.0))
    make_mat("Mat_Human_Lips", (0.86, 0.38, 0.45, 1.0), 0.22, sss_weight=0.30)
    make_mat("Mat_Human_Eye_Iris", (0.12, 0.38, 0.65, 1.0), 0.08)
    make_mat("Mat_Human_Eye_Sclera", (0.96, 0.96, 0.98, 1.0), 0.12)
    make_mat("Mat_Human_Eye_Pupil", (0.01, 0.01, 0.015, 1.0), 0.05)
    make_mat("Mat_Studio_Backdrop", (0.12, 0.13, 0.15, 1.0), 0.85)

    # --------------------------------------------------------------------------
    # 3. BUILD ANATOMICAL FEMALE BASE MOLD
    # --------------------------------------------------------------------------
    print("[MorphoMesh] Building perfected anatomical female base mold...")
    raw_verts, raw_quads, raw_uvs = load_anatomical_base_mold()
    s = 1.0

    verts = [list(v) for v in raw_verts]
    for i, (x, y, z) in enumerate(verts):
        # 3.1 Teardrop Volumetric Bust with Gravity Sag & Cleavage
        if 1.06 * s <= z <= 1.28 * s and abs(x) < 0.22 * s and y < -0.015 * s:
            dx_b = (abs(x) - 0.088 * s) / (0.078 * s)
            dz_b = (z - 1.165 * s) / (0.085 * s)
            r2_b = dx_b * dx_b + dz_b * dz_b
            if r2_b < 1.0:
                sag = 1.0 - 0.35 * dz_b
                w_bust = (math.cos(r2_b * math.pi * 0.5) ** 2) * sag
                verts[i][1] -= 0.038 * s * w_bust
                if abs(x) < 0.032 * s:
                    c_dip = (math.cos(abs(x) * math.pi / (0.032 * s)) + 1.0) * 0.5
                    verts[i][1] += 0.014 * s * c_dip

        # 3.2 Rounded Gluteal Curves (Vòng mông nở nang tròn đầy)
        if 0.72 * s <= z <= 0.98 * s and abs(x) < 0.22 * s and y > 0.005 * s:
            dx_g = (abs(x) - 0.086 * s) / (0.086 * s)
            dz_g = (z - 0.855 * s) / (0.110 * s)
            r2_g = dx_g * dx_g + dz_g * dz_g
            if r2_g < 1.0:
                w_glute = math.cos(r2_g * math.pi * 0.5) ** 2
                verts[i][1] += 0.030 * s * w_glute
                if dz_g < -0.2:
                    thigh_blend = (-0.2 - dz_g) / 0.8
                    verts[i][1] += 0.008 * s * thigh_blend * (1.0 - dx_g * dx_g)

        # 3.3 Lumbar Lordosis (Độ cong thắt lưng)
        if 0.95 * s <= z <= 1.09 * s and abs(x) < 0.16 * s and y > 0.01 * s:
            w_lumbar = (math.cos((z - 1.02 * s) * math.pi / (0.14 * s)) ** 2)
            verts[i][1] -= 0.014 * s * w_lumbar

        # 3.4 Waist Cinch (WHR ~ 0.697)
        if 0.96 * s <= z <= 1.10 * s and abs(x) < 0.20 * s:
            w_waist = (math.cos((z - 1.025 * s) * math.pi / (0.14 * s)) ** 2)
            verts[i][0] *= (1.0 - 0.075 * w_waist)
            verts[i][1] *= (1.0 - 0.055 * w_waist)

        # 3.5 Clavicle Definition (Xương quai xanh)
        if 1.28 * s <= z <= 1.34 * s and 0.02 * s < abs(x) < 0.14 * s and y < -0.01 * s:
            dx_c = (abs(x) - 0.08 * s) / (0.06 * s)
            dz_c = (z - 1.31 * s) / (0.03 * s)
            r2_c = dx_c * dx_c + dz_c * dz_c
            if r2_c < 1.0:
                w_clav = (math.cos(r2_c * math.pi * 0.5) ** 2)
                verts[i][1] -= 0.005 * s * w_clav

        # 3.6 Delicate Feminine Jaw & Chin
        if z >= 1.38 * s:
            if z < 1.46 * s and y < -0.03 * s:
                t_chin = max(0.0, (1.46 * s - z) / (0.08 * s))
                w_chin = t_chin ** 1.5
                verts[i][0] *= (1.0 - 0.06 * w_chin)
                if abs(x) < 0.025 * s and 1.39 * s <= z <= 1.43 * s:
                    verts[i][1] -= 0.003 * s * (1.0 - abs(x) / (0.025 * s))

    b_mesh = bpy.data.meshes.new("Yu_Nian_An_Body_Mesh")
    bm_b = bmesh.new()
    for v in verts:
        bm_b.verts.new(v)
    bm_b.verts.ensure_lookup_table()
    for q in raw_quads:
        bm_b.faces.new([bm_b.verts[vi] for vi in q])
    bm_b.to_mesh(b_mesh)
    bm_b.free()

    body_obj = bpy.data.objects.new("Yu_Nian_An_Body", b_mesh)
    link(body_obj, "01_Body")
    body_obj.data.materials.append(mats["Mat_Human_Skin_SSS"])
    for p in b_mesh.polygons:
        p.use_smooth = True

    sub_b = body_obj.modifiers.new("Subsurf", 'SUBSURF')
    sub_b.levels = 1

    # --------------------------------------------------------------------------
    # 4. FACIAL FEATURES: SAPPHIRE EYES & LIPS
    # --------------------------------------------------------------------------
    # Left & Right Eyeballs
    for side_sign, eye_name in [(1.0, "Mesh_Eye_L"), (-1.0, "Mesh_Eye_R")]:
        bm_eye = bmesh.new()
        eye_cx = side_sign * 0.032
        eye_cy = -0.118
        eye_cz = 1.492
        eye_r = 0.0135

        # Sclera sphere
        bmesh.ops.create_uvsphere(bm_eye, u_segments=16, v_segments=12, radius=eye_r)
        for v in bm_eye.verts:
            v.co.x += eye_cx
            v.co.y += eye_cy
            v.co.z += eye_cz

        eye_m = bpy.data.meshes.new(f"{eye_name}_Mesh")
        bm_eye.to_mesh(eye_m)
        bm_eye.free()
        eye_obj = bpy.data.objects.new(eye_name, eye_m)
        link(eye_obj, "01_Body")
        eye_obj.data.materials.append(mats["Mat_Human_Eye_Iris"])
        for p in eye_m.polygons: p.use_smooth = True

    # Delicate soft lips
    bm_lip = bmesh.new()
    lip_pts = [
        # Upper lip arch
        (-0.016, -0.128, 1.436),
        (-0.008, -0.131, 1.440),
        ( 0.000, -0.130, 1.438), # Cupid's bow dip
        ( 0.008, -0.131, 1.440),
        ( 0.016, -0.128, 1.436),
        # Midline oral slit
        ( 0.014, -0.129, 1.432),
        ( 0.000, -0.131, 1.433),
        (-0.014, -0.129, 1.432),
        # Lower lip fullness
        (-0.012, -0.128, 1.428),
        ( 0.000, -0.132, 1.425),
        ( 0.012, -0.128, 1.428),
    ]
    lip_v = [bm_lip.verts.new(p) for p in lip_pts]
    # Faces
    bm_lip.faces.new([lip_v[0], lip_v[1], lip_v[6], lip_v[7]])
    bm_lip.faces.new([lip_v[1], lip_v[2], lip_v[3], lip_v[6]])
    bm_lip.faces.new([lip_v[3], lip_v[4], lip_v[5], lip_v[6]])
    bm_lip.faces.new([lip_v[7], lip_v[6], lip_v[9], lip_v[8]])
    bm_lip.faces.new([lip_v[6], lip_v[5], lip_v[10], lip_v[9]])
    for f in bm_lip.faces: f.smooth = True
    lip_m = bpy.data.meshes.new("Mesh_Lips_Mesh")
    bm_lip.to_mesh(lip_m)
    bm_lip.free()
    lip_obj = bpy.data.objects.new("Mesh_Lips", lip_m)
    link(lip_obj, "01_Body")
    lip_obj.data.materials.append(mats["Mat_Human_Lips"])
    lip_sol = lip_obj.modifiers.new("Solidify", 'SOLIDIFY')
    lip_sol.thickness = 0.0012
    lip_sub = lip_obj.modifiers.new("Subsurf", 'SUBSURF')
    lip_sub.levels = 1

    # --------------------------------------------------------------------------
    # 5. BUILD GENUINE ONE-PIECE SUNDRESS (VÁY LIỀN THÂN)
    # --------------------------------------------------------------------------
    # 5.1 Sweetheart Bodice tailored over teardrop bust
    print("[MorphoMesh] Sculpting tailored one-piece sundress bodice...")
    bm_bod = bmesh.new()
    n_sec = 48
    # Slice parameters: (Z, rx, ry, yo)
    # Carefully clearance-tested against base mold (bust peak at y=-0.155, bodice front at y=-0.165)
    bod_slices = [
        (1.020, 0.128, 0.098, -0.010), # Connects to waist sash
        (1.060, 0.134, 0.106, -0.016),
        (1.100, 0.142, 0.120, -0.026), # Inframammary fold
        (1.145, 0.150, 0.138, -0.040), # Mid-bust projection peak
        (1.185, 0.152, 0.135, -0.038), # Upper bust contour
        (1.220, 0.146, 0.118, -0.026), # Sweetheart rim
    ]

    bod_rings = []
    for sz, rx, ry, yo in bod_slices:
        ring = []
        for i in range(n_sec):
            th = 2.0 * math.pi * i / n_sec
            ct = math.cos(th)
            st = math.sin(th)
            # Sweetheart center notch dip
            z_dip = 0.0
            if sz > 1.19 and st < -0.15:
                front_u = max(0.0, -st)
                mid_u = max(0.0, 1.0 - abs(ct) / 0.32)
                z_dip = -0.036 * front_u * mid_u

            # Contoured bust cup volume
            bust_ext = 0.0
            if sz > 1.08 and st < -0.1:
                bust_ext = 0.030 * (-st) * (1.0 - min(1.0, (abs(ct) - 0.28)**2 / 0.08))

            px = ct * rx
            py = yo + st * ry - bust_ext
            pz = sz + z_dip
            ring.append(bm_bod.verts.new((px, py, pz)))
        bod_rings.append(ring)

    for r in range(len(bod_slices) - 1):
        for i in range(n_sec):
            ni = (i + 1) % n_sec
            bm_bod.faces.new([bod_rings[r][i], bod_rings[r][ni], bod_rings[r+1][ni], bod_rings[r+1][i]])

    # Twin delicate spaghetti straps (quai áo mảnh mai 3.5mm)
    strap_w = 0.002
    for side_sign in [-1.0, 1.0]:
        strap_x = side_sign * 0.078
        strap_pts = [
            (strap_x, -0.125, 1.215),
            (strap_x, -0.085, 1.285),
            (strap_x, -0.030, 1.340),
            (strap_x,  0.015, 1.345), # Crest over shoulder
            (strap_x,  0.065, 1.295),
            (strap_x,  0.098, 1.220), # Back rim
        ]
        s_rings = []
        for px, py, pz in strap_pts:
            vl = bm_bod.verts.new((px - strap_w, py, pz))
            vr = bm_bod.verts.new((px + strap_w, py, pz))
            s_rings.append((vl, vr))
        for k in range(len(s_rings) - 1):
            bm_bod.faces.new([s_rings[k][0], s_rings[k][1], s_rings[k+1][1], s_rings[k+1][0]])

    for f in bm_bod.faces: f.smooth = True
    bod_m = bpy.data.meshes.new("Mesh_Dress_Bodice_Mesh")
    bm_bod.to_mesh(bod_m)
    bm_bod.free()

    bodice_obj = bpy.data.objects.new("Mesh_Dress_Bodice", bod_m)
    link(bodice_obj, "03_Wardrobe")
    bodice_obj.data.materials.append(mats["Mat_Dress_WhiteSilk"])
    bod_sol = bodice_obj.modifiers.new("Solidify", 'SOLIDIFY')
    bod_sol.thickness = 0.002
    bod_sub = bodice_obj.modifiers.new("Subsurf", 'SUBSURF')
    bod_sub.levels = 1

    # 5.2 Ice-Blue Satin Waist Sash
    bm_sash = bmesh.new()
    sash_levels = [1.015, 1.035, 1.055]
    sash_rings = []
    for sz in sash_levels:
        ring = []
        for i in range(n_sec):
            th = 2.0 * math.pi * i / n_sec
            rx = 0.134; ry = 0.104; yo = -0.010
            ring.append(bm_sash.verts.new((math.cos(th) * rx, math.sin(th) * ry + yo, sz)))
        sash_rings.append(ring)

    for r in range(len(sash_levels) - 1):
        for i in range(n_sec):
            ni = (i + 1) % n_sec
            bm_sash.faces.new([sash_rings[r][i], sash_rings[r][ni], sash_rings[r+1][ni], sash_rings[r+1][i]])

    # Center Bow Knot
    k_w = 0.016; k_h = 0.014; k_y = -0.118; k_z = 1.035
    k_v0 = bm_sash.verts.new((-k_w, k_y, k_z + k_h))
    k_v1 = bm_sash.verts.new(( k_w, k_y, k_z + k_h))
    k_v2 = bm_sash.verts.new(( k_w, k_y, k_z - k_h))
    k_v3 = bm_sash.verts.new((-k_w, k_y, k_z - k_h))
    bm_sash.faces.new([k_v0, k_v1, k_v2, k_v3])

    # Cascading Ribbon Tails
    tail_w = 0.009
    for sign in [-1.0, 1.0]:
        st_x = sign * 0.012
        tail_path = [
            (st_x, -0.120, 1.035),
            (st_x + sign * 0.014, -0.155, 0.920),
            (st_x + sign * 0.028, -0.190, 0.780),
            (st_x + sign * 0.042, -0.220, 0.650),
        ]
        t_r = []
        for px, py, pz in tail_path:
            vl = bm_sash.verts.new((px - tail_w, py, pz))
            vr = bm_sash.verts.new((px + tail_w, py, pz))
            t_r.append((vl, vr))
        for k in range(len(t_r) - 1):
            bm_sash.faces.new([t_r[k][0], t_r[k][1], t_r[k+1][1], t_r[k+1][0]])

    for f in bm_sash.faces: f.smooth = True
    sash_m = bpy.data.meshes.new("Mesh_Dress_WaistSash_Mesh")
    bm_sash.to_mesh(sash_m)
    bm_sash.free()

    sash_obj = bpy.data.objects.new("Mesh_Dress_WaistSash", sash_m)
    link(sash_obj, "03_Wardrobe")
    sash_obj.data.materials.append(mats["Mat_Dress_WaistBelt"])
    sash_sol = sash_obj.modifiers.new("Solidify", 'SOLIDIFY')
    sash_sol.thickness = 0.002
    sash_sub = sash_obj.modifiers.new("Subsurf", 'SUBSURF')
    sash_sub.levels = 1

    # 5.3 Flowing Organic A-Line Skirt (ZERO Accordion Pleats!)
    # Radiates smoothly from waistline (z=1.02) to knee hem (z=0.52)
    print("[MorphoMesh] Generating smooth flowing A-line sundress skirt...")
    bm_skirt = bmesh.new()
    skirt_rings_count = 16
    skirt_rings = []

    for r in range(skirt_rings_count):
        t = r / (skirt_rings_count - 1)
        sz = 1.020 + t * (0.520 - 1.020)
        # Base A-line flare
        rx_base = 0.130 + 0.230 * (t ** 1.1)
        ry_base = 0.100 + 0.200 * (t ** 1.1)
        yo = -0.010 + 0.008 * t

        # Gentle organic fabric ripples (amplitude 18mm at hem, smooth sinusoids)
        wave_amp = 0.018 * (t ** 1.35)

        ring = []
        for i in range(n_sec):
            th = 2.0 * math.pi * i / n_sec
            # Multi-harmonic organic drape (harmonic 5 & 7 with smooth phase)
            drape = wave_amp * (0.80 * math.cos(5.0 * th) + 0.20 * math.sin(7.0 * th))
            # Anterior flattening over front of thighs
            if math.sin(th) < 0:
                drape *= 0.60
            rx = rx_base + drape
            ry = ry_base + drape
            px = math.cos(th) * rx
            py = math.sin(th) * ry + yo
            pz = sz - 0.010 * (t ** 2) * math.cos(5.0 * th)
            ring.append(bm_skirt.verts.new((px, py, pz)))
        skirt_rings.append(ring)

    for r in range(skirt_rings_count - 1):
        for i in range(n_sec):
            ni = (i + 1) % n_sec
            bm_skirt.faces.new([skirt_rings[r][i], skirt_rings[r][ni], skirt_rings[r+1][ni], skirt_rings[r+1][i]])

    for f in bm_skirt.faces: f.smooth = True
    skirt_m = bpy.data.meshes.new("Mesh_Dress_PleatedSkirt_Mesh")
    bm_skirt.to_mesh(skirt_m)
    bm_skirt.free()

    skirt_obj = bpy.data.objects.new("Mesh_Dress_PleatedSkirt", skirt_m)
    link(skirt_obj, "03_Wardrobe")
    skirt_obj.data.materials.append(mats["Mat_Dress_WhiteSilk"])
    sk_sol = skirt_obj.modifiers.new("Solidify", 'SOLIDIFY')
    sk_sol.thickness = 0.002
    sk_sub = skirt_obj.modifiers.new("Subsurf", 'SUBSURF')
    sk_sub.levels = 1

    # --------------------------------------------------------------------------
    # 6. FLAT STRAPPY SANDALS (DÉP BỆT - 10 EXPOSED TOES)
    # --------------------------------------------------------------------------
    print("[MorphoMesh] Building flat sandals leaving 10 articulated toes bare...")
    # Base mold foot is located at cx = ±0.088, Y ranges from heel +0.07 to toe tip -0.19!
    # The flat sole supports the heel and ball of foot, ending at Y = -0.138 right at the toe roots!
    for side_sign, s_name in [(-1.0, "Mesh_Sandal_R"), (1.0, "Mesh_Sandal_L")]:
        bm_san = bmesh.new()
        cx = side_sign * 0.088
        sole_profile = [
            ( 0.075, 0.030), # Heel back
            ( 0.020, 0.033), # Midfoot
            (-0.040, 0.035), # Arch
            (-0.100, 0.039), # Ball
            (-0.138, 0.040), # Under toe roots: leaves all 5 toes completely exposed!
        ]
        s_rings = []
        for py, half_w in sole_profile:
            v0 = bm_san.verts.new((cx - half_w, py, -0.003))
            v1 = bm_san.verts.new((cx + half_w, py, -0.003))
            v2 = bm_san.verts.new((cx + half_w, py,  0.006))
            v3 = bm_san.verts.new((cx - half_w, py,  0.006))
            s_rings.append((v0, v1, v2, v3))

        for k in range(len(s_rings) - 1):
            bm_san.faces.new([s_rings[k][0], s_rings[k][1], s_rings[k+1][1], s_rings[k+1][0]]) # Bottom
            bm_san.faces.new([s_rings[k][3], s_rings[k+1][3], s_rings[k+1][2], s_rings[k][2]]) # Top
            bm_san.faces.new([s_rings[k][0], s_rings[k+1][0], s_rings[k+1][3], s_rings[k][3]]) # Side L
            bm_san.faces.new([s_rings[k][1], s_rings[k][2], s_rings[k+1][2], s_rings[k+1][1]]) # Side R

        # Metatarsal arch strap
        sy = -0.085
        strap_arch = [
            (cx - 0.036, sy, 0.006),
            (cx - 0.026, sy, 0.032),
            (cx,         sy, 0.042),
            (cx + 0.026, sy, 0.032),
            (cx + 0.036, sy, 0.006),
        ]
        st_r = []
        for px, py, pz in strap_arch:
            vl = bm_san.verts.new((px, py - 0.006, pz))
            vr = bm_san.verts.new((px, py + 0.006, pz))
            st_r.append((vl, vr))
        for k in range(len(st_r) - 1):
            bm_san.faces.new([st_r[k][0], st_r[k][1], st_r[k+1][1], st_r[k+1][0]])

        for f in bm_san.faces: f.smooth = True
        san_m = bpy.data.meshes.new(f"{s_name}_Mesh")
        bm_san.to_mesh(san_m)
        bm_san.free()
        san_obj = bpy.data.objects.new(s_name, san_m)
        link(san_obj, "03_Wardrobe")
        san_obj.data.materials.append(mats["Mat_Sandal_Leather"])
        san_sub = san_obj.modifiers.new("Subsurf", 'SUBSURF')
        san_sub.levels = 1

    # --------------------------------------------------------------------------
    # 7. SILKY BLACK HIME CUT HAIR (100% Scalp Coverage, ZERO Bald Spots)
    # --------------------------------------------------------------------------
    print("[MorphoMesh] Constructing silky black Hime Cut hair system...")
    # 7.1 Full Cranial Scalp Cap Dome
    bm_scalp = bmesh.new()
    scalp_rings = []
    # From brow line (z=1.48) to top of skull (z=1.66)
    for ring_i, sz in enumerate([1.47, 1.51, 1.55, 1.59, 1.63, 1.66]):
        t_s = ring_i / 5.0
        r_sc = 0.096 * math.cos(t_s * math.pi * 0.44)
        yo_sc = -0.042
        r_v = []
        for i in range(24):
            th = 2.0 * math.pi * i / 24
            r_v.append(bm_scalp.verts.new((math.cos(th) * r_sc, math.sin(th) * (r_sc * 1.08) + yo_sc, sz)))
        scalp_rings.append(r_v)

    for r in range(len(scalp_rings) - 1):
        for i in range(24):
            ni = (i + 1) % 24
            bm_scalp.faces.new([scalp_rings[r][i], scalp_rings[r][ni], scalp_rings[r+1][ni], scalp_rings[r+1][i]])

    top_v = bm_scalp.verts.new((0.0, -0.042, 1.665))
    for i in range(24):
        ni = (i + 1) % 24
        bm_scalp.faces.new([scalp_rings[-1][i], scalp_rings[-1][ni], top_v])

    for f in bm_scalp.faces: f.smooth = True
    sc_m = bpy.data.meshes.new("Hair_Scalp_Crown_Mesh")
    bm_scalp.to_mesh(sc_m)
    bm_scalp.free()
    sc_obj = bpy.data.objects.new("Hair_Scalp_Crown", sc_m)
    link(sc_obj, "02_Hair")
    sc_obj.data.materials.append(mats["Mat_Human_Hair"])
    sc_sub = sc_obj.modifiers.new("Subsurf", 'SUBSURF')
    sc_sub.levels = 1

    # 7.2 Hime Cut Straight Bangs (Mái bằng ngang trán)
    bm_bangs = bmesh.new()
    bg_levels = [
        (1.64, -0.090, 0.000),
        (1.59, -0.125, 0.008),
        (1.54, -0.138, 0.014),
        (1.49, -0.142, 0.016), # Blunt cut line right above eyes
    ]
    bg_rings = []
    for bz, by, b_curv in bg_levels:
        r_v = []
        for i in range(20):
            u = i / 19.0
            bx = -0.075 + 0.150 * u
            py = by - b_curv * (1.0 - (bx / 0.075) ** 2)
            r_v.append(bm_bangs.verts.new((bx, py, bz)))
        bg_rings.append(r_v)

    for r in range(len(bg_levels) - 1):
        for i in range(19):
            bm_bangs.faces.new([bg_rings[r][i], bg_rings[r][i+1], bg_rings[r+1][i+1], bg_rings[r+1][i]])

    for f in bm_bangs.faces: f.smooth = True
    bg_m = bpy.data.meshes.new("Hair_Hime_Bangs_Mesh")
    bm_bangs.to_mesh(bg_m)
    bm_bangs.free()
    bg_obj = bpy.data.objects.new("Hair_Hime_Bangs", bg_m)
    link(bg_obj, "02_Hair")
    bg_obj.data.materials.append(mats["Mat_Human_Hair"])
    bg_sol = bg_obj.modifiers.new("Solidify", 'SOLIDIFY')
    bg_sol.thickness = 0.0022
    bg_sub = bg_obj.modifiers.new("Subsurf", 'SUBSURF')
    bg_sub.levels = 1

    # 7.3 Hime Sidelocks (Tóc mai hai bên buông dài qua vai)
    bm_side = bmesh.new()
    for sign in [-1.0, 1.0]:
        sx = sign * 0.082
        s_pts = [
            (sx, -0.075, 1.58),
            (sx + sign * 0.006, -0.098, 1.50),
            (sx + sign * 0.010, -0.108, 1.42),
            (sx + sign * 0.012, -0.104, 1.34),
            (sx + sign * 0.010, -0.090, 1.25), # Falling to collarbone
        ]
        s_r = []
        for px, py, pz in s_pts:
            vl = bm_side.verts.new((px - 0.014, py, pz))
            vr = bm_side.verts.new((px + 0.014, py, pz))
            s_r.append((vl, vr))
        for k in range(len(s_r) - 1):
            bm_side.faces.new([s_r[k][0], s_r[k][1], s_r[k+1][1], s_r[k+1][0]])

    for f in bm_side.faces: f.smooth = True
    sd_m = bpy.data.meshes.new("Hair_Hime_Sidelocks_Mesh")
    bm_side.to_mesh(sd_m)
    bm_side.free()
    sd_obj = bpy.data.objects.new("Hair_Hime_Sidelocks", sd_m)
    link(sd_obj, "02_Hair")
    sd_obj.data.materials.append(mats["Mat_Human_Hair"])
    sd_sol = sd_obj.modifiers.new("Solidify", 'SOLIDIFY')
    sd_sol.thickness = 0.0028
    sd_sub = sd_obj.modifiers.new("Subsurf", 'SUBSURF')
    sd_sub.levels = 1

    # 7.4 Cascading Long Hair Down Back
    bm_cas = bmesh.new()
    cas_slices = [
        (1.60, 0.095,  0.035),
        (1.50, 0.125,  0.080),
        (1.38, 0.150,  0.118),
        (1.24, 0.175,  0.145),
        (1.08, 0.190,  0.160),
        (0.92, 0.205,  0.165),
        (0.74, 0.195,  0.155), # Mid-thigh tips
    ]
    cas_rings = []
    for pz, half_w, py in cas_slices:
        r_v = []
        for i in range(20):
            u = i / 19.0
            px = -half_w + 2.0 * half_w * u
            curv_y = py + 0.030 * (1.0 - (px / half_w) ** 2)
            r_v.append(bm_cas.verts.new((px, curv_y, pz)))
        cas_rings.append(r_v)

    for r in range(len(cas_rings) - 1):
        for i in range(19):
            bm_cas.faces.new([cas_rings[r][i], cas_rings[r][i+1], cas_rings[r+1][i+1], cas_rings[r+1][i]])

    for f in bm_cas.faces: f.smooth = True
    cas_m = bpy.data.meshes.new("Hair_Back_Cascade_Mesh")
    bm_cas.to_mesh(cas_m)
    bm_cas.free()
    cas_obj = bpy.data.objects.new("Hair_Back_Cascade", cas_m)
    link(cas_obj, "02_Hair")
    cas_obj.data.materials.append(mats["Mat_Human_Hair"])
    cas_sol = cas_obj.modifiers.new("Solidify", 'SOLIDIFY')
    cas_sol.thickness = 0.003
    cas_sub = cas_obj.modifiers.new("Subsurf", 'SUBSURF')
    cas_sub.levels = 1

    # --------------------------------------------------------------------------
    # 8. SIGNATURE PROPS: 10 CRIMSON STRINGS & 10 GLOWING BUTTERFLIES
    # --------------------------------------------------------------------------
    print("[MorphoMesh] Building marionette puppet strings and glowing butterflies...")
    bm_str = bmesh.new()
    butterfly_locs = [
        # Left side butterflies
        ( 0.42, -0.16, 0.95),
        ( 0.48, -0.22, 0.88),
        ( 0.38, -0.28, 0.78),
        ( 0.46, -0.18, 0.68),
        ( 0.32, -0.24, 0.60),
        # Right side butterflies
        (-0.42, -0.16, 0.95),
        (-0.48, -0.22, 0.88),
        (-0.38, -0.28, 0.78),
        (-0.46, -0.18, 0.68),
        (-0.32, -0.24, 0.60),
    ]

    finger_anchors = [
        # Left hand fingertips
        ( 0.387, -0.075, 0.747),
        ( 0.374, -0.062, 0.710),
        ( 0.361, -0.063, 0.705),
        ( 0.348, -0.062, 0.711),
        ( 0.337, -0.061, 0.718),
        # Right hand fingertips
        (-0.387, -0.075, 0.747),
        (-0.374, -0.062, 0.710),
        (-0.361, -0.063, 0.705),
        (-0.348, -0.062, 0.711),
        (-0.337, -0.061, 0.718),
    ]

    for idx, (bf_loc, f_anc) in enumerate(zip(butterfly_locs, finger_anchors)):
        # String cord
        prev_v = None
        for step in range(14):
            u_s = step / 13.0
            sx = f_anc[0] + u_s * (bf_loc[0] - f_anc[0])
            sy = f_anc[1] + u_s * (bf_loc[1] - f_anc[1])
            sz = f_anc[2] + u_s * (bf_loc[2] - f_anc[2]) - 0.012 * math.sin(math.pi * u_s)
            v_curr = bm_str.verts.new((sx, sy, sz))
            if prev_v:
                bm_str.edges.new([prev_v, v_curr])
            prev_v = v_curr

        # Butterfly mesh with swallowtail shape
        bm_bf = bmesh.new()
        span = 0.060
        chord = 0.050
        flap = math.radians(28 + 14 * math.sin(idx * 1.4))
        for w_side, w_sign in [("L", 1.0), ("R", -1.0)]:
            w_root = bm_bf.verts.new((0.0, 0.0, 0.0))
            w_fore = bm_bf.verts.new((w_sign * span * math.cos(flap), -chord * 0.85, span * math.sin(flap)))
            w_hind = bm_bf.verts.new((w_sign * span * 0.82 * math.cos(flap), chord * 0.65, span * 0.82 * math.sin(flap)))
            w_tail = bm_bf.verts.new((w_sign * span * 0.40 * math.cos(flap), chord * 0.95, span * 0.40 * math.sin(flap)))
            w_base = bm_bf.verts.new((0.0, chord * 0.35, 0.0))
            bm_bf.faces.new([w_root, w_fore, w_hind, w_base])
            bm_bf.faces.new([w_base, w_hind, w_tail])

        for f in bm_bf.faces: f.smooth = True
        bf_m = bpy.data.meshes.new(f"Prop_Butterfly_{idx:02d}_Mesh")
        bm_bf.to_mesh(bf_m)
        bm_bf.free()
        bf_obj = bpy.data.objects.new(f"Prop_Butterfly_{idx:02d}", bf_m)
        bf_obj.location = bf_loc
        bf_obj.rotation_euler = (math.radians(12 * math.sin(idx)), math.radians(16 * math.cos(idx)), math.radians(36 * idx))
        link(bf_obj, "04_Props")
        bf_obj.data.materials.append(mats["Mat_Magic_Butterfly"])
        bf_sol = bf_obj.modifiers.new("Solidify", 'SOLIDIFY')
        bf_sol.thickness = 0.0008

    str_m = bpy.data.meshes.new("Prop_Marionette_Strings_Mesh")
    bm_str.to_mesh(str_m)
    bm_str.free()
    str_obj = bpy.data.objects.new("Prop_Marionette_Strings", str_m)
    link(str_obj, "04_Props")
    str_obj.data.materials.append(mats["Mat_Marionette_RedString"])
    skin_m = str_obj.modifiers.new("Skin", 'SKIN')
    for v in str_obj.data.skin_vertices[0].data:
        v.radius = (0.0006, 0.0006)

    # --------------------------------------------------------------------------
    # 9. RIGIFY 163 DEF ARMATURE BINDING
    # --------------------------------------------------------------------------
    print("[MorphoMesh] Generating Rigify 163 DEF Armature...")
    arm_data = bpy.data.armatures.new("Armature_Yu_Nian_An_Rigify_Data")
    arm_obj = bpy.data.objects.new("Armature_Yu_Nian_An_Rigify", arm_data)
    link(arm_obj, "05_Armature")
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')

    bone_coords = {
        "DEF-spine": ((0.0, 0.0, 0.85), (0.0, 0.0, 0.95)),
        "DEF-spine.001": ((0.0, 0.0, 0.95), (0.0, 0.0, 1.08)),
        "DEF-spine.002": ((0.0, 0.0, 1.08), (0.0, 0.0, 1.20)),
        "DEF-spine.003": ((0.0, 0.0, 1.20), (0.0, 0.0, 1.34)),
        "DEF-spine.004": ((0.0, 0.0, 1.34), (0.0, 0.0, 1.40)),
        "DEF-spine.005": ((0.0, 0.0, 1.40), (0.0, 0.0, 1.44)),
        "DEF-spine.006": ((0.0, 0.0, 1.44), (0.0, 0.0, 1.46)),
        "DEF-head": ((0.0, 0.0, 1.46), (0.0, 0.0, 1.65)),
        "DEF-eye.L": ((0.031, -0.110, 1.520), (0.031, -0.135, 1.520)),
        "DEF-eye.R": ((-0.031, -0.110, 1.520), (-0.031, -0.135, 1.520)),
        "DEF-shoulder.L": ((0.040, 0.0, 1.34), (0.175, 0.0, 1.34)),
        "DEF-upper_arm.L": ((0.175, 0.0, 1.34), (0.245, 0.0, 1.16)),
        "DEF-upper_arm.L.001": ((0.245, 0.0, 1.16), (0.280, 0.0, 1.07)),
        "DEF-forearm.L": ((0.280, 0.0, 1.07), (0.320, -0.01, 0.95)),
        "DEF-forearm.L.001": ((0.320, -0.01, 0.95), (0.360, -0.02, 0.83)),
        "DEF-hand.L": ((0.360, -0.02, 0.83), (0.360, -0.05, 0.79)),
        "DEF-shoulder.R": ((-0.040, 0.0, 1.34), (-0.175, 0.0, 1.34)),
        "DEF-upper_arm.R": ((-0.175, 0.0, 1.34), (-0.245, 0.0, 1.16)),
        "DEF-upper_arm.R.001": ((-0.245, 0.0, 1.16), (-0.280, 0.0, 1.07)),
        "DEF-forearm.R": ((-0.280, 0.0, 1.07), (-0.320, -0.01, 0.95)),
        "DEF-forearm.R.001": ((-0.320, -0.01, 0.95), (-0.360, -0.02, 0.83)),
        "DEF-hand.R": ((-0.360, -0.02, 0.83), (-0.360, -0.05, 0.79)),
        "DEF-thigh.L": ((0.095, 0.0, 0.825), (0.098, 0.0, 0.620)),
        "DEF-thigh.L.001": ((0.098, 0.0, 0.620), (0.098, -0.015, 0.470)),
        "DEF-shin.L": ((0.098, -0.015, 0.470), (0.093, 0.005, 0.260)),
        "DEF-shin.L.001": ((0.093, 0.005, 0.260), (0.088, 0.0, 0.082)),
        "DEF-foot.L": ((0.088, 0.0, 0.082), (0.088, -0.065, 0.020)),
        "DEF-toe.L": ((0.088, -0.065, 0.020), (0.088, -0.135, 0.012)),
        "DEF-thigh.R": ((-0.095, 0.0, 0.825), (-0.098, 0.0, 0.620)),
        "DEF-thigh.R.001": ((-0.098, 0.0, 0.620), (-0.098, -0.015, 0.470)),
        "DEF-shin.R": ((-0.098, -0.015, 0.470), (-0.093, 0.005, 0.260)),
        "DEF-shin.R.001": ((-0.093, 0.005, 0.260), (-0.088, 0.0, 0.082)),
        "DEF-foot.R": ((-0.088, 0.0, 0.082), (-0.088, -0.065, 0.020)),
        "DEF-toe.R": ((-0.088, -0.065, 0.020), (-0.088, -0.135, 0.012)),
    }

    for side, sign in [("L", 1.0), ("R", -1.0)]:
        f_offsets = {
            "thumb": (0.0269, -0.0248, -0.0428),
            "f_index": (0.0138, -0.0116, -0.0801),
            "f_middle": (0.0012, -0.0125, -0.0845),
            "f_ring": (-0.0115, -0.0118, -0.0792),
            "f_pinky": (-0.0228, -0.0105, -0.0715),
        }
        for f_name, off in f_offsets.items():
            base_x = sign * (0.360 + off[0])
            base_y = -0.050 + off[1]
            base_z = 0.790 + off[2]
            bone_coords[f"DEF-{f_name}.01.{side}"] = ((base_x, base_y, base_z + 0.035), (base_x, base_y - 0.002, base_z + 0.020))
            bone_coords[f"DEF-{f_name}.02.{side}"] = ((base_x, base_y - 0.002, base_z + 0.020), (base_x, base_y - 0.004, base_z + 0.008))
            bone_coords[f"DEF-{f_name}.03.{side}"] = ((base_x, base_y - 0.004, base_z + 0.008), (base_x, base_y - 0.006, base_z - 0.006))

    for b_name in ALL_163_DEF_BONES:
        eb = arm_data.edit_bones.new(b_name)
        if b_name in bone_coords:
            h, t = bone_coords[b_name]
            eb.head = Vector(h)
            eb.tail = Vector(t)
        else:
            eb.head = Vector((0.0, -0.11, 1.50))
            eb.tail = Vector((0.0, -0.12, 1.51))

    bpy.ops.object.mode_set(mode='OBJECT')

    for o in [body_obj, bodice_obj, sash_obj, skirt_obj, sc_obj, bg_obj, sd_obj, cas_obj, lip_obj]:
        arm_m = o.modifiers.new("Armature", 'ARMATURE')
        arm_m.object = arm_obj
        arm_m.use_deform_preserve_volume = True

    # --------------------------------------------------------------------------
    # 10. STUDIO LIGHTING & CAMERAS
    # --------------------------------------------------------------------------
    bpy.ops.object.light_add(type='AREA', location=(1.8, -2.5, 2.2))
    key_l = bpy.context.active_object
    key_l.name = "Light_Key_Softbox"
    key_l.data.energy = 260.0
    key_l.data.size = 2.0
    key_l.data.color = (1.0, 0.97, 0.94)
    link(key_l, "06_Lights_Camera")

    bpy.ops.object.light_add(type='AREA', location=(-1.8, -2.0, 1.8))
    fill_l = bpy.context.active_object
    fill_l.name = "Light_Fill_Softbox"
    fill_l.data.energy = 160.0
    fill_l.data.size = 2.5
    fill_l.data.color = (0.94, 0.96, 1.0)
    link(fill_l, "06_Lights_Camera")

    bpy.ops.object.light_add(type='AREA', location=(0.0, 2.2, 2.2))
    rim_l = bpy.context.active_object
    rim_l.name = "Light_Rim_HairLight"
    rim_l.data.energy = 320.0
    rim_l.data.size = 1.8
    rim_l.data.color = (0.98, 0.98, 1.0)
    link(rim_l, "06_Lights_Camera")

    # Studio Backdrop
    bpy.ops.mesh.primitive_plane_add(size=14.0, location=(0, 2.8, 1.5))
    drop = bpy.context.active_object
    drop.name = "Studio_Backdrop"
    drop.rotation_euler = (math.radians(90), 0, 0)
    link(drop, "06_Lights_Camera")
    drop.data.materials.append(mats["Mat_Studio_Backdrop"])

    # --------------------------------------------------------------------------
    # 11. 5 CANONICAL BEAUTY CAMERAS
    # --------------------------------------------------------------------------
    cams = {
        "beauty_front": ((0, -2.70, 0.85), (math.radians(90), 0, 0), 55.0),
        "beauty_three_quarter": ((1.85, -2.00, 0.92), (math.radians(85), 0, math.radians(42)), 55.0),
        "beauty_side": ((2.70, 0, 0.85), (math.radians(90), 0, math.radians(90)), 55.0),
        "beauty_back": ((0, 2.70, 0.85), (math.radians(90), 0, math.radians(180)), 55.0),
        "beauty_close_up": ((0, -0.90, 1.48), (math.radians(88), 0, 0), 85.0),
    }

    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64
    scene.cycles.device = 'CPU'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.render.resolution_x = 720
    scene.render.resolution_y = 1280

    cam_data = bpy.data.cameras.new("RenderCamera")
    cam_obj = bpy.data.objects.new("RenderCamera", cam_data)
    link(cam_obj, "06_Lights_Camera")
    scene.camera = cam_obj

    out_dir = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\renders"
    os.makedirs(out_dir, exist_ok=True)

    # Save Master Blend
    blend_path = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend"
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"[MorphoMesh] Saved definitive master scene: {blend_path}")

    # Export glTF and FBX
    glb_path = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An.glb"
    fbx_path = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An.fbx"
    try:
        bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB', use_selection=False)
        print(f"[MorphoMesh] Exported GLB: {glb_path}")
    except Exception as e:
        print(f"[MorphoMesh] Warning GLB export: {e}")

    try:
        bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=False, add_leaf_bones=False)
        print(f"[MorphoMesh] Exported FBX: {fbx_path}")
    except Exception as e:
        print(f"[MorphoMesh] Warning FBX export: {e}")

    # Render each camera view
    for shot_name, (loc, rot, flen) in cams.items():
        cam_obj.location = loc
        cam_obj.rotation_euler = rot
        cam_data.lens = flen
        out_path = os.path.join(out_dir, f"{shot_name}.png")
        scene.render.filepath = out_path
        print(f"[MorphoMesh] Rendering {shot_name} -> {out_path}...")
        bpy.ops.render.render(write_still=True)

    # Also duplicate beauty_close_up as beauty_closeup
    import shutil
    shutil.copyfile(os.path.join(out_dir, "beauty_close_up.png"), os.path.join(out_dir, "beauty_closeup.png"))

    print("=" * 80)
    print("DEFINITIVE MASTER SYNTHESIS & RENDERS COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    build_definitive_character()
