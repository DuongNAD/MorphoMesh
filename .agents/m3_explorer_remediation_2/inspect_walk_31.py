import bpy
import math
from pathlib import Path
from mathutils.kdtree import KDTree

blend_path = Path(r"E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_animated.blend")
bpy.ops.wm.open_mainfile(filepath=str(blend_path))

arm_obj = bpy.data.objects.get("Anime_Armature")
skirt_obj = bpy.data.objects.get("Anime_Skirt")
legs_obj = bpy.data.objects.get("Anime_Legs")
scene = bpy.context.scene

act = bpy.data.actions.get("action_anime_walk_cycle")
arm_obj.animation_data.action = act
scene.frame_set(31)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()

thigh_vgroups = {g.index: g.name for g in legs_obj.vertex_groups if "Thigh" in g.name}
thigh_vert_indices = [
    v.index for v in legs_obj.data.vertices
    for g in v.groups if g.group in thigh_vgroups and g.weight > 0.05
]
skirt_rest_z_min = min(v.co.z for v in skirt_obj.data.vertices)
skirt_rest_z_max = max(v.co.z for v in skirt_obj.data.vertices)

eval_skirt = skirt_obj.evaluated_get(depsgraph)
eval_legs = legs_obj.evaluated_get(depsgraph)
me_skirt = eval_skirt.to_mesh()
me_legs = eval_legs.to_mesh()
mw_skirt = eval_skirt.matrix_world
mw_legs = eval_legs.matrix_world

skirt_cos = [mw_skirt @ v.co for v in me_skirt.vertices]
thigh_cos = [(i, mw_legs @ me_legs.vertices[i].co) for i in thigh_vert_indices]

kd = KDTree(len(skirt_cos))
for i, co in enumerate(skirt_cos): kd.insert(co, i)
kd.balance()

all_close = []
for t_orig_idx, tc in thigh_cos:
    if (skirt_rest_z_min - 0.05) <= tc.z <= (skirt_rest_z_max + 0.05):
        sco, s_idx, dist = kd.find(tc)
        all_close.append((dist * 1000.0, t_orig_idx, s_idx, tc, sco))

all_close.sort(key=lambda x: x[0])
print(f"Top 10 closest pairs at Frame 31 (with unpatched blend):")
for d, ti, si, tc, sc in all_close[:10]:
    tv = legs_obj.data.vertices[ti]
    sv = skirt_obj.data.vertices[si]
    t_groups = {legs_obj.vertex_groups[g.group].name: f"{g.weight:.2f}" for g in tv.groups}
    s_groups = {skirt_obj.vertex_groups[g.group].name: f"{g.weight:.2f}" for g in sv.groups}
    print(f"Dist {d:5.2f}mm | Thigh vert #{ti} {t_groups} at ({tc.x:.3f}, {tc.y:.3f}, {tc.z:.3f}) | Skirt vert #{si} {s_groups} at ({sc.x:.3f}, {sc.y:.3f}, {sc.z:.3f})")
