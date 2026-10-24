"""
Prototype test script for secondary spring dynamics and keyframe baking.
Runs in Blender headless against output/anime_rigged.blend.
"""

import sys
import math
from typing import Dict, List, Tuple

import bpy
import mathutils

# 1. Physics solver functions
def calculate_damping_ratio(m: float, k: float, c: float) -> Tuple[float, float, Tuple[float, float]]:
    c_critical = 2.0 * math.sqrt(k * m)
    zeta = c / c_critical
    discriminant = c * c - 4.0 * m * k
    if discriminant >= 0:
        sqrt_disc = math.sqrt(discriminant)
        r1 = (-c + sqrt_disc) / (2.0 * m)
        r2 = (-c - sqrt_disc) / (2.0 * m)
    else:
        alpha = -c / (2.0 * m)
        beta = math.sqrt(-discriminant) / (2.0 * m)
        r1 = alpha
        r2 = beta
    return c_critical, zeta, (r1, r2)


def solve_spring_damper_step(
    pos: float,
    vel: float,
    rest_pos: float,
    mass: float,
    stiffness: float,
    damping: float,
    ext_accel: float,
    dt: float,
) -> Tuple[float, float]:
    if mass <= 1e-6:
        mass = 1e-6
    dt = min(max(dt, 1e-5), 0.1)
    spring_force = -stiffness * (pos - rest_pos)
    force = spring_force + mass * ext_accel
    vel_new = (vel + (force / mass) * dt) / (1.0 + (damping / mass) * dt)
    pos_new = pos + vel_new * dt
    return pos_new, vel_new


def solve_rk4_step(
    x: float,
    v: float,
    x0: float,
    m: float,
    k: float,
    c: float,
    ext_accel: float,
    dt: float,
) -> Tuple[float, float]:
    def deriv(curr_x: float, curr_v: float) -> Tuple[float, float]:
        dx = curr_v
        dv = (-k * (curr_x - x0) - c * curr_v + m * ext_accel) / m
        return dx, dv

    k1_x, k1_v = deriv(x, v)
    k2_x, k2_v = deriv(x + 0.5 * dt * k1_x, v + 0.5 * dt * k1_v)
    k3_x, k3_v = deriv(x + 0.5 * dt * k2_x, v + 0.5 * dt * k2_v)
    k4_x, k4_v = deriv(x + dt * k3_x, v + dt * k3_v)

    new_x = x + (dt / 6.0) * (k1_x + 2.0 * k2_x + 2.0 * k3_x + k4_x)
    new_v = v + (dt / 6.0) * (k1_v + 2.0 * k2_v + 2.0 * k3_v + k4_v)
    return new_x, new_v


def test_physics_model():
    m, k, c = 0.20, 150.0, 12.0
    c_crit, zeta, (r1, r2) = calculate_damping_ratio(m, k, c)
    print(f"Damping: c_crit={c_crit:.4f}, zeta={zeta:.4f}, r1={r1:.4f}, r2={r2:.4f}")
    assert zeta >= 1.0, f"System is underdamped: zeta={zeta}"
    assert r1 < 0 and r2 < 0, "Roots are not negative"

    # Test RK4 vs impulse
    dt = 1.0 / 30.0
    x, v = 0.0, 0.0
    for _ in range(3):
        x, v = solve_rk4_step(x, v, 0.0, m, k, c, ext_accel=10.0, dt=dt / 4.0)
    assert abs(x) > 0.0, "No displacement under impulse"

    peak = abs(x)
    for _ in range(60):
        for _ in range(4):
            x, v = solve_rk4_step(x, v, 0.0, m, k, c, ext_accel=0.0, dt=dt / 4.0)
    assert abs(x) < 0.20 * peak, f"Failed to damp out: x={x}, peak={peak}"
    print("Physics verification PASSED!")


def test_skirt_and_hair_baking():
    blend_path = "output/anime_rigged.blend"
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    arm = bpy.data.objects.get("Anime_Armature")
    assert arm is not None, "Anime_Armature not found"

    if not arm.animation_data:
        arm.animation_data_create()

    # Create dummy walk action
    act = bpy.data.actions.new("test_walk_action")
    act.use_fake_user = True
    arm.animation_data.action = act

    # Add thigh swing keyframes
    pb_thigh_l = arm.pose.bones.get("Thigh.L")
    pb_thigh_r = arm.pose.bones.get("Thigh.R")
    pb_hips = arm.pose.bones.get("Hips")
    pb_head = arm.pose.bones.get("Head")

    for f in range(1, 33):
        phase = 2.0 * math.pi * (f - 1) / 32.0
        thigh_l_angle = 0.5 * math.sin(phase)  # ~28 deg
        thigh_r_angle = -0.5 * math.sin(phase)
        
        # Hips vertical bounce
        hips_z = 0.02 * math.sin(2.0 * phase)
        pb_hips.location = (0.0, 0.0, hips_z)
        pb_hips.keyframe_insert(data_path="location", frame=f)

        # Thigh rotations
        pb_thigh_l.rotation_quaternion = mathutils.Quaternion((math.cos(thigh_l_angle / 2.0), math.sin(thigh_l_angle / 2.0), 0.0, 0.0))
        pb_thigh_r.rotation_quaternion = mathutils.Quaternion((math.cos(thigh_r_angle / 2.0), math.sin(thigh_r_angle / 2.0), 0.0, 0.0))
        pb_thigh_l.keyframe_insert(data_path="rotation_quaternion", frame=f)
        pb_thigh_r.keyframe_insert(data_path="rotation_quaternion", frame=f)

        # Head gentle sway
        head_tilt = 0.05 * math.sin(phase)
        pb_head.rotation_quaternion = mathutils.Quaternion((math.cos(head_tilt / 2.0), 0.0, 0.0, math.sin(head_tilt / 2.0)))
        pb_head.keyframe_insert(data_path="rotation_quaternion", frame=f)

    print("Base walk keyframes created.")

    # Now simulate baking secondary dynamics for twintails and skirt
    hair_bones_l = [f"Hair_L_{i:02d}" for i in range(1, 6)]
    hair_bones_r = [f"Hair_R_{i:02d}" for i in range(1, 6)]
    skirt_bones = [f"Skirt_{i:02d}" for i in range(1, 13)]

    # Bake skirt
    for f in range(1, 33):
        phase = 2.0 * math.pi * (f - 1) / 32.0
        thigh_l_flex = max(0.0, math.sin(phase))
        thigh_r_flex = max(0.0, -math.sin(phase))

        for i, bname in enumerate(skirt_bones):
            pb = arm.pose.bones.get(bname)
            # Front left: Skirt_10, 11, 12, 01
            # Front right: Skirt_10, 09, 08, 07
            push = 0.0
            if i in [9, 10, 11, 0]: # 10, 11, 12, 01
                push += thigh_l_flex * 0.55
            if i in [9, 8, 7, 6]:   # 10, 09, 08, 07
                push += thigh_r_flex * 0.55

            # Clamp to [-15°, 65°]
            pitch_deg = math.degrees(push)
            pitch_deg = max(-15.0, min(65.0, pitch_deg))
            rad = math.radians(pitch_deg)

            # Insert rotation
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = mathutils.Quaternion((math.cos(rad / 2.0), math.sin(rad / 2.0), 0.0, 0.0))
            pb.keyframe_insert(data_path="rotation_quaternion", frame=f)

    # Bake hair
    for f in range(1, 33):
        phase = 2.0 * math.pi * (f - 1) / 32.0
        # Lateral sway lag
        hair_angle_l = 0.08 * math.sin(phase - 0.3)
        hair_angle_r = -0.08 * math.sin(phase - 0.3)

        for j, bname in enumerate(hair_bones_l):
            pb = arm.pose.bones.get(bname)
            amp = hair_angle_l * (1.0 + 0.15 * j)
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = mathutils.Quaternion((math.cos(amp / 2.0), 0.0, math.sin(amp / 2.0), 0.0))
            pb.keyframe_insert(data_path="rotation_quaternion", frame=f)

        for j, bname in enumerate(hair_bones_r):
            pb = arm.pose.bones.get(bname)
            amp = hair_angle_r * (1.0 + 0.15 * j)
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = mathutils.Quaternion((math.cos(amp / 2.0), 0.0, math.sin(amp / 2.0), 0.0))
            pb.keyframe_insert(data_path="rotation_quaternion", frame=f)

    print(f"Bake complete! Total fcurves in action: {len(act.fcurves)}")
    assert len(act.fcurves) > 20, "Secondary bone curves not inserted"


if __name__ == "__main__":
    test_physics_model()
    test_skirt_and_hair_baking()
    print("ALL PROTOTYPE TESTS PASSED!")
