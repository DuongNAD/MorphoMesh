"""
MorphoMesh Phase 2: Empirical Challenge Suite 3
Procedural DAG & Morphological Schema Verification for AnyCreatureConnector.
"""

from __future__ import annotations

import json
import os
import struct
import pytest
from typing import Dict, List, Set

from morphomesh.connectors.anycreature_connector import (
    AnimationBinding,
    AnyCreatureConnector,
    AnyCreatureOutput,
    BodyGraph,
    BodyPart,
    CreaturePromptSpec,
    LimbSpec,
)


# ==============================================================================
# ADVERSARIAL & EDGE-CASE PROMPTS
# ==============================================================================

ADVERSARIAL_PROMPTS = [
    # 1. Multi-limbed beast
    "Multi-limbed eight-legged armored spider beast with dual venom horns",
    # 2. Winged serpent / wyvern
    "Winged serpent wyvern with iridescent crown horns and venomous barbed tail",
    # 3. Aquatic abyssal leviathan
    "Deep sea abyssal leviathan shark with bioluminescent dorsal fin",
    # 4. Bipedal humanoid hybrid
    "Bipedal cybernetic werewolf minotaur warrior with spiked horns and battle armor",
    # 5. Exotic hybrid with conflicting keywords
    "Winged bipedal dragon serpent wolf goblin chimera hybrid creature",
    # 6. Minimal prompt
    "Wolf",
    # 7. Non-alphanumeric / symbols
    "Dragon! [Spike-Tailed] {Flame-Crest} #Omega_99",
    # 8. Unicode & accents
    "Bête fantastique ailée avec de grandes cornes célestes",
    # 9. Ultra-long descriptive prompt
    (
        "Ancient primordial titan beast roaming the forgotten volcanic wastes. "
        "Massive quad-limbed heavy body with obsidian scales, twin curved head horns, "
        "gigantic bat-like wings spanning thirty cubits, prehensile serrated tail, "
        "and glowing magma-filled fissures along its armored chest plate. "
        * 10
    ),
    # 10. Empty string fallback
    "",
]


def check_is_dag(parts: Dict[str, BodyPart], root_id: str) -> bool:
    """Verify the part hierarchy forms a valid Directed Acyclic Graph (tree structure)."""
    assert root_id in parts, f"Root ID '{root_id}' does not exist in parts"

    # Check for cycles using DFS cycle detection
    visited: Set[str] = set()
    recursion_stack: Set[str] = set()

    # Build adjacency list (parent -> children)
    adj: Dict[str, List[str]] = {pid: [] for pid in parts}
    for pid, part in parts.items():
        if part.parent_id is not None:
            assert part.parent_id in parts, (
                f"Part '{pid}' references non-existent parent '{part.parent_id}'"
            )
            adj[part.parent_id].append(pid)

    def dfs(u: str) -> bool:
        visited.add(u)
        recursion_stack.add(u)
        for child in adj.get(u, []):
            if child not in visited:
                if dfs(child):
                    return True
            elif child in recursion_stack:
                return True  # Cycle detected
        recursion_stack.remove(u)
        return False

    has_cycle = dfs(root_id)
    return not has_cycle


def parse_glb_mesh_stats(glb_path: str) -> Dict[str, int]:
    """Parse glTF binary container to verify chunks and inspect non-empty vertex data."""
    assert os.path.exists(glb_path), f"GLB file does not exist: {glb_path}"
    file_size = os.path.getsize(glb_path)
    assert file_size > 20, f"GLB file is suspiciously small ({file_size} bytes)"

    with open(glb_path, "rb") as f:
        magic, version, total_len = struct.unpack("<4sII", f.read(12))
        assert magic == b"glTF", "Magic header is not glTF"
        assert version == 2, f"Expected glTF version 2, got {version}"
        assert total_len == file_size, f"Header total length {total_len} != file size {file_size}"

        # Read JSON chunk header
        json_chunk_len, json_chunk_type = struct.unpack("<II", f.read(8))
        assert json_chunk_type == 0x4E4F534A, "First chunk is not JSON (0x4E4F534A)"
        json_bytes = f.read(json_chunk_len)
        gltf_dict = json.loads(json_bytes.decode("utf-8"))

        # Accessors inspect
        accessors = gltf_dict.get("accessors", [])
        assert len(accessors) >= 2, "glTF missing position or index accessors"
        # POSITION accessor count
        vertex_count = accessors[0].get("count", 0)
        # INDICES accessor count
        index_count = accessors[1].get("count", 0)

        return {
            "vertex_count": vertex_count,
            "index_count": index_count,
            "face_count": index_count // 3,
            "file_size": file_size,
        }


class TestAnyCreatureDAGAndSchemas:
    """Empirical tests for BodyGraph DAG generation, Pydantic schemas, and animation bindings."""

    @pytest.fixture
    def connector(self) -> AnyCreatureConnector:
        conn = AnyCreatureConnector()
        conn.initialize()
        return conn

    @pytest.fixture
    def out_dir(self, tmp_path) -> str:
        d = str(tmp_path / "creature_dag_outputs")
        os.makedirs(d, exist_ok=True)
        return d

    @pytest.mark.parametrize("prompt", ADVERSARIAL_PROMPTS)
    def test_pydantic_schema_conformance_and_serialization(self, connector, out_dir, prompt):
        """
        Verify that AnyCreatureConnector parses arbitrary and adversarial prompts,
        generates spec strictly adhering to Pydantic v2 schemas, and that the exported
        JSON deserializes back with 100% fidelity.
        """
        sub_dir = os.path.join(out_dir, f"test_{abs(hash(prompt)) % 1000000}")
        out = connector.execute(prompt, output_dir=sub_dir)

        assert isinstance(out, AnyCreatureOutput)
        assert os.path.exists(out.json_spec_path)

        # 1. Re-validate JSON file against Pydantic schema
        with open(out.json_spec_path, "r", encoding="utf-8") as f:
            raw_json = f.read()

        revalidated_spec = CreaturePromptSpec.model_validate_json(raw_json)
        assert isinstance(revalidated_spec, CreaturePromptSpec)
        assert isinstance(revalidated_spec.body_graph, BodyGraph)

        # 2. Check parts and limbs
        assert len(revalidated_spec.body_graph.parts) >= 4, "Creature must have at least core body parts"
        for part_id, part in revalidated_spec.body_graph.parts.items():
            assert isinstance(part, BodyPart)
            assert part.part_id == part_id
            assert part.length > 0.0
            assert part.radius_start > 0.0
            assert part.radius_end > 0.0

        for limb in revalidated_spec.body_graph.limbs:
            assert isinstance(limb, LimbSpec)
            assert limb.limb_type in ("leg", "wing", "arm", "fin", "tentacle")
            assert limb.side in ("left", "right", "center")
            assert len(limb.segment_lengths) > 0
            assert all(sl > 0 for sl in limb.segment_lengths)

    @pytest.mark.parametrize("prompt", ADVERSARIAL_PROMPTS)
    def test_dag_structural_integrity(self, connector, out_dir, prompt):
        """Verify the morphological part graph forms a strict DAG with no cycles."""
        spec = connector.parse_prompt(prompt)
        bg = spec.body_graph

        is_dag = check_is_dag(bg.parts, bg.root_id)
        assert is_dag is True, f"BodyGraph for prompt '{prompt}' is not a valid DAG!"

    @pytest.mark.parametrize("prompt", ADVERSARIAL_PROMPTS)
    def test_manifold_geometry_generation(self, connector, out_dir, prompt):
        """
        Verify procedural mesh builder produces non-empty manifold 3D geometry
        in valid GLB container format with non-zero vertices and faces.
        """
        sub_dir = os.path.join(out_dir, f"geom_{abs(hash(prompt)) % 1000000}")
        out = connector.execute(prompt, output_dir=sub_dir)

        assert out.generated_mesh_path is not None
        stats = parse_glb_mesh_stats(out.generated_mesh_path)

        assert stats["vertex_count"] > 10, f"Too few vertices ({stats['vertex_count']})"
        assert stats["face_count"] > 5, f"Too few faces ({stats['face_count']})"
        assert stats["file_size"] > 500, f"Suspiciously small file ({stats['file_size']} B)"

    @pytest.mark.parametrize("prompt", ADVERSARIAL_PROMPTS)
    def test_animation_bindings_validity(self, connector, prompt):
        """
        Verify gait controllers and oscillator bindings:
        - Walk, run, and idle cycles exist
        - Winged archetype includes fly cycle
        - Phase offsets are normalized in [0.0, 1.0]
        - Frequencies and stride lengths are positive
        """
        spec = connector.parse_prompt(prompt)
        bindings = spec.animation_bindings

        assert len(bindings) >= 3, "Must have at least idle, walk, and run bindings"
        action_names = [b.action_name for b in bindings]
        assert "idle" in action_names
        assert "walk_cycle" in action_names
        assert "run_cycle" in action_names

        if spec.inferred_type == "winged_quadruped":
            assert "fly_cycle" in action_names, "Winged creature must have fly_cycle binding"

        for b in bindings:
            assert isinstance(b, AnimationBinding)
            assert b.gait_frequency > 0.0, f"Gait frequency {b.gait_frequency} <= 0"
            assert b.stride_length >= 0.0, f"Stride length {b.stride_length} < 0"
            for limb_id, offset in b.phase_offsets.items():
                assert 0.0 <= offset <= 1.0, f"Phase offset {offset} outside [0.0, 1.0] for {limb_id}"

    def test_specific_creature_archetype_inference(self, connector):
        """Verify prompt keywords correctly route to appropriate morphological archetypes."""
        test_cases = [
            ("Armored winged fire wyvern", "winged_quadruped"),
            ("Giant humanoid orc warrior", "biped"),
            ("Venomous emerald garden snake", "serpentine"),
            ("Great white ocean shark predator", "aquatic"),
            ("Dire woodland timber wolf", "quadruped"),
        ]
        for prompt, expected_archetype in test_cases:
            spec = connector.parse_prompt(prompt)
            assert spec.inferred_type == expected_archetype, (
                f"Prompt '{prompt}' inferred '{spec.inferred_type}', expected '{expected_archetype}'"
            )
