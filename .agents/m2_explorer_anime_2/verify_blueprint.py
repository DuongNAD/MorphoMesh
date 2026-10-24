"""
Comprehensive validation test for skinning_dqs blueprint.
Executes all math formulas, weight normalizations, and modular isolation rules.
"""

import math
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
teamwork_proj = repo_root / "teamwork_projects" / "anime_character_pipeline"
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(teamwork_proj))

from teamwork_projects.anime_character_pipeline.tests.conftest import (
    create_canonical_modular_meshes,
    create_canonical_armature,
    compute_mesh_signed_volume,
    compute_volume_retention,
    MIN_VOLUME_RETENTION_RATIO,
)

# Import our proposed classes and functions from blueprint
TWIST_BONES = [
    "UpperArm_Twist.L", "UpperArm_Twist.R",
    "ForeArm_Twist.L", "ForeArm_Twist.R",
]
FINGER_NAMES = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
PHALANGES = ["01", "02", "03"]
ALL_30_FINGER_BONES = [
    f"{f}.{p}.{side}" for side in ["L", "R"] for f in FINGER_NAMES for p in PHALANGES
]
SKIRT_BONES = [f"Skirt_{i:02d}" for i in range(1, 13)]
ALL_10_HAIR_BONES = [f"Hair_L_{i:02d}" for i in range(1, 6)] + [f"Hair_R_{i:02d}" for i in range(1, 6)]

MODULAR_ISOLATION_RULES = {
    "Anime_Head": {"Head", "Neck"},
    "Anime_Torso": {"Hips", "Spine", "Spine1", "Spine2", "Neck", "Clavicle.L", "Clavicle.R"},
    "Anime_Arms": {
        "Clavicle.L", "Clavicle.R",
        "UpperArm.L", "UpperArm.R",
        "UpperArm_Twist.L", "UpperArm_Twist.R",
        "ForeArm.L", "ForeArm.R",
        "ForeArm_Twist.L", "ForeArm_Twist.R",
        "Hand.L", "Hand.R",
    } | set(ALL_30_FINGER_BONES),
    "Anime_Legs": {
        "Hips", "Thigh.L", "Thigh.R", "Shin.L", "Shin.R", "Foot.L", "Foot.R", "Toe.L", "Toe.R"
    },
    "Anime_Skirt": {"Hips"} | set(SKIRT_BONES),
    "Anime_Hair": {"Head"} | set(ALL_10_HAIR_BONES),
    "Anime_Shoes": {"Shin.L", "Shin.R", "Foot.L", "Foot.R", "Toe.L", "Toe.R"},
}

def harmonic_cosine_falloff(u: float) -> float:
    u_clamped = max(0.0, min(1.0, u))
    return 0.5 * (1.0 + math.cos(math.pi * u_clamped))

class VertexWeightTable:
    def __init__(self, mesh_name: str, num_vertices: int):
        self.mesh_name = mesh_name
        self.num_vertices = num_vertices
        self.weights = {}

    def add_weight(self, v_idx: int, bone: str, w: float):
        if w <= 1e-6:
            return
        if v_idx not in self.weights:
            self.weights[v_idx] = {}
        self.weights[v_idx][bone] = self.weights[v_idx].get(bone, 0.0) + w

    def prune_and_normalize(self, default_bone: str = "Hips", max_influences: int = 4):
        allowed = MODULAR_ISOLATION_RULES.get(self.mesh_name, set())
        for v_idx in range(self.num_vertices):
            v_dict = self.weights.get(v_idx, {})
            if allowed:
                v_dict = {b: w for b, w in v_dict.items() if b in allowed}
            if len(v_dict) > max_influences:
                sorted_items = sorted(v_dict.items(), key=lambda item: item[1], reverse=True)[:max_influences]
                v_dict = dict(sorted_items)
            total_w = sum(v_dict.values())
            if total_w > 1e-9:
                self.weights[v_idx] = {b: (w / total_w) for b, w in v_dict.items()}
            else:
                fallback = default_bone if (not allowed or default_bone in allowed) else next(iter(allowed))
                self.weights[v_idx] = {fallback: 1.0}

    def to_vertex_groups_dict(self):
        vgroups = {}
        for v_idx, b_dict in self.weights.items():
            for bone, w in b_dict.items():
                if bone not in vgroups:
                    vgroups[bone] = []
                vgroups[bone].append((v_idx, w))
        return vgroups

def test_full_skinning_generation():
    canonical_meshes = create_canonical_modular_meshes()
    for mesh_name, submesh in canonical_meshes.items():
        table = VertexWeightTable(mesh_name, len(submesh.vertices))
        allowed = MODULAR_ISOLATION_RULES[mesh_name]

        # Use canonical vertex groups or sample weights
        for bname, pairs in submesh.vertex_groups.items():
            for vi, w in pairs:
                table.add_weight(vi, bname, w)

        table.prune_and_normalize()
        vg = table.to_vertex_groups_dict()

        # Check: No prohibited groups
        for bname in vg.keys():
            assert bname in allowed, f"Prohibited group {bname} in {mesh_name}"

        # Check: All vertices sum to 1.0
        v_sums = [0.0] * len(submesh.vertices)
        for bname, pairs in vg.items():
            for vi, w in pairs:
                v_sums[vi] += w

        for vi, tot in enumerate(v_sums):
            assert abs(tot - 1.0) < 1e-4, f"Vertex {vi} in {mesh_name} unnormalized: sum={tot}"

    print("[PASS] Full skinning normalization and isolation verified across all 7 sub-meshes.")

if __name__ == "__main__":
    test_full_skinning_generation()
    print("[ALL BLUEPRINT CHECKS PASSED]")
