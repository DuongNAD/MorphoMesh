import bpy

print("=== CHECKING HAIR MODIFIER STATUS AND DISPLACEMENT ===")
for h_name in ["Hair_Hime_Bangs", "Hair_Back_Cascade"]:
    obj = bpy.data.objects.get(h_name)
    if not obj:
        print(f"Object {h_name} not found!")
        continue
    print(f"\nObject: {obj.name}")
    for mod in obj.modifiers:
        print(f"  Modifier: {mod.name}, type: {mod.type}, show_viewport: {mod.show_viewport}, show_render: {mod.show_render}")
        if mod.type == 'NODES':
            tree = mod.node_group
            print(f"  Node group: {tree.name}")
            print(f"  Nodes count: {len(tree.nodes)}")
            for n in tree.nodes:
                print(f"    Node: {n.name} ({n.type})")
            print(f"  Links count: {len(tree.links)}")
            for l in tree.links:
                print(f"    Link: {l.from_node.name}.{l.from_socket.name} -> {l.to_node.name}.{l.to_socket.name}")
