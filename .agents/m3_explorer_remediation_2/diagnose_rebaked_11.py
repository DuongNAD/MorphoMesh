import bpy
import math
from pathlib import Path
from mathutils import Euler
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
SKIRT_BONE_NAMES = [f"Skirt_{i:02d}" for i in range(1, 13)]
pb = arm_obj.pose.bones

flare_mult = 1.85
w10 = 0.85
w_cross = 0.40
w_flank = 0.85
w_side = 0.45
rear_mult = 0.40
bounce_mult = 2.5

weights_l = {
    "Skirt_01": w_side,  "Skirt_02": 0.00, "Skirt_03": 0.00, "Skirt_04": 0.00,
    "Skirt_05": 0.00,    "Skirt_06": 0.00, "Skirt_07": 0.00, "Skirt_08": 0.00,
    "Skirt_09": w_cross, "Skirt_10": w10,  "Skirt_11": 1.00, "Skirt_12": w_flank,
}
weights_r = {
    "Skirt_01": 0.00,    "Skirt_02": 0.00, "Skirt_03": 0.00, "Skirt_04": 0.00,
    "Skirt_05": 0.00,    "Skirt_06": 0.00, "Skirt_07": w_side, "Skirt_08": w_flank,
    "Skirt_09": 1.00,    "Skirt_10": w10,  "Skirt_11": w_cross, "Skirt_12": 0.00,
}

act = bpy.data.actions['action_anime_jump_cheer']
arm_obj.animation_data.action = act
f_start, f_end = int(act.frame_range[0]), int(act.frame_range[1])
frames = list(range(f_start, f_end + 1))

tl_pitches = []
tr_pitches = []
hb_z = []
tl_bone = pb.get("Thigh.L")
tr_bone = pb.get("Thigh.R")
hips_bone = pb.get("Hips")

for f in frames:
    scene.frame_set(f)
    bpy.context.view_layer.update()
    tl_pitches.append(tl_bone.rotation_euler.x if tl_bone else 0.0)
    tr_pitches.append(tr_bone.rotation_euler.x if tr_bone else 0.0)
    hb_z.append(hips_bone.location.z if hips_bone else 0.0)

for idx, f in enumerate(frames):
    tl_p = tl_pitches[idx]
    tr_p = tr_pitches[idx]
    hz = hb_z[idx]

    tl_fwd = max(0.0, -tl_p)
    tr_fwd = max(0.0, -tr_p)
    tl_back = max(0.0, tl_p)
    tr_back = max(0.0, tr_p)

    bounce = max(0.0, -hz * bounce_mult)

    for bname in SKIRT_BONE_NAMES:
        wl = weights_l.get(bname, 0.0)
        wr = weights_r.get(bname, 0.0)
        flare = (wl * tl_fwd + wr * tr_fwd) * flare_mult
        
        rear_push = 0.0
        if bname in ["Skirt_02", "Skirt_03", "Skirt_04"]:
            rear_push += tl_back * rear_mult
        if bname in ["Skirt_04", "Skirt_05", "Skirt_06"]:
            rear_push += tr_back * rear_mult

        tot = flare + rear_push + bounce
        deg = max(-15.0, min(65.0, math.degrees(tot)))
        rad = math.radians(deg)

        p_b = pb.get(bname)
        p_b.rotation_euler = Euler((rad, 0, 0), "XYZ")
        p_b.keyframe_insert(data_path="rotation_euler", frame=f)

scene.frame_set(11)
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()
print("\n=== RE-BAKED Jump Cheer Frame 11 Skirt Pitches ===")
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
print("\nTop 5 closest pairs at Frame 11 after rebake:")
for d, ti, si, tc, sc in all_c[:5]:
    tv = legs_obj.data.vertices[ti]
    sv = skirt_obj.data.vertices[si]
    t_grp = {legs_obj.vertex_groups[g.group].name: f'{g.weight:.2f}' for g in tv.groups}
    s_grp = {skirt_obj.vertex_groups[g.group].name: f'{g.weight:.2f}' for g in sv.groups}
    print(f"Dist {d:5.2f}mm | Thigh #{ti} {t_grp} at ({tc.x:.3f}, {tc.y:.3f}, {tc.z:.3f}) | Skirt #{si} {s_grp} at ({sc.x:.3f}, {sc.y:.3f}, {sc.z:.3f})")
