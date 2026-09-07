import bpy
import bmesh
import mathutils
import math
import sys
import json

print("==================== FORENSIC AUDIT START ====================")

results = {}

# ----------------------------------------------------------------------
# 1. BUTTERFLY AUDIT
# ----------------------------------------------------------------------
butterflies = [o for o in bpy.data.objects if o.name.startswith("Prop_Butterfly_")]
results["butterfly_count"] = len(butterflies)
results["butterflies"] = []

zero_loc_butterflies = []
unrigged_butterflies = []

for bf in sorted(butterflies, key=lambda x: x.name):
    loc = [round(v, 4) for v in bf.location]
    is_zero = (abs(loc[0]) < 1e-4 and abs(loc[1]) < 1e-4 and abs(loc[2]) < 1e-4)
    if is_zero:
        zero_loc_butterflies.append(bf.name)
    
    # Modifiers
    arm_mods = [m for m in bf.modifiers if m.type == 'ARMATURE']
    arm_target = arm_mods[0].object.name if (arm_mods and arm_mods[0].object) else None
    
    # Vertex groups
    vgs = {vg.name: vg.index for vg in bf.vertex_groups}
    vg_weights = {}
    for v in bf.data.vertices:
        for g in v.groups:
            vg_name = [name for name, idx in vgs.items() if idx == g.group]
            if vg_name:
                vg_weights[vg_name[0]] = max(vg_weights.get(vg_name[0], 0.0), g.weight)
                
    if not arm_mods or not arm_target or not vg_weights:
        unrigged_butterflies.append(bf.name)
        
    results["butterflies"].append({
        "name": bf.name,
        "location": loc,
        "armature_target": arm_target,
        "vertex_groups": vg_weights,
        "materials": [m.name for m in bf.data.materials if m],
    })

results["butterfly_zero_count"] = len(zero_loc_butterflies)
results["butterfly_unrigged_count"] = len(unrigged_butterflies)

# ----------------------------------------------------------------------
# 2. MARIONETTE CORDS AUDIT
# ----------------------------------------------------------------------
strings_obj = bpy.data.objects.get("Prop_Marionette_Strings")
results["strings_present"] = strings_obj is not None

if strings_obj:
    str_arm_mods = [m for m in strings_obj.modifiers if m.type == 'ARMATURE']
    str_arm_target = str_arm_mods[0].object.name if (str_arm_mods and str_arm_mods[0].object) else None
    str_vgs = {vg.name: vg.index for vg in strings_obj.vertex_groups}
    
    # Check max weight and vertex count per finger DEF bone
    str_weights_summary = {}
    for vg_name, vg_idx in str_vgs.items():
        v_count = 0
        max_w = 0.0
        min_w = 1.0
        for v in strings_obj.data.vertices:
            for g in v.groups:
                if g.group == vg_idx:
                    v_count += 1
                    max_w = max(max_w, g.weight)
                    min_w = min(min_w, g.weight)
        str_weights_summary[vg_name] = {"vert_count": v_count, "max_w": max_w, "min_w": min_w if v_count > 0 else 0.0}
        
    verts_z = [v.co.z for v in strings_obj.data.vertices]
    results["strings_info"] = {
        "name": strings_obj.name,
        "armature_target": str_arm_target,
        "preserve_volume": str_arm_mods[0].use_deform_preserve_volume if str_arm_mods else False,
        "vertex_count": len(strings_obj.data.vertices),
        "z_range": [round(min(verts_z), 4), round(max(verts_z), 4)] if verts_z else [],
        "vertex_groups": str_weights_summary,
        "materials": [m.name for m in strings_obj.data.materials if m],
    }

# ----------------------------------------------------------------------
# 3. HAIR GEOMETRY NODES EVALUATION AUDIT
# ----------------------------------------------------------------------
hair_names = [
    "Hair_Hime_Bangs",
    "Hair_Hime_Sidelocks",
    "Hair_Scalp_Crown",
    "Hair_Back_Cascade",
    "Hair_Eyebrows",
    "Hair_Eyelashes",
]

depsgraph = bpy.context.evaluated_depsgraph_get()
results["hair_layers"] = {}
total_hair_eval_verts = 0

for h_name in hair_names:
    h_obj = bpy.data.objects.get(h_name)
    if not h_obj:
        results["hair_layers"][h_name] = {"present": False}
        continue
    
    eval_obj = h_obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.data
    eval_vert_count = len(eval_mesh.vertices) if eval_mesh else 0
    total_hair_eval_verts += eval_vert_count
    
    # Check GN modifiers
    gn_mods = [m for m in h_obj.modifiers if m.type == 'NODES']
    gn_details = []
    for m in gn_mods:
        tree = getattr(m, "node_group", getattr(m, "node_tree", None))
        if tree:
            has_interface = hasattr(tree, "interface")
            interface_items = len(tree.interface.items_tree) if has_interface and hasattr(tree.interface, "items_tree") else None
            node_types = [n.type for n in tree.nodes]
            gn_details.append({
                "modifier_name": m.name,
                "tree_name": tree.name,
                "has_interface": has_interface,
                "interface_items_count": interface_items,
                "node_types": node_types,
            })
            
    results["hair_layers"][h_name] = {
        "present": True,
        "raw_vertices": len(h_obj.data.vertices) if hasattr(h_obj.data, "vertices") else len(h_obj.data.curves) if hasattr(h_obj.data, "curves") else 0,
        "evaluated_vertices": eval_vert_count,
        "gn_modifiers": gn_details,
        "materials": [m.name for m in h_obj.data.materials if m],
    }

results["total_evaluated_hair_vertices"] = total_hair_eval_verts

# ----------------------------------------------------------------------
# 4. EYE MESH POSITIONING AUDIT
# ----------------------------------------------------------------------
body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
eye_cornea_L = bpy.data.objects.get("Mesh_Eye_Left_CorneaSclera")
eye_cornea_R = bpy.data.objects.get("Mesh_Eye_Right_CorneaSclera")
eye_iris_L = bpy.data.objects.get("Mesh_Eye_Left_IrisPupil")
eye_iris_R = bpy.data.objects.get("Mesh_Eye_Right_IrisPupil")

if body_obj and eye_cornea_L:
    # Find face front Y at eye level (Z in [1.50, 1.58])
    eye_level_verts = [v.co for v in body_obj.data.vertices if 1.50 <= v.co.z <= 1.58]
    face_min_y = min(v.y for v in eye_level_verts) if eye_level_verts else 0.0
    
    cornea_L_verts_y = [v.co.y for v in eye_cornea_L.data.vertices]
    cornea_L_min_y = min(cornea_L_verts_y) if cornea_L_verts_y else 0.0
    cornea_L_center_y = eye_cornea_L.location.y
    
    results["eye_positioning"] = {
        "face_anterior_y_at_eye_level": round(face_min_y, 4),
        "eye_left_cornea_loc": [round(v, 4) for v in eye_cornea_L.location],
        "eye_left_cornea_most_anterior_y": round(cornea_L_min_y, 4),
        "eye_left_iris_loc": [round(v, 4) for v in eye_iris_L.location] if eye_iris_L else None,
        "is_buried": cornea_L_min_y > (face_min_y + 0.01),  # Buried if anterior cornea is behind face surface
    }

# ----------------------------------------------------------------------
# 5. STUDIO LIGHTS & TRACK_TO CONSTRAINTS AUDIT
# ----------------------------------------------------------------------
lights = [o for o in bpy.data.objects if o.type == 'LIGHT']
results["lights"] = []

for lt in lights:
    con_list = []
    has_valid_track_to = False
    track_target_name = None
    track_target_loc = None
    
    for c in lt.constraints:
        con_info = {"type": c.type, "name": c.name}
        if c.type == 'TRACK_TO':
            con_info["target"] = c.target.name if c.target else None
            con_info["track_axis"] = c.track_axis
            con_info["up_axis"] = c.up_axis
            if c.target:
                has_valid_track_to = True
                track_target_name = c.target.name
                track_target_loc = [round(v, 4) for v in c.target.location]
        con_list.append(con_info)
        
    results["lights"].append({
        "name": lt.name,
        "location": [round(v, 4) for v in lt.location],
        "energy": lt.data.energy,
        "constraints": con_list,
        "has_valid_track_to": has_valid_track_to,
        "target_name": track_target_name,
        "target_loc": track_target_loc,
    })

# ----------------------------------------------------------------------
# 6. CAMERA FRAMING AUDIT
# ----------------------------------------------------------------------
cameras = [o for o in bpy.data.objects if o.type == 'CAMERA']
results["cameras"] = []

for cam in cameras:
    cd = cam.data
    loc = [round(v, 4) for v in cam.location]
    
    # Calculate vertical FOV in degrees
    # lens in mm, sensor_height = 24mm
    sensor_h = cd.sensor_height if hasattr(cd, "sensor_height") else 24.0
    fov_v = 2.0 * math.atan(sensor_h / (2.0 * cd.lens))
    fov_v_deg = math.degrees(fov_v)
    
    # At target distance: distance = abs(cam.location.y)
    dist = abs(cam.location.y)
    frame_height = 2.0 * dist * math.tan(fov_v / 2.0)
    top_z = cam.location.z + frame_height / 2.0
    bottom_z = cam.location.z - frame_height / 2.0
    
    results["cameras"].append({
        "name": cam.name,
        "location": loc,
        "lens": cd.lens,
        "sensor_height": sensor_h,
        "distance": round(dist, 3),
        "vertical_fov_deg": round(fov_v_deg, 2),
        "frame_height_at_origin": round(frame_height, 3),
        "vertical_coverage_z": [round(bottom_z, 3), round(top_z, 3)],
        "captures_full_body": (bottom_z <= 0.05 and top_z >= 1.65),
    })

# ----------------------------------------------------------------------
# 7. WARDROBE SHADING & MATERIALS AUDIT
# ----------------------------------------------------------------------
sash_obj = bpy.data.objects.get("Mesh_Dress_WaistSash")
sash_mat = sash_obj.data.materials[0].name if (sash_obj and sash_obj.data.materials) else None

sandal_l = bpy.data.objects.get("Mesh_Sandal_L") or bpy.data.objects.get("Mesh_Sandal_Left")
sandal_mat = sandal_l.data.materials[0].name if (sandal_l and sandal_l.data.materials) else None

results["wardrobe_materials"] = {
    "sash_object": sash_obj.name if sash_obj else None,
    "sash_material": sash_mat,
    "sandal_object": sandal_l.name if sandal_l else None,
    "sandal_material": sandal_mat,
}

# Inspect Principled BSDF base colors of sash and sandal
mat_sash = bpy.data.materials.get(sash_mat) if sash_mat else None
if mat_sash and mat_sash.node_tree:
    bsdf = next((n for n in mat_sash.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf and "Base Color" in bsdf.inputs:
        results["wardrobe_materials"]["sash_base_color"] = [round(v, 3) for v in bsdf.inputs["Base Color"].default_value]

mat_sandal = bpy.data.materials.get(sandal_mat) if sandal_mat else None
if mat_sandal and mat_sandal.node_tree:
    bsdf = next((n for n in mat_sandal.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf and "Base Color" in bsdf.inputs:
        results["wardrobe_materials"]["sandal_base_color"] = [round(v, 3) for v in bsdf.inputs["Base Color"].default_value]

# ----------------------------------------------------------------------
# 8. BONE DEFORMATION EMPIRICAL TEST (TESTING PROPS RIGGING INTEGRITY)
# ----------------------------------------------------------------------
# Pose bone DEF-thumb.03.L by rotating 45 degrees
rig_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
if rig_obj and rig_obj.type == 'ARMATURE' and strings_obj:
    bpy.context.view_layer.objects.active = rig_obj
    bpy.ops.object.mode_set(mode='POSE')
    pbone = rig_obj.pose.bones.get("DEF-thumb.03.L")
    if pbone:
        orig_rot = pbone.rotation_euler.copy() if pbone.rotation_mode == 'XYZ' else (0,0,0)
        pbone.rotation_mode = 'XYZ'
        
        # Get unposed evaluated coords of vertex 0 on strings
        depsgraph = bpy.context.evaluated_depsgraph_get()
        v0_rest = strings_obj.evaluated_get(depsgraph).data.vertices[0].co.copy()
        
        # Rotate bone
        pbone.rotation_euler = (math.radians(45.0), 0.0, 0.0)
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        v0_posed = strings_obj.evaluated_get(depsgraph).data.vertices[0].co.copy()
        
        # Check delta
        delta = (v0_posed - v0_rest).length
        results["bone_deformation_test"] = {
            "tested_bone": "DEF-thumb.03.L",
            "strings_v0_rest": [round(c, 4) for c in v0_rest],
            "strings_v0_posed": [round(c, 4) for c in v0_posed],
            "displacement_delta": round(delta, 5),
            "deforms_properly": delta > 1e-4,
        }
        
        # Reset bone
        pbone.rotation_euler = (0, 0, 0)
        bpy.ops.object.mode_set(mode='OBJECT')

print("=== FORENSIC RESULTS JSON ===")
print(json.dumps(results, indent=2))
print("=== FORENSIC AUDIT END ===")
