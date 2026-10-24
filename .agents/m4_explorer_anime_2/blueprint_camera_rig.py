"""
anime_pipeline/rendering/camera_rig.py (also importable as anime_pipeline/render/camera_rig.py)
Milestone 4 Feature F17: Cinematic Anime Camera Rig & Calibrated 3-Point Lighting.

Authoritative Specification:
- F17: Studio-grade cinematic camera and 3-point lighting rig for EEVEE-Next cel-shading:
    1. Camera Anime_Camera:
       - Focal Length: 65.0mm (cinematic anime portrait lens, minimizes perspective distortion).
       - Sensor Size: 36.0mm width x 20.25mm height (35mm Full Frame 16:9 aspect ratio).
       - Position: (0.0, -2.6, 1.25) in meters (medium portrait / cowboy shot framing,
         spanning X=0.0, Y in [-2.8m, -2.5m], Z=1.25m).
       - Constraint: TRACK_TO targeting Anime_Armature bone Spine2 (fallback Head).
         Track axis: TRACK_NEGATIVE_Z, Up axis: UP_Y.
       - Active Scene Camera: Assigned as scene.camera for headless rendering.
    2. Anime 3-Point Lighting Rig (calibrated for EEVEE-Next cel-shading & shadow ramps):
       - Key Light (Light_Key / Key_Light):
         * Type: POINT (or SUN).
         * Color: #FFF5EA -> linear RGB (1.0, 0.913, 0.823) (warm sunlight).
         * Energy: 650.0W.
         * Position: (1.8, -2.0, 2.5) (35-45 deg frontal-lateral elevation).
       - Fill Light (Light_Fill / Fill_Light):
         * Type: POINT (or SUN).
         * Color: #D6E4FF -> linear RGB (0.672, 0.776, 1.0) (soft cool ambient skylight).
         * Energy: 200.0W.
         * Position: (-1.5, -1.8, 1.8) (opposite lateral angle).
       - Rim Light (Light_Rim / Rim_Light):
         * Type: POINT (or SUN).
         * Color: #FFFFFF -> linear RGB (1.0, 1.0, 1.0) (crisp separation highlight).
         * Energy: 800.0W.
         * Position: (-0.5, 1.5, 2.2) (behind character targeting twintails and shoulders).
       - All lights include TRACK_TO aiming constraints targeting the character.
- Dual-Mode Architecture: Fully functional inside live Blender 4.5.4 LTS (bpy) and provides
  pure-Python dataclasses, optical math formulas, and dictionary exports for offline tests.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import bpy
    HAS_BPY = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    HAS_BPY = False


# ==============================================================================
# CANONICAL CONSTANTS
# ==============================================================================

DEFAULT_CAMERA_NAME: str = "Anime_Camera"
DEFAULT_CAMERA_FOCAL_LENGTH: float = 65.0  # mm
DEFAULT_CAMERA_SENSOR_WIDTH: float = 36.0  # mm
DEFAULT_CAMERA_SENSOR_HEIGHT: float = 20.25  # mm (36.0 * 1080 / 1920)
DEFAULT_CAMERA_POSITION: Tuple[float, float, float] = (0.0, -2.6, 1.25)
DEFAULT_TRACK_TARGET_ARMATURE: str = "Anime_Armature"
DEFAULT_TRACK_TARGET_BONE: str = "Spine2"
DEFAULT_FALLBACK_BONE: str = "Head"
DEFAULT_TRACK_AXIS: str = "TRACK_NEGATIVE_Z"
DEFAULT_UP_AXIS: str = "UP_Y"

# Lighting Constants
KEY_LIGHT_NAME: str = "Light_Key"
FILL_LIGHT_NAME: str = "Light_Fill"
RIM_LIGHT_NAME: str = "Light_Rim"

# Alternate names for backward-compatibility with tier 1 tests
KEY_LIGHT_ALT_NAME: str = "Key_Light"
FILL_LIGHT_ALT_NAME: str = "Fill_Light"
RIM_LIGHT_ALT_NAME: str = "Rim_Light"


def hex_to_linear_rgb(hex_str: str) -> Tuple[float, float, float]:
    """Convert a hex color string (e.g. #FFF5EA) to Blender linear RGB float tuple."""
    clean_hex = hex_str.lstrip("#")
    if len(clean_hex) != 6:
        raise ValueError(f"Invalid hex color string: {hex_str}")
    srgb = [int(clean_hex[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    # Standard sRGB to Linear RGB conversion formula
    linear = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        for c in srgb
    ]
    return (linear[0], linear[1], linear[2])


# Pre-computed linear colors
KEY_LIGHT_COLOR: Tuple[float, float, float] = hex_to_linear_rgb("FFF5EA")
FILL_LIGHT_COLOR: Tuple[float, float, float] = hex_to_linear_rgb("D6E4FF")
RIM_LIGHT_COLOR: Tuple[float, float, float] = hex_to_linear_rgb("FFFFFF")


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

@dataclass
class CameraConfig:
    """Configuration for cinematic anime camera."""

    name: str = DEFAULT_CAMERA_NAME
    focal_length_mm: float = DEFAULT_CAMERA_FOCAL_LENGTH
    sensor_width_mm: float = DEFAULT_CAMERA_SENSOR_WIDTH
    sensor_height_mm: float = DEFAULT_CAMERA_SENSOR_HEIGHT
    position: Tuple[float, float, float] = DEFAULT_CAMERA_POSITION
    target_armature: str = DEFAULT_TRACK_TARGET_ARMATURE
    target_bone: str = DEFAULT_TRACK_TARGET_BONE
    fallback_bone: str = DEFAULT_FALLBACK_BONE
    track_axis: str = DEFAULT_TRACK_AXIS
    up_axis: str = DEFAULT_UP_AXIS
    clip_start: float = 0.1
    clip_end: float = 100.0

    def calculate_fov_vertical(self) -> float:
        """Calculate vertical Field of View in radians."""
        return 2.0 * math.atan(self.sensor_height_mm / (2.0 * self.focal_length_mm))

    def calculate_fov_horizontal(self) -> float:
        """Calculate horizontal Field of View in radians."""
        return 2.0 * math.atan(self.sensor_width_mm / (2.0 * self.focal_length_mm))

    def calculate_framing_distance(self, target_height: float, margin: float = 0.15) -> float:
        """Calculate required distance to frame a target height with given margin."""
        fov_v = self.calculate_fov_vertical()
        effective_height = target_height * (1.0 + margin)
        return (effective_height * 0.5) / math.tan(fov_v * 0.5)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tracked_target"] = self.target_bone
        return d


@dataclass
class LightSpec:
    """Specification for an individual light source."""

    name: str
    light_type: str = "POINT"  # POINT, SUN, AREA, SPOT
    energy_watts: float = 650.0
    color_hex: str = "#FFF5EA"
    color_rgb: Tuple[float, float, float] = KEY_LIGHT_COLOR
    position: Tuple[float, float, float] = (1.8, -2.0, 2.5)
    track_target: Optional[str] = DEFAULT_TRACK_TARGET_ARMATURE
    track_bone: Optional[str] = DEFAULT_TRACK_TARGET_BONE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.light_type,
            "energy_watts": self.energy_watts,
            "color_hex": self.color_hex,
            "color_rgb": self.color_rgb,
            "position": self.position,
        }


@dataclass
class LightingRigConfig:
    """Configuration for calibrated 3-point anime lighting rig."""

    key_light: LightSpec = field(
        default_factory=lambda: LightSpec(
            name=KEY_LIGHT_NAME,
            light_type="POINT",
            energy_watts=650.0,
            color_hex="#FFF5EA",
            color_rgb=KEY_LIGHT_COLOR,
            position=(1.8, -2.0, 2.5),
        )
    )
    fill_light: LightSpec = field(
        default_factory=lambda: LightSpec(
            name=FILL_LIGHT_NAME,
            light_type="POINT",
            energy_watts=200.0,
            color_hex="#D6E4FF",
            color_rgb=FILL_LIGHT_COLOR,
            position=(-1.5, -1.8, 1.8),
        )
    )
    rim_light: LightSpec = field(
        default_factory=lambda: LightSpec(
            name=RIM_LIGHT_NAME,
            light_type="POINT",
            energy_watts=800.0,
            color_hex="#FFFFFF",
            color_rgb=RIM_LIGHT_COLOR,
            position=(-0.5, 1.5, 2.2),
        )
    )

    def get_lights(self) -> List[LightSpec]:
        return [self.key_light, self.fill_light, self.rim_light]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary supporting both primary and alternate naming conventions."""
        lights = {
            self.key_light.name: self.key_light.to_dict(),
            self.fill_light.name: self.fill_light.to_dict(),
            self.rim_light.name: self.rim_light.to_dict(),
            # Aliases for Tier 1 tests
            KEY_LIGHT_ALT_NAME: self.key_light.to_dict(),
            FILL_LIGHT_ALT_NAME: self.fill_light.to_dict(),
            RIM_LIGHT_ALT_NAME: self.rim_light.to_dict(),
        }
        return lights


@dataclass
class CinematicStageResult:
    """Result summary of setting up camera and lighting stage."""

    success: bool
    camera_name: str = DEFAULT_CAMERA_NAME
    camera_position: Tuple[float, float, float] = DEFAULT_CAMERA_POSITION
    focal_length_mm: float = DEFAULT_CAMERA_FOCAL_LENGTH
    lights: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# CAMERA CREATION & TRACKING
# ==============================================================================

def create_cinematic_camera(config: Optional[CameraConfig] = None) -> Any:
    """
    Create or update the cinematic camera Anime_Camera with tracking constraint.

    Configures:
    - 65mm focal length, 36x20.25mm sensor
    - Position (0.0, -2.6, 1.25)
    - TRACK_TO targeting Anime_Armature bone Spine2 (fallback Head)
    - Sets active camera in scene
    """
    if config is None:
        config = CameraConfig()

    if not HAS_BPY:
        return config.to_dict()

    scene = bpy.context.scene

    # Get or create camera data
    cam_data = bpy.data.cameras.get(config.name)
    if cam_data is None:
        cam_data = bpy.data.cameras.new(config.name)

    cam_data.lens = config.focal_length_mm
    cam_data.sensor_width = config.sensor_width_mm
    cam_data.sensor_height = config.sensor_height_mm
    cam_data.clip_start = config.clip_start
    cam_data.clip_end = config.clip_end

    # Get or create camera object
    cam_obj = bpy.data.objects.get(config.name)
    if cam_obj is None:
        cam_obj = bpy.data.objects.new(config.name, cam_data)
        scene.collection.objects.link(cam_obj)

    cam_obj.location = config.position

    # Add or update TRACK_TO constraint
    target_arm = bpy.data.objects.get(config.target_armature)
    if target_arm is not None:
        con_name = f"Track_{config.target_bone}"
        con = cam_obj.constraints.get(con_name)
        if con is None:
            # Check for any existing TRACK_TO constraint
            track_cons = [c for c in cam_obj.constraints if c.type == "TRACK_TO"]
            con = track_cons[0] if track_cons else cam_obj.constraints.new(type="TRACK_TO")
            con.name = con_name

        con.target = target_arm
        # Choose subtarget bone
        if hasattr(target_arm, "pose") and target_arm.pose:
            if config.target_bone in target_arm.pose.bones:
                con.subtarget = config.target_bone
            elif config.fallback_bone in target_arm.pose.bones:
                con.subtarget = config.fallback_bone

        con.track_axis = config.track_axis
        con.up_axis = config.up_axis

    # Set as active scene camera
    scene.camera = cam_obj
    return cam_obj


# ==============================================================================
# 3-POINT LIGHTING RIG CREATION
# ==============================================================================

def create_3point_lighting_rig(config: Optional[LightingRigConfig] = None) -> Dict[str, Any]:
    """
    Create or update the calibrated 3-point anime lighting rig.

    Creates:
    1. Light_Key: 650W warm sunlight at (1.8, -2.0, 2.5)
    2. Light_Fill: 200W cool ambient skylight at (-1.5, -1.8, 1.8)
    3. Light_Rim: 800W crisp rim separator at (-0.5, 1.5, 2.2)

    All lights track Anime_Armature Spine2 for consistent directional focus.
    """
    if config is None:
        config = LightingRigConfig()

    if not HAS_BPY:
        return config.to_dict()

    scene = bpy.context.scene
    target_arm = bpy.data.objects.get(DEFAULT_TRACK_TARGET_ARMATURE)
    created_lights: Dict[str, Any] = {}

    for spec in config.get_lights():
        # Light data block
        ldata = bpy.data.lights.get(spec.name)
        if ldata is None:
            ldata = bpy.data.lights.new(spec.name, spec.light_type)
        ldata.type = spec.light_type
        ldata.energy = spec.energy_watts
        ldata.color = spec.color_rgb

        # Light object
        lobj = bpy.data.objects.get(spec.name)
        if lobj is None:
            lobj = bpy.data.objects.new(spec.name, ldata)
            scene.collection.objects.link(lobj)

        lobj.location = spec.position

        # Track to character
        if target_arm is not None:
            con_name = f"Track_{spec.track_bone}"
            con = lobj.constraints.get(con_name)
            if con is None:
                track_cons = [c for c in lobj.constraints if c.type == "TRACK_TO"]
                con = track_cons[0] if track_cons else lobj.constraints.new(type="TRACK_TO")
                con.name = con_name
            con.target = target_arm
            if hasattr(target_arm, "pose") and target_arm.pose:
                if spec.track_bone in target_arm.pose.bones:
                    con.subtarget = spec.track_bone
                elif DEFAULT_FALLBACK_BONE in target_arm.pose.bones:
                    con.subtarget = DEFAULT_FALLBACK_BONE
            con.track_axis = DEFAULT_TRACK_AXIS
            con.up_axis = DEFAULT_UP_AXIS

        created_lights[spec.name] = lobj

    # Register aliases
    created_lights[KEY_LIGHT_ALT_NAME] = created_lights.get(KEY_LIGHT_NAME)
    created_lights[FILL_LIGHT_ALT_NAME] = created_lights.get(FILL_LIGHT_NAME)
    created_lights[RIM_LIGHT_ALT_NAME] = created_lights.get(RIM_LIGHT_NAME)
    return created_lights


# ==============================================================================
# MASTER STAGE SETUP
# ==============================================================================

def setup_cinematic_stage(
    camera_config: Optional[CameraConfig] = None,
    lighting_config: Optional[LightingRigConfig] = None,
) -> CinematicStageResult:
    """
    Set up the complete cinematic stage (Camera + 3-Point Lighting Rig).

    Returns CinematicStageResult with summary metrics.
    """
    if camera_config is None:
        camera_config = CameraConfig()
    if lighting_config is None:
        lighting_config = LightingRigConfig()

    errors: List[str] = []

    try:
        cam_obj = create_cinematic_camera(camera_config)
    except Exception as e:
        errors.append(f"Failed creating camera: {e}")
        cam_obj = None

    try:
        lights = create_3point_lighting_rig(lighting_config)
    except Exception as e:
        errors.append(f"Failed creating lighting rig: {e}")
        lights = {}

    return CinematicStageResult(
        success=len(errors) == 0,
        camera_name=camera_config.name,
        camera_position=camera_config.position,
        focal_length_mm=camera_config.focal_length_mm,
        lights=lighting_config.to_dict(),
        errors=errors,
    )


def calculate_optical_framing_distance(
    character_height: float,
    focal_length_mm: float = DEFAULT_CAMERA_FOCAL_LENGTH,
    sensor_height_mm: float = DEFAULT_CAMERA_SENSOR_HEIGHT,
    margin: float = 0.15,
) -> float:
    """
    Calculate optical camera distance to frame a character of given height.

    Formula:
    FOV_v = 2 * atan(sensor_height / (2 * focal_length))
    Distance = (character_height * (1 + margin) / 2) / tan(FOV_v / 2)
    """
    fov_v = 2.0 * math.atan(sensor_height_mm / (2.0 * focal_length_mm))
    effective_h = character_height * (1.0 + margin)
    return (effective_h * 0.5) / math.tan(fov_v * 0.5)
