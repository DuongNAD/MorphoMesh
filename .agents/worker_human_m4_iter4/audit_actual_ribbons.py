import bpy
import bmesh
import mathutils
import sys

# Add src to sys.path
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
from morphomesh.human_grooming import (
    generate_hime_cut_splines,
    convert_curves_to_ribbon_mesh,
)

body = bpy.data.objects.get('Yu_Nian_An_Body')
if not body:
    print("Body not found")
    exit(1)

bm = bmesh.new()
bm.from_mesh(body.data)
bm.transform(body.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm)

splines_by_layer = generate_hime_cut_splines(height=1.65, sample_density_scale=0.05)
for layer_name, splines in splines_by_layer.items():
    ribbon = convert_curves_to_ribbon_mesh(splines, ribbon_width=0.002)
    verts = ribbon.vertices
    inside = 0
    total = len(verts)
    for v in verts:
        vec = mathutils.Vector(v)
        nearest_co, normal, idx, dist = bvh.find_nearest(vec)
        if nearest_co is not None and normal is not None:
            diff = vec - nearest_co
            if diff.dot(normal) < 0:
                inside += 1
    pct_outside = (total - inside) / total * 100.0 if total > 0 else 0.0
    print(f"Ribbon {layer_name}: Total {total} | Inside: {inside} | OUTSIDE: {total - inside} ({pct_outside:.1f}%)")
