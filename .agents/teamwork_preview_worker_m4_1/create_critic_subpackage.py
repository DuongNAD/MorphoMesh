import os
import json

os.makedirs('src/morphomesh/critic', exist_ok=True)

with open('src/morphomesh/visual_critic.py', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()

# ==========================================
# 1. geometry_math.py (lines 66 to 461, 0-indexed: 65 to 461)
# ==========================================
geo_body = lines[65:462]
geo_content = '''"""
MorphoMesh: Critic Geometric Math & Ray-Triangle Primitives.

Pure-Python 3D vector arithmetic, Möller–Trumbore ray-triangle intersection,
Möller triangle-triangle intersection, Eberly point-to-triangle distance,
and Axis-Aligned Bounding Box (AABB) spatial primitives.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

''' + '\n'.join(geo_body) + '''

__all__ = [
    "_cross_product",
    "_dot_product",
    "_sub_vec",
    "_add_vec",
    "_scale_vec",
    "_norm_vec",
    "_vec_len",
    "point_to_triangle_distance_eberly",
    "ray_triangle_intersection_moller_trumbore",
    "_segments_intersect_2d",
    "_point_in_triangle_2d",
    "_coplanar_triangle_triangle_intersection_2d",
    "triangle_triangle_intersection_moller",
    "PurePythonAABB",
]
'''

with open('src/morphomesh/critic/geometry_math.py', 'w', encoding='utf-8') as f:
    f.write(geo_content)
print('geometry_math.py written')

# ==========================================
# 2. bvh.py (lines 464 to 739, 0-indexed: 463 to 739)
# ==========================================
bvh_body = lines[463:739]
bvh_content = '''"""
MorphoMesh: Pure Python Bounding Volume Hierarchy (BVH) Spatial Index.

Provides PurePythonBVHTree for sub-millisecond ray casting, nearest-neighbor
point-to-surface projection, and triangle-triangle overlap queries without
external C libraries or Blender dependencies.
"""

from __future__ import annotations

import heapq
import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from .geometry_math import (
    PurePythonAABB,
    _cross_product,
    _dot_product,
    _norm_vec,
    _scale_vec,
    _sub_vec,
    _vec_len,
    point_to_triangle_distance_eberly,
    ray_triangle_intersection_moller_trumbore,
    triangle_triangle_intersection_moller,
)

try:
    import bpy
    import bmesh
    import mathutils
    from mathutils.bvhtree import BVHTree as BlenderBVHTree
    HAS_BLENDER = True
except (ImportError, ModuleNotFoundError):
    bpy = None
    bmesh = None
    mathutils = None
    BlenderBVHTree = None
    HAS_BLENDER = False

''' + '\n'.join(bvh_body) + '''

__all__ = [
    "PurePythonBVHNode",
    "PurePythonBVHTree",
    "get_bvh_tree",
    "BlenderBVHTree",
    "HAS_BLENDER",
]
'''

with open('src/morphomesh/critic/bvh.py', 'w', encoding='utf-8') as f:
    f.write(bvh_content)
print('bvh.py written')

# ==========================================
# 3. penetration.py (lines 746 to 1294, 0-indexed: 745 to 1294)
# ==========================================
pen_body = lines[745:1294]
pen_content = '''"""
MorphoMesh: Mesh Penetration & Grooming Collision Evaluation Engine.

Analyzes signed distance clearances between cloth-body, cloth-cloth, and
hair curve guides, identifying garment clipping, skin bursts, and grooming intersections.
"""

from __future__ import annotations

import math
import time
import uuid
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np

from morphomesh.models import (
    ActionableRecommendation,
    BoundingBox3D,
    DefectCategory,
    DefectItem,
    DefectSeverity,
)

from .geometry_math import (
    _add_vec,
    _cross_product,
    _dot_product,
    _norm_vec,
    _scale_vec,
    _sub_vec,
    _vec_len,
    point_to_triangle_distance_eberly,
    ray_triangle_intersection_moller_trumbore,
    triangle_triangle_intersection_moller,
)
from .bvh import PurePythonBVHTree, get_bvh_tree

''' + '\n'.join(pen_body) + '''

__all__ = [
    "_compute_vertex_normals",
    "_find_garment_boundary_edges",
    "evaluate_mesh_penetration",
    "evaluate_hair_grooming_intersections",
]
'''

with open('src/morphomesh/critic/penetration.py', 'w', encoding='utf-8') as f:
    f.write(pen_content)
print('penetration.py written')

# ==========================================
# 4. proportions.py (lines 1301 to 1539, 0-indexed: 1300 to 1539)
# ==========================================
prop_body = lines[1300:1539]
prop_content = '''"""
MorphoMesh: Anthropometric Body Proportions & Aesthetic Critique Engine.

Audits digital human anatomical ratios against golden ratio and character styling
presets (realistic, stylized heroine, heroic male, chibi), evaluating head-to-body
ratio, arm span index, and shoulder-to-hip breadth proportions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from morphomesh.models import (
    ActionableRecommendation,
    DefectCategory,
    DefectItem,
    DefectSeverity,
)

''' + '\n'.join(prop_body) + '''

__all__ = [
    "ANTHROPOMETRIC_PRESETS",
    "AnthropometricMetrics",
    "evaluate_body_proportions",
]
'''

with open('src/morphomesh/critic/proportions.py', 'w', encoding='utf-8') as f:
    f.write(prop_content)
print('proportions.py written')

# ==========================================
# 5. deformation.py (lines 1547 to 1840, 0-indexed: 1546 to 1840)
# ==========================================
deform_body = lines[1546:1840]
deform_content = '''"""
MorphoMesh: Rig Skinning Deformation & Volume Preservation Engine.

Evaluates mesh signed volume conservation, joint collapse (candy-wrapper twisting),
extreme acute dihedral creases, and skinning pinch defects under pose deformation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np

from morphomesh.models import (
    ActionableRecommendation,
    DefectCategory,
    DefectItem,
    DefectSeverity,
)
from .geometry_math import (
    _cross_product,
    _dot_product,
    _norm_vec,
    _sub_vec,
    _vec_len,
)

''' + '\n'.join(deform_body) + '''

__all__ = [
    "JointDeformationMetrics",
    "compute_mesh_signed_volume",
    "compute_bounding_slice_volume",
    "compute_mesh_dihedral_creases",
    "evaluate_rig_skinning_deformation",
    "evaluate_rig_skinning_pinch",
]
'''

with open('src/morphomesh/critic/deformation.py', 'w', encoding='utf-8') as f:
    f.write(deform_content)
print('deformation.py written')

# ==========================================
# 6. reporter.py (lines 1847 to 2268, 0-indexed: 1846 to 2269)
# ==========================================
rep_body = lines[1846:2269]
rep_content = '''"""
MorphoMesh: Visual Quality Critique Reporter & Benchmarking Suite.

Coordinates full multi-angle inspection, aggregates quality critique scores,
generates structured JSON / Markdown diagnostic defect reports, and provides
procedural defect injection test fixtures (>95% detection accuracy benchmark).
"""

from __future__ import annotations

import math
import time
import uuid
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np

from morphomesh.models import (
    ActionableRecommendation,
    BoundingBox3D,
    DefectCategory,
    DefectItem,
    DefectSeverity,
    VisualCritiqueInput,
    VisualCritiqueOutput,
)

from .geometry_math import (
    _cross_product,
    _dot_product,
    _norm_vec,
    _sub_vec,
    _vec_len,
)
from .bvh import PurePythonBVHTree, get_bvh_tree
from .penetration import evaluate_mesh_penetration, evaluate_hair_grooming_intersections
from .proportions import evaluate_body_proportions
from .deformation import (
    compute_bounding_slice_volume,
    compute_mesh_dihedral_creases,
    compute_mesh_signed_volume,
    evaluate_rig_skinning_deformation,
)

''' + '\n'.join(rep_body) + '''

__all__ = [
    "make_procedural_cylinder",
    "create_penetration_fixture",
    "create_proportion_fixture",
    "create_skinning_fixture",
    "create_grooming_fixture",
    "run_defect_detection_benchmark",
    "benchmark_defect_detection",
    "run_visual_critique",
]
'''

with open('src/morphomesh/critic/reporter.py', 'w', encoding='utf-8') as f:
    f.write(rep_content)
print('reporter.py written')

print('All 6 critic modules created successfully!')
