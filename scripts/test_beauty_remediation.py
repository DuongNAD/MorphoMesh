import bpy
import bmesh
import math
from mathutils import Vector

bpy.ops.wm.read_factory_settings(use_empty=True)
vrm_path = r"C:\Users\Admin\Downloads\_3D_Models_Assets\Liva.vrm"
scale_factor = 1.65 / 1.4649
bpy.ops.import_scene.gltf(filepath=vrm_path)
arm = bpy.data.objects.get("Armature")
body = bpy.data.objects.get("Body")
face = bpy.data.objects.get("Face")
hair = bpy.data.objects.get("Hair")

if arm:
    arm.scale = (scale_factor, scale_factor, scale_factor)

if body:
    bm = bmesh.new()
    bm.from_mesh(body.data)
    
    del_f = [f for f in bm.faces if f.material_index not in {0, 1, 6}]
    
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
            
    for f in bm.faces:
        if f.material_index == 0:
            avg_z = sum(v.co.z for v in f.verts) / len(f.verts)
            max_ax = max(abs(v.co.x) for v in f.verts)
            if 0.60 < avg_z < 0.90 and max_ax < 0.080:
                del_f.append(f)
                
    bmesh.ops.delete(bm, geom=list(set(del_f)), context='FACES_ONLY')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    
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

mat_skin = bpy.data.materials.new("Mat_Human_Skin_SSS")
mat_skin.use_nodes = True
bsdf_s = mat_skin.node_tree.nodes.get("Principled BSDF")
bsdf_s.inputs["Base Color"].default_value = (0.92, 0.77, 0.71, 1.0)
bsdf_s.inputs["Roughness"].default_value = 0.38
if "Subsurface Weight" in bsdf_s.inputs:
    bsdf_s.subsurface_method = 'RANDOM_WALK'
    bsdf_s.inputs["Subsurface Weight"].default_value = 0.35
    bsdf_s.inputs["Subsurface Radius"].default_value = (0.025, 0.012, 0.007)
    bsdf_s.inputs["Subsurface Scale"].default_value = 0.03

for i in range(len(body.data.materials)):
    if i == 1: pass
    else: body.data.materials[i] = mat_skin

if face:
    m_fskin = bpy.data.materials.get("N00_000_00_Face_00_SKIN (Instance)")
    if m_fskin and m_fskin.node_tree:
        tex_f = next((n for n in m_fskin.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None)
        bsdf_f = next((n for n in m_fskin.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf_f:
            bsdf_f.inputs['Roughness'].default_value = 0.36
            if 'Subsurface Method' in bsdf_f.inputs: bsdf_f.subsurface_method = 'RANDOM_WALK'
            if 'Subsurface Weight' in bsdf_f.inputs:
                bsdf_f.inputs['Subsurface Weight'].default_value = 0.30
                bsdf_f.inputs['Subsurface Radius'].default_value = (0.025, 0.012, 0.007)
                bsdf_f.inputs['Subsurface Scale'].default_value = 0.03

# Posing arm
if arm:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    p_up_l = arm.pose.bones.get('J_Bip_L_UpperArm')
    p_up_r = arm.pose.bones.get('J_Bip_R_UpperArm')
    p_low_l = arm.pose.bones.get('J_Bip_L_LowerArm')
    p_low_r = arm.pose.bones.get('J_Bip_R_LowerArm')
    p_hand_l = arm.pose.bones.get('J_Bip_L_Hand')
    p_hand_r = arm.pose.bones.get('J_Bip_R_Hand')
    
    if p_up_l and p_up_r:
        p_up_l.rotation_mode = 'XYZ'
        p_up_l.rotation_euler = (math.radians(12), math.radians(6), math.radians(-55))
        p_up_r.rotation_mode = 'XYZ'
        p_up_r.rotation_euler = (math.radians(12), math.radians(-6), math.radians(55))
    if p_low_l and p_low_r:
        p_low_l.rotation_mode = 'XYZ'
        p_low_l.rotation_euler = (math.radians(18), math.radians(-20), math.radians(-10))
        p_low_r.rotation_mode = 'XYZ'
        p_low_r.rotation_euler = (math.radians(18), math.radians(20), math.radians(10))
    bpy.ops.object.mode_set(mode='OBJECT')

cam = bpy.data.cameras.new("Cam")
cam.lens = 70.0
co = bpy.data.objects.new("Cam", cam)
co.location = (0.0, -1.8, 1.25)
co.rotation_euler = (math.radians(90), 0, 0)
bpy.context.scene.collection.objects.link(co)
bpy.context.scene.camera = co

l1 = bpy.data.lights.new("L1", 'AREA')
l1.energy = 160.0
l1.size = 1.5
l1.color = (1.0, 0.96, 0.92)
lo1 = bpy.data.objects.new("L1", l1)
lo1.location = (1.2, -1.8, 1.8)
bpy.context.scene.collection.objects.link(lo1)

l2 = bpy.data.lights.new("L2", 'AREA')
l2.energy = 60.0
l2.size = 1.8
l2.color = (0.90, 0.94, 1.0)
lo2 = bpy.data.objects.new("L2", l2)
lo2.location = (-1.2, -1.5, 1.4)
bpy.context.scene.collection.objects.link(lo2)

bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 64
bpy.context.scene.render.resolution_x = 720
bpy.context.scene.render.resolution_y = 960
bpy.context.scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_remediation_preview.png"
bpy.ops.render.render(write_still=True)
print("Rendered test_remediation_preview.png successfully")
