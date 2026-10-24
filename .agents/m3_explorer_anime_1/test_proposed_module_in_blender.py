"""
test_proposed_module_in_blender.py
Full unit test suite for proposed_action_library.py.
"""

import sys
sys.path.append(r'E:\tool\mcp\MorphoMesh\.agents\m3_explorer_anime_1')

import bpy
import proposed_action_library as lib

def test_pure_python_fixtures():
    defs = lib.get_canonical_action_definitions()
    assert len(defs) == 4
    for name in lib.ACTION_NAMES:
        assert name in defs
        d = defs[name]
        assert d.frame_end > d.frame_start
        assert d.fps == 30
        assert len(d.curves) > 0
    print("test_pure_python_fixtures: PASSED")

def test_blender_live_actions():
    arm = bpy.data.objects.get('Anime_Armature')
    assert arm is not None, "Anime_Armature object not found!"

    # Build all actions
    actions = lib.build_all_anime_actions(arm, push_to_nla=True)
    assert len(actions) == 4, f"Expected 4 actions, got {len(actions)}"

    # Check NLA tracks
    track_names = [t.name for t in arm.animation_data.nla_tracks]
    print("NLA Tracks:", track_names)
    for name in lib.ACTION_NAMES:
        assert f"NLA_{name}" in track_names, f"Missing NLA track NLA_{name}"

    # Check active action
    assert arm.animation_data.action.name == "action_anime_idle_cute"

    # Check each action properties
    for name, act in actions.items():
        assert act.use_fake_user, f"Action {name} missing fake_user"
        meta = lib.ACTION_METADATA_REGISTRY[name]
        assert act.frame_start == meta.frame_start, f"Action {name} frame_start mismatch"
        assert act.frame_end == meta.frame_end, f"Action {name} frame_end mismatch"
        assert len(act.fcurves) > 0, f"Action {name} has no fcurves"

        # Check BEZIER interpolation on all keyframe points
        for fc in act.fcurves:
            for kp in fc.keyframe_points:
                assert kp.interpolation == 'BEZIER', f"Action {name} curve {fc.data_path} has non-BEZIER interpolation: {kp.interpolation}"

        # Evaluate across entire frame range
        arm.animation_data.action = act
        for frame in range(int(act.frame_start), int(act.frame_end) + 1):
            bpy.context.scene.frame_set(frame)

        print(f"Action {name}: {len(act.fcurves)} fcurves, range [{act.frame_start}, {act.frame_end}] -> PASSED")

    print("test_blender_live_actions: ALL PASSED!")

if __name__ == '__main__':
    test_pure_python_fixtures()
    test_blender_live_actions()