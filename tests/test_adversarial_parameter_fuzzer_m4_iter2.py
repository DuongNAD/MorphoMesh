# Adversarial Enum and Parameter Fuzzer Test Suite for Milestone 4 Iteration 2.
from __future__ import annotations
import math
from typing import Any, Dict
import pytest
from mcp.server.fastmcp.exceptions import ToolError
from morphomesh.server import (
    mcp,
    morphomesh_capture_viewport,
    morphomesh_critique_visual_quality,
    morphomesh_setup_inspector_camera_rig,
)

@pytest.fixture(autouse=True)
def enable_inspection_tools(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv('MORPHOMESH_INCLUDE_INSPECTION_TOOLS', '1')

class TestWhitespacePaddedEnums:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('padded_vp', [
        '  front  ',
        '  THREE_QUARTER  ',
        '  side_left  ',
        '   turntable   ',
        '   bottom   ',
    ])
    async def test_whitespace_padded_viewpoints_normalized_safely(self, padded_vp: str):
        res = await morphomesh_setup_inspector_camera_rig(viewpoint=padded_vp)
        assert isinstance(res, dict)
        assert res.get('status') == 'success'
        assert 'location' in res or 'camera_location' in res

    @pytest.mark.asyncio
    @pytest.mark.parametrize('padded_invalid_vp', [
        '  nadir_flipped  ',
        '  zenith_99  ',
        '  UPWARD_45  ',
        '   diagonal_underneath   ',
    ])
    async def test_whitespace_padded_invalid_viewpoints_rejected(self, padded_invalid_vp: str):
        with pytest.raises(ToolError, match=r'(?i)(viewpoint|validation|invalid|allowed)'):
            await morphomesh_setup_inspector_camera_rig(viewpoint=padded_invalid_vp)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('whitespace_only', [
        ' ',
        '   ',
        '   \t  ',
    ])
    async def test_whitespace_only_viewpoints_rejected(self, whitespace_only: str):
        with pytest.raises(ToolError, match=r'(?i)(viewpoint|empty|validation)'):
            await morphomesh_setup_inspector_camera_rig(viewpoint=whitespace_only)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('padded_shading', [
        '  SOLID  ',
        '  wireframe  ',
        '  MATERIAL  ',
    ])
    async def test_whitespace_padded_shading_modes(self, padded_shading: str):
        res = await morphomesh_capture_viewport(shading_mode=padded_shading)
        assert isinstance(res, dict)
        assert res.get('status') == 'success'

    @pytest.mark.asyncio
    @pytest.mark.parametrize('padded_invalid_shading', [
        '  RAYTRACING  ',
        '  PATH_TRACING  ',
        '  UNLIT_DEBUG  ',
    ])
    async def test_whitespace_padded_invalid_shading_rejected(self, padded_invalid_shading: str):
        with pytest.raises(ToolError, match=r'(?i)(shading_mode|validation|invalid)'):
            await morphomesh_capture_viewport(shading_mode=padded_invalid_shading)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('padded_preset', [
        '  stylized_heroine  ',
        '  REALISTIC_HUMAN  ',
        '  chibi_petite  ',
    ])
    async def test_whitespace_padded_target_presets(self, padded_preset: str):
        res = await morphomesh_critique_visual_quality(target_preset=padded_preset)
        assert isinstance(res, dict)
        assert res.get('status') == 'success'

    @pytest.mark.asyncio
    @pytest.mark.parametrize('padded_invalid_preset', [
        '  alien_hydra  ',
        '  draconic_quadruped  ',
        '  spider_titan  ',
    ])
    async def test_whitespace_padded_invalid_preset_rejected(self, padded_invalid_preset: str):
        with pytest.raises(ToolError, match=r'(?i)(target_preset|validation|invalid)'):
            await morphomesh_critique_visual_quality(target_preset=padded_invalid_preset)

class TestInvalidStringTypes:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('bad_vp', [123, None, {'view': 'front'}, ['front'], 45.6, True])
    async def test_setup_camera_invalid_viewpoint_types(self, bad_vp: Any):
        with pytest.raises(ToolError):
            await morphomesh_setup_inspector_camera_rig(viewpoint=bad_vp)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('bad_name', [123, None, {'name': 'cam'}, ['cam'], False])
    async def test_setup_camera_invalid_camera_name_types(self, bad_name: Any):
        # Direct async invocation raises ToolError if None or AttributeError if non-str lacking .strip()
        with pytest.raises((ToolError, AttributeError)):
            await morphomesh_setup_inspector_camera_rig(camera_name=bad_name)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('bad_shading', [123, None, {'mode': 'SOLID'}, ['SOLID'], 9.9])
    async def test_capture_viewport_invalid_shading_types(self, bad_shading: Any):
        with pytest.raises(ToolError):
            await morphomesh_capture_viewport(shading_mode=bad_shading)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('bad_color', [123, None, {'color': 'RANDOM'}, ['RANDOM'], True])
    async def test_capture_viewport_invalid_color_types(self, bad_color: Any):
        with pytest.raises(ToolError):
            await morphomesh_capture_viewport(color_type=bad_color)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('bad_name', [123, None, {'name': 'cam'}, ['cam']])
    async def test_capture_viewport_invalid_camera_name_types(self, bad_name: Any):
        with pytest.raises((ToolError, AttributeError)):
            await morphomesh_capture_viewport(camera_name=bad_name)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('bad_preset', [123, None, {'preset': 'heroine'}, ['stylized_heroine'], 42.0])
    async def test_critique_invalid_target_preset_types(self, bad_preset: Any):
        with pytest.raises(ToolError):
            await morphomesh_critique_visual_quality(target_preset=bad_preset)

class TestExtremeFocalLengths:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('sub_min_focal', [0.0, 5.0, 9.9, 9.999, 1e-6])
    async def test_focal_length_below_minimum_rejected(self, sub_min_focal: float):
        with pytest.raises(ToolError, match=r'(?i)(focal_length|validation|between 10.0 and 300.0)'):
            await morphomesh_setup_inspector_camera_rig(focal_length=sub_min_focal)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('negative_focal', [-0.0001, -1.0, -10.0, -50.0, -300.0, -999.0])
    async def test_negative_focal_length_rejected(self, negative_focal: float):
        with pytest.raises(ToolError, match=r'(?i)(focal_length|validation|between 10.0 and 300.0)'):
            await morphomesh_setup_inspector_camera_rig(focal_length=negative_focal)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('ultra_tele_focal', [300.01, 301.0, 400.0, 500.0, 1000.0, 1e6])
    async def test_focal_length_above_maximum_rejected(self, ultra_tele_focal: float):
        with pytest.raises(ToolError, match=r'(?i)(focal_length|validation|between 10.0 and 300.0)'):
            await morphomesh_setup_inspector_camera_rig(focal_length=ultra_tele_focal)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('special_float', [float('inf'), float('-inf')])
    async def test_infinite_focal_length_rejected(self, special_float: float):
        with pytest.raises(ToolError):
            await morphomesh_setup_inspector_camera_rig(focal_length=special_float)

class TestClearanceToleranceBounds:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('neg_tol', [
        -0.0001,
        -0.001,
        -0.005,
        -0.05,
        -0.1,
        -1.0,
        -100.0,
        float('-inf'),
    ])
    async def test_negative_clearance_tolerance_rejected(self, neg_tol: float):
        with pytest.raises(ToolError, match=r'(?i)(clearance_tolerance|validation|non-negative)'):
            await morphomesh_critique_visual_quality(clearance_tolerance=neg_tol)

class TestProtocolCallToolFuzzing:
    @pytest.mark.asyncio
    @pytest.mark.parametrize('bad_payload', [
        {'viewpoint': 999},
        {'viewpoint': ''},
        {'viewpoint': 'zenith_invalid'},
        {'focal_length': -10.0},
        {'focal_length': 500.0},
        {'camera_name': ''},
        {'camera_name': 123},
        {'target_center': [1, 2]},
    ])
    async def test_call_tool_setup_camera_bad_payloads(self, bad_payload: Dict[str, Any]):
        with pytest.raises(ToolError):
            await mcp.call_tool('morphomesh_setup_inspector_camera_rig', bad_payload)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('bad_payload', [
        {'shading_mode': 999},
        {'shading_mode': 'RAYTRACING'},
        {'color_type': 'NEON'},
        {'resolution': [0, 0]},
        {'camera_name': ''},
        {'camera_name': 123},
    ])
    async def test_call_tool_capture_viewport_bad_payloads(self, bad_payload: Dict[str, Any]):
        with pytest.raises(ToolError):
            await mcp.call_tool('morphomesh_capture_viewport', bad_payload)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('bad_payload', [
        {'target_preset': 999},
        {'target_preset': 'alien_hydra'},
        {'clearance_tolerance': -0.5},
        {'character_name': '', 'target_object': ''},
    ])
    async def test_call_tool_critique_bad_payloads(self, bad_payload: Dict[str, Any]):
        with pytest.raises(ToolError):
            await mcp.call_tool('morphomesh_critique_visual_quality', bad_payload)
