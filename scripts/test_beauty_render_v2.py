"""
MorphoMesh: Test Beauty Render V2
- Eliminates collar/vest artifacts on neck/chest
- Natural tapering cascading black hair with shoulder locks
- Exquisite tailored white two-strap sundress with ice-blue satin sash & ribbon tails
- 10 curved 3D swallowtail butterflies and crimson strings anchored to fingers
- Studio lighting with soft cyclorama backdrop
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
    if sss > 0 and "Subsurface Weight" in b.inputs:
        b.subsurface_method = 'RANDOM_WALK'
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (0.008, 0.004, 0.002)
        b.inputs["Subsurface Scale"].default_value = 0.05
    return m

mat_skin = new_mat("Mat_Human_Skin_SSS", (0.965, 0.880, 0.835, 1.0), 0.35, sss=0.28)

mat_hair = new_mat("Mat_Human_Hair", (0.012, 0.011, 0.015, 1.0), 0.28)
b_h = mat_hair.node_tree.nodes.get("Principled BSDF")
if "Anisotropic" in b_h.inputs: b_h.inputs["Anisotropic"].default_value = 0.72
if "Coat Roughness" in b_h.inputs: b_h.inputs["Coat Roughness"].default_value = 0.30
if "Coat Weight" in b_h.inputs: b_h.inputs["Coat Weight"].default_value = 0.05

mat_dress = new_mat("Mat_Dress_WhiteSilk", (0.965, 0.960, 0.950, 1.0), 0.38)
if "Sheen Weight" in mat_dress.node_tree.nodes.get("Principled BSDF").inputs:
    mat_dress.node_tree.nodes.get("Principled BSDF").inputs["Sheen Weight"].default_value = 0.85

# Distinctive ice-blue satin ribbon sash matching media_1788716034772.jpg
mat_sash = new_mat("Mat_Dress_WaistBelt", (0.35, 0.55, 0.80, 1.0), 0.24)
if "Sheen Weight" in mat_sash.node_tree.nodes.get("Principled BSDF").inputs:
    mat_sash.node_tree.nodes.get("Principled BSDF").inputs["Sheen Weight"].default_value = 0.90

mat_sandal = new_mat("Mat_Sandal_Leather", (0.94, 0.94, 0.95, 1.0), 0.40)

mat_string = new_mat("Mat_Marionette_RedString", (0.95, 0.04, 0.08, 1.0), 0.25)
b_str = mat_string.node_tree.nodes.get("Principled BSDF")
if "Emission Color" in b_str.inputs:
    b_str.inputs["Emission Color"].default_value = (0.95, 0.04, 0.08, 1.0)
    b_str.inputs["Emission Strength"].default_value = 5.5

mat_bf = new_mat("Mat_Magic_Butterfly", (0.96, 0.98, 1.0, 1.0), 0.20)
b_bf = mat_bf.node_tree.nodes.get("Principled BSDF")
if "Emission Color" in b_bf.inputs:
    b_bf.inputs["Emission Color"].default_value = (0.88, 0.96, 1.0, 1.0)
    b_bf.inputs["Emission Strength"].default_value = 4.5

# 1. Import VRM
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
        p_low_r.rotation_mode = 'XYZ'
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

# 2. Face
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
        else: bsdf_f.inputs['Base Color'].default_value = (0.965, 0.910, 0.880, 1.0)
        bsdf_f.inputs['Roughness'].default_value = 0.35
        if 'Subsurface Method' in bsdf_f.inputs: bsdf_f.subsurface_method = 'RANDOM_WALK'
        if 'Subsurface Weight' in bsdf_f.inputs:
            bsdf_f.inputs['Subsurface Weight'].default_value = 0.28
            bsdf_f.inputs['Subsurface Radius'].default_value = (0.008, 0.004, 0.002)
        m_fskin.node_tree.links.new(bsdf_f.outputs['BSDF'], out_f.inputs['Surface'])

# 3. Hair (Base: prune fox ears, front braids, and floating tufts)
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
        if max_z > 1.48 and center_y > -0.03: del_h.extend(isl) # fox ears
        elif min_z < 1.15 and min_y < -0.05: del_h.extend(isl)  # braids
        elif min_z < 1.25 and max_y > 0.04: del_h.extend(isl)   # back braid tufts

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
            bsdf_h.inputs['Base Color'].default_value = (0.012, 0.011, 0.015, 1.0)
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

# 4. Body (Prune torso clothing completely, reshape sleeves into slender bare arms)
if body:
    bm_b = bmesh.new()
    bm_b.from_mesh(body.data)
    keep_slots = {0, 1, 3, 6}
    del_faces = [f for f in bm_b.faces if f.material_index not in keep_slots]
    # In slots 3 and 6, delete all torso islands (keep only arm sleeve islands where max(abs(x)) >= 0.20)
    for slot in [3, 6]:
        slot_faces = [f for f in bm_b.faces if f.material_index == slot]
        visited = set()
        for f in slot_faces:
            if f in visited: continue
            isl = [f]
            visited.add(f)
            st = [f]
            while st:
                curr = st.pop()
                for e in curr.edges:
                    for nxt in e.link_faces:
                        if nxt.material_index == slot and nxt not in visited:
                            visited.add(nxt)
                            isl.append(nxt)
                            st.append(nxt)
            max_x = max(abs(v.co.x) for f_isl in isl for v in f_isl.verts)
            if max_x < 0.20:
                del_faces.extend(isl)

    bmesh.ops.delete(bm_b, geom=list(set(del_faces)), context='FACES_ONLY')
    del_v = [v for v in bm_b.verts if len(v.link_faces) == 0]
    bmesh.ops.delete(bm_b, geom=del_v, context='VERTS')

    # Reshape sleeve vertices in slots 3 and 6 into slender bare arms
    y_c, z_c = 0.022, 1.145
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
                bsdf_hb.inputs['Base Color'].default_value = (0.012, 0.011, 0.015, 1.0)
                bsdf_hb.inputs['Roughness'].default_value = 0.28
                m_hb.node_tree.links.new(bsdf_hb.outputs['BSDF'], out_hb.inputs['Surface'])
        else:
            body.data.materials[i] = mat_skin

# 5. Long Cascading Black Hair (Naturally tapered, following back curve down to hips)
casc_m = bpy.data.meshes.new("Beauty_Hair_Cascade_Mesh")
bm_casc = bmesh.new()
# Elegant anatomical slices: crown (Z=1.44) -> nape (Z=1.30) -> back (Z=1.15) -> waist (Z=1.00) -> hips (Z=0.70)
casc_profile = [
    # (z, width, y_pos, arch_depth)
    (1.44, 0.095, 0.065, 0.025), # Scalp crown attachment
    (1.36, 0.090, 0.075, 0.025), # Nape of neck
    (1.26, 0.110, 0.082, 0.028), # Collarbone / shoulder blade top
    (1.15, 0.135, 0.090, 0.030), # Mid shoulder blades
    (1.00, 0.140, 0.092, 0.030), # Small of back / waist
    (0.85, 0.125, 0.088, 0.028), # Upper hips
    (0.72, 0.090, 0.078, 0.022), # Mid hips
    (0.66, 0.040, 0.068, 0.015), # Tapering tips
]
n_pts = 14
c_rings = []
for cz, cw, cy, cd in casc_profile:
    rv = []
    for p_i in range(n_pts):
        u = p_i / (n_pts - 1)
        th = (u - 0.5) * math.pi * 0.85
        x = math.sin(th) * cw
        y = cy + math.cos(th) * cd
        rv.append(bm_casc.verts.new((x, y, cz)))
    c_rings.append(rv)

bm_casc.verts.ensure_lookup_table()
for r_i in range(len(casc_profile) - 1):
    for p_i in range(n_pts - 1):
        # Face normal pointing outward (+Y)
        p0 = c_rings[r_i][p_i]
        p1 = c_rings[r_i + 1][p_i]
        p2 = c_rings[r_i + 1][p_i + 1]
        p3 = c_rings[r_i][p_i + 1]
        bm_casc.faces.new([p0, p1, p2, p3])

# Front shoulder drape locks (falling gracefully over collarbones to chest)
for side_x, sign in [(-0.075, -1.0), (0.075, 1.0)]:
    # Ribbon from temple over shoulder down to upper bust
    strand_slices = [
        (1.42, side_x, 0.020, 0.016),
        (1.32, side_x + sign*0.005, -0.015, 0.018),
        (1.22, side_x + sign*0.008, -0.055, 0.020),
        (1.12, side_x + sign*0.006, -0.078, 0.016),
        (1.02, side_x + sign*0.002, -0.090, 0.010),
        (0.95, side_x, -0.095, 0.004),
    ]
    st_rings = []
    for sz, sx, sy, sw in strand_slices:
        v0 = bm_casc.verts.new((sx - sw*0.5, sy, sz))
        v1 = bm_casc.verts.new((sx + sw*0.5, sy, sz))
        st_rings.append((v0, v1))
    for r_i in range(len(strand_slices) - 1):
        v0, v1 = st_rings[r_i]
        v2, v3 = st_rings[r_i + 1]
        bm_casc.faces.new([v0, v1, v3, v2])

for f in bm_casc.faces: f.smooth = True
bm_casc.to_mesh(casc_m)
bm_casc.free()
casc_obj = bpy.data.objects.new("Beauty_Hair_Cascade", casc_m)
casc_obj.data.materials.append(mat_hair)
sol_c = casc_obj.modifiers.new("Solidify", 'SOLIDIFY')
sol_c.thickness = 0.0018
sub_c = casc_obj.modifiers.new("Subsurf", 'SUBSURF')
sub_c.levels = 1
scene.collection.objects.link(casc_obj)

# 6. Tailored White Silk Two-Strap Sundress
# Bodice (Anatomically hugging torso landmarks)
bod_m = bpy.data.meshes.new("Beauty_Bodice_Mesh")
bm_bod = bmesh.new()
n_sec = 40
bod_slices = [
    # (z, rx, ry, cy)
    (0.96, 0.142, 0.108, -0.011), # Waist seam
    (1.00, 0.126, 0.096, -0.026), # High waist
    (1.05, 0.112, 0.088, -0.038), # Ribcage
    (1.10, 0.114, 0.096, -0.040), # Underbust
    (1.15, 0.122, 0.108, -0.034), # Bust apex
    (1.19, 0.120, 0.104, -0.022), # Sweetheart scoop neckline
]
b_rings = []
for r_i, (bz, rx, ry, yo) in enumerate(bod_slices):
    rv = []
    for s_i in range(n_sec):
        th = 2.0 * math.pi * s_i / n_sec
        st, ct = math.sin(th), math.cos(th)
        z_dip = 0.0
        if r_i == len(bod_slices) - 1:
            # Sweetheart scoop neckline dip at front center
            if st < -0.2:
                z_dip = -0.022 * (-st - 0.2)
            elif abs(ct) > 0.82: # armhole scoop
                z_dip = -0.016 * (abs(ct) - 0.82) / 0.18
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

# Shoulder Straps (width ~ 1.2cm)
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
    # Apex over shoulder
    sm0 = bm_bod.verts.new((mx - 0.006, 0.005, 1.285))
    sm1 = bm_bod.verts.new((mx + 0.006, 0.005, 1.285))
    bm_bod.faces.new([vf0, vf1, sm1, sm0])
    bm_bod.faces.new([sm0, sm1, vb0, vb1])

for f in bm_bod.faces: f.smooth = True
bm_bod.to_mesh(bod_m)
bm_bod.free()
bodice_obj = bpy.data.objects.new("Beauty_Bodice", bod_m)
bodice_obj.data.materials.append(mat_dress)
sol_b = bodice_obj.modifiers.new("Solidify", 'SOLIDIFY')
sol_b.thickness = 0.0018
sub_b = bodice_obj.modifiers.new("Subsurf", 'SUBSURF')
sub_b.levels = 1
scene.collection.objects.link(bodice_obj)

# Waist Ribbon Sash (Ice-blue satin with dangling tails)
sash_m = bpy.data.meshes.new("Beauty_Sash_Mesh")
bm_sash = bmesh.new()
sash_slices = [
    (0.99, 0.118, 0.084, -0.026),
    (1.02, 0.115, 0.082, -0.026),
    (1.05, 0.118, 0.084, -0.026),
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

# Front ribbon tails
for st_x, angle in [(-0.022, 0.08), (0.022, -0.08)]:
    v0 = bm_sash.verts.new((st_x - 0.008, -0.112, 1.01))
    v1 = bm_sash.verts.new((st_x + 0.008, -0.112, 1.01))
    v2 = bm_sash.verts.new((st_x + 0.010 + math.sin(angle)*0.15, -0.128, 0.85))
    v3 = bm_sash.verts.new((st_x - 0.006 + math.sin(angle)*0.15, -0.128, 0.85))
    v4 = bm_sash.verts.new((st_x + 0.012 + math.sin(angle)*0.30, -0.142, 0.70))
    v5 = bm_sash.verts.new((st_x - 0.004 + math.sin(angle)*0.30, -0.142, 0.70))
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

# Flared Pleated Skirt (28 natural soft pleats, A-line silhouette)
skirt_m = bpy.data.meshes.new("Beauty_Skirt_Mesh")
bm_skirt = bmesh.new()
n_pleats = 28
sk_pts = n_pleats * 2
sk_slices = [
    # (z, r_in, r_out, yo)
    (0.99, 0.118, 0.120, -0.018), # Waist attachment
    (0.90, 0.145, 0.155, -0.010), # Hip flare
    (0.78, 0.180, 0.200, -0.002), # Upper thigh
    (0.68, 0.220, 0.245, 0.005),  # Mid thigh
    (0.58, 0.250, 0.285, 0.008),  # Just above knee hemline
]
sk_rings = []
for sz, r_in, r_out, yo in sk_slices:
    rv = []
    for i_p in range(sk_pts):
        th = 2.0 * math.pi * i_p / sk_pts
        r = r_out if (i_p % 2 == 1) else r_in
        rx = r * 1.04
        ry = r * 0.96
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
sol_sk.thickness = 0.0018
sub_sk = skirt_obj.modifiers.new("Subsurf", 'SUBSURF')
sub_sk.levels = 1
scene.collection.objects.link(skirt_obj)

# 7. Flat White Sandals
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

    # Instep Strap
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

# 8. Beautiful 3D Curved Swallowtail Butterflies
bf_positions = [
    Vector((0.46, -0.16, 1.05)),
    Vector((0.54, -0.06, 1.22)),
    Vector((0.40, 0.08, 1.35)),
    Vector((0.56, 0.12, 1.12)),
    Vector((0.36, -0.20, 0.90)),
    Vector((-0.46, -0.16, 1.05)),
    Vector((-0.54, -0.06, 1.22)),
    Vector((-0.40, 0.08, 1.35)),
    Vector((-0.56, 0.12, 1.12)),
    Vector((-0.36, -0.20, 0.90)),
]

def make_curved_swallowtail(name, loc, rot, wing_fold_deg=35.0):
    m = bpy.data.meshes.new(f"{name}_Mesh")
    bm = bmesh.new()
    ang = math.radians(wing_fold_deg)
    ca, sa = math.cos(ang), math.sin(ang)

    # Body
    v_head = bm.verts.new((0, 0.022, 0.002))
    v_mid = bm.verts.new((0, 0, 0.002))
    v_tail = bm.verts.new((0, -0.022, 0.001))

    for sign in [1.0, -1.0]:
        # Forewing (upper)
        w_f_base = bm.verts.new((sign * 0.004 * ca, 0.008, 0.002 + 0.004 * sa))
        w_f_apex = bm.verts.new((sign * 0.088 * ca, 0.045, 0.002 + 0.088 * sa))
        w_f_mid = bm.verts.new((sign * 0.092 * ca, 0.015, 0.002 + 0.092 * sa))
        w_f_inner = bm.verts.new((sign * 0.055 * ca, -0.005, 0.002 + 0.055 * sa))

        # Hindwing (lower with swallowtail point)
        w_h_outer = bm.verts.new((sign * 0.075 * ca, -0.015, 0.002 + 0.075 * sa))
        w_h_swallow = bm.verts.new((sign * 0.068 * ca, -0.058, 0.002 + 0.068 * sa)) # swallowtail spur!
        w_h_tornus = bm.verts.new((sign * 0.035 * ca, -0.042, 0.002 + 0.035 * sa))

        # Faces
        bm.faces.new([v_head, w_f_base, w_f_apex])
        bm.faces.new([w_f_base, w_f_inner, w_f_mid, w_f_apex])
        bm.faces.new([w_f_base, v_mid, w_f_inner])
        bm.faces.new([w_f_inner, v_mid, v_tail, w_h_tornus])
        bm.faces.new([w_f_inner, w_h_tornus, w_h_swallow, w_h_outer])

    for f in bm.faces: f.smooth = True
    bm.to_mesh(m)
    bm.free()
    obj = bpy.data.objects.new(name, m)
    obj.data.materials.append(mat_bf)
    obj.location = loc
    obj.rotation_euler = rot
    sol = obj.modifiers.new("Solidify", 'SOLIDIFY')
    sol.thickness = 0.0006
    scene.collection.objects.link(obj)
    return obj

for i in range(10):
    rot = (
        math.radians(12.0 + (i % 3) * 15.0),
        math.radians(((i % 2) * 2 - 1) * 20.0),
        math.radians((i * 36.0) % 360.0)
    )
    wing_f = 25.0 + (i % 4) * 12.0
    make_curved_swallowtail(f"Beauty_Butterfly_{i:02d}", bf_positions[i], rot, wing_fold_deg=wing_f)

# 9. Marionette Strings (Anchored directly to finger tips)
# Posed hand fingertip coordinates from rig
fingertip_anchors = [
    # Left hand fingers
    Vector((0.365, -0.045, 0.905)),
    Vector((0.375, -0.058, 0.892)),
    Vector((0.385, -0.055, 0.895)),
    Vector((0.378, -0.048, 0.888)),
    Vector((0.368, -0.038, 0.878)),
    # Right hand fingers
    Vector((-0.365, -0.045, 0.905)),
    Vector((-0.375, -0.058, 0.892)),
    Vector((-0.385, -0.055, 0.895)),
    Vector((-0.378, -0.048, 0.888)),
    Vector((-0.368, -0.038, 0.878)),
]

bstr_m = bpy.data.meshes.new("Beauty_Strings_Mesh")
bm_bstr = bmesh.new()
n_sides = 6
tube_r = 0.0014
for i in range(10):
    start_pt = fingertip_anchors[i]
    end_pt = bf_positions[i]
    n_segs = 12
    dir_v = (end_pt - start_pt).normalized()
    # Orthonormal basis
    up = Vector((0, 0, 1)) if abs(dir_v.z) < 0.9 else Vector((0, 1, 0))
    side_v = dir_v.cross(up).normalized()
    norm_v = side_v.cross(dir_v).normalized()

    rings = []
    for s_idx in range(n_segs + 1):
        t = s_idx / n_segs
        pt = start_pt.lerp(end_pt, t)
        droop = math.sin(math.pi * t) * 0.012
        pt.z -= droop
        ring = []
        for side_idx in range(n_sides):
            ang = 2.0 * math.pi * side_idx / n_sides
            offset = (side_v * math.cos(ang) + norm_v * math.sin(ang)) * tube_r
            ring.append(bm_bstr.verts.new(pt + offset))
        rings.append(ring)

    for s_idx in range(n_segs):
        for side_idx in range(n_sides):
            ni = (side_idx + 1) % n_sides
            bm_bstr.faces.new([rings[s_idx][side_idx], rings[s_idx][ni], rings[s_idx + 1][ni], rings[s_idx + 1][side_idx]])

for f in bm_bstr.faces: f.smooth = True
bm_bstr.to_mesh(bstr_m)
bm_bstr.free()
bstrings_obj = bpy.data.objects.new("Beauty_Marionette_Strings", bstr_m)
bstrings_obj.data.materials.append(mat_string)
scene.collection.objects.link(bstrings_obj)

# 10. Studio Backdrop & Lighting
# Soft neutral studio cyclorama curve
bg_mesh = bpy.data.meshes.new("Studio_Backdrop_Mesh")
bm_bg = bmesh.new()
bg_pts = [
    (0.0, 1.80, 0.0),
    (0.0, 1.20, 0.0),
    (0.0, 0.80, 0.0),
    (0.0, -1.20, 0.0),
]
# Create curved sweep behind character
v_b0 = bm_bg.verts.new((-3.0, 1.5, 0.0))
v_b1 = bm_bg.verts.new((3.0, 1.5, 0.0))
v_b2 = bm_bg.verts.new((3.0, 1.8, 0.8))
v_b3 = bm_bg.verts.new((-3.0, 1.8, 0.8))
v_b4 = bm_bg.verts.new((3.0, 2.0, 2.6))
v_b5 = bm_bg.verts.new((-3.0, 2.0, 2.6))
bm_bg.faces.new([v_b0, v_b1, v_b2, v_b3])
bm_bg.faces.new([v_b3, v_b2, v_b4, v_b5])
for f in bm_bg.faces: f.smooth = True
bm_bg.to_mesh(bg_mesh)
bm_bg.free()
bg_obj = bpy.data.objects.new("Studio_Backdrop", bg_mesh)
mat_bg = new_mat("Mat_Studio_Backdrop", (0.12, 0.14, 0.18, 1.0), 0.85)
bg_obj.data.materials.append(mat_bg)
scene.collection.objects.link(bg_obj)

target_l = bpy.data.objects.new("Target_L", None)
target_l.location = (0.0, 0.0, 1.30)
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

# Cinema-grade 3-point lighting
add_l("Key_Softbox", (1.2, -2.4, 1.8), (1.0, 0.97, 0.94), 180.0, 1.6)
add_l("Fill_Softbox", (-1.4, -2.0, 1.5), (0.92, 0.95, 1.0), 80.0, 2.0)
add_l("Rim_HairLight", (0.0, 1.6, 2.2), (1.0, 0.96, 0.90), 140.0, 1.2)

# Cameras
cam_p_d = bpy.data.cameras.new("Cam_Portrait")
cam_p_d.lens = 85.0
cam_p = bpy.data.objects.new("Cam_Portrait", cam_p_d)
cam_p.location = (0.0, -1.65, 1.46)
cam_p.rotation_euler = (math.radians(90.0), 0, 0)
scene.collection.objects.link(cam_p)

cam_fb_d = bpy.data.cameras.new("Cam_FullBody")
cam_fb_d.lens = 50.0
cam_fb = bpy.data.objects.new("Cam_FullBody", cam_fb_d)
cam_fb.location = (0.0, -3.8, 0.88)
cam_fb.rotation_euler = (math.radians(90.0), 0, 0)
scene.collection.objects.link(cam_fb)

# Render Settings
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.view_settings.view_transform = 'AgX'
scene.cycles.use_denoising = False

# Render Portrait
scene.camera = cam_p
scene.render.resolution_x = 1080
scene.render.resolution_y = 1440
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_beauty_v2_portrait.png"
bpy.ops.render.render(write_still=True)
print("Rendered test_beauty_v2_portrait.png")

# Render Full Body
scene.camera = cam_fb
scene.render.resolution_x = 1080
scene.render.resolution_y = 1920
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_beauty_v2_fb.png"
bpy.ops.render.render(write_still=True)
print("Rendered test_beauty_v2_fb.png")
