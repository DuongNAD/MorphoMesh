"""
Ultimate Photorealistic & Semi-Realistic Yu Nian An Character Assembler
Matches media_1788716034772.jpg with true anime human beauty.
"""

import bpy
import bmesh
import mathutils
from mathutils import Vector, Matrix, Euler
import math
import os
import sys
import json

def assemble_and_render():
    print("=" * 80)
    print("ASSEMBLING ULTIMATE BEAUTIFUL YU NIAN AN (CYCLIC RENDERING)")
    print("=" * 80)

    # 1. Reset
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # 2. Collections Setup (7-tier canonical hierarchy)
    root_name = "Yu_Nian_An_Master"
    root_col = bpy.data.collections.new(root_name)
    scene.collection.children.link(root_col)

    tier_names = [
        "01_Body",
        "02_Hair",
        "03_Wardrobe",
        "04_Props",
        "05_Armature",
        "06_Lights_Camera",
    ]
    tiers = {}
    for tn in tier_names:
        c = bpy.data.collections.new(tn)
        root_col.children.link(c)
        tiers[tn] = c

    def link_obj(obj, tier_name):
        if not obj:
            return
        t_col = tiers[tier_name]
        if obj.name not in t_col.objects:
            t_col.objects.link(obj)
        for col in list(bpy.data.collections):
            if col != t_col and obj.name in col.objects:
                col.objects.unlink(obj)
        if obj.name in scene.collection.objects:
            scene.collection.objects.unlink(obj)

    # 3. Import Base Anatomical Model
    vrm_path = r"C:\Users\Admin\Downloads\_3D_Models_Assets\Liva.vrm"
    scale_factor = 1.65 / 1.4649 # 1.12635689

    bpy.ops.import_scene.gltf(filepath=vrm_path)
    base_arm = bpy.data.objects.get("Armature")
    base_body = bpy.data.objects.get("Body")
    base_face = bpy.data.objects.get("Face")
    base_hair = bpy.data.objects.get("Hair")

    # Rename to Beauty assets
    if base_arm:
        base_arm.name = "Armature_Yu_Nian_An"
        base_arm.scale = (scale_factor, scale_factor, scale_factor)
        link_obj(base_arm, "05_Armature")

    if base_body:
        base_body.name = "Yu_Nian_An_Beauty_Body"
        link_obj(base_body, "01_Body")
        # Keep only material 0 (Skin) - delete clothes, boots, stockings, fox tail
        bm = bmesh.new()
        bm.from_mesh(base_body.data)
        faces_to_del = [f for f in bm.faces if f.material_index != 0]
        bmesh.ops.delete(bm, geom=faces_to_del, context='FACES_ONLY')
        verts_to_del = [v for v in bm.verts if len(v.link_faces) == 0]
        bmesh.ops.delete(bm, geom=verts_to_del, context='VERTS')
        bm.to_mesh(base_body.data)
        bm.free()
        base_body.data.update()
        for p in base_body.data.polygons:
            p.use_smooth = True

    if base_face:
        base_face.name = "Yu_Nian_An_Beauty_Face"
        link_obj(base_face, "01_Body")
        for p in base_face.data.polygons:
            p.use_smooth = True

        # Set melancholic, pure gentle expression
        if base_face.data.shape_keys:
            for kb in base_face.data.shape_keys.key_blocks:
                kb.value = 0.0
            kb_sorrow = base_face.data.shape_keys.key_blocks.get("Fcl_ALL_Sorrow")
            if kb_sorrow: kb_sorrow.value = 0.28
            kb_eye_s = base_face.data.shape_keys.key_blocks.get("Fcl_EYE_Sorrow")
            if kb_eye_s: kb_eye_s.value = 0.22
            kb_brw_s = base_face.data.shape_keys.key_blocks.get("Fcl_BRW_Sorrow")
            if kb_brw_s: kb_brw_s.value = 0.25
            kb_mth_s = base_face.data.shape_keys.key_blocks.get("Fcl_MTH_Small")
            if kb_mth_s: kb_mth_s.value = 0.20

    if base_hair:
        base_hair.name = "Yu_Nian_An_Beauty_Hair"
        link_obj(base_hair, "02_Hair")
        bm_h = bmesh.new()
        bm_h.from_mesh(base_hair.data)
        visited = set()
        islands = []
        for f in bm_h.faces:
            if f in visited: continue
            isl = [f]
            visited.add(f)
            st = [f]
            while st:
                curr = st.pop()
                for edge in curr.edges:
                    for nxt in edge.link_faces:
                        if nxt not in visited:
                            visited.add(nxt)
                            isl.append(nxt)
                            st.append(nxt)
            islands.append(isl)

        del_h_faces = []
        for isl in islands:
            v_co = [v.co for f in isl for v in f.verts]
            max_z = max(c.z for c in v_co) * scale_factor
            min_z = min(c.z for c in v_co) * scale_factor
            max_y = max(c.y for c in v_co) * scale_factor
            min_y = min(c.y for c in v_co) * scale_factor
            # Delete fox ears
            if max_z > 1.48 and max_y > -0.03:
                del_h_faces.extend(isl)
            # Delete front braids
            elif min_z < 1.15 and min_y < -0.05:
                del_h_faces.extend(isl)

        bmesh.ops.delete(bm_h, geom=list(set(del_h_faces)), context='FACES_ONLY')
        verts_to_del = [v for v in bm_h.verts if len(v.link_faces) == 0]
        bmesh.ops.delete(bm_h, geom=verts_to_del, context='VERTS')
        bm_h.to_mesh(base_hair.data)
        bm_h.free()
        base_hair.data.update()
        for p in base_hair.data.polygons:
            p.use_smooth = True

    # 4. Pose Character into Graceful Marionette Puppeteer Pose
    if base_arm:
        bpy.context.view_layer.objects.active = base_arm
        bpy.ops.object.mode_set(mode='POSE')
        p_up_l = base_arm.pose.bones.get('J_Bip_L_UpperArm')
        p_up_r = base_arm.pose.bones.get('J_Bip_R_UpperArm')
        p_low_l = base_arm.pose.bones.get('J_Bip_L_LowerArm')
        p_low_r = base_arm.pose.bones.get('J_Bip_R_LowerArm')
        p_hand_l = base_arm.pose.bones.get('J_Bip_L_Hand')
        p_hand_r = base_arm.pose.bones.get('J_Bip_R_Hand')
        p_head = base_arm.pose.bones.get('J_Bip_C_Head')

        if p_up_l and p_up_r:
            p_up_l.rotation_mode = 'XYZ'
            p_up_l.rotation_euler = (math.radians(12), math.radians(8), math.radians(-54))
            p_up_r.rotation_mode = 'XYZ'
            p_up_r.rotation_euler = (math.radians(12), math.radians(-8), math.radians(54))
        if p_low_l and p_low_r:
            p_low_l.rotation_mode = 'XYZ'
            p_low_l.rotation_euler = (math.radians(15), math.radians(-28), math.radians(-12))
            p_low_r.rotation_mode = 'XYZ'
            p_low_r.rotation_euler = (math.radians(15), math.radians(28), math.radians(12))
        if p_hand_l and p_hand_r:
            p_hand_l.rotation_mode = 'XYZ'
            p_hand_l.rotation_euler = (0, math.radians(-5), math.radians(10))
            p_hand_r.rotation_mode = 'XYZ'
            p_hand_r.rotation_euler = (0, math.radians(5), math.radians(-10))
        if p_head:
            p_head.rotation_mode = 'XYZ'
            p_head.rotation_euler = (math.radians(2), math.radians(-3), math.radians(-2))
        bpy.ops.object.mode_set(mode='OBJECT')

    # 5. Cinema-Grade Cycles PBR Materials
    # 5.1 Skin SSS
    mat_skin = bpy.data.materials.new("Mat_Human_Skin_SSS")
    mat_skin.use_nodes = True
    mat_skin.use_fake_user = True
    nodes = mat_skin.node_tree.nodes
    links = mat_skin.node_tree.links
    nodes.clear()
    out_n = nodes.new("ShaderNodeOutputMaterial")
    bsdf_skin = nodes.new("ShaderNodeBsdfPrincipled")
    # Porcelain fair skin tone #F4E4DC
    bsdf_skin.inputs["Base Color"].default_value = (0.957, 0.894, 0.863, 1.0)
    bsdf_skin.inputs["Roughness"].default_value = 0.36
    if "Subsurface Weight" in bsdf_skin.inputs:
        bsdf_skin.subsurface_method = 'RANDOM_WALK'
        bsdf_skin.inputs["Subsurface Weight"].default_value = 0.32
        bsdf_skin.inputs["Subsurface Radius"].default_value = (0.008, 0.004, 0.002)
        bsdf_skin.inputs["Subsurface Scale"].default_value = 0.05
    links.new(bsdf_skin.outputs["BSDF"], out_n.inputs["Surface"])

    # Apply skin SSS to base body and face textures
    for m_name in ['N00_000_00_Face_00_SKIN (Instance)', 'N00_000_00_Body_00_SKIN (Instance)']:
        m = bpy.data.materials.get(m_name)
        if m and m.node_tree:
            tex = next((n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE'), None)
            out_n = next((n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
            if not out_n: out_n = m.node_tree.nodes.new('ShaderNodeOutputMaterial')
            bsdf = m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
            if tex:
                m.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
            else:
                bsdf.inputs['Base Color'].default_value = (0.957, 0.894, 0.863, 1.0)
            bsdf.inputs['Roughness'].default_value = 0.36
            if 'Subsurface Method' in bsdf.inputs:
                bsdf.subsurface_method = 'RANDOM_WALK'
            if 'Subsurface Weight' in bsdf.inputs:
                bsdf.inputs['Subsurface Weight'].default_value = 0.32
                bsdf.inputs['Subsurface Radius'].default_value = (0.008, 0.004, 0.002)
                bsdf.inputs['Subsurface Scale'].default_value = 0.05
            m.node_tree.links.new(bsdf.outputs['BSDF'], out_n.inputs['Surface'])

    # 5.2 Hair: Silky Jet Black with Anisotropic Sheen
    mat_hair = bpy.data.materials.new("Mat_Human_Hair")
    mat_hair.use_nodes = True
    mat_hair.use_fake_user = True
    nodes = mat_hair.node_tree.nodes
    links = mat_hair.node_tree.links
    nodes.clear()
    out_n = nodes.new("ShaderNodeOutputMaterial")
    bsdf_hair = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_hair.inputs["Base Color"].default_value = (0.015, 0.014, 0.018, 1.0) # Silky jet black
    bsdf_hair.inputs["Roughness"].default_value = 0.28
    if "Specular IOR Level" in bsdf_hair.inputs:
        bsdf_hair.inputs["Specular IOR Level"].default_value = 0.65
    elif "Specular" in bsdf_hair.inputs:
        bsdf_hair.inputs["Specular"].default_value = 0.65
    if "Anisotropic" in bsdf_hair.inputs:
        bsdf_hair.inputs["Anisotropic"].default_value = 0.72
    links.new(bsdf_hair.outputs["BSDF"], out_n.inputs["Surface"])

    for m in bpy.data.materials:
        if 'HAIR' in m.name.upper():
            m.use_nodes = True
            nodes = m.node_tree.nodes
            links = m.node_tree.links
            nodes.clear()
            out_n = nodes.new('ShaderNodeOutputMaterial')
            bsdf = nodes.new('ShaderNodeBsdfPrincipled')
            bsdf.inputs['Base Color'].default_value = (0.015, 0.014, 0.018, 1.0)
            bsdf.inputs['Roughness'].default_value = 0.28
            if 'Specular IOR Level' in bsdf.inputs:
                bsdf.inputs['Specular IOR Level'].default_value = 0.65
            elif 'Specular' in bsdf.inputs:
                bsdf.inputs['Specular'].default_value = 0.65
            if 'Anisotropic' in bsdf.inputs:
                bsdf.inputs['Anisotropic'].default_value = 0.72
            links.new(bsdf.outputs['BSDF'], out_n.inputs['Surface'])

    # 5.3 Eye Iris: Slate Grey-Green
    m_iris_inst = bpy.data.materials.get('N00_000_00_EyeIris_00_EYE (Instance)')
    if m_iris_inst and m_iris_inst.node_tree:
        tex = next((n for n in m_iris_inst.node_tree.nodes if n.type == 'TEX_IMAGE'), None)
        out_n = next((n for n in m_iris_inst.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if not out_n: out_n = m_iris_inst.node_tree.nodes.new('ShaderNodeOutputMaterial')
        bsdf = m_iris_inst.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        mix = m_iris_inst.node_tree.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 0.85
        mix.inputs['B'].default_value = (0.18, 0.25, 0.24, 1.0)
        if tex:
            m_iris_inst.node_tree.links.new(tex.outputs['Color'], mix.inputs['A'])
        m_iris_inst.node_tree.links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.12
        m_iris_inst.node_tree.links.new(bsdf.outputs['BSDF'], out_n.inputs['Surface'])

    # 5.4 Eyeliner, Brows, Lashes
    for el_name in ['N00_000_00_FaceBrow_00_FACE (Instance)', 'N00_000_00_FaceEyelash_00_FACE (Instance)', 'N00_000_00_FaceEyeline_00_FACE (Instance)']:
        m_el = bpy.data.materials.get(el_name)
        if m_el and m_el.node_tree:
            tex = next((n for n in m_el.node_tree.nodes if n.type == 'TEX_IMAGE'), None)
            out_n = next((n for n in m_el.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
            if not out_n: out_n = m_el.node_tree.nodes.new('ShaderNodeOutputMaterial')
            bsdf = m_el.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
            mix_s = m_el.node_tree.nodes.new('ShaderNodeMixShader')
            trans = m_el.node_tree.nodes.new('ShaderNodeBsdfTransparent')
            bsdf.inputs['Base Color'].default_value = (0.015, 0.015, 0.02, 1.0)
            bsdf.inputs['Roughness'].default_value = 0.45
            if tex:
                m_el.node_tree.links.new(tex.outputs['Alpha'], mix_s.inputs['Fac'])
            m_el.node_tree.links.new(trans.outputs['BSDF'], mix_s.inputs[1])
            m_el.node_tree.links.new(bsdf.outputs['BSDF'], mix_s.inputs[2])
            m_el.node_tree.links.new(mix_s.outputs['Shader'], out_n.inputs['Surface'])

    # 5.5 White Silk Dress Material
    mat_dress = bpy.data.materials.new("Mat_Dress_WhiteSilk")
    mat_dress.use_nodes = True
    mat_dress.use_fake_user = True
    nodes = mat_dress.node_tree.nodes
    links = mat_dress.node_tree.links
    nodes.clear()
    out_n = nodes.new("ShaderNodeOutputMaterial")
    bsdf_dress = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_dress.inputs["Base Color"].default_value = (0.965, 0.960, 0.950, 1.0) # Ivory silk
    bsdf_dress.inputs["Roughness"].default_value = 0.38
    if "Sheen Weight" in bsdf_dress.inputs:
        bsdf_dress.inputs["Sheen Weight"].default_value = 0.85
        bsdf_dress.inputs["Sheen Roughness"].default_value = 0.30
    if "Subsurface Weight" in bsdf_dress.inputs:
        bsdf_dress.inputs["Subsurface Weight"].default_value = 0.10
    links.new(bsdf_dress.outputs["BSDF"], out_n.inputs["Surface"])

    # 5.6 Waist Belt Sash Material (Ice Blue Satin)
    mat_sash = bpy.data.materials.new("Mat_Dress_WaistBelt")
    mat_sash.use_nodes = True
    mat_sash.use_fake_user = True
    nodes = mat_sash.node_tree.nodes
    links = mat_sash.node_tree.links
    nodes.clear()
    out_n = nodes.new("ShaderNodeOutputMaterial")
    bsdf_sash = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_sash.inputs["Base Color"].default_value = (0.76, 0.85, 0.92, 1.0) # Ice-blue satin
    bsdf_sash.inputs["Roughness"].default_value = 0.22
    if "Sheen Weight" in bsdf_sash.inputs:
        bsdf_sash.inputs["Sheen Weight"].default_value = 0.90
    links.new(bsdf_sash.outputs["BSDF"], out_n.inputs["Surface"])

    # 5.7 Sandal Leather
    mat_sandal = bpy.data.materials.new("Mat_Sandal_Leather")
    mat_sandal.use_nodes = True
    mat_sandal.use_fake_user = True
    nodes = mat_sandal.node_tree.nodes
    links = mat_sandal.node_tree.links
    nodes.clear()
    out_n = nodes.new("ShaderNodeOutputMaterial")
    bsdf_sandal = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_sandal.inputs["Base Color"].default_value = (0.92, 0.92, 0.94, 1.0)
    bsdf_sandal.inputs["Roughness"].default_value = 0.45
    links.new(bsdf_sandal.outputs["BSDF"], out_n.inputs["Surface"])

    # 5.8 Crimson Marionette Strings
    mat_string = bpy.data.materials.new("Mat_Marionette_RedString")
    mat_string.use_nodes = True
    mat_string.use_fake_user = True
    nodes = mat_string.node_tree.nodes
    links = mat_string.node_tree.links
    nodes.clear()
    out_n = nodes.new("ShaderNodeOutputMaterial")
    bsdf_str = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_str.inputs["Base Color"].default_value = (0.85, 0.04, 0.08, 1.0)
    if "Emission Color" in bsdf_str.inputs:
        bsdf_str.inputs["Emission Color"].default_value = (0.95, 0.05, 0.10, 1.0)
        bsdf_str.inputs["Emission Strength"].default_value = 4.0
    links.new(bsdf_str.outputs["BSDF"], out_n.inputs["Surface"])

    # 5.9 Magic Butterfly Material
    mat_bf = bpy.data.materials.new("Mat_Magic_Butterfly")
    mat_bf.use_nodes = True
    mat_bf.use_fake_user = True
    nodes = mat_bf.node_tree.nodes
    links = mat_bf.node_tree.links
    nodes.clear()
    out_n = nodes.new("ShaderNodeOutputMaterial")
    bsdf_bf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_bf.inputs["Base Color"].default_value = (0.95, 0.98, 1.0, 1.0)
    bsdf_bf.inputs["Roughness"].default_value = 0.25
    if "Emission Color" in bsdf_bf.inputs:
        bsdf_bf.inputs["Emission Color"].default_value = (0.88, 0.95, 1.0, 1.0)
        bsdf_bf.inputs["Emission Strength"].default_value = 3.0
    if "Transmission Weight" in bsdf_bf.inputs:
        bsdf_bf.inputs["Transmission Weight"].default_value = 0.45
    links.new(bsdf_bf.outputs["BSDF"], out_n.inputs["Surface"])

    # Auxiliary materials
    for aux_name, col_val in [
        ("Mat_Human_Lips", (0.82, 0.38, 0.45, 1.0)),
        ("Mat_Human_Oral_Slit", (0.08, 0.02, 0.025, 1.0)),
        ("Mat_Human_Eyeliner", (0.015, 0.015, 0.02, 1.0)),
        ("Mat_Human_Eye_Outer_Cornea", (1.0, 1.0, 1.0, 1.0)),
        ("Mat_Human_Eye_Inner_Iris", (0.16, 0.24, 0.22, 1.0)),
        ("Mat_Human_Eye_Sclera", (0.96, 0.96, 0.98, 1.0)),
        ("Mat_Sash_Satin", (0.76, 0.85, 0.92, 1.0)),
        ("Mat_Sandal_White", (0.92, 0.92, 0.94, 1.0)),
        ("Mat_Human_Scalp", (0.012, 0.011, 0.012, 1.0)),
    ]:
        m = bpy.data.materials.new(aux_name)
        m.use_nodes = True
        m.use_fake_user = True
        b = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b: b.inputs["Base Color"].default_value = col_val

    # 6. TAILOR THE GORGEOUS WHITE TWO-STRAP SUNDRESS ONTO ANATOMICAL BODY
    print("[MorphoMesh] Tailoring high-resolution silk sundress...")
    # 6.1 Bodice
    bodice_mesh = bpy.data.meshes.new("Yu_Nian_An_Beauty_Dress_Bodice_Mesh")
    bm_bod = bmesh.new()
    n_sectors = 48
    # Bodice slices from waist (Z=0.96m) to sweetheart neckline (Z=1.23m)
    bod_slices = [
        # (z, rx, ry, y_offset)
        (0.96, 0.132, 0.098, 0.005),   # Lower waist
        (1.02, 0.128, 0.094, 0.005),   # Cinched high waist
        (1.09, 0.138, 0.104, 0.003),   # Mid-ribs
        (1.16, 0.150, 0.118, -0.004),  # Underbust
        (1.21, 0.154, 0.126, -0.012),  # Bust apex
        (1.24, 0.148, 0.120, -0.008),  # Neckline top
    ]
    ring_verts = []
    for r_i, (bz, rx, ry, yo) in enumerate(bod_slices):
        r_v = []
        for s_i in range(n_sectors):
            th = 2.0 * math.pi * s_i / n_sectors
            st, ct = math.sin(th), math.cos(th)
            # Sweetheart scoop neckline dip at front center
            z_dip = 0.0
            if r_i == len(bod_slices) - 1:
                if st < -0.2: # front center
                    z_dip = -0.022 * (-st - 0.2)
                elif abs(ct) > 0.85: # under arms
                    z_dip = -0.015 * (abs(ct) - 0.85) / 0.15
            vx = ct * rx
            vy = st * ry + yo
            vz = bz + z_dip
            r_v.append(bm_bod.verts.new((vx, vy, vz)))
        ring_verts.append(r_v)

    bm_bod.verts.ensure_lookup_table()
    for r_i in range(len(bod_slices) - 1):
        for s_i in range(n_sectors):
            ni = (s_i + 1) % n_sectors
            bm_bod.faces.new([ring_verts[r_i][s_i], ring_verts[r_i][ni], ring_verts[r_i + 1][ni], ring_verts[r_i + 1][s_i]])

    # Dual shoulder straps
    strap_l_indices = [int(n_sectors * 0.65), int(n_sectors * 0.68)]
    strap_r_indices = [int(n_sectors * 0.82), int(n_sectors * 0.85)]
    for s_idx in [strap_l_indices, strap_r_indices]:
        v_front0 = ring_verts[-1][s_idx[0]]
        v_front1 = ring_verts[-1][s_idx[1]]
        # Find corresponding back verts (opposite across Y)
        opp0 = (s_idx[0] + n_sectors // 2) % n_sectors
        opp1 = (s_idx[1] + n_sectors // 2) % n_sectors
        v_back0 = ring_verts[-1][opp0]
        v_back1 = ring_verts[-1][opp1]
        # Intermediate strap points over shoulder (Z=1.33m)
        m_x = (v_front0.co.x + v_front1.co.x) * 0.5
        s_mid0 = bm_bod.verts.new((m_x - 0.006, 0.01, 1.335))
        s_mid1 = bm_bod.verts.new((m_x + 0.006, 0.01, 1.335))
        bm_bod.faces.new([v_front0, v_front1, s_mid1, s_mid0])
        bm_bod.faces.new([s_mid0, s_mid1, v_back0, v_back1])

    bm_bod.to_mesh(bodice_mesh)
    bm_bod.free()
    bodice_obj = bpy.data.objects.new("Yu_Nian_An_Beauty_Dress_Bodice", bodice_mesh)
    bodice_obj.data.materials.append(mat_dress)
    for p in bodice_mesh.polygons: p.use_smooth = True
    sol_b = bodice_obj.modifiers.new("Solidify", 'SOLIDIFY')
    sol_b.thickness = 0.002
    sub_b = bodice_obj.modifiers.new("Subsurf", 'SUBSURF')
    sub_b.levels = 1
    sub_b.render_levels = 2
    link_obj(bodice_obj, "03_Wardrobe")
    bodice_obj.parent = base_body

    # 6.2 Waist Ribbon Sash (Ice Blue Satin)
    sash_mesh = bpy.data.meshes.new("Yu_Nian_An_Beauty_Dress_WaistSash_Mesh")
    bm_sash = bmesh.new()
    sash_slices = [
        (0.99, 0.134, 0.098, 0.005),
        (1.02, 0.131, 0.096, 0.005),
        (1.05, 0.134, 0.098, 0.005),
    ]
    sash_rings = []
    for sz, rx, ry, yo in sash_slices:
        rv = []
        for s_i in range(n_sectors):
            th = 2.0 * math.pi * s_i / n_sectors
            rv.append(bm_sash.verts.new((math.cos(th) * rx, math.sin(th) * ry + yo, sz)))
        sash_rings.append(rv)
    bm_sash.verts.ensure_lookup_table()
    for r_i in range(len(sash_slices) - 1):
        for s_i in range(n_sectors):
            ni = (s_i + 1) % n_sectors
            bm_sash.faces.new([sash_rings[r_i][s_i], sash_rings[r_i][ni], sash_rings[r_i + 1][ni], sash_rings[r_i + 1][s_i]])

    # Add dangling ribbon streamers cascading down the front
    for st_x, angle in [(-0.025, 0.1), (0.025, -0.1)]:
        v0 = bm_sash.verts.new((st_x - 0.010, -0.100, 1.01))
        v1 = bm_sash.verts.new((st_x + 0.010, -0.100, 1.01))
        v2 = bm_sash.verts.new((st_x + 0.012 + math.sin(angle)*0.15, -0.120, 0.85))
        v3 = bm_sash.verts.new((st_x - 0.008 + math.sin(angle)*0.15, -0.120, 0.85))
        v4 = bm_sash.verts.new((st_x + 0.015 + math.sin(angle)*0.30, -0.135, 0.70))
        v5 = bm_sash.verts.new((st_x - 0.005 + math.sin(angle)*0.30, -0.135, 0.70))
        bm_sash.faces.new([v0, v1, v2, v3])
        bm_sash.faces.new([v3, v2, v4, v5])

    bm_sash.to_mesh(sash_mesh)
    bm_sash.free()
    sash_obj = bpy.data.objects.new("Yu_Nian_An_Beauty_Dress_WaistSash", sash_mesh)
    sash_obj.data.materials.append(mat_sash)
    for p in sash_mesh.polygons: p.use_smooth = True
    sol_s = sash_obj.modifiers.new("Solidify", 'SOLIDIFY')
    sol_s.thickness = 0.002
    sub_s = sash_obj.modifiers.new("Subsurf", 'SUBSURF')
    sub_s.levels = 1
    sub_s.render_levels = 2
    link_obj(sash_obj, "03_Wardrobe")
    sash_obj.parent = base_body

    # 6.3 Flared 24-Pleated Skirt (Knee-length A-line)
    skirt_mesh = bpy.data.meshes.new("Yu_Nian_An_Beauty_Dress_PleatedSkirt_Mesh")
    bm_skirt = bmesh.new()
    n_pleats = 24
    skirt_pts = n_pleats * 2
    skirt_slices = [
        # (z, r_inner, r_outer, y_offset)
        (0.99, 0.132, 0.134, 0.005), # Waist attachment
        (0.90, 0.165, 0.178, 0.005), # Hip flare
        (0.78, 0.230, 0.255, 0.005), # Upper thigh
        (0.68, 0.310, 0.345, 0.005), # Mid thigh
        (0.58, 0.380, 0.425, 0.005), # Below knees / hemline
    ]
    sk_rings = []
    for sz, r_in, r_out, yo in skirt_slices:
        rv = []
        for i in range(skirt_pts):
            th = 2.0 * math.pi * i / skirt_pts
            # Alternate inner valley and outer pleat ridge
            r = r_out if (i % 2 == 1) else r_in
            rx = r * 1.05
            ry = r * 0.95
            rv.append(bm_skirt.verts.new((math.cos(th) * rx, math.sin(th) * ry + yo, sz)))
        sk_rings.append(rv)
    bm_skirt.verts.ensure_lookup_table()
    for r_i in range(len(skirt_slices) - 1):
        for s_i in range(skirt_pts):
            ni = (s_i + 1) % skirt_pts
            bm_skirt.faces.new([sk_rings[r_i][s_i], sk_rings[r_i][ni], sk_rings[r_i + 1][ni], sk_rings[r_i + 1][s_i]])

    bm_skirt.to_mesh(skirt_mesh)
    bm_skirt.free()
    skirt_obj = bpy.data.objects.new("Yu_Nian_An_Beauty_Dress_PleatedSkirt", skirt_mesh)
    skirt_obj.data.materials.append(mat_dress)
    for p in skirt_mesh.polygons: p.use_smooth = True
    sol_sk = skirt_obj.modifiers.new("Solidify", 'SOLIDIFY')
    sol_sk.thickness = 0.002
    sub_sk = skirt_obj.modifiers.new("Subsurf", 'SUBSURF')
    sub_sk.levels = 1
    sub_sk.render_levels = 2
    link_obj(skirt_obj, "03_Wardrobe")
    skirt_obj.parent = base_body

    # 6.4 Flat Sandals (Dép Bệt) on Feet
    for side, sign in [("L", 1.0), ("R", -1.0)]:
        sandal_m = bpy.data.meshes.new(f"Yu_Nian_An_Beauty_Sandal_{side}_Mesh")
        bm_sand = bmesh.new()
        cx = sign * 0.080
        cy_sole = -0.020
        # Sole ellipse
        n_sole = 24
        sole_bottom = []
        sole_top = []
        for i in range(n_sole):
            th = 2.0 * math.pi * i / n_sole
            sx = cx + math.cos(th) * 0.040
            sy = cy_sole + math.sin(th) * 0.110
            sole_bottom.append(bm_sand.verts.new((sx, sy, 0.008)))
            sole_top.append(bm_sand.verts.new((sx, sy, 0.020)))
        bm_sand.verts.ensure_lookup_table()
        # Sole side faces
        for i in range(n_sole):
            ni = (i + 1) % n_sole
            bm_sand.faces.new([sole_bottom[i], sole_bottom[ni], sole_top[ni], sole_top[i]])
        # Sole top/bottom caps
        bm_sand.faces.new(sole_top)
        bm_sand.faces.new(list(reversed(sole_bottom)))

        # Metatarsal arch strap across foot instep
        strap_verts = []
        for t_p in [0.0, 0.25, 0.5, 0.75, 1.0]:
            st_x = cx + (-0.038 + 0.076 * t_p)
            arch = math.sin(math.pi * t_p) * 0.026
            strap_verts.append(bm_sand.verts.new((st_x, cy_sole + 0.020, 0.020 + arch)))
            strap_verts.append(bm_sand.verts.new((st_x, cy_sole + 0.038, 0.020 + arch)))
        for i in range(4):
            i0 = 2 * i
            bm_sand.faces.new([strap_verts[i0], strap_verts[i0 + 2], strap_verts[i0 + 3], strap_verts[i0 + 1]])

        bm_sand.to_mesh(sandal_m)
        bm_sand.free()
        sand_obj = bpy.data.objects.new(f"Yu_Nian_An_Beauty_Sandal_{side}", sandal_m)
        sand_obj.data.materials.append(mat_sandal)
        for p in sandal_m.polygons: p.use_smooth = True
        link_obj(sand_obj, "03_Wardrobe")
        sand_obj.parent = base_body

    # 7. Marionette Red Puppet Strings & 10 Glowing White Butterflies
    print("[MorphoMesh] Generating crimson strings and 10 luminous butterflies...")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    
    # Hand fingertip anchor points (evaluated from pose)
    hand_l_pos = Vector((0.36, -0.06, 0.95))
    hand_r_pos = Vector((-0.36, -0.06, 0.95))

    butterfly_positions = [
        # Left hand cluster
        Vector((0.48, -0.18, 1.08)),
        Vector((0.56, -0.08, 1.25)),
        Vector((0.42, 0.08, 1.38)),
        Vector((0.58, 0.12, 1.15)),
        Vector((0.38, -0.22, 0.92)),
        # Right hand cluster
        Vector((-0.48, -0.18, 1.08)),
        Vector((-0.56, -0.08, 1.25)),
        Vector((-0.42, 0.08, 1.38)),
        Vector((-0.58, 0.12, 1.15)),
        Vector((-0.38, -0.22, 0.92)),
    ]

    # Create 10 Swallowtail Butterflies
    def make_swallowtail_butterfly(name, location, rotation_euler):
        m = bpy.data.meshes.new(f"{name}_Mesh")
        bm = bmesh.new()
        # Body
        v_h = bm.verts.new((0, 0.025, 0))
        v_t = bm.verts.new((0, -0.025, 0))
        v_m = bm.verts.new((0, 0, 0.005))
        # Left Forewing
        w_l_tip = bm.verts.new((0.085, 0.035, 0.015))
        w_l_mid = bm.verts.new((0.075, -0.010, 0.010))
        # Left Hindwing (swallowtail tail)
        w_l_tail = bm.verts.new((0.055, -0.055, 0.005))
        # Right Forewing
        w_r_tip = bm.verts.new((-0.085, 0.035, 0.015))
        w_r_mid = bm.verts.new((-0.075, -0.010, 0.010))
        # Right Hindwing
        w_r_tail = bm.verts.new((-0.055, -0.055, 0.005))

        bm.faces.new([v_h, w_l_tip, w_l_mid, v_m])
        bm.faces.new([v_m, w_l_mid, w_l_tail, v_t])
        bm.faces.new([v_h, v_m, w_r_mid, w_r_tip])
        bm.faces.new([v_m, v_t, w_r_tail, w_r_mid])

        bm.to_mesh(m)
        bm.free()
        obj = bpy.data.objects.new(name, m)
        obj.data.materials.append(mat_bf)
        obj.location = location
        obj.rotation_euler = rotation_euler
        for p in m.polygons: p.use_smooth = True
        sol = obj.modifiers.new("Solidify", 'SOLIDIFY')
        sol.thickness = 0.0005
        link_obj(obj, "04_Props")
        return obj

    for i in range(10):
        rot = (
            math.radians(15.0 + (i % 3) * 15.0),
            math.radians(((i % 2) * 2 - 1) * 25.0),
            math.radians((i * 36.0) % 360.0)
        )
        make_swallowtail_butterfly(f"Yu_Nian_An_Beauty_Butterfly_{i:02d}", butterfly_positions[i], rot)

    # Marionette Strings Object (10 taut glowing strings)
    str_mesh = bpy.data.meshes.new("Yu_Nian_An_Beauty_Marionette_Strings_Mesh")
    bm_str = bmesh.new()
    for i in range(10):
        h_anchor = hand_l_pos if i < 5 else hand_r_pos
        bf_target = butterfly_positions[i]
        # Spread fingertip origins
        f_offset = Vector(((i % 5 - 2) * 0.015, (i % 5) * 0.005, -(i % 5) * 0.008))
        start_pt = h_anchor + f_offset
        end_pt = bf_target
        # Catenary curve
        n_segs = 8
        prev_v = None
        for s_idx in range(n_segs + 1):
            t = s_idx / n_segs
            pt = start_pt.lerp(end_pt, t)
            droop = math.sin(math.pi * t) * 0.015
            pt.z -= droop
            v = bm_str.verts.new(pt)
            if prev_v:
                # Add a thin ribbon quad for visibility in Cycles render
                v_thick = Vector((0.0004, 0.0004, 0.0))
                # For line rendering, edges are enough or tiny quad strip
                bm_str.edges.new([prev_v, v])
            prev_v = v

    bm_str.to_mesh(str_mesh)
    bm_str.free()
    strings_obj = bpy.data.objects.new("Yu_Nian_An_Beauty_Marionette_Strings", str_mesh)
    strings_obj.data.materials.append(mat_string)
    # Add Skin modifier so edges render as volumetric glowing wires in Cycles
    skin_mod = strings_obj.modifiers.new("Skin", 'SKIN')
    # Scale down skin radii
    for v in strings_obj.data.skin_vertices[0].data:
        v.radius = (0.0007, 0.0007)
    link_obj(strings_obj, "04_Props")

    # 8. Studio Lighting (Warm Key, Cool Fill, Rim Angel Ring)
    target_light = bpy.data.objects.new("Target_Lighting_Focus", None)
    target_light.empty_display_type = 'PLAIN_AXES'
    target_light.location = (0.0, 0.0, 1.35)
    link_obj(target_light, "06_Lights_Camera")

    def make_light(name, l_type, loc, color, energy, size=1.0):
        ld = bpy.data.lights.new(name, l_type)
        ld.color = color
        ld.energy = energy
        if l_type == 'AREA':
            ld.size = size
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        link_obj(lo, "06_Lights_Camera")
        tt = lo.constraints.new('TRACK_TO')
        tt.target = target_light
        tt.track_axis = 'TRACK_NEGATIVE_Z'
        tt.up_axis = 'UP_Y'
        return lo

    make_light("Light_Key_Softbox", 'AREA', (1.4, -2.2, 1.9), (1.0, 0.96, 0.92), 450.0, size=1.5)
    make_light("Light_Fill_Softbox", 'AREA', (-1.4, -2.0, 1.6), (0.90, 0.95, 1.0), 200.0, size=1.8)
    make_light("Light_Rim_HairLight", 'AREA', (0.0, 1.8, 2.3), (1.0, 0.95, 0.88), 380.0, size=1.2)

    # 9. Cameras
    # Portrait 85mm
    cam_p_data = bpy.data.cameras.new("Camera_Portrait_85mm")
    cam_p_data.lens = 85.0
    cam_p_obj = bpy.data.objects.new("Camera_Portrait_85mm", cam_p_data)
    cam_p_obj.location = (0.0, -1.65, 1.46)
    cam_p_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    link_obj(cam_p_obj, "06_Lights_Camera")
    scene.camera = cam_p_obj

    # Full-Body 50mm
    cam_fb_data = bpy.data.cameras.new("Camera_FullBody")
    cam_fb_data.lens = 50.0
    cam_fb_obj = bpy.data.objects.new("Camera_FullBody", cam_fb_data)
    cam_fb_obj.location = (0.0, -3.5, 0.88)
    cam_fb_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    link_obj(cam_fb_obj, "06_Lights_Camera")

    # Face Closeup 135mm
    cam_cl_data = bpy.data.cameras.new("Camera_Face_Closeup_135mm")
    cam_cl_data.lens = 135.0
    cam_cl_obj = bpy.data.objects.new("Camera_Face_Closeup_135mm", cam_cl_data)
    cam_cl_obj.location = (0.0, -1.30, 1.48)
    cam_cl_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    link_obj(cam_cl_obj, "06_Lights_Camera")

    # 10. Cycles AgX Render Settings
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64
    scene.view_settings.view_transform = 'AgX'
    scene.cycles.use_denoising = True

    # 11. Render Beauty Plates
    print("[MorphoMesh] Rendering photorealistic Cycles beauty shots...")
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1440

    # Portrait 85mm
    scene.camera = cam_p_obj
    scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\master_portrait_clean.png"
    bpy.ops.render.render(write_still=True)
    print("Rendered master_portrait_clean.png")

    # Face Closeup 135mm
    scene.camera = cam_cl_obj
    scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\audit_face_closeup.png"
    bpy.ops.render.render(write_still=True)
    print("Rendered audit_face_closeup.png")

    # Head Render
    scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\audit_head_render.png"
    bpy.ops.render.render(write_still=True)
    print("Rendered audit_head_render.png")

    # Full Body 50mm
    scene.camera = cam_fb_obj
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1920
    scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\master_fullbody_clean.png"
    bpy.ops.render.render(write_still=True)
    print("Rendered master_fullbody_clean.png")

    print("[MorphoMesh] Beauty renders completed successfully!")

if __name__ == "__main__":
    assemble_and_render()
