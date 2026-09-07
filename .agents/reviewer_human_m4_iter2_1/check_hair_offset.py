import bpy

print("=== CHECKING VERTEX OFFSET BY NOISE IN GEOMETRY NODES ===")
depsgraph = bpy.context.evaluated_depsgraph_get()

for h_name in ["Hair_Hime_Bangs", "Hair_Back_Cascade"]:
    obj = bpy.data.objects.get(h_name)
    eval_obj = obj.evaluated_get(depsgraph)
    eval_mesh = eval_obj.to_mesh()
    
    raw_verts = obj.data.vertices
    eval_verts = eval_mesh.vertices
    
    max_diff = 0.0
    for rv, ev in zip(raw_verts, eval_verts):
        diff = (ev.co - rv.co).length
        if diff > max_diff:
            max_diff = diff
            
    print(f"{h_name}: max vertex offset applied by GN = {max_diff*1000:.4f} mm")
    eval_obj.to_mesh_clear()
