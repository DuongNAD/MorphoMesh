import bpy

glb_path = r"E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\output\tropical\veg_tropical_palm_01\veg_tropical_palm_01.glb"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb_path)

scene = bpy.context.scene
for obj in scene.objects:
    print(f"Object: {obj.name}, type={obj.type}, loc={obj.location}, rot={obj.rotation_euler}, scale={obj.scale}")
    if obj.type == 'MESH':
        for i, slot in enumerate(obj.material_slots):
            print(f"  Slot {i}: {slot.material.name if slot.material else 'None'}")
            if slot.material and slot.material.use_nodes:
                print("    Nodes in material:")
                for node in slot.material.node_tree.nodes:
                    print(f"      - {node.name} ({node.type})")
                    if node.type == 'TEX_IMAGE':
                        print(f"        Image: {node.image.name if node.image else 'None'}, size={node.image.size if node.image else 'None'}")
                    elif node.type == 'BSDF_PRINCIPLED':
                        for inp in node.inputs:
                            if inp.is_linked:
                                print(f"        Principled input linked: {inp.name} <- {[l.from_node.name for l in inp.links]}")
                            elif inp.name in ("Base Color", "Roughness", "Metallic", "Alpha"):
                                print(f"        Principled input default: {inp.name} = {inp.default_value}")
