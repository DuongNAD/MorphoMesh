"""
Decompose src/morphomesh/wardrobe.py into src/morphomesh/wardrobe/ sub-package
with exact source preservation and 100% backward-compatible facade.
"""

import os
from pathlib import Path

SRC = Path("src/morphomesh")
PKG = SRC / "wardrobe"
PKG.mkdir(parents=True, exist_ok=True)

with open(SRC / "wardrobe.py", "r", encoding="utf-8") as f:
    orig_lines = f.readlines()

# 1. skinning.py (lines 46-77, and lines 112-376)
skinning_content = '''"""
MorphoMesh Wardrobe Skin Weights and Pinning Subsystem.

Responsible for:
- Finger DEF bone key aliases and material aliases.
- Elevation radii computation for dress waist.
- Cloth simulation pin weighting (Pin_Bodice).
- Rigify DEF skin weights computation for Bodice, Skirt, Sash, Sandals.
- compute_wardrobe_skin_weights entrypoint.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    from morphomesh.inference_adapter import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]

logger = logging.getLogger("morphomesh.wardrobe.skinning")

'''
# Lines 46-77 (0-indexed: 45 to 76)
skinning_content += "".join(orig_lines[45:77]) + "\n\n"
# Lines 112-376 (0-indexed: 111 to 376)
skinning_content += "".join(orig_lines[111:376])

with open(PKG / "skinning.py", "w", encoding="utf-8") as f:
    f.write(skinning_content)
print("Wrote skinning.py")

# 2. props.py (lines 1454-1774)
props_content = '''"""
MorphoMesh Magic Props Engine: Swallowtail Butterflies & Marionette Strings.

Responsible for:
- BUTTERFLY_FLUTTER_POSITIONS canonical flight coordinates.
- get_butterfly_vortex_positions & get_butterfly_flutter_positions.
- generate_catenary_magic_strings (marionette red threads).
- generate_swallowtail_quad_butterfly (luminous white swallowtail butterflies).
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from morphomesh.inference_adapter import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]

from .skinning import (
    FINGER_DEF_BONE_KEYS,
    FINGER_DEF_BONE_ALIASES,
    resolve_finger_def_bone_name,
)

logger = logging.getLogger("morphomesh.wardrobe.props")

'''
# Lines 1454-1774 (0-indexed: 1453 to 1774)
props_content += "".join(orig_lines[1453:1774])
props_content += '''

# Additional aliases for public contract
generate_marionette_strings = generate_catenary_magic_strings
generate_glowing_butterflies = generate_swallowtail_quad_butterfly
'''

with open(PKG / "props.py", "w", encoding="utf-8") as f:
    f.write(props_content)
print("Wrote props.py")

# 3. garments.py
# Config (lines 80-107), then garments (lines 378-1453), then generate_yu_nian_an_wardrobe (lines 1775-1825)
garments_content = '''"""
MorphoMesh Parametric Garment Synthesis Engine: Slip Dress, Sash, Sandals.

Responsible for:
- WardrobeConfig master configuration dataclass.
- generate_dress_bodice: Sweetheart scoop neckline, teardrop bust, 3D straps.
- generate_dress_waist_sash: High waist sash wrap, barrel-cuff knot, ribbon streamers.
- generate_dress_organic_skirt / generate_dress_pleated_skirt: 20-pleat A-line drape.
- generate_organic_dress & generate_waist_sash_and_bow contract wrappers.
- generate_flat_strappy_sandals: Sole, straps, and ankle bindings.
- generate_yu_nian_an_wardrobe: High-level complete outfit synthesizer.
"""

from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    from morphomesh.inference_adapter import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]

from .skinning import (
    compute_dress_waist_radii,
    assign_dress_pin_weights,
    assign_bodice_skin_weights,
    assign_skirt_skin_weights,
    assign_sash_skin_weights,
    compute_wardrobe_skin_weights,
    MATERIAL_NAME_ALIASES,
)
from .props import (
    get_butterfly_flutter_positions,
    generate_marionette_red_strings,
    generate_swallowtail_butterfly,
)

logger = logging.getLogger("morphomesh.wardrobe.garments")

'''
# Lines 82-108 (0-indexed: 81 to 108)
garments_content += "".join(orig_lines[81:108]) + "\n\n"
# Lines 378-1453 (0-indexed: 377 to 1453)
garments_content += "".join(orig_lines[377:1453]) + "\n\n"
# generate_dress_skirt alias
garments_content += "\ngenerate_dress_skirt = generate_dress_organic_skirt\n\n"
# Lines 1775-1825 (0-indexed: 1774 to 1825)
garments_content += "".join(orig_lines[1774:1825])

with open(PKG / "garments.py", "w", encoding="utf-8") as f:
    f.write(garments_content)
print("Wrote garments.py")

# 4. scripts.py (lines 1826-2182)
scripts_content = '''"""
MorphoMesh In-Blender Wardrobe Generation Script Template & CLI Entrypoint.

Responsible for:
- get_wardrobe_script: Generates Python script executable inside Blender 4.5+ LTS
  building dress, sash, sandals, ribbons, butterflies, materials, and DEF bone binding.
- dress_human: Procedural high-level wardrobe entrypoint returning HumanWardrobeResult.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from morphomesh.inference_adapter import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]

try:
    import bpy
    HAS_BPY = True
except (ImportError, ModuleNotFoundError):
    HAS_BPY = False

from .skinning import (
    FINGER_DEF_BONE_KEYS,
    FINGER_DEF_BONE_ALIASES,
    resolve_finger_def_bone_name,
    MATERIAL_NAME_ALIASES,
    compute_dress_waist_radii,
    assign_dress_pin_weights,
    assign_bodice_skin_weights,
    assign_skirt_skin_weights,
    assign_sash_skin_weights,
    compute_wardrobe_skin_weights,
)
from .props import (
    BUTTERFLY_FLUTTER_POSITIONS,
    get_butterfly_vortex_positions,
    get_butterfly_flutter_positions,
    generate_catenary_magic_strings,
    generate_marionette_red_strings,
    generate_marionette_strings,
    generate_swallowtail_quad_butterfly,
    generate_swallowtail_butterfly,
    generate_glowing_butterflies,
)
from .garments import (
    WardrobeConfig,
    generate_dress_bodice,
    generate_dress_waist_sash,
    generate_dress_organic_skirt,
    generate_dress_pleated_skirt,
    generate_dress_skirt,
    generate_organic_dress,
    generate_waist_sash_and_bow,
    generate_flat_strappy_sandals,
    generate_flat_sandals,
    generate_yu_nian_an_wardrobe,
)

logger = logging.getLogger("morphomesh.wardrobe.scripts")

'''
# Lines 1829-2182 (0-indexed: 1828 to 2182)
scripts_content += "".join(orig_lines[1828:])

with open(PKG / "scripts.py", "w", encoding="utf-8") as f:
    f.write(scripts_content)
print("Wrote scripts.py")

# 5. __init__.py
init_content = '''"""
MorphoMesh: Parametric Digital Human Wardrobe & Magic Props Subsystem.

Decomposed modular wardrobe package providing:
- skinning: Rigify DEF bone weights, vertex group mapping, pin weights, and material aliases.
- props: Luminous white swallowtail butterflies, upward vortex flocking, and crimson marionette strings.
- garments: White slip dress (bodice, 20-pleat skirt), empire waist sash & bow, strappy flat sandals.
- scripts: Standalone Blender 4.5+ LTS script generator and dress_human entrypoint.
"""

from __future__ import annotations

from .garments import (
    WardrobeConfig,
    generate_dress_bodice,
    generate_dress_organic_skirt,
    generate_dress_pleated_skirt,
    generate_dress_skirt,
    generate_dress_waist_sash,
    generate_flat_sandals,
    generate_flat_strappy_sandals,
    generate_organic_dress,
    generate_waist_sash_and_bow,
    generate_yu_nian_an_wardrobe,
)
from .props import (
    BUTTERFLY_FLUTTER_POSITIONS,
    generate_catenary_magic_strings,
    generate_glowing_butterflies,
    generate_marionette_red_strings,
    generate_marionette_strings,
    generate_swallowtail_butterfly,
    generate_swallowtail_quad_butterfly,
    get_butterfly_flutter_positions,
    get_butterfly_vortex_positions,
)
from .scripts import (
    dress_human,
    get_wardrobe_script,
)
from .skinning import (
    FINGER_DEF_BONE_ALIASES,
    FINGER_DEF_BONE_KEYS,
    MATERIAL_NAME_ALIASES,
    assign_bodice_skin_weights,
    assign_dress_pin_weights,
    assign_sash_skin_weights,
    assign_skirt_skin_weights,
    compute_dress_waist_radii,
    compute_wardrobe_skin_weights,
    resolve_finger_def_bone_name,
)

__all__ = [
    # Sub-modules
    "garments",
    "props",
    "scripts",
    "skinning",
    # Constants & Aliases
    "FINGER_DEF_BONE_KEYS",
    "FINGER_DEF_BONE_ALIASES",
    "MATERIAL_NAME_ALIASES",
    "BUTTERFLY_FLUTTER_POSITIONS",
    "resolve_finger_def_bone_name",
    # Configuration
    "WardrobeConfig",
    # Skinning & Pinning
    "compute_dress_waist_radii",
    "assign_dress_pin_weights",
    "assign_bodice_skin_weights",
    "assign_skirt_skin_weights",
    "assign_sash_skin_weights",
    "compute_wardrobe_skin_weights",
    # Garment Generators
    "generate_dress_bodice",
    "generate_dress_waist_sash",
    "generate_dress_organic_skirt",
    "generate_dress_pleated_skirt",
    "generate_dress_skirt",
    "generate_organic_dress",
    "generate_waist_sash_and_bow",
    "generate_flat_strappy_sandals",
    "generate_flat_sandals",
    "generate_yu_nian_an_wardrobe",
    # Magic Props Generators
    "get_butterfly_vortex_positions",
    "get_butterfly_flutter_positions",
    "generate_catenary_magic_strings",
    "generate_marionette_red_strings",
    "generate_marionette_strings",
    "generate_swallowtail_quad_butterfly",
    "generate_swallowtail_butterfly",
    "generate_glowing_butterflies",
    # Scripts & Entrypoints
    "get_wardrobe_script",
    "dress_human",
]
'''

with open(PKG / "__init__.py", "w", encoding="utf-8") as f:
    f.write(init_content)
print("Wrote __init__.py")

# 6. wardrobe.py (facade)
facade_content = '''"""
MorphoMesh: Parametric Wardrobe & Magic Props Facade.

Refactored into backward-compatible facade re-exporting all symbols from
the morphomesh.wardrobe modular sub-package.
"""

from __future__ import annotations

from morphomesh.wardrobe import (
    BUTTERFLY_FLUTTER_POSITIONS,
    FINGER_DEF_BONE_ALIASES,
    FINGER_DEF_BONE_KEYS,
    MATERIAL_NAME_ALIASES,
    WardrobeConfig,
    assign_bodice_skin_weights,
    assign_dress_pin_weights,
    assign_sash_skin_weights,
    assign_skirt_skin_weights,
    compute_dress_waist_radii,
    compute_wardrobe_skin_weights,
    dress_human,
    generate_catenary_magic_strings,
    generate_dress_bodice,
    generate_dress_organic_skirt,
    generate_dress_pleated_skirt,
    generate_dress_skirt,
    generate_dress_waist_sash,
    generate_flat_sandals,
    generate_flat_strappy_sandals,
    generate_glowing_butterflies,
    generate_marionette_red_strings,
    generate_marionette_strings,
    generate_organic_dress,
    generate_swallowtail_butterfly,
    generate_swallowtail_quad_butterfly,
    generate_waist_sash_and_bow,
    generate_yu_nian_an_wardrobe,
    get_butterfly_flutter_positions,
    get_butterfly_vortex_positions,
    get_wardrobe_script,
    resolve_finger_def_bone_name,
)

__all__ = [
    "FINGER_DEF_BONE_KEYS",
    "FINGER_DEF_BONE_ALIASES",
    "MATERIAL_NAME_ALIASES",
    "BUTTERFLY_FLUTTER_POSITIONS",
    "resolve_finger_def_bone_name",
    "WardrobeConfig",
    "compute_dress_waist_radii",
    "assign_dress_pin_weights",
    "assign_bodice_skin_weights",
    "assign_skirt_skin_weights",
    "assign_sash_skin_weights",
    "compute_wardrobe_skin_weights",
    "generate_dress_bodice",
    "generate_dress_waist_sash",
    "generate_dress_organic_skirt",
    "generate_dress_pleated_skirt",
    "generate_dress_skirt",
    "generate_organic_dress",
    "generate_waist_sash_and_bow",
    "generate_flat_strappy_sandals",
    "generate_flat_sandals",
    "generate_yu_nian_an_wardrobe",
    "get_butterfly_vortex_positions",
    "get_butterfly_flutter_positions",
    "generate_catenary_magic_strings",
    "generate_marionette_red_strings",
    "generate_marionette_strings",
    "generate_swallowtail_quad_butterfly",
    "generate_swallowtail_butterfly",
    "generate_glowing_butterflies",
    "get_wardrobe_script",
    "dress_human",
]
'''

with open(SRC / "wardrobe.py", "w", encoding="utf-8") as f:
    f.write(facade_content)
print("Wrote facade wardrobe.py")
