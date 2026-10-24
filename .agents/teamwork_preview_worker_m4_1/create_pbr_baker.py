import os

with open('src/morphomesh/character_assembler.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Extract lines 2069 to 2341
lines = text.splitlines()
func_lines = lines[2068:2341]

pbr_content = '''"""
MorphoMesh: 4K PBR Procedural Texture Baking Subsystem.

Provides 4K PBR procedural texture map synthesis (BaseColor, Normal, Roughness,
Metallic, SSS, Alpha, Height, packed ORM, Unity HDRP MaskMap, and discrete 4K maps)
for Yu Nian An and digital human character pipelines.
"""

from __future__ import annotations

import logging
import os
import math
from typing import Dict, Any, Optional

logger = logging.getLogger("morphomesh.assembler.pbr_baker")

''' + '\n'.join(func_lines) + '\n\n__all__ = ["generate_yu_nian_an_pbr_textures"]\n'

old_lips = '''    d_lips = np.sqrt(((u1 - 0.50) / 0.10)**2 + ((v1 - 0.72) / 0.045)**2)
    mask_lips = mask_q1 & (d_lips < 1.0)'''

new_lips = '''    d_lips1 = np.sqrt(((u1 - 0.50) / 0.12)**2 + ((v1 - 0.76) / 0.08)**2)
    d_lips2 = np.sqrt(((u - 0.25) / 0.06)**2 + ((v - 0.64) / 0.05)**2)
    d_lips = np.minimum(d_lips1, d_lips2)
    mask_lips = (mask_q1 & (d_lips1 < 1.0)) | (d_lips2 < 1.0)'''

pbr_content = pbr_content.replace(old_lips, new_lips)

with open('src/morphomesh/assembler/pbr_baker.py', 'w', encoding='utf-8') as f:
    f.write(pbr_content)

print('pbr_baker.py written successfully!')
