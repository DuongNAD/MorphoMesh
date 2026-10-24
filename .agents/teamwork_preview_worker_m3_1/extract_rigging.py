import os

with open("src/morphomesh/human_rigging.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

os.makedirs("src/morphomesh/rigging", exist_ok=True)

# 1. metarig.py
# Lines 106-206: BODY_DEF_BONES, FACIAL_DEF_BONES, ALL_163_DEF_BONES
# Lines 250-335: HumanRigConfig, BoneDefinition, MetarigStructure
# Lines 392-917: get_default_human_landmarks, generate_rigify_human_metarig, align_rigify_metarig_pivots
metarig_body = (
    "".join(lines[105:207])
    + "\n"
    + "".join(lines[249:336])
    + "\n"
    + "".join(lines[391:918])
)

metarig_content = '''"""
Rigify Human Metarig Generator and Landmark Alignment.

Responsible for:
- Authoritative 163 DEF bone definitions (64 body + 99 facial).
- Bone hierarchy, parent-child relations, and joint pre-bends (elbow +Y, knee -Y).
- align_rigify_metarig_pivots: Biological joint rotation axes and instantaneous centers of rotation.
- generate_rigify_human_metarig: Constructing MetarigStructure with all 163 DEF bones.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

try:
    from morphomesh.anatomy.bone_roll import solve_biomechanical_bone_roll
except (ImportError, ModuleNotFoundError):
    try:
        from ...anatomy.bone_roll import solve_biomechanical_bone_roll  # type: ignore[no-redef]
    except Exception:
        solve_biomechanical_bone_roll = None  # type: ignore[assignment]


''' + metarig_body + '''

__all__ = [
    "BODY_DEF_BONES",
    "FACIAL_DEF_BONES",
    "ALL_163_DEF_BONES",
    "HumanRigConfig",
    "BoneDefinition",
    "MetarigStructure",
    "get_default_human_landmarks",
    "generate_rigify_human_metarig",
    "align_rigify_metarig_pivots",
]
'''

with open("src/morphomesh/rigging/metarig.py", "w", encoding="utf-8") as f:
    f.write(metarig_content)
print("Wrote src/morphomesh/rigging/metarig.py, lines:", len(metarig_content.splitlines()))

# 2. anti_pinch.py
# Lines 51-98: _point_to_segment_distance, _CANONICAL_FINGER_MAP, _get_canonical_finger_map
# Lines 340-385: SkinWeightMap
# Lines 924-1306: calculate_anti_pinch_weights
anti_pinch_body = (
    "".join(lines[50:98])
    + "\n"
    + "".join(lines[339:386])
    + "\n"
    + "".join(lines[923:1307])
)

anti_pinch_content = '''"""
Anti-Pinching Skin Weights Calculation & Volume Preservation.

Responsible for:
- Dual-bone twist distribution on limbs.
- Deltoid clavicular weighting & axilla fold clamping.
- Olecranon (elbow) 3-loop hinge cosine gradient.
- Patella (knee) rigid sesamoid locking.
- Finger bounding-cylinder isolation.
- Strict weight normalization summing to 1.0 for every vertex.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from morphomesh.geometry.mesh import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]

from .metarig import MetarigStructure, ALL_163_DEF_BONES


''' + anti_pinch_body + '''

__all__ = [
    "_point_to_segment_distance",
    "_CANONICAL_FINGER_MAP",
    "_get_canonical_finger_map",
    "SkinWeightMap",
    "calculate_anti_pinch_weights",
]
'''

with open("src/morphomesh/rigging/anti_pinch.py", "w", encoding="utf-8") as f:
    f.write(anti_pinch_content)
print("Wrote src/morphomesh/rigging/anti_pinch.py, lines:", len(anti_pinch_content.splitlines()))

# 3. blendshapes.py
# Lines 219-241: ARKIT_52_BLENDSHAPES
# Lines 1313-1522: generate_arkit_52_blendshapes
blendshapes_body = (
    "".join(lines[218:242])
    + "\n"
    + "".join(lines[1312:1523])
)

blendshapes_content = '''"""
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


''' + blendshapes_body + '''

__all__ = [
    "ARKIT_52_BLENDSHAPES",
    "generate_arkit_52_blendshapes",
]
'''

with open("src/morphomesh/rigging/blendshapes.py", "w", encoding="utf-8") as f:
    f.write(blendshapes_content)
print("Wrote src/morphomesh/rigging/blendshapes.py, lines:", len(blendshapes_content.splitlines()))

# 4. scripts.py
# Lines 1529-1835: get_rigging_script, auto_rig_human
scripts_body = "".join(lines[1528:1836])

scripts_content = '''"""
Blender Runtime Rigging Script Generation and High-Level Pipeline.

Responsible for:
- get_rigging_script: Generates Python script executable inside Blender 4.5+ LTS
  building 163 DEF bones Armature, landmark snapping, anti-pinch weights, and 52 ARKit keys.
- auto_rig_human: Procedural rigging entrypoint returning HumanRigResult dictionary.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from typing import Any, Dict, List, Optional, Tuple

try:
    from morphomesh.geometry.mesh import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]

from .metarig import (
    ALL_163_DEF_BONES,
    BODY_DEF_BONES,
    FACIAL_DEF_BONES,
    HumanRigConfig,
    generate_rigify_human_metarig,
    get_default_human_landmarks,
)
from .anti_pinch import calculate_anti_pinch_weights
from .blendshapes import ARKIT_52_BLENDSHAPES, generate_arkit_52_blendshapes


''' + scripts_body + '''

__all__ = [
    "get_rigging_script",
    "auto_rig_human",
]
'''

with open("src/morphomesh/rigging/scripts.py", "w", encoding="utf-8") as f:
    f.write(scripts_content)
print("Wrote src/morphomesh/rigging/scripts.py, lines:", len(scripts_content.splitlines()))
