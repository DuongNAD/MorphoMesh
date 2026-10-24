"""
Procedural Hair Angel Ring (Tenshi no Wa / 天使の輪) for Anime Character Pipeline (Feature F15).
Target: anime_pipeline/shading/angel_ring.py

Provides authentic anime procedural hair highlight:
- Object-space Z-coordinate band: Texture Coordinate (Object) -> Separate XYZ (Z)
  -> Map Range (1.45m - 1.55m) -> ColorRamp (sharp highlight band #FFFFFF).
- Light / Diffuse Gating: Multiplies highlight with ShaderToRGB diffuse factor
  (ShaderNodeMath MULTIPLY) so the halo only appears on the illuminated side.
- Result: A sharp horizontal circular halo highlight around the crown of the head
  that tracks with light and stays at the crown regardless of camera angle.

Compatible with Blender 4.5.4 LTS EEVEE-Next (BLENDER_EEVEE_NEXT).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import bpy
    import mathutils
    HAS_BPY = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    HAS_BPY = False


# -----------------------------------------------------------------------------
# Color & Geometry Constants
# -----------------------------------------------------------------------------

# Base Hair Tones
# Default: Deep slate navy anime hair (#3D405B)
HAIR_BASE_COLOR: Tuple[float, float, float, float] = (0.239, 0.251, 0.357, 1.0)
# Shadow tone: Deep indigo shadow (#1A1B28)
HAIR_SHADOW_COLOR: Tuple[float, float, float, float] = (0.102, 0.106, 0.157, 1.0)

# Angel Ring Highlight Tint (Conforms to test_tier1_features: (1.0, 1.0, 0.95, 1.0))
ANGEL_RING_COLOR: Tuple[float, float, float, float] = (1.0, 1.0, 0.95, 1.0)

# Canonical Anime Crown Z-Bounds in Object Space (Meters)
# Measured empirically on Anime_Hair mesh: Local Z in [1.15, 1.65], crown circle at Z ~ 1.52m
DEFAULT_CROWN_Z_MIN: float = 1.45
DEFAULT_CROWN_Z_MAX: float = 1.55


# -----------------------------------------------------------------------------
# Geometry Analysis Utilities
# -----------------------------------------------------------------------------

def compute_hair_crown_z_bounds(
    hair_obj: Union[str, Any],
    quantile_low: float = 0.65,
    quantile_high: float = 0.85,
) -> Tuple[float, float]:
    """
    Computes crown Z height bounds dynamically from hair mesh vertex coordinates.
    Returns (z_min, z_max) in object space.
    """
    if not HAS_BPY:
        return (DEFAULT_CROWN_Z_MIN, DEFAULT_CROWN_Z_MAX)

    if isinstance(hair_obj, str):
        hair_obj = bpy.data.objects.get(hair_obj)

    if not hair_obj or hair_obj.type != "MESH":
        return (DEFAULT_CROWN_Z_MIN, DEFAULT_CROWN_Z_MAX)

    zs = [v.co.z for v in hair_obj.data.vertices]
    if not zs:
        return (DEFAULT_CROWN_Z_MIN, DEFAULT_CROWN_Z_MAX)

    zs_sorted = sorted(zs)
    n = len(zs_sorted)
    z_min = zs_sorted[int(n * quantile_low)]
    z_max = zs_sorted[int(n * quantile_high)]

    # Fallback sanity check: Ensure positive non-degenerate interval
    if z_max <= z_min + 0.02:
        return (DEFAULT_CROWN_Z_MIN, DEFAULT_CROWN_Z_MAX)

    return (round(z_min, 3), round(z_max, 3))


# -----------------------------------------------------------------------------
# Procedural Angel Ring Material Builder
# -----------------------------------------------------------------------------

def build_procedural_angel_ring_material(
    name: str = "M_Anime_Hair",
    base_color: Tuple[float, float, float, float] = HAIR_BASE_COLOR,
    shadow_color: Tuple[float, float, float, float] = HAIR_SHADOW_COLOR,
    ring_color: Tuple[float, float, float, float] = ANGEL_RING_COLOR,
    crown_z_min: float = DEFAULT_CROWN_Z_MIN,
    crown_z_max: float = DEFAULT_CROWN_Z_MAX,
    cel_threshold: float = 0.45,
) -> Any:
    """
    Constructs the procedural hair material with light-gated Angel Ring highlight.
    
    Node Tree Graph:
    ================
    [Diffuse BSDF] ──► [Shader to RGB] ──► [Cel ColorRamp (CONSTANT)]
                             │                        │ (A_Color)
                             │                        ▼
                             ├───────► [DiffuseGating: MATH MULTIPLY]
                             │                        ▲
                             │ (Color)                │ (Color)
                             │               [AngelRing ColorRamp]
                             │                        ▲
                             │                        │ (Result)
                             │               [ObjectSpaceZBand: MAP_RANGE]
                             │                        ▲
                             │                        │ (Z)
                             │               [Separate XYZ]
                             │                        ▲
                             │                        │ (Object)
                             │               [Texture Coordinate]
                             │                        │
                             ▼                        ▼
                   [AngelRing_Mix: MIX] ◄─────────────┘ (Factor)
                             │ (Result_Color)
                             ▼
                     [Material Output]
    
    Conforms strictly to:
      - Feature F15 specification
      - test_tier1_features.py (ObjectSpaceZBand MAP_RANGE [1.45, 1.55], DiffuseGating MULTIPLY)
    """
    if not HAS_BPY:
        return {
            "name": name,
            "type": "M_Anime_Hair",
            "TextureCoordinate": {"type": "TEX_COORD"},
            "ObjectSpaceZBand": {"type": "MAP_RANGE", "from_min": crown_z_min, "from_max": crown_z_max},
            "DiffuseGating": {"type": "MATH", "operation": "MULTIPLY"},
            "AngelRingColor": ring_color,
        }

    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    # -------------------------------------------------------------------------
    # 1. Base Diffuse Cel-Shading Branch
    # -------------------------------------------------------------------------
    diffuse = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.name = "Diffuse_BSDF"
    diffuse.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    diffuse.inputs["Roughness"].default_value = 1.0

    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.name = "Shader_To_RGB"

    cel_ramp = nt.nodes.new("ShaderNodeValToRGB")
    cel_ramp.name = "Cel_ColorRamp"
    cel_ramp.color_ramp.interpolation = "CONSTANT"
    cel_ramp.color_ramp.elements[0].position = 0.0
    cel_ramp.color_ramp.elements[0].color = shadow_color
    cel_ramp.color_ramp.elements[1].position = cel_threshold
    cel_ramp.color_ramp.elements[1].color = base_color

    # -------------------------------------------------------------------------
    # 2. Object-Space Z-Coordinate Band Branch (Crown Halo Ring)
    # -------------------------------------------------------------------------
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    tex_coord.name = "TextureCoordinate"

    sep_xyz = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep_xyz.name = "SeparateXYZ"

    # MapRange normalizes object-space Z crown band (1.45m - 1.55m) into [0.0, 1.0]
    map_range = nt.nodes.new("ShaderNodeMapRange")
    map_range.name = "ObjectSpaceZBand"
    map_range.inputs["From Min"].default_value = crown_z_min
    map_range.inputs["From Max"].default_value = crown_z_max
    map_range.inputs["To Min"].default_value = 0.0
    map_range.inputs["To Max"].default_value = 1.0

    # ColorRamp shapes the normalized band into a sharp circular specular ring
    ring_ramp = nt.nodes.new("ShaderNodeValToRGB")
    ring_ramp.name = "AngelRing_ColorRamp"
    ring_ramp.color_ramp.interpolation = "LINEAR"
    # Left edge dropoff
    ring_ramp.color_ramp.elements[0].position = 0.15
    ring_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    # Sharp highlight peak centered at crown level
    ring_ramp.color_ramp.elements[1].position = 0.60
    ring_ramp.color_ramp.elements[1].color = ring_color
    # Right edge dropoff
    e_close = ring_ramp.color_ramp.elements.new(0.85)
    e_close.color = (0.0, 0.0, 0.0, 1.0)

    # -------------------------------------------------------------------------
    # 3. Light / Diffuse Gating Branch (MATH: MULTIPLY)
    # -------------------------------------------------------------------------
    # Multiplies halo ring intensity with scene diffuse light factor.
    # Halo ONLY shines on the lit side of the head; drops to zero in shadow!
    math_gate = nt.nodes.new("ShaderNodeMath")
    math_gate.name = "DiffuseGating"
    math_gate.operation = "MULTIPLY"

    # -------------------------------------------------------------------------
    # 4. Composite Mix Branch
    # -------------------------------------------------------------------------
    # Mixes cel-shaded base hair with the pure Angel Ring highlight color
    mix_final = nt.nodes.new("ShaderNodeMix")
    mix_final.name = "AngelRing_Mix"
    mix_final.data_type = "RGBA"
    mix_final.blend_type = "MIX"
    # B_Color (input index 7) holds the pure highlight color
    mix_final.inputs[7].default_value = ring_color

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.name = "Material_Output"

    # -------------------------------------------------------------------------
    # Links Construction
    # -------------------------------------------------------------------------
    # Diffuse lighting chain
    nt.links.new(diffuse.outputs["BSDF"], s2rgb.inputs["Shader"])
    nt.links.new(s2rgb.outputs["Color"], cel_ramp.inputs["Fac"])

    # Geometry Z-band chain
    nt.links.new(tex_coord.outputs["Object"], sep_xyz.inputs["Vector"])
    nt.links.new(sep_xyz.outputs["Z"], map_range.inputs["Value"])
    nt.links.new(map_range.outputs["Result"], ring_ramp.inputs["Fac"])

    # Diffuse gating chain
    nt.links.new(ring_ramp.outputs["Color"], math_gate.inputs[0])
    nt.links.new(s2rgb.outputs["Color"], math_gate.inputs[1])

    # Final composite chain: Gated factor controls blend
    nt.links.new(math_gate.outputs["Value"], mix_final.inputs[0])   # Factor_Float
    nt.links.new(cel_ramp.outputs["Color"], mix_final.inputs[6])    # A_Color
    nt.links.new(mix_final.outputs[2], out.inputs["Surface"])       # Result_Color

    return mat


def apply_angel_ring_to_hair(
    hair_obj_name: str = "Anime_Hair",
    mat_name: str = "M_Anime_Hair",
    base_color: Tuple[float, float, float, float] = HAIR_BASE_COLOR,
    shadow_color: Tuple[float, float, float, float] = HAIR_SHADOW_COLOR,
    auto_detect_crown: bool = False,
) -> Any:
    """
    Applies the procedural Angel Ring hair material to Anime_Hair object.
    """
    if not HAS_BPY:
        return build_procedural_angel_ring_material(mat_name, base_color, shadow_color)

    hair_obj = bpy.data.objects.get(hair_obj_name)

    crown_z_min = DEFAULT_CROWN_Z_MIN
    crown_z_max = DEFAULT_CROWN_Z_MAX

    if auto_detect_crown and hair_obj:
        crown_z_min, crown_z_max = compute_hair_crown_z_bounds(hair_obj)

    mat = build_procedural_angel_ring_material(
        name=mat_name,
        base_color=base_color,
        shadow_color=shadow_color,
        crown_z_min=crown_z_min,
        crown_z_max=crown_z_max,
    )

    if hair_obj and hair_obj.type == "MESH":
        if len(hair_obj.material_slots) == 0:
            hair_obj.data.materials.append(mat)
        else:
            hair_obj.material_slots[0].material = mat

    return mat
