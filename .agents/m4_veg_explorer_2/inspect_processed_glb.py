import bpy

glb_path = r"E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_2\processed_palm\tropical\veg_tropical_palm_01\veg_tropical_palm_01.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb_path)

print("Objects:", [o.name for o in bpy.data.objects])
print("Materials:", [m.name for m in bpy.data.materials])
print("Images:", [img.name for img in bpy.data.images])

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        print(f"Object {obj.name}:")
        print(f"  matrix_world: {obj.matrix_world}")
        print(f"  rotation_euler: {obj.rotation_euler}")
        print(f"  bounds min/max:")
        import mathutils
        corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        min_c = [min(c[i] for c in corners) for i in range(3)]
        max_c = [max(c[i] for c in corners) for i in range(3)]
        print(f"  min: {min_c}")
        print(f"  max: {max_c}")
        for slot in obj.material_slots:
            if slot.material:
                mat = slot.material
                print(f"  Material {mat.name}:")
                print(f"    blend_method: {getattr(mat, 'blend_method', None)}")
                print(f"    surface_render_method: {getattr(mat, 'surface_render_method', None)}")
                if mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        print(f"      Node: {node.name} ({node.type})")
                        if node.type == 'TEX_IMAGE' and node.image:
                            print(f"        Image: {node.image.name}, size={node.image.size[:]}, colorspace={node.image.colorspace_settings.name}")
                        if node.type == 'BSDF_PRINCIPLED':
                            for inp in node.inputs:
                                if inp.is_linked:
                                    print(f"        BSDF linked input: {inp.name} <- {[l.from_node.name for l in inp.links]}")
