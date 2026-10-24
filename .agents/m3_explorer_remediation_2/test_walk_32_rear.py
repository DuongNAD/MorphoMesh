import bpy
import math
from pathlib import Path
from mathutils import Euler
from mathutils.kdtree import KDTree

blend_path = Path(r"E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_animated.blend")
bpy.ops.wm.open_mainfile(filepath=str(blend_path))

arm_obj = bpy.data.objects.get("Anime_Armature")
skirt_obj = bpy.data.objects.get("Anime_Skirt")
legs_obj = bpy.data.objects.get("Anime_Legs")
scene = bpy.context.scene

act = bpy.data.actions.get("action_anime_walk_cycle")
arm_obj.animation_data.action = act
scene.frame_set(32)

pb = arm_obj.pose.bones
thigh_vgroups = {g.index: g.name for g in legs_obj.vertex_groups if "Thigh" in g.name}
thigh_vert_indices = [
    v.index for v in legs_obj.data.vertices
    for g in v.groups if g.group in thigh_vgroups and g.weight > 0.05
]
skirt_rest_z_min = min(v.co.z for v in skirt_obj.data.vertices)
skirt_rest_z_max = max(v.co.z for v in skirt_obj.data.vertices)

def eval_frame():
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
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

    min_dist = 999.0
    best_tc = None
    best_ti = -1
    best_si = -1
    for t_orig_idx, tc in thigh_cos:
        if (skirt_rest_z_min - 0.05) <= tc.z <= (skirt_rest_z_max + 0.05):
            sco, s_idx, dist = kd.find(tc)
            if dist < min_dist:
                min_dist = dist
                best_tc = tc
                best_ti = t_orig_idx
                best_si = s_idx
    eval_skirt.to_mesh_clear()
    eval_legs.to_mesh_clear()
    return min_dist * 1000.0, best_ti, best_si, best_tc

print("=== Walk cycle frame 32: testing both front and rear pitch ===")
# Set front flare (Right leg forward)
for b in ["Skirt_08", "Skirt_09", "Skirt_10"]:
    pb.get(b).rotation_euler = Euler((math.radians(35.0), 0, 0), "XYZ")

# Now sweep rear-left pitch (Skirt_02, Skirt_03, Skirt_04)
for p_rear in [0, 5, 10, 15, 20, 25, 30, 35]:
    for b in ["Skirt_02", "Skirt_03", "Skirt_04"]:
        pb.get(b).rotation_euler = Euler((math.radians(p_rear), 0, 0), "XYZ")
    c, ti, si, tc = eval_frame()
    tv = legs_obj.data.vertices[ti]
    sv = skirt_obj.data.vertices[si]
    t_grp = {legs_obj.vertex_groups[g.group].name: f"{g.weight:.2f}" for g in tv.groups}
    s_grp = {skirt_obj.vertex_groups[g.group].name: f"{g.weight:.2f}" for g in sv.groups}
    print(f"rear pitch = {p_rear:2d}° -> clearance = {c:6.2f} mm | Thigh #{ti} {t_grp} (Y={tc.y:+.3f}) | Skirt #{si} {s_grp}")
