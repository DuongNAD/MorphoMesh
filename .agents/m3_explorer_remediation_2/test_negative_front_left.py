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

pb = arm_obj.pose.bones

print("=== JUMP CHEER FRAME 8: TESTING NEGATIVE VS POSITIVE ON SKIRT_11..12 ===")
act = bpy.data.actions.get("action_anime_jump_cheer")
arm_obj.animation_data.action = act
scene.frame_set(8)

for p_right in [15, 25, 35]:
    for p_left in [-15, -10, -5, 0, 5, 15]:
        pb["Skirt_08"].rotation_euler = Euler((math.radians(p_right * 0.8), 0, 0), "XYZ")
        pb["Skirt_09"].rotation_euler = Euler((math.radians(p_right), 0, 0), "XYZ")
        pb["Skirt_10"].rotation_euler = Euler((math.radians(10.0), 0, 0), "XYZ")
        pb["Skirt_11"].rotation_euler = Euler((math.radians(p_left), 0, 0), "XYZ")
        pb["Skirt_12"].rotation_euler = Euler((math.radians(p_left * 0.8), 0, 0), "XYZ")
        c, ti, si, tc = eval_frame()
        print(f"p_right={p_right:2d}°, p_left={p_left:+3d}° -> clearance={c:6.2f}mm (Thigh #{ti} Y={tc.y:+.3f})")
