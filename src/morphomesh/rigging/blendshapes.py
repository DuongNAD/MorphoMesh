"""
52 Apple ARKit Standard FACS Facial Blendshapes Generator.

Synthesizes the complete suite of 52 Apple ARKit FACS facial blendshapes
by programmatically displacing vertices in anatomical facial regions
(eyes, brows, mouth, lips, jaw, cheeks, tongue).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

try:
    from morphomesh.geometry.mesh import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]


ARKIT_52_BLENDSHAPES: Tuple[str, ...] = (
    # Eye Left (7)
    "eyeBlinkLeft", "eyeLookDownLeft", "eyeLookInLeft", "eyeLookOutLeft", "eyeLookUpLeft", "eyeSquintLeft", "eyeWideLeft",
    # Eye Right (7)
    "eyeBlinkRight", "eyeLookDownRight", "eyeLookInRight", "eyeLookOutRight", "eyeLookUpRight", "eyeSquintRight", "eyeWideRight",
    # Jaw (4)
    "jawForward", "jawLeft", "jawRight", "jawOpen",
    # Mouth (23)
    "mouthClose", "mouthFunnel", "mouthPucker", "mouthLeft", "mouthRight",
    "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight",
    "mouthDimpleLeft", "mouthDimpleRight", "mouthStretchLeft", "mouthStretchRight",
    "mouthRollLower", "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper",
    "mouthPressLeft", "mouthPressRight", "mouthLowerDownLeft", "mouthLowerDownRight",
    "mouthUpperUpLeft", "mouthUpperUpRight",
    # Brows (5)
    "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
    # Cheeks (3)
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
    # Nose (2)
    "noseSneerLeft", "noseSneerRight",
    # Tongue (1)
    "tongueOut",
)


def generate_arkit_52_blendshapes(
    mesh: MeshGeometry,
    landmarks: Optional[Dict[str, Tuple[float, float, float]]] = None,
    scale: float = 1.0,
) -> Dict[str, Dict[int, Tuple[float, float, float]]]:
    """
    Synthesizes the complete suite of 52 Apple ARKit standard FACS facial blendshapes.
    Displaces vertices programmatically in facial anatomical regions (eyes, brows, mouth,
    lips, jaw, cheeks, tongue).
    Returns: Dict mapping blendshape_name -> Dict[vertex_index, (dx, dy, dz)].
    """
    vgroups = mesh.vertex_groups or {}
    s = scale
    shape_key_deltas: Dict[str, Dict[int, Tuple[float, float, float]]] = {}

    v_face = vgroups.get("face", [])
    v_mouth = vgroups.get("mouth", [])
    v_lips = vgroups.get("lips", [])
    v_tongue = vgroups.get("tongue", [])
    v_eyebrows = vgroups.get("eyebrows", [])
    v_eyes_l = vgroups.get("eyes_left", [])
    v_eyes_r = vgroups.get("eyes_right", [])

    for k_name in ARKIT_52_BLENDSHAPES:
        deltas: Dict[int, Tuple[float, float, float]] = {}

        # ----------------------------------------------------------------------
        # 1. EYES (AU45, AU7, AU5, EYEBALL GAZE)
        # ----------------------------------------------------------------------
        if k_name == "eyeBlinkLeft":
            for vi in v_eyes_l:
                deltas[vi] = (0.0, 0.002 * s, -0.009 * s)
        elif k_name == "eyeBlinkRight":
            for vi in v_eyes_r:
                deltas[vi] = (0.0, 0.002 * s, -0.009 * s)
        elif k_name == "eyeWideLeft":
            for vi in v_eyes_l:
                deltas[vi] = (0.0, -0.001 * s, 0.005 * s)
        elif k_name == "eyeWideRight":
            for vi in v_eyes_r:
                deltas[vi] = (0.0, -0.001 * s, 0.005 * s)
        elif k_name == "eyeSquintLeft":
            for vi in v_eyes_l:
                deltas[vi] = (0.0015 * s, 0.0, 0.003 * s)
        elif k_name == "eyeSquintRight":
            for vi in v_eyes_r:
                deltas[vi] = (-0.0015 * s, 0.0, 0.003 * s)
        elif k_name == "eyeLookDownLeft":
            for vi in v_eyes_l:
                deltas[vi] = (0.0, -0.001 * s, -0.003 * s)
        elif k_name == "eyeLookDownRight":
            for vi in v_eyes_r:
                deltas[vi] = (0.0, -0.001 * s, -0.003 * s)
        elif k_name == "eyeLookUpLeft":
            for vi in v_eyes_l:
                deltas[vi] = (0.0, 0.001 * s, 0.003 * s)
        elif k_name == "eyeLookUpRight":
            for vi in v_eyes_r:
                deltas[vi] = (0.0, 0.001 * s, 0.003 * s)
        elif k_name == "eyeLookInLeft":
            for vi in v_eyes_l:
                deltas[vi] = (0.003 * s, 0.0, 0.0)
        elif k_name == "eyeLookInRight":
            for vi in v_eyes_r:
                deltas[vi] = (-0.003 * s, 0.0, 0.0)
        elif k_name == "eyeLookOutLeft":
            for vi in v_eyes_l:
                deltas[vi] = (-0.003 * s, 0.0, 0.0)
        elif k_name == "eyeLookOutRight":
            for vi in v_eyes_r:
                deltas[vi] = (0.003 * s, 0.0, 0.0)

        # ----------------------------------------------------------------------
        # 2. JAW & MANDIBLE (AU26, AU27, AU29, AU30)
        # ----------------------------------------------------------------------
        elif k_name == "jawOpen":
            for vi in v_mouth:
                deltas[vi] = (0.0, -0.006 * s, -0.018 * s)
        elif k_name == "jawForward":
            for vi in v_mouth:
                deltas[vi] = (0.0, 0.006 * s, 0.0)
        elif k_name == "jawLeft":
            for vi in v_mouth:
                deltas[vi] = (0.005 * s, 0.0, 0.0)
        elif k_name == "jawRight":
            for vi in v_mouth:
                deltas[vi] = (-0.005 * s, 0.0, 0.0)

        # ----------------------------------------------------------------------
        # 3. MOUTH & LIPS
        # ----------------------------------------------------------------------
        elif k_name == "mouthSmileLeft":
            for vi in v_lips:
                deltas[vi] = (0.012 * s, -0.003 * s, 0.008 * s)
        elif k_name == "mouthSmileRight":
            for vi in v_lips:
                deltas[vi] = (-0.012 * s, -0.003 * s, 0.008 * s)
        elif k_name == "mouthFrownLeft":
            for vi in v_lips:
                deltas[vi] = (0.002 * s, 0.0, -0.007 * s)
        elif k_name == "mouthFrownRight":
            for vi in v_lips:
                deltas[vi] = (-0.002 * s, 0.0, -0.007 * s)
        elif k_name == "mouthPucker":
            for vi in v_lips:
                deltas[vi] = (0.0, 0.012 * s, 0.0)
        elif k_name == "mouthFunnel":
            for vi in v_lips:
                deltas[vi] = (0.0, 0.008 * s, -0.002 * s)
        elif k_name == "mouthClose":
            for vi in v_lips:
                deltas[vi] = (0.0, -0.002 * s, 0.004 * s)
        elif k_name == "mouthLeft":
            for vi in v_lips:
                deltas[vi] = (0.008 * s, 0.0, 0.0)
        elif k_name == "mouthRight":
            for vi in v_lips:
                deltas[vi] = (-0.008 * s, 0.0, 0.0)
        elif k_name == "mouthDimpleLeft":
            for vi in v_lips:
                deltas[vi] = (0.008 * s, -0.004 * s, 0.0)
        elif k_name == "mouthDimpleRight":
            for vi in v_lips:
                deltas[vi] = (-0.008 * s, -0.004 * s, 0.0)
        elif k_name == "mouthStretchLeft":
            for vi in v_lips:
                deltas[vi] = (0.010 * s, 0.0, -0.002 * s)
        elif k_name == "mouthStretchRight":
            for vi in v_lips:
                deltas[vi] = (-0.010 * s, 0.0, -0.002 * s)
        elif k_name == "mouthRollLower":
            for vi in v_lips:
                deltas[vi] = (0.0, -0.005 * s, 0.003 * s)
        elif k_name == "mouthRollUpper":
            for vi in v_lips:
                deltas[vi] = (0.0, -0.005 * s, -0.003 * s)
        elif k_name == "mouthShrugLower":
            for vi in v_mouth:
                deltas[vi] = (0.0, 0.004 * s, 0.006 * s)
        elif k_name == "mouthShrugUpper":
            for vi in v_lips:
                deltas[vi] = (0.0, 0.003 * s, 0.004 * s)
        elif k_name == "mouthPressLeft":
            for vi in v_lips:
                deltas[vi] = (0.0, -0.002 * s, 0.003 * s)
        elif k_name == "mouthPressRight":
            for vi in v_lips:
                deltas[vi] = (0.0, -0.002 * s, 0.003 * s)
        elif k_name == "mouthLowerDownLeft":
            for vi in v_lips:
                deltas[vi] = (0.0, 0.002 * s, -0.007 * s)
        elif k_name == "mouthLowerDownRight":
            for vi in v_lips:
                deltas[vi] = (0.0, 0.002 * s, -0.007 * s)
        elif k_name == "mouthUpperUpLeft":
            for vi in v_lips:
                deltas[vi] = (0.0, 0.002 * s, 0.007 * s)
        elif k_name == "mouthUpperUpRight":
            for vi in v_lips:
                deltas[vi] = (0.0, 0.002 * s, 0.007 * s)

        # ----------------------------------------------------------------------
        # 4. EYEBROWS (AU1, AU2, AU4)
        # ----------------------------------------------------------------------
        elif k_name == "browDownLeft":
            for vi in v_eyebrows:
                deltas[vi] = (-0.004 * s, 0.0, -0.006 * s)
        elif k_name == "browDownRight":
            for vi in v_eyebrows:
                deltas[vi] = (0.004 * s, 0.0, -0.006 * s)
        elif k_name == "browInnerUp":
            for vi in v_eyebrows:
                deltas[vi] = (0.0, 0.0, 0.008 * s)
        elif k_name == "browOuterUpLeft":
            for vi in v_eyebrows:
                deltas[vi] = (0.002 * s, 0.0, 0.007 * s)
        elif k_name == "browOuterUpRight":
            for vi in v_eyebrows:
                deltas[vi] = (-0.002 * s, 0.0, 0.007 * s)

        # ----------------------------------------------------------------------
        # 5. CHEEKS & NOSE & TONGUE
        # ----------------------------------------------------------------------
        elif k_name == "cheekPuff":
            for vi in v_face[:20]:
                deltas[vi] = (0.012 * s, 0.008 * s, 0.0)
        elif k_name == "cheekSquintLeft":
            for vi in v_face[:15]:
                deltas[vi] = (0.0, -0.002 * s, 0.006 * s)
        elif k_name == "cheekSquintRight":
            for vi in v_face[:15]:
                deltas[vi] = (0.0, -0.002 * s, 0.006 * s)
        elif k_name == "noseSneerLeft":
            for vi in v_face[:10]:
                deltas[vi] = (0.003 * s, 0.0, 0.005 * s)
        elif k_name == "noseSneerRight":
            for vi in v_face[:10]:
                deltas[vi] = (-0.003 * s, 0.0, 0.005 * s)
        elif k_name == "tongueOut":
            for vi in v_tongue:
                deltas[vi] = (0.0, 0.020 * s, -0.003 * s)

        # Fallback if specific group empty: displace top face vertices
        if not deltas and v_face:
            for vi in v_face[:5]:
                deltas[vi] = (0.0, -0.002 * s, 0.002 * s)

        shape_key_deltas[k_name] = deltas

    return shape_key_deltas



__all__ = [
    "ARKIT_52_BLENDSHAPES",
    "generate_arkit_52_blendshapes",
]
