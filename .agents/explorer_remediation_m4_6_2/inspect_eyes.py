import bpy

print("=" * 60)
for name in ["Mesh_Eye_Left_IrisPupil", "Mesh_Eye_Left_CorneaSclera", "Mesh_Eyelid_Left", "Yu_Nian_An_Body"]:
    obj = bpy.data.objects.get(name)
    if obj and obj.data:
        uv_count = len(obj.data.uv_layers) if hasattr(obj.data, "uv_layers") else 0
        mat_names = [m.name for m in obj.data.materials if m]
        print(f"Object: {name}")
        print(f"  verts: {len(obj.data.vertices)}, polys: {len(obj.data.polygons)}, uv_layers: {uv_count}")
        print(f"  materials: {mat_names}")
        if name == "Mesh_Eye_Left_IrisPupil":
            # inspect material node tree
            mat = bpy.data.materials.get("Mat_Human_Eye_Inner_Iris")
            if mat and mat.node_tree:
                print("  Mat_Human_Eye_Inner_Iris nodes:")
                for n in mat.node_tree.nodes:
                    print(f"    - {n.name} ({n.type})")
print("=" * 60)
