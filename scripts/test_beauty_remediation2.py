import bpy
import bmesh
import math
from mathutils import Vector

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# 1. Materials
def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_fake_user = True
    return m

# Skin (warm porcelain anime tone)
mat_skin = new_mat("Mat_Human_Skin_SSS")
b_sk = next(n for n in mat_skin.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
b_sk.inputs["Base Color"].default_value = (0.92, 0.77, 0.71, 1.0)
b_sk.inputs["Roughness"].default_value = 0.38
if "Subsurface Weight" in b_sk.inputs:
    b_sk.subsurface_method = 'RANDOM_WALK'
    b_sk.inputs["Subsurface Weight"].default_value = 0.35
    b_sk.inputs["Subsurface Radius"].default_value = (0.025, 0.012, 0.007)
    b_sk.inputs["Subsurface Scale"].default_value = 0.03

# Silky jet black hair
mat_hair = new_mat("Mat_Human_Hair")
b_h = next(n for n in mat_hair.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
b_h.inputs["Base Color"].default_value = (0.014, 0.013, 0.016, 1.0)
b_h.inputs["Roughness"].default_value = 0.28
if "Specular IOR Level" in b_h.inputs: b_h.inputs["Specular IOR Level"].default_value = 0.65
if "Anisotropic" in b_h.inputs: b_h.inputs["Anisotropic"].default_value = 0.75
if "Coat Weight" in b_h.inputs: b_h.inputs["Coat Weight"].default_value = 0.12

# White silk dress (with contrast against skin)
mat_dress = new_mat("Mat_Dress_WhiteSilk")
b_d = next(n for n in mat_dress.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
b_d.inputs["Base Color"].default_value = (0.86, 0.86, 0.88, 1.0)
b_d.inputs["Roughness"].default_value = 0.34
if "Sheen Weight" in b_d.inputs:
    b_d.inputs["Sheen Weight"].default_value = 0.85
    b_d.inputs["Sheen Roughness"].default_value = 0.25
if "Subsurface Weight" in b_d.inputs:
    b_d.inputs["Subsurface Weight"].default_value = 0.06

# Vibrant ice-blue satin waist sash
mat_sash = new_mat("Mat_Dress_WaistBelt")
b_sa = next(n for n in mat_sash.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
b_sa.inputs["Base Color"].default_value = (0.24, 0.58, 0.84, 1.0) # Vibrant ice-blue
b_sa.inputs["Roughness"].default_value = 0.20
if "Sheen Weight" in b_sa.inputs: b_sa.inputs["Sheen Weight"].default_value = 1.0

# Leather sandals
mat_sandal = new_mat("Mat_Sandal_Leather")
b_sd = next(n for n in mat_sandal.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
b_sd.inputs["Base Color"].default_value = (0.90, 0.90, 0.92, 1.0)
b_sd.inputs["Roughness"].default_value = 0.40

# Crimson silk strings
mat_str = new_mat("Mat_Marionette_RedString")
b_st = next(n for n in mat_str.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
b_st.inputs["Base Color"].default_value = (0.88, 0.02, 0.06, 1.0)
if "Emission Color" in b_st.inputs:
    b_st.inputs["Emission Color"].default_value = (0.92, 0.05, 0.08, 1.0)
    b_st.inputs["Emission Strength"].default_value = 3.5

# Translucent glowing white magic butterflies
mat_bf = new_mat("Mat_Magic_Butterfly")
b_bf = next(n for n in mat_bf.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
b_bf.inputs["Base Color"].default_value = (0.94, 0.98, 1.0, 1.0)
b_bf.inputs["Roughness"].default_value = 0.18
if "Emission Color" in b_bf.inputs:
    b_bf.inputs["Emission Color"].default_value = (0.85, 0.95, 1.0, 1.0)
    b_bf.inputs["Emission Strength"].default_value = 2.5
if "Transmission Weight" in b_bf.inputs:
    b_bf.inputs["Transmission Weight"].default_value = 0.60

# 2. Import VRM
vrm_path = r"C:\Users\Admin\Downloads\_3D_Models_Assets\Liva.vrm"
scale_factor = 1.65 / 1.4649
bpy.ops.import_scene.gltf(filepath=vrm_path)
arm = bpy.data.objects.get("Armature")
body = bpy.data.objects.get("Body")
face = bpy.data.objects.get("Face")
hair = bpy.data.objects.get("Hair")

if arm:
    arm.name = "Yu_Nian_An_Beauty_Armature"
    arm.scale = (scale_factor, scale_factor, scale_factor)

for o in list(bpy.data.objects):
    if 'Icosphere' in o.name or o.name.startswith('J_Sec_') or o.name.startswith('J_Opt_'):
        bpy.data.objects.remove(o, do_unlink=True)

# 3. Armature Puppeteer Pose
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

    if p_up_l and p_up_r:
        p_up_l.rotation_mode = 'XYZ'
        p_up_l.rotation_euler = (math.radians(12), math.radians(6), math.radians(-52))
        p_up_r.rotation_mode = 'XYZ'
        p_up_r.rotation_euler = (math.radians(12), math.radians(-6), math.radians(52))
    if p_low_l and p_low_r:
        p_low_l.rotation_mode = 'XYZ'
        p_low_l.rotation_euler = (math.radians(20), math.radians(-18), math.radians(-10))
        p_low_r.rotation_mode = 'XYZ'
        p_low_r.rotation_euler = (math.radians(20), math.radians(18), math.radians(10))
    if p_hand_l and p_hand_r:
        p_hand_l.rotation_mode = 'XYZ'
        p_hand_l.rotation_euler = (math.radians(-6), math.radians(-6), math.radians(10))
        p_hand_r.rotation_mode = 'XYZ'
        p_hand_r.rotation_euler = (math.radians(-6), math.radians(6), math.radians(-10))
    if p_head:
        p_head.rotation_mode = 'XYZ'
        p_head.rotation_euler = (math.radians(2), math.radians(-2), math.radians(-1))
    bpy.ops.object.mode_set(mode='OBJECT')

# 4. Face Features & Expression
if face:
    face.name = "Yu_Nian_An_Beauty_Face"
    for p in face.data.polygons: p.use_smooth = True
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

    m_iris = bpy.data.materials.get("N00_000_00_EyeIris_00_EYE (Instance)")
    if m_iris and m_iris.node_tree:
        em_n = next((n for n in m_iris.node_tree.nodes if n.type == 'EMISSION'), None)
        tex_n = next((n for n in m_iris.node_tree.nodes if n.type == 'TEX_IMAGE'), None)
        if em_n and tex_n:
            mix_n = m_iris.node_tree.nodes.new('ShaderNodeMix')
            mix_n.data_type = 'RGBA'
            mix_n.blend_type = 'MULTIPLY'
            mix_n.inputs['Factor'].default_value = 0.85
            mix_n.inputs['B'].default_value = (0.18, 0.26, 0.25, 1.0)
            m_iris.node_tree.links.new(tex_n.outputs['Color'], mix_n.inputs['A'])
            m_iris.node_tree.links.new(mix_n.outputs['Result'], em_n.inputs['Color'])

    m_fskin = bpy.data.materials.get("N00_000_00_Face_00_SKIN (Instance)")
    if m_fskin and m_fskin.node_tree:
        tex_f = next((n for n in m_fskin.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None)
        bsdf_f = next((n for n in m_fskin.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf_f:
            bsdf_f.inputs['Roughness'].default_value = 0.36
            if 'Subsurface Method' in bsdf_f.inputs: bsdf_f.subsurface_method = 'RANDOM_WALK'
            if 'Subsurface Weight' in bsdf_f.inputs:
                bsdf_f.inputs['Subsurface Weight'].default_value = 0.32
                bsdf_f.inputs['Subsurface Radius'].default_value = (0.025, 0.012, 0.007)
                bsdf_f.inputs['Subsurface Scale'].default_value = 0.03
            if tex_f:
                # Soft rosy tint
                mix_f = m_fskin.node_tree.nodes.new('ShaderNodeMix')
                mix_f.data_type = 'RGBA'
                mix_f.blend_type = 'MULTIPLY'
                mix_f.inputs['Factor'].default_value = 0.15
                mix_f.inputs['B'].default_value = (1.0, 0.92, 0.88, 1.0)
                m_fskin.node_tree.links.new(tex_f.outputs['Color'], mix_f.inputs['A'])
                m_fskin.node_tree.links.new(mix_f.outputs['Result'], bsdf_f.inputs['Base Color'])

# 5. Body Mesh & Slender Anime Arms
if body:
    body.name = "Yu_Nian_An_Beauty_Figure"
    bm = bmesh.new()
    bm.from_mesh(body.data)
    
    del_f = [f for f in bm.faces if f.material_index not in {0, 1, 6}]
    
    # Prune jacket/collar from slot 6
    s6_faces = [f for f in bm.faces if f.material_index == 6]
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
            
    # Delete internal pelvis faces
    for f in bm.faces:
        if f.material_index == 0:
            avg_z = sum(v.co.z for v in f.verts) / len(f.verts)
            max_ax = max(abs(v.co.x) for v in f.verts)
            if 0.60 < avg_z < 0.90 and max_ax < 0.080:
                del_f.append(f)
                
    bmesh.ops.delete(bm, geom=list(set(del_f)), context='FACES_ONLY')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    
    # Weld sleeve rim to torso armhole
    yc_arm, zc_arm = 0.0219, 1.1445
    for side_sign in [1.0, -1.0]:
        s_open = [v for v in bm.verts if any(f.material_index == 6 for f in v.link_faces)
                  and any(e.is_boundary for e in v.link_edges)
                  and 0.04 < (v.co.x * side_sign) < 0.22]
        t_open = [v for v in bm.verts if any(f.material_index == 0 for f in v.link_faces)
                  and any(e.is_boundary for e in v.link_edges)
                  and 0.04 < (v.co.x * side_sign) < 0.12 and 1.0 < v.co.z < 1.185]

        s_sorted = sorted(s_open, key=lambda v: math.atan2(v.co.z - zc_arm, v.co.y - yc_arm))
        t_sorted = sorted(t_open, key=lambda v: math.atan2(v.co.z - zc_arm, v.co.y - yc_arm))
        used_tv = set()
        for sv in s_sorted:
            sa = math.atan2(sv.co.z - zc_arm, sv.co.y - yc_arm)
            avail_tv = [tv for tv in t_sorted if tv not in used_tv]
            if not avail_tv: avail_tv = t_sorted
            best_tv = min(avail_tv, key=lambda tv: abs(math.atan2(tv.co.z - zc_arm, tv.co.y - yc_arm) - sa))
            used_tv.add(best_tv)
            sv.co = best_tv.co

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.006)
    
    # Smooth cylindrical slender bare arms
    arm_verts = []
    for v in bm.verts:
        is_sleeve = any(f.material_index == 6 for f in v.link_faces)
        ax = abs(v.co.x)
        if is_sleeve and ax >= 0.09:
            arm_verts.append(v)
            u = max(0.0, min(1.0, (ax - 0.09) / (0.48 - 0.09)))
            target_r = (1.0 - u) * 0.029 + u * 0.017
            dy = v.co.y - yc_arm
            dz = v.co.z - zc_arm
            curr_r = math.sqrt(dy * dy + dz * dz)
            if curr_r > 1e-5:
                th = math.atan2(dz, dy)
                blend = min(1.0, (ax - 0.09) / 0.04)
                new_y = yc_arm + target_r * 0.92 * math.cos(th)
                new_z = zc_arm + target_r * 1.05 * math.sin(th)
                v.co.y = (1.0 - blend) * v.co.y + blend * new_y
                v.co.z = (1.0 - blend) * v.co.z + blend * new_z
                
    if arm_verts:
        for _ in range(3):
            bmesh.ops.smooth_vert(bm, verts=arm_verts, factor=0.3)
        
    for f in bm.faces: f.smooth = True
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    
    bpy.context.view_layer.objects.active = body
    bpy.ops.mesh.customdata_custom_splitnormals_clear()

    for i in range(len(body.data.materials)):
        if i == 1: body.data.materials[i] = mat_hair
        else: body.data.materials[i] = mat_skin

# 6. Hair Front (Bangs & Sidelocks)
if hair:
    hair.name = "Yu_Nian_An_Beauty_Hair"
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
        bsdf_h.inputs['Roughness'].default_value = 0.32
        if 'Specular IOR Level' in bsdf_h.inputs: bsdf_h.inputs['Specular IOR Level'].default_value = 0.55
        if 'Anisotropic' in bsdf_h.inputs: bsdf_h.inputs['Anisotropic'].default_value = 0.65
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

# 7. Voluminous Long Hair Cascade (Flowing past waist down to hips + Shoulder locks)
casc_m = bpy.data.meshes.new("Yu_Nian_An_Beauty_Hair_Cascade_Mesh")
bm_c = bmesh.new()
bm_c.loops.layers.uv.new("UVMap")

# Multi-segment layered hair locks
def build_strand(pts, w_profile, camber=0.008, n_sub=8):
    rings = []
    for (px, py, pz), hw in zip(pts, w_profile):
        row = []
        for j in range(n_sub):
            u = j / (n_sub - 1)
            lx = -hw + 2.0 * hw * u
            arch = (1.0 - (lx / (hw + 1e-5)) ** 2) * camber
            row.append(bm_c.verts.new((px + lx, py + arch, pz)))
        rings.append(row)
    for r_i in range(len(pts) - 1):
        for j in range(n_sub - 1):
            bm_c.faces.new([rings[r_i][j], rings[r_i][j + 1], rings[r_i + 1][j + 1], rings[r_i + 1][j]])

# Center broad back cascade (flowing down past hips)
pts_back_c = [
    (0.000, 0.082, 1.340),
    (0.000, 0.090, 1.250),
    (0.000, 0.098, 1.130),
    (0.000, 0.094, 1.010),
    (0.000, 0.088, 0.890),
    (0.000, 0.080, 0.770),
    (0.000, 0.068, 0.650),
    (0.000, 0.054, 0.520),
    (0.000, 0.046, 0.440),
]
w_back_c = [0.065, 0.085, 0.110, 0.118, 0.105, 0.085, 0.058, 0.030, 0.005]
build_strand(pts_back_c, w_back_c, camber=0.012)

# Left & right flowing back layers
for sign in [-1.0, 1.0]:
    pts_bl = [
        (sign * 0.045, 0.080, 1.320),
        (sign * 0.065, 0.088, 1.220),
        (sign * 0.085, 0.094, 1.100),
        (sign * 0.088, 0.090, 0.980),
        (sign * 0.075, 0.082, 0.850),
        (sign * 0.055, 0.072, 0.720),
        (sign * 0.035, 0.058, 0.580),
        (sign * 0.015, 0.048, 0.460),
    ]
    w_bl = [0.030, 0.042, 0.052, 0.050, 0.040, 0.028, 0.015, 0.003]
    build_strand(pts_bl, w_bl, camber=0.008)

# Shoulder-draping front locks (visible from front camera, flowing over chest)
for side_sign in [-1.0, 1.0]:
    pts_sh = [
        (side_sign * 0.068, 0.020, 1.350),
        (side_sign * 0.072, -0.015, 1.270),
        (side_sign * 0.075, -0.055, 1.180),
        (side_sign * 0.072, -0.076, 1.090),
        (side_sign * 0.065, -0.086, 1.000),
        (side_sign * 0.055, -0.092, 0.920),
    ]
    w_sh = [0.015, 0.018, 0.020, 0.016, 0.010, 0.003]
    build_strand(pts_sh, w_sh, camber=0.006)

for f in bm_c.faces: f.smooth = True
bm_c.to_mesh(casc_m)
bm_c.free()
casc_obj = bpy.data.objects.new("Yu_Nian_An_Beauty_Hair_Cascade", casc_m)
if arm: casc_obj.parent = arm
casc_obj.data.materials.append(mat_hair)
sol_c = casc_obj.modifiers.new("Solidify", 'SOLIDIFY')
sol_c.thickness = 0.0012
sub_c = casc_obj.modifiers.new("Subsurf", 'SUBSURF')
sub_c.levels = 1
scene.collection.objects.link(casc_obj)

# 8. Fitted Sundress Bodice with Sweetheart Scoop Neckline & Spaghetti Straps
bm_bod = bmesh.new()
bm_bod.loops.layers.uv.new("UVMap")
n_sec = 40

b_slices = [
    (0.910, 0.094, 0.075, 0.070, -0.033), # Empire waistline
    (0.950, 0.089, 0.073, 0.067, -0.037), # Lower ribcage
    (0.995, 0.097, 0.083, 0.073, -0.034), # Underbust
    (1.050, 0.104, 0.099, 0.080, -0.028), # Bust peak
    (1.100, 0.100, 0.095, 0.078, -0.020), # Upper bust
    (1.138, 0.093, 0.085, 0.074, -0.014), # Neckline rim
]

rings = []
for r_i, (bz, rx, ry_f, ry_b, cy) in enumerate(b_slices):
    rv = []
    for s_i in range(n_sec):
        th = 2.0 * math.pi * s_i / n_sec
        st, ct = math.sin(th), math.cos(th)
        ry = ry_f if st < 0 else ry_b

        bust_cup = 0.0
        if r_i in (2, 3, 4) and st < -0.2:
            x_val = ct * rx
            cup_l = math.exp(-((x_val - 0.046) / 0.025) ** 2)
            cup_r = math.exp(-((x_val + 0.046) / 0.025) ** 2)
            bust_cup = -0.016 * (cup_l + cup_r) * (-st)

        z_dip = 0.0
        if r_i == len(b_slices) - 1:
            x_val = ct * rx
            if st < 0:
                if abs(x_val) < 0.038:
                    u_neck = max(0.0, 1.0 - (x_val / 0.038) ** 2)
                    z_dip = -0.026 * u_neck
                elif abs(x_val) > 0.075:
                    u_arm = min(1.0, (abs(x_val) - 0.075) / (rx - 0.075 + 1e-5))
                    z_dip = -0.024 * u_arm
            elif st > 0.25:
                z_dip = -0.014 * ((st - 0.25) / 0.75)

        px = ct * rx
        py = cy + st * ry + bust_cup
        pz = bz + z_dip
        rv.append(bm_bod.verts.new((px, py, pz)))
    rings.append(rv)

for r_i in range(len(b_slices) - 1):
    for s_i in range(n_sec):
        ni = (s_i + 1) % n_sec
        bm_bod.faces.new([rings[r_i][s_i], rings[r_i][ni], rings[r_i + 1][ni], rings[r_i + 1][s_i]])

# Contoured spaghetti straps over shoulders
w_half = 0.0020
strap_arch = [
    (-0.074, 1.126),
    (-0.048, 1.144),
    (-0.020, 1.162),
    ( 0.008, 1.174),
    ( 0.035, 1.166),
    ( 0.055, 1.142),
    ( 0.068, 1.122),
]
for s0, s1 in [(26, 27), (33, 34)]:
    vf0 = rings[-1][s0]; vf1 = rings[-1][s1]
    b0 = (n_sec - s0) % n_sec; b1 = (n_sec - s1) % n_sec
    vb0 = rings[-1][b0]; vb1 = rings[-1][b1]
    mx = (vf0.co.x + vf1.co.x) * 0.5
    strap_rings = []
    for py_arch, pz_arch in strap_arch:
        v_l = bm_bod.verts.new((mx - w_half, py_arch, pz_arch))
        v_r = bm_bod.verts.new((mx + w_half, py_arch, pz_arch))
        strap_rings.append((v_l, v_r))
    bm_bod.faces.new([vf0, vf1, strap_rings[0][1], strap_rings[0][0]])
    for k in range(len(strap_rings) - 1):
        bm_bod.faces.new([strap_rings[k][0], strap_rings[k][1], strap_rings[k + 1][1], strap_rings[k + 1][0]])
    bm_bod.faces.new([strap_rings[-1][0], strap_rings[-1][1], vb1, vb0])

for f in bm_bod.faces: f.smooth = True
bod_m = bpy.data.meshes.new("Yu_Nian_An_Beauty_Dress_Bodice_Mesh")
bm_bod.to_mesh(bod_m)
bm_bod.free()
bodice_obj = bpy.data.objects.new("Yu_Nian_An_Beauty_Dress_Bodice", bod_m)
if arm: bodice_obj.parent = arm
bodice_obj.data.materials.append(mat_dress)
sol_b = bodice_obj.modifiers.new("Solidify", 'SOLIDIFY')
sol_b.thickness = 0.0016
sub_b = bodice_obj.modifiers.new("Subsurf", 'SUBSURF')
sub_b.levels = 1
scene.collection.objects.link(bodice_obj)

# 9. Vibrant Ice-Blue Satin Waist Sash
bm_sa = bmesh.new()
bm_sa.loops.layers.uv.new("UVMap")
sash_slices = [
    (0.898, 0.097, 0.077, 0.073, -0.033),
    (0.918, 0.096, 0.076, 0.072, -0.033),
    (0.938, 0.092, 0.074, 0.070, -0.035),
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

# Front knot & cascading ribbon tails
k_v0 = bm_sa.verts.new((-0.014, -0.118, 0.934))
k_v1 = bm_sa.verts.new(( 0.014, -0.118, 0.934))
k_v2 = bm_sa.verts.new(( 0.014, -0.118, 0.902))
k_v3 = bm_sa.verts.new((-0.014, -0.118, 0.902))
bm_sa.faces.new([k_v0, k_v1, k_v2, k_v3])

w_tail = 0.009
for side_sign in [-1.0, 1.0]:
    st_x = side_sign * 0.008
    tail_profile = [
        (st_x, -0.120, 0.912),
        (st_x + side_sign * 0.012, -0.155, 0.830),
        (st_x + side_sign * 0.024, -0.185, 0.730),
        (st_x + side_sign * 0.034, -0.210, 0.630),
    ]
    t_rings = []
    for px, py, pz in tail_profile:
        vl = bm_sa.verts.new((px - w_tail, py, pz))
        vr = bm_sa.verts.new((px + w_tail, py, pz))
        t_rings.append((vl, vr))
    for k in range(len(t_rings) - 1):
        bm_sa.faces.new([t_rings[k][0], t_rings[k][1], t_rings[k + 1][1], t_rings[k + 1][0]])

for f in bm_sa.faces: f.smooth = True
sash_m = bpy.data.meshes.new("Yu_Nian_An_Beauty_Dress_WaistSash_Mesh")
bm_sa.to_mesh(sash_m)
bm_sa.free()
sash_obj = bpy.data.objects.new("Yu_Nian_An_Beauty_Dress_WaistSash", sash_m)
if arm: sash_obj.parent = arm
sash_obj.data.materials.append(mat_sash)
sol_sa = sash_obj.modifiers.new("Solidify", 'SOLIDIFY')
sol_sa.thickness = 0.0016
sub_sa = sash_obj.modifiers.new("Subsurf", 'SUBSURF')
sub_sa.levels = 1
scene.collection.objects.link(sash_obj)

# 10. Flared Pleated Skirt (PROPER A-LINE SILHOUETTE, NO PROTRUDING WINGS)
bm_sk = bmesh.new()
bm_sk.loops.layers.uv.new("UVMap")
n_pleats = 28
sk_pts = n_pleats * 2
sk_slices = [
    (0.915, 0.096, 0.100, -0.033), # Under sash
    (0.820, 0.122, 0.130, -0.026),
    (0.710, 0.152, 0.164, -0.016),
    (0.605, 0.185, 0.200, -0.006),
    (0.505, 0.218, 0.238,  0.004), # Hem ending gracefully above knees
]
sk_rings = []
for sz, r_in, r_out, yo in sk_slices:
    rv = []
    for i_p in range(sk_pts):
        th = 2.0 * math.pi * i_p / sk_pts
        r = r_out if (i_p % 2 == 1) else r_in
        rx = r * 1.02; ry = r * 0.98
        rv.append(bm_sk.verts.new((math.cos(th) * rx, math.sin(th) * ry + yo, sz)))
    sk_rings.append(rv)

for r_i in range(len(sk_slices) - 1):
    for s_i in range(sk_pts):
        ni = (s_i + 1) % sk_pts
        bm_sk.faces.new([sk_rings[r_i][s_i], sk_rings[r_i][ni], sk_rings[r_i + 1][ni], sk_rings[r_i + 1][s_i]])

for f in bm_sk.faces: f.smooth = True
skirt_m = bpy.data.meshes.new("Yu_Nian_An_Beauty_Dress_PleatedSkirt_Mesh")
bm_sk.to_mesh(skirt_m)
bm_sk.free()
skirt_obj = bpy.data.objects.new("Yu_Nian_An_Beauty_Dress_PleatedSkirt", skirt_m)
if arm: skirt_obj.parent = arm
skirt_obj.data.materials.append(mat_dress)

# PURE CLEAN HIP WEIGHTING (NO ARM / FINGER INFLUENCE!)
vg_hip = skirt_obj.vertex_groups.new(name="J_Bip_C_Hips")
vg_spine = skirt_obj.vertex_groups.new(name="J_Bip_C_Spine")
for v in skirt_obj.data.vertices:
    # Blend between Spine (at top) and Hips (at bottom)
    u_top = max(0.0, min(1.0, (v.co.z - 0.70) / (0.915 - 0.70)))
    vg_spine.add([v.index], u_top * 0.4, 'REPLACE')
    vg_hip.add([v.index], 1.0 - u_top * 0.4, 'REPLACE')

if arm:
    arm_sk = skirt_obj.modifiers.new("Armature", 'ARMATURE')
    arm_sk.object = arm

sol_sk = skirt_obj.modifiers.new("Solidify", 'SOLIDIFY')
sol_sk.thickness = 0.0016
sub_sk = skirt_obj.modifiers.new("Subsurf", 'SUBSURF')
sub_sk.levels = 1
scene.collection.objects.link(skirt_obj)

# 11. 10 Luminous Translucent Butterflies & Marionette Strings
bf_positions = [
    Vector(( 0.38, -0.14, 1.08)), Vector(( 0.45, -0.02, 1.20)), Vector(( 0.32,  0.10, 1.30)),
    Vector(( 0.48,  0.08, 1.02)), Vector(( 0.28, -0.18, 0.86)),
    Vector((-0.38, -0.14, 1.08)), Vector((-0.45, -0.02, 1.20)), Vector((-0.32,  0.10, 1.30)),
    Vector((-0.48,  0.08, 1.02)), Vector((-0.28, -0.18, 0.86)),
]

def make_butterfly(name, loc, rot, fold_deg=30.0):
    m = bpy.data.meshes.new(f"{name}_Mesh")
    bm = bmesh.new()
    ang = math.radians(fold_deg)
    ca, sa = math.cos(ang), math.sin(ang)

    vh = bm.verts.new((0,  0.022, 0.002))
    vm = bm.verts.new((0,  0.000, 0.002))
    vt = bm.verts.new((0, -0.022, 0.001))

    for sign in [1.0, -1.0]:
        f0 = bm.verts.new((sign * 0.006 * ca,  0.008, 0.002 + 0.006 * sa))
        f1 = bm.verts.new((sign * 0.045 * ca,  0.035, 0.003 + 0.045 * sa))
        f2 = bm.verts.new((sign * 0.085 * ca,  0.050, 0.004 + 0.085 * sa))
        f3 = bm.verts.new((sign * 0.090 * ca,  0.020, 0.003 + 0.090 * sa))
        f4 = bm.verts.new((sign * 0.060 * ca, -0.002, 0.002 + 0.060 * sa))

        h0 = bm.verts.new((sign * 0.068 * ca, -0.018, 0.002 + 0.068 * sa))
        h1 = bm.verts.new((sign * 0.062 * ca, -0.055, 0.002 + 0.062 * sa))
        h2 = bm.verts.new((sign * 0.035 * ca, -0.040, 0.002 + 0.035 * sa))

        bm.faces.new([vh, f0, f1])
        bm.faces.new([f0, f4, f3, f1])
        bm.faces.new([f1, f3, f2])
        bm.faces.new([f0, vm, f4])
        bm.faces.new([f4, vm, vt, h2])
        bm.faces.new([f4, h2, h1, h0])

    for f in bm.faces: f.smooth = True
    bm.to_mesh(m)
    bm.free()
    o = bpy.data.objects.new(name, m)
    o.data.materials.append(mat_bf)
    o.location = loc
    o.rotation_euler = rot
    sol = o.modifiers.new("Solidify", 'SOLIDIFY')
    sol.thickness = 0.0006
    sub = o.modifiers.new("Subsurf", 'SUBSURF')
    sub.levels = 1
    scene.collection.objects.link(o)
    return o

for i in range(10):
    rot = (math.radians(10 + (i % 3) * 12), math.radians(((i % 2) * 2 - 1) * 18), math.radians((i * 36) % 360))
    make_butterfly(f"Butterfly_{i:02d}", bf_positions[i], rot, fold_deg=25 + (i % 4) * 8)

# Query actual world positions of fingertips from posed armature
finger_names = [
    'J_Bip_L_Thumb3', 'J_Bip_L_Index3', 'J_Bip_L_Middle3', 'J_Bip_L_Ring3', 'J_Bip_L_Little3',
    'J_Bip_R_Thumb3', 'J_Bip_R_Index3', 'J_Bip_R_Middle3', 'J_Bip_R_Ring3', 'J_Bip_R_Little3',
]

c_data = bpy.data.curves.new("Strings_Curve", type='CURVE')
c_data.dimensions = '3D'
c_data.bevel_depth = 0.00032

for i, fn in enumerate(finger_names):
    p_bone = arm.pose.bones.get(fn)
    if p_bone:
        p_start = arm.matrix_world @ p_bone.tail
    else:
        side_s = 1.0 if i < 5 else -1.0
        p_start = Vector((side_s * 0.25, -0.05, 0.88))
        
    p_end = bf_positions[i]
    spline = c_data.splines.new('BEZIER')
    spline.bezier_points.add(1)
    p0 = spline.bezier_points[0]
    p1 = spline.bezier_points[1]
    p0.co = p_start
    p1.co = p_end

    mid = (p_start + p_end) * 0.5
    sag = Vector((0.0, 0.0, -0.030 * (p_end - p_start).length))
    p0.handle_right = p_start + (mid - p_start) * 0.6 + sag
    p0.handle_left = p_start - (p0.handle_right - p_start)
    p1.handle_left = p_end + (mid - p_end) * 0.6 + sag
    p1.handle_right = p_end - (p1.handle_left - p_end)

str_obj = bpy.data.objects.new("Strings", c_data)
str_obj.data.materials.append(mat_str)
scene.collection.objects.link(str_obj)

# 12. Studio Cyclorama Backdrop & Balanced Lighting
bm_bg = bmesh.new()
bm_bg.loops.layers.uv.new("UVMap")
cyc_pts = [
    (-2.5, 0.0), (-1.5, 0.0), (-0.5, 0.0), (0.5, 0.0),
    (1.2, 0.02), (1.5, 0.12), (1.7, 0.32), (1.85, 0.65),
    (1.95, 1.10), (2.00, 1.70), (2.00, 2.50), (2.00, 3.20)
]
cyc_rings = []
for yc, zc in cyc_pts:
    vl = bm_bg.verts.new((-3.5, yc, zc))
    vr = bm_bg.verts.new(( 3.5, yc, zc))
    cyc_rings.append((vl, vr))
for k in range(len(cyc_rings) - 1):
    bm_bg.faces.new([cyc_rings[k][0], cyc_rings[k][1], cyc_rings[k + 1][1], cyc_rings[k + 1][0]])

for f in bm_bg.faces: f.smooth = True
bg_m = bpy.data.meshes.new("Studio_Backdrop_Mesh")
bm_bg.to_mesh(bg_m)
bm_bg.free()
bg_obj = bpy.data.objects.new("Studio_Backdrop", bg_m)
mat_bg = new_mat("Mat_Studio_Backdrop")
b_bg = next(n for n in mat_bg.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
b_bg.inputs['Base Color'].default_value = (0.16, 0.18, 0.22, 1.0)
b_bg.inputs['Roughness'].default_value = 0.92
bg_obj.data.materials.append(mat_bg)
scene.collection.objects.link(bg_obj)

# Soft Studio 3-Point Lighting
tl = bpy.data.objects.new("Target_L", None)
tl.location = (0.0, 0.0, 1.15)
scene.collection.objects.link(tl)

def make_light(name, loc, col, energy, sz):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.color = col
    ld.energy = energy
    ld.size = sz
    lo = bpy.data.objects.new(name, ld)
    lo.location = loc
    tt = lo.constraints.new('TRACK_TO')
    tt.target = tl
    tt.track_axis = 'TRACK_NEGATIVE_Z'
    tt.up_axis = 'UP_Y'
    scene.collection.objects.link(lo)
    return lo

make_light("Key_Light", (1.4, -1.8, 1.9), (1.0, 0.96, 0.92), 160.0, 1.6)
make_light("Fill_Light", (-1.4, -1.5, 1.3), (0.88, 0.94, 1.0), 55.0, 1.8)
make_light("Rim_Light", (-0.5, 1.6, 2.0), (1.0, 0.96, 0.92), 150.0, 1.4)

# Cameras
cam_bp = bpy.data.cameras.new("Cam_Beauty_Portrait")
cam_bp.lens = 58.0
cam_bp_obj = bpy.data.objects.new("Cam_Beauty_Portrait", cam_bp)
cam_bp_obj.location = (0.0, -2.05, 1.26)
cam_bp_obj.rotation_euler = (math.radians(90), 0, 0)
scene.collection.objects.link(cam_bp_obj)

cam_fb = bpy.data.cameras.new("Cam_FullBody")
cam_fb.lens = 50.0
cam_fb_obj = bpy.data.objects.new("Cam_FullBody", cam_fb)
cam_fb_obj.location = (0.0, -5.5, 0.825)
cam_fb_obj.rotation_euler = (math.radians(90), 0, 0)
scene.collection.objects.link(cam_fb_obj)

# Cycles settings
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.view_settings.view_transform = 'AgX'
scene.cycles.use_denoising = True

# Render Beauty Portrait
scene.camera = cam_bp_obj
scene.render.resolution_x = 1080
scene.render.resolution_y = 1440
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_remediation_preview2.png"
bpy.ops.render.render(write_still=True)
print("Rendered test_remediation_preview2.png successfully")
