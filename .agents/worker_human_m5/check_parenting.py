import bpy

print("=== CHECKING OBJECT PARENTING AND MODIFIERS ===")
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        arm_mod = next((m for m in obj.modifiers if m.type == 'ARMATURE'), None)
        vg_count = len(obj.vertex_groups)
        parent_name = obj.parent.name if obj.parent else None
        print(f"Mesh: {obj.name:<30} | Parent: {str(parent_name):<25} | ArmMod: {str(bool(arm_mod)):<5} | VGroups: {vg_count}")
