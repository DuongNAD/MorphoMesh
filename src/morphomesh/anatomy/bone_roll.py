"""
MorphoMesh Anatomy: Biomechanical Bone Roll & Pre-Bend Solver.

Solves closed-form bone roll normalization and 1-DOF joint pre-bends:
- Hinge plane normal calculation: n_hinge = (u1 x u2) / ||u1 x u2||
- 1-DOF joint pre-bending (elbows +Y, knees -Y, animal stifles/hocks) eliminating collinear IK singularities
- Closed-form Blender zero-roll frame normalization:
    theta_roll = atan2(x0 . z_desired, z0 . z_desired)
  eliminating candy-wrapper collapse and pole target flipping
- Bilateral symmetry reflection across sagittal plane
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np


@dataclass
class BoneRollResult:
    """Result of biomechanical bone roll calculation."""
    bone_name: str
    roll_radians: float
    roll_degrees: float
    hinge_normal: Tuple[float, float, float]
    local_y: Tuple[float, float, float]
    local_z_target: Tuple[float, float, float]
    blender_script_command: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bone_name": self.bone_name,
            "roll_radians": round(self.roll_radians, 6),
            "roll_degrees": round(self.roll_degrees, 3),
            "hinge_normal": [round(c, 5) for c in self.hinge_normal],
            "local_y": [round(c, 5) for c in self.local_y],
            "local_z_target": [round(c, 5) for c in self.local_z_target],
            "blender_script_command": self.blender_script_command,
        }


@dataclass
class PreBendResult:
    """Result of 1-DOF joint pre-bending."""
    chain_name: str
    middle_joint_name: str
    original_position: Tuple[float, float, float]
    prebent_position: Tuple[float, float, float]
    displacement_vector: Tuple[float, float, float]
    interior_angle_deg: float
    is_prebent: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_name": self.chain_name,
            "middle_joint_name": self.middle_joint_name,
            "original_position": [round(c, 5) for c in self.original_position],
            "prebent_position": [round(c, 5) for c in self.prebent_position],
            "displacement_vector": [round(c, 5) for c in self.displacement_vector],
            "interior_angle_deg": round(self.interior_angle_deg, 2),
            "is_prebent": self.is_prebent,
        }


def _to_np_vec(p: Union[Tuple[float, float, float], List[float], np.ndarray]) -> np.ndarray:
    return np.asarray(p, dtype=np.float64)[:3]


def compute_hinge_plane_normal(
    p_parent: Union[Tuple[float, float, float], np.ndarray],
    p_joint: Union[Tuple[float, float, float], np.ndarray],
    p_child: Union[Tuple[float, float, float], np.ndarray],
    default_normal: Optional[Union[Tuple[float, float, float], np.ndarray]] = None,
) -> np.ndarray:
    """
    Calculate the biological hinge plane unit normal vector:
      m = u1 x u2
      n = m / ||m||
    
    If the limb chain is strictly collinear (||m|| < 1e-4), falls back to default normal
    projected orthogonal to the limb axis.
    """
    p1 = _to_np_vec(p_parent)
    p2 = _to_np_vec(p_joint)
    p3 = _to_np_vec(p_child)

    u1 = p2 - p1
    u2 = p3 - p2

    len_u1 = np.linalg.norm(u1)
    len_u2 = np.linalg.norm(u2)
    if len_u1 < 1e-6 or len_u2 < 1e-6:
        return np.array([1.0, 0.0, 0.0])

    u1_hat = u1 / len_u1
    u2_hat = u2 / len_u2

    cross = np.cross(u1_hat, u2_hat)
    cross_len = np.linalg.norm(cross)

    if cross_len > 1e-4:
        return cross / cross_len

    # Collinear fallback: choose vector perpendicular to bone axis
    if default_normal is not None:
        def_norm = _to_np_vec(default_normal)
        proj = def_norm - np.dot(def_norm, u1_hat) * u1_hat
        proj_len = np.linalg.norm(proj)
        if proj_len > 1e-4:
            return proj / proj_len

    # Default anatomical flexion axis: lateral X axis (1, 0, 0)
    ref = np.array([1.0, 0.0, 0.0])
    proj = ref - np.dot(ref, u1_hat) * u1_hat
    proj_len = np.linalg.norm(proj)
    if proj_len > 1e-4:
        return proj / proj_len

    ref2 = np.array([0.0, 1.0, 0.0])
    proj2 = ref2 - np.dot(ref2, u1_hat) * u1_hat
    return proj2 / (np.linalg.norm(proj2) + 1e-9)


def apply_joint_prebend(
    p_parent: Union[Tuple[float, float, float], np.ndarray],
    p_joint: Union[Tuple[float, float, float], np.ndarray],
    p_child: Union[Tuple[float, float, float], np.ndarray],
    min_bend_angle_deg: float = 3.5,
    min_displacement: float = 0.015,
    bend_direction: Optional[Union[Tuple[float, float, float], np.ndarray]] = None,
    joint_name: str = "joint",
    chain_name: str = "limb_chain",
) -> PreBendResult:
    """
    Enforce a natural biological pre-bend on 1-DOF hinge joints.
    
    If collinear or straight, displaces the middle joint in the bend direction
    by at least `min_displacement` (e.g. 15mm) to eliminate collinear IK singularities.
    """
    p1 = _to_np_vec(p_parent)
    p2 = _to_np_vec(p_joint)
    p3 = _to_np_vec(p_child)

    orig_p2 = p2.copy()
    u1 = p2 - p1
    u2 = p3 - p2
    len_u1 = max(float(np.linalg.norm(u1)), 1e-6)
    len_u2 = max(float(np.linalg.norm(u2)), 1e-6)
    u1_hat = u1 / len_u1
    u2_hat = u2 / len_u2

    # Interior angle between segments
    dot_val = float(np.clip(np.dot(u1_hat, u2_hat), -1.0, 1.0))
    interior_angle = math.degrees(math.acos(dot_val))

    # Perpendicular distance from collinear line p1 -> p3
    w = p3 - p1
    len_w = max(float(np.linalg.norm(w)), 1e-6)
    w_hat = w / len_w
    proj_on_w = p1 + np.dot(p2 - p1, w_hat) * w_hat
    d_perp = float(np.linalg.norm(p2 - proj_on_w))

    needs_prebend = (interior_angle < min_bend_angle_deg) or (d_perp < min_displacement)

    if not needs_prebend:
        return PreBendResult(
            chain_name=chain_name,
            middle_joint_name=joint_name,
            original_position=(float(orig_p2[0]), float(orig_p2[1]), float(orig_p2[2])),
            prebent_position=(float(orig_p2[0]), float(orig_p2[1]), float(orig_p2[2])),
            displacement_vector=(0.0, 0.0, 0.0),
            interior_angle_deg=interior_angle,
            is_prebent=False,
        )

    # Determine bend direction vector
    if bend_direction is not None:
        bend_dir = _to_np_vec(bend_direction)
        # Project orthogonal to w_hat
        bend_dir = bend_dir - np.dot(bend_dir, w_hat) * w_hat
        len_b = np.linalg.norm(bend_dir)
        if len_b > 1e-4:
            bend_hat = bend_dir / len_b
        else:
            bend_hat = np.array([0.0, 1.0, 0.0])
    else:
        # If already slightly displaced, follow existing displacement
        if d_perp > 1e-4:
            bend_hat = (p2 - proj_on_w) / d_perp
        else:
            # Hinge cross bone
            n_hinge = compute_hinge_plane_normal(p1, p2, p3)
            bend_hat = np.cross(n_hinge, w_hat)
            bend_hat = bend_hat / (np.linalg.norm(bend_hat) + 1e-9)

    # Amount of displacement required to reach min_displacement
    disp_needed = max(min_displacement - d_perp, min_displacement)
    p2_new = p2 + disp_needed * bend_hat
    disp_vec = p2_new - orig_p2

    # Recompute angle
    u1_new = (p2_new - p1) / np.linalg.norm(p2_new - p1)
    u2_new = (p3 - p2_new) / np.linalg.norm(p3 - p2_new)
    new_angle = math.degrees(math.acos(float(np.clip(np.dot(u1_new, u2_new), -1.0, 1.0))))

    return PreBendResult(
        chain_name=chain_name,
        middle_joint_name=joint_name,
        original_position=(float(orig_p2[0]), float(orig_p2[1]), float(orig_p2[2])),
        prebent_position=(float(p2_new[0]), float(p2_new[1]), float(p2_new[2])),
        displacement_vector=(float(disp_vec[0]), float(disp_vec[1]), float(disp_vec[2])),
        interior_angle_deg=new_angle,
        is_prebent=True,
    )


def solve_biomechanical_bone_roll(
    head: Union[Tuple[float, float, float], List[float], np.ndarray],
    tail: Union[Tuple[float, float, float], List[float], np.ndarray],
    pole_target: Union[Tuple[float, float, float], List[float], np.ndarray],
    bone_name: str = "bone",
) -> BoneRollResult:
    """
    Compute closed-form Blender edit bone roll angle theta_roll.
    
    In Blender:
    - EditBone.y_axis = (tail - head) / ||tail - head||
    - Default zero-roll reference frame is (x0, y, z0)
    - Given desired local Z axis target (pole target direction):
        theta_roll = atan2(x0 . z_desired, z0 . z_desired)
    
    This guarantees that the bone's local Z axis points directly at the pole target,
    completely eliminating candy-wrapper collapse and 180-degree pole target flips.
    """
    h = _to_np_vec(head)
    t = _to_np_vec(tail)
    pole = _to_np_vec(pole_target)

    bone_vec = t - h
    bone_len = np.linalg.norm(bone_vec)
    if bone_len < 1e-6:
        # Degenerate bone fallback
        return BoneRollResult(
            bone_name=bone_name,
            roll_radians=0.0,
            roll_degrees=0.0,
            hinge_normal=(1.0, 0.0, 0.0),
            local_y=(0.0, 0.0, 1.0),
            local_z_target=(0.0, 1.0, 0.0),
            blender_script_command=f"bone.roll = 0.000000",
        )

    y_hat = bone_vec / bone_len

    # 1. Blender Default Zero-Roll Reference Frame (x0, y_hat, z0)
    # Per Blender source code (source/blender/blenkernel/intern/armature.cc):
    # If bone is parallel to world Z axis:
    if abs(y_hat[0]) < 1e-4 and abs(y_hat[1]) < 1e-4:
        if y_hat[2] > 0:
            x0 = np.array([0.0, 1.0, 0.0])
        else:
            x0 = np.array([0.0, -1.0, 0.0])
    else:
        # Default: x0 = [-y, x, 0] / sqrt(x^2 + y^2)
        x0 = np.array([-y_hat[1], y_hat[0], 0.0])
        x0 = x0 / np.linalg.norm(x0)

    z0 = np.cross(x0, y_hat)
    z0 = z0 / np.linalg.norm(z0)

    # 2. Desired Local Z Axis (perpendicular to y_hat pointing toward pole)
    # If pole_target is an absolute position:
    v_target = pole - h
    # If pole was already a unit direction:
    if np.linalg.norm(v_target) < 1e-4:
        v_target = pole

    # Project v_target perpendicular to y_hat
    z_desired = v_target - np.dot(v_target, y_hat) * y_hat
    z_desired_len = np.linalg.norm(z_desired)

    if z_desired_len < 1e-4:
        # Target is parallel to bone vector; fallback to z0
        z_desired_hat = z0.copy()
    else:
        z_desired_hat = z_desired / z_desired_len

    # 3. Closed-Form Angle Calculation
    # In the (x0, z0) plane:
    # cos(theta) = z0 . z_desired
    # sin(theta) = x0 . z_desired
    dot_z = float(np.clip(np.dot(z0, z_desired_hat), -1.0, 1.0))
    dot_x = float(np.clip(np.dot(x0, z_desired_hat), -1.0, 1.0))
    theta_roll = math.atan2(dot_x, dot_z)

    # Hinge normal is cross product (x_axis = y_hat x z_desired_hat)
    hinge_norm = np.cross(y_hat, z_desired_hat)
    hinge_norm_len = np.linalg.norm(hinge_norm)
    if hinge_norm_len > 1e-4:
        hinge_norm = hinge_norm / hinge_norm_len
    else:
        hinge_norm = x0.copy()

    cmd = f"bone.roll = {theta_roll:.6f}"

    return BoneRollResult(
        bone_name=bone_name,
        roll_radians=theta_roll,
        roll_degrees=math.degrees(theta_roll),
        hinge_normal=(float(hinge_norm[0]), float(hinge_norm[1]), float(hinge_norm[2])),
        local_y=(float(y_hat[0]), float(y_hat[1]), float(y_hat[2])),
        local_z_target=(float(z_desired_hat[0]), float(z_desired_hat[1]), float(z_desired_hat[2])),
        blender_script_command=cmd,
    )


def solve_limb_chain_bone_roll_and_prebend(
    joint_proximal: Union[Tuple[float, float, float], np.ndarray],
    joint_middle: Union[Tuple[float, float, float], np.ndarray],
    joint_distal: Union[Tuple[float, float, float], np.ndarray],
    chain_type: str = "human_arm",
    side: str = "L",
) -> Tuple[PreBendResult, BoneRollResult, BoneRollResult]:
    """
    Solve pre-bend and bone rolls for a 2-segment limb chain (e.g. arm or leg).
    
    Args:
        joint_proximal: Shoulder / Hip position.
        joint_middle: Elbow / Knee / Stifle position.
        joint_distal: Wrist / Ankle / Hock position.
        chain_type: "human_arm", "human_leg", "quadruped_forelimb", "quadruped_hindlimb".
        side: "L" or "R".
        
    Returns:
        (prebend_result, proximal_bone_roll, distal_bone_roll)
    """
    p1 = _to_np_vec(joint_proximal)
    p2 = _to_np_vec(joint_middle)
    p3 = _to_np_vec(joint_distal)

    # Determine biological bend direction and pole direction
    # In Blender:
    # Human arm: elbow points posterior (+Y in Blender coords)
    # Human leg: knee points anterior (-Y in Blender coords)
    # Quadruped forelimb: elbow points posterior (+Y)
    # Quadruped hindlimb: stifle points anterior (-Y), hock points posterior (+Y)
    if "arm" in chain_type or "forelimb" in chain_type:
        bend_dir = np.array([0.0, 1.0, 0.0])  # +Y posterior
        pole_target_prox = p2 + np.array([0.0, 0.5, 0.0])
        pole_target_dist = p2 + np.array([0.0, 0.5, 0.0])
        mid_name = "elbow"
    elif "hindlimb" in chain_type:
        bend_dir = np.array([0.0, -1.0, 0.0])  # Stifle bends forward (-Y)
        pole_target_prox = p2 + np.array([0.0, -0.5, 0.0])
        pole_target_dist = p2 + np.array([0.0, 0.5, 0.0])  # Hock bends backward (+Y)
        mid_name = "stifle"
    else:  # human_leg
        bend_dir = np.array([0.0, -1.0, 0.0])  # -Y anterior (kneecap)
        pole_target_prox = p2 + np.array([0.0, -0.5, 0.0])
        pole_target_dist = p2 + np.array([0.0, -0.5, 0.0])
        mid_name = "knee"

    # Enforce pre-bend
    prebend_res = apply_joint_prebend(
        p1, p2, p3,
        min_bend_angle_deg=4.0,
        min_displacement=0.018,
        bend_direction=bend_dir,
        joint_name=f"{mid_name}_{side}",
        chain_name=f"{chain_type}_{side}",
    )
    p2_bent = _to_np_vec(prebend_res.prebent_position)

    # Proximal bone: p1 -> p2_bent
    prox_name = f"{chain_type}_proximal_{side}"
    dist_name = f"{chain_type}_distal_{side}"

    roll_prox = solve_biomechanical_bone_roll(p1, p2_bent, pole_target_prox, bone_name=prox_name)
    roll_dist = solve_biomechanical_bone_roll(p2_bent, p3, pole_target_dist, bone_name=dist_name)

    return prebend_res, roll_prox, roll_dist
