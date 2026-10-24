import bpy
import math
from pathlib import Path
from mathutils.kdtree import KDTree

blend_path = Path(r"E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_animated.blend")
bpy.ops.wm.open_mainfile(filepath=str(blend_path))

arm_obj = bpy.data.objects['Anime_Armature']
skirt_obj = bpy.data.objects['Anime_Skirt']
legs_obj = bpy.data.objects['Anime_Legs']
scene = bpy.context.scene

thigh_vgroups = {g.index: g.name for g in legs_obj.vertex_groups if "Thigh" in g.name}
thigh_vert_indices = [
    v.index for v in legs_obj.data.vertices
    for g in v.groups if g.group in thigh_vgroups and g.weight > 0.05
]
skirt_rest_z_min = min(v.co.z for v in skirt_obj.data.vertices)
skirt_rest_z_max = max(v.co.z for v in skirt_obj.data.vertices)

def inspect_point(act_name, f):
    act = bpy.data.actions[act_name]
    arm_obj.animation_data.action = act
    scene.frame_set(f)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()

    pb = arm_obj.pose.bones
    tl = pb['Thigh.L'].rotation_euler.x
    tr = pb['Thigh.R'].rotation_euler.x
    print(f"\n=== INSPECT: {act_name} Frame {f} ===")
    print(f"Thigh.L={math.degrees(tl):.1f}°, Thigh.R={math.degrees(tr):.1f}°")
    print("Skirt pitches:")
    for i in range(1, 13):
        bname = f"Skirt_{i:02d}"
        print(f"  {bname}: {math.degrees(pb[bname].rotation_euler.x):.1f}°", end=" ")
        if i % 4 == 0: print()

    es = skirt_obj.evaluated_get(deps)
    el = legs_obj.evaluated_get(deps)
    scos = [es.matrix_world @ v.co for v in es.to_mesh().vertices]
    tcos = [(i, el.matrix_world @ el.to_mesh().vertices[i].co) for i in thigh_vert_indices]

    kd = KDTree(len(scos))
    for i, co in enumerate(scos): kd.insert(co, i)
    kd.balance()

    all_c = []
    for ti, tc in tcos:
        if (skirt_rest_z_min - 0.05) <= tc.z <= (skirt_rest_z_max + 0.05):
            sco, si, d = kd.find(tc)
            all_c.append((d*1000.0, ti, si, tc, sco))
    all_c.sort(key=lambda x: x[0])
    for d, ti, si, tc, sc in all_c[:5]:
        tv = legs_obj.data.vertices[ti]
        sv = skirt_obj.data.vertices[si]
        t_grp = {legs_obj.vertex_groups[g.group].name: f'{g.weight:.2f}' for g in tv.groups}
        s_grp = {skirt_obj.vertex_groups[g.group].name: f'{g.weight:.2f}' for g in sv.groups}
        print(f"Dist {d:5.2f}mm | Thigh #{ti} {t_grp} at ({tc.x:.3f}, {tc.y:.3f}, {tc.z:.3f}) | Skirt #{si} {s_grp} at ({sc.x:.3f}, {sc.y:.3f}, {sc.z:.3f})")

inspect_point("action_anime_jump_cheer", 11)
inspect_point("action_anime_walk_cycle", 17)
