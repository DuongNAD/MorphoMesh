"""
Unit tests for blueprint_inverted_hull.py and blueprint_camera_rig.py.
Run via: uv run pytest .agents/m4_explorer_anime_2/test_blueprints_unit.py -v
"""

import sys
import os
import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import blueprint_inverted_hull as bih
import blueprint_camera_rig as bcr


def test_inverted_hull_config_defaults():
    cfg = bih.OutlineConfig()
    assert cfg.modifier_name == "Anime_Outline"
    assert cfg.material_name == "M_Anime_Outline"
    assert -0.004 <= cfg.thickness <= -0.003
    assert cfg.offset == 1.0
    assert cfg.use_flip_normals is True
    assert cfg.use_rim is False
    assert cfg.material_offset == 1
    assert cfg.use_backface_culling is True
    assert cfg.validate() is True


def test_inverted_hull_offline_simulation():
    res = bih.apply_inverted_hull_outline()
    assert res.success is True
    assert len(res.modified_objects) == 7
    for name in bih.CANONICAL_MESH_NAMES:
        assert name in res.modified_objects


def test_camera_config_optical_properties():
    cfg = bcr.CameraConfig()
    assert cfg.name == "Anime_Camera"
    assert 50.0 <= cfg.focal_length_mm <= 85.0
    assert cfg.focal_length_mm == 65.0
    assert cfg.sensor_width_mm == 36.0
    assert cfg.position == (0.0, -2.6, 1.25)
    assert cfg.target_bone == "Spine2"
    assert cfg.track_axis == "TRACK_NEGATIVE_Z"
    assert cfg.up_axis == "UP_Y"

    fov_v = cfg.calculate_fov_vertical()
    assert 0.25 <= fov_v <= 0.35  # ~17.65 degrees

    dist = cfg.calculate_framing_distance(1.65, margin=0.15)
    assert 2.5 <= dist <= 7.0


def test_3point_lighting_rig_specifications():
    rig = bcr.LightingRigConfig()
    lights_dict = rig.to_dict()

    # Test presence of primary names and tier 1 aliases
    for key in ["Light_Key", "Light_Fill", "Light_Rim", "Key_Light", "Fill_Light", "Rim_Light"]:
        assert key in lights_dict, f"Missing light key: {key}"

    key_light = lights_dict["Key_Light"]
    fill_light = lights_dict["Fill_Light"]
    rim_light = lights_dict["Rim_Light"]

    assert key_light["energy_watts"] == 650.0
    assert fill_light["energy_watts"] == 200.0
    assert rim_light["energy_watts"] == 800.0

    # Key light must be stronger than fill light
    assert key_light["energy_watts"] > fill_light["energy_watts"]
    # Rim light must provide high intensity back separation
    assert rim_light["energy_watts"] > key_light["energy_watts"]


def test_hex_to_linear_rgb_conversion():
    key_rgb = bcr.hex_to_linear_rgb("FFF5EA")
    assert abs(key_rgb[0] - 1.0) < 1e-4
    assert 0.90 <= key_rgb[1] <= 0.92
    assert 0.80 <= key_rgb[2] <= 0.84

    white_rgb = bcr.hex_to_linear_rgb("FFFFFF")
    assert white_rgb == (1.0, 1.0, 1.0)


def test_setup_cinematic_stage_offline_simulation():
    res = bcr.setup_cinematic_stage()
    assert res.success is True
    assert res.camera_name == "Anime_Camera"
    assert res.focal_length_mm == 65.0
    assert "Light_Key" in res.lights
    assert "Light_Fill" in res.lights
    assert "Light_Rim" in res.lights
