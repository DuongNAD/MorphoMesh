"""
MorphoMesh: Pipeline Enumerations & Presets Taxonomy.
"""
from __future__ import annotations

from enum import Enum
from typing import Any


class CreatureType(str, Enum):
    QUADRUPED = "quadruped"
    BIPED = "biped"
    WINGED = "winged"
    AQUATIC = "aquatic"
    SERPENTINE = "serpentine"
    HYBRID = "hybrid"
    CUSTOM = "custom"
    WINGED_QUADRUPED = "winged_quadruped"
    BIRD = "bird"
    SPIDER_ARTHROPOD = "spider_arthropod"
    FISH_AQUATIC = "fish_aquatic"
    CUSTOM_AUTO = "custom_auto"


class ViewMode(str, Enum):
    FRONT = "front"
    SIDE = "side"
    THREE_QUARTER = "three_quarter"
    TOP = "top"
    TURNAROUND_SHEET = "turnaround_sheet"
    ORTHOGRAPHIC_FRONT_SIDE = "orthographic_front_side"
    TURNTABLE_4VIEWS = "turntable_4views"
    ACTIVE_CAMERA = "active_camera"


class Pose(str, Enum):
    NEUTRAL_T_POSE = "neutral_t_pose"
    NEUTRAL_A_POSE = "neutral_a_pose"
    STANDING_NEUTRAL = "standing_neutral"
    RELAXED = "relaxed"


class Style(str, Enum):
    REALISTIC = "realistic"
    STYLIZED = "stylized"
    DARK_FANTASY = "dark_fantasy"
    SCI_FI = "sci_fi"
    CARTOON = "cartoon"
    SCULPTURE = "sculpture"


class QualityTier(str, Enum):
    DRAFT = "draft"
    STANDARD = "standard"
    PRODUCTION = "production"
    ULTRA = "ultra"


class TopologyType(str, Enum):
    QUAD_DOMINANT = "quad_dominant"
    PURE_QUAD = "pure_quad"
    TRIANGULATED = "triangulated"
    ADAPTIVE = "adaptive"


class RetopoMethod(str, Enum):
    QUADRIFLOW = "quadriflow"
    DECIMATE = "decimate"
    VOXEL_REMESH = "voxel_remesh"
    MESHANYTHING_V2 = "meshanything_v2"
    MOCK = "mock"


class RigType(str, Enum):
    BASIC_FK = "basic_fk"
    RIGIFY_CREATURE = "rigify_creature"
    GAME_ENGINE_ROOT = "game_engine_root"
    DEFORM_ONLY = "deform_only"


class SkinningMethod(str, Enum):
    AUTOMATIC_WEIGHTS = "automatic_weights"
    VOXEL_HEAT_DIFFUSE = "voxel_heat_diffuse"
    GEODESIC_VOXEL = "geodesic_voxel"


class RenderEngine(str, Enum):
    BLENDER_EEVEE = "BLENDER_EEVEE"
    BLENDER_EEVEE_NEXT = "BLENDER_EEVEE_NEXT"
    CYCLES = "CYCLES"
    BLENDER_WORKBENCH = "BLENDER_WORKBENCH"


class LightingPreset(str, Enum):
    STUDIO_THREE_POINT = "studio_three_point"
    DRAMATIC_RIM = "dramatic_rim"
    NEUTRAL_SOFTBOX = "neutral_softbox"
    OUTDOOR_SUN = "outdoor_sun"
    SCENE_DEFAULT = "scene_default"


class InspectorViewpoint(str, Enum):
    FRONT = "front"
    SIDE = "side"
    SIDE_LEFT = "side_left"
    BACK = "back"
    THREE_QUARTER = "three_quarter"
    TOP = "top"
    BOTTOM = "bottom"
    HEAD = "head"
    CLOSE_UP_HEAD = "close_up_head"
    PORTRAIT = "portrait"
    HANDS = "hands"
    CLOSE_UP_HANDS = "close_up_hands"
    TORSO = "torso"
    FEET = "feet"
    TURNTABLE = "turntable"
    TURNTABLE_4VIEWS = "turntable_4views"


class AnthropometricPreset(str, Enum):
    REALISTIC_HUMAN = "realistic_human"
    STYLIZED_HEROINE = "stylized_heroine"
    CHIBI_PETITE = "chibi_petite"
    REALISTIC_FEMALE = "realistic_female"
    HEROIC_MALE = "heroic_male"
    CHIBI = "chibi"


TargetPreset = AnthropometricPreset


VALID_INSPECTOR_VIEWPOINTS_SET = {e.value for e in InspectorViewpoint} | {
    "view_front", "front_view", "side_right", "view_side", "view_side_left",
    "view_back", "back_view", "front_three_quarter", "three_quarter_left",
    "back_three_quarter", "head_close_up", "hands_close_up", "marionette",
    "bodice", "sandals", "shoes",
}


class DiagnosticShadingMode(str, Enum):
    SOLID = "SOLID"
    FLAT = "FLAT"
    WIREFRAME = "WIREFRAME"
    MATERIAL = "MATERIAL"
    RENDERED = "RENDERED"


class DiagnosticColorType(str, Enum):
    RANDOM = "RANDOM"
    MATERIAL = "MATERIAL"
    SINGLE = "SINGLE"
    OBJECT = "OBJECT"
    TEXTURE = "TEXTURE"


class DefectSeverity(str, Enum):
    """Authoritative defect severity ranking."""
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            val_upper = value.strip().upper()
            mapping = {
                "HIGH": cls.CRITICAL,
                "MEDIUM": cls.MAJOR,
                "LOW": cls.MINOR,
                "ERROR": cls.CRITICAL,
                "WARNING": cls.MAJOR,
                "NOTICE": cls.INFO,
            }
            if val_upper in mapping:
                return mapping[val_upper]
            for member in cls:
                if member.value.upper() == val_upper or member.name.upper() == val_upper:
                    return member
        return None


class DefectCategory(str, Enum):
    """Categorization of automated visual critique defects."""
    PENETRATION = "PENETRATION"
    PROPORTION = "PROPORTION"
    SKINNING_PINCH = "SKINNING_PINCH"
    GROOMING_COLLISION = "GROOMING_COLLISION"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            val_upper = value.strip().upper()
            mapping = {
                "CLIPPING": cls.PENETRATION,
                "MESH_PENETRATION": cls.PENETRATION,
                "FACE_OVERLAP": cls.PENETRATION,
                "SKIN_BURST": cls.PENETRATION,
                "PROPORTION_DEVIATION": cls.PROPORTION,
                "BODY_PROPORTION": cls.PROPORTION,
                "SKINNING_ARTIFACT": cls.SKINNING_PINCH,
                "RIG_PINCH": cls.SKINNING_PINCH,
                "PINCHING": cls.SKINNING_PINCH,
                "GROOMING_INTERSECTION": cls.GROOMING_COLLISION,
                "HAIR_CLIPPING": cls.GROOMING_COLLISION,
                "GROOMING_ROOT_SUBMERGED": cls.GROOMING_COLLISION,
                "GROOMING_BODY_COLLISION": cls.GROOMING_COLLISION,
                "GROOMING_GARMENT_COLLISION": cls.GROOMING_COLLISION,
            }
            if val_upper in mapping:
                return mapping[val_upper]
            for member in cls:
                if member.value.upper() == val_upper or member.name.upper() == val_upper:
                    return member
        return None


__all__ = [
    "AnthropometricPreset",
    "CreatureType",
    "DefectCategory",
    "DefectSeverity",
    "DiagnosticColorType",
    "DiagnosticShadingMode",
    "InspectorViewpoint",
    "LightingPreset",
    "Pose",
    "QualityTier",
    "RenderEngine",
    "RetopoMethod",
    "RigType",
    "SkinningMethod",
    "Style",
    "TargetPreset",
    "TopologyType",
    "VALID_INSPECTOR_VIEWPOINTS_SET",
    "ViewMode",
]
