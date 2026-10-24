import bpy
import math
from mathutils import Vector

def run_adversarial_audit():
    print("==================================================")
    print("STARTING ADVERSARIAL RIGGING & INTEGRITY AUDIT")
    print("==================================================")

    arm = bpy.data.objects.get("Anime_Armature")
    assert arm is not None, "Anime_Armature not found in scene"
    bones = arm.data.bones
    pb = arm.pose.bones

    # 1. Exact Bone Count & Hierarchy
    total_bones = len(bones)
    print(f"Total bones: {total_bones}")
    assert total_bones == 78, f"Bone count mismatch: expected 78, got {total_bones}"

    # Spine chain check
    spine_expected = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head"]
    for i in range(len(spine_expected)):
        b = bones[spine_expected[i]]
        if i == 0:
            assert b.parent is None, f"{b.name} must be root"
        else:
            expected_parent = spine_expected[i - 1]
            assert b.parent.name == expected_parent, f"{b.name} parent expected {expected_parent}, got {b.parent.name}"

    # 2. Finger Curling Under Local +X Rotation
    finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
    phalanges = ["01", "02", "03"]
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')

    print("\n--- FINGER BONE ROLLS & LOCAL +X FLEXION AUDIT ---")
    failing_fingers = []
    for side in ["L", "R"]:
        sign = 1.0 if side == "L" else -1.0
        palm = Vector((sign * 0.43550, -0.18575, 1.01439))
        for f in finger_names:
            for p in phalanges:
                bname = f"{f}.{p}.{side}"
                pbone = pb[bname]
                pbone.rotation_mode = 'XYZ'
                pbone.rotation_euler = (0.0, 0.0, 0.0)
                bpy.context.view_layer.update()
                rest_pos = arm.matrix_world @ pbone.tail
                d_rest = (rest_pos - palm).length

                # Rotate +30 degrees around local X
                pbone.rotation_euler = (math.radians(30.0), 0.0, 0.0)
                bpy.context.view_layer.update()
                flex_pos = arm.matrix_world @ pbone.tail
                d_flex = (flex_pos - palm).length

                pbone.rotation_euler = (0.0, 0.0, 0.0)
                bpy.context.view_layer.update()

                delta = d_rest - d_flex
                if delta <= 0.0:
                    failing_fingers.append((bname, d_rest, d_flex, delta))
                else:
                    print(f"PASS: {bname} curls toward palm by {delta*1000:.2f} mm")

    assert len(failing_fingers) == 0, f"Failing finger flexions: {failing_fingers}"
    print("All 30 finger phalanges curled cleanly toward palm under +local X!")

    # 3. Twist Bone Constraints Check
    print("\n--- TWIST BONES CONSTRAINT AUDIT ---")
    twist_specs = {
        "UpperArm_Twist.L": ("ForeArm.L", 0.50),
        "UpperArm_Twist.R": ("ForeArm.R", 0.50),
        "ForeArm_Twist.L": ("Hand.L", 0.50),
        "ForeArm_Twist.R": ("Hand.R", 0.50),
    }
    for bname, (expected_target, expected_inf) in twist_specs.items():
        pbone = pb[bname]
        c = [c for c in pbone.constraints if c.type == 'COPY_ROTATION']
        assert len(c) > 0, f"No COPY_ROTATION on {bname}"
        c0 = c[0]
        assert c0.subtarget == expected_target, f"{bname} target: {c0.subtarget} != {expected_target}"
        assert abs(c0.influence - expected_inf) < 1e-4, f"{bname} influence: {c0.influence} != {expected_inf}"
        assert c0.use_y is True and c0.use_x is False and c0.use_z is False
        assert c0.target_space == 'LOCAL' and c0.owner_space == 'LOCAL'
        print(f"PASS: {bname} copy-rotation -> {expected_target} (inf={c0.influence}, local Y)")

    # 4. Skirt Radial Bones Pitch Limits
    print("\n--- SKIRT RADIAL BONES PITCH LIMIT AUDIT ---")
    for i in range(1, 13):
        bname = f"Skirt_{i:02d}"
        pbone = pb[bname]
        c = [c for c in pbone.constraints if c.type == 'LIMIT_ROTATION']
        assert len(c) > 0, f"No LIMIT_ROTATION on {bname}"
        c0 = c[0]
        min_deg = math.degrees(c0.min_x)
        max_deg = math.degrees(c0.max_x)
        assert abs(min_deg - (-15.0)) < 0.1, f"{bname} min_x: {min_deg} != -15.0"
        assert abs(max_deg - 65.0) < 0.1, f"{bname} max_x: {max_deg} != 65.0"
        assert c0.use_limit_x is True
        assert c0.owner_space == 'LOCAL'
        assert pbone.get("is_secondary_skirt") is True
        print(f"PASS: {bname} pitch clamped to [{min_deg:.1f}°, {max_deg:.1f}°]")

    # 5. Twintail Hair Spring Dynamics Properties
    print("\n--- TWINTAIL HAIR SPRING DYNAMICS AUDIT ---")
    for side in ["L", "R"]:
        for i in range(1, 6):
            bname = f"Hair_{side}_{i:02d}"
            pbone = pb[bname]
            assert pbone.get("is_secondary_hair") is True
            m = pbone.get("spring_mass")
            k = pbone.get("spring_stiffness")
            c = pbone.get("spring_damping")
            assert abs(m - 0.20) < 1e-4, f"{bname} mass: {m} != 0.20"
            assert abs(k - 150.0) < 1e-4, f"{bname} stiffness: {k} != 150.0"
            assert abs(c - 12.0) < 1e-4, f"{bname} damping: {c} != 12.0"
            print(f"PASS: {bname} spring params m={m}kg, k={k}N/m, c={c}N*s/m")

    bpy.ops.object.mode_set(mode='OBJECT')

    # 6. Submesh Skinning, DQS, and Partition of Unity
    print("\n--- SUBMESH DQS & SKINNING AUDIT ---")
    expected_submeshes = [
        "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
        "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
    ]
    for mname in expected_submeshes:
        obj = bpy.data.objects.get(mname)
        assert obj is not None, f"Mesh {mname} missing"
        # Check DQS
        arm_mods = [m for m in obj.modifiers if m.type == 'ARMATURE']
        assert len(arm_mods) > 0, f"{mname} missing Armature modifier"
        assert arm_mods[0].use_deform_preserve_volume is True, f"{mname} DQS preserve volume is False"
        assert arm_mods[0].object == arm, f"{mname} Armature modifier target is not Anime_Armature"

        # Check weights on every vertex
        num_v = len(obj.data.vertices)
        for v in obj.data.vertices:
            tot = sum(g.weight for g in v.groups)
            assert tot > 0.0, f"Vertex {v.index} in {mname} is orphaned"
            assert abs(tot - 1.0) < 1e-3, f"Vertex {v.index} in {mname} weight sum {tot} != 1.0"
        print(f"PASS: {mname} ({num_v} verts) - DQS active, zero orphans, 100% normalized")

    # 7. Critical Invariant: 0% Thigh Weight Bleeding on Anime_Skirt
    print("\n--- CRITICAL INVARIANT: ZERO THIGH WEIGHTS ON SKIRT ---")
    skirt = bpy.data.objects["Anime_Skirt"]
    prohibited = [vg.name for vg in skirt.vertex_groups if "Thigh" in vg.name or not vg.name.startswith("Skirt_")]
    assert len(prohibited) == 0, f"Prohibited groups found on Anime_Skirt: {prohibited}"
    for v in skirt.data.vertices:
        for g in v.groups:
            vg_name = skirt.vertex_groups[g.group].name
            assert vg_name.startswith("Skirt_"), f"Unexpected group {vg_name} on vertex {v.index}"
    print("PASS: Anime_Skirt has 0.000% weight on Thigh and is exclusively driven by Skirt_01..12!")

    # 8. Cross-standard metadata mapping check on Armature data block
    print("\n--- CROSS-STANDARD METADATA CHECK ---")
    arm_data = arm.data
    assert "vrm_1_0_bone_map" in arm_data, "vrm_1_0_bone_map missing from armature data"
    assert "rigify_def_bone_map" in arm_data, "rigify_def_bone_map missing from armature data"
    assert "mmd_bone_map" in arm_data, "mmd_bone_map missing from armature data"
    print("PASS: All cross-standard maps (VRM 1.0, Rigify, MMD) present on Armature data block")

    print("\n==================================================")
    print("ALL ADVERSARIAL CHECKS COMPLETED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_adversarial_audit()
