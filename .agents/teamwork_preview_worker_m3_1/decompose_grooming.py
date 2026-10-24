"""
Decompose src/morphomesh/human_grooming.py and migrate src/morphomesh/grooming.py
into src/morphomesh/grooming/ modular sub-package with zero regressions.
"""

import os
import shutil
from pathlib import Path

SRC = Path("src/morphomesh")
PKG = SRC / "grooming"
PKG.mkdir(parents=True, exist_ok=True)

with open(SRC / "human_grooming.py", "r", encoding="utf-8") as f:
    orig_hg_lines = f.readlines()

# 1. hime_cut.py (lines 49 to 570)
hime_cut_content = '''"""
MorphoMesh Hime Cut Hair Strata and Spline Curves Generator.

Responsible for:
- HairLayerConfig & HairGroomConfig parameter definitions.
- get_6_stratum_hime_cut_layers: Bangs, Sidelocks, Crown, Temporal, Dorsal cascade, Flyaways.
- get_default_hime_cut_layers: 6 layers backward-compatible mapping.
- HairCurveSpline container dataclass.
- generate_hime_cut_splines: 3D procedural curve point evaluation.
- generate_6_stratum_hime_cut_splines: Master 6-stratum generator.
"""

from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("morphomesh.grooming.hime_cut")

'''
# Lines 49-570 (0-indexed: 48 to 570)
hime_cut_content += "".join(orig_hg_lines[48:570])

with open(PKG / "hime_cut.py", "w", encoding="utf-8") as f:
    f.write(hime_cut_content)
print("Wrote hime_cut.py")

# 2. ribbons.py (lines 572 to 654)
ribbons_content = '''"""
MorphoMesh Hair Curves-to-Ribbon Mesh Extrusion Evaluator.

Responsible for:
- convert_curves_to_ribbon_mesh: Evaluates 3D hair splines into polygonal quad ribbon meshes.
- UV coordinate generation, outward-facing normal calculation, and Rigify DEF-head binding.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from morphomesh.inference_adapter import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]

from .hime_cut import HairCurveSpline

logger = logging.getLogger("morphomesh.grooming.ribbons")

'''
# Lines 572-654 (0-indexed: 571 to 654)
ribbons_content += "".join(orig_hg_lines[571:654])

with open(PKG / "ribbons.py", "w", encoding="utf-8") as f:
    f.write(ribbons_content)
print("Wrote ribbons.py")

# 3. curves_pipeline.py (lines 660 to 772)
curves_pipeline_content = '''"""
MorphoMesh Blender Geometry Nodes Hair Curve Modifier Network.

Responsible for:
- build_hair_geom_node_tree: Procedurally builds GN_HairGroom modifier node tree in Blender 4.0+ LTS
  with root-to-tip taper, tip clumping, micro-frizz noise, and material assignment.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("morphomesh.grooming.curves_pipeline")

'''
# Lines 660-772 (0-indexed: 659 to 772)
curves_pipeline_content += "".join(orig_hg_lines[659:772])

with open(PKG / "curves_pipeline.py", "w", encoding="utf-8") as f:
    f.write(curves_pipeline_content)
print("Wrote curves_pipeline.py")

# 4. scripts.py (lines 774 to 1188)
scripts_content = '''"""
MorphoMesh In-Blender Hair Grooming Script Template & CLI Entrypoint.

Responsible for:
- get_grooming_script: Generates Python script executable inside Blender 4.5+ LTS
  generating Curves objects, hair modifier node trees, surface snapping, and Melanin materials.
- groom_human: High-level procedural grooming entrypoint returning HumanGroomResult.
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

from .hime_cut import (
    HairLayerConfig,
    HairGroomConfig,
    HairCurveSpline,
    get_6_stratum_hime_cut_layers,
    get_default_hime_cut_layers,
    generate_hime_cut_splines,
    generate_6_stratum_hime_cut_splines,
)
from .ribbons import convert_curves_to_ribbon_mesh
from .curves_pipeline import build_hair_geom_node_tree

logger = logging.getLogger("morphomesh.grooming.scripts")

'''
# Lines 774-1188 (0-indexed: 773 to 1188)
scripts_content += "".join(orig_hg_lines[773:])

with open(PKG / "scripts.py", "w", encoding="utf-8") as f:
    f.write(scripts_content)
print("Wrote scripts.py")

# 5. creature.py (Move original grooming.py contents into grooming/creature.py)
with open(SRC / "grooming.py", "r", encoding="utf-8") as f:
    creature_content = f.read()

with open(PKG / "creature.py", "w", encoding="utf-8") as f:
    f.write(creature_content)
print("Wrote creature.py")

# 6. __init__.py
init_content = '''"""
MorphoMesh: Volumetric Fur & Digital Human Hair Curves Grooming Subsystem.

Decomposed modular grooming package providing:
- hime_cut: 6-stratum hime cut hair strata definitions, parameters, and 3D spline curves generator.
- ribbons: Offline & real-time polygonal quad ribbon mesh extrusion from hair curves.
- curves_pipeline: Blender 4.5+ Geometry Nodes hair modifier network builder.
- scripts: Standalone Blender script generator and groom_human entrypoint.
- creature: Quadruped volumetric fur grooming engine and biological flow vector fields.
"""

from __future__ import annotations

from .creature import (
    ZERO_FUR_GROUPS,
    CreatureGroomingEngine,
    FurLayerConfig,
    compute_biological_flow_vector,
    evaluate_fur_ribbons_for_gltf,
    get_default_guard_hair_config,
    get_default_undercoat_config,
    setup_volumetric_fur,
)
from .curves_pipeline import build_hair_geom_node_tree
from .hime_cut import (
    HairCurveSpline,
    HairGroomConfig,
    HairLayerConfig,
    _calc_spline_length,
    generate_6_stratum_hime_cut_splines,
    generate_hime_cut_splines,
    get_6_stratum_hime_cut_layers,
    get_default_hime_cut_layers,
)
from .ribbons import convert_curves_to_ribbon_mesh
from .scripts import (
    get_grooming_script,
    groom_human,
)

__all__ = [
    # Sub-modules
    "creature",
    "curves_pipeline",
    "hime_cut",
    "ribbons",
    "scripts",
    # Human Hair Grooming Configs & Dataclasses
    "HairLayerConfig",
    "HairGroomConfig",
    "HairCurveSpline",
    # Human Hair Functions
    "_calc_spline_length",
    "get_6_stratum_hime_cut_layers",
    "get_default_hime_cut_layers",
    "generate_hime_cut_splines",
    "generate_6_stratum_hime_cut_splines",
    "convert_curves_to_ribbon_mesh",
    "build_hair_geom_node_tree",
    "get_grooming_script",
    "groom_human",
    # Creature Volumetric Fur Grooming
    "ZERO_FUR_GROUPS",
    "FurLayerConfig",
    "get_default_undercoat_config",
    "get_default_guard_hair_config",
    "compute_biological_flow_vector",
    "CreatureGroomingEngine",
    "setup_volumetric_fur",
    "evaluate_fur_ribbons_for_gltf",
]
'''

with open(PKG / "__init__.py", "w", encoding="utf-8") as f:
    f.write(init_content)
print("Wrote __init__.py")

# 7. human_grooming.py (facade)
facade_content = '''"""
MorphoMesh: Digital Human Geometry Nodes Hair Curves Grooming Facade.

Refactored into backward-compatible facade re-exporting all symbols from
the morphomesh.grooming modular sub-package.
"""

from __future__ import annotations

from morphomesh.grooming import (
    HairCurveSpline,
    HairGroomConfig,
    HairLayerConfig,
    _calc_spline_length,
    build_hair_geom_node_tree,
    convert_curves_to_ribbon_mesh,
    generate_6_stratum_hime_cut_splines,
    generate_hime_cut_splines,
    get_6_stratum_hime_cut_layers,
    get_default_hime_cut_layers,
    get_grooming_script,
    groom_human,
)

__all__ = [
    "HairLayerConfig",
    "HairGroomConfig",
    "HairCurveSpline",
    "_calc_spline_length",
    "get_6_stratum_hime_cut_layers",
    "get_default_hime_cut_layers",
    "generate_hime_cut_splines",
    "generate_6_stratum_hime_cut_splines",
    "convert_curves_to_ribbon_mesh",
    "build_hair_geom_node_tree",
    "get_grooming_script",
    "groom_human",
]
'''

with open(SRC / "human_grooming.py", "w", encoding="utf-8") as f:
    f.write(facade_content)
print("Wrote facade human_grooming.py")

# 8. Remove obsolete src/morphomesh/grooming.py so package directory takes clean effect
if (SRC / "grooming.py").exists():
    os.remove(SRC / "grooming.py")
    print("Removed obsolete grooming.py in favor of grooming/ package")
