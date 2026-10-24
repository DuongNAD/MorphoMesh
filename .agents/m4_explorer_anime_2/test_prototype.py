import bpy
import os
import math

print("=== TESTING PROTOTYPE ON ANIME_ANIMATED.BLEND ===")
blend_path = "E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_animated.blend"
bpy.ops.wm.open_mainfile(filepath=blend_path)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'

# 1. SETUP OUTLINE MATERIAL
print("\n--- 1. Testing Outline Material Setup ---")
mat_name = "M_Anime_Outline"
mat = bpy.data.materials.get(mat_name)
if mat is None:
    mat = bpy.data.materials.new(name=mat_name)

mat.use_nodes = True
mat.use_backface_culling = True
if hasattr(mat, "shadow_method"):
    mat.shadow_method = 'NONE'
if hasattr(mat, "use_backface_culling_shadow"):
    mat.use_backface_culling_shadow = True
if hasattr(mat, "use_transparent_shadow"):
    mat.use_transparent_shadow = True
if hasattr(mat, "blend_method"):
    mat.blend_method = 'OPAQUE'

nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

emission = nodes.new("ShaderNodeEmission")
emission.name = "Outline_Emission"
emission.inputs["Color"].default_value = (0.02, 0.02, 0.02, 1.0)
emission.inputs["Strength"].default_value = 1.0

output = nodes.new("ShaderNodeOutputMaterial")
output.name = "Material_Output"
links.new(emission.outputs["Emission"], output.inputs["Surface"])

print(f"Material {mat.name} configured:")
print(f"  use_backface_culling: {mat.use_backface_culling}")
print(f"  nodes: {[n.name for n in nodes]}")

# 2. APPLY SOLIDIFY MODIFIER TO ALL MESHES
print("\n--- 2. Testing Solidify Outline Modifiers ---")
submesh_names = ["Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs", "Anime_Hair", "Anime_Skirt", "Anime_Shoes"]
for name in submesh_names:
    obj = bpy.data.objects.get(name)
    assert obj is not None, f"Mesh {name} not found"
    
    # Check or assign material slot
    if mat.name not in [slot.material.name if slot.material else "" for slot in obj.material_slots]:
        obj.data.materials.append(mat)
    
    outline_slot_idx = [i for i, s in enumerate(obj.material_slots) if s.material and s.material.name == mat.name][0]
    
    mod = obj.modifiers.get("Anime_Outline")
    if mod is None:
        mod = obj.modifiers.new(name="Anime_Outline", type="SOLIDIFY")
    
    mod.thickness = -0.0035
    mod.offset = 1.0
    mod.use_flip_normals = True
    mod.material_offset = outline_slot_idx
    mod.use_rim = False
    
    # Verify modifier position (must be after Armature)
    arm_idx = -1
    out_idx = -1
    for i, m in enumerate(obj.modifiers):
        if m.type == 'ARMATURE':
            arm_idx = i
        elif m.name == 'Anime_Outline':
            out_idx = i
    
    if arm_idx != -1 and out_idx < arm_idx:
        # Move after armature
        while out_idx < arm_idx:
            bpy.ops.object.modifier_move_down({"object": obj}, modifier="Anime_Outline")
            out_idx += 1
            
    print(f"  Obj: {obj.name} -> Modifiers: {[m.name for m in obj.modifiers]}, outline slot: {mod.material_offset}")

# 3. SETUP CAMERA RIG
print("\n--- 3. Testing Camera Rig ---")
cam_name = "Anime_Camera"
cam_data = bpy.data.cameras.get(cam_name)
if cam_data is None:
    cam_data = bpy.data.cameras.new(cam_name)

cam_data.lens = 65.0
cam_data.sensor_width = 36.0
cam_data.sensor_height = 20.25

cam_obj = bpy.data.objects.get(cam_name)
if cam_obj is None:
    cam_obj = bpy.data.objects.new(cam_name, cam_data)
    scene.collection.objects.link(cam_obj)

scene.camera = cam_obj
cam_obj.location = (0.0, -2.6, 1.25)

# Constraint
arm_obj = bpy.data.objects.get("Anime_Armature")
con = cam_obj.constraints.get("Track_Spine2")
if con is None:
    con = cam_obj.constraints.new(type='TRACK_TO')
    con.name = "Track_Spine2"

con.target = arm_obj
con.subtarget = "Spine2" if "Spine2" in arm_obj.pose.bones else "Head"
con.track_axis = 'TRACK_NEGATIVE_Z'
con.up_axis = 'UP_Y'

bpy.context.view_layer.update()
print(f"Camera '{cam_obj.name}': loc={cam_obj.location}, lens={cam_data.lens}mm, target={con.target.name}.{con.subtarget}")

# 4. SETUP 3-POINT LIGHTING RIG
print("\n--- 4. Testing 3-Point Lighting Rig ---")
def hex_to_linear(hex_str):
    hex_str = hex_str.lstrip('#')
    srgb = [int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb)

lights_data = [
    ("Light_Key", "POINT", 650.0, hex_to_linear("FFF5EA"), (1.8, -2.0, 2.5)),
    ("Light_Fill", "POINT", 200.0, hex_to_linear("D6E4FF"), (-1.5, -1.8, 1.8)),
    ("Light_Rim", "POINT", 800.0, hex_to_linear("FFFFFF"), (-0.5, 1.5, 2.2)),
]

created_lights = {}
for lname, ltype, energy, color, loc in lights_data:
    ldata = bpy.data.lights.get(lname)
    if ldata is None:
        ldata = bpy.data.lights.new(lname, ltype)
    ldata.type = ltype
    ldata.energy = energy
    ldata.color = color
    
    lobj = bpy.data.objects.get(lname)
    if lobj is None:
        lobj = bpy.data.objects.new(lname, ldata)
        scene.collection.objects.link(lobj)
    lobj.location = loc
    
    # Aim at character
    lcon = lobj.constraints.get("Track_Character")
    if lcon is None:
        lcon = lobj.constraints.new(type='TRACK_TO')
        lcon.name = "Track_Character"
    lcon.target = arm_obj
    lcon.subtarget = "Spine2"
    lcon.track_axis = 'TRACK_NEGATIVE_Z'
    lcon.up_axis = 'UP_Y'
    created_lights[lname] = lobj
    print(f"  Light '{lname}': type={ltype}, energy={energy}W, loc={loc}, color={color}")

# 5. RENDER TEST FRAME
print("\n--- 5. Rendering Test Frame ---")
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.fps = 30
scene.display_settings.display_device = 'sRGB'
scene.view_settings.view_transform = 'Standard'

out_render = "E:/tool/mcp/MorphoMesh/.agents/m4_explorer_anime_2/test_anime_cinematic_frame.png"
scene.render.filepath = out_render
bpy.context.view_layer.update()
bpy.ops.render.render(write_still=True)
print(f"Successfully rendered frame to {out_render}")
