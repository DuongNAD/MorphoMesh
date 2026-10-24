"""
Unit and integration tests for Meshy Rigging and Animation Library support,
as well as local Blender rigging fixes in MorphoMesh.
"""
import os
import json
import pytest
from unittest.mock import MagicMock, patch

from morphomesh.connectors.meshy_connector import (
    MeshyConnector,
    MeshyConfig,
    MeshyRiggingInput,
    MeshyAnimationInput,
    CURATED_ANIMATIONS,
)
from morphomesh.server import (
    morphomesh_list_animations,
    morphomesh_auto_rig,
    morphomesh_animate_asset,
)
from morphomesh.blender_bridge import BlenderBridge


# ==============================================================================
# 1. ANIMATION LIBRARY TESTS
# ==============================================================================

def test_list_animation_library_offline_fallback():
    connector = MeshyConnector(config=MeshyConfig(mode="mock"))
    res = connector.list_animation_library()
    assert len(res) >= len(CURATED_ANIMATIONS)
    first = res[0]
    assert first.action_id is not None
    assert first.name
    assert first.category


def test_list_animation_library_filtering_category():
    connector = MeshyConnector(config=MeshyConfig(mode="mock"))
    fighting_res = connector.list_animation_library(category="Fighting")
    assert len(fighting_res) > 0
    for anim in fighting_res:
        assert anim.category.lower() == "fighting"


def test_list_animation_library_search():
    connector = MeshyConnector(config=MeshyConfig(mode="mock"))
    search_res = connector.list_animation_library(search="dance")
    assert len(search_res) > 0
    for anim in search_res:
        assert "dance" in anim.name.lower() or "dance" in anim.category.lower() or "dance" in anim.key.lower()


# ==============================================================================
# 2. RIGGING TESTS
# ==============================================================================

def test_rig_asset_offline_mock(tmp_path):
    dummy_glb = tmp_path / "test.glb"
    dummy_glb.write_bytes(b"glTF" + b"\x00" * 100)

    connector = MeshyConnector(config=MeshyConfig(mode="mock"))
    rig_input = MeshyRiggingInput(
        model_path=str(dummy_glb),
        height_meters=1.75
    )
    result = connector.rig_asset(rig_input)
    assert result.status == "SUCCEEDED"
    assert "mock" in result.rig_task_id
    assert result.rigged_character_glb_path is not None
    assert os.path.exists(result.rigged_character_glb_path)
    assert len(result.basic_animations) > 0


def test_rig_asset_with_api_mock(monkeypatch, tmp_path):
    connector = MeshyConnector(config=MeshyConfig(api_key="msy_test_key_12345", mode="api"))

    monkeypatch.setattr(connector, "_post_json_task", lambda url, payload, key: "rig_task_999")
    monkeypatch.setattr(connector, "_poll_task", lambda url, key, timeout=None: {
        "id": "rig_task_999",
        "status": "SUCCEEDED",
        "result": {
            "rigged_character_glb_url": "https://assets.meshy.ai/rigged.glb",
            "basic_animations": {
                "walking": "https://assets.meshy.ai/walk.fbx"
            }
        }
    })
    monkeypatch.setattr(connector, "_download_file", lambda url, dest: dest)

    res = connector.rig_asset(MeshyRiggingInput(
        model_url="https://assets.meshy.ai/model.glb",
        output_dir=str(tmp_path)
    ))
    assert res.rig_task_id == "rig_task_999"
    assert res.status == "SUCCEEDED"
    assert res.basic_animation_urls.get("walking") == "https://assets.meshy.ai/walk.fbx"


# ==============================================================================
# 3. ANIMATION RETARGETING TESTS
# ==============================================================================

def test_animate_asset_offline_mock(tmp_path):
    connector = MeshyConnector(config=MeshyConfig(mode="mock"))
    anim_input = MeshyAnimationInput(
        rig_task_id="rig_mock_123",
        action_id=0,
        output_dir=str(tmp_path)
    )
    result = connector.animate_asset(anim_input)
    assert result.status == "SUCCEEDED"
    assert "mock" in result.animation_task_id
    assert result.animation_glb_path is not None
    assert os.path.exists(result.animation_glb_path)


def test_animate_asset_with_api_mock(monkeypatch, tmp_path):
    connector = MeshyConnector(config=MeshyConfig(api_key="msy_test_key_12345", mode="api"))

    monkeypatch.setattr(connector, "_post_json_task", lambda url, payload, key: "anim_task_777")
    monkeypatch.setattr(connector, "_poll_task", lambda url, key, timeout=None: {
        "id": "anim_task_777",
        "status": "SUCCEEDED",
        "result": {
            "animation_glb_url": "https://assets.meshy.ai/animated.glb"
        }
    })
    monkeypatch.setattr(connector, "_download_file", lambda url, dest: dest)

    res = connector.animate_asset(MeshyAnimationInput(
        rig_task_id="rig_task_999",
        action_id=0,
        output_dir=str(tmp_path)
    ))
    assert res.animation_task_id == "anim_task_777"
    assert res.status == "SUCCEEDED"
    assert res.animation_glb_path is not None


# ==============================================================================
# 4. FASTMCP SERVER TOOLS INTEGRATION
# ==============================================================================

@pytest.mark.asyncio
async def test_server_list_animations_tool():
    res = await morphomesh_list_animations(category="WalkAndRun", limit=10)
    assert res["total_count"] > 0
    assert len(res["animations"]) <= 10
    for a in res["animations"]:
        assert a["category"].lower() == "walkandrun"


@pytest.mark.asyncio
async def test_server_auto_rig_meshy_tool(tmp_path):
    dummy_glb = tmp_path / "server_test.glb"
    dummy_glb.write_bytes(b"glTF" + b"\x00" * 100)

    res = await morphomesh_auto_rig(
        input_mesh_path=str(dummy_glb),
        backend="meshy",
        height_meters=1.8
    )
    assert res["status"] in ("success", "mock_success")
    assert "rig_task_id" in res
    assert res["creature_type"] == "biped"
    assert os.path.exists(res["downloaded_glb_path"])


@pytest.mark.asyncio
async def test_server_animate_asset_tool():
    res = await morphomesh_animate_asset(
        rig_task_id="rig_mock_123",
        action_id=0,
    )
    assert res["status"] in ("success", "mock_success")
    assert "animation_task_id" in res
    assert res["action_id"] == 0
    assert os.path.exists(res["animated_glb_path"])


# ==============================================================================
# 5. BLENDER LOCAL RIGGING FIX VERIFICATION
# ==============================================================================

def test_blender_headless_rigging_script_contains_fixes(tmp_path):
    bridge = BlenderBridge()
    script = bridge._generate_headless_script("rig", {
        "mesh_path": "/fake/model.obj",
        "rig_type": "biped",
        "output_path": str(tmp_path / "rigged.fbx")
    })
    
    # 1. Automatic weighting instead of naive 1/d^2 distance
    assert "type='ARMATURE_AUTO'" in script
    # 2. Dynamic mesh bounding box calculation
    assert "bound_box" in script
    # 3. Keyframe insertion for idle animation
    assert "keyframe_insert" in script
    # 4. Actual FBX export
    assert "export_scene.fbx" in script
