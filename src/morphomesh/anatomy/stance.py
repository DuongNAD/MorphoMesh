"""
MorphoMesh Anatomy: Locomotor Stance Classifier & Morphology Analysis.

Automatically classifies vertebrate locomotor stance archetypes:
- Humanoid (erect biped)
- Plantigrade (sole-walker, bear/human/badger)
- Digitigrade (digit-walker, canine/feline/wolf)
- Unguligrade (hoof-walker, equine/bovine/cervid)

Uses biomechanical indicators:
- Relative hock height (eta_hock)
- Ground contact clustering & footprint aspect ratio (lambda_contact)
- Contact area ratio (sigma_contact)
- Metapodial segment inclination angle
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np


class LocomotorStance(str, Enum):
    """Vertebrate locomotor stance archetypes."""
    HUMANOID = "humanoid"
    PLANTIGRADE = "plantigrade"
    DIGITIGRADE = "digitigrade"
    UNGULIGRADE = "unguligrade"


@dataclass
class StanceClassificationResult:
    """Detailed result of locomotor stance classification."""
    stance: LocomotorStance
    confidence: float
    is_biped: bool
    ground_contact_count: int
    hock_height_ratio: float
    contact_area_ratio: float
    contact_aspect_ratio: float
    metapodial_angle_deg: float
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stance": self.stance.value,
            "confidence": round(self.confidence, 4),
            "is_biped": self.is_biped,
            "ground_contact_count": self.ground_contact_count,
            "hock_height_ratio": round(self.hock_height_ratio, 4),
            "contact_area_ratio": round(self.contact_area_ratio, 6),
            "contact_aspect_ratio": round(self.contact_aspect_ratio, 4),
            "metapodial_angle_deg": round(self.metapodial_angle_deg, 2),
            "diagnostics": self.diagnostics,
        }


def _extract_vertices_array(vertices: Any) -> np.ndarray:
    """Normalize input vertices into an (N, 3) float64 numpy array."""
    if hasattr(vertices, "vertices"):
        vertices = vertices.vertices
    arr = np.asarray(vertices, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"Expected vertices shape (N, 3), got {arr.shape}")
    return arr


def _cluster_ground_points(points_2d: np.ndarray, cluster_radius: float) -> List[np.ndarray]:
    """Cluster 2D ground contact points into connected groups via distance threshold."""
    if len(points_2d) == 0:
        return []
    
    n = len(points_2d)
    visited = np.zeros(n, dtype=bool)
    clusters: List[np.ndarray] = []
    
    for i in range(n):
        if visited[i]:
            continue
        cluster_indices = [i]
        visited[i] = True
        queue = [i]
        
        while queue:
            curr = queue.pop()
            curr_pt = points_2d[curr]
            # Euclidean distance in 2D
            dists = np.linalg.norm(points_2d - curr_pt, axis=1)
            neighbors = np.where((dists <= cluster_radius) & (~visited))[0]
            for nb in neighbors:
                visited[nb] = True
                cluster_indices.append(int(nb))
                queue.append(int(nb))
        
        clusters.append(points_2d[cluster_indices])
    
    return clusters


def classify_locomotor_stance(
    vertices: Union[np.ndarray, List[Any], Any],
    faces: Optional[Union[np.ndarray, List[Any]]] = None,
    skeleton_joints: Optional[Dict[str, Any]] = None,
    species_hint: Optional[str] = None,
) -> StanceClassificationResult:
    """
    Classify the locomotor stance archetype of a character or creature mesh.
    
    Args:
        vertices: Mesh vertex positions (N, 3).
        faces: Optional mesh polygon faces (M, 3) or (M, 4).
        skeleton_joints: Optional mapping of joint names to 3D coordinates.
        species_hint: Optional string hint (e.g. "bear", "human", "canine", "horse").
        
    Returns:
        StanceClassificationResult with stance enum, confidence, and biomechanical metrics.
    """
    V = _extract_vertices_array(vertices)
    if len(V) < 4:
        # Trivial fallback
        return StanceClassificationResult(
            stance=LocomotorStance.HUMANOID,
            confidence=0.5,
            is_biped=True,
            ground_contact_count=0,
            hock_height_ratio=0.1,
            contact_area_ratio=0.01,
            contact_aspect_ratio=1.5,
            metapodial_angle_deg=10.0,
            diagnostics={"reason": "insufficient_vertices"},
        )

    # 1. Bounding Box & Ground Plane
    z_min = float(np.min(V[:, 2]))
    z_max = float(np.max(V[:, 2]))
    height = max(z_max - z_min, 1e-4)

    x_min = float(np.min(V[:, 0]))
    x_max = float(np.max(V[:, 0]))
    span_x = max(x_max - x_min, 1e-4)

    y_min = float(np.min(V[:, 1]))
    y_max = float(np.max(V[:, 1]))
    span_y = max(y_max - y_min, 1e-4)

    vertical_aspect = height / max(span_x, span_y)

    # Ground contact threshold: bottom 4% of total height
    ground_thresh = z_min + 0.04 * height
    ground_mask = V[:, 2] <= ground_thresh
    ground_pts = V[ground_mask]

    if len(ground_pts) < 3:
        # Fallback to bottom 8% if mesh has sparse feet
        ground_thresh = z_min + 0.08 * height
        ground_mask = V[:, 2] <= ground_thresh
        ground_pts = V[ground_mask]

    # Cluster ground contact points in XY plane
    pts_xy = ground_pts[:, :2] if len(ground_pts) > 0 else np.empty((0, 2))
    cluster_radius = max(0.035 * height, 0.03 * max(span_x, span_y))
    clusters = _cluster_ground_points(pts_xy, cluster_radius)
    contact_count = len(clusters)

    # Compute contact footprint metrics
    total_contact_area = 0.0
    aspect_ratios = []
    
    for c in clusters:
        if len(c) < 2:
            continue
        c_xmin, c_xmax = float(np.min(c[:, 0])), float(np.max(c[:, 0]))
        c_ymin, c_ymax = float(np.min(c[:, 1])), float(np.max(c[:, 1]))
        w_x = max(c_xmax - c_xmin, 1e-4)
        l_y = max(c_ymax - c_ymin, 1e-4)
        # In animal locomotion, AP length / ML width defines sole elongation
        aspect = max(l_y / w_x, w_x / l_y)
        aspect_ratios.append(aspect)
        total_contact_area += w_x * l_y

    mean_aspect = float(np.mean(aspect_ratios)) if aspect_ratios else 1.0
    contact_area_ratio = total_contact_area / (height * height)

    # 2. Hock Height Ratio & Metapodial Angle Estimation
    # Default initializations
    eta_hock = 0.20
    metapodial_angle = 20.0

    if skeleton_joints is not None and len(skeleton_joints) > 0:
        # Extract joints by canonical names
        def find_joint_z(*names: str) -> Optional[float]:
            for name in names:
                for k, v in skeleton_joints.items():
                    if name in k.lower():
                        if isinstance(v, (list, tuple, np.ndarray)) and len(v) >= 3:
                            return float(v[2])
            return None

        z_hock_val = find_joint_z("hock", "ankle", "tarsus", "calcaneus")
        z_hip_val = find_joint_z("hip", "pelvis", "thigh")
        z_toe_val = find_joint_z("foot", "toe", "hoof", "paw")

        if z_hock_val is not None and z_hip_val is not None:
            hip_elev = max(z_hip_val - z_min, 1e-4)
            eta_hock = max(0.0, min(1.0, (z_hock_val - z_min) / hip_elev))

        # Estimate metapodial angle from hock and toe
        if z_hock_val is not None and z_toe_val is not None:
            dh = abs(z_hock_val - z_toe_val)
            # Find horizontal distance if full joint positions known
            metapodial_angle = math.degrees(math.asin(max(-1.0, min(1.0, dh / max(0.2 * height, 1e-4)))))
    else:
        # Estimate from mesh geometry
        # For quadrupeds: hindlimb profile in the bottom 45% of height
        hind_mask = (V[:, 2] >= z_min) & (V[:, 2] <= z_min + 0.50 * height)
        # Hind quarters have higher/lower Y depending on orientation
        mid_y = 0.5 * (y_min + y_max)
        hind_pts = V[hind_mask & (V[:, 1] > mid_y)]
        if len(hind_pts) < 10:
            hind_pts = V[hind_mask & (V[:, 1] < mid_y)]
        
        if len(hind_pts) >= 10:
            # Measure local AP protrusion or minimum width along Z bins
            z_bins = np.linspace(z_min, z_min + 0.45 * height, 15)
            bin_widths = []
            for b_idx in range(len(z_bins) - 1):
                b_mask = (hind_pts[:, 2] >= z_bins[b_idx]) & (hind_pts[:, 2] < z_bins[b_idx + 1])
                if np.sum(b_mask) >= 3:
                    sub = hind_pts[b_mask]
                    span_ap = np.max(sub[:, 1]) - np.min(sub[:, 1])
                    bin_widths.append((0.5 * (z_bins[b_idx] + z_bins[b_idx + 1]), span_ap))
            
            if bin_widths:
                # Hock corresponds to prominent posterior peak or constriction
                max_w_z = max(bin_widths, key=lambda x: x[1])[0]
                eta_hock = (max_w_z - z_min) / (0.50 * height)
                eta_hock = max(0.10, min(0.70, eta_hock))

    # Infer metapodial angle from eta_hock if not explicitly calculated
    if metapodial_angle == 20.0 and eta_hock > 0.1:
        # eta_hock ~ 0.15 -> 10 deg (plantigrade)
        # eta_hock ~ 0.35 -> 50 deg (digitigrade)
        # eta_hock ~ 0.60 -> 80 deg (unguligrade)
        metapodial_angle = float(np.clip(10.0 + (eta_hock - 0.15) * 155.0, 5.0, 88.0))

    # 3. Decision Logic & Scoring
    species_lower = species_hint.lower() if species_hint else ""
    is_human_hint = any(s in species_lower for s in ["human", "humanoid", "person", "biped"])
    is_bear_hint = any(s in species_lower for s in ["bear", "ursine", "panda"])
    is_canine_hint = any(s in species_lower for s in ["dog", "canine", "wolf", "fox", "cat", "feline"])
    is_ungulate_hint = any(s in species_lower for s in ["horse", "equine", "deer", "cow", "cattle", "goat", "sheep", "pig"])

    diagnostics = {
        "vertical_aspect": round(vertical_aspect, 3),
        "cluster_count": contact_count,
        "raw_eta_hock": round(eta_hock, 4),
        "contact_area_ratio": round(contact_area_ratio, 6),
        "mean_aspect": round(mean_aspect, 3),
        "metapodial_angle": round(metapodial_angle, 2),
        "species_hint": species_hint,
    }

    # Case A: Humanoid Biped
    if is_human_hint or (vertical_aspect >= 1.40 and contact_count <= 2) or (contact_count == 2 and vertical_aspect >= 1.25):
        conf = 0.98 if is_human_hint else 0.92
        return StanceClassificationResult(
            stance=LocomotorStance.HUMANOID,
            confidence=conf,
            is_biped=True,
            ground_contact_count=contact_count,
            hock_height_ratio=eta_hock,
            contact_area_ratio=contact_area_ratio,
            contact_aspect_ratio=mean_aspect,
            metapodial_angle_deg=metapodial_angle,
            diagnostics=diagnostics,
        )

    # Case B: Quadruped Stances
    # Evaluate scores for Plantigrade, Digitigrade, Unguligrade
    scores: Dict[LocomotorStance, float] = {
        LocomotorStance.PLANTIGRADE: 0.0,
        LocomotorStance.DIGITIGRADE: 0.0,
        LocomotorStance.UNGULIGRADE: 0.0,
    }

    # Plantigrade indicators: low hock, high contact area, elongated footprint
    if eta_hock <= 0.23:
        scores[LocomotorStance.PLANTIGRADE] += 0.40
    elif eta_hock <= 0.28:
        scores[LocomotorStance.PLANTIGRADE] += 0.20
    
    if contact_area_ratio >= 0.008:
        scores[LocomotorStance.PLANTIGRADE] += 0.30
    if mean_aspect >= 1.25:
        scores[LocomotorStance.PLANTIGRADE] += 0.30
    if metapodial_angle < 30.0:
        scores[LocomotorStance.PLANTIGRADE] += 0.20

    # Digitigrade indicators: medium hock, moderate contact area, medium metapodial angle
    if 0.22 < eta_hock <= 0.48:
        scores[LocomotorStance.DIGITIGRADE] += 0.50
    if 0.0001 <= contact_area_ratio < 0.012:
        scores[LocomotorStance.DIGITIGRADE] += 0.30
    if 30.0 <= metapodial_angle <= 70.0:
        scores[LocomotorStance.DIGITIGRADE] += 0.35

    # Unguligrade indicators: high hock, tiny contact footprint (hooves), near-vertical metapodial
    if eta_hock > 0.48:
        scores[LocomotorStance.UNGULIGRADE] += 0.55
    elif eta_hock > 0.40:
        scores[LocomotorStance.UNGULIGRADE] += 0.25
    if contact_area_ratio < 0.0035:
        scores[LocomotorStance.UNGULIGRADE] += 0.35
    if metapodial_angle >= 65.0:
        scores[LocomotorStance.UNGULIGRADE] += 0.35

    # Decisive species hint bonus
    if is_bear_hint:
        scores[LocomotorStance.PLANTIGRADE] += 1.50
    elif is_canine_hint:
        scores[LocomotorStance.DIGITIGRADE] += 1.50
    elif is_ungulate_hint:
        scores[LocomotorStance.UNGULIGRADE] += 1.50

    best_stance = max(scores.items(), key=lambda x: x[1])[0]
    total_score = sum(scores.values()) + 1e-6
    best_score = scores[best_stance]
    confidence = float(np.clip(best_score / total_score + 0.35, 0.85, 0.98))

    return StanceClassificationResult(
        stance=best_stance,
        confidence=confidence,
        is_biped=False,
        ground_contact_count=contact_count,
        hock_height_ratio=eta_hock,
        contact_area_ratio=contact_area_ratio,
        contact_aspect_ratio=mean_aspect,
        metapodial_angle_deg=metapodial_angle,
        diagnostics=diagnostics,
    )
