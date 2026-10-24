"""
MorphoMesh Hime Cut Hair Strata and Spline Curves Generator.

Responsible for:
- HairLayerConfig & HairGroomConfig parameter definitions.
- get_6_stratum_hime_cut_layers: Bangs, Sidelocks, Crown, Temporal, Dorsal cascade, Flyaways.
- get_default_hime_cut_layers: 6 layers backward-compatible mapping.
- HairCurveSpline container dataclass.
- generate_hime_cut_splines: 3D procedural curve point evaluation.
- generate_6_stratum_hime_cut_splines: Master 6-stratum generator.
"""

from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("morphomesh.grooming.hime_cut")

@dataclass
class HairLayerConfig:
    """Parametric specification for a single structural hair stratum."""

    name: str
    strand_count: int  # Guide parent curves count
    render_strand_count: int  # Interpolated render strands
    length: float  # Mean length in meters
    length_variation: float = 0.05
    clump_factor: float = 0.25
    clump_shape: float = 0.70  # Curve exponent from root to tip
    noise_frequency: float = 14.0
    noise_amplitude: float = 0.0012
    root_radius: float = 0.00016
    tip_radius: float = 0.000025
    points_per_curve: int = 12
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HairGroomConfig:
    """Master hair grooming configuration for a character hairstyle."""

    hair_style: str = "hime_cut_long"
    hair_color: str = "silky_black"
    total_strand_count: int = 15000
    scalp_vertex_group: str = "head"
    material_name: str = "Mat_Human_Hair"
    viewport_density: float = 0.20
    layers: Dict[str, HairLayerConfig] = field(default_factory=dict)

    def __post_init__(self):
        if not self.layers:
            self.layers = get_default_hime_cut_layers(self.total_strand_count)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hair_style": self.hair_style,
            "hair_color": self.hair_color,
            "total_strand_count": self.total_strand_count,
            "scalp_vertex_group": self.scalp_vertex_group,
            "material_name": self.material_name,
            "viewport_density": self.viewport_density,
            "layers": {k: v.to_dict() for k, v in self.layers.items()},
        }


def get_6_stratum_hime_cut_layers(total_guides: int = 15000) -> Dict[str, HairLayerConfig]:
    """Returns the dedicated 6 cranial strata defining the authentic Hime Cut hairstyle."""
    scale = total_guides / 15000.0
    return {
        "Hair_Hime_Bangs": HairLayerConfig(
            name="Hair_Hime_Bangs",
            strand_count=int(2200 * scale),
            render_strand_count=14000,
            length=0.13,  # Reaches cleanly above eyebrow line (Z ≈ 1.54m - 1.57m)
            length_variation=0.02,
            clump_factor=0.15,
            noise_amplitude=0.0006,
            description="Stratum 1: Blunt straight forehead bangs cleanly cut above eyebrows",
        ),
        "Hair_Hime_Sidelocks": HairLayerConfig(
            name="Hair_Hime_Sidelocks",
            strand_count=int(2500 * scale),
            render_strand_count=18000,
            length=0.20,  # Cheek length to jawline / chin (Z ≈ 1.42m)
            length_variation=0.03,
            clump_factor=0.20,
            noise_amplitude=0.0008,
            description="Stratum 2: Symmetrical cheek-length sidelocks (bins) framing jawline down to Z ≈ 1.42m",
        ),
        "Hair_Scalp_Crown": HairLayerConfig(
            name="Hair_Scalp_Crown",
            strand_count=int(3200 * scale),
            render_strand_count=25000,
            length=0.18,
            length_variation=0.04,
            clump_factor=0.22,
            noise_amplitude=0.0010,
            description="Stratum 3: Scalp crown cap providing root volume and offset parting line",
        ),
        "Hair_Temporal_Transitions": HairLayerConfig(
            name="Hair_Temporal_Transitions",
            strand_count=int(1800 * scale),
            render_strand_count=12000,
            length=0.30,
            length_variation=0.04,
            clump_factor=0.22,
            noise_amplitude=0.0009,
            description="Stratum 4: Temporal transitions wrapping naturally around the ears without clipping",
        ),
        "Hair_Back_Cascade": HairLayerConfig(
            name="Hair_Back_Cascade",
            strand_count=int(5000 * scale),
            render_strand_count=45000,
            length=0.72,  # Cascades past shoulders down to mid-back (Z ≈ 0.95m)
            length_variation=0.05,
            clump_factor=0.28,
            noise_amplitude=0.0012,
            description="Stratum 5: Flowing dorsal cascade falling past shoulders down to mid-back (Z ≈ 0.95m)",
        ),
        "Hair_Flyaways": HairLayerConfig(
            name="Hair_Flyaways",
            strand_count=int(500 * scale),
            render_strand_count=3000,
            length=0.14,
            length_variation=0.05,
            clump_factor=0.05,
            noise_amplitude=0.0025,
            root_radius=0.00009,
            tip_radius=0.000015,
            description="Stratum 6: Fine flyaway strands for natural photorealism",
        ),
    }


def get_default_hime_cut_layers(
    total_guides: int = 15000,
    pure_strata: bool = False,
) -> Dict[str, HairLayerConfig]:
    """
    Returns hair strata. If pure_strata=True, returns the authentic 6 cranial hairstyle strata.
    If pure_strata=False (default), returns the 6 backward-compatible strata including facial grooming.
    """
    if pure_strata:
        return get_6_stratum_hime_cut_layers(total_guides)

    # Distribute total guide budget proportionally
    scale = total_guides / 15000.0

    return {
        "Hair_Hime_Bangs": HairLayerConfig(
            name="Hair_Hime_Bangs",
            strand_count=int(2200 * scale),
            render_strand_count=14000,
            length=0.13,  # 13 cm: reaches right at eyebrow ridge (Z = 1.53m)
            length_variation=0.03,
            clump_factor=0.15,
            noise_amplitude=0.0008,
            description="Blunt straight forehead fringe bangs grazing the eyebrows",
        ),
        "Hair_Hime_Sidelocks": HairLayerConfig(
            name="Hair_Hime_Sidelocks",
            strand_count=int(2500 * scale),
            render_strand_count=18000,
            length=0.38,  # 38 cm: descending past cheeks down to clavicle
            length_variation=0.04,
            clump_factor=0.20,
            noise_amplitude=0.0010,
            description="Symmetrical face-framing sidelocks flanking the cheeks to collarbone",
        ),
        "Hair_Scalp_Crown": HairLayerConfig(
            name="Hair_Scalp_Crown",
            strand_count=int(3200 * scale),
            render_strand_count=25000,
            length=0.20,
            length_variation=0.05,
            clump_factor=0.22,
            noise_amplitude=0.0012,
            description="Scalp crown volume contouring cranium with soft center-offset parting",
        ),
        "Hair_Back_Cascade": HairLayerConfig(
            name="Hair_Back_Cascade",
            strand_count=int(6100 * scale),
            render_strand_count=48000,
            length=0.98,  # ~1.0m: flows over scapulae and spine down to hips/mid-thigh
            length_variation=0.06,
            clump_factor=0.28,
            noise_amplitude=0.0015,
            description="Long flowing back hair cascade extending to hips (~1.0m length)",
        ),
        "Hair_Eyebrows": HairLayerConfig(
            name="Hair_Eyebrows",
            strand_count=int(500 * scale),
            render_strand_count=2000,
            length=0.012,
            length_variation=0.02,
            clump_factor=0.10,
            noise_amplitude=0.0004,
            description="Soft melancholic thin arched eyebrows above upper eyelids",
        ),
        "Hair_Eyelashes": HairLayerConfig(
            name="Hair_Eyelashes",
            strand_count=int(500 * scale),
            render_strand_count=2000,
            length=0.009,
            length_variation=0.02,
            clump_factor=0.08,
            noise_amplitude=0.0003,
            description="Upper and lower curved eyelashes framing almond eyes",
        ),
    }


# ==============================================================================
# 2. PURE PYTHON 3D HAIR SPLINE GENERATOR
# ==============================================================================

@dataclass
class HairCurveSpline:
    """Encapsulates a single 3D hair curve spline with points and radii."""

    points: List[Tuple[float, float, float]]
    radii: List[float]
    layer_name: str
    length: float


def _calc_spline_length(pts: Sequence[Tuple[float, float, float]]) -> float:
    """Computes genuine polyline arc length by summing 3D Euclidean segment distances."""
    return sum(
        math.sqrt(sum((pts[k][c] - pts[k - 1][c]) ** 2 for c in range(3)))
        for k in range(1, len(pts))
    )


def generate_hime_cut_splines(
    config: Optional[HairGroomConfig] = None,
    height: float = 1.65,
    sample_density_scale: float = 0.10,  # Fraction of guides to generate for offline testing
) -> Dict[str, List[HairCurveSpline]]:
    """
    Generates authentic 3D spline curves for Yu Nian An's signature hime cut.
    Returns dictionary mapping layer name to list of HairCurveSpline objects.
    """
    if config is None:
        config = HairGroomConfig()

    s = height / 1.65
    z_crown = 1.645 * s
    z_brow = 1.540 * s
    z_clavicle = 1.320 * s
    z_hip = 0.720 * s

    splines_by_layer: Dict[str, List[HairCurveSpline]] = {}

    for layer_name, layer_cfg in config.layers.items():
        count = max(4, int(layer_cfg.strand_count * sample_density_scale))
        pts_per_curve = layer_cfg.points_per_curve
        layer_splines: List[HairCurveSpline] = []

        if layer_name == "Hair_Hime_Bangs":
            # Stratum 1: Forehead fringe cut blunt cleanly above eyebrows (Z ≈ 1.54m - 1.57m)
            bangs_count = max(36, count)
            for i in range(bangs_count):
                u = i / max(1, bangs_count - 1)
                u_rel = (u - 0.5) / 0.5  # Normalized lateral coordinate in [-1.0, 1.0]
                u_rel_sq = u_rel * u_rel

                x0 = 0.075 * u_rel * s
                # Roots follow anatomical cranial curvature
                y_root = (-0.095 + 0.040 * u_rel_sq) * s
                z0 = (1.638 - 0.012 * u_rel_sq) * s

                # Target Z above eyebrows
                target_z = (1.552 - 0.015 * max(0.0, abs(u_rel) - 0.70)) * s
                y_tip = (-0.118 + 0.038 * u_rel_sq) * s

                curve_pts: List[Tuple[float, float, float]] = []
                radii: List[float] = []

                for p in range(pts_per_curve):
                    t = p / max(1, pts_per_curve - 1)
                    drape_y = -0.010 * (1.0 - 0.35 * abs(u_rel)) * math.sin(t * math.pi) * s
                    curv_y = y_root + t * (y_tip - y_root) + drape_y
                    curv_z = z0 + t * (target_z - z0)
                    curv_x = x0 + 0.002 * u_rel * t * s
                    curve_pts.append((round(curv_x, 5), round(curv_y, 5), round(curv_z, 5)))
                    r = layer_cfg.root_radius + t * (layer_cfg.tip_radius - layer_cfg.root_radius)
                    radii.append(round(r, 6))

                length = _calc_spline_length(curve_pts)
                layer_splines.append(HairCurveSpline(curve_pts, radii, layer_name, length))

        elif layer_name == "Hair_Hime_Sidelocks":
            # Stratum 2: Symmetrical cheek-framing locks terminated blunt at jawline / chin (Z ≈ 1.42m)
            half = count // 2
            if layer_cfg.length <= 0.25:
                # 6-stratum mode: cheek-length sidelocks framing jawline and chin down to Z ≈ 1.42m
                for side, sign in [("L", 1.0), ("R", -1.0)]:
                    for i in range(half):
                        u = i / max(1, half - 1)
                        x0 = sign * (0.052 + 0.014 * u) * s
                        y0 = (-0.088 - 0.018 * u) * s
                        z0 = (1.615 - 0.025 * u) * s

                        target_z = 1.418 * s
                        curve_pts = []
                        radii = []

                        for p in range(pts_per_curve):
                            t = p / max(1, pts_per_curve - 1)
                            curv_x = x0 + sign * (0.001 - 0.003 * math.sin(t * math.pi)) * s
                            curv_y = y0 - 0.015 * t * s - 0.004 * math.sin(t * math.pi) * s
                            curv_z = z0 + t * (target_z - z0)
                            curve_pts.append((round(curv_x, 5), round(curv_y, 5), round(curv_z, 5)))
                            r = layer_cfg.root_radius + t * (layer_cfg.tip_radius - layer_cfg.root_radius)
                            radii.append(round(r, 6))

                        length = _calc_spline_length(curve_pts)
                        layer_splines.append(HairCurveSpline(curve_pts, radii, layer_name, length))
            else:
                # Legacy mode: descending to collarbone (Z ≈ 1.35m) for backward test compatibility
                for side, sign in [("L", 1.0), ("R", -1.0)]:
                    for i in range(half):
                        u = i / max(1, half - 1)
                        x0 = sign * (0.050 + 0.015 * u) * s
                        y0 = (-0.095 - 0.018 * u) * s
                        z0 = (z_crown - 0.045 - 0.015 * u) * s

                        target_z = z_clavicle + 0.030 * s
                        curve_pts = []
                        radii = []

                        for p in range(pts_per_curve):
                            t = p / max(1, pts_per_curve - 1)
                            curv_x = x0 + sign * 0.002 * math.sin(t * math.pi) * s
                            curv_y = y0 - 0.018 * t * s - 0.004 * math.sin(t * math.pi) * s
                            curv_z = z0 + t * (target_z - z0)
                            curve_pts.append((round(curv_x, 5), round(curv_y, 5), round(curv_z, 5)))
                            r = layer_cfg.root_radius + t * (layer_cfg.tip_radius - layer_cfg.root_radius)
                            radii.append(round(r, 6))

                        length = _calc_spline_length(curve_pts)
                        layer_splines.append(HairCurveSpline(curve_pts, radii, layer_name, length))

        elif layer_name == "Hair_Scalp_Crown":
            # Stratum 3: Scalp crown cap providing root volume (+3mm lift) and offset parting (+4mm)
            for i in range(count):
                u = i / max(1, count - 1)
                ang = math.pi * (0.85 + 1.30 * u)
                r_cx = 0.090 * s
                r_cy = 0.092 * s
                x0 = r_cx * math.cos(ang) + 0.004 * s  # +4mm offset parting
                y0 = r_cy * math.sin(ang) + 0.005 * s
                z0 = z_crown + 0.008 * s  # +3mm root volume lift
                tip_x = x0 * 1.01
                tip_y = y0 * 1.01
                tip_z = z0 - 0.025 * s
                curve_pts = [
                    (round(x0, 5), round(y0, 5), round(z0, 5)),
                    (round(tip_x, 5), round(tip_y, 5), round(tip_z, 5)),
                ]
                radii = [layer_cfg.root_radius, layer_cfg.tip_radius]
                length = _calc_spline_length(curve_pts)
                layer_splines.append(HairCurveSpline(curve_pts, radii, layer_name, length))

        elif layer_name == "Hair_Temporal_Transitions":
            # Stratum 4: Temporal transitions wrapping naturally around ears (clearance >= 0.015m)
            half = count // 2
            for side, sign in [("L", 1.0), ("R", -1.0)]:
                for i in range(half):
                    u = i / max(1, half - 1)
                    x0 = sign * (0.076 + 0.012 * u) * s
                    y0 = (-0.015 + 0.035 * u) * s
                    z0 = (1.590 - 0.015 * u) * s

                    target_z = 1.450 * s
                    curve_pts = []
                    radii = []

                    for p in range(pts_per_curve):
                        t = p / max(1, pts_per_curve - 1)
                        curv_x = x0 + sign * 0.008 * math.sin(t * math.pi * 0.8) * s
                        curv_y = y0 + 0.030 * t * s
                        curv_z = z0 + t * (target_z - z0)
                        curve_pts.append((round(curv_x, 5), round(curv_y, 5), round(curv_z, 5)))
                        r = layer_cfg.root_radius + t * (layer_cfg.tip_radius - layer_cfg.root_radius)
                        radii.append(round(r, 6))

                    length = _calc_spline_length(curve_pts)
                    layer_splines.append(HairCurveSpline(curve_pts, radii, layer_name, length))

        elif layer_name == "Hair_Back_Cascade":
            # Stratum 5: Flowing dorsal cascade falling past shoulders to mid-back (Z ≈ 0.95m)
            if layer_cfg.length < 0.85:
                # 6-stratum mode: terminates at mid-back Z ≈ 0.95m with +15mm thoracic clearance
                for i in range(count):
                    u = i / max(1, count - 1)
                    angle = -math.pi * 0.38 + u * math.pi * 0.76
                    rad = 0.096 * s
                    x0 = rad * math.sin(angle)
                    y0 = rad * math.cos(angle) + 0.016 * s
                    z0 = (1.618 - 0.022 * abs(math.sin(angle))) * s

                    target_z = 0.950 * s
                    curve_pts = []
                    radii = []

                    for p in range(pts_per_curve):
                        t = p / max(1, pts_per_curve - 1)
                        bulge_y = (0.042 * math.sin(t * math.pi * 0.75) if t < 0.65 else 0.028) * s
                        curv_y = y0 + bulge_y + 0.015 * t * s
                        fan_x = x0 * (1.0 + 0.38 * math.sin(t * math.pi * 0.85))
                        curv_z = z0 + t * (target_z - z0)
                        curve_pts.append((round(fan_x, 5), round(curv_y, 5), round(curv_z, 5)))
                        r = layer_cfg.root_radius + t * (layer_cfg.tip_radius - layer_cfg.root_radius)
                        radii.append(round(r, 6))

                    length = _calc_spline_length(curve_pts)
                    layer_splines.append(HairCurveSpline(curve_pts, radii, layer_name, length))
            else:
                # Legacy mode: falls down to hip level (~0.70m, L ~ 1.0m)
                for i in range(count):
                    u = i / max(1, count - 1)
                    angle = -math.pi * 0.40 + u * math.pi * 0.80
                    rad = 0.098 * s
                    x0 = rad * math.sin(angle)
                    y0 = rad * math.cos(angle) + 0.018 * s
                    z0 = (z_crown - 0.030 - 0.020 * abs(math.sin(angle))) * s

                    target_z = z_hip - 0.020 * s
                    curve_pts = []
                    radii = []

                    for p in range(pts_per_curve):
                        t = p / max(1, pts_per_curve - 1)
                        bulge_y = 0.038 * math.sin(t * math.pi * 0.8) * s if t < 0.6 else 0.018 * s
                        curv_y = y0 + bulge_y + 0.012 * t * s
                        fan_x = x0 * (1.0 + 0.35 * math.sin(t * math.pi))
                        curv_z = z0 + t * (target_z - z0)
                        curve_pts.append((round(fan_x, 5), round(curv_y, 5), round(curv_z, 5)))
                        r = layer_cfg.root_radius + t * (layer_cfg.tip_radius - layer_cfg.root_radius)
                        radii.append(round(r, 6))

                    length = _calc_spline_length(curve_pts)
                    layer_splines.append(HairCurveSpline(curve_pts, radii, layer_name, length))

        elif layer_name == "Hair_Flyaways":
            # Stratum 6: 500 fine flyaway strands with harmonic micro-frizz for airy photorealism
            for i in range(count):
                u = i / max(1, count - 1)
                angle = -math.pi * 0.85 + u * math.pi * 1.70
                rad = (0.092 + 0.006 * math.sin(i * 1.7)) * s
                x0 = rad * math.sin(angle)
                y0 = rad * math.cos(angle) + 0.005 * s
                z0 = (1.640 + 0.010 * math.cos(i * 2.3)) * s

                curve_pts = []
                radii = []

                for p in range(pts_per_curve):
                    t = p / max(1, pts_per_curve - 1)
                    curl_x = 0.0025 * math.sin(24.0 * t + i) * s
                    curl_y = 0.0025 * math.cos(24.0 * t + i) * s
                    curv_x = x0 + curl_x + 0.005 * t * math.sin(angle) * s
                    curv_y = y0 + curl_y + 0.005 * t * math.cos(angle) * s
                    curv_z = z0 - 0.14 * t * s
                    curve_pts.append((round(curv_x, 5), round(curv_y, 5), round(curv_z, 5)))
                    r = layer_cfg.root_radius + t * (layer_cfg.tip_radius - layer_cfg.root_radius)
                    radii.append(round(r, 6))

                length = _calc_spline_length(curve_pts)
                layer_splines.append(HairCurveSpline(curve_pts, radii, layer_name, length))

        else:
            # General facial strata (Eyebrows, Eyelashes)
            is_brow = "Eyebrows" in layer_name
            is_lash = "Eyelashes" in layer_name

            for i in range(count):
                u = i / max(1, count - 1)
                if is_brow:
                    side = 1.0 if i % 2 == 0 else -1.0
                    sub_u = (i // 2) / max(1, (count // 2) - 1)
                    x0 = side * (0.018 + 0.032 * sub_u) * s
                    y0 = (-0.126 - 0.003 * math.sin(sub_u * math.pi)) * s
                    z0 = (1.536 + 0.008 * math.sin(sub_u * math.pi)) * s
                    tip_x = x0 + side * 0.004 * s
                    tip_y = y0 - 0.003 * s
                    tip_z = z0 - 0.003 * s
                    curve_pts = [(round(x0, 5), round(y0, 5), round(z0, 5)),
                                 (round(tip_x, 5), round(tip_y, 5), round(tip_z, 5))]
                elif is_lash:
                    side = 1.0 if i % 2 == 0 else -1.0
                    sub_u = (i // 2) / max(1, (count // 2) - 1)
                    x0 = side * (0.019 + 0.026 * sub_u) * s
                    y0 = (-0.128 - 0.003 * math.sin(sub_u * math.pi)) * s
                    z0 = (1.520 + 0.002 * math.sin(sub_u * math.pi)) * s
                    tip_x = x0 + side * 0.003 * s
                    tip_y = y0 - 0.004 * s
                    tip_z = z0 + 0.002 * s
                    curve_pts = [(round(x0, 5), round(y0, 5), round(z0, 5)),
                                 (round(tip_x, 5), round(tip_y, 5), round(tip_z, 5))]
                else:
                    ang = math.pi * (0.85 + 1.30 * u)
                    r_cx = 0.090 * s
                    r_cy = 0.092 * s
                    x0 = r_cx * math.cos(ang)
                    y0 = r_cy * math.sin(ang) + 0.005 * s
                    z0 = z_crown + 0.005 * s
                    tip_x = x0 * 1.01
                    tip_y = y0 * 1.01
                    tip_z = z0 - 0.025 * s
                    curve_pts = [(round(x0, 5), round(y0, 5), round(z0, 5)),
                                 (round(tip_x, 5), round(tip_y, 5), round(tip_z, 5))]

                radii = [layer_cfg.root_radius, layer_cfg.tip_radius]
                length = _calc_spline_length(curve_pts)
                layer_splines.append(HairCurveSpline(curve_pts, radii, layer_name, length))

        splines_by_layer[layer_name] = layer_splines

    return splines_by_layer


def generate_6_stratum_hime_cut_splines(
    height: float = 1.65,
    sample_density_scale: float = 0.10,
) -> Dict[str, List[HairCurveSpline]]:
    """Generates 3D splines for the authentic 6 cranial hairstyle strata."""
    cfg = HairGroomConfig(hair_style="hime_cut_6_strata")
    cfg.layers = get_6_stratum_hime_cut_layers(cfg.total_strand_count)
    return generate_hime_cut_splines(
        config=cfg,
        height=height,
        sample_density_scale=sample_density_scale,
    )

