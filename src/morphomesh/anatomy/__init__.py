"""
MorphoMesh Anatomy: Biomechanical Skeletal Estimation, Stance Classification,
Bone Roll Normalization, and Volumetric Geodesic Biharmonic Skinning Engine.
"""

from morphomesh.anatomy.stance import (
    LocomotorStance,
    StanceClassificationResult,
    classify_locomotor_stance,
)
from morphomesh.anatomy.landmarks import (
    BonyLandmark,
    BonyLandmarks,
    ICRJointPivot,
    compute_bony_landmarks,
    estimate_icr_joint_pivot,
    estimate_icr_joint_pivots,
)
from morphomesh.anatomy.bone_roll import (
    BoneRollResult,
    PreBendResult,
    apply_joint_prebend,
    compute_hinge_plane_normal,
    solve_biomechanical_bone_roll,
    solve_limb_chain_bone_roll_and_prebend,
)
from morphomesh.anatomy.skinning import (
    SkinWeightMap,
    VoxelGrid,
    compute_geodesic_skin_weights,
)

__all__ = [
    "LocomotorStance",
    "StanceClassificationResult",
    "classify_locomotor_stance",
    "BonyLandmark",
    "BonyLandmarks",
    "ICRJointPivot",
    "compute_bony_landmarks",
    "estimate_icr_joint_pivot",
    "estimate_icr_joint_pivots",
    "BoneRollResult",
    "PreBendResult",
    "apply_joint_prebend",
    "compute_hinge_plane_normal",
    "solve_biomechanical_bone_roll",
    "solve_limb_chain_bone_roll_and_prebend",
    "SkinWeightMap",
    "VoxelGrid",
    "compute_geodesic_skin_weights",
]
