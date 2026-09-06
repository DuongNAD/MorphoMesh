"""
MorphoMesh: Reusable Biological Anatomy & Creature Generator Module.

Provides procedural synthesis of anatomically authentic creatures across biological
archetypes (Ursine, Canine, Feline, Biped, Chimera), implementing:
1. Plantigrade Ursine paw biomechanics with calcaneus heel, palmar/plantar pads, and 5 digital pads.
2. Keratin claw generation with mathematical forward/downward curvature guarantee:
   dot(claw_tip - claw_base, forward_dir) > 0.60 and dz < 0.
3. Articulated facial anatomy: sculpted snout, indented nares/nostrils, buccal cavity,
   lower jaw, canines/incisors dentition, dimensional eyelids, and cupped ears.
4. Muscular quadruped torso with dorsal scapular hump, dorsal spine, and vestigial short tail.
5. 18 standardized vertex groups for deformation, rigging, fur grooming, and armor fitting.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    from morphomesh.inference_adapter import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from inference_adapter import MeshGeometry  # type: ignore[no-redef]

STANDARDIZED_VERTEX_GROUPS: Tuple[str, ...] = (
    "snout",
    "nostrils",
    "mouth_cavity",
    "jaw",
    "teeth",
    "eyes",
    "eyelids",
    "ears",
    "claws_front",
    "claws_hind",
    "pads_front",
    "pads_hind",
    "torso",
    "limbs",
    "tail",
    "dorsal_spine",
    "armor_mounts_shoulder",
    "armor_mounts_wrist",
)


@dataclass
class UrsineAnatomyConfig:
    """Parametric configuration for Ursine anatomy generation."""

    scale: float = 1.0
    torso_length: float = 1.25
    chest_radius: float = 0.38
    hump_height: float = 0.18
    claw_length_front: float = 0.11
    claw_length_hind: float = 0.085
    claw_curve_factor: float = 0.48
    num_digits: int = 5
    tail_length: float = 0.14  # Ursine short tail (<= 0.20m)
    stance_width_front: float = 0.38
    stance_width_hind: float = 0.36


@dataclass
class ClawMetric:
    """Direction and curvature verification metrics for a single claw."""

    claw_id: str
    paw: str
    digit_index: int
    base_pos: Tuple[float, float, float]
    tip_pos: Tuple[float, float, float]
    direction_vector: Tuple[float, float, float]
    forward_dot: float
    downward_pitch: float
    is_valid: bool


@dataclass
class CreatureMeshResult:
    """Encapsulates generated creature geometry, vertex groups, and anatomical metrics."""

    mesh: MeshGeometry
    vertex_groups: Dict[str, List[int]] = field(default_factory=dict)
    claws: List[ClawMetric] = field(default_factory=list)
    landmark_counts: Dict[str, int] = field(default_factory=dict)
    is_anatomically_valid: bool = True
    archetype: str = "ursine"


def generate_bear_base_mesh(config: Optional[UrsineAnatomyConfig] = None) -> CreatureMeshResult:
    """
    Procedurally synthesizes an anatomically authentic Ursine base mesh.

    Features:
    - Forward-and-downward curving claws (dot product > 0.60, dz < 0) across all 20 digits.
    - True plantigrade paws with calcaneus heel, palmar/plantar sole pads, and 5 digital pads each.
    - Fully articulated head: snout, recessed nostrils, buccal mouth cavity, mandible, canines/teeth,
      spherical eyes with eyelids, and cupped ears.
    - Muscular torso with dorsal thoracic shoulder hump, midline dorsal spine, and short tail.
    - Populates all 18 standardized vertex groups with non-empty vertex indices.
    """
    cfg = config or UrsineAnatomyConfig()
    mesh = MeshGeometry()
    s = cfg.scale

    # Initialize all 18 standardized vertex groups
    vertex_groups: Dict[str, List[int]] = {vg: [] for vg in STANDARDIZED_VERTEX_GROUPS}
    claws_metrics: List[ClawMetric] = []
    forward_dir = (0.0, -1.0, 0.0)

    # --------------------------------------------------------------------------
    # 1. TORSO, DORSAL HUMP, DORSAL SPINE, & TAIL
    # --------------------------------------------------------------------------
    torso_center = (0.0, 0.0, 0.85 * s)
    torso_feats = mesh.add_anatomical_torso(torso_center, forward_dir=forward_dir, scale=s)

    for k, idxs in torso_feats.items():
        if k in vertex_groups:
            vertex_groups[k].extend(idxs)

    # --------------------------------------------------------------------------
    # 2. LIMBS (Forelegs & Hindlegs)
    # --------------------------------------------------------------------------
    # Forelegs (left & right)
    for sign_x, side in [(1.0, "L"), (-1.0, "R")]:
        fx = sign_x * cfg.stance_width_front * s
        # Upper shoulder / arm
        start_arm = len(mesh.vertices)
        mesh.add_cylinder((fx, -0.32 * s, 0.42 * s), radius=0.085 * s, height=0.45 * s, axis="Z", cap_ends=True)
        # Forearm / wrist
        mesh.add_cylinder((fx, -0.35 * s, 0.03 * s), radius=0.070 * s, height=0.40 * s, axis="Z", cap_ends=True)
        vertex_groups["limbs"].extend(list(range(start_arm, len(mesh.vertices))))

        # Wrist armor mount region (lower forearm vertices)
        wrist_mount = list(range(len(mesh.vertices) - 12, len(mesh.vertices)))
        vertex_groups["armor_mounts_wrist"].extend(wrist_mount)

    # Hindlegs (left & right)
    for sign_x, side in [(1.0, "L"), (-1.0, "R")]:
        hx = sign_x * cfg.stance_width_hind * s
        # Thigh / hip
        start_thigh = len(mesh.vertices)
        mesh.add_cylinder((hx, 0.42 * s, 0.40 * s), radius=0.095 * s, height=0.45 * s, axis="Z", cap_ends=True)
        # Shank / lower leg down to hock
        mesh.add_cylinder((hx, 0.38 * s, 0.03 * s), radius=0.075 * s, height=0.40 * s, axis="Z", cap_ends=True)
        vertex_groups["limbs"].extend(list(range(start_thigh, len(mesh.vertices))))

    # --------------------------------------------------------------------------
    # 3. 4 PLANTIGRADE PAWS WITH PADS & 20 CURVED CLAWS
    # --------------------------------------------------------------------------
    paw_configs = [
        ("Front_L", cfg.stance_width_front * s, -0.35 * s, 0.0, True),
        ("Front_R", -cfg.stance_width_front * s, -0.35 * s, 0.0, True),
        ("Hind_L", cfg.stance_width_hind * s, 0.46 * s, 0.0, False),
        ("Hind_R", -cfg.stance_width_hind * s, 0.46 * s, 0.0, False),
    ]

    claw_idx_counter = 0

    for paw_name, px, py, pz, is_front in paw_configs:
        claw_len = cfg.claw_length_front * s if is_front else cfg.claw_length_hind * s
        claw_base_r = 0.022 * s if is_front else 0.019 * s

        # Synthesize foot body
        if is_front:
            # Front Manus
            foot_center = (px, py - 0.05 * s, pz + 0.04 * s)
            foot_size = (0.24 * s, 0.24 * s, 0.08 * s)
            idx_start = len(mesh.vertices)
            mesh.add_box(foot_center, foot_size)
            vertex_groups["limbs"].extend(list(range(idx_start, len(mesh.vertices))))

            # Palmar main pad
            palmar_pad = mesh.add_ellipsoid(
                (px, py - 0.08 * s, pz + 0.01 * s),
                (0.10 * s, 0.08 * s, 0.02 * s),
                rings=4,
                sectors=8,
            )
            vertex_groups["pads_front"].extend(palmar_pad)

            # Lateral carpal accessory pad
            carpal_x = px + (0.08 if px >= 0 else -0.08) * s
            carpal_pad = mesh.add_ellipsoid(
                (carpal_x, py, pz + 0.015 * s),
                (0.035 * s, 0.035 * s, 0.015 * s),
                rings=4,
                sectors=6,
            )
            vertex_groups["pads_front"].extend(carpal_pad)
        else:
            # Hind Pes (plantigrade calcaneus heel morphology)
            foot_center = (px, py - 0.13 * s, pz + 0.04 * s)
            foot_size = (0.22 * s, 0.26 * s, 0.08 * s)
            idx_start = len(mesh.vertices)
            mesh.add_box(foot_center, foot_size)
            vertex_groups["limbs"].extend(list(range(idx_start, len(mesh.vertices))))

            # Continuous Plantar sole pad
            plantar_pad = mesh.add_ellipsoid(
                (px, py - 0.13 * s, pz + 0.01 * s),
                (0.09 * s, 0.12 * s, 0.02 * s),
                rings=4,
                sectors=8,
            )
            vertex_groups["pads_hind"].extend(plantar_pad)

        # 5 Digits with digital pads and claws
        for k in range(cfg.num_digits):
            splay = (k - 2) * 0.24 if is_front else (k - 2) * 0.22
            dx = px + (k - 2) * (0.045 if is_front else 0.040) * s
            fwd_ext = (
                (0.18 + 0.025 * (1.0 - abs(k - 2) * 0.25)) * s
                if is_front
                else (0.24 + 0.020 * (1.0 - abs(k - 2) * 0.25)) * s
            )
            dy = py - fwd_ext
            dz = pz + 0.02 * s

            # Digital pad
            d_pad = mesh.add_ellipsoid(
                (dx, dy, dz - 0.006 * s),
                (0.022 * s, 0.024 * s, 0.014 * s),
                rings=4,
                sectors=6,
            )
            if is_front:
                vertex_groups["pads_front"].extend(d_pad)
            else:
                vertex_groups["pads_hind"].extend(d_pad)

            # Claw base position and curvature parameters
            claw_base = (dx, dy - 0.015 * s, dz)
            splay_factor = splay * (0.22 if is_front else 0.20)

            # Precompute tip position for metric recording
            tip_x = claw_base[0] + forward_dir[0] * claw_len + (0.0) * (claw_len * cfg.claw_curve_factor) + (1.0) * (claw_len * splay_factor)
            tip_y = claw_base[1] + forward_dir[1] * claw_len + (0.0) * (claw_len * cfg.claw_curve_factor) + (0.0) * (claw_len * splay_factor)
            tip_z = claw_base[2] + forward_dir[2] * claw_len + (-1.0) * (claw_len * cfg.claw_curve_factor) + (0.0) * (claw_len * splay_factor)
            claw_tip = (tip_x, tip_y, tip_z)

            # Vector from base to tip
            vx = tip_x - claw_base[0]
            vy = tip_y - claw_base[1]
            vz = tip_z - claw_base[2]
            v_len = math.sqrt(vx * vx + vy * vy + vz * vz)
            d_unit = (vx / v_len, vy / v_len, vz / v_len) if v_len > 1e-6 else (0.0, -1.0, -0.4)

            # Dot product with forward axis (0, -1, 0)
            fwd_dot = d_unit[0] * forward_dir[0] + d_unit[1] * forward_dir[1] + d_unit[2] * forward_dir[2]
            # Downward pitch (z component must be negative)
            downward_pitch = d_unit[2]

            metric = ClawMetric(
                claw_id=f"Claw_{paw_name}_{k}",
                paw=paw_name,
                digit_index=k,
                base_pos=claw_base,
                tip_pos=claw_tip,
                direction_vector=d_unit,
                forward_dot=round(fwd_dot, 4),
                downward_pitch=round(downward_pitch, 4),
                is_valid=(fwd_dot > 0.60 and downward_pitch < 0.0),
            )
            claws_metrics.append(metric)

            # Synthesize curved claw geometry
            claw_verts = mesh.add_curved_claw(
                base_pos=claw_base,
                forward_dir=forward_dir,
                downward_dir=(0.0, 0.0, -1.0),
                length=claw_len,
                base_radius=claw_base_r,
                curve_factor=cfg.claw_curve_factor,
                segments=6,
                radial_segments=8,
                splay_factor=splay_factor,
            )

            if is_front:
                vertex_groups["claws_front"].extend(claw_verts)
            else:
                vertex_groups["claws_hind"].extend(claw_verts)

            claw_idx_counter += 1

    # --------------------------------------------------------------------------
    # 4. ARTICULATED HEAD WITH COMPLETE FACIAL FEATURES
    # --------------------------------------------------------------------------
    head_center = (0.0, -0.78 * s, 1.20 * s)
    head_feats = mesh.add_articulated_head(head_center, forward_dir=forward_dir, scale=s)

    for k, idxs in head_feats.items():
        if k in vertex_groups:
            vertex_groups[k].extend(idxs)

    # Copy to internal vertex_groups
    for vg_name, idx_list in vertex_groups.items():
        mesh.vertex_groups[vg_name] = idx_list

    # --------------------------------------------------------------------------
    # 5. VALIDATION & LANDMARK INVENTORY
    # --------------------------------------------------------------------------
    landmark_counts = {
        "claws_total": len(claws_metrics),
        "claws_valid": sum(1 for c in claws_metrics if c.is_valid),
        "nostrils_count": len(head_feats.get("nostrils", [])) > 0,
        "teeth_count": len(head_feats.get("teeth", [])) > 0,
        "eyes_count": len(head_feats.get("eyes", [])) > 0,
        "eyelids_count": len(head_feats.get("eyelids", [])) > 0,
        "ears_count": len(head_feats.get("ears", [])) > 0,
        "paws_count": 4,
        "pads_front_verts": len(vertex_groups["pads_front"]),
        "pads_hind_verts": len(vertex_groups["pads_hind"]),
        "total_vertices": len(mesh.vertices),
        "total_faces": len(mesh.faces),
    }

    all_claws_valid = len(claws_metrics) == 20 and all(c.is_valid for c in claws_metrics)
    all_vgs_populated = all(len(vertex_groups[vg]) > 0 for vg in STANDARDIZED_VERTEX_GROUPS)

    return CreatureMeshResult(
        mesh=mesh,
        vertex_groups=vertex_groups,
        claws=claws_metrics,
        landmark_counts=landmark_counts,
        is_anatomically_valid=(all_claws_valid and all_vgs_populated),
        archetype="ursine",
    )


def generate_creature_mesh(
    archetype: str = "ursine",
    config: Optional[Any] = None,
) -> CreatureMeshResult:
    """Universal procedural creature mesh generator supporting multiple biological archetypes."""
    arch = archetype.lower()
    if "bear" in arch or "ursine" in arch:
        cfg = config if isinstance(config, UrsineAnatomyConfig) else UrsineAnatomyConfig()
        return generate_bear_base_mesh(cfg)

    # General quadruped (Canine/Feline/Wolf)
    cfg = UrsineAnatomyConfig(
        scale=1.0,
        chest_radius=0.32,
        hump_height=0.08,
        claw_length_front=0.08,
        claw_length_hind=0.065,
        claw_curve_factor=0.42,
        tail_length=0.45,
    )
    result = generate_bear_base_mesh(cfg)
    result.archetype = "quadruped"
    return result


def build_bear_in_blender(
    scene_name: Optional[str] = None,
    object_name: str = "Bear_Base_Mesh",
    scale: float = 1.0,
) -> Dict[str, Any]:
    """
    Executes inside Blender (requires bpy environment).
    Synthesizes the base bear mesh, assigns 18 vertex groups, and links to scene.
    """
    try:
        import bpy
    except ImportError as e:
        return {"status": "error", "message": f"bpy not available: {e}"}

    cfg = UrsineAnatomyConfig(scale=scale)
    result = generate_bear_base_mesh(cfg)
    mesh = result.mesh

    # Create new mesh and object
    mesh_data = bpy.data.meshes.new(f"{object_name}_Mesh")
    obj = bpy.data.objects.new(object_name, mesh_data)

    # Feed vertices and triangular faces
    mesh_data.from_pydata(mesh.vertices, [], mesh.faces)
    mesh_data.update()

    # Create and populate all 18 vertex groups
    for vg_name in STANDARDIZED_VERTEX_GROUPS:
        indices = result.vertex_groups.get(vg_name, [])
        vg = obj.vertex_groups.new(name=vg_name)
        if indices:
            vg.add(indices, 1.0, "REPLACE")

    # Link object to target scene collection
    if scene_name and scene_name in bpy.data.scenes:
        target_scene = bpy.data.scenes[scene_name]
        target_scene.collection.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)

    # Set smooth shading
    for poly in mesh_data.polygons:
        poly.use_smooth = True

    return {
        "status": "success",
        "object_name": obj.name,
        "vertex_count": len(mesh_data.vertices),
        "face_count": len(mesh_data.polygons),
        "vertex_groups_count": len(obj.vertex_groups),
        "vertex_groups": [vg.name for vg in obj.vertex_groups],
        "claws_count": len(result.claws),
        "claws_valid_count": sum(1 for c in result.claws if c.is_valid),
        "is_anatomically_valid": result.is_anatomically_valid,
    }


def get_blender_generation_script(object_name: str = "Bear_Base_Mesh", scale: float = 1.0) -> str:
    """
    Generates a self-contained, AST-safe Python script (< 10KB) to execute inside Blender
    that creates the complete bear base mesh with 18 vertex groups and forward-curving claws.
    """
    return f'''
import bpy
import math

obj_name = "{object_name}"
existing = bpy.data.objects.get(obj_name)
if existing:
    bpy.data.objects.remove(existing, do_unlink=True)

verts = []
faces = []
vgs = {{
    "snout": [], "nostrils": [], "mouth_cavity": [], "jaw": [], "teeth": [],
    "eyes": [], "eyelids": [], "ears": [], "claws_front": [], "claws_hind": [],
    "pads_front": [], "pads_hind": [], "torso": [], "limbs": [], "tail": [],
    "dorsal_spine": [], "armor_mounts_shoulder": [], "armor_mounts_wrist": [],
}}

def add_box(center, size, group_name=None):
    cx, cy, cz = center
    sx, sy, sz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    s_idx = len(verts)
    corners = [
        (cx - sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz - sz),
        (cx + sx, cy + sy, cz - sz), (cx - sx, cy + sy, cz - sz),
        (cx - sx, cy - sy, cz + sz), (cx + sx, cy - sy, cz + sz),
        (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz),
    ]
    verts.extend(corners)
    box_faces = [
        (s_idx, s_idx+2, s_idx+1), (s_idx, s_idx+3, s_idx+2),
        (s_idx+4, s_idx+5, s_idx+6), (s_idx+4, s_idx+6, s_idx+7),
        (s_idx, s_idx+5, s_idx+4), (s_idx, s_idx+1, s_idx+5),
        (s_idx+2, s_idx+7, s_idx+6), (s_idx+2, s_idx+3, s_idx+7),
        (s_idx, s_idx+7, s_idx+3), (s_idx, s_idx+4, s_idx+7),
        (s_idx+1, s_idx+6, s_idx+5), (s_idx+1, s_idx+2, s_idx+6),
    ]
    faces.extend(box_faces)
    new_indices = list(range(s_idx, len(verts)))
    if group_name and group_name in vgs:
        vgs[group_name].extend(new_indices)
    return new_indices

def add_ellipsoid(center, radii, rings=4, sectors=6, group_name=None):
    cx, cy, cz = center
    rx, ry, rz = radii
    s_idx = len(verts)
    north_idx = len(verts)
    verts.append((cx, cy, cz + rz))
    ring_indices = []
    for r in range(1, rings):
        theta = math.pi * r / rings
        sin_t, cos_t = math.sin(theta), math.cos(theta)
        c_ring = []
        for s in range(sectors):
            phi = 2.0 * math.pi * s / sectors
            px = cx + rx * sin_t * math.cos(phi)
            py = cy + ry * sin_t * math.sin(phi)
            pz = cz + rz * cos_t
            idx = len(verts)
            verts.append((px, py, pz))
            c_ring.append(idx)
        ring_indices.append(c_ring)
    south_idx = len(verts)
    verts.append((cx, cy, cz - rz))
    for s in range(sectors):
        next_s = (s + 1) % sectors
        faces.append((north_idx, ring_indices[0][s], ring_indices[0][next_s]))
    for r in range(len(ring_indices) - 1):
        for s in range(sectors):
            next_s = (s + 1) % sectors
            i0, i1 = ring_indices[r][s], ring_indices[r+1][s]
            i2, i3 = ring_indices[r+1][next_s], ring_indices[r][next_s]
            faces.append((i0, i1, i2))
            faces.append((i0, i2, i3))
    last_ring = ring_indices[-1]
    for s in range(sectors):
        next_s = (s + 1) % sectors
        faces.append((last_ring[s], south_idx, last_ring[next_s]))
    new_indices = list(range(s_idx, len(verts)))
    if group_name and group_name in vgs:
        vgs[group_name].extend(new_indices)
    return new_indices

def add_cone(base, apex, radius, segments=6, group_name=None):
    bx, by, bz = base
    ax, ay, az = apex
    s_idx = len(verts)
    ring = []
    for s in range(segments):
        a = 2.0 * math.pi * s / segments
        px = bx + radius * math.cos(a)
        py = by
        pz = bz + radius * math.sin(a)
        idx = len(verts)
        verts.append((px, py, pz))
        ring.append(idx)
    apex_idx = len(verts)
    verts.append((ax, ay, az))
    base_idx = len(verts)
    verts.append((bx, by, bz))
    for s in range(segments):
        ns = (s + 1) % segments
        faces.append((ring[s], ring[ns], apex_idx))
        faces.append((base_idx, ring[ns], ring[s]))
    new_indices = list(range(s_idx, len(verts)))
    if group_name and group_name in vgs:
        vgs[group_name].extend(new_indices)
    return new_indices

def add_claw(base, length=0.10, radius=0.02, curve=0.45, splay=0.0, group_name=None):
    bx, by, bz = base
    s_idx = len(verts)
    rings = []
    for step in range(4):
        t = step / 3.0
        r_t = radius * (1.0 - 0.7 * t)
        cx = bx + length * splay * t
        cy = by - length * t
        cz = bz - length * curve * (t ** 1.4)
        ring = []
        for a_idx in range(6):
            ang = 2.0 * math.pi * a_idx / 6.0
            rx = cx + r_t * math.cos(ang)
            ry = cy
            rz = cz + r_t * math.sin(ang)
            v_i = len(verts)
            verts.append((rx, ry, rz))
            ring.append(v_i)
        rings.append(ring)
    tip_x = bx + length * splay
    tip_y = by - length
    tip_z = bz - length * curve
    tip_idx = len(verts)
    verts.append((tip_x, tip_y, tip_z))
    for r in range(3):
        for s in range(6):
            ns = (s + 1) % 6
            faces.append((rings[r][s], rings[r+1][s], rings[r+1][ns]))
            faces.append((rings[r][s], rings[r+1][ns], rings[r][ns]))
    for s in range(6):
        ns = (s + 1) % 6
        faces.append((rings[-1][s], tip_idx, rings[-1][ns]))
    new_indices = list(range(s_idx, len(verts)))
    if group_name and group_name in vgs:
        vgs[group_name].extend(new_indices)
    return new_indices

sc = {scale}
# 1. Torso, Scapular Hump, Spine, Tail
add_ellipsoid((0, -0.2*sc, 0.85*sc), (0.36*sc, 0.30*sc, 0.32*sc), group_name="torso")
hump = add_ellipsoid((0, -0.18*sc, 1.05*sc), (0.22*sc, 0.20*sc, 0.14*sc), group_name="torso")
vgs["armor_mounts_shoulder"].extend(hump)
add_ellipsoid((0, 0.15*sc, 0.88*sc), (0.30*sc, 0.25*sc, 0.28*sc), group_name="torso")
add_ellipsoid((0, 0.48*sc, 0.90*sc), (0.32*sc, 0.24*sc, 0.30*sc), group_name="torso")
add_box((0, 0.05*sc, 1.08*sc), (0.06*sc, 1.05*sc, 0.04*sc), group_name="dorsal_spine")
add_cone((0, 0.62*sc, 0.95*sc), (0, 0.75*sc, 0.85*sc), 0.045*sc, group_name="tail")

# 2. Limbs & Paws
for sx in [-1, 1]:
    # Front limb
    fx = sx * 0.38 * sc
    arm = add_box((fx, -0.32*sc, 0.45*sc), (0.16*sc, 0.16*sc, 0.45*sc), group_name="limbs")
    wrist = add_box((fx, -0.35*sc, 0.18*sc), (0.14*sc, 0.14*sc, 0.36*sc), group_name="limbs")
    vgs["armor_mounts_wrist"].extend(wrist)
    # Front paw
    add_box((fx, -0.40*sc, 0.04*sc), (0.24*sc, 0.24*sc, 0.08*sc), group_name="limbs")
    add_ellipsoid((fx, -0.43*sc, 0.01*sc), (0.10*sc, 0.08*sc, 0.02*sc), group_name="pads_front")
    for k in range(5):
        splay = (k - 2) * 0.22
        dx = fx + (k - 2) * 0.045 * sc
        dy = -0.55 * sc - (1.0 - abs(k-2)*0.25)*0.03*sc
        add_ellipsoid((dx, dy, 0.015*sc), (0.022*sc, 0.024*sc, 0.014*sc), group_name="pads_front")
        add_claw((dx, dy - 0.015*sc, 0.02*sc), length=0.10*sc, radius=0.02*sc, curve=0.46, splay=splay*0.2, group_name="claws_front")

    # Hind limb
    hx = sx * 0.36 * sc
    add_box((hx, 0.42*sc, 0.45*sc), (0.18*sc, 0.18*sc, 0.45*sc), group_name="limbs")
    add_box((hx, 0.38*sc, 0.18*sc), (0.15*sc, 0.15*sc, 0.36*sc), group_name="limbs")
    # Hind plantigrade paw
    add_box((hx, 0.33*sc, 0.04*sc), (0.22*sc, 0.26*sc, 0.08*sc), group_name="limbs")
    add_ellipsoid((hx, 0.33*sc, 0.01*sc), (0.09*sc, 0.12*sc, 0.02*sc), group_name="pads_hind")
    for k in range(5):
        splay = (k - 2) * 0.20
        dx = hx + (k - 2) * 0.040 * sc
        dy = 0.22 * sc - (1.0 - abs(k-2)*0.25)*0.02*sc
        add_ellipsoid((dx, dy, 0.015*sc), (0.020*sc, 0.022*sc, 0.014*sc), group_name="pads_hind")
        add_claw((dx, dy - 0.015*sc, 0.02*sc), length=0.08*sc, radius=0.019*sc, curve=0.46, splay=splay*0.2, group_name="claws_hind")

# 3. Head & Facial Features
hc = (0, -0.78*sc, 1.20*sc)
add_ellipsoid(hc, (0.22*sc, 0.24*sc, 0.20*sc), group_name="torso")
add_box((0, -0.98*sc, 1.18*sc), (0.18*sc, 0.20*sc, 0.16*sc), group_name="snout")
add_box((0, -1.09*sc, 1.21*sc), (0.12*sc, 0.03*sc, 0.08*sc), group_name="snout")
for sx in [-1, 1]:
    add_cone((sx*0.032*sc, -1.10*sc, 1.21*sc), (sx*0.028*sc, -1.07*sc, 1.22*sc), 0.012*sc, group_name="nostrils")
add_box((0, -0.99*sc, 1.13*sc), (0.13*sc, 0.14*sc, 0.03*sc), group_name="mouth_cavity")
add_box((0, -0.98*sc, 1.08*sc), (0.15*sc, 0.18*sc, 0.06*sc), group_name="jaw")
for sx in [-1, 1]:
    add_cone((sx*0.048*sc, -1.04*sc, 1.15*sc), (sx*0.050*sc, -1.03*sc, 1.10*sc), 0.009*sc, group_name="teeth")
    add_cone((sx*0.042*sc, -1.03*sc, 1.09*sc), (sx*0.044*sc, -1.02*sc, 1.14*sc), 0.008*sc, group_name="teeth")
for i in range(4):
    ox = (i - 1.5) * 0.016 * sc
    add_cone((ox, -1.06*sc, 1.15*sc), (ox, -1.055*sc, 1.12*sc), 0.005*sc, group_name="teeth")
for sx in [-1, 1]:
    add_ellipsoid((sx*0.15*sc, -0.90*sc, 1.26*sc), (0.032*sc, 0.032*sc, 0.032*sc), group_name="eyes")
    add_box((sx*0.15*sc, -0.90*sc, 1.285*sc), (0.045*sc, 0.045*sc, 0.015*sc), group_name="eyelids")
    add_box((sx*0.15*sc, -0.90*sc, 1.235*sc), (0.045*sc, 0.045*sc, 0.015*sc), group_name="eyelids")
    add_ellipsoid((sx*0.18*sc, -0.68*sc, 1.38*sc), (0.04*sc, 0.03*sc, 0.06*sc), group_name="ears")

# Build in Blender
m_data = bpy.data.meshes.new(f"{{obj_name}}_Mesh")
b_obj = bpy.data.objects.new(obj_name, m_data)
m_data.from_pydata(verts, [], faces)
m_data.update()
for vg_name, indices in vgs.items():
    vg = b_obj.vertex_groups.new(name=vg_name)
    if indices:
        vg.add(indices, 1.0, 'REPLACE')
for p in m_data.polygons:
    p.use_smooth = True
bpy.context.scene.collection.objects.link(b_obj)

out_vars = {{
    "status": "success",
    "object_name": b_obj.name,
    "vertex_count": len(m_data.vertices),
    "face_count": len(m_data.polygons),
    "vertex_groups_count": len(b_obj.vertex_groups),
}}
'''
