import bpy

print("=== M_Anime_Outline DETAILS ===")
mat = bpy.data.materials.get("M_Anime_Outline")
if mat:
    print(f"Material name: {mat.name}")
    print(f"use_nodes: {mat.use_nodes}")
    print(f"use_backface_culling: {mat.use_backface_culling}")
    # Inspect attributes
    for attr in ["blend_method", "shadow_method", "alpha_threshold", "show_transparent_back"]:
        if hasattr(mat, attr):
            print(f"  {attr}: {getattr(mat, attr)}")
    if mat.use_nodes and mat.node_tree:
        print("  Nodes:")
        for node in mat.node_tree.nodes:
            print(f"    - {node.name} ({node.type})")
            for inp in node.inputs:
                if inp.is_linked:
                    links = [f"{l.from_node.name}.{l.from_socket.name}" for l in inp.links]
                    print(f"        Input {inp.name} <- {links}")
                else:
                    if hasattr(inp, 'default_value'):
                        print(f"        Input {inp.name} = {inp.default_value}")
else:
    print("M_Anime_Outline not found!")

print("=== SCENE RENDER ENGINE ===")
scene = bpy.context.scene
print(f"Engine: {scene.render.engine}")
