"""
Anti-Pinching Skin Weights Calculation & Volume Preservation.

Responsible for:
- Dual-bone twist distribution on limbs.
- Deltoid clavicular weighting & axilla fold clamping.
- Olecranon (elbow) 3-loop hinge cosine gradient.
- Patella (knee) rigid sesamoid locking.
- Finger bounding-cylinder isolation.
- Strict weight normalization summing to 1.0 for every vertex.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from morphomesh.geometry.mesh import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]

from .metarig import MetarigStructure, ALL_163_DEF_BONES


def _point_to_segment_distance(
    p: Tuple[float, float, float],
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
) -> float:
    """Computes minimum Euclidean distance from 3D point p to line segment a-b."""
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    l2 = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2
    if l2 < 1e-12:
        return math.sqrt((p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2 + (p[2] - a[2]) ** 2)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1] + (p[2] - a[2]) * ab[2]) / l2))
    proj = (a[0] + t * ab[0], a[1] + t * ab[1], a[2] + t * ab[2])
    return math.sqrt((p[0] - proj[0]) ** 2 + (p[1] - proj[1]) ** 2 + (p[2] - proj[2]) ** 2)


@dataclass
class SkinWeightMap:
    """Manages sparse vertex skin weights across all bones with strict normalization."""

    weights: Dict[int, Dict[str, float]] = field(default_factory=dict)

    def set_weight(self, vertex_idx: int, bone_name: str, weight: float) -> None:
        if weight <= 0.0:
            return
        if vertex_idx not in self.weights:
            self.weights[vertex_idx] = {}
        self.weights[vertex_idx][bone_name] = weight

    def add_weight(self, vertex_idx: int, bone_name: str, weight: float) -> None:
        if weight <= 0.0:
            return
        if vertex_idx not in self.weights:
            self.weights[vertex_idx] = {}
        self.weights[vertex_idx][bone_name] = self.weights[vertex_idx].get(bone_name, 0.0) + weight

    def get_vertex_weight(self, vertex_idx: int, bone_name: str) -> float:
        return self.weights.get(vertex_idx, {}).get(bone_name, 0.0)

    def normalize(self, default_bone: str = "DEF-spine.003") -> None:
        """Enforces that sum of weights for every vertex equals 1.0 (with 1e-6 epsilon)."""
        for v_idx, b_dict in list(self.weights.items()):
            tot = sum(b_dict.values())
            if tot > 1e-9:
                for b_name in list(b_dict.keys()):
                    b_dict[b_name] = b_dict[b_name] / tot
            else:
                self.weights[v_idx] = {default_bone: 1.0}

    def verify_normalization(self, tolerance: float = 1e-4) -> Tuple[bool, int, float]:
        """
        Validates that all vertices have weight sum == 1.0.
        Returns: (all_valid, total_checked, max_discrepancy).
        """
        max_disc = 0.0
        for v_idx, b_dict in self.weights.items():
            tot = sum(b_dict.values())
            disc = abs(tot - 1.0)
            if disc > max_disc:
                max_disc = disc
            if disc > tolerance:
                return False, len(self.weights), max_disc
        return True, len(self.weights), max_disc


def calculate_anti_pinch_weights(
    mesh: MeshGeometry,
    metarig: MetarigStructure,
    landmarks: Optional[Dict[str, Tuple[float, float, float]]] = None,
) -> SkinWeightMap:
    """
    Computes mathematically sound anti-pinching vertex skin weights:
    1. Dual-bone twist distribution on arms and legs.
    2. Deltoid clavicular weighting & axilla fold clamping (>=70% on spine.003).
    3. Olecranon (elbow) 3-loop hinge cosine gradient.
    4. Patella (knee) rigid locking (>=90% on shin).
    5. Finger bounding-cylinder isolation.
    6. Strict weight normalization summing to 1.0 for every vertex.
    """
    weight_map = SkinWeightMap()
    verts = mesh.vertices
    vgroups = mesh.vertex_groups or {}
    lm = landmarks or metarig.landmarks

    # Invert vertex group mapping for O(1) query: vertex_idx -> set of group names
    vg_by_v: Dict[int, Set[str]] = {i: set() for i in range(len(verts))}
    for g_name, v_indices in vgroups.items():
        for vi in v_indices:
            if vi in vg_by_v:
                vg_by_v[vi].add(g_name)

    z_chin = lm.get("chin", (0.0, 0.0, 1.427))[2]
    z_clav = lm.get("clavicle_L", (0.0, 0.0, 1.350))[2]
    z_crotch = lm.get("spine_pelvis", (0.0, 0.0, 0.825))[2]

    # Pre-extract finger centers for bounding-cylinder isolation
    finger_data: Dict[str, Tuple[Tuple[float, float, float], float]] = {}
    for side in ["L", "R"]:
        for digit in ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]:
            b = metarig.get_bone(f"DEF-{digit}.01.{side}")
    # Precompute finger x-bounds per side for robust quantile partitioning
    finger_bounds: Dict[str, Tuple[float, float]] = {}
    for s in ("L", "R"):
        s_sgn = 1.0 if s == "L" else -1.0
        v_indices = [idx for idx, grps in vg_by_v.items() if f"fingers_{s}" in grps]
        if v_indices:
            xs = [verts[vi][0] * s_sgn for vi in v_indices]
            finger_bounds[s] = (min(xs), max(xs))

    for i, (vx, vy, vz) in enumerate(verts):
        assigned = False
        groups = vg_by_v.get(i, set())

        # ----------------------------------------------------------------------
        # A. HEAD & FACIAL STRUCTURES
        # ----------------------------------------------------------------------
        if "eyes_left" in groups:
            weight_map.set_weight(i, "DEF-eye.L", 0.90)
            weight_map.set_weight(i, "DEF-lid.B.L.000", 0.05)
            weight_map.set_weight(i, "DEF-lid.T.L.000", 0.05)
            assigned = True
        elif "eyes_right" in groups:
            weight_map.set_weight(i, "DEF-eye.R", 0.90)
            weight_map.set_weight(i, "DEF-lid.B.R.000", 0.05)
            weight_map.set_weight(i, "DEF-lid.T.R.000", 0.05)
            assigned = True
        elif "eyebrows" in groups:
            side_eb = "L" if vx >= 0.0 else "R"
            weight_map.set_weight(i, f"DEF-brow.T.{side_eb}.002", 0.80)
            weight_map.set_weight(i, "DEF-head", 0.20)
            assigned = True
        elif "eyelashes" in groups:
            side_el = "L" if vx >= 0.0 else "R"
            weight_map.set_weight(i, f"DEF-lid.T.{side_el}.000", 0.70)
            weight_map.set_weight(i, f"DEF-lid.B.{side_el}.000", 0.30)
            assigned = True
        elif "lips" in groups or "mouth" in groups:
            side_s = "L" if vx >= 0.0 else "R"
            if vz > z_chin + 0.18:
                weight_map.set_weight(i, f"DEF-lip.T.{side_s}.000", 0.70)
                weight_map.set_weight(i, "DEF-head", 0.30)
            else:
                weight_map.set_weight(i, f"DEF-lip.B.{side_s}.000", 0.65)
                weight_map.set_weight(i, "DEF-jaw.center", 0.25)
                weight_map.set_weight(i, "DEF-head", 0.10)
            assigned = True
        elif "tongue" in groups:
            side_s = "L" if vx >= 0.0 else "R"
            weight_map.set_weight(i, f"DEF-tongue.{side_s}.000", 0.85)
            weight_map.set_weight(i, "DEF-jaw.center", 0.15)
            assigned = True
        elif "teeth" in groups:
            if vz > z_chin + 0.18:
                weight_map.set_weight(i, "DEF-head", 1.0)
            else:
                weight_map.set_weight(i, "DEF-jaw.center", 0.90)
                weight_map.set_weight(i, "DEF-head", 0.10)
            assigned = True
        elif "head" in groups or "face" in groups:
            weight_map.set_weight(i, "DEF-head", 0.85)
            weight_map.set_weight(i, "DEF-spine.006", 0.15)
            assigned = True
        elif "neck" in groups:
            u_neck = max(0.0, min(1.0, (vz - z_clav) / max(1e-4, (z_chin - z_clav))))
            weight_map.set_weight(i, "DEF-spine.004", (1.0 - u_neck) * 0.5)
            weight_map.set_weight(i, "DEF-spine.005", 0.5)
            weight_map.set_weight(i, "DEF-spine.006", u_neck * 0.5)
            assigned = True

        # ----------------------------------------------------------------------
        # B. FINGERS & HANDS (BOUNDING-CYLINDER ISOLATION)
        # ----------------------------------------------------------------------
        elif "fingers_L" in groups or "fingers_R" in groups:
            side_f = "L" if "fingers_L" in groups or vx >= 0.0 else "R"
            s_sign = 1.0 if side_f == "L" else -1.0
            scale_f = lm.get("head_top", (0, 0, 1.65))[2] / 1.65
            thumb_lm_key = f"joint-{side_f.lower()}-finger-1-1"
            thumb_lm = lm.get(thumb_lm_key)
            if thumb_lm and sum((c - t) ** 2 for c, t in zip((vx, vy, vz), thumb_lm)) < (0.035 * scale_f) ** 2:
                best_digit = "thumb"
            elif side_f in finger_bounds and finger_bounds[side_f][1] > (finger_bounds[side_f][0] + 1e-4):
                min_fx, max_fx = finger_bounds[side_f]
                u_f = (vx * s_sign - min_fx) / (max_fx - min_fx)
                if u_f > 0.60:
                    best_digit = "thumb"
                elif u_f > 0.38:
                    best_digit = "f_index"
                elif u_f > 0.18:
                    best_digit = "f_middle"
                elif u_f > 0.05:
                    best_digit = "f_ring"
                else:
                    best_digit = "f_pinky"
            else:
                wrist_x = lm.get(f"wrist_{side_f}", (s_sign * 0.360 * scale_f, -0.020, 0.830))[0]
                palm_x = wrist_x + s_sign * 0.025 * scale_f
                rel_x = (vx - palm_x) * s_sign

                if rel_x > 0.017 * scale_f:
                    best_digit = "thumb"
                elif rel_x > 0.007 * scale_f:
                    best_digit = "f_index"
                elif rel_x > -0.003 * scale_f:
                    best_digit = "f_middle"
                elif rel_x > -0.013 * scale_f:
                    best_digit = "f_ring"
                else:
                    best_digit = "f_pinky"

            # Assign weights exclusively to the matched finger's 3 DEF phalanges
            weight_map.set_weight(i, f"DEF-{best_digit}.01.{side_f}", 0.35)
            weight_map.set_weight(i, f"DEF-{best_digit}.02.{side_f}", 0.40)
            weight_map.set_weight(i, f"DEF-{best_digit}.03.{side_f}", 0.25)
            assigned = True

        elif "hand_L" in groups or "hand_R" in groups:
            side_h = "L" if "hand_L" in groups or vx >= 0.0 else "R"
            weight_map.set_weight(i, f"DEF-hand.{side_h}", 0.85)
            weight_map.set_weight(i, f"DEF-forearm.{side_h}.001", 0.15)
            assigned = True

        # ----------------------------------------------------------------------
        # C. UPPER LIMBS (DUAL-BONE TWIST & DELTOID CLAVICULAR & AXILLA CLAMP)
        # ----------------------------------------------------------------------
        elif "arm_upper_L" in groups or "arm_upper_R" in groups:
            side_a = "L" if "arm_upper_L" in groups or vx >= 0.0 else "R"
            sh_pt = lm[f"shoulder_{side_a}"]
            el_pt = lm[f"elbow_{side_a}"]

            u_arm = max(0.0, min(1.0, (sh_pt[2] - vz) / max(1e-4, (sh_pt[2] - el_pt[2]))))
            cx_arm = sh_pt[0] + u_arm * (el_pt[0] - sh_pt[0])

            # Axilla: medial side of upper arm (towards torso) in upper half
            is_medial = abs(vx) < abs(cx_arm) - 0.005
            is_upper = vz > el_pt[2] + 0.05
            is_axilla = (abs(vx) < 0.20 and vz < 1.32 and is_upper) or (is_medial and is_upper and (vz < sh_pt[2] - 0.01 or (vz >= sh_pt[2] - 0.01 and vy < 0.0)))

            # Acromion: superior / lateral shoulder
            is_acromion = (vz >= sh_pt[2] - 0.02) and (abs(vx) >= abs(cx_arm))

            if is_axilla:
                # Axilla skin fold locked >= 70% to chest spine.003
                weight_map.set_weight(i, "DEF-spine.003", 0.75)
                weight_map.set_weight(i, f"DEF-shoulder.{side_a}", 0.15)
                weight_map.set_weight(i, f"DEF-upper_arm.{side_a}", 0.10)
            elif is_acromion:
                weight_map.set_weight(i, f"DEF-shoulder.{side_a}", 0.45)
                weight_map.set_weight(i, f"DEF-upper_arm.{side_a}", 0.35)
                weight_map.set_weight(i, "DEF-spine.003", 0.20)
            else:
                # Dual-bone twist decomposition
                u_arm = max(0.0, min(1.0, (sh_pt[2] - vz) / max(1e-4, (sh_pt[2] - el_pt[2]))))
                # Olecranon cosine gradient near elbow (calibrated to actual elbow span 0.40 <= u_arm <= 0.65+)
                if u_arm >= 0.40:
                    u_hinge = min(1.0, max(0.0, (u_arm - 0.40) / 0.25))
                    cos_w = math.cos(0.5 * math.pi * u_hinge) ** 2
                    weight_map.set_weight(i, f"DEF-upper_arm.{side_a}.001", cos_w * 0.7)
                    weight_map.set_weight(i, f"DEF-forearm.{side_a}", (1.0 - cos_w) * 0.7)
                    weight_map.set_weight(i, f"DEF-upper_arm.{side_a}", 0.3 * (1.0 - u_arm))
                else:
                    weight_map.set_weight(i, f"DEF-upper_arm.{side_a}", 1.0 - u_arm)
                    weight_map.set_weight(i, f"DEF-upper_arm.{side_a}.001", u_arm)
            assigned = True

        elif "arm_lower_L" in groups or "arm_lower_R" in groups:
            side_a = "L" if "arm_lower_L" in groups or vx >= 0.0 else "R"
            el_pt = lm[f"elbow_{side_a}"]
            wr_pt = lm[f"wrist_{side_a}"]
            dx = wr_pt[0] - el_pt[0]
            dy = wr_pt[1] - el_pt[1]
            dz = wr_pt[2] - el_pt[2]
            bone_len_sq = dx * dx + dy * dy + dz * dz
            if bone_len_sq > 1e-6:
                u_fa = ((vx - el_pt[0]) * dx + (vy - el_pt[1]) * dy + (vz - el_pt[2]) * dz) / bone_len_sq
                u_fa = max(0.0, min(1.0, u_fa))
            else:
                u_fa = max(0.0, min(1.0, (el_pt[2] - vz) / max(1e-4, (el_pt[2] - wr_pt[2]))))

            # Dual-bone twist decomposition on forearm
            weight_map.set_weight(i, f"DEF-forearm.{side_a}", 1.0 - u_fa)
            weight_map.set_weight(i, f"DEF-forearm.{side_a}.001", u_fa)
            assigned = True

        # ----------------------------------------------------------------------
        # D. LOWER LIMBS & FEET (PATELLA LOCKING, MALLEOLI ANCHORING, 5-TOE SKINNING)
        # ----------------------------------------------------------------------
        elif "leg_upper_L" in groups or "leg_upper_R" in groups:
            side_l = "L" if "leg_upper_L" in groups or vx >= 0.0 else "R"
            s_sign = 1.0 if side_l == "L" else -1.0
            hip_pt = lm[f"hip_{side_l}"]
            kn_pt = lm[f"knee_{side_l}"]
            scale_l = lm.get("head_top", (0, 0, 1.65))[2] / 1.65

            u_thigh = max(0.0, min(1.0, (hip_pt[2] - vz) / max(1e-4, (hip_pt[2] - kn_pt[2]))))

            # 1. Sesamoid Patella Facet Bounding Test
            pat_pt = lm.get(f"patella_{side_l}", (kn_pt[0], kn_pt[1] - 0.022 * scale_l, kn_pt[2] + 0.010 * scale_l))
            r_px = 0.025 * scale_l
            r_py = 0.028 * scale_l
            r_pz = 0.034 * scale_l
            d_pat = math.sqrt(
                ((vx - pat_pt[0]) / r_px) ** 2 +
                ((vy - pat_pt[1]) / r_py) ** 2 +
                ((vz - pat_pt[2]) / r_pz) ** 2
            )
            is_patella_facet = (d_pat <= 1.0) and (vy < kn_pt[1] - 0.005 * scale_l)

            if is_patella_facet:
                # Rigid locking: core facet gets 0.95 shin, outer halo transitions down to 0.92
                if d_pat <= 0.75:
                    w_shin = 0.95
                else:
                    t_halo = (d_pat - 0.75) / 0.25
                    s_halo = 3.0 * (t_halo ** 2) - 2.0 * (t_halo ** 3)
                    w_shin = 0.95 * (1.0 - s_halo) + 0.92 * s_halo
                w_shin = max(0.92, w_shin)
                weight_map.set_weight(i, f"DEF-shin.{side_l}", w_shin)
                weight_map.set_weight(i, f"DEF-thigh.{side_l}.001", 1.0 - w_shin)
            else:
                # Cosine-squared dual-bone twist decomposition
                cos_w = math.cos(0.5 * math.pi * u_thigh) ** 2
                weight_map.set_weight(i, f"DEF-thigh.{side_l}", cos_w)
                weight_map.set_weight(i, f"DEF-thigh.{side_l}.001", 1.0 - cos_w)
            assigned = True

        elif "leg_lower_L" in groups or "leg_lower_R" in groups:
            side_l = "L" if "leg_lower_L" in groups or vx >= 0.0 else "R"
            s_sign = 1.0 if side_l == "L" else -1.0
            kn_pt = lm[f"knee_{side_l}"]
            ak_pt = lm[f"ankle_{side_l}"]
            scale_l = lm.get("head_top", (0, 0, 1.65))[2] / 1.65

            u_shin = max(0.0, min(1.0, (kn_pt[2] - vz) / max(1e-4, (kn_pt[2] - ak_pt[2]))))

            # 1. Lower Patella / Patellar Ligament Facet
            pat_pt = lm.get(f"patella_{side_l}", (kn_pt[0], kn_pt[1] - 0.022 * scale_l, kn_pt[2] + 0.010 * scale_l))
            d_pat = math.sqrt(
                ((vx - pat_pt[0]) / (0.025 * scale_l)) ** 2 +
                ((vy - pat_pt[1]) / (0.028 * scale_l)) ** 2 +
                ((vz - pat_pt[2]) / (0.034 * scale_l)) ** 2
            )
            is_patella_lower = (d_pat <= 1.0) and (vy < kn_pt[1] - 0.005 * scale_l)

            # 2. Distal Ankle Malleoli Anchoring
            m_med = lm.get(f"malleolus_medial_{side_l}", (ak_pt[0] - s_sign * 0.022 * scale_l, 0.002 * scale_l, 0.088 * scale_l))
            m_lat = lm.get(f"malleolus_lateral_{side_l}", (ak_pt[0] + s_sign * 0.026 * scale_l, -0.006 * scale_l, 0.076 * scale_l))
            d_med = math.sqrt(((vx - m_med[0]) / (0.018 * scale_l)) ** 2 + ((vy - m_med[1]) / (0.020 * scale_l)) ** 2 + ((vz - m_med[2]) / (0.024 * scale_l)) ** 2)
            d_lat = math.sqrt(((vx - m_lat[0]) / (0.016 * scale_l)) ** 2 + ((vy - m_lat[1]) / (0.020 * scale_l)) ** 2 + ((vz - m_lat[2]) / (0.024 * scale_l)) ** 2)
            d_mal = min(d_med, d_lat)

            if is_patella_lower:
                weight_map.set_weight(i, f"DEF-shin.{side_l}", 0.95)
                weight_map.set_weight(i, f"DEF-thigh.{side_l}.001", 0.05)
            elif d_mal <= 1.0:
                # Ankle malleoli locked >= 80% to DEF-shin.001
                w_mal = 0.88 - 0.08 * (3.0 * (d_mal ** 2) - 2.0 * (d_mal ** 3))
                w_mal = max(0.80, w_mal)
                weight_map.set_weight(i, f"DEF-shin.{side_l}.001", w_mal)
                weight_map.set_weight(i, f"DEF-foot.{side_l}", 1.0 - w_mal)
            else:
                # Cosine-squared dual-bone twist decomposition on lower leg
                cos_sh = math.cos(0.5 * math.pi * u_shin) ** 2
                weight_map.set_weight(i, f"DEF-shin.{side_l}", cos_sh)
                weight_map.set_weight(i, f"DEF-shin.{side_l}.001", 1.0 - cos_sh)
            assigned = True

        elif "toenails_L" in groups or "toenails_R" in groups or "toenails" in groups:
            # Dedicated Keratin Toenail Plates: Rigid 100% lock to DEF-toe
            side_tn = "L" if "toenails_L" in groups or vx >= 0.0 else "R"
            weight_map.set_weight(i, f"DEF-toe.{side_tn}", 1.0)
            assigned = True

        elif "foot_L" in groups or "foot_R" in groups:
            side_f = "L" if "foot_L" in groups or vx >= 0.0 else "R"
            s_sign = 1.0 if side_f == "L" else -1.0
            ak_pt = lm[f"ankle_{side_f}"]
            scale_f = lm.get("head_top", (0, 0, 1.65))[2] / 1.65

            # 1. Ankle Malleoli Anchoring in Foot Group
            m_med = lm.get(f"malleolus_medial_{side_f}", (ak_pt[0] - s_sign * 0.022 * scale_f, 0.002 * scale_f, 0.088 * scale_f))
            m_lat = lm.get(f"malleolus_lateral_{side_f}", (ak_pt[0] + s_sign * 0.026 * scale_f, -0.006 * scale_f, 0.076 * scale_f))
            d_med = math.sqrt(((vx - m_med[0]) / (0.018 * scale_f)) ** 2 + ((vy - m_med[1]) / (0.020 * scale_f)) ** 2 + ((vz - m_med[2]) / (0.024 * scale_f)) ** 2)
            d_lat = math.sqrt(((vx - m_lat[0]) / (0.016 * scale_f)) ** 2 + ((vy - m_lat[1]) / (0.020 * scale_f)) ** 2 + ((vz - m_lat[2]) / (0.024 * scale_f)) ** 2)
            d_mal = min(d_med, d_lat)

            if d_mal <= 1.0:
                # Malleoli anchored to shin.001 even if mesh vertex is categorized in foot_L/R
                w_mal = 0.88 - 0.08 * (3.0 * (d_mal ** 2) - 2.0 * (d_mal ** 3))
                w_mal = max(0.80, w_mal)
                weight_map.set_weight(i, f"DEF-shin.{side_f}.001", w_mal)
                weight_map.set_weight(i, f"DEF-foot.{side_f}", 1.0 - w_mal)
                assigned = True
            else:
                # 2. 5 Longitudinal Voronoi Corridors & Oblique MTP Break Line (~65 deg)
                # Calibrated for remediated Hallux (ox=-0.0265m) and Toe 2 (ox=-0.0045m)
                mtp_digit_offsets = [
                    (-0.0265, -0.095),  # Digit 0 (Hallux)
                    (-0.0045, -0.093),  # Digit 1 (Second Toe - Greek profile)
                    ( 0.0080, -0.088),  # Digit 2 (Middle Toe)
                    ( 0.0195, -0.082),  # Digit 3 (Ring Toe)
                    ( 0.0305, -0.075),  # Digit 4 (Pinky Toe)
                ]
                xi = (s_sign * (vx - ak_pt[0])) / max(1e-4, scale_f)

                if xi <= mtp_digit_offsets[0][0]:
                    y_mtp = mtp_digit_offsets[0][1] * scale_f
                elif xi >= mtp_digit_offsets[-1][0]:
                    y_mtp = mtp_digit_offsets[-1][1] * scale_f
                else:
                    y_mtp = -0.085 * scale_f
                    for k in range(len(mtp_digit_offsets) - 1):
                        x_k, y_k = mtp_digit_offsets[k]
                        x_next, y_next = mtp_digit_offsets[k + 1]
                        if x_k <= xi <= x_next:
                            t_k = (xi - x_k) / max(1e-4, (x_next - x_k))
                            y_mtp = (y_k + t_k * (y_next - y_k)) * scale_f
                            break

                # 3. Cubic Hermite Smoothstep Transition Across Oblique MTP Line
                delta_mtp = 0.015 * scale_f
                u_toe = (y_mtp - vy) / (2.0 * delta_mtp) + 0.5
                t_toe = max(0.0, min(1.0, u_toe))
                s_toe = 3.0 * (t_toe ** 2) - 2.0 * (t_toe ** 3)

                if s_toe > 0.001:
                    # Articulated phalanges and toes
                    weight_map.set_weight(i, f"DEF-toe.{side_f}", s_toe)
                    weight_map.set_weight(i, f"DEF-foot.{side_f}", 1.0 - s_toe)
                else:
                    # Posterior foot check:
                    # Restrict 15% shin blend strictly to posterior Achilles tendon insertion zone
                    is_achilles = (vy > ak_pt[1] + 0.035 * scale_f) and (vz > ak_pt[2] - 0.030 * scale_f)
                    if is_achilles:
                        weight_map.set_weight(i, f"DEF-foot.{side_f}", 0.85)
                        weight_map.set_weight(i, f"DEF-shin.{side_f}.001", 0.15)
                    else:
                        # Plantar arch bridge, midtarsus, and metatarsal ball: 100% DEF-foot
                        weight_map.set_weight(i, f"DEF-foot.{side_f}", 1.0)
                assigned = True

        # ----------------------------------------------------------------------
        # E. TORSO: CHEST, WAIST, HIPS, BREASTS
        # ----------------------------------------------------------------------
        elif "breast.L" in groups or "breast.R" in groups or "breast" in groups:
            weight_map.set_weight(i, "DEF-spine.003", 0.85)
            weight_map.set_weight(i, "DEF-spine.002", 0.15)
            assigned = True
        elif "chest" in groups:
            weight_map.set_weight(i, "DEF-spine.003", 0.80)
            weight_map.set_weight(i, "DEF-spine.002", 0.20)
            assigned = True
        elif "waist" in groups:
            weight_map.set_weight(i, "DEF-spine.001", 0.60)
            weight_map.set_weight(i, "DEF-spine.002", 0.40)
            assigned = True
        elif "hips" in groups:
            side_hip = "L" if vx >= 0.0 else "R"
            weight_map.set_weight(i, "DEF-spine", 0.70)
            weight_map.set_weight(i, f"DEF-thigh.{side_hip}", 0.30)
            assigned = True

        # Fallback: assign to closest spine bone
        if not assigned:
            if vz > z_chin:
                weight_map.set_weight(i, "DEF-head", 1.0)
            elif vz > z_clav:
                weight_map.set_weight(i, "DEF-spine.004", 1.0)
            elif vz > z_crotch:
                weight_map.set_weight(i, "DEF-spine.002", 1.0)
            else:
                weight_map.set_weight(i, "DEF-spine", 1.0)

    # Strictly normalize weights to 1.0 for every vertex
    weight_map.normalize()
    return weight_map



__all__ = [
    "_point_to_segment_distance",
    "_CANONICAL_FINGER_MAP",
    "_get_canonical_finger_map",
    "SkinWeightMap",
    "calculate_anti_pinch_weights",
]
