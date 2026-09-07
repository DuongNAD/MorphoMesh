"""
Test Beauty Fit: Render portrait and full body with perfectly tailored dress, natural arms, and realistic hair
"""
import bpy
import bmesh
import math
from mathutils import Vector, Matrix, Euler

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# Materials
def new_mat(name, col, rough=0.35, sss=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = col
    b.inputs["Roughness"].default_value = rough
    if sss > 0:
        if "Subsurface Weight" in b.inputs:
            b.subsurface_method = 'RANDOM_WALK'
            b.inputs["Subsurface Weight"].default_value = sss
            b.inputs["Subsurface Radius"].default_value = (0.008, 0.004, 0.002)
            b.inputs["Subsurface Scale"].default_value = 0.05
    return m

mat_skin = new_mat("Mat_Human_Skin_SSS", (0.957, 0.894, 0.863, 1.0), 0.36, sss=0.30)
mat_hair = new_mat("Mat_Human_Hair", (0.015, 0.014, 0.018, 1.0), 0.28)
if "Anisotropic" in mat_hair.node_tree.nodes.get("Principled BSDF").inputs:
    mat_hair.node_tree.nodes.get("Principled BSDF").inputs["Anisotropic"].default_value = 0.70

mat_dress = new_mat("Mat_Dress_WhiteSilk", (0.965, 0.960, 0.950, 1.0), 0.38)
if "Sheen Weight" in mat_dress.node_tree.nodes.get("Principled BSDF").inputs:
    mat_dress.node_tree.nodes.get("Principled BSDF").inputs["Sheen Weight"].default_value = 0.85

mat_sash = new_mat("Mat_Dress_WaistBelt", (0.76, 0.85, 0.92, 1.0), 0.22)
if "Sheen Weight" in mat_sash.node_tree.nodes.get("Principled BSDF").inputs:
    mat_sash.node_tree.nodes.get("Principled BSDF").inputs["Sheen Weight"].default_value = 0.90

mat_sandal = new_mat("Mat_Sandal_Leather", (0.92, 0.92, 0.94, 1.0), 0.45)
mat_string = new_mat("Mat_Marionette_RedString", (0.85, 0.04, 0.08, 1.0), 0.25)
b_str = mat_string.node_tree.nodes.get("Principled BSDF")
if "Emission Color" in b_str.inputs:
    b_str.inputs["Emission Color"].default_value = (0.95, 0.05, 0.10, 1.0)
    b_str.inputs["Emission Strength"].default_value = 4.0

mat_bf = new_mat("Mat_Magic_Butterfly", (0.95, 0.98, 1.0, 1.0), 0.25)
b_bf = mat_bf.node_tree.nodes.get("Principled BSDF")
if "Emission Color" in b_bf.inputs:
    b_bf.inputs["Emission Color"].default_value = (0.88, 0.95, 1.0, 1.0)
    b_bf.inputs["Emission Strength"].default_value = 3.5

# Import VRM
vrm_path = r"C:\Users\Admin\Downloads\_3D_Models_Assets\Liva.vrm"
scale_factor = 1.65 / 1.4649
bpy.ops.import_scene.gltf(filepath=vrm_path)
arm = bpy.data.objects.get("Armature")
body = bpy.data.objects.get("Body")
face = bpy.data.objects.get("Face")
hair = bpy.data.objects.get("Hair")

if arm:
    arm.scale = (scale_factor, scale_factor, scale_factor)
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
        p_up_l.rotation_euler = (math.radians(14), math.radians(6), math.radians(-50))
        p_up_r.rotation_mode = 'XYZ'
        p_up_r.rotation_euler = (math.radians(14), math.radians(-6), math.radians(50))
    if p_low_l and p_low_r:
        p_low_l.rotation_mode = 'XYZ'
        p_low_l.rotation_euler = (math.radians(16), math.radians(-24), math.radians(-10))
        p_low_r.rotation_euler = (math.radians(16), math.radians(24), math.radians(10))
    if p_hand_l and p_hand_r:
        p_hand_l.rotation_mode = 'XYZ'
        p_hand_l.rotation_euler = (0, math.radians(-5), math.radians(8))
        p_hand_r.rotation_mode = 'XYZ'
        p_hand_r.rotation_euler = (0, math.radians(5), math.radians(-8))
    if p_head:
        p_head.rotation_mode = 'XYZ'
        p_head.rotation_euler = (math.radians(2), math.radians(-2), math.radians(-1))
    bpy.ops.object.mode_set(mode='OBJECT')

# Face
if face:
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
        tex_f = next((n for n in m_fskin.node_tree.nodes if n.type == 'TEX_IMAGE'), None)
        out_f = next((n for n in m_fskin.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if not out_f: out_f = m_fskin.node_tree.nodes.new('ShaderNodeOutputMaterial')
        bsdf_f = m_fskin.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        if tex_f: m_fskin.node_tree.links.new(tex_f.outputs['Color'], bsdf_f.inputs['Base Color'])
        else: bsdf_f.inputs['Base Color'].default_value = (0.957, 0.894, 0.863, 1.0)
        bsdf_f.inputs['Roughness'].default_value = 0.36
        if 'Subsurface Method' in bsdf_f.inputs: bsdf_f.subsurface_method = 'RANDOM_WALK'
        if 'Subsurface Weight' in bsdf_f.inputs:
            bsdf_f.inputs['Subsurface Weight'].default_value = 0.30
            bsdf_f.inputs['Subsurface Radius'].default_value = (0.008, 0.004, 0.002)
        m_fskin.node_tree.links.new(bsdf_f.outputs['BSDF'], out_f.inputs['Surface'])

# Hair
if hair:
    bm_h = bmesh.new()
    bm_h.from_mesh(hair.data)
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

    del_h = []
    for isl in islands:
        v_co = [v.co for f in isl for v in f.verts]
        max_z = max(c.z for c in v_co) * scale_factor
        min_z = min(c.z for c in v_co) * scale_factor
        center_y = sum(c.y for c in v_co) / len(v_co) * scale_factor
        min_y = min(c.y for c in v_co) * scale_factor
        max_y = max(c.y for c in v_co) * scale_factor
        if max_z > 1.48 and center_y > -0.03: del_h.extend(isl)
        elif min_z < 1.15 and min_y < -0.05: del_h.extend(isl)
        elif min_z < 1.25 and max_y > 0.04: del_h.extend(isl)

    bmesh.ops.delete(bm_h, geom=list(set(del_h)), context='FACES_ONLY')
    del_v = [v for v in bm_h.verts if len(v.link_faces) == 0]
    bmesh.ops.delete(bm_h, geom=del_v, context='VERTS')
    bm_h.to_mesh(hair.data)
    bm_h.free()
    hair.data.update()

    for m in list(hair.data.materials):
        if m and m.node_tree:
            tex_h = next((n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE'), None)
            out_h = next((n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
            if not out_h: out_h = m.node_tree.nodes.new('ShaderNodeOutputMaterial')
            bsdf_h = m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
            bsdf_h.inputs['Base Color'].default_value = (0.015, 0.014, 0.018, 1.0)
            bsdf_h.inputs['Roughness'].default_value = 0.28
            if 'Anisotropic' in bsdf_h.inputs: bsdf_h.inputs['Anisotropic'].default_value = 0.72
            if tex_h:
                mix_s = m.node_tree.nodes.new('ShaderNodeMixShader')
                trans_h = m.node_tree.nodes.new('ShaderNodeBsdfTransparent')
                m.node_tree.links.new(tex_h.outputs['Alpha'], mix_s.inputs['Fac'])
                m.node_tree.links.new(trans_h.outputs['BSDF'], mix_s.inputs[1])
                m.node_tree.links.new(bsdf_h.outputs['BSDF'], mix_s.inputs[2])
                m.node_tree.links.new(mix_s.outputs['Shader'], out_h.inputs['Surface'])
            else:
                m.node_tree.links.new(bsdf_h.outputs['BSDF'], out_h.inputs['Surface'])

# Body (Slender bare arms, bare legs, skin SSS)
if body:
    bm_b = bmesh.new()
    bm_b.from_mesh(body.data)
    keep_slots = {0, 1, 3, 6}
    del_faces = [f for f in bm_b.faces if f.material_index not in keep_slots]
    bmesh.ops.delete(bm_b, geom=del_faces, context='FACES_ONLY')
    del_v = [v for v in bm_b.verts if len(v.link_faces) == 0]
    bmesh.ops.delete(bm_b, geom=del_v, context='VERTS')

    y_c = 0.022
    z_c = 1.145
    for v in bm_b.verts:
        is_sleeve = any(f.material_index in {3, 6} for f in v.link_faces)
        if is_sleeve and abs(v.co.x) > 0.09:
            ax = abs(v.co.x)
            t = max(0.0, min(1.0, (ax - 0.09) / (0.50 - 0.09)))
            target_r = 0.034 * (1.0 - t) + 0.020 * t
            dy = v.co.y - y_c
            dz = v.co.z - z_c
            curr_r = math.sqrt(dy * dy + dz * dz)
            if curr_r > target_r:
                scale_r = target_r / curr_r
                v.co.y = y_c + dy * scale_r
                v.co.z = z_c + dz * scale_r

    for f in bm_b.faces: f.smooth = True
    bm_b.to_mesh(body.data)
    bm_b.free()
    body.data.update()

    for i in range(len(body.data.materials)):
        if i == 1:
            m_hb = body.data.materials[1]
            if m_hb and m_hb.node_tree:
                m_hb.node_tree.nodes.clear()
                out_hb = m_hb.node_tree.nodes.new('ShaderNodeOutputMaterial')
                bsdf_hb = m_hb.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
                bsdf_hb.inputs['Base Color'].default_value = (0.015, 0.014, 0.018, 1.0)
                bsdf_hb.inputs['Roughness'].default_value = 0.28
                m_hb.node_tree.links.new(bsdf_hb.outputs['BSDF'], out_hb.inputs['Surface'])
        else:
            body.data.materials[i] = mat_skin

# Cascading Hair Back
casc_m = bpy.data.meshes.new("Casc_Hair_Mesh")
bm_casc = bmesh.new()
casc_slices = [
    # (z, cw, cy) in WORLD coordinates (scale 1.0)
    (1.42, 0.12, 0.060),
    (1.30, 0.14, 0.065),
    (1.15, 0.16, 0.070),
    (1.00, 0.17, 0.075),
    (0.85, 0.16, 0.075),
    (0.70, 0.14, 0.070),
]
n_pts = 16
c_rings = []
for cz, cw, cy in casc_slices:
    rv = []
    for p_i in range(n_pts):
        u = p_i / (n_pts - 1)
        th = (u - 0.5) * math.pi * 0.70
        x = math.sin(th) * cw
        y = cy + math.cos(th) * 0.025
        rv.append(bm_casc.verts.new((x, y, cz)))
    c_rings.append(rv)

bm_casc.verts.ensure_lookup_table()
for r_i in range(len(casc_slices) - 1):
    for p_i in range(n_pts - 1):
        bm_casc.faces.new([c_rings[r_i][p_i], c_rings[r_i][p_i + 1], c_rings[r_i + 1][p_i + 1], c_rings[r_i + 1][p_i]])

for f in bm_casc.faces: f.smooth = True
bm_casc.to_mesh(casc_m)
bm_casc.free()
casc_obj = bpy.data.objects.new("Beauty_Hair_Cascade", casc_m)
casc_obj.data.materials.append(mat_hair)
sol_c = casc_obj.modifiers.new("Solidify", 'SOLIDIFY')
sol_c.thickness = 0.002
sub_c = casc_obj.modifiers.new("Subsurf", 'SUBSURF')
sub_c.levels = 1
scene.collection.objects.link(casc_obj)

# Exquisite Tailored Sundress (WORLD coordinates, perfectly hugging anatomy)
# Bodice
bod_m = bpy.data.meshes.new("Beauty_Bodice_Mesh")
bm_bod = bmesh.new()
n_sec = 40
bod_slices = [
    # (z, rx, ry, cy)
    (0.96, 0.134, 0.092, -0.010),  # Waist
    (1.00, 0.118, 0.082, -0.028),  # High waist
    (1.05, 0.102, 0.076, -0.035),  # Ribs
    (1.10, 0.098, 0.078, -0.038),  # Underbust
    (1.15, 0.112, 0.098, -0.036),  # Bust apex
    (1.19, 0.108, 0.094, -0.020),  # Sweetheart scoop neckline
]
b_rings = []
for r_i, (bz, rx, ry, yo) in enumerate(bod_slices):
    rv = []
    for s_i in range(n_sec):
        th = 2.0 * math.pi * s_i / n_sec
        st, ct = math.sin(th), math.cos(th)
        z_dip = 0.0
        if r_i == len(bod_slices) - 1:
            if st < -0.2:
                z_dip = -0.020 * (-st - 0.2)
            elif abs(ct) > 0.82:
                z_dip = -0.015 * (abs(ct) - 0.82) / 0.18
        vx = ct * rx
        vy = st * ry + yo
        vz = bz + z_dip
        rv.append(bm_bod.verts.new((vx, vy, vz)))
    b_rings.append(rv)

bm_bod.verts.ensure_lookup_table()
for r_i in range(len(bod_slices) - 1):
    for s_i in range(n_sec):
        ni = (s_i + 1) % n_sec
        bm_bod.faces.new([b_rings[r_i][s_i], b_rings[r_i][ni], b_rings[r_i + 1][ni], b_rings[r_i + 1][s_i]])

# Shoulder straps
strap_l = [int(n_sec * 0.64), int(n_sec * 0.67)]
strap_r = [int(n_sec * 0.83), int(n_sec * 0.86)]
for s_idx in [strap_l, strap_r]:
    vf0 = b_rings[-1][s_idx[0]]
    vf1 = b_rings[-1][s_idx[1]]
    opp0 = (s_idx[0] + n_sec // 2) % n_sec
    opp1 = (s_idx[1] + n_sec // 2) % n_sec
    vb0 = b_rings[-1][opp0]
    vb1 = b_rings[-1][opp1]
    mx = (vf0.co.x + vf1.co.x) * 0.5
    sm0 = bm_bod.verts.new((mx - 0.006, 0.008, 1.285))
    sm1 = bm_bod.verts.new((mx + 0.006, 0.008, 1.285))
    bm_bod.faces.new([vf0, vf1, sm1, sm0])
    bm_bod.faces.new([sm0, sm1, vb0, vb1])

for f in bm_bod.faces: f.smooth = True
bm_bod.to_mesh(bod_m)
bm_bod.free()
bodice_obj = bpy.data.objects.new("Beauty_Bodice", bod_m)
bodice_obj.data.materials.append(mat_dress)
sol_b = bodice_obj.modifiers.new("Solidify", 'SOLIDIFY')
sol_b.thickness = 0.002
sub_b = bodice_obj.modifiers.new("Subsurf", 'SUBSURF')
sub_b.levels = 1
scene.collection.objects.link(bodice_obj)

# Waist Ribbon Sash
sash_m = bpy.data.meshes.new("Beauty_Sash_Mesh")
bm_sash = bmesh.new()
sash_slices = [
    (0.99, 0.120, 0.084, -0.028),
    (1.02, 0.117, 0.082, -0.028),
    (1.05, 0.120, 0.084, -0.028),
]
s_rings = []
for sz, rx, ry, yo in sash_slices:
    rv = []
    for s_i in range(n_sec):
        th = 2.0 * math.pi * s_i / n_sec
        rv.append(bm_sash.verts.new((math.cos(th) * rx, math.sin(th) * ry + yo, sz)))
    s_rings.append(rv)
bm_sash.verts.ensure_lookup_table()
for r_i in range(len(sash_slices) - 1):
    for s_i in range(n_sec):
        ni = (s_i + 1) % n_sec
        bm_sash.faces.new([s_rings[r_i][s_i], s_rings[r_i][ni], s_rings[r_i + 1][ni], s_rings[r_i + 1][s_i]])

# Ribbon tails
for st_x, angle in [(-0.022, 0.08), (0.022, -0.08)]:
    v0 = bm_sash.verts.new((st_x - 0.008, -0.114, 1.01))
    v1 = bm_sash.verts.new((st_x + 0.008, -0.114, 1.01))
    v2 = bm_sash.verts.new((st_x + 0.010 + math.sin(angle)*0.15, -0.130, 0.85))
    v3 = bm_sash.verts.new((st_x - 0.006 + math.sin(angle)*0.15, -0.130, 0.85))
    v4 = bm_sash.verts.new((st_x + 0.012 + math.sin(angle)*0.30, -0.145, 0.70))
    v5 = bm_sash.verts.new((st_x - 0.004 + math.sin(angle)*0.30, -0.145, 0.70))
    bm_sash.faces.new([v0, v1, v2, v3])
    bm_sash.faces.new([v3, v2, v4, v5])

for f in bm_sash.faces: f.smooth = True
bm_sash.to_mesh(sash_m)
bm_sash.free()
sash_obj = bpy.data.objects.new("Beauty_Sash", sash_m)
sash_obj.data.materials.append(mat_sash)
sol_s = sash_obj.modifiers.new("Solidify", 'SOLIDIFY')
sol_s.thickness = 0.002
sub_s = sash_obj.modifiers.new("Subsurf", 'SUBSURF')
sub_s.levels = 1
scene.collection.objects.link(sash_obj)

# Flared Pleated Skirt
skirt_m = bpy.data.meshes.new("Beauty_Skirt_Mesh")
bm_skirt = bmesh.new()
n_pleats = 28
sk_pts = n_pleats * 2
sk_slices = [
    # (z, r_in, r_out, yo)
    (0.99, 0.120, 0.122, -0.020),
    (0.90, 0.155, 0.168, -0.010),
    (0.78, 0.220, 0.245, 0.000),
    (0.68, 0.295, 0.330, 0.005),
    (0.58, 0.360, 0.405, 0.010),
]
sk_rings = []
for sz, r_in, r_out, yo in sk_slices:
    rv = []
    for i_p in range(sk_pts):
        th = 2.0 * math.pi * i_p / sk_pts
        r = r_out if (i_p % 2 == 1) else r_in
        rx = r * 1.05
        ry = r * 0.95
        rv.append(bm_skirt.verts.new((math.cos(th) * rx, math.sin(th) * ry + yo, sz)))
    sk_rings.append(rv)

bm_skirt.verts.ensure_lookup_table()
for r_i in range(len(sk_slices) - 1):
    for s_i in range(sk_pts):
        ni = (s_i + 1) % sk_pts
        bm_skirt.faces.new([sk_rings[r_i][s_i], sk_rings[r_i][ni], sk_rings[r_i + 1][ni], sk_rings[r_i + 1][s_i]])

for f in bm_skirt.faces: f.smooth = True
bm_skirt.to_mesh(skirt_m)
bm_skirt.free()
skirt_obj = bpy.data.objects.new("Beauty_Skirt", skirt_m)
skirt_obj.data.materials.append(mat_dress)
sol_sk = skirt_obj.modifiers.new("Solidify", 'SOLIDIFY')
sol_sk.thickness = 0.002
sub_sk = skirt_obj.modifiers.new("Subsurf", 'SUBSURF')
sub_sk.levels = 1
scene.collection.objects.link(skirt_obj)

# Flat White Sandals
for side, sign in [("L", 1.0), ("R", -1.0)]:
    sand_m = bpy.data.meshes.new(f"Beauty_Sandal_{side}_Mesh")
    bm_sand = bmesh.new()
    cx = sign * 0.080
    cy_sole = -0.020
    n_sole = 24
    sole_bot = []
    sole_top = []
    for i_s in range(n_sole):
        th = 2.0 * math.pi * i_s / n_sole
        sx = cx + math.cos(th) * 0.040
        sy = cy_sole + math.sin(th) * 0.110
        sole_bot.append(bm_sand.verts.new((sx, sy, 0.008)))
        sole_top.append(bm_sand.verts.new((sx, sy, 0.020)))
    bm_sand.verts.ensure_lookup_table()
    for i_s in range(n_sole):
        ni = (i_s + 1) % n_sole
        bm_sand.faces.new([sole_bot[i_s], sole_bot[ni], sole_top[ni], sole_top[i_s]])
    bm_sand.faces.new(sole_top)
    bm_sand.faces.new(list(reversed(sole_bot)))

    strap_v = []
    for t_p in [0.0, 0.25, 0.5, 0.75, 1.0]:
        st_x = cx + (-0.038 + 0.076 * t_p)
        arch = math.sin(math.pi * t_p) * 0.026
        strap_v.append(bm_sand.verts.new((st_x, cy_sole + 0.020, 0.020 + arch)))
        strap_v.append(bm_sand.verts.new((st_x, cy_sole + 0.038, 0.020 + arch)))
    for i_st in range(4):
        i0 = 2 * i_st
        bm_sand.faces.new([strap_v[i0], strap_v[i0 + 2], strap_v[i0 + 3], strap_v[i0 + 1]])

    for f in bm_sand.faces: f.smooth = True
    bm_sand.to_mesh(sand_m)
    bm_sand.free()
    sand_obj = bpy.data.objects.new(f"Beauty_Sandal_{side}", sand_m)
    sand_obj.data.materials.append(mat_sandal)
    scene.collection.objects.link(sand_obj)

# 10 Glowing White Swallowtail Butterflies & Red Strings
hand_l_pos = Vector((0.36, -0.06, 0.95))
hand_r_pos = Vector((-0.36, -0.06, 0.95))
bf_positions = [
    Vector((0.48, -0.18, 1.08)),
    Vector((0.56, -0.08, 1.25)),
    Vector((0.42, 0.08, 1.38)),
    Vector((0.58, 0.12, 1.15)),
    Vector((0.38, -0.22, 0.92)),
    Vector((-0.48, -0.18, 1.08)),
    Vector((-0.56, -0.08, 1.25)),
    Vector((-0.42, 0.08, 1.38)),
    Vector((-0.58, 0.12, 1.15)),
    Vector((-0.38, -0.22, 0.92)),
]

def make_swallowtail(name, loc, rot):
    m = bpy.data.meshes.new(f"{name}_Mesh")
    bm = bmesh.new()
    vh = bm.verts.new((0, 0.025, 0))
    vt = bm.verts.new((0, -0.025, 0))
    vm = bm.verts.new((0, 0, 0.005))
    wl_tip = bm.verts.new((0.085, 0.035, 0.015))
    wl_mid = bm.verts.new((0.075, -0.010, 0.010))
    wl_tail = bm.verts.new((0.055, -0.055, 0.005))
    wr_tip = bm.verts.new((-0.085, 0.035, 0.015))
    wr_mid = bm.verts.new((-0.075, -0.010, 0.010))
    wr_tail = bm.verts.new((-0.055, -0.055, 0.005))

    bm.faces.new([vh, wl_tip, wl_mid, vm])
    bm.faces.new([vm, wl_mid, wl_tail, vt])
    bm.faces.new([vh, vm, wr_mid, wr_tip])
    bm.faces.new([vm, vt, wr_tail, wr_mid])

    for f in bm.faces: f.smooth = True
    bm.to_mesh(m)
    bm.free()
    obj = bpy.data.objects.new(name, m)
    obj.data.materials.append(mat_bf)
    obj.location = loc
    obj.rotation_euler = rot
    sol = obj.modifiers.new("Solidify", 'SOLIDIFY')
    sol.thickness = 0.0005
    scene.collection.objects.link(obj)
    return obj

for i in range(10):
    rot = (
        math.radians(15.0 + (i % 3) * 15.0),
        math.radians(((i % 2) * 2 - 1) * 25.0),
        math.radians((i * 36.0) % 360.0)
    )
    make_swallowtail(f"Beauty_Butterfly_{i:02d}", bf_positions[i], rot)

# Marionette Strings
bstr_m = bpy.data.meshes.new("Beauty_Strings_Mesh")
bm_bstr = bmesh.new()
for i in range(10):
    h_anchor = hand_l_pos if i < 5 else hand_r_pos
    bf_target = bf_positions[i]
    f_offset = Vector(((i % 5 - 2) * 0.015, (i % 5) * 0.005, -(i % 5) * 0.008))
    start_pt = h_anchor + f_offset
    end_pt = bf_target
    n_segs = 8
    prev_v = None
    for s_idx in range(n_segs + 1):
        t = s_idx / n_segs
        pt = start_pt.lerp(end_pt, t)
        droop = math.sin(math.pi * t) * 0.015
        pt.z -= droop
        v = bm_bstr.verts.new(pt)
        if prev_v: bm_bstr.edges.new([prev_v, v])
        prev_v = v

bm_bstr.to_mesh(bstr_m)
bm_bstr.free()
bstrings_obj = bpy.data.objects.new("Beauty_Marionette_Strings", bstr_m)
bstrings_obj.data.materials.append(mat_string)
skin_mod = bstrings_obj.modifiers.new("Skin", 'SKIN')
for v in bstrings_obj.data.skin_vertices[0].data:
    v.radius = (0.0007, 0.0007)
scene.collection.objects.link(bstrings_obj)

# Lighting & Camera
target_l = bpy.data.objects.new("Target_L", None)
target_l.location = (0.0, 0.0, 1.35)
scene.collection.objects.link(target_l)

def add_l(name, loc, col, energy, sz):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.color = col
    ld.energy = energy
    ld.size = sz
    lo = bpy.data.objects.new(name, ld)
    lo.location = loc
    scene.collection.objects.link(lo)
    tt = lo.constraints.new('TRACK_TO')
    tt.target = target_l
    tt.track_axis = 'TRACK_NEGATIVE_Z'
    tt.up_axis = 'UP_Y'

add_l("Key", (1.4, -2.2, 1.9), (1.0, 0.96, 0.92), 480.0, 1.5)
add_l("Fill", (-1.4, -2.0, 1.6), (0.90, 0.95, 1.0), 220.0, 1.8)
add_l("Rim", (0.0, 1.8, 2.3), (1.0, 0.95, 0.88), 400.0, 1.2)

# Portrait Camera 85mm
cam_p_d = bpy.data.cameras.new("CamP")
cam_p_d.lens = 85.0
cam_p = bpy.data.objects.new("CamP", cam_p_d)
cam_p.location = (0.0, -1.55, 1.48)
cam_p.rotation_euler = (math.radians(90.0), 0, 0)
scene.collection.objects.link(cam_p)

# FullBody Camera 50mm
cam_fb_d = bpy.data.cameras.new("CamFB")
cam_fb_d.lens = 50.0
cam_fb = bpy.data.objects.new("CamFB", cam_fb_d)
cam_fb.location = (0.0, -3.8, 0.88)
cam_fb.rotation_euler = (math.radians(90.0), 0, 0)
scene.collection.objects.link(cam_fb)

# Render Settings
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.view_settings.view_transform = 'AgX'
scene.cycles.use_denoising = True

# 1. Render Portrait
scene.camera = cam_p
scene.render.resolution_x = 1080
scene.render.resolution_y = 1440
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_beauty_fit_portrait.png"
bpy.ops.render.render(write_still=True)
print("Rendered test_beauty_fit_portrait.png")

# 2. Render Full Body
scene.camera = cam_fb
scene.render.resolution_x = 1080
scene.render.resolution_y = 1920
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_beauty_fit_fb.png"
bpy.ops.render.render(write_still=True)
print("Rendered test_beauty_fit_fb.png")
