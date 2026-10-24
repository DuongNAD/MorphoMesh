import bpy

print("=== SCENE OBJECTS ===")
for obj in bpy.data.objects:
    parent_name = obj.parent.name if obj.parent else None
    print(f"Object: {obj.name}, Type: {obj.type}, Parent: {parent_name}")
    if obj.type == 'MESH':
        print(f"  Mesh: {obj.data.name}, Verts: {len(obj.data.vertices)}, Polys: {len(obj.data.polygons)}")
        mats = [slot.material.name if slot.material else None for slot in obj.material_slots]
        print(f"  Materials: {mats}")
        mods = [f"{m.name} ({m.type})" for m in obj.modifiers]
        print(f"  Modifiers: {mods}")
        # Print bounding box
        coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
        if coords:
            min_x = min(c.x for c in coords)
            max_x = max(c.x for c in coords)
            min_y = min(c.y for c in coords)
            max_y = max(c.y for c in coords)
            min_z = min(c.z for c in coords)
            max_z = max(c.z for c in coords)
            print(f"  Bounds: X=[{min_x:.3f}, {max_x:.3f}], Y=[{min_y:.3f}, {max_y:.3f}], Z=[{min_z:.3f}, {max_z:.3f}]")
    elif obj.type == 'ARMATURE':
        print(f"  Bones count: {len(obj.data.bones)}")
        bone_names = [b.name for b in obj.data.bones]
        print(f"  Bone names: {bone_names[:15]} ... (total {len(bone_names)})")
        print(f"  Actions in bpy.data: {[act.name for act in bpy.data.actions]}")
        if obj.animation_data and obj.animation_data.action:
            print(f"  Active Action on Armature: {obj.animation_data.action.name}")
        # Check specific tracking target bones
        for target in ["Spine2", "Head", "Spine", "Hips"]:
            if target in obj.data.bones:
                b = obj.data.bones[target]
                print(f"  Target bone '{target}' found: head={b.head_local}, tail={b.tail_local}")

print("=== ALL MATERIALS ===")
for mat in bpy.data.materials:
    print(f"Material: {mat.name}, use_nodes={mat.use_nodes}, backface_culling={mat.use_backface_culling}")
    if hasattr(mat, "shadow_method"):
        print(f"  shadow_method: {mat.shadow_method}")
