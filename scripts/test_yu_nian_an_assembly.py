"""
MorphoMesh: Build and Render Real Yu Nian An Character Asset
Based on Anatomical Female Base Mold + Organic One-Piece Sundress (Váy Liền Thân)
Zero accordion pleats, zero chibi hack, 100% authentic human anatomy & concept styling.
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

def build_character():
    print("=" * 80)
    print("ASSEMBLING REAL YU NIAN AN FROM ANATOMICAL BASE MOLD")
    print("=" * 80)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # 1. Setup Collections
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

    # 2. Setup Materials
    mats = {}

    def create_pbr(name, base_color, roughness, metallic=0.0, sss_weight=0.0, sss_radius=(0.008, 0.004, 0.002), sheen=0.0, emission=None):
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

    # Materials
    create_pbr("Mat_Human_Skin_SSS", (0.957, 0.894, 0.863, 1.0), 0.36, sss_weight=0.35)
    create_pbr("Mat_Dress_WhiteSilk", (0.96, 0.96, 0.97, 1.0), 0.32, sheen=0.85)
    create_pbr("Mat_Dress_WaistBelt", (0.28, 0.58, 0.82, 1.0), 0.18, sheen=1.0) # Ice blue satin
    create_pbr("Mat_Human_Hair", (0.015, 0.014, 0.016, 1.0), 0.28) # Jet black silky hair
    create_pbr("Mat_Sandal_Leather", (0.92, 0.90, 0.88, 1.0), 0.40)
    create_pbr("Mat_Marionette_RedString", (0.95, 0.08, 0.12, 1.0), 0.40, emission=((0.95, 0.08, 0.12, 1.0), 3.0))
    create_pbr("Mat_Magic_Butterfly", (0.98, 0.99, 1.00, 1.0), 0.20, emission=((0.95, 0.98, 1.00, 1.0), 4.5))
    create_pbr("Mat_Human_Lips", (0.86, 0.42, 0.48, 1.0), 0.25, sss_weight=0.3)
    create_pbr("Mat_Human_Eyes", (0.12, 0.35, 0.58, 1.0), 0.10) # Soulful sapphire eyes

    # 3. Build Body Mesh from Perfected Base Mold
    raw_verts, raw_quads, raw_uvs = load_anatomical_base_mold()
    s = 1.0

    verts = [list(v) for v in raw_verts]
    for i, (x, y, z) in enumerate(verts):
        # Bust
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

        # Buttocks (seamless transition)
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

        # Lumbar Lordosis
        if 0.95 * s <= z <= 1.09 * s and abs(x) < 0.16 * s and y > 0.01 * s:
            w_lumbar = (math.cos((z - 1.02 * s) * math.pi / (0.14 * s)) ** 2)
            verts[i][1] -= 0.014 * s * w_lumbar

        # Waist Cinch (WHR 0.697)
        if 0.96 * s <= z <= 1.10 * s and abs(x) < 0.20 * s:
            w_waist = (math.cos((z - 1.025 * s) * math.pi / (0.14 * s)) ** 2)
            verts[i][0] *= (1.0 - 0.075 * w_waist)
            verts[i][1] *= (1.0 - 0.055 * w_waist)

        # Clavicle & Neck Grace
        if 1.28 * s <= z <= 1.34 * s and 0.02 * s < abs(x) < 0.14 * s and y < -0.01 * s:
            dx_c = (abs(x) - 0.08 * s) / (0.06 * s)
            dz_c = (z - 1.31 * s) / (0.03 * s)
            r2_c = dx_c * dx_c + dz_c * dz_c
            if r2_c < 1.0:
                w_clav = (math.cos(r2_c * math.pi * 0.5) ** 2)
                verts[i][1] -= 0.005 * s * w_clav

        # Facial Refinement: delicate chin and jawline
        if z >= 1.38 * s:
            if z < 1.46 * s and y < -0.03 * s:
                t_chin = max(0.0, (1.46 * s - z) / (0.08 * s))
                w_chin = t_chin ** 1.5
                verts[i][0] *= (1.0 - 0.06 * w_chin)
                if abs(x) < 0.025 * s and 1.39 * s <= z <= 1.43 * s:
                    verts[i][1] -= 0.003 * s * (1.0 - abs(x) / (0.025 * s))

    # Construct Body Mesh
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

    # 4. Rigify Armature
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

    # Fingers
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

    # Parent body to armature
    arm_m = body_obj.modifiers.new("Armature", 'ARMATURE')
    arm_m.object = arm_obj
    arm_m.use_deform_preserve_volume = True

    # 5. Build Genuine One-Piece Sundress (Váy Liền Thân)
    # 5.1 Bodice hugging teardrop bust with sweetheart neckline & spaghetti straps
    bm_bod = bmesh.new()
    n_sec = 48
    # Bodice vertical rings from empire waist (z=1.02) to sweetheart top (z=1.24)
    bod_slices = [
        (1.020, 0.122, 0.092, -0.010),
        (1.060, 0.125, 0.095, -0.015),
        (1.100, 0.130, 0.100, -0.022),
        (1.140, 0.138, 0.118, -0.036), # Across fullest bust projection
        (1.180, 0.142, 0.122, -0.038),
        (1.215, 0.135, 0.105, -0.026), # Sweetheart neckline curve
    ]

    bod_rings = []
    for sz, rx, ry, yo in bod_slices:
        ring = []
        for i in range(n_sec):
            th = 2.0 * math.pi * i / n_sec
            ct = math.cos(th)
            st = math.sin(th)
            # Sweetheart dip at center front (th ~ 3*pi/2, st ~ -1, ct ~ 0)
            z_dip = 0.0
            if sz > 1.18 and st < -0.2:
                front_u = max(0.0, -st)
                mid_u = max(0.0, 1.0 - abs(ct) / 0.35)
                z_dip = -0.032 * front_u * mid_u
            # Bust cup projection
            bust_proj = 0.0
            if sz > 1.08 and st < -0.1:
                bust_proj = 0.028 * (-st) * (1.0 - min(1.0, (abs(ct) - 0.28)**2 / 0.08))
            px = ct * rx
            py = yo + st * ry - bust_proj
            pz = sz + z_dip
            ring.append(bm_bod.verts.new((px, py, pz)))
        bod_rings.append(ring)

    for r in range(len(bod_slices) - 1):
        for i in range(n_sec):
            ni = (i + 1) % n_sec
            bm_bod.faces.new([bod_rings[r][i], bod_rings[r][ni], bod_rings[r+1][ni], bod_rings[r+1][i]])

    # Dual Spaghetti Straps (Quai áo mảnh mai ôm qua vai)
    strap_w = 0.003
    for side_sign in [-1.0, 1.0]:
        strap_x = side_sign * 0.075
        strap_pts = [
            (strap_x, -0.115, 1.210),
            (strap_x, -0.070, 1.280),
            (strap_x, -0.020, 1.330),
            (strap_x,  0.020, 1.335), # Clavicle crest
            (strap_x,  0.060, 1.290),
            (strap_x,  0.088, 1.215), # Back rim
        ]
        s_rings = []
        for px, py, pz in strap_pts:
            vl = bm_bod.verts.new((px - strap_w, py, pz))
            vr = bm_bod.verts.new((px + strap_w, py, pz))
            s_rings.append((vl, vr))
        for k in range(len(s_rings) - 1):
            bm_bod.faces.new([s_rings[k][0], s_rings[k][1], s_rings[k+1][1], s_rings[k+1][0]])

    for f in bm_bod.faces: f.smooth = True
    bod_mesh = bpy.data.meshes.new("Mesh_Dress_Bodice_Mesh")
    bm_bod.to_mesh(bod_mesh)
    bm_bod.free()

    bodice_obj = bpy.data.objects.new("Mesh_Dress_Bodice", bod_mesh)
    link(bodice_obj, "03_Wardrobe")
    bodice_obj.data.materials.append(mats["Mat_Dress_WhiteSilk"])
    bod_sol = bodice_obj.modifiers.new("Solidify", 'SOLIDIFY')
    bod_sol.thickness = 0.0018
    bod_sub = bodice_obj.modifiers.new("Subsurf", 'SUBSURF')
    bod_sub.levels = 1

    # 5.2 Waist Sash (Ice Blue Satin Ribbon with Center Bow Knot & Cascading Tails)
    bm_sash = bmesh.new()
    sash_z_levels = [1.015, 1.035, 1.055]
    sash_rings = []
    for sz in sash_z_levels:
        ring = []
        for i in range(n_sec):
            th = 2.0 * math.pi * i / n_sec
            rx = 0.125; ry = 0.095; yo = -0.010
            ring.append(bm_sash.verts.new((math.cos(th) * rx, math.sin(th) * ry + yo, sz)))
        sash_rings.append(ring)

    for r in range(len(sash_z_levels) - 1):
        for i in range(n_sec):
            ni = (i + 1) % n_sec
            bm_sash.faces.new([sash_rings[r][i], sash_rings[r][ni], sash_rings[r+1][ni], sash_rings[r+1][i]])

    # Front bow knot & dangling tails
    tail_w = 0.009
    for sign in [-1.0, 1.0]:
        st_x = sign * 0.012
        tail_path = [
            (st_x, -0.110, 1.035),
            (st_x + sign * 0.015, -0.140, 0.920),
            (st_x + sign * 0.030, -0.170, 0.780),
            (st_x + sign * 0.045, -0.195, 0.650),
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

    # 5.3 Flowing Organic A-line Skirt (ZERO Accordion Pleats - Natural Silk Folds)
    # Radiates smoothly from waistline (z=1.02) to knee hem (z=0.52)
    bm_skirt = bmesh.new()
    skirt_rings_count = 14
    skirt_rings = []

    for r in range(skirt_rings_count):
        t = r / (skirt_rings_count - 1)
        sz = 1.020 + t * (0.520 - 1.020)
        # Base A-line flare
        rx_base = 0.125 + 0.220 * (t ** 1.1)
        ry_base = 0.095 + 0.190 * (t ** 1.1)
        yo = -0.010 + 0.010 * t

        # Organic wave amplitude grows gently down the skirt (smooth sinusoidal folds, NOT accordion teeth!)
        wave_amp = 0.024 * (t ** 1.4)

        ring = []
        for i in range(n_sec):
            th = 2.0 * math.pi * i / n_sec
            # Organic multi-harmonic fabric drape (harmonics 5 and 7, gentle ripples)
            drape = wave_amp * (0.75 * math.cos(5.0 * th) + 0.25 * math.sin(7.0 * th))
            # Smooth anterior flattening over thighs
            if math.sin(th) < 0:
                drape *= 0.65
            rx = rx_base + drape
            ry = ry_base + drape
            px = math.cos(th) * rx
            py = math.sin(th) * ry + yo
            pz = sz - 0.012 * (t ** 2) * math.cos(5.0 * th) # Scalloped organic hem wave
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

    # 6. Flat Sandals (Dép Bệt - Bare 10 Toes Exposed)
    for side_sign, s_name in [(-1.0, "Mesh_Sandal_R"), (1.0, "Mesh_Sandal_L")]:
        bm_san = bmesh.new()
        cx = side_sign * 0.088
        # Flat sole under foot (from heel y=+0.08 to ball y=-0.13, leaving toes at y<-0.13 bare!)
        sole_slices = [
            ( 0.075, 0.030, 0.008), # Heel
            ( 0.020, 0.034, 0.008), # Midfoot
            (-0.040, 0.036, 0.008), # Arch
            (-0.110, 0.040, 0.008), # Ball of foot
            (-0.132, 0.041, 0.008), # Stops right behind toe roots!
        ]
        s_rings = []
        for py, half_w, pz in sole_slices:
            v0 = bm_san.verts.new((cx - half_w, py, pz - 0.006))
            v1 = bm_san.verts.new((cx + half_w, py, pz - 0.006))
            v2 = bm_san.verts.new((cx + half_w, py, pz))
            v3 = bm_san.verts.new((cx - half_w, py, pz))
            s_rings.append((v0, v1, v2, v3))

        for k in range(len(s_rings) - 1):
            # Bottom face
            bm_san.faces.new([s_rings[k][0], s_rings[k][1], s_rings[k+1][1], s_rings[k+1][0]])
            # Top face
            bm_san.faces.new([s_rings[k][3], s_rings[k+1][3], s_rings[k+1][2], s_rings[k][2]])
            # Left side
            bm_san.faces.new([s_rings[k][0], s_rings[k+1][0], s_rings[k+1][3], s_rings[k][3]])
            # Right side
            bm_san.faces.new([s_rings[k][1], s_rings[k][2], s_rings[k+1][2], s_rings[k+1][1]])

        # Metatarsal instep strap arching over foot
        strap_y = -0.075
        strap_arch = [
            (cx - 0.038, strap_y, 0.008),
            (cx - 0.030, strap_y, 0.038),
            (cx,         strap_y, 0.048),
            (cx + 0.030, strap_y, 0.038),
            (cx + 0.038, strap_y, 0.008),
        ]
        st_rings = []
        for px, py, pz in strap_arch:
            vl = bm_san.verts.new((px, py - 0.006, pz))
            vr = bm_san.verts.new((px, py + 0.006, pz))
            st_rings.append((vl, vr))
        for k in range(len(st_rings) - 1):
            bm_san.faces.new([st_rings[k][0], st_rings[k][1], st_rings[k+1][1], st_rings[k+1][0]])

        for f in bm_san.faces: f.smooth = True
        san_m = bpy.data.meshes.new(f"{s_name}_Mesh")
        bm_san.to_mesh(san_m)
        bm_san.free()
        san_obj = bpy.data.objects.new(s_name, san_m)
        link(san_obj, "03_Wardrobe")
        san_obj.data.materials.append(mats["Mat_Sandal_Leather"])
        san_sub = san_obj.modifiers.new("Subsurf", 'SUBSURF')
        san_sub.levels = 1

    # 7. Silky Black Hime Cut Hair (100% Scalp Coverage, ZERO Bald Spots)
    # 7.1 Scalp Cap Dome
    bm_scalp = bmesh.new()
    scalp_rings = []
    for ring_i, sz in enumerate([1.50, 1.54, 1.58, 1.62, 1.645]):
        t_s = ring_i / 4.0
        r_sc = 0.088 * math.cos(t_s * math.pi * 0.45)
        yo_sc = -0.035
        r_v = []
        for i in range(24):
            th = 2.0 * math.pi * i / 24
            r_v.append(bm_scalp.verts.new((math.cos(th) * r_sc, math.sin(th) * (r_sc * 1.05) + yo_sc, sz)))
        scalp_rings.append(r_v)

    for r in range(len(scalp_rings) - 1):
        for i in range(24):
            ni = (i + 1) % 24
            bm_scalp.faces.new([scalp_rings[r][i], scalp_rings[r][ni], scalp_rings[r+1][ni], scalp_rings[r+1][i]])
    # Cap top
    top_center = bm_scalp.verts.new((0.0, -0.035, 1.650))
    for i in range(24):
        ni = (i + 1) % 24
        bm_scalp.faces.new([scalp_rings[-1][i], scalp_rings[-1][ni], top_center])

    for f in bm_scalp.faces: f.smooth = True
    sc_m = bpy.data.meshes.new("Hair_Scalp_Crown_Mesh")
    bm_scalp.to_mesh(sc_m)
    bm_scalp.free()
    sc_obj = bpy.data.objects.new("Hair_Scalp_Crown", sc_m)
    link(sc_obj, "02_Hair")
    sc_obj.data.materials.append(mats["Mat_Human_Hair"])

    # 7.2 Hime Bangs (Blunt Straight Cut at Eyebrow line z=1.52)
    bm_bangs = bmesh.new()
    b_rings = []
    for b_z, b_y, b_curv in [(1.63, -0.085, 0.00), (1.58, -0.115, 0.012), (1.525, -0.128, 0.016)]:
        r_v = []
        for i in range(16):
            u = i / 15.0
            bx = -0.065 + 0.130 * u
            by = b_y - b_curv * (1.0 - (bx / 0.065) ** 2)
            r_v.append(bm_bangs.verts.new((bx, by, b_z)))
        b_rings.append(r_v)
    for r in range(len(b_rings) - 1):
        for i in range(15):
            bm_bangs.faces.new([b_rings[r][i], b_rings[r][i+1], b_rings[r+1][i+1], b_rings[r+1][i]])
    for f in bm_bangs.faces: f.smooth = True
    bg_m = bpy.data.meshes.new("Hair_Hime_Bangs_Mesh")
    bm_bangs.to_mesh(bg_m)
    bm_bangs.free()
    bg_obj = bpy.data.objects.new("Hair_Hime_Bangs", bg_m)
    link(bg_obj, "02_Hair")
    bg_obj.data.materials.append(mats["Mat_Human_Hair"])
    bg_sol = bg_obj.modifiers.new("Solidify", 'SOLIDIFY')
    bg_sol.thickness = 0.002

    # 7.3 Hime Sidelocks (Tóc mai rơi xuống qua vai tới xương quai xanh)
    bm_side = bmesh.new()
    for sign in [-1.0, 1.0]:
        sx = sign * 0.076
        s_pts = [
            (sx, -0.080, 1.58),
            (sx + sign * 0.005, -0.095, 1.50),
            (sx + sign * 0.008, -0.102, 1.42),
            (sx + sign * 0.010, -0.098, 1.34),
            (sx + sign * 0.008, -0.085, 1.26), # Blunt tip near clavicle
        ]
        s_r = []
        for px, py, pz in s_pts:
            vl = bm_side.verts.new((px - 0.012, py, pz))
            vr = bm_side.verts.new((px + 0.012, py, pz))
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
    sd_sol.thickness = 0.0025

    # 7.4 Cascading Long Back Hair (Dài qua hông tới giữa đùi)
    bm_cas = bmesh.new()
    cas_slices = [
        (1.58, 0.095,  0.035),
        (1.48, 0.120,  0.075),
        (1.36, 0.145,  0.110),
        (1.22, 0.170,  0.135),
        (1.06, 0.185,  0.150),
        (0.90, 0.200,  0.155),
        (0.72, 0.190,  0.145), # Mid-thigh tips
    ]
    cas_rings = []
    for pz, half_w, py in cas_slices:
        r_v = []
        for i in range(16):
            u = i / 15.0
            px = -half_w + 2.0 * half_w * u
            # Slight curve embracing back
            curv_y = py + 0.025 * (1.0 - (px / half_w) ** 2)
            r_v.append(bm_cas.verts.new((px, curv_y, pz)))
        cas_rings.append(r_v)

    for r in range(len(cas_rings) - 1):
        for i in range(15):
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

    # 8. Signature Props: 10 Crimson Marionette Strings & 10 Glowing Butterflies
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

    # Fingertip anchor points
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
        # String cord (14 segments)
        prev_v = None
        for step in range(12):
            u_s = step / 11.0
            # Straight line with slight gravitational sag
            sx = f_anc[0] + u_s * (bf_loc[0] - f_anc[0])
            sy = f_anc[1] + u_s * (bf_loc[1] - f_anc[1])
            sz = f_anc[2] + u_s * (bf_loc[2] - f_anc[2]) - 0.015 * math.sin(math.pi * u_s)
            v_curr = bm_str.verts.new((sx, sy, sz))
            if prev_v:
                bm_str.edges.new([prev_v, v_curr])
            prev_v = v_curr

        # Butterfly mesh
        bm_bf = bmesh.new()
        wing_span = 0.055
        wing_chord = 0.045
        # Quad wings with dihedral flap angle
        flap_ang = math.radians(25 + 15 * math.sin(idx * 1.3))
        for w_side, w_sign in [("L", 1.0), ("R", -1.0)]:
            w_root = bm_bf.verts.new((0.0, 0.0, 0.0))
            w_tip_fore = bm_bf.verts.new((w_sign * wing_span * math.cos(flap_ang), -wing_chord * 0.8, wing_span * math.sin(flap_ang)))
            w_tip_hind = bm_bf.verts.new((w_sign * wing_span * 0.8 * math.cos(flap_ang), wing_chord * 0.6, wing_span * 0.8 * math.sin(flap_ang)))
            w_root_hind = bm_bf.verts.new((0.0, wing_chord * 0.4, 0.0))
            bm_bf.faces.new([w_root, w_tip_fore, w_tip_hind, w_root_hind])

        for f in bm_bf.faces: f.smooth = True
        bf_m = bpy.data.meshes.new(f"Prop_Butterfly_{idx:02d}_Mesh")
        bm_bf.to_mesh(bf_m)
        bm_bf.free()
        bf_obj = bpy.data.objects.new(f"Prop_Butterfly_{idx:02d}", bf_m)
        bf_obj.location = bf_loc
        bf_obj.rotation_euler = (math.radians(10 * math.sin(idx)), math.radians(15 * math.cos(idx)), math.radians(35 * idx))
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
    # Skin modifier or curve for thickness
    skin_m = str_obj.modifiers.new("Skin", 'SKIN')
    for v in str_obj.data.skin_vertices[0].data:
        v.radius = (0.0006, 0.0006)

    # 9. Lighting & Studio Environment
    # Key light
    bpy.ops.object.light_add(type='AREA', location=(1.8, -2.4, 2.2))
    key_l = bpy.context.active_object
    key_l.name = "Light_Key_Softbox"
    key_l.data.energy = 220.0
    key_l.data.size = 2.0
    key_l.data.color = (1.0, 0.96, 0.92)
    link(key_l, "06_Lights_Camera")

    # Fill light
    bpy.ops.object.light_add(type='AREA', location=(-1.8, -2.0, 1.8))
    fill_l = bpy.context.active_object
    fill_l.name = "Light_Fill_Softbox"
    fill_l.data.energy = 140.0
    fill_l.data.size = 2.5
    fill_l.data.color = (0.92, 0.95, 1.0)
    link(fill_l, "06_Lights_Camera")

    # Rim / Hair light
    bpy.ops.object.light_add(type='AREA', location=(0.0, 2.2, 2.1))
    rim_l = bpy.context.active_object
    rim_l.name = "Light_Rim_HairLight"
    rim_l.data.energy = 260.0
    rim_l.data.size = 1.8
    rim_l.data.color = (0.98, 0.98, 1.0)
    link(rim_l, "06_Lights_Camera")

    # Studio Backdrop
    bpy.ops.mesh.primitive_plane_add(size=12.0, location=(0, 2.8, 1.5))
    drop = bpy.context.active_object
    drop.name = "Studio_Backdrop"
    drop.rotation_euler = (math.radians(90), 0, 0)
    link(drop, "06_Lights_Camera")
    mat_drop = bpy.data.materials.new("Mat_Studio_Backdrop")
    mat_drop.use_nodes = True
    b_drop = mat_drop.node_tree.nodes.get("Principled BSDF")
    if b_drop:
        b_drop.inputs["Base Color"].default_value = (0.08, 0.085, 0.095, 1.0)
        b_drop.inputs["Roughness"].default_value = 0.8
    drop.data.materials.append(mat_drop)

    # 10. Cameras & Render Configuration
    cams = {
        "beauty_front": ((0, -2.65, 0.85), (math.radians(90), 0, 0)),
        "beauty_three_quarter": ((1.8, -2.0, 0.92), (math.radians(85), 0, math.radians(42))),
        "beauty_side": ((2.65, 0, 0.85), (math.radians(90), 0, math.radians(90))),
        "beauty_back": ((0, 2.65, 0.85), (math.radians(90), 0, math.radians(180))),
        "beauty_close_up": ((0, -0.95, 1.45), (math.radians(88), 0, 0)),
    }

    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64
    scene.cycles.device = 'CPU'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - High Contrast'
    scene.render.resolution_x = 720
    scene.render.resolution_y = 1280

    cam_data = bpy.data.cameras.new("RenderCamera")
    cam_data.lens = 65.0
    cam_obj = bpy.data.objects.new("RenderCamera", cam_data)
    link(cam_obj, "06_Lights_Camera")
    scene.camera = cam_obj

    out_dir = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\renders"
    os.makedirs(out_dir, exist_ok=True)

    # Save Master Blend
    blend_path = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend"
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"[MorphoMesh] Saved master scene: {blend_path}")

    # Render each camera view
    for shot_name, (loc, rot) in cams.items():
        cam_obj.location = loc
        cam_obj.rotation_euler = rot
        if "close_up" in shot_name:
            cam_data.lens = 85.0
        else:
            cam_data.lens = 60.0
        out_path = os.path.join(out_dir, f"{shot_name}.png")
        scene.render.filepath = out_path
        print(f"[MorphoMesh] Rendering {shot_name} -> {out_path}...")
        bpy.ops.render.render(write_still=True)

    print("=" * 80)
    print("YU NIAN AN REAL CHARACTER RENDERING COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    build_character()
