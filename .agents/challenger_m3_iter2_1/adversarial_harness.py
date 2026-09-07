"""
Adversarial Test Harness: Normal Alignment & Skin Burst Stress Challenger.

Evaluates Milestone 3 Iteration 2 visual critic remediation:
1. Exposed Anatomy False-Positive Stress (strapless tube top, sleeveless tunic, exposed head/neck/shoulders/arms/hands/legs)
2. True Skin Burst Detection Stress (+1mm, +5mm, +15mm displacements, 100% recall)
3. Forward Penetration Normal Alignment Stress (grazing contacts <= 0.3 vs direct inward penetrations > 0.3)
"""

import json
import math
import os
import sys
import time
from typing import Any, Dict, List, Tuple

# Ensure morphomesh is importable
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(repo_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from morphomesh.human_generator import generate_human_base_mesh
from morphomesh.inference_adapter import MeshGeometry
from morphomesh.models import DefectCategory, DefectSeverity
from morphomesh.visual_critic import (
    _compute_vertex_normals,
    evaluate_mesh_penetration,
    make_procedural_cylinder,
)


def create_strapless_tube_top(
    height: float = 1.65,
    clearance: float = 0.018,
    sectors: int = 24,
    waist_girth: float = 0.58,
    chest_girth: float = 0.82,
) -> Tuple[List[Tuple[float, float, float]], List[Tuple[int, ...]]]:
    """Generates tailored strapless tube top matching female torso anatomy without straps."""
    mesh = MeshGeometry()
    s = height / 1.65
    k_w = waist_girth / 0.58
    k_c = chest_girth / 0.82
    slices = [
        (1.03 * s, 0.125 * s * k_w + clearance, 0.088 * s * k_w + clearance, 0.0),
        (1.07 * s, 0.130 * s * (0.8 * k_w + 0.2 * k_c) + clearance, 0.092 * s * (0.8 * k_w + 0.2 * k_c) + clearance, 0.0),
        (1.14 * s, 0.142 * s * (0.4 * k_w + 0.6 * k_c) + clearance, 0.098 * s * (0.4 * k_w + 0.6 * k_c) + clearance, -0.005 * s * k_c),
        (1.22 * s, 0.150 * s * k_c + clearance, 0.112 * s * k_c + clearance, -0.012 * s * k_c),
        (1.25 * s, 0.150 * s * k_c + clearance, 0.104 * s * k_c + clearance, -0.006 * s * k_c),
    ]
    rings: List[List[int]] = []
    num_rings = len(slices)
    for r_idx, (z, rx, ry, yo) in enumerate(slices):
        ring: List[int] = []
        for i in range(sectors):
            theta = 2.0 * math.pi * i / sectors
            sin_t = math.sin(theta)
            cos_t = math.cos(theta)
            dip_z = 0.0
            if r_idx == num_rings - 1:
                if sin_t < -0.3:
                    dip_z = -0.025 * (-sin_t - 0.3) * s
                elif abs(cos_t) > 0.7:
                    dip_z = -0.020 * (abs(cos_t) - 0.7) / 0.3 * s
            mod_ry = ry
            if z >= 1.10 * s and sin_t < -0.3:
                mod_ry = ry * (1.0 + 0.38 * (-sin_t - 0.3))
            px = rx * cos_t
            py = mod_ry * sin_t + yo
            pz = z + dip_z
            norm_len = math.sqrt(px * px + py * py) or 1.0
            norm = (px / norm_len, py / norm_len, 0.0)
            idx = mesh.add_vertex((round(px, 5), round(py, 5), round(pz, 5)), norm, (i / sectors, r_idx / (num_rings - 1)))
            ring.append(idx)
        rings.append(ring)
    for r in range(len(rings) - 1):
        for i in range(sectors):
            ni = (i + 1) % sectors
            mesh.add_quad(rings[r][i], rings[r][ni], rings[r + 1][ni], rings[r + 1][i])
    verts = [v[:3] for v in mesh.vertices]
    faces = [tuple(f) for f in mesh.faces]
    return verts, faces


def create_sleeveless_tunic(
    height: float = 1.65,
    clearance: float = 0.022,
    sectors: int = 24,
) -> Tuple[List[Tuple[float, float, float]], List[Tuple[int, ...]]]:
    """Generates sleeveless tunic extending from waist down past hips to mid-thigh (z=0.72m to 1.25m)."""
    mesh = MeshGeometry()
    s = height / 1.65
    slices = [
        # bottom hem at midthigh (z = 0.72)
        (0.72 * s, 0.220 * s + clearance, 0.170 * s + clearance, 0.0),
        # thigh/hip flare (z = 0.82)
        (0.82 * s, 0.200 * s + clearance, 0.155 * s + clearance, 0.0),
        # hip line (z = 0.92)
        (0.92 * s, 0.180 * s + clearance, 0.140 * s + clearance, 0.0),
        # waist cinched (z = 1.03)
        (1.03 * s, 0.135 * s + clearance, 0.098 * s + clearance, 0.0),
        # mid torso (z = 1.14)
        (1.14 * s, 0.145 * s + clearance, 0.108 * s + clearance, -0.005 * s),
        # upper chest / scoop (z = 1.25)
        (1.25 * s, 0.152 * s + clearance, 0.115 * s + clearance, -0.008 * s),
    ]
    rings: List[List[int]] = []
    num_rings = len(slices)
    for r_idx, (z, rx, ry, yo) in enumerate(slices):
        ring: List[int] = []
        for i in range(sectors):
            theta = 2.0 * math.pi * i / sectors
            sin_t = math.sin(theta)
            cos_t = math.cos(theta)
            # Armhole dip on the top ring
            dip_z = 0.0
            if r_idx == num_rings - 1:
                if abs(cos_t) > 0.65:
                    dip_z = -0.030 * (abs(cos_t) - 0.65) / 0.35 * s
            mod_ry = ry
            if z >= 1.10 * s and sin_t < -0.3:
                mod_ry = ry * (1.0 + 0.40 * (-sin_t - 0.3))
            px = rx * cos_t
            py = mod_ry * sin_t + yo
            pz = z + dip_z
            norm_len = math.sqrt(px * px + py * py) or 1.0
            norm = (px / norm_len, py / norm_len, 0.0)
            idx = mesh.add_vertex((round(px, 5), round(py, 5), round(pz, 5)), norm, (i / sectors, r_idx / (num_rings - 1)))
            ring.append(idx)
        rings.append(ring)
    for r in range(len(rings) - 1):
        for i in range(sectors):
            ni = (i + 1) % sectors
            mesh.add_quad(rings[r][i], rings[r][ni], rings[r + 1][ni], rings[r + 1][i])
    verts = [v[:3] for v in mesh.vertices]
    faces = [tuple(f) for f in mesh.faces]
    return verts, faces


def build_segmented_human_mesh() -> Tuple[List[Tuple[float, float, float]], List[Tuple[int, ...]], Dict[str, List[int]]]:
    """
    Constructs a complete segmented anatomical human body mesh with
    distinct geometric components: Head, Neck, Shoulders, Torso, Arms (L/R), Hands (L/R), Legs (L/R), Feet (L/R).
    """
    mesh = MeshGeometry()
    vertex_groups: Dict[str, List[int]] = {}

    def add_submesh(v_list, f_list, name: str):
        base_idx = len(mesh.vertices)
        grp_indices = []
        for v in v_list:
            idx = mesh.add_vertex(v[:3], (0, 0, 1), (0, 0))
            grp_indices.append(idx)
        for f in f_list:
            if len(f) == 3:
                mesh.add_triangle(base_idx + f[0], base_idx + f[1], base_idx + f[2])
            elif len(f) == 4:
                mesh.add_quad(base_idx + f[0], base_idx + f[1], base_idx + f[2], base_idx + f[3])
        vertex_groups[name] = grp_indices

    # 1. Head (ellipsoid at z=1.60m)
    v_head, f_head = make_procedural_cylinder(radius=0.10, height=0.18, num_rings=6, num_segments=16, center_z=1.60)
    add_submesh(v_head, f_head, "head")

    # 2. Neck (cylinder at z=1.45m)
    v_neck, f_neck = make_procedural_cylinder(radius=0.06, height=0.12, num_rings=4, num_segments=16, center_z=1.45)
    add_submesh(v_neck, f_neck, "neck")

    # 3. Torso (chest/waist/hips at z=1.12m, height=0.50m)
    v_torso, f_torso = make_procedural_cylinder(radius=0.14, height=0.50, num_rings=12, num_segments=24, center_z=1.12)
    add_submesh(v_torso, f_torso, "torso")

    # 4. Shoulders (capsule connecting neck to arm joints z=1.35m)
    for sign, side in [(1.0, "L"), (-1.0, "R")]:
        v_sh = []
        for z in [1.32, 1.36]:
            for th in [0, math.pi/2, math.pi, 3*math.pi/2]:
                v_sh.append((sign * 0.18 + 0.03 * math.cos(th), 0.03 * math.sin(th), z))
        f_sh = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        add_submesh(v_sh, f_sh, f"shoulder_{side}")

    # 5. Arms (cylinders at x=+-0.22m, z=1.10m, height=0.40m)
    for sign, side in [(1.0, "L"), (-1.0, "R")]:
        v_arm, f_arm = make_procedural_cylinder(radius=0.045, height=0.38, num_rings=8, num_segments=16, center_z=1.10)
        v_arm_shifted = [(v[0] + sign * 0.22, v[1], v[2]) for v in v_arm]
        add_submesh(v_arm_shifted, f_arm, f"arm_{side}")

    # 6. Hands (spheres/boxes at x=+-0.22m, z=0.75m)
    for sign, side in [(1.0, "L"), (-1.0, "R")]:
        v_h, f_h = make_procedural_cylinder(radius=0.035, height=0.12, num_rings=4, num_segments=12, center_z=0.75)
        v_h_shifted = [(v[0] + sign * 0.22, v[1], v[2]) for v in v_h]
        add_submesh(v_h_shifted, f_h, f"hand_{side}")

    # 7. Lower legs (cylinders at x=+-0.09m, z=0.30m, height=0.45m)
    for sign, side in [(1.0, "L"), (-1.0, "R")]:
        v_leg, f_leg = make_procedural_cylinder(radius=0.055, height=0.45, num_rings=8, num_segments=16, center_z=0.30)
        v_leg_shifted = [(v[0] + sign * 0.09, v[1], v[2]) for v in v_leg]
        add_submesh(v_leg_shifted, f_leg, f"leg_lower_{side}")

    # 8. Feet (boxes at x=+-0.09m, z=0.04m)
    for sign, side in [(1.0, "L"), (-1.0, "R")]:
        v_ft, f_ft = make_procedural_cylinder(radius=0.05, height=0.08, num_rings=4, num_segments=12, center_z=0.04)
        v_ft_shifted = [(v[0] + sign * 0.09, v[1] + 0.04, v[2]) for v in v_ft]
        add_submesh(v_ft_shifted, f_ft, f"foot_{side}")

    all_verts = [v[:3] for v in mesh.vertices]
    all_faces = [tuple(f) for f in mesh.faces]
    return all_verts, all_faces, vertex_groups


class AdversarialTestRunner:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.start_time = time.time()

    def record(self, suite: str, name: str, passed: bool, details: Dict[str, Any]):
        entry = {
            "suite": suite,
            "name": name,
            "passed": passed,
            "details": details,
        }
        self.results.append(entry)
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] {suite} :: {name}")
        if not passed:
            print(f"    FAILURE DETAILS: {details}")

    # ==========================================================================
    # SUITE 1: EXPOSED ANATOMY FALSE-POSITIVE STRESS
    # ==========================================================================
    def run_suite_1_exposed_anatomy(self):
        print("\n" + "=" * 80)
        print("SUITE 1: EXPOSED ANATOMY FALSE-POSITIVE STRESS")
        print("=" * 80)

        # 1.1 Human Base Mesh (Yu Nian An) with Strapless Tube Top
        h = generate_human_base_mesh()
        b_verts = [v[:3] for v in h.mesh.vertices]
        b_faces = [tuple(f) for f in h.mesh.faces]
        tube_verts, tube_faces = create_strapless_tube_top()

        defs = evaluate_mesh_penetration(
            "Yu_Nian_An",
            ["StraplessTubeTop"],
            body_geo=(b_verts, b_faces),
            garment_geos={"StraplessTubeTop": (tube_verts, tube_faces)},
        )
        bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
        self.record(
            "Suite 1: Exposed Anatomy",
            "1.1 Clean Human Base Mesh with Strapless Tube Top (0 FP)",
            len(bursts) == 0,
            {"skin_burst_count": len(bursts), "total_defects": len(defs)},
        )

        # 1.2 Flared Shoulders Stress (+30%, +60% lateral scale on shoulders/trapezius z > 1.28m)
        for flare_pct in [30, 60]:
            scale = 1.0 + flare_pct / 100.0
            b_flared = [[v[0], v[1], v[2]] for v in b_verts]
            for idx in h.vertex_groups.get("torso", []) + h.vertex_groups.get("neck", []):
                if b_flared[idx][2] >= 1.27:
                    b_flared[idx][0] *= scale
                    b_flared[idx][1] *= scale
            defs = evaluate_mesh_penetration(
                "Yu_Nian_An_FlaredShoulders",
                ["StraplessTubeTop"],
                body_geo=(b_flared, b_faces),
                garment_geos={"StraplessTubeTop": (tube_verts, tube_faces)},
            )
            bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
            self.record(
                "Suite 1: Exposed Anatomy",
                f"1.2 Flared Shoulders (+{flare_pct}%) above Tube Top (0 FP)",
                len(bursts) == 0,
                {"scale": scale, "skin_burst_count": len(bursts)},
            )

        # 1.3 Giant Head & Thick Neck (+50% radial expansion)
        b_head = [[v[0], v[1], v[2]] for v in b_verts]
        for idx in h.vertex_groups.get("head", []) + h.vertex_groups.get("neck", []):
            b_head[idx][0] *= 1.5
            b_head[idx][1] *= 1.5
        defs = evaluate_mesh_penetration(
            "Yu_Nian_An_LargeHead",
            ["StraplessTubeTop"],
            body_geo=(b_head, b_faces),
            garment_geos={"StraplessTubeTop": (tube_verts, tube_faces)},
        )
        bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
        self.record(
            "Suite 1: Exposed Anatomy",
            "1.3 Giant Head & Neck (+50% radial expansion) (0 FP)",
            len(bursts) == 0,
            {"skin_burst_count": len(bursts)},
        )

        # 1.4 Muscular Calves & Lower Legs (+50% radial expansion)
        b_legs = [[v[0], v[1], v[2]] for v in b_verts]
        for idx in h.vertex_groups.get("leg_lower_L", []) + h.vertex_groups.get("leg_lower_R", []):
            b_legs[idx][0] *= 1.5
            b_legs[idx][1] *= 1.5
        defs = evaluate_mesh_penetration(
            "Yu_Nian_An_MuscularCalves",
            ["StraplessTubeTop"],
            body_geo=(b_legs, b_faces),
            garment_geos={"StraplessTubeTop": (tube_verts, tube_faces)},
        )
        bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
        self.record(
            "Suite 1: Exposed Anatomy",
            "1.4 Muscular Calves & Lower Legs (+50% radial expansion) (0 FP)",
            len(bursts) == 0,
            {"skin_burst_count": len(bursts)},
        )

        # 1.5 Clean Human Base Mesh with Sleeveless Tunic
        tunic_verts, tunic_faces = create_sleeveless_tunic()
        defs = evaluate_mesh_penetration(
            "Yu_Nian_An",
            ["SleevelessTunic"],
            body_geo=(b_verts, b_faces),
            garment_geos={"SleevelessTunic": (tunic_verts, tunic_faces)},
        )
        bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
        self.record(
            "Suite 1: Exposed Anatomy",
            "1.5 Clean Human Base Mesh with Sleeveless Tunic (0 FP)",
            len(bursts) == 0,
            {"skin_burst_count": len(bursts)},
        )

        # 1.5b Flared Shoulders with Sleeveless Tunic (+40%)
        b_tunic_sh = [[v[0], v[1], v[2]] for v in b_verts]
        for idx in h.vertex_groups.get("torso", []) + h.vertex_groups.get("neck", []):
            if b_tunic_sh[idx][2] >= 1.27:
                b_tunic_sh[idx][0] *= 1.40
                b_tunic_sh[idx][1] *= 1.40
        defs = evaluate_mesh_penetration(
            "Yu_Nian_An_TunicFlaredShoulders",
            ["SleevelessTunic"],
            body_geo=(b_tunic_sh, b_faces),
            garment_geos={"SleevelessTunic": (tunic_verts, tunic_faces)},
        )
        bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
        self.record(
            "Suite 1: Exposed Anatomy",
            "1.5b Flared Shoulders (+40%) above Sleeveless Tunic (0 FP)",
            len(bursts) == 0,
            {"skin_burst_count": len(bursts)},
        )

        # 1.5c Posed / Raised Arms beside Sleeveless Tunic (Lateral Displacement)
        b_tunic_arms = [[v[0], v[1], v[2]] for v in b_verts]
        for idx in h.vertex_groups.get("arm_upper_L", []) + h.vertex_groups.get("arm_lower_L", []) + h.vertex_groups.get("hand_L", []):
            b_tunic_arms[idx][0] += 0.05
        for idx in h.vertex_groups.get("arm_upper_R", []) + h.vertex_groups.get("arm_lower_R", []) + h.vertex_groups.get("hand_R", []):
            b_tunic_arms[idx][0] -= 0.05
        defs = evaluate_mesh_penetration(
            "Yu_Nian_An_TunicArms",
            ["SleevelessTunic"],
            body_geo=(b_tunic_arms, b_faces),
            garment_geos={"SleevelessTunic": (tunic_verts, tunic_faces)},
        )
        bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
        self.record(
            "Suite 1: Exposed Anatomy",
            "1.5c Posed/Laterally Spread Arms with Sleeveless Tunic (0 FP)",
            len(bursts) == 0,
            {"skin_burst_count": len(bursts)},
        )

        # 1.6 Segmented Articulated Human Geometric Body Benchmark
        seg_verts, seg_faces, seg_groups = build_segmented_human_mesh()
        g_tube_verts, g_tube_faces = make_procedural_cylinder(radius=0.16, height=0.30, num_rings=10, num_segments=24, center_z=1.12)
        defs = evaluate_mesh_penetration(
            "SegmentedBody",
            ["TubeTop"],
            body_geo=(seg_verts, seg_faces),
            garment_geos={"TubeTop": (g_tube_verts, g_tube_faces)},
        )
        bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
        self.record(
            "Suite 1: Exposed Anatomy",
            "1.6 Segmented Articulated Human Body with Tube Top (0 FP)",
            len(bursts) == 0,
            {"skin_burst_count": len(bursts)},
        )

        # 1.7 Vertical Proximity Fuzzing around Collar and Hem
        g_min_z = min(v[2] for v in g_tube_verts)
        g_max_z = max(v[2] for v in g_tube_verts)
        for delta_mm in [0.1, 0.5, 1.0, 2.0, 5.0]:
            delta_m = delta_mm / 1000.0
            collar_ring = [(0.18 * math.cos(i * math.pi / 4), 0.18 * math.sin(i * math.pi / 4), g_max_z + delta_m) for i in range(8)]
            hem_ring = [(0.18 * math.cos(i * math.pi / 4), 0.18 * math.sin(i * math.pi / 4), g_min_z - delta_m) for i in range(8)]
            b_prox_verts = seg_verts + collar_ring + hem_ring
            b_prox_faces = seg_faces + [(len(seg_verts) + i, len(seg_verts) + (i + 1) % 8, len(seg_verts) + (i + 2) % 8) for i in range(0, 6, 2)]
            defs = evaluate_mesh_penetration(
                "Body_Proximity",
                ["TubeTop"],
                body_geo=(b_prox_verts, b_prox_faces),
                garment_geos={"TubeTop": (g_tube_verts, g_tube_faces)},
            )
            bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
            self.record(
                "Suite 1: Exposed Anatomy",
                f"1.7 Vertical Boundary Proximity delta_z = +{delta_mm:.1f}mm outside garment (0 FP)",
                len(bursts) == 0,
                {"delta_mm": delta_mm, "skin_burst_count": len(bursts)},
            )

        # 1.8 Boundary Edge Open Hem Stepping (Tier 3 filter validation)
        b_hem_step = [[v[0], v[1], v[2]] for v in seg_verts]
        for i, v in enumerate(b_hem_step):
            if abs(v[2] - (g_min_z + 0.004)) < 0.003:
                b_hem_step[i][0] *= 1.25
                b_hem_step[i][1] *= 1.25
        defs = evaluate_mesh_penetration(
            "Body_HemStep",
            ["TubeTop"],
            body_geo=(b_hem_step, seg_faces),
            garment_geos={"TubeTop": (g_tube_verts, g_tube_faces)},
        )
        bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
        self.record(
            "Suite 1: Exposed Anatomy",
            "1.8 Open Boundary Hem Stepping (Tier 3 filter) (0 FP)",
            len(bursts) == 0,
            {"skin_burst_count": len(bursts)},
        )

    # ==========================================================================
    # SUITE 2: TRUE SKIN BURST DETECTION STRESS
    # ==========================================================================
    def run_suite_2_true_skin_burst(self):
        print("\n" + "=" * 80)
        print("SUITE 2: TRUE SKIN BURST DETECTION STRESS")
        print("=" * 80)

        R_body = 0.14
        R_garm = 0.16
        height = 0.50
        b_verts, b_faces = make_procedural_cylinder(radius=R_body, height=height, num_rings=16, num_segments=32, center_z=0.0)
        g_verts, g_faces = make_procedural_cylinder(radius=R_garm, height=height * 0.8, num_rings=16, num_segments=32, center_z=0.0)

        # 2.1 Prescribed displacements: +1mm, +5mm, +15mm past garment surface
        for disp_mm in [1.0, 5.0, 15.0]:
            disp_m = disp_mm / 1000.0
            R_target = R_garm + disp_m
            scale = R_target / R_body
            b_burst = [[v[0], v[1], v[2]] for v in b_verts]
            displaced_count = 0
            for i, v in enumerate(b_burst):
                theta = math.atan2(v[1], v[0])
                if abs(v[2]) < 0.05 and abs(theta) < math.pi / 4.0:
                    b_burst[i][0] *= scale
                    b_burst[i][1] *= scale
                    displaced_count += 1

            defs = evaluate_mesh_penetration(
                "Torso",
                ["Garment"],
                clearance_tolerance=0.0005,
                body_geo=(b_burst, b_faces),
                garment_geos={"Garment": (g_verts, g_faces)},
            )
            bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
            has_burst = len(bursts) >= 1
            depth_measured = bursts[0].penetration_depth_mm if has_burst else 0.0
            expected_depth = disp_mm
            depth_err = abs(depth_measured - expected_depth)
            expected_sev = DefectSeverity.MAJOR if disp_mm <= 3.0 else DefectSeverity.CRITICAL
            sev_match = (bursts[0].severity == expected_sev) if has_burst else False

            self.record(
                "Suite 2: True Skin Burst",
                f"2.1 Genuine Skin Burst +{disp_mm:.1f}mm protrusion (100% Recall, Analytical Depth)",
                has_burst and depth_err <= 0.35 and sev_match,
                {
                    "disp_mm": disp_mm,
                    "displaced_vert_count": displaced_count,
                    "burst_detected": has_burst,
                    "measured_depth_mm": round(depth_measured, 2),
                    "depth_error_mm": round(depth_err, 4),
                    "severity": str(bursts[0].severity) if has_burst else None,
                    "expected_severity": str(expected_sev),
                },
            )

        # 2.2 Pin-point Burst (Single isolated vertex burst)
        b_single = [[v[0], v[1], v[2]] for v in b_verts]
        best_idx = min(range(len(b_single)), key=lambda i: abs(b_single[i][2]) + abs(b_single[i][1]) + abs(b_single[i][0] - R_body))
        b_single[best_idx][0] = R_garm + 0.005  # +5mm burst
        defs = evaluate_mesh_penetration(
            "Torso",
            ["Garment"],
            clearance_tolerance=0.0005,
            body_geo=(b_single, b_faces),
            garment_geos={"Garment": (g_verts, g_faces)},
        )
        bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
        self.record(
            "Suite 2: True Skin Burst",
            "2.2 Pin-Point Isolated Vertex Burst (+5mm) (100% Recall)",
            len(bursts) >= 1 and math.isclose(bursts[0].penetration_depth_mm, 5.0, abs_tol=0.4),
            {"burst_count": len(bursts), "measured_depth": bursts[0].penetration_depth_mm if bursts else None},
        )

        # 2.3 Spatial Locations: Upper Torso, Mid Torso, Lower Torso, Back
        g_min_z = min(v[2] for v in g_verts)
        g_max_z = max(v[2] for v in g_verts)
        locations = [
            ("Upper Torso (near collar)", g_max_z - 0.02, 0.0),
            ("Mid Torso (waist)", 0.0, 0.0),
            ("Lower Torso (near hem)", g_min_z + 0.02, 0.0),
            ("Back Torso (dorsal)", 0.0, math.pi),
            ("Left Flank", 0.0, math.pi / 2.0),
            ("Right Flank", 0.0, -math.pi / 2.0),
        ]
        for loc_name, target_z, target_theta in locations:
            b_loc = [[v[0], v[1], v[2]] for v in b_verts]
            for i, v in enumerate(b_loc):
                th = math.atan2(v[1], v[0])
                if abs(v[2] - target_z) < 0.03 and abs(th - target_theta) < math.pi / 6.0:
                    b_loc[i][0] *= (R_garm + 0.008) / R_body
                    b_loc[i][1] *= (R_garm + 0.008) / R_body
            defs = evaluate_mesh_penetration(
                "Torso",
                ["Garment"],
                clearance_tolerance=0.0005,
                body_geo=(b_loc, b_faces),
                garment_geos={"Garment": (g_verts, g_faces)},
            )
            bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
            self.record(
                "Suite 2: True Skin Burst",
                f"2.3 Spatial Location Burst: {loc_name} (+8mm) (100% Recall)",
                len(bursts) >= 1,
                {"location": loc_name, "burst_count": len(bursts), "depth_mm": bursts[0].penetration_depth_mm if bursts else None},
            )

        # 2.4 Sub-millimeter Tolerance Margin Test (+0.3mm < 0.5mm tolerance vs +0.7mm > 0.5mm tolerance)
        for test_disp_mm, should_detect in [(0.3, False), (0.7, True)]:
            b_tol = [[v[0], v[1], v[2]] for v in b_verts]
            R_target = R_garm + (test_disp_mm / 1000.0)
            scale = R_target / R_body
            for i, v in enumerate(b_tol):
                th = math.atan2(v[1], v[0])
                if abs(v[2]) < 0.05 and abs(th) < math.pi / 6.0:
                    b_tol[i][0] *= scale
                    b_tol[i][1] *= scale
            defs = evaluate_mesh_penetration(
                "Torso",
                ["Garment"],
                clearance_tolerance=0.0005,  # 0.5mm
                body_geo=(b_tol, b_faces),
                garment_geos={"Garment": (g_verts, g_faces)},
            )
            bursts = [d for d in defs if d.defect_type == "SKIN_BURST"]
            detected = len(bursts) >= 1
            self.record(
                "Suite 2: True Skin Burst",
                f"2.4 Sub-millimeter Tolerance Margin +{test_disp_mm:.1f}mm (Expect Detected = {should_detect})",
                detected == should_detect,
                {"disp_mm": test_disp_mm, "detected": detected, "expected": should_detect},
            )

    # ==========================================================================
    # SUITE 3: FORWARD PENETRATION NORMAL ALIGNMENT STRESS
    # ==========================================================================
    def run_suite_3_forward_penetration_normal_alignment(self):
        print("\n" + "=" * 80)
        print("SUITE 3: FORWARD PENETRATION NORMAL ALIGNMENT STRESS")
        print("=" * 80)

        # Base body wall at x=0 facing +X (normal = (1, 0, 0))
        b_verts = [(0.0, -0.5, -0.5), (0.0, 0.5, -0.5), (0.0, 0.5, 0.5), (0.0, -0.5, 0.5)]
        b_faces = [(0, 1, 2, 3)]

        # 3.1 Grazing & Non-Opposing Contacts (n_g . n_b <= 0.3)
        grazing_scenarios = [
            ("Perpendicular Grazing (dot = 0.0, 90 deg)", 90.0, 0.0),
            ("Oblique Grazing (dot = 0.15, 81.4 deg)", math.degrees(math.acos(0.15)), 0.15),
            ("Oblique Grazing (dot = 0.25, 75.5 deg)", math.degrees(math.acos(0.25)), 0.25),
            ("Exact Threshold Non-Opposing (dot = 0.3000)", math.degrees(math.acos(0.3000)), 0.3000),
            ("Inverted Backfacing (dot = -0.50, 120 deg)", 120.0, -0.50),
            ("Completely Inverted (dot = -1.00, 180 deg)", 180.0, -1.00),
        ]
        for desc, angle_deg, expected_dot in grazing_scenarios:
            rad = math.radians(angle_deg)
            s = 0.01
            t_xy = (-math.sin(rad), math.cos(rad), 0.0)
            c = (-0.010, 0.0, 0.0)  # submerged 10mm inside body
            v0 = (c[0] - s * t_xy[0], c[1] - s * t_xy[1], c[2] - s)
            v1 = (c[0] + s * t_xy[0], c[1] + s * t_xy[1], c[2] - s)
            v2 = (c[0] + s * t_xy[0], c[1] + s * t_xy[1], c[2] + s)
            v3 = (c[0] - s * t_xy[0], c[1] - s * t_xy[1], c[2] + s)
            g_verts = [v0, v1, v2, v3]
            g_faces = [(0, 1, 2, 3)]

            defs = evaluate_mesh_penetration(
                "Wall",
                ["Sheet"],
                clearance_tolerance=0.0005,
                max_search_radius=0.05,
                body_geo=(b_verts, b_faces),
                garment_geos={"Sheet": (g_verts, g_faces)},
            )
            pen_defs = [d for d in defs if d.category == DefectCategory.PENETRATION and d.defect_type == "PENETRATION"]
            self.record(
                "Suite 3: Forward Penetration",
                f"3.1 Grazing/Non-Opposing Contact: {desc} (Filtered Out = True)",
                len(pen_defs) == 0,
                {"angle_deg": round(angle_deg, 2), "expected_dot": round(expected_dot, 4), "pen_defs_count": len(pen_defs)},
            )

        # 3.2 Direct Inward Penetrations (n_g . n_b > 0.3)
        direct_scenarios = [
            ("Parallel Direct Penetration (dot = 1.000, 0 deg)", 0.0, 1.000, 5.0),
            ("Angled Direct Penetration (dot = 0.866, 30 deg)", 30.0, 0.866, 5.0),
            ("Angled Direct Penetration (dot = 0.707, 45 deg)", 45.0, 0.7071, 5.0),
            ("Angled Direct Penetration (dot = 0.500, 60 deg)", 60.0, 0.500, 5.0),
            ("Threshold Penetration (dot = 0.3001, 72.54 deg)", math.degrees(math.acos(0.3001)), 0.3001, 5.0),
            ("Threshold Penetration (dot = 0.3500, 69.51 deg)", math.degrees(math.acos(0.3500)), 0.3500, 5.0),
        ]
        for desc, angle_deg, expected_dot, depth_mm in direct_scenarios:
            rad = math.radians(angle_deg)
            s = 0.01
            t_xy = (-math.sin(rad), math.cos(rad), 0.0)
            c = (-depth_mm / 1000.0, 0.0, 0.0)
            v0 = (c[0] - s * t_xy[0], c[1] - s * t_xy[1], c[2] - s)
            v1 = (c[0] + s * t_xy[0], c[1] + s * t_xy[1], c[2] - s)
            v2 = (c[0] + s * t_xy[0], c[1] + s * t_xy[1], c[2] + s)
            v3 = (c[0] - s * t_xy[0], c[1] - s * t_xy[1], c[2] + s)
            g_verts = [v0, v1, v2, v3]
            g_faces = [(0, 1, 2, 3)]

            defs = evaluate_mesh_penetration(
                "Wall",
                ["Sheet"],
                clearance_tolerance=0.0005,
                max_search_radius=0.05,
                body_geo=(b_verts, b_faces),
                garment_geos={"Sheet": (g_verts, g_faces)},
            )
            pen_defs = [d for d in defs if d.category == DefectCategory.PENETRATION and d.defect_type == "PENETRATION"]
            diagnosed = len(pen_defs) >= 1
            measured_depth = pen_defs[0].penetration_depth_mm if diagnosed else 0.0

            self.record(
                "Suite 3: Forward Penetration",
                f"3.2 Direct Inward Penetration: {desc} (Diagnosed = True)",
                diagnosed,
                {"angle_deg": round(angle_deg, 2), "expected_dot": round(expected_dot, 4), "measured_depth": measured_depth},
            )

        # 3.3 Micro-Stepping Quantization Across Cosine Alignment Spectrum [-1.0, +1.0]
        dot_steps = [-1.0, -0.8, -0.6, -0.4, -0.2, 0.0, 0.1, 0.2, 0.25, 0.28, 0.299, 0.3000, 0.3001, 0.301, 0.32, 0.4, 0.5, 0.6, 0.8, 0.95, 1.0]
        step_passed = True
        step_details = []
        for d_val in dot_steps:
            rad = math.acos(max(-1.0, min(1.0, d_val)))
            s = 0.005
            t_xy = (-math.sin(rad), math.cos(rad), 0.0)
            c = (-0.015, 0.0, 0.0)  # -15mm
            v0 = (c[0] - s * t_xy[0], c[1] - s * t_xy[1], c[2] - s)
            v1 = (c[0] + s * t_xy[0], c[1] + s * t_xy[1], c[2] - s)
            v2 = (c[0] + s * t_xy[0], c[1] + s * t_xy[1], c[2] + s)
            v3 = (c[0] - s * t_xy[0], c[1] - s * t_xy[1], c[2] + s)
            g_verts = [v0, v1, v2, v3]
            g_faces = [(0, 1, 2, 3)]

            defs = evaluate_mesh_penetration(
                "Wall",
                ["Sheet"],
                clearance_tolerance=0.0005,
                max_search_radius=0.05,
                body_geo=(b_verts, b_faces),
                garment_geos={"Sheet": (g_verts, g_faces)},
            )
            pen_defs = [d for d in defs if d.category == DefectCategory.PENETRATION and d.defect_type == "PENETRATION"]
            detected = len(pen_defs) >= 1
            expected = d_val > 0.3000
            if detected != expected:
                step_passed = False
            step_details.append({"dot": d_val, "detected": detected, "expected": expected, "correct": detected == expected})

        self.record(
            "Suite 3: Forward Penetration",
            "3.3 Micro-Stepping Quantization Across Spectrum (Binary Cutoff at dot > 0.3)",
            step_passed,
            {"total_steps": len(dot_steps), "all_correct": step_passed, "sample_steps": step_details},
        )

        # 3.4 Penetration Depths & Actionable Recommendation Formula Validation (d_rec = 1.25 * d_pen + 1mm)
        for test_depth_mm in [1.0, 3.0, 5.0, 12.0]:
            test_depth_m = test_depth_mm / 1000.0
            s = 0.02
            c = (-test_depth_m, 0.0, 0.0)
            v0 = (c[0], -s, -s)
            v1 = (c[0], s, -s)
            v2 = (c[0], s, s)
            v3 = (c[0], -s, s)
            g_verts = [v0, v1, v2, v3]
            g_faces = [(0, 1, 2, 3)]

            defs = evaluate_mesh_penetration(
                "Wall",
                ["Sheet"],
                clearance_tolerance=0.0005,
                max_search_radius=0.05,
                body_geo=(b_verts, b_faces),
                garment_geos={"Sheet": (g_verts, g_faces)},
            )
            pen_defs = [d for d in defs if d.category == DefectCategory.PENETRATION and d.defect_type == "PENETRATION"]
            valid = False
            rec_offset_match = False
            smoothing_match = False
            if len(pen_defs) >= 1:
                p = pen_defs[0]
                rec = p.recommendation
                expected_offset_m = round(1.25 * (p.penetration_depth_mm / 1000.0) + 0.001, 4)
                if rec and rec.parameters.get("offset") == expected_offset_m:
                    rec_offset_match = True
                if rec and rec.parameters.get("smooth_weights") is True and rec.parameters.get("smoothing_method") == "LAPLACIAN":
                    smoothing_match = True
                valid = rec_offset_match and smoothing_match

            self.record(
                "Suite 3: Forward Penetration",
                f"3.4 Recommendation Formula & Smoothing (depth = {test_depth_mm:.1f}mm)",
                valid,
                {
                    "test_depth_mm": test_depth_mm,
                    "measured_depth_mm": pen_defs[0].penetration_depth_mm if pen_defs else None,
                    "rec_offset_match": rec_offset_match,
                    "smoothing_match": smoothing_match,
                },
            )

    def summarize(self) -> Dict[str, Any]:
        duration = time.time() - self.start_time
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["passed"])
        failed_tests = total_tests - passed_tests
        pass_rate = (passed_tests / total_tests) * 100.0 if total_tests > 0 else 0.0

        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate_percentage": round(pass_rate, 2),
            "verdict": "APPROVE" if failed_tests == 0 else "REJECT",
            "duration_seconds": round(duration, 3),
            "results": self.results,
        }

        print("\n" + "=" * 80)
        print("ADVERSARIAL STRESS TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests Executed : {total_tests}")
        print(f"Passed               : {passed_tests}")
        print(f"Failed               : {failed_tests}")
        print(f"Pass Rate            : {pass_rate:.2f}%")
        print(f"Verdict              : {summary['verdict']}")
        print(f"Elapsed Time         : {duration:.3f}s")
        print("=" * 80)

        return summary


def main():
    runner = AdversarialTestRunner()
    runner.run_suite_1_exposed_anatomy()
    runner.run_suite_2_true_skin_burst()
    runner.run_suite_3_forward_penetration_normal_alignment()
    summary = runner.summarize()

    out_json = os.path.join(os.path.dirname(__file__), "adversarial_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote full structured test results to: {out_json}")

    sys.exit(0 if summary["verdict"] == "APPROVE" else 1)


if __name__ == "__main__":
    main()
