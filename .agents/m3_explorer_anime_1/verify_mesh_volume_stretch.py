"""
verify_mesh_volume_stretch.py
Measures edge length stretch ratio and volume retention across actions.
"""

import sys
sys.path.append(r'E:\tool\mcp\MorphoMesh\.agents\m3_explorer_anime_1')

import math
import numpy as np
import bpy

arm = bpy.data.objects['Anime_Armature']
scene = bpy.context.scene

from test_all_4_actions import build_all_anime_actions
actions = build_all_anime_actions(arm, push_to_nla=False)

def compute_mesh_volume(mesh):
    """Computes signed volume of a triangular/quad surface mesh."""
    vol = 0.0
    for poly in mesh.polygons:
        # Fan triangulation
        v0 = mesh.vertices[poly.vertices[0]].co
        for i in range(1, len(poly.vertices) - 1):
            v1 = mesh.vertices[poly.vertices[i]].co
            v2 = mesh.vertices[poly.vertices[i + 1]].co
            vol += v0.dot(v1.cross(v2)) / 6.0
    return abs(vol)

mesh_objs = [bpy.data.objects[name] for name in ['Anime_Arms', 'Anime_Legs', 'Anime_Skirt'] if name in bpy.data.objects]

# Reset armature to rest pose
arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.location = (0, 0, 0)
    pb.rotation_euler = (0, 0, 0)
bpy.context.view_layer.update()

rest_edge_lengths = {}
rest_volumes = {}

depsgraph = bpy.context.evaluated_depsgraph_get()

for obj in mesh_objs:
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    verts = np.array([v.co for v in mesh.vertices])
    
    # Edges
    edges = np.array([[e.vertices[0], e.vertices[1]] for e in mesh.edges])
    diffs = verts[edges[:, 1]] - verts[edges[:, 0]]
    lens = np.linalg.norm(diffs, axis=1)
    rest_edge_lengths[obj.name] = (edges, lens)
    
    vol = compute_mesh_volume(mesh)
    rest_volumes[obj.name] = max(vol, 1e-6)
    eval_obj.to_mesh_clear()

print("Rest volumes:", {k: f"{v:.6f}" for k, v in rest_volumes.items()})

max_overall_stretch = 0.0
min_overall_retention = 1.0

for act_name, act in actions.items():
    arm.animation_data.action = act
    f_start = int(act.frame_range[0])
    f_end = int(act.frame_range[1])
    sample_frames = list(range(f_start, f_end + 1, max(1, (f_end - f_start) // 10)))
    if f_end not in sample_frames:
        sample_frames.append(f_end)

    act_max_stretch = 0.0
    act_min_volume_ratio = 1.0

    for f in sample_frames:
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for obj in mesh_objs:
            eval_obj = obj.evaluated_get(dg)
            mesh = eval_obj.to_mesh()
            verts = np.array([v.co for v in mesh.vertices])
            
            edges, l0 = rest_edge_lengths[obj.name]
            diffs = verts[edges[:, 1]] - verts[edges[:, 0]]
            cur_lens = np.linalg.norm(diffs, axis=1)
            stretch = cur_lens / np.maximum(l0, 1e-6)
            act_max_stretch = max(act_max_stretch, np.max(stretch))
            
            cur_vol = compute_mesh_volume(mesh)
            vol_ratio = cur_vol / rest_volumes[obj.name]
            act_min_volume_ratio = min(act_min_volume_ratio, vol_ratio)

            eval_obj.to_mesh_clear()

    max_overall_stretch = max(max_overall_stretch, act_max_stretch)
    min_overall_retention = min(min_overall_retention, act_min_volume_ratio)
    print(f"[{act_name}] Max edge stretch: {act_max_stretch:.3f} (Limit <= 1.85) | Min volume retention: {act_min_volume_ratio:.3f} (Limit >= 0.85)")

print("=== DEFORMATION AUDIT RESULT ===")
print(f"Max overall edge stretch: {max_overall_stretch:.3f} (Threshold: 1.85) -> {'PASS' if max_overall_stretch <= 1.85 else 'FAIL'}")
print(f"Min overall volume retention: {min_overall_retention:.3f} (Threshold: 0.85) -> {'PASS' if min_overall_retention >= 0.85 else 'FAIL'}")