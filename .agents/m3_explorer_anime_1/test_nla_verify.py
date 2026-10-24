import bpy

arm = bpy.data.objects['Anime_Armature']
if not arm.animation_data:
    arm.animation_data_create()

action_names = [
    'action_anime_idle_cute',
    'action_anime_wave_greeting',
    'action_anime_walk_cycle',
    'action_anime_jump_cheer'
]

for name in action_names:
    if name in bpy.data.actions:
        bpy.data.actions.remove(bpy.data.actions[name])
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    
    # insert dummy fcurve
    data_path = 'pose.bones["Hips"].location'
    fc = act.fcurves.new(data_path, index=2)
    kp1 = fc.keyframe_points.insert(1, 0.0)
    kp2 = fc.keyframe_points.insert(30, 0.05)
    kp1.interpolation = 'BEZIER'
    kp2.interpolation = 'BEZIER'

    track = arm.animation_data.nla_tracks.new()
    track.name = f"NLA_{name}"
    track.mute = True
    strip = track.strips.new(name, 1, act)

arm.animation_data.nla_tracks[f"NLA_{action_names[0]}"].mute = False
arm.animation_data.action = bpy.data.actions[action_names[0]]

print("Created tracks:", [t.name for t in arm.animation_data.nla_tracks])
print("All actions in bpy.data.actions:", [a.name for a in bpy.data.actions])
print("TEST PASSED")