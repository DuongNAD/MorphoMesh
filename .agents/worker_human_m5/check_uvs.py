import bpy

print("=== CHECKING UV MAPS ===")
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        uv_layers = [uv.name for uv in obj.data.uv_layers]
        print(f"Mesh {obj.name:<30}: UV layers = {uv_layers}")
        if obj.data.uv_layers.active:
            uv_layer = obj.data.uv_layers.active.data
            min_u = min(d.uv.x for d in uv_layer) if len(uv_layer) > 0 else 0
            max_u = max(d.uv.x for d in uv_layer) if len(uv_layer) > 0 else 0
            min_v = min(d.uv.y for d in uv_layer) if len(uv_layer) > 0 else 0
            max_v = max(d.uv.y for d in uv_layer) if len(uv_layer) > 0 else 0
            print(f"   UV bounds: U=[{min_u:.3f}, {max_u:.3f}], V=[{min_v:.3f}, {max_v:.3f}]")
