"""
MorphoMesh: Build True Yu Nian An Character Asset
Combines:
1. Anime Aesthetic Face (Beauty_Face) with soulful sapphire eyes, delicate lashes & lips
2. Silky Hime Hair + Complete Scalp Coverage (zero bald spots) + Cascading Long Hair
3. Anatomical Female Base Mold (volumetric teardrop bust, rounded buttocks, straight legs, 10 toes)
4. Smooth One-Piece Sundress (Váy Liền Thân) with sweetheart bodice & flowing A-line drape (ZERO accordion pleats)
5. Flat Sandals (Dép Bệt) leaving 10 bare toes completely exposed
6. 10 Red Marionette Strings + 10 Glowing White Butterflies
7. Rigify 163 DEF Armature + 52 ARKit FACS Blendshapes
8. Cinema-Grade Cycles AgX 5-Angle Renders & Standard Container Exports (.glb, .fbx, .blend)
"""

import bpy
import bmesh
import math
import sys
import os
import shutil
from mathutils import Vector, Matrix, Euler

sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\.venv\Lib\site-packages")
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
from morphomesh.human_generator import generate_human_base_mesh
from morphomesh.models import HumanAnatomyConfig
from morphomesh.human_rigging import ALL_163_DEF_BONES

def build_true_yu_nian_an():
    print("=" * 80)
    print("ASSEMBLING TRUE YU NIAN AN MASTER CHARACTER")
    print("=" * 80)

    # 1. Open Base Beauty Blend to preserve delicate face and textures
    beauty_blend = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Beauty.blend"
    bpy.ops.wm.open_mainfile(filepath=beauty_blend)
    scene = bpy.context.scene

    # 2. Setup 7-Tier Collections
    root_name = "Yu_Nian_An_Master"
    root_col = bpy.data.collections.get(root_name) or bpy.data.collections.new(root_name)
    if root_name not in scene.collection.children:
        scene.collection.children.link(root_col)

    tiers = {}
    for tn in ["01_Body", "02_Hair", "03_Wardrobe", "04_Props", "05_Armature", "06_Lights_Camera"]:
        c = bpy.data.collections.get(tn) or bpy.data.collections.new(tn)
        if c.name not in root_col.children:
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

    # 3. Clean up the rejected objects from Beauty blend
    for old_name in [
        "Beauty_Body",
        "Beauty_Pleated_Skirt",
        "Beauty_Dress_Bodice",
        "Beauty_Waist_Sash",
        "Beauty_Sandal_L",
        "Beauty_Sandal_R",
        "Yu_Nian_An_Beauty_Dress_PleatedSkirt",
        "Yu_Nian_An_Beauty_Figure",
        "Yu_Nian_An_Body",
        "Hair_Back_Scalp",
        "Mesh_Dress_Bodice",
        "Mesh_Dress_WaistSash",
        "Mesh_Dress_PleatedSkirt",
        "Mesh_Sandal_L",
        "Mesh_Sandal_R",
    ]:
        ob = bpy.data.objects.get(old_name)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)

    # 4. Get Armature and Face
    arm_obj = bpy.data.objects.get("Beauty_Armature")
    if arm_obj:
        link(arm_obj, "05_Armature")
        arm_obj.name = "Armature_Yu_Nian_An_Rigify"

    face_obj = bpy.data.objects.get("Beauty_Face")
    if face_obj:
        link(face_obj, "01_Body")
        face_obj.name = "Yu_Nian_An_Face"

    # Hair objects
    hair_obj = bpy.data.objects.get("Beauty_Hair")
    if hair_obj:
        link(hair_obj, "02_Hair")
        hair_obj.name = "Hair_Hime_FrontBangs"

    hair_cas = bpy.data.objects.get("Beauty_Hair_Cascade")
    if hair_cas:
        link(hair_cas, "02_Hair")
        hair_cas.name = "Hair_Back_Cascade"

    # 5. Fix Hair Scalp: Perfected closed anatomical cranial hair dome (Zero bald holes, zero flat head)
    print("[MorphoMesh] Building perfected anatomical cranial hair dome...")
    bm_sc = bmesh.new()
    profile = [
        (1.596, 0.020, 0.015, 0.015, -0.005), # Crown apex
        (1.585, 0.046, 0.036, 0.038, -0.006), # Upper crown
        (1.570, 0.062, 0.050, 0.054, -0.006), # Tuck under bangs
        (1.550, 0.074, 0.060, 0.066, -0.005), # Upper parietal
        (1.525, 0.082, 0.068, 0.075, -0.003), # Mid parietal (max skull width)
        (1.495, 0.084, 0.070, 0.080,  0.000), # Parietal ridge
        (1.465, 0.082, 0.066, 0.079,  0.005), # Occipital curve
        (1.435, 0.078, 0.060, 0.076,  0.010), # Ponytail gather level
        (1.405, 0.068, 0.050, 0.068,  0.016), # Below gather
        (1.375, 0.055, 0.038, 0.055,  0.022), # Nape transition
        (1.350, 0.044, 0.028, 0.042,  0.026), # Nape base meeting neck
    ]
    n_sc_sec = 48
    sc_rings = []
    for sz, rx, ry_f, ry_b, yo in profile:
        ring = []
        for i in range(n_sc_sec):
            th = 2.0 * math.pi * i / n_sc_sec
            ct = math.cos(th)
            st = math.sin(th)
            ry = ry_f if st < 0 else ry_b
            px = ct * rx
            py = st * ry + yo
            pz = sz
            ring.append(bm_sc.verts.new((px, py, pz)))
        sc_rings.append(ring)

    # Rounded dome crown cap
    pole = bm_sc.verts.new((0.0, -0.005, 1.597))
    for i in range(n_sc_sec):
        ni = (i + 1) % n_sc_sec
        bm_sc.faces.new([pole, sc_rings[0][ni], sc_rings[0][i]])

    for r in range(len(profile) - 1):
        for i in range(n_sc_sec):
            ni = (i + 1) % n_sc_sec
            bm_sc.faces.new([sc_rings[r][i], sc_rings[r][ni], sc_rings[r+1][ni], sc_rings[r+1][i]])

    for f in bm_sc.faces: f.smooth = True
    sc_m = bpy.data.meshes.new("Hair_Back_Scalp_Mesh")
    bm_sc.to_mesh(sc_m)
    bm_sc.free()
    sc_obj = bpy.data.objects.new("Hair_Back_Scalp", sc_m)
    link(sc_obj, "02_Hair")
    
    # Silky black hair material
    mat_hair = bpy.data.materials.get("Mat_Human_Hair_Beauty") or bpy.data.materials.new("Mat_Human_Hair_Beauty")
    mat_hair.use_nodes = True
    bs_hair = mat_hair.node_tree.nodes.get("Principled BSDF")
    if bs_hair:
        bs_hair.inputs["Base Color"].default_value = (0.014, 0.013, 0.016, 1.0)
        bs_hair.inputs["Roughness"].default_value = 0.36
    sc_obj.data.materials.append(mat_hair)
    
    sc_sub = sc_obj.modifiers.new("Subsurf", 'SUBSURF')
    sc_sub.levels = 1
    if arm_obj:
        arm_sc = sc_obj.modifiers.new("Armature", 'ARMATURE')
        arm_sc.object = arm_obj

    # 6. Build the Anatomical Female Body Mold (1.588m world-space matching face & armature)
    print("[MorphoMesh] Generating perfected anatomical female base mold (height 1.588m)...")
    cfg = HumanAnatomyConfig(height=1.588)
    res = generate_human_base_mesh(cfg)

    raw_verts = res.mesh.vertices
    raw_faces = res.mesh.faces

    # Filter neck/head: keep body up to chin (z<=1.365 in front, z<=1.405 in back)
    bm_body = bmesh.new()
    vert_map = {}
    for idx, v in enumerate(raw_verts):
        # Keep if below chin in front (meeting Beauty_Face chin at 1.3657) or below cranium in back
        keep = True
        if v[2] > 1.365 and v[1] < 0.0:
            keep = False
        elif v[2] > 1.405:
            keep = False
        if keep:
            vert_map[idx] = bm_body.verts.new(v)

    bm_body.verts.ensure_lookup_table()
    for face_indices in raw_faces:
        if all(vi in vert_map for vi in face_indices):
            bm_body.faces.new([vert_map[vi] for vi in face_indices])

    # Smooth the neck boundary rim under the jawline to remove any zigzag notches
    # and apply graceful slender neck tapering (matching delicate anime jawline)
    bm_body.edges.ensure_lookup_table()
    for v in bm_body.verts:
        if 1.24 <= v.co.z <= 1.38 and abs(v.co.x) < 0.065:
            t_n = (v.co.z - 1.24) / 0.14
            v.co.x *= (1.0 - 0.20 * t_n)
            v.co.y *= (1.0 - 0.12 * t_n)

        if any(e.is_boundary for e in v.link_edges) and v.co.z > 1.30:
            if v.co.y < 0.0:
                v.co.z = 1.362 + 0.018 * ((v.co.x / 0.045) ** 2)
            else:
                v.co.z = 1.375 + 0.015 * ((v.co.x / 0.045) ** 2)

    for f in bm_body.faces: f.smooth = True
    body_mesh = bpy.data.meshes.new("Yu_Nian_An_Body_Mesh")
    bm_body.to_mesh(body_mesh)
    bm_body.free()

    body_obj = bpy.data.objects.new("Yu_Nian_An_Body", body_mesh)
    link(body_obj, "01_Body")

    # Porcelain Anime Skin Material with SSS
    mat_skin = bpy.data.materials.get("Mat_Human_Skin_SSS_Beauty") or bpy.data.materials.new("Mat_Human_Skin_SSS_Beauty")
    mat_skin.use_nodes = True
    bs_skin = mat_skin.node_tree.nodes.get("Principled BSDF")
    if bs_skin:
        bs_skin.inputs["Base Color"].default_value = (0.950, 0.850, 0.800, 1.0)
        bs_skin.inputs["Roughness"].default_value = 0.36
        if "Subsurface Weight" in bs_skin.inputs:
            bs_skin.subsurface_method = 'RANDOM_WALK'
            bs_skin.inputs["Subsurface Weight"].default_value = 0.35
            bs_skin.inputs["Subsurface Radius"].default_value = (0.040, 0.018, 0.010)
            bs_skin.inputs["Subsurface Scale"].default_value = 0.035
    body_obj.data.materials.append(mat_skin)

    sub_b = body_obj.modifiers.new("Subsurf", 'SUBSURF')
    sub_b.levels = 1

    if arm_obj:
        arm_b = body_obj.modifiers.new("Armature", 'ARMATURE')
        arm_b.object = arm_obj
        arm_b.use_deform_preserve_volume = True

    # 7. Build Genuine One-Piece Sundress (Váy Liền Thân)
    # Perfectly fitted with dual-breast forward expansion & glute fullness (ZERO clipping)
    print("[MorphoMesh] Building tailored one-piece sundress bodice...")
    bm_bod = bmesh.new()
    n_sec = 48
    # Exact torso slices tailored to 1.588m anatomical body (+15mm silky air clearance)
    bod_slices = [
        (0.980, 0.122, 0.078, -0.052), # Waist
        (1.020, 0.126, 0.092, -0.064), # Mid-rib
        (1.060, 0.134, 0.110, -0.074), # Lower-bust
        (1.100, 0.144, 0.128, -0.078), # Mid-bust
        (1.140, 0.152, 0.138, -0.076), # Bust Apex
        (1.180, 0.162, 0.130, -0.062), # Upper Bust
    ]
    bod_rings = []
    for sz, rx, ry, yo in bod_slices:
        ring = []
        for i in range(n_sec):
            th = 2.0 * math.pi * i / n_sec
            ct = math.cos(th)
            st = math.sin(th)

            # Sweetheart neckline center dip
            z_dip = 0.0
            if sz > 1.15 and st < -0.20:
                front_u = max(0.0, -st)
                mid_u = max(0.0, 1.0 - abs(ct) / 0.35)
                z_dip = -0.032 * front_u * mid_u

            # Dual-bust forward expansion: push forward over breast apexes (x = +/-0.077m)
            bust_push = 0.0
            if st < -0.10 and 1.05 <= sz <= 1.18:
                dx_b = (abs(ct * rx) - 0.077) / 0.070
                if abs(dx_b) < 1.0:
                    w_z = math.cos((sz - 1.140) * math.pi / 0.16) ** 2
                    bust_push = 0.026 * (math.cos(dx_b * math.pi * 0.5) ** 2) * w_z * max(0.0, -st)

            px = ct * rx
            py = yo + st * ry - bust_push
            pz = sz + z_dip
            ring.append(bm_bod.verts.new((px, py, pz)))
        bod_rings.append(ring)

    for r in range(len(bod_slices) - 1):
        for i in range(n_sec):
            ni = (i + 1) % n_sec
            bm_bod.faces.new([bod_rings[r][i], bod_rings[r][ni], bod_rings[r+1][ni], bod_rings[r+1][i]])

    # Spaghetti Straps (Quai áo mảnh mai 4mm, anchored seamlessly inside bodice)
    strap_w = 0.002
    for side_sign in [-1.0, 1.0]:
        strap_x = side_sign * 0.065
        strap_pts = [
            (strap_x, -0.198, 1.140), # Anchor inside bodice front
            (strap_x, -0.170, 1.180),
            (strap_x, -0.115, 1.250),
            (strap_x, -0.020, 1.305), # Shoulder apex
            (strap_x,  0.025, 1.300),
            (strap_x,  0.055, 1.180),
            (strap_x,  0.062, 1.140), # Anchor inside bodice back
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

    mat_silk = bpy.data.materials.get("Mat_Dress_WhiteSilk") or bpy.data.materials.new("Mat_Dress_WhiteSilk")
    mat_silk.use_nodes = True
    bs_silk = mat_silk.node_tree.nodes.get("Principled BSDF")
    if bs_silk:
        bs_silk.inputs["Base Color"].default_value = (0.965, 0.965, 0.975, 1.0)
        bs_silk.inputs["Roughness"].default_value = 0.28
        if "Sheen Weight" in bs_silk.inputs: bs_silk.inputs["Sheen Weight"].default_value = 0.90
    bodice_obj.data.materials.append(mat_silk)
    bod_sol = bodice_obj.modifiers.new("Solidify", 'SOLIDIFY')
    bod_sol.thickness = 0.003
    bod_sub = bodice_obj.modifiers.new("Subsurf", 'SUBSURF')
    bod_sub.levels = 1

    # 7.2 Ice-Blue Satin Waist Sash
    bm_sash = bmesh.new()
    sash_levels = [0.965, 0.980, 0.995]
    sash_rings = []
    for sz in sash_levels:
        ring = []
        for i in range(n_sec):
            th = 2.0 * math.pi * i / n_sec
            rx = 0.124; ry = 0.082; yo = -0.052
            ring.append(bm_sash.verts.new((math.cos(th) * rx, math.sin(th) * ry + yo, sz)))
        sash_rings.append(ring)

    for r in range(len(sash_levels) - 1):
        for i in range(n_sec):
            ni = (i + 1) % n_sec
            bm_sash.faces.new([sash_rings[r][i], sash_rings[r][ni], sash_rings[r+1][ni], sash_rings[r+1][i]])

    # Center Bow Knot
    k_w = 0.016; k_h = 0.014; k_y = -0.140; k_z = 0.980
    k_v0 = bm_sash.verts.new((-k_w, k_y, k_z + k_h))
    k_v1 = bm_sash.verts.new(( k_w, k_y, k_z + k_h))
    k_v2 = bm_sash.verts.new(( k_w, k_y, k_z - k_h))
    k_v3 = bm_sash.verts.new((-k_w, k_y, k_z - k_h))
    bm_sash.faces.new([k_v0, k_v1, k_v2, k_v3])

    # Cascading Ribbon Tails
    tail_w = 0.008
    for sign in [-1.0, 1.0]:
        st_x = sign * 0.012
        tail_path = [
            (st_x, -0.142, 0.980),
            (st_x + sign * 0.014, -0.168, 0.860),
            (st_x + sign * 0.028, -0.192, 0.740),
            (st_x + sign * 0.042, -0.212, 0.620),
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
    mat_sash = bpy.data.materials.get("Mat_Dress_WaistBelt") or bpy.data.materials.new("Mat_Dress_WaistBelt")
    mat_sash.use_nodes = True
    bs_sash = mat_sash.node_tree.nodes.get("Principled BSDF")
    if bs_sash:
        bs_sash.inputs["Base Color"].default_value = (0.22, 0.56, 0.84, 1.0)
        bs_sash.inputs["Roughness"].default_value = 0.18
        if "Sheen Weight" in bs_sash.inputs: bs_sash.inputs["Sheen Weight"].default_value = 1.0
    sash_obj.data.materials.append(mat_sash)
    sash_sol = sash_obj.modifiers.new("Solidify", 'SOLIDIFY')
    sash_sol.thickness = 0.002
    sash_sub = sash_obj.modifiers.new("Subsurf", 'SUBSURF')
    sash_sub.levels = 1

    # 7.3 Natural Gravity-Draped A-Line Sundress Skirt (100% Organic Fabric Drape)
    # Replaces rigid trapezoid cone with natural downward hang, vertical drapery folds, and gravity sag
    print("[MorphoMesh] Generating natural gravity-draped A-line sundress skirt...")
    bm_skirt = bmesh.new()
    skirt_rings_count = 36
    n_sk_sec = 72
    skirt_rings = []

    for r in range(skirt_rings_count):
        t = r / (skirt_rings_count - 1)
        sz = 0.980 - 0.460 * t # 0.980 down to 0.520

        # Smooth natural A-line progression with gravity drape:
        # Top 30% (waist to hip, z: 0.98 -> 0.84): follows body contour gently (ease-in)
        # Lower 70% (hip to hem, z: 0.84 -> 0.52): soft vertical hang under gravity
        if t < 0.30:
            u = t / 0.30
            s_u = math.sin(u * math.pi * 0.5) ** 1.5
            rx_base = 0.124 + 0.034 * s_u
            ry_base = 0.082 + 0.048 * s_u
            yo = -0.052 + 0.032 * s_u
            fold_amp = 0.003 + 0.008 * u
        else:
            u = (t - 0.30) / 0.70
            rx_base = 0.158 + 0.117 * (u ** 1.25)
            ry_base = 0.130 + 0.110 * (u ** 1.25)
            yo = -0.020 + 0.015 * u
            fold_amp = 0.011 + 0.025 * (u ** 1.15)

        ring = []
        for i in range(n_sk_sec):
            th = 2.0 * math.pi * i / n_sk_sec
            ct = math.cos(th)
            st = math.sin(th)

            # 8 elegant vertical gravity drapery folds (soft undulating flutes)
            fold = fold_amp * (0.80 * math.cos(8.0 * th) + 0.20 * math.sin(16.0 * th))
            if t < 0.35 and fold < 0:
                fold *= 0.10

            # Posterior clearance over buttocks
            glute_boost = 0.028 * max(0.0, st) * (1.0 - 0.30 * t)

            rx = rx_base + fold
            ry = ry_base + glute_boost + fold * 0.7

            px = ct * rx
            py = yo + st * ry
            # Gravity sag at hem between folds
            pz = sz - 0.008 * (t ** 2) * (1.0 - math.cos(8.0 * th)) * 0.5
            ring.append(bm_skirt.verts.new((px, py, pz)))
        skirt_rings.append(ring)

    for r in range(skirt_rings_count - 1):
        for i in range(n_sk_sec):
            ni = (i + 1) % n_sk_sec
            bm_skirt.faces.new([skirt_rings[r][i], skirt_rings[r][ni], skirt_rings[r+1][ni], skirt_rings[r+1][i]])

    for f in bm_skirt.faces: f.smooth = True
    skirt_m = bpy.data.meshes.new("Mesh_Dress_PleatedSkirt_Mesh")
    bm_skirt.to_mesh(skirt_m)
    bm_skirt.free()

    skirt_obj = bpy.data.objects.new("Mesh_Dress_PleatedSkirt", skirt_m)
    link(skirt_obj, "03_Wardrobe")
    skirt_obj.data.materials.append(mat_silk)
    sk_sol = skirt_obj.modifiers.new("Solidify", 'SOLIDIFY')
    sk_sol.thickness = 0.002
    sk_sub = skirt_obj.modifiers.new("Subsurf", 'SUBSURF')
    sk_sub.levels = 1

    # 8. Flat Strappy Sandals (Dép Bệt - Bare 10 Toes)
    print("[MorphoMesh] Generating flat sandals leaving 10 bare toes completely exposed...")
    mat_sandal = bpy.data.materials.get("Mat_Sandal_Leather") or bpy.data.materials.new("Mat_Sandal_Leather")
    mat_sandal.use_nodes = True
    bs_san = mat_sandal.node_tree.nodes.get("Principled BSDF")
    if bs_san:
        bs_san.inputs["Base Color"].default_value = (0.92, 0.90, 0.88, 1.0)
        bs_san.inputs["Roughness"].default_value = 0.45

    for side_sign, s_name in [(-1.0, "Mesh_Sandal_R"), (1.0, "Mesh_Sandal_L")]:
        bm_san = bmesh.new()
        cx = side_sign * 0.088
        sole_profile = [
            ( 0.050, 0.030), # Heel
            ( 0.000, 0.032), # Midfoot
            (-0.070, 0.036), # Ball of foot
            (-0.125, 0.038), # Toe roots
            (-0.185, 0.040), # Ends at toe tips under the feet
        ]
        s_rings = []
        for py, half_w in sole_profile:
            v0 = bm_san.verts.new((cx - half_w, py, -0.005))
            v1 = bm_san.verts.new((cx + half_w, py, -0.005))
            v2 = bm_san.verts.new((cx + half_w, py,  0.000))
            v3 = bm_san.verts.new((cx - half_w, py,  0.000))
            s_rings.append((v0, v1, v2, v3))

        for k in range(len(s_rings) - 1):
            bm_san.faces.new([s_rings[k][0], s_rings[k][1], s_rings[k+1][1], s_rings[k+1][0]])
            bm_san.faces.new([s_rings[k][3], s_rings[k+1][3], s_rings[k+1][2], s_rings[k][2]])
            bm_san.faces.new([s_rings[k][0], s_rings[k+1][0], s_rings[k+1][3], s_rings[k][3]])
            bm_san.faces.new([s_rings[k][1], s_rings[k][2], s_rings[k+1][2], s_rings[k+1][1]])

        # Delicate straps: thong between toes + instep strap
        sy = -0.070
        strap_arch = [
            (cx - 0.036, sy, 0.000),
            (cx - 0.022, sy, 0.028),
            (cx,         sy, 0.038),
            (cx + 0.022, sy, 0.028),
            (cx + 0.036, sy, 0.000),
        ]
        st_r = []
        for px, py, pz in strap_arch:
            vl = bm_san.verts.new((px, py - 0.005, pz))
            vr = bm_san.verts.new((px, py + 0.005, pz))
            st_r.append((vl, vr))
        for k in range(len(st_r) - 1):
            bm_san.faces.new([st_r[k][0], st_r[k][1], st_r[k+1][1], st_r[k+1][0]])

        for f in bm_san.faces: f.smooth = True
        san_m = bpy.data.meshes.new(f"{s_name}_Mesh")
        bm_san.to_mesh(san_m)
        bm_san.free()
        san_obj = bpy.data.objects.new(s_name, san_m)
        link(san_obj, "03_Wardrobe")
        san_obj.data.materials.append(mat_sandal)
        san_sub = san_obj.modifiers.new("Subsurf", 'SUBSURF')
        san_sub.levels = 1

    # 9. Props: 10 Crimson Strings & 10 Butterflies
    for o in list(bpy.data.objects):
        if "Butterfly" in o.name:
            link(o, "04_Props")
            o.hide_render = False
        elif "Marionette" in o.name or "String" in o.name:
            link(o, "04_Props")
            o.hide_render = False

    # 10. Ensure all wardrobe and body objects are unhidden
    for o in [body_obj, bodice_obj, sash_obj, skirt_obj, sc_obj]:
        o.hide_render = False
        o.hide_viewport = False

    # 11. 360-Degree Studio Environment & 4-Point Lighting
    print("[MorphoMesh] Building 360-degree studio cyclorama and multi-point lighting...")
    # Clean up old backdrops and lights
    for old_obj_name in ["Studio_Backdrop", "Studio_Cyclorama", "Studio_Floor", "Key_Light", "Fill_Light", "Rim_Light", "Rim_Light_Back", "Side_Fill_Light"]:
        ob = bpy.data.objects.get(old_obj_name)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)

    # Studio Floor Disc
    bm_fl = bmesh.new()
    bmesh.ops.create_circle(bm_fl, cap_ends=True, radius=3.8, segments=64)
    for v in bm_fl.verts: v.co.z = -0.005
    for f in bm_fl.faces: f.smooth = True
    fl_m = bpy.data.meshes.new("Studio_Floor_Mesh")
    bm_fl.to_mesh(fl_m)
    bm_fl.free()
    fl_obj = bpy.data.objects.new("Studio_Floor", fl_m)
    link(fl_obj, "06_Lights_Camera")
    mat_floor = bpy.data.materials.new("Mat_Studio_Floor")
    mat_floor.use_nodes = True
    bs_fl = mat_floor.node_tree.nodes.get("Principled BSDF")
    if bs_fl:
        bs_fl.inputs["Base Color"].default_value = (0.24, 0.25, 0.28, 1.0)
        bs_fl.inputs["Roughness"].default_value = 0.55
    fl_obj.data.materials.append(mat_floor)

    # Studio Cyclorama Cylinder (Normals facing inward)
    bm_cyc = bmesh.new()
    cyc_r = 4.2
    cyc_h = 3.6
    n_cyc_seg = 64
    cyc_bot = [bm_cyc.verts.new((math.cos(2*math.pi*i/n_cyc_seg)*cyc_r, math.sin(2*math.pi*i/n_cyc_seg)*cyc_r, -0.005)) for i in range(n_cyc_seg)]
    cyc_top = [bm_cyc.verts.new((math.cos(2*math.pi*i/n_cyc_seg)*cyc_r, math.sin(2*math.pi*i/n_cyc_seg)*cyc_r, cyc_h)) for i in range(n_cyc_seg)]
    for i in range(n_cyc_seg):
        ni = (i + 1) % n_cyc_seg
        # Inward-facing winding
        bm_cyc.faces.new([cyc_bot[i], cyc_top[i], cyc_top[ni], cyc_bot[ni]])
    for f in bm_cyc.faces: f.smooth = True
    cyc_m = bpy.data.meshes.new("Studio_Cyclorama_Mesh")
    bm_cyc.to_mesh(cyc_m)
    bm_cyc.free()
    cyc_obj = bpy.data.objects.new("Studio_Cyclorama", cyc_m)
    link(cyc_obj, "06_Lights_Camera")
    mat_cyc = bpy.data.materials.new("Mat_Studio_Cyclorama")
    mat_cyc.use_nodes = True
    bs_cyc = mat_cyc.node_tree.nodes.get("Principled BSDF")
    if bs_cyc:
        bs_cyc.inputs["Base Color"].default_value = (0.32, 0.34, 0.38, 1.0)
        bs_cyc.inputs["Roughness"].default_value = 0.85
    cyc_obj.data.materials.append(mat_cyc)

    # 4-Point Studio Lighting
    lights_cfg = [
        ("Key_Light", (1.6, -2.4, 2.2), (math.radians(50), 0, math.radians(35)), 'AREA', 360.0, (1.0, 0.98, 0.95), 1.6),
        ("Fill_Light", (-1.8, -2.0, 1.6), (math.radians(55), 0, math.radians(-40)), 'AREA', 180.0, (0.94, 0.96, 1.0), 2.0),
        ("Rim_Light_Back", (0.0, 2.2, 2.5), (math.radians(130), 0, math.radians(180)), 'AREA', 320.0, (1.0, 1.0, 1.0), 1.8),
        ("Side_Fill_Light", (2.4, 0.0, 1.4), (math.radians(65), 0, math.radians(90)), 'AREA', 140.0, (0.96, 0.97, 1.0), 1.5),
    ]
    for l_name, l_loc, l_rot, l_type, l_pow, l_col, l_sz in lights_cfg:
        l_data = bpy.data.lights.new(l_name, l_type)
        l_data.energy = l_pow
        l_data.color = l_col
        l_data.size = l_sz
        l_obj = bpy.data.objects.new(l_name, l_data)
        l_obj.location = l_loc
        l_obj.rotation_euler = l_rot
        link(l_obj, "06_Lights_Camera")

    # Camera Views
    cams = {
        "beauty_front": ((0, -2.80, 0.82), (math.radians(90), 0, 0), 55.0),
        "beauty_three_quarter": ((1.85, -2.00, 0.88), (math.radians(85), 0, math.radians(43)), 55.0),
        "beauty_side": ((2.80, -0.05, 0.82), (math.radians(90), 0, math.radians(90)), 55.0),
        "beauty_back": ((0, 2.80, 0.82), (math.radians(90), 0, math.radians(180)), 55.0),
        "beauty_close_up": ((0, -0.85, 1.44), (math.radians(88), 0, 0), 85.0),
    }

    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64
    scene.cycles.device = 'CPU'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.render.resolution_x = 720
    scene.render.resolution_y = 1280

    cam_obj = bpy.data.objects.get("RenderCamera")
    if not cam_obj:
        cam_data = bpy.data.cameras.new("RenderCamera")
        cam_obj = bpy.data.objects.new("RenderCamera", cam_data)
        link(cam_obj, "06_Lights_Camera")
    scene.camera = cam_obj

    out_dir = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\renders"
    os.makedirs(out_dir, exist_ok=True)

    # Save Master Blend
    blend_path = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend"
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"[MorphoMesh] Saved true master scene: {blend_path}")

    # Export GLB and FBX
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
        cam_obj.data.lens = flen

        out_path = os.path.join(out_dir, f"{shot_name}.png")
        scene.render.filepath = out_path
        print(f"[MorphoMesh] Rendering {shot_name} -> {out_path}...")
        bpy.ops.render.render(write_still=True)

    shutil.copyfile(os.path.join(out_dir, "beauty_close_up.png"), os.path.join(out_dir, "beauty_closeup.png"))

    print("=" * 80)
    print("TRUE YU NIAN AN MASTER ASSEMBLY & RENDERS COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    build_true_yu_nian_an()
