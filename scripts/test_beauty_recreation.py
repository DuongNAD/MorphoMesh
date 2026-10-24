"""
High-Fidelity Beauty Prototype for Yu Nian An Character Re-creation (v6):
- Bare anime torso from Slot 0 (zero jacket, zero collar lapels, delicate collarbones & neck)
- Sleeve meshes from Slot 6 connected to torso armholes and reshaped into slender bare arms
- Fitted two-strap dress bodice with scoop neckline dipping below clavicles and thin spaghetti straps (4mm)
- Ice-blue satin waist sash with cascading front ribbon tails
- Flared 28-pleat A-line skirt down to knees
- Flat white strap sandals
- Natural flowing long black hair cascade staying gracefully BEHIND back (past hips)
- 10 luminous swallowtail butterflies & slender catenary crimson silk threads
- Reference-matching arm pose (upper arms at 15 deg, forearms forward)
- AgX Cycles render with denoising
"""

import os
import sys
import math
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler, kdtree

def run_test():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    vrm_path = r"C:\Users\Admin\Downloads\_3D_Models_Assets\Liva.vrm"
    scale_factor = 1.65 / 1.4649 # 1.12635689

    bpy.ops.import_scene.gltf(filepath=vrm_path)
    arm = bpy.data.objects.get("Armature")
    body = bpy.data.objects.get("Body")
    face = bpy.data.objects.get("Face")
    hair = bpy.data.objects.get("Hair")

    if arm:
        arm.name = "Beauty_Armature"
        arm.scale = (scale_factor, scale_factor, scale_factor)
        arm.show_in_front = False
        arm.data.display_type = 'WIRE'
        for pb in arm.pose.bones:
            pb.custom_shape = None

    for o in list(bpy.data.objects):
        if 'Icosphere' in o.name or o.name.startswith('J_Sec_') or o.name.startswith('J_Opt_'):
            bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        if 'Icosphere' in m.name:
            bpy.data.meshes.remove(m, do_unlink=True)

    # 1. MATERIALS
    # Warm Porcelain Skin SSS
    mat_skin = bpy.data.materials.new("Mat_Human_Skin_SSS_Beauty")
    mat_skin.use_nodes = True
    mat_skin.node_tree.nodes.clear()
    out_sk = mat_skin.node_tree.nodes.new('ShaderNodeOutputMaterial')
    bsdf_sk = mat_skin.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf_sk.inputs['Base Color'].default_value = (0.950, 0.850, 0.800, 1.0)
    bsdf_sk.inputs['Roughness'].default_value = 0.36
    if 'Subsurface Method' in bsdf_sk.inputs: bsdf_sk.subsurface_method = 'RANDOM_WALK'
    if 'Subsurface Weight' in bsdf_sk.inputs:
        bsdf_sk.inputs['Subsurface Weight'].default_value = 0.28
        bsdf_sk.inputs['Subsurface Radius'].default_value = (0.015, 0.008, 0.004)
        bsdf_sk.inputs['Subsurface Scale'].default_value = 0.035
    mat_skin.node_tree.links.new(bsdf_sk.outputs['BSDF'], out_sk.inputs['Surface'])

    # White Silk Dress
    mat_silk = bpy.data.materials.new("Mat_Dress_WhiteSilk_Beauty")
    mat_silk.use_nodes = True
    bs_s = next((n for n in mat_silk.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bs_s:
        bs_s.inputs['Base Color'].default_value = (0.975, 0.970, 0.965, 1.0)
        bs_s.inputs['Roughness'].default_value = 0.32
        if 'Sheen Weight' in bs_s.inputs: bs_s.inputs['Sheen Weight'].default_value = 0.85
        if 'Subsurface Weight' in bs_s.inputs: bs_s.inputs['Subsurface Weight'].default_value = 0.05

    # Ice-blue Satin Sash
    mat_sash = bpy.data.materials.new("Mat_Dress_WaistBelt_Beauty")
    mat_sash.use_nodes = True
    bs_sa = next((n for n in mat_sash.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bs_sa:
        bs_sa.inputs['Base Color'].default_value = (0.55, 0.78, 0.94, 1.0)
        bs_sa.inputs['Roughness'].default_value = 0.20
        if 'Sheen Weight' in bs_sa.inputs: bs_sa.inputs['Sheen Weight'].default_value = 0.92

    # Silky Jet Black Hair
    mat_hair = bpy.data.materials.new("Mat_Human_Hair_Beauty")
    mat_hair.use_nodes = True
    bs_h = next((n for n in mat_hair.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bs_h:
        bs_h.inputs['Base Color'].default_value = (0.014, 0.013, 0.016, 1.0)
        bs_h.inputs['Roughness'].default_value = 0.36
        if 'Specular IOR Level' in bs_h.inputs: bs_h.inputs['Specular IOR Level'].default_value = 0.50
        if 'Anisotropic' in bs_h.inputs: bs_h.inputs['Anisotropic'].default_value = 0.50

    # 2. BODY: BARE PORCELAIN ANIME TORSO + SLENDER BARE ARMS (NO JACKET, NO LAPELS)
    if body:
        body.name = "Beauty_Body"
        bm_b = bmesh.new()
        bm_b.from_mesh(body.data)

        # Keep slot 0 (skin), slot 1 (scalp hair base), and slot 6 (tops sleeves)
        del_f = [f for f in bm_b.faces if f.material_index not in {0, 1, 6}]

        # In slot 6, keep ONLY Island 1 and Island 2 (the two sleeves)
        # DELETE Island 0 (the jacket/bolero) and Island 3 (the collar)
        s6_faces = [f for f in bm_b.faces if f.material_index == 6]
        visited = set()
        for f in s6_faces:
            if f in visited: continue
            isl = [f]; visited.add(f); st = [f]
            while st:
                curr = st.pop()
                for e in curr.edges:
                    for nxt in e.link_faces:
                        if nxt.material_index == 6 and nxt not in visited:
                            visited.add(nxt); isl.append(nxt); st.append(nxt)
            max_ax = max(abs(v.co.x) for f_i in isl for v in f_i.verts)
            if max_ax < 0.35:
                del_f.extend(isl)

        # In slot 0, delete ALL interior torso/pelvis faces under dress between 0.56 and 1.125
        for f in bm_b.faces:
            if f.material_index == 0:
                avg_z = sum(v.co.z for v in f.verts) / len(f.verts)
                if 0.56 < avg_z < 1.125:
                    del_f.append(f)

        bmesh.ops.delete(bm_b, geom=list(set(del_f)), context='FACES_ONLY')
        bmesh.ops.delete(bm_b, geom=[v for v in bm_b.verts if not v.link_faces], context='VERTS')
        bmesh.ops.remove_doubles(bm_b, verts=bm_b.verts, dist=0.001)

        # Reshape sleeve (Slot 6) into clean, smooth, natural bare arms
        y_c, z_c = 0.015, 1.140
        for v in bm_b.verts:
            if any(f.material_index == 6 for f in v.link_faces):
                ax = abs(v.co.x)
                t = max(0.0, min(1.0, (ax - 0.10) / (0.50 - 0.10)))
                target_r = 0.026 * (1.0 - t) + 0.016 * t
                dy = v.co.y - y_c
                dz = v.co.z - z_c
                curr_r = math.sqrt(dy * dy + dz * dz)
                if curr_r > target_r and curr_r > 1e-4:
                    v.co.y = y_c + dy * (target_r / curr_r)
                    v.co.z = z_c + dz * (target_r / curr_r)

        # Cap the inner sleeve boundary at shoulder cleanly
        for side_sign in [1.0, -1.0]:
            s_open = [v for v in bm_b.verts if any(f.material_index == 6 for f in v.link_faces)
                      and any(e.is_boundary for e in v.link_edges)
                      and 0.08 < (v.co.x * side_sign) < 0.20 and 1.0 < v.co.z < 1.25]
            if s_open:
                s_edges = list(set(e for v in s_open for e in v.link_edges if e.is_boundary))
                bmesh.ops.holes_fill(bm_b, edges=s_edges, sides=len(s_edges))

        # ANATOMICAL SCULPTING: Clavicles, Knees, Elbows, and Ankles
        for v in bm_b.verts:
            ax = abs(v.co.x)

            # 1. Clavicle S-Curve & Suprasternal Notch (hõm ức)
            if 1.135 < v.co.z < 1.190 and v.co.y < -0.015 and 0.005 < ax < 0.085:
                z_clav = 1.152 + 0.016 * (ax / 0.085) - 0.004 * (ax / 0.085) ** 2
                dz = abs(v.co.z - z_clav)
                if dz < 0.012:
                    blend = 1.0 - dz / 0.012
                    v.co.y -= 0.0045 * blend
            elif 1.145 < v.co.z < 1.168 and v.co.y < -0.020 and ax <= 0.010:
                blend = 1.0 - ax / 0.010
                v.co.y += 0.0030 * blend

            # 2. Patella Knee Joint (Xương bánh chè & Hõm gối)
            if 0.370 < v.co.z < 0.440 and v.co.y < -0.010:
                dz = (v.co.z - 0.405) / 0.022
                dx = (ax - 0.078) / 0.020
                r2 = dx * dx + dz * dz
                if r2 < 1.0:
                    v.co.y -= 0.0040 * (1.0 - r2)

            # 3. Elbow Olecranon (Mỏm khuỷu tay)
            if 0.28 < ax < 0.35 and v.co.y > 0.015:
                dx = (ax - 0.315) / 0.020
                dy = (v.co.y - 0.022) / 0.012
                r2 = dx * dx + dy * dy
                if r2 < 1.0:
                    v.co.y += 0.0035 * (1.0 - r2)

            # 4. Asymmetrical Ankle Malleoli (Mắt cá chân)
            if 0.075 < v.co.z < 0.125:
                # Medial malleolus (mắt cá trong: higher, slightly anterior)
                if ax < 0.075:
                    dz = abs(v.co.z - 0.105) / 0.015
                    if dz < 1.0:
                        v.co.x -= 0.0030 * (1.0 - dz) * (1.0 if v.co.x > 0 else -1.0)
                # Lateral malleolus (mắt cá ngoài: lower, slightly posterior)
                elif ax > 0.080:
                    dz = abs(v.co.z - 0.095) / 0.015
                    if dz < 1.0:
                        v.co.x += 0.0035 * (1.0 - dz) * (1.0 if v.co.x > 0 else -1.0)

        for f in bm_b.faces: f.smooth = True
        bm_b.to_mesh(body.data)
        bm_b.free()
        body.data.update()

        # Apply porcelain skin to body and jet black to scalp slot 1
        for i in range(len(body.data.materials)):
            if i == 1:
                body.data.materials[i] = mat_hair
            else:
                body.data.materials[i] = mat_skin

    # 3. FACE: Detailed anime facial features & sorrow expression
    if face:
        face.name = "Beauty_Face"
        for p in face.data.polygons: p.use_smooth = True

        # Sculpt sharp, delicate Mandible Jawline & V-line Chin
        bm_f = bmesh.new()
        bm_f.from_mesh(face.data)
        for v in bm_f.verts:
            ax = abs(v.co.x)
            # Chin apex definition
            if 1.205 < v.co.z < 1.240 and ax < 0.035 and v.co.y < -0.050:
                t_chin = max(0.0, 1.0 - (ax / 0.025) ** 2 - ((v.co.z - 1.222) / 0.018) ** 2)
                if t_chin > 0:
                    v.co.y -= 0.0020 * t_chin
                    v.co.z -= 0.0010 * t_chin
            # Mandible jawline contour
            elif 1.215 < v.co.z < 1.265 and 0.025 < ax < 0.065 and -0.055 < v.co.y < -0.010:
                target_y = -0.060 + 0.045 * ((ax - 0.025) / 0.040)
                dy = abs(v.co.y - target_y)
                if dy < 0.010:
                    blend = 1.0 - dy / 0.010
                    v.co.y += (target_y - v.co.y) * 0.35 * blend

        for f in bm_f.faces: f.smooth = True
        bm_f.to_mesh(face.data)
        bm_f.free()
        face.data.update()

        if face.data.shape_keys:
            for kb in face.data.shape_keys.key_blocks: kb.value = 0.0
            kb_sorrow = face.data.shape_keys.key_blocks.get("Fcl_ALL_Sorrow")
            if kb_sorrow: kb_sorrow.value = 0.28
            kb_eye_s = face.data.shape_keys.key_blocks.get("Fcl_EYE_Sorrow")
            if kb_eye_s: kb_eye_s.value = 0.22
            kb_brw_s = face.data.shape_keys.key_blocks.get("Fcl_BRW_Sorrow")
            if kb_brw_s: kb_brw_s.value = 0.25
            kb_mth_s = face.data.shape_keys.key_blocks.get("Fcl_MTH_Small")
            if kb_mth_s: kb_mth_s.value = 0.20

        # Iris: vivid ocean teal with subtle glow
        m_iris = bpy.data.materials.get("N00_000_00_EyeIris_00_EYE (Instance)")
        if m_iris and m_iris.node_tree:
            em_n = next((n for n in m_iris.node_tree.nodes if n.type == 'EMISSION'), None)
            tex_n = next((n for n in m_iris.node_tree.nodes if n.type == 'TEX_IMAGE'), None)
            if em_n and tex_n:
                m_iris.node_tree.links.new(tex_n.outputs['Color'], em_n.inputs['Color'])
                em_n.inputs['Strength'].default_value = 0.85

        # Crisp dark eyelashes and eyeliner
        for mat_name in ["N00_000_00_FaceEyelash_00_FACE (Instance)", "N00_000_00_FaceEyeline_00_FACE (Instance)"]:
            m_eye = bpy.data.materials.get(mat_name)
            if m_eye and m_eye.node_tree:
                bs = next((n for n in m_eye.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if bs:
                    bs.inputs['Base Color'].default_value = (0.015, 0.015, 0.020, 1.0)
                    bs.inputs['Roughness'].default_value = 0.30

        # Soft cherry-tinted lips
        m_mth = bpy.data.materials.get("N00_000_00_FaceMouth_00_FACE (Instance)")
        if m_mth and m_mth.node_tree:
            bs_m = next((n for n in m_mth.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bs_m:
                bs_m.inputs['Base Color'].default_value = (0.92, 0.42, 0.46, 1.0)
                bs_m.inputs['Roughness'].default_value = 0.25

        # Face skin: preserve all painted blush, lip shading, and contour details
        m_fskin = bpy.data.materials.get("N00_000_00_Face_00_SKIN (Instance)")
        if m_fskin and m_fskin.node_tree:
            tex_f = next((n for n in m_fskin.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None)
            tex_img_f = tex_f.image if tex_f else None
            m_fskin.node_tree.nodes.clear()
            out_f = m_fskin.node_tree.nodes.new('ShaderNodeOutputMaterial')
            bsdf_f = m_fskin.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
            if tex_img_f:
                tn_f = m_fskin.node_tree.nodes.new('ShaderNodeTexImage')
                tn_f.image = tex_img_f
                m_fskin.node_tree.links.new(tn_f.outputs['Color'], bsdf_f.inputs['Base Color'])
            else:
                bsdf_f.inputs['Base Color'].default_value = (0.958, 0.885, 0.850, 1.0)
            bsdf_f.inputs['Roughness'].default_value = 0.32
            if 'Subsurface Method' in bsdf_f.inputs: bsdf_f.subsurface_method = 'RANDOM_WALK'
            if 'Subsurface Weight' in bsdf_f.inputs:
                bsdf_f.inputs['Subsurface Weight'].default_value = 0.14
                bsdf_f.inputs['Subsurface Radius'].default_value = (0.010, 0.005, 0.003)
                bsdf_f.inputs['Subsurface Scale'].default_value = 0.012
            m_fskin.node_tree.links.new(bsdf_f.outputs['BSDF'], out_f.inputs['Surface'])

    # 4. UNIFIED ONE-PIECE SUNDRESS (VÁY LIỀN THÂN: CONTINUOUS STRAPS, BODICE, WAIST, AND PLEATED SKIRT)
    bm_dress = bmesh.new()
    n_pleats = 28
    n_sec = n_pleats * 2 # 56 sections for perfectly smooth silhouette and aligned pleats

    # Skirt slices (bottom hem to waist)
    sk_slices = [
        (0.500, 0.235, 0.265,  0.008), # 0: Hem below knees
        (0.605, 0.190, 0.210,  0.000), # 1: Mid lower skirt
        (0.710, 0.150, 0.165, -0.012), # 2: Mid upper skirt
        (0.810, 0.108, 0.118, -0.024), # 3: Skirt flare start
        (0.865, 0.082, 0.088, -0.030), # 4: Gathers under sash
    ]

    # Bodice slices (waist to neckline rim) with sculpted feminine curves
    b_slices = [
        (0.895, 0.078, 0.062, 0.058, -0.033), # 0: Empire waist seam (slender hourglass waist)
        (0.940, 0.077, 0.062, 0.058, -0.035), # 1: Cinched lower ribcage
        (0.980, 0.082, 0.068, 0.062, -0.033), # 2: Defined underbust fold
        (1.045, 0.096, 0.098, 0.072, -0.025), # 3: Full feminine bust apex
        (1.095, 0.094, 0.086, 0.070, -0.018), # 4: Upper bust slope
        (1.138, 0.090, 0.078, 0.068, -0.012), # 5: Sweetheart scoop neckline rim
    ]

    all_rings = []

    # 1. Build skirt rings (from hem upward)
    for sz, r_in, r_out, yo in sk_slices:
        rv = []
        for s_i in range(n_sec):
            th = 2.0 * math.pi * s_i / n_sec
            r = r_out if (s_i % 2 == 1) else r_in
            rx = r * 1.03
            ry = r * 0.97
            rv.append(bm_dress.verts.new((math.cos(th) * rx, math.sin(th) * ry + yo, sz)))
        all_rings.append(rv)

    # 2. Build bodice rings (from waist up to neckline)
    for r_i, (bz, rx, ry_f, ry_b, cy) in enumerate(b_slices):
        rv = []
        for s_i in range(n_sec):
            th = 2.0 * math.pi * s_i / n_sec
            st, ct = math.sin(th), math.cos(th)
            ry = ry_f if st < 0 else ry_b

            bust_cup = 0.0
            cleavage_valley = 0.0
            if r_i in (2, 3, 4) and st < -0.12:
                x_val = ct * rx
                dz = (bz - 1.040) / 0.052
                cup_l = math.exp(-(((x_val - 0.045) / 0.032) ** 2 + dz ** 2))
                cup_r = math.exp(-(((x_val + 0.045) / 0.032) ** 2 + dz ** 2))
                # 4.2cm natural teardrop projection
                bust_cup = -0.042 * (cup_l + cup_r) * (-st)
                # Defined cleavage valley between breasts
                if abs(x_val) < 0.022:
                    cleavage_valley = 0.012 * (1.0 - (x_val / 0.022) ** 2) * (-st)

            z_dip = 0.0
            if r_i == len(b_slices) - 1: # Neckline rim
                x_val = ct * rx
                if st < 0:
                    if abs(x_val) < 0.042:
                        u_neck = max(0.0, 1.0 - (x_val / 0.042) ** 2)
                        z_dip = -0.026 * u_neck
                    elif abs(x_val) > 0.075:
                        u_arm = min(1.0, (abs(x_val) - 0.075) / (rx - 0.075 + 1e-5))
                        z_dip = -0.008 * u_arm
                elif st > 0.25:
                    z_dip = -0.016 * ((st - 0.25) / 0.75)

            pleat_subtle = 0.0012 * (1.0 if s_i % 2 == 1 else -1.0) if r_i == 0 else 0.0

            px = ct * (rx + pleat_subtle)
            py = cy + st * (ry + pleat_subtle) + bust_cup + cleavage_valley
            pz = bz + z_dip
            rv.append(bm_dress.verts.new((px, py, pz)))
        all_rings.append(rv)

    # 3. Connect all consecutive rings into a single continuous watertight quad mesh
    for r_i in range(len(all_rings) - 1):
        for s_i in range(n_sec):
            ni = (s_i + 1) % n_sec
            bm_dress.faces.new([all_rings[r_i][s_i], all_rings[r_i][ni], all_rings[r_i + 1][ni], all_rings[r_i + 1][s_i]])

    # 4. Thin delicate spaghetti straps (3.2mm wide) over bare shoulders
    w_half = 0.0016
    strap_arch = [
        (-0.072, 1.130),  # Front rim of bodice
        (-0.046, 1.146),  # Over clavicle
        (-0.018, 1.162),  # Front curve of shoulder
        ( 0.008, 1.174),  # Peak of shoulder
        ( 0.035, 1.166),  # Rear slope of shoulder
        ( 0.055, 1.142),  # Descending towards back
        ( 0.068, 1.122),  # Back rim of bodice
    ]

    for s0, s1 in [(37, 38), (46, 47)]:
        vf0 = all_rings[-1][s0]; vf1 = all_rings[-1][s1]
        b0 = (n_sec - s0) % n_sec; b1 = (n_sec - s1) % n_sec
        vb0 = all_rings[-1][b0]; vb1 = all_rings[-1][b1]

        mx = (vf0.co.x + vf1.co.x) * 0.5
        strap_rings = []
        for py_arch, pz_arch in strap_arch:
            v_l = bm_dress.verts.new((mx - w_half, py_arch, pz_arch))
            v_r = bm_dress.verts.new((mx + w_half, py_arch, pz_arch))
            strap_rings.append((v_l, v_r))

        bm_dress.faces.new([vf0, vf1, strap_rings[0][1], strap_rings[0][0]])
        for k in range(len(strap_rings) - 1):
            bm_dress.faces.new([strap_rings[k][0], strap_rings[k][1], strap_rings[k + 1][1], strap_rings[k + 1][0]])
        bm_dress.faces.new([strap_rings[-1][0], strap_rings[-1][1], vb1, vb0])

    for f in bm_dress.faces: f.smooth = True
    dress_m = bpy.data.meshes.new("Beauty_Dress_Mesh")
    bm_dress.to_mesh(dress_m)
    bm_dress.free()
    dress_obj = bpy.data.objects.new("Beauty_Dress", dress_m)
    dress_obj.parent = arm
    scene.collection.objects.link(dress_obj)
    dress_obj.data.materials.append(mat_silk)

    dt_d = dress_obj.modifiers.new("DataTransfer", 'DATA_TRANSFER')
    dt_d.object = body
    dt_d.use_vert_data = True
    dt_d.data_types_verts = {'VGROUP_WEIGHTS'}
    dt_d.vert_mapping = 'NEAREST'
    bpy.context.view_layer.objects.active = dress_obj
    bpy.ops.object.datalayout_transfer(modifier=dt_d.name)
    bpy.ops.object.modifier_apply(modifier=dt_d.name)

    arm_d = dress_obj.modifiers.new("Armature", 'ARMATURE')
    arm_d.object = arm
    sol_d = dress_obj.modifiers.new("Solidify", 'SOLIDIFY')
    sol_d.thickness = 0.0016
    sub_d = dress_obj.modifiers.new("Subsurf", 'SUBSURF')
    sub_d.levels = 1

    # 5. WAIST SASH (Vibrant Ice-blue Satin Ribbon Conforming Snugly to Dress Waist)
    bm_sa = bmesh.new()
    sash_slices = [
        (0.880, 0.086, 0.072, 0.068, -0.033),
        (0.902, 0.084, 0.070, 0.066, -0.033),
        (0.925, 0.083, 0.069, 0.065, -0.034),
    ]
    sa_rings = []
    for sz, rx, ry_f, ry_b, cy in sash_slices:
        rv = []
        for s_i in range(n_sec):
            th = 2.0 * math.pi * s_i / n_sec
            st, ct = math.sin(th), math.cos(th)
            ry = ry_f if st < 0 else ry_b
            rv.append(bm_sa.verts.new((ct * rx, cy + st * ry, sz)))
        sa_rings.append(rv)

    for r_i in range(len(sash_slices) - 1):
        for s_i in range(n_sec):
            ni = (s_i + 1) % n_sec
            bm_sa.faces.new([sa_rings[r_i][s_i], sa_rings[r_i][ni], sa_rings[r_i + 1][ni], sa_rings[r_i + 1][s_i]])

    # Front ribbon bow knot and cascading tails
    k_v0 = bm_sa.verts.new((-0.014, -0.106, 0.924))
    k_v1 = bm_sa.verts.new(( 0.014, -0.106, 0.924))
    k_v2 = bm_sa.verts.new(( 0.014, -0.106, 0.892))
    k_v3 = bm_sa.verts.new((-0.014, -0.106, 0.892))
    bm_sa.faces.new([k_v0, k_v1, k_v2, k_v3])

    # Left and right cascading tails
    w_tail = 0.008
    for side_sign, ang in [(-1.0, 0.08), (1.0, -0.08)]:
        st_x = side_sign * 0.008
        tail_profile = [
            (st_x, -0.108, 0.902),                                # Knot anchor
            (st_x + side_sign * 0.012, -0.145, 0.820),            # Upper skirt drape
            (st_x + side_sign * 0.024, -0.180, 0.720),            # Mid skirt drape
            (st_x + side_sign * 0.034, -0.215, 0.630),            # Fluttering tip
        ]
        t_rings = []
        for px, py, pz in tail_profile:
            vl = bm_sa.verts.new((px - w_tail, py, pz))
            vr = bm_sa.verts.new((px + w_tail, py, pz))
            t_rings.append((vl, vr))
        for k in range(len(t_rings) - 1):
            bm_sa.faces.new([t_rings[k][0], t_rings[k][1], t_rings[k + 1][1], t_rings[k + 1][0]])

    for f in bm_sa.faces: f.smooth = True
    sash_m = bpy.data.meshes.new("Beauty_Waist_Sash_Mesh")
    bm_sa.to_mesh(sash_m)
    bm_sa.free()
    sash_obj = bpy.data.objects.new("Beauty_Waist_Sash", sash_m)
    sash_obj.parent = arm
    scene.collection.objects.link(sash_obj)
    
    # Vibrant rich ice-blue satin shader
    bs_sa.inputs['Base Color'].default_value = (0.28, 0.72, 0.96, 1.0)
    bs_sa.inputs['Roughness'].default_value = 0.18
    if 'Sheen Weight' in bs_sa.inputs: bs_sa.inputs['Sheen Weight'].default_value = 1.0
    sash_obj.data.materials.append(mat_sash)

    dt_sa = sash_obj.modifiers.new("DataTransfer", 'DATA_TRANSFER')
    dt_sa.object = body
    dt_sa.use_vert_data = True
    dt_sa.data_types_verts = {'VGROUP_WEIGHTS'}
    dt_sa.vert_mapping = 'NEAREST'
    bpy.context.view_layer.objects.active = sash_obj
    bpy.ops.object.datalayout_transfer(modifier=dt_sa.name)
    bpy.ops.object.modifier_apply(modifier=dt_sa.name)

    arm_sa = sash_obj.modifiers.new("Armature", 'ARMATURE')
    arm_sa.object = arm
    sol_sa = sash_obj.modifiers.new("Solidify", 'SOLIDIFY')
    sol_sa.thickness = 0.0012
    sub_sa = sash_obj.modifiers.new("Subsurf", 'SUBSURF')
    sub_sa.levels = 1

    # 7. FLAT WHITE STRAP SANDALS
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        sand_m = bpy.data.meshes.new(f"Beauty_Sandal_{side}_Mesh")
        bm_sd = bmesh.new()
        cx = sign * 0.078
        cy_sole = -0.020
        n_sole = 24
        sole_bot, sole_top = [], []
        for i_s in range(n_sole):
            th = 2.0 * math.pi * i_s / n_sole
            sx = cx + math.cos(th) * 0.034
            sy = cy_sole + math.sin(th) * 0.096
            sole_bot.append(bm_sd.verts.new((sx, sy, 0.008)))
            sole_top.append(bm_sd.verts.new((sx, sy, 0.018)))
        for i_s in range(n_sole):
            ni = (i_s + 1) % n_sole
            bm_sd.faces.new([sole_bot[i_s], sole_bot[ni], sole_top[ni], sole_top[i_s]])
        bm_sd.faces.new(sole_top)
        bm_sd.faces.new(list(reversed(sole_bot)))

        # Metatarsal arch strap
        strap_v = []
        for t_p in [0.0, 0.25, 0.5, 0.75, 1.0]:
            st_x = cx + (-0.032 + 0.064 * t_p)
            arch = math.sin(math.pi * t_p) * 0.025
            strap_v.append(bm_sd.verts.new((st_x, cy_sole + 0.018, 0.018 + arch)))
            strap_v.append(bm_sd.verts.new((st_x, cy_sole + 0.034, 0.018 + arch)))
        for i_st in range(4):
            i0 = 2 * i_st
            bm_sd.faces.new([strap_v[i0], strap_v[i0 + 2], strap_v[i0 + 3], strap_v[i0 + 1]])

        for f in bm_sd.faces: f.smooth = True
        bm_sd.to_mesh(sand_m)
        bm_sd.free()
        sand_obj = bpy.data.objects.new(f"Beauty_Sandal_{side}", sand_m)
        sand_obj.parent = arm
        scene.collection.objects.link(sand_obj)

        mat_sand = bpy.data.materials.new(f"Mat_Sandal_{side}")
        mat_sand.use_nodes = True
        bs_sd = next((n for n in mat_sand.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bs_sd:
            bs_sd.inputs['Base Color'].default_value = (0.92, 0.92, 0.94, 1.0)
            bs_sd.inputs['Roughness'].default_value = 0.45
        sand_obj.data.materials.append(mat_sand)

        dt_sd = sand_obj.modifiers.new("DataTransfer", 'DATA_TRANSFER')
        dt_sd.object = body
        dt_sd.use_vert_data = True
        dt_sd.data_types_verts = {'VGROUP_WEIGHTS'}
        dt_sd.vert_mapping = 'NEAREST'
        bpy.context.view_layer.objects.active = sand_obj
        bpy.ops.object.datalayout_transfer(modifier=dt_sd.name)
        bpy.ops.object.modifier_apply(modifier=dt_sd.name)

        arm_sd = sand_obj.modifiers.new("Armature", 'ARMATURE')
        arm_sd.object = arm

    # 8. POSE ARMATURE INTO MARIONETTE PUPPETEER POSE (Natural reference-matching poise)
    if arm:
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode='POSE')
        p_up_l = arm.pose.bones.get('J_Bip_L_UpperArm')
        p_up_r = arm.pose.bones.get('J_Bip_R_UpperArm')
        p_low_l = arm.pose.bones.get('J_Bip_L_LowerArm')
        p_low_r = arm.pose.bones.get('J_Bip_R_LowerArm')
        p_hand_l = arm.pose.bones.get('J_Bip_L_Hand')
        p_hand_r = arm.pose.bones.get('J_Bip_R_Hand')
        p_head = arm.pose.bones.get('J_Bip_C_Head')

        # Upper arms draped down to sides at -65 deg from horizontal T-pose
        if p_up_l and p_up_r:
            p_up_l.rotation_mode = 'XYZ'
            p_up_l.rotation_euler = (math.radians(12), math.radians(6), math.radians(-65))
            p_up_r.rotation_mode = 'XYZ'
            p_up_r.rotation_euler = (math.radians(12), math.radians(-6), math.radians(65))
        if p_low_l and p_low_r:
            p_low_l.rotation_mode = 'XYZ'
            p_low_l.rotation_euler = (math.radians(24), math.radians(-20), math.radians(-10))
            p_low_r.rotation_mode = 'XYZ'
            p_low_r.rotation_euler = (math.radians(24), math.radians(20), math.radians(10))
        if p_hand_l and p_hand_r:
            p_hand_l.rotation_mode = 'XYZ'
            p_hand_l.rotation_euler = (math.radians(-6), math.radians(-8), math.radians(10))
            p_hand_r.rotation_mode = 'XYZ'
            p_hand_r.rotation_euler = (math.radians(-6), math.radians(8), math.radians(-10))
        if p_head:
            p_head.rotation_mode = 'XYZ'
            p_head.rotation_euler = (math.radians(2), math.radians(-2), math.radians(-1))
        bpy.ops.object.mode_set(mode='OBJECT')
        arm.hide_viewport = True
        arm.hide_render = True

    # 9. HAIR: Front Bangs & Sidelocks (Keep slot 1 from Hair)
    if hair:
        hair.name = "Beauty_Hair"
        bm_h = bmesh.new()
        bm_h.from_mesh(hair.data)
        del_h = [f for f in bm_h.faces if f.material_index != 1]
        bmesh.ops.delete(bm_h, geom=del_h, context='FACES_ONLY')
        bmesh.ops.delete(bm_h, geom=[v for v in bm_h.verts if not v.link_faces], context='VERTS')
        for f in bm_h.faces: f.smooth = True
        bm_h.to_mesh(hair.data)
        bm_h.free()
        hair.data.update()

        mat_hair_vrm = hair.data.materials[1] if len(hair.data.materials) > 1 else None
        if mat_hair_vrm and mat_hair_vrm.node_tree:
            tex_img = next((n.image for n in mat_hair_vrm.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None)
            mat_hair_vrm.node_tree.nodes.clear()
            out_h = mat_hair_vrm.node_tree.nodes.new('ShaderNodeOutputMaterial')
            bsdf_h = mat_hair_vrm.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
            bsdf_h.inputs['Base Color'].default_value = (0.014, 0.013, 0.016, 1.0)
            bsdf_h.inputs['Roughness'].default_value = 0.36
            if 'Specular IOR Level' in bsdf_h.inputs: bsdf_h.inputs['Specular IOR Level'].default_value = 0.50
            if 'Anisotropic' in bsdf_h.inputs: bsdf_h.inputs['Anisotropic'].default_value = 0.50
            if tex_img:
                tex_node = mat_hair_vrm.node_tree.nodes.new('ShaderNodeTexImage')
                tex_node.image = tex_img
                mix_s = mat_hair_vrm.node_tree.nodes.new('ShaderNodeMixShader')
                trans_h = mat_hair_vrm.node_tree.nodes.new('ShaderNodeBsdfTransparent')
                mat_hair_vrm.node_tree.links.new(tex_node.outputs['Alpha'], mix_s.inputs['Fac'])
                mat_hair_vrm.node_tree.links.new(trans_h.outputs['BSDF'], mix_s.inputs[1])
                mat_hair_vrm.node_tree.links.new(bsdf_h.outputs['BSDF'], mix_s.inputs[2])
                mat_hair_vrm.node_tree.links.new(mix_s.outputs['Shader'], out_h.inputs['Surface'])
            else:
                mat_hair_vrm.node_tree.links.new(bsdf_h.outputs['BSDF'], out_h.inputs['Surface'])

    # 10. LONG BLACK HAIR CASCADE BEHIND BACK (Graceful anime flow past waist to hips)
    casc_m = bpy.data.meshes.new("Beauty_Hair_Cascade_Mesh")
    bm_c = bmesh.new()

    def build_hair_strand(points, width_profile, camber=0.005, n_sub=8):
        rings = []
        for idx, ((px, py, pz), hw) in enumerate(zip(points, width_profile)):
            row = []
            for j in range(n_sub):
                u = j / (n_sub - 1)
                lx = -hw + 2.0 * hw * u
                arch = (1.0 - (lx / (hw + 1e-5)) ** 2) * camber
                row.append(bm_c.verts.new((px + lx, py + arch, pz)))
            rings.append(row)

        for r_i in range(len(points) - 1):
            for j in range(n_sub - 1):
                bm_c.faces.new([rings[r_i][j], rings[r_i][j + 1], rings[r_i + 1][j + 1], rings[r_i + 1][j]])

    # Center back cascade: tucked neatly behind neck (Z: 1.28 to 1.18), fanning smoothly over shoulder blades
    pts_center = [
        (0.000, 0.082, 1.280),
        (0.000, 0.088, 1.210),
        (0.000, 0.094, 1.100),
        (0.000, 0.088, 0.980),
        (0.000, 0.080, 0.860),
        (0.000, 0.068, 0.740),
        (0.000, 0.056, 0.620),
        (0.000, 0.048, 0.520),
    ]
    w_center = [0.034, 0.046, 0.068, 0.076, 0.068, 0.052, 0.028, 0.004]
    build_hair_strand(pts_center, w_center, camber=0.007)

    # Left & Right back drapes (tucked behind neck, spreading lower down back)
    for sign in [-1.0, 1.0]:
        pts_side = [
            (sign * 0.022, 0.080, 1.275),
            (sign * 0.030, 0.086, 1.200),
            (sign * 0.048, 0.092, 1.100),
            (sign * 0.056, 0.086, 0.980),
            (sign * 0.048, 0.076, 0.860),
            (sign * 0.038, 0.064, 0.740),
            (sign * 0.022, 0.052, 0.610),
        ]
        w_side = [0.016, 0.022, 0.034, 0.038, 0.032, 0.020, 0.004]
        build_hair_strand(pts_side, w_side, camber=0.005)

    for f in bm_c.faces: f.smooth = True
    bm_c.to_mesh(casc_m)
    bm_c.free()
    casc_obj = bpy.data.objects.new("Beauty_Hair_Cascade", casc_m)
    casc_obj.parent = arm
    scene.collection.objects.link(casc_obj)
    casc_obj.data.materials.append(mat_hair)

    dt_c = casc_obj.modifiers.new("DataTransfer", 'DATA_TRANSFER')
    dt_c.object = body
    dt_c.use_vert_data = True
    dt_c.data_types_verts = {'VGROUP_WEIGHTS'}
    dt_c.vert_mapping = 'NEAREST'
    bpy.context.view_layer.objects.active = casc_obj
    bpy.ops.object.datalayout_transfer(modifier=dt_c.name)
    bpy.ops.object.modifier_apply(modifier=dt_c.name)

    arm_c = casc_obj.modifiers.new("Armature", 'ARMATURE')
    arm_c.object = arm
    sol_c = casc_obj.modifiers.new("Solidify", 'SOLIDIFY')
    sol_c.thickness = 0.0008
    sub_c = casc_obj.modifiers.new("Subsurf", 'SUBSURF')
    sub_c.levels = 1

    # 11. 10 LUMINOUS TRANSLUCENT SWALLOWTAIL BUTTERFLIES & CRIMSON SILK THREADS
    mat_bf = bpy.data.materials.new("Mat_Magic_Butterfly_Beauty")
    mat_bf.use_nodes = True
    bs_bf = next((n for n in mat_bf.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bs_bf:
        bs_bf.inputs['Base Color'].default_value = (0.96, 0.98, 1.0, 1.0)
        bs_bf.inputs['Roughness'].default_value = 0.20
        if 'Transmission Weight' in bs_bf.inputs: bs_bf.inputs['Transmission Weight'].default_value = 0.50
        if 'Subsurface Weight' in bs_bf.inputs: bs_bf.inputs['Subsurface Weight'].default_value = 0.25
        if 'Emission Color' in bs_bf.inputs:
            bs_bf.inputs['Emission Color'].default_value = (0.90, 0.95, 1.0, 1.0)
            bs_bf.inputs['Emission Strength'].default_value = 1.8

    bf_positions = [
        Vector((0.36, -0.16, 1.02)), Vector((0.44, -0.06, 1.18)), Vector((0.32, 0.08, 1.28)),
        Vector((0.46, 0.10, 1.06)),  Vector((0.28, -0.20, 0.88)),
        Vector((-0.36, -0.16, 1.02)), Vector((-0.44, -0.06, 1.18)), Vector((-0.32, 0.08, 1.28)),
        Vector((-0.46, 0.10, 1.06)),  Vector((-0.28, -0.20, 0.88)),
    ]

    def make_swallowtail(name, loc, rot, wing_fold_deg=35.0):
        m = bpy.data.meshes.new(f"{name}_Mesh")
        bm = bmesh.new()
        ang = math.radians(wing_fold_deg)
        ca, sa = math.cos(ang), math.sin(ang)

        v_h = bm.verts.new((0, 0.024, 0.002))
        v_m = bm.verts.new((0, 0.000, 0.002))
        v_t = bm.verts.new((0, -0.024, 0.001))

        for sign in [1.0, -1.0]:
            f0 = bm.verts.new((sign * 0.006 * ca, 0.008, 0.002 + 0.006 * sa))
            f1 = bm.verts.new((sign * 0.045 * ca, 0.035, 0.003 + 0.045 * sa))
            f2 = bm.verts.new((sign * 0.088 * ca, 0.052, 0.004 + 0.088 * sa))
            f3 = bm.verts.new((sign * 0.092 * ca, 0.022, 0.003 + 0.092 * sa))
            f4 = bm.verts.new((sign * 0.062 * ca, -0.002, 0.002 + 0.062 * sa))

            h0 = bm.verts.new((sign * 0.072 * ca, -0.020, 0.002 + 0.072 * sa))
            h1 = bm.verts.new((sign * 0.065 * ca, -0.058, 0.002 + 0.065 * sa))
            h2 = bm.verts.new((sign * 0.038 * ca, -0.042, 0.002 + 0.038 * sa))

            bm.faces.new([v_h, f0, f1])
            bm.faces.new([f0, f4, f3, f1])
            bm.faces.new([f1, f3, f2])
            bm.faces.new([f0, v_m, f4])
            bm.faces.new([f4, v_m, v_t, h2])
            bm.faces.new([f4, h2, h1, h0])

        for f in bm.faces: f.smooth = True
        bm.to_mesh(m)
        bm.free()
        obj = bpy.data.objects.new(name, m)
        obj.data.materials.append(mat_bf)
        obj.location = loc
        obj.rotation_euler = rot
        sol = obj.modifiers.new("Solidify", 'SOLIDIFY')
        sol.thickness = 0.0006
        sub = obj.modifiers.new("Subsurf", 'SUBSURF')
        sub.levels = 1
        scene.collection.objects.link(obj)
        return obj

    for i in range(10):
        rot = (
            math.radians(12.0 + (i % 3) * 15.0),
            math.radians(((i % 2) * 2 - 1) * 20.0),
            math.radians((i * 36.0) % 360.0)
        )
        wing_f = 25.0 + (i % 4) * 12.0
        make_swallowtail(f"Beauty_Butterfly_{i:02d}", bf_positions[i], rot, wing_fold_deg=wing_f)

    # Slender crimson silk threads (0.6mm diameter)
    fingertip_anchors = [
        Vector((0.26, -0.08, 0.94)), Vector((0.27, -0.09, 0.93)), Vector((0.28, -0.08, 0.93)),
        Vector((0.27, -0.07, 0.92)), Vector((0.26, -0.06, 0.91)),
        Vector((-0.26, -0.08, 0.94)), Vector((-0.27, -0.09, 0.93)), Vector((-0.28, -0.08, 0.93)),
        Vector((-0.27, -0.07, 0.92)), Vector((-0.26, -0.06, 0.91)),
    ]

    curve_data = bpy.data.curves.new("Beauty_Marionette_Strings_Curve", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = 0.00030 # Slender 0.6mm thread

    for i in range(10):
        p_start = fingertip_anchors[i]
        p_end = bf_positions[i]
        spline = curve_data.splines.new('BEZIER')
        spline.bezier_points.add(1)
        p0 = spline.bezier_points[0]
        p1 = spline.bezier_points[1]
        p0.co = p_start
        p1.co = p_end

        mid = (p_start + p_end) * 0.5
        sag_vec = Vector((0.0, 0.0, -0.035 * (p_end - p_start).length))
        p0.handle_right = p_start + (mid - p_start) * 0.6 + sag_vec
        p0.handle_left = p_start - (p0.handle_right - p_start)
        p1.handle_left = p_end + (mid - p_end) * 0.6 + sag_vec
        p1.handle_right = p_end - (p1.handle_left - p_end)

    strings_obj = bpy.data.objects.new("Beauty_Marionette_Strings", curve_data)
    mat_str = bpy.data.materials.new("Mat_Marionette_RedString_Beauty")
    mat_str.use_nodes = True
    bs_str = next((n for n in mat_str.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bs_str:
        bs_str.inputs['Base Color'].default_value = (0.85, 0.04, 0.06, 1.0)
        bs_str.inputs['Roughness'].default_value = 0.40
        if 'Emission Color' in bs_str.inputs:
            bs_str.inputs['Emission Color'].default_value = (0.75, 0.03, 0.05, 1.0)
            bs_str.inputs['Emission Strength'].default_value = 0.6
    strings_obj.data.materials.append(mat_str)
    scene.collection.objects.link(strings_obj)

    # 12. SEAMLESS INFINITY CYCLORAMA & LIGHTING
    bg_m = bpy.data.meshes.new("Studio_Backdrop_Mesh")
    bm_bg = bmesh.new()
    
    # Smooth curved infinity cyc from floor under feet (Y=-2.5) curving up to wall (Z=3.0)
    cyc_pts = [
        (-2.5, 0.0),
        (-1.5, 0.0),
        (-0.5, 0.0),
        ( 0.5, 0.0),
        ( 1.2, 0.02),
        ( 1.5, 0.12),
        ( 1.7, 0.32),
        ( 1.85, 0.65),
        ( 1.95, 1.10),
        ( 2.00, 1.70),
        ( 2.00, 2.50),
        ( 2.00, 3.20),
    ]
    cyc_rings = []
    for y_c, z_c in cyc_pts:
        vl = bm_bg.verts.new((-3.5, y_c, z_c))
        vr = bm_bg.verts.new(( 3.5, y_c, z_c))
        cyc_rings.append((vl, vr))
    for k in range(len(cyc_rings) - 1):
        bm_bg.faces.new([cyc_rings[k][0], cyc_rings[k][1], cyc_rings[k + 1][1], cyc_rings[k + 1][0]])

    for f in bm_bg.faces: f.smooth = True
    bm_bg.to_mesh(bg_m)
    bm_bg.free()
    bg_obj = bpy.data.objects.new("Studio_Backdrop", bg_m)
    mat_bg = bpy.data.materials.new("Mat_Studio_Backdrop_Beauty")
    mat_bg.use_nodes = True
    bs_bg = next((n for n in mat_bg.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bs_bg:
        bs_bg.inputs['Base Color'].default_value = (0.18, 0.20, 0.24, 1.0)
        bs_bg.inputs['Roughness'].default_value = 0.92
    bg_obj.data.materials.append(mat_bg)
    scene.collection.objects.link(bg_obj)

    target_l = bpy.data.objects.new("Target_Light", None)
    target_l.location = (0.0, 0.0, 1.20)
    scene.collection.objects.link(target_l)

    def add_light(name, loc, color, energy, size):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.color = color
        ld.energy = energy
        ld.size = size
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        tt = lo.constraints.new('TRACK_TO')
        tt.target = target_l
        tt.track_axis = 'TRACK_NEGATIVE_Z'
        tt.up_axis = 'UP_Y'
        scene.collection.objects.link(lo)
        return lo

    add_light("Key_Light", (1.4, -1.6, 1.9), (1.0, 0.96, 0.92), 160.0, 1.5)
    add_light("Fill_Light", (-1.4, -1.4, 1.3), (0.88, 0.94, 1.0), 45.0, 1.8)
    add_light("Rim_Light", (-0.6, 1.5, 1.9), (1.0, 0.96, 0.92), 160.0, 1.2)

    # Target for cameras to focus on chest / portrait center
    target_cam = bpy.data.objects.new("Target_Cam", None)
    target_cam.location = (0.0, -0.02, 1.08)
    scene.collection.objects.link(target_cam)

    # Cameras: Perfectly framed
    # Portrait Camera: 58mm lens at (0, -2.05, 1.26) framing from head to waist sash & ribbons
    cam_p = bpy.data.cameras.new("Cam_Portrait")
    cam_p.lens = 58.0
    cam_p_obj = bpy.data.objects.new("Cam_Portrait", cam_p)
    cam_p_obj.location = (0.0, -2.05, 1.26)
    cam_p_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    scene.collection.objects.link(cam_p_obj)

    # 3/4 Beauty Camera: 62mm lens at (0.95, -1.85, 1.20) tracking bust and silhouette
    cam_tq = bpy.data.cameras.new("Cam_ThreeQuarter")
    cam_tq.lens = 62.0
    cam_tq_obj = bpy.data.objects.new("Cam_ThreeQuarter", cam_tq)
    cam_tq_obj.location = (0.95, -1.85, 1.20)
    tt_tq = cam_tq_obj.constraints.new('TRACK_TO')
    tt_tq.target = target_cam
    tt_tq.track_axis = 'TRACK_NEGATIVE_Z'
    tt_tq.up_axis = 'UP_Y'
    scene.collection.objects.link(cam_tq_obj)

    # FullBody Camera: 50mm lens at (0, -4.2, 0.82) framing entire character head-to-toe
    cam_fb = bpy.data.cameras.new("Cam_FullBody")
    cam_fb.lens = 50.0
    cam_fb_obj = bpy.data.objects.new("Cam_FullBody", cam_fb)
    cam_fb_obj.location = (0.0, -4.2, 0.82)
    cam_fb_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    scene.collection.objects.link(cam_fb_obj)

    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64
    scene.view_settings.view_transform = 'AgX'
    scene.cycles.use_denoising = True

    # Redirect test prototype renders and exports to scratch directory (never overwrite master production files)
    test_out_dir = r"E:\tool\mcp\MorphoMesh\output\beauty_test"
    os.makedirs(test_out_dir, exist_ok=True)

    # Render Portrait
    scene.camera = cam_p_obj
    scene.render.resolution_x = 720
    scene.render.resolution_y = 960
    out_p = os.path.join(test_out_dir, "test_prototype_portrait.png")
    scene.render.filepath = out_p
    bpy.ops.render.render(write_still=True)
    print(f"Rendered test prototype portrait: {out_p}")

    # Render 3/4 Beauty Angle (clearly showing bust profile, cleavage, and waist silhouette)
    scene.camera = cam_tq_obj
    scene.render.resolution_x = 720
    scene.render.resolution_y = 960
    out_tq = os.path.join(test_out_dir, "test_prototype_threequarter.png")
    scene.render.filepath = out_tq
    bpy.ops.render.render(write_still=True)
    print(f"Rendered test prototype 3/4: {out_tq}")

    # Render FullBody
    scene.camera = cam_fb_obj
    scene.render.resolution_x = 720
    scene.render.resolution_y = 1280
    out_fb = os.path.join(test_out_dir, "test_prototype_fullbody.png")
    scene.render.filepath = out_fb
    bpy.ops.render.render(write_still=True)
    print(f"Rendered test prototype fullbody: {out_fb}")

    # Save experimental prototype scenes in test_out_dir
    beauty_blend = os.path.join(test_out_dir, "test_prototype_beauty.blend")
    master_blend = os.path.join(test_out_dir, "test_prototype_master.blend")

    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'
                        space.overlay.show_bones = False

    bpy.ops.wm.save_as_mainfile(filepath=beauty_blend)
    print(f"Saved prototype beauty: {beauty_blend}")
    bpy.ops.wm.save_as_mainfile(filepath=master_blend)
    print(f"Saved prototype master: {master_blend}")

    # Export prototype GLB and FBX to scratch dir
    out_glb = os.path.join(test_out_dir, "test_prototype.glb")
    bpy.ops.export_scene.gltf(filepath=out_glb, export_format='GLB')
    print(f"Exported prototype GLB: {out_glb}")

    out_fbx = os.path.join(test_out_dir, "test_prototype.fbx")
    bpy.ops.export_scene.fbx(filepath=out_fbx)
    print(f"Exported prototype FBX: {out_fbx}")

if __name__ == "__main__":
    run_test()


