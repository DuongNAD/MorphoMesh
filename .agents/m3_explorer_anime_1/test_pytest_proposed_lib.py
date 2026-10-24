"""
test_pytest_proposed_lib.py
Pytest suite verifying proposed_action_library.py offline compatibility.
"""

import sys
sys.path.append(r'E:\tool\mcp\MorphoMesh\.agents\m3_explorer_anime_1')

import proposed_action_library as lib

def test_canonical_actions_fixture_conformance():
    actions = lib.get_canonical_action_definitions()
    assert len(actions) == 4
    for name in lib.ACTION_NAMES:
        assert name in actions
        act = actions[name]
        assert act.name == name
        assert act.frame_end > act.frame_start
        assert act.fps >= 30
        assert len(act.curves) > 0
        assert act.duration_seconds > 0.0

def test_metadata_registry_conformance():
    for name in lib.ACTION_NAMES:
        assert name in lib.ACTION_METADATA_REGISTRY
        meta = lib.ACTION_METADATA_REGISTRY[name]
        assert meta.fps == 30
        assert meta.total_frames >= 32
        assert meta.duration_seconds >= 1.0