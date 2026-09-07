"""
Test 3: Fixed Y-offsets (negative Y is forward) for Mesh_Lips and matte eyeliner.
"""
import bpy
import bmesh
import math

def test_fixed_offsets():
    blend_path = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    
    body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
    arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
    col_body = bpy.data.collections.get("01_Body")
    
    # 1. Reset body polygons to skin
    for poly in body_obj.data.polygons:
        if poly.material_index == 5:
            poly.material_index = 0
            
    # 2. Oral slit material (pure matte dark charcoal-rose slit)
    mat_slit = bpy.data.materials.get("Mat_Human_Oral_Slit")
    if not mat_slit:
        mat_slit = bpy.data.materials.new("Mat_Human_Oral_Slit")
    mat_slit.use_nodes = True
    bsdf_slit = mat_slit.node_tree.nodes.get("Principled BSDF")
    if bsdf_slit:
        bsdf_slit.inputs["Base Color"].default_value = (0.05, 0.015, 0.02, 1.0) # Deep dark line
        bsdf_slit.inputs["Roughness"].default_value = 0.85
        if "Specular IOR Level" in bsdf_slit.inputs:
            bsdf_slit.inputs["Specular IOR Level"].default_value = 0.0
        if "Subsurface Weight" in bsdf_slit.inputs:
            bsdf_slit.inputs["Subsurface Weight"].default_value = 0.0

    mat_lips = bpy.data.materials.get("Mat_Human_Lips")
    if not mat_lips:
        mat_lips = bpy.data.materials.new("Mat_Human_Lips")
    mat_lips.use_nodes = True
    bsdf_lips = mat_lips.node_tree.nodes.get("Principled BSDF")
    if bsdf_lips:
        bsdf_lips.inputs["Base Color"].default_value = (0.84, 0.44, 0.46, 1.0) # Soft rose
        bsdf_lips.inputs["Roughness"].default_value = 0.26
        if "Subsurface Weight" in bsdf_lips.inputs:
            bsdf_lips.inputs["Subsurface Weight"].default_value = 0.25
        if "Subsurface Radius" in bsdf_lips.inputs:
            bsdf_lips.inputs["Subsurface Radius"].default_value = (0.85, 0.25, 0.25)
        if "Subsurface Scale" in bsdf_lips.inputs:
            bsdf_lips.inputs["Subsurface Scale"].default_value = 0.008

    mat_upper = bpy.data.materials.get("Mat_Human_Lip_Upper")
    if not mat_upper:
        mat_upper = bpy.data.materials.new("Mat_Human_Lip_Upper")
    mat_upper.use_nodes = True
    bsdf_u = mat_upper.node_tree.nodes.get("Principled BSDF")
    if bsdf_u:
        bsdf_u.inputs["Base Color"].default_value = (0.88, 0.60, 0.58, 1.0)
        bsdf_u.inputs["Roughness"].default_value = 0.32
        if "Subsurface Weight" in bsdf_u.inputs:
            bsdf_u.inputs["Subsurface Weight"].default_value = 0.22

    # Clean old Mesh_Lips if present
    old_lips = bpy.data.objects.get("Mesh_Lips")
    if old_lips:
        bpy.data.objects.remove(old_lips, do_unlink=True)

    # Rebuild Mesh_Lips with guaranteed exterior placement (-Y is forward!)
    lips_mesh = bpy.data.meshes.new("Mesh_Lips_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    
    n_rows = 6
    n_cols = 11
    w_half = 0.0100 # 20mm width
    z_center = 1.4655
    y_base = -0.1182
    
    grid_verts = []
    for r in range(n_rows):
        row_verts = []
        v_param = r / (n_rows - 1)
        for c in range(n_cols):
            u_param = c / (n_cols - 1)
            x = -w_half + 2.0 * w_half * u_param
            x_norm = x / w_half
            arch = max(0.0, 1.0 - x_norm * x_norm)
            
            if r == 5:
                z = z_center + 0.0080 - 0.0012 * math.sin(math.pi * u_param) ** 2
            elif r == 4:
                z = z_center + 0.0045 + 0.0005 * arch
            elif r == 3:
                z = z_center + 0.0012 - 0.0008 * (1.0 - arch)
            elif r == 2:
                z = z_center + 0.0000 - 0.0008 * (1.0 - arch)
            elif r == 1:
                z = z_center - 0.0040 - 0.0010 * arch
            else:
                z = z_center - 0.0085
                
            y_curve = y_base + (math.sqrt(max(0.0, 0.075**2 - x**2)) - 0.075)
            
            # All dy are NEGATIVE (forward in front of skull surface)
            if r == 5 or r == 0:
                dy = -0.0004 # flush border
            elif r == 4:
                dy = -0.0012 * arch - 0.0005 # upper lip
            elif r == 3:
                dy = -0.0008 * arch - 0.0004 # fissure upper edge
            elif r == 2:
                dy = -0.0006 * arch - 0.0004 # fissure line (recessed relative to vermilion, but in front of skull!)
            elif r == 1:
                dy = -0.0022 * arch - 0.0005 # lower lip vermilion (pillowed forward)
            else:
                dy = -0.0004
                
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
                
            # Row 2 is oral fissure
            if r == 2 and 1 <= c <= n_cols - 2:
                face.material_index = 1 # Oral Slit
            elif r in (0, 1):
                face.material_index = 0 # Lower lip
            else:
                face.material_index = 2 # Upper lip
                
    bm.to_mesh(lips_mesh)
    bm.free()
    
    lips_obj = bpy.data.objects.new("Mesh_Lips", lips_mesh)
    for poly in lips_mesh.polygons:
        poly.use_smooth = True
    col_body.objects.link(lips_obj)
    lips_obj.data.materials.append(mat_lips)
    lips_obj.data.materials.append(mat_slit)
    lips_obj.data.materials.append(mat_upper)
    lips_obj.parent = body_obj
    
    vg_head = lips_obj.vertex_groups.new(name="DEF-head")
    vg_head.add(list(range(len(lips_obj.data.vertices))), 1.0, 'REPLACE')
    arm_mod = lips_obj.modifiers.new("Armature", 'ARMATURE')
    arm_mod.object = arm_obj
    arm_mod.use_deform_preserve_volume = True

    # 3. Eyeliner: Make it velvety matte black (no shiny specular streak)
    mat_eyeliner = bpy.data.materials.get("Mat_Human_Eyeliner")
    if not mat_eyeliner:
        mat_eyeliner = bpy.data.materials.new("Mat_Human_Eyeliner")
    mat_eyeliner.use_nodes = True
    bsdf_el = mat_eyeliner.node_tree.nodes.get("Principled BSDF")
    if bsdf_el:
        bsdf_el.inputs["Base Color"].default_value = (0.010, 0.010, 0.012, 1.0)
        bsdf_el.inputs["Roughness"].default_value = 0.65 # Velvet matte
        if "Specular IOR Level" in bsdf_el.inputs:
            bsdf_el.inputs["Specular IOR Level"].default_value = 0.10

    # Rebuild eyelids
    mat_skin = bpy.data.materials.get("Mat_Human_Skin_SSS")
    for el_name in ["Mesh_Eyelid_Left", "Mesh_Eyelid_Right"]:
        el_obj = bpy.data.objects.get(el_name)
        if el_obj:
            bpy.data.objects.remove(el_obj, do_unlink=True)
            
    ipd = 0.062
    eye_z = 1.520
    eye_y = -0.118
    eye_radius = 0.0125
    
    for is_left, el_name in [(True, "Mesh_Eyelid_Left"), (False, "Mesh_Eyelid_Right")]:
        center = (ipd / 2.0 if is_left else -ipd / 2.0, eye_y, eye_z)
        sign = 1.0 if is_left else -1.0
        cx, cy, cz = center
        mesh = bpy.data.meshes.new(f"{el_name}_Mesh")
        bm = bmesh.new()
        num_pts = 20
        inner_verts = []
        outer_verts = []
        
        for i in range(num_pts):
            t = 2.0 * math.pi * i / num_pts
            cos_t = math.cos(t)
            sin_t = math.sin(t)
            
            dx = sign * cos_t * 0.0138
            dz = (sin_t * 0.0065 if sin_t >= 0 else sin_t * 0.0036)
            dz += (1.0 - cos_t) * 0.0006
            
            r_sph = eye_radius * 1.012
            dist_sq = dx * dx + dz * dz
            dy = -math.sqrt(max(0.0, r_sph * r_sph - dist_sq)) if dist_sq < r_sph * r_sph else 0.0
            
            v_in = bm.verts.new((cx + dx, cy + dy, cz + dz))
            inner_verts.append(v_in)
            
            if sin_t >= -0.10:
                dx_out = dx * 1.28 + (sign * 0.0025 if cos_t > 0.6 else 0.0)
                dz_out = dz + 0.0030
                dy_out = dy - 0.0008 # forward over eye
            else:
                dx_out = dx * 1.06
                dz_out = dz - 0.0010
                dy_out = dy - 0.0002 # flush
                
            v_out = bm.verts.new((cx + dx_out, cy + dy_out, cz + dz_out))
            outer_verts.append(v_out)
            
        for i in range(num_pts):
            ni = (i + 1) % num_pts
            t_mid = 2.0 * math.pi * (i + 0.5) / num_pts
            sin_mid = math.sin(t_mid)
            face = bm.faces.new([inner_verts[i], inner_verts[ni], outer_verts[ni], outer_verts[i]])
            if sin_mid >= -0.15:
                face.material_index = 0
            else:
                face.material_index = 1
                
        bm.to_mesh(mesh)
        bm.free()
        
        el_obj = bpy.data.objects.new(el_name, mesh)
        for poly in mesh.polygons:
            poly.use_smooth = True
        col_body.objects.link(el_obj)
        el_obj.data.materials.append(mat_eyeliner)
        el_obj.data.materials.append(mat_skin)
        el_obj.parent = body_obj
        
        vg_head = el_obj.vertex_groups.new(name="DEF-head")
        vg_head.add(list(range(len(el_obj.data.vertices))), 1.0, 'REPLACE')
        arm_mod = el_obj.modifiers.new("Armature", 'ARMATURE')
        arm_mod.object = arm_obj
        arm_mod.use_deform_preserve_volume = True

    # 4. Eye Optics & UVs
    mat_iris = bpy.data.materials.get("Mat_Human_Eye_Inner_Iris")
    if mat_iris and mat_iris.node_tree:
        nt = mat_iris.node_tree
        nt.nodes.clear()
        out_node = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Roughness"].default_value = 0.12
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.55
            
        tex_coord = nt.nodes.new("ShaderNodeTexCoord")
        uv_sub = nt.nodes.new("ShaderNodeVectorMath")
        uv_sub.operation = 'SUBTRACT'
        uv_sub.inputs[1].default_value = (0.5, 0.5, 0.0)
        nt.links.new(tex_coord.outputs["UV"], uv_sub.inputs[0])
        
        dist_node = nt.nodes.new("ShaderNodeVectorMath")
        dist_node.operation = 'LENGTH'
        nt.links.new(uv_sub.outputs["Vector"], dist_node.inputs[0])
        
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        el = ramp.color_ramp.elements
        el[0].position = 0.0
        el[0].color = (0.008, 0.008, 0.012, 1.0)
        el[1].position = 0.16
        el[1].color = (0.008, 0.008, 0.012, 1.0)
        
        e_iris1 = ramp.color_ramp.elements.new(0.22)
        e_iris1.color = (0.17, 0.22, 0.26, 1.0)
        e_iris2 = ramp.color_ramp.elements.new(0.36)
        e_iris2.color = (0.13, 0.17, 0.20, 1.0)
        e_limbal = ramp.color_ramp.elements.new(0.42)
        e_limbal.color = (0.025, 0.025, 0.035, 1.0)
        e_sclera_edge = ramp.color_ramp.elements.new(0.46)
        e_sclera_edge.color = (0.86, 0.86, 0.89, 1.0)
        e_sclera = ramp.color_ramp.elements.new(0.65)
        e_sclera.color = (0.95, 0.95, 0.97, 1.0)
        
        nt.links.new(dist_node.outputs["Value"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        nt.links.new(bsdf.outputs["BSDF"], out_node.inputs["Surface"])

    for e_name in ["Mesh_Eye_Left_IrisPupil", "Mesh_Eye_Right_IrisPupil"]:
        e_obj = bpy.data.objects.get(e_name)
        if e_obj and e_obj.data:
            bm_e = bmesh.new()
            bm_e.from_mesh(e_obj.data)
            uv_l = bm_e.loops.layers.uv.verify()
            cx = sum(v.co.x for v in bm_e.verts) / len(bm_e.verts)
            cz = sum(v.co.z for v in bm_e.verts) / len(bm_e.verts)
            r_eye = 0.0105
            for face in bm_e.faces:
                for loop in face.loops:
                    v = loop.vert
                    u = 0.5 + 0.5 * ((v.co.x - cx) / r_eye)
                    v_coord = 0.5 + 0.5 * ((v.co.z - cz) / r_eye)
                    loop[uv_l].uv = (u, v_coord)
            bm_e.to_mesh(e_obj.data)
            bm_e.free()

    # 5. Tame hair clearcoat
    mat_hair = bpy.data.materials.get("Mat_Human_Hair")
    if mat_hair and mat_hair.node_tree:
        bsdf_h = mat_hair.node_tree.nodes.get("Principled BSDF")
        if bsdf_h:
            if "Coat Weight" in bsdf_h.inputs: bsdf_h.inputs["Coat Weight"].default_value = 0.10
            if "Coat Roughness" in bsdf_h.inputs: bsdf_h.inputs["Coat Roughness"].default_value = 0.30
            if "Specular IOR Level" in bsdf_h.inputs: bsdf_h.inputs["Specular IOR Level"].default_value = 0.40

    # 6. Render Full Portrait
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.filepath = r"E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_m4_6_2\prototype_portrait_clean.png"
    
    cam = bpy.data.objects.get("Camera_Portrait_85mm")
    if cam:
        cam.location = (0.0, -1.25, 1.51)
        cam.rotation_euler = (math.radians(88.5), 0.0, 0.0)
        cam.data.lens = 85.0
        scene.camera = cam
        
    bpy.ops.render.render(write_still=True)
    print("Successfully rendered prototype_portrait_clean.png")

if __name__ == "__main__":
    test_fixed_offsets()
