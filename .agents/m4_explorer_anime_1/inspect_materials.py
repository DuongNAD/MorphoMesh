import bpy

print("=== MATERIALS IN SCENE ===")
for mat in bpy.data.materials:
    print(f"\nMaterial: {mat.name}, use_nodes={mat.use_nodes}")
    if mat.use_nodes and mat.node_tree:
        print("  Nodes:")
        for node in mat.node_tree.nodes:
            print(f"    - {node.name} (type: {node.type}, bl_idname: {node.bl_idname})")
            if node.type == 'VALTORGB':
                print(f"        ColorRamp interpolation: {node.color_ramp.interpolation}")
                for i, elem in enumerate(node.color_ramp.elements):
                    print(f"          Stop {i}: pos={elem.position:.3f}, color={tuple(round(c, 3) for c in elem.color)}")
            elif node.type == 'BSDF_DIFFUSE':
                col = tuple(round(c, 3) for c in node.inputs['Color'].default_value)
                rough = round(node.inputs['Roughness'].default_value, 3)
                print(f"        Diffuse Color: {col}, Roughness: {rough}")
            elif node.type == 'MATH':
                print(f"        Math operation: {node.operation}")
            elif node.type == 'MAP_RANGE':
                print(f"        MapRange inputs: from_min={node.inputs['From Min'].default_value}, from_max={node.inputs['From Max'].default_value}")
            elif node.type == 'MIX':
                dt = getattr(node, 'data_type', 'N/A')
                bt = getattr(node, 'blend_type', 'N/A')
                print(f"        Mix: data_type={dt}, blend_type={bt}")
        print("  Links:")
        for link in mat.node_tree.links:
            print(f"    - {link.from_node.name}.{link.from_socket.name} -> {link.to_node.name}.{link.to_socket.name}")
