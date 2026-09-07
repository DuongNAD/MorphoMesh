import bpy

print("=== CHECKING RIGGING ON CORDS AND BUTTERFLIES ===")
strings = bpy.data.objects.get("Prop_Marionette_Strings")
if strings:
    print(f"Prop_Marionette_Strings:")
    arm_mod = next((m for m in strings.modifiers if m.type == 'ARMATURE'), None)
    print(f"  Armature modifier: {arm_mod is not None}")
    if arm_mod:
        print(f"  Target: {arm_mod.object.name if arm_mod.object else 'None'}")
    vgroups = [vg.name for vg in strings.vertex_groups]
    print(f"  Vertex groups ({len(vgroups)}): {vgroups}")
    
    # Check if vertices actually have weights assigned
    weighted_verts = 0
    for v in strings.data.vertices:
        if len(v.groups) > 0:
            weighted_verts += 1
    print(f"  Weighted vertices: {weighted_verts} / {len(strings.data.vertices)}")

for i in range(2): # Spot check first 2 butterflies
    bf = bpy.data.objects.get(f"Prop_Butterfly_{i:02d}")
    if bf:
        print(f"\n{bf.name}:")
        arm_mod = next((m for m in bf.modifiers if m.type == 'ARMATURE'), None)
        print(f"  Armature modifier: {arm_mod is not None}")
        if arm_mod:
            print(f"  Target: {arm_mod.object.name if arm_mod.object else 'None'}")
        vgroups = [vg.name for vg in bf.vertex_groups]
        print(f"  Vertex groups: {vgroups}")
        weighted_verts = sum(1 for v in bf.data.vertices if len(v.groups) > 0)
        print(f"  Weighted vertices: {weighted_verts} / {len(bf.data.vertices)}")
