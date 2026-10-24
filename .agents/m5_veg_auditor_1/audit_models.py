import hashlib
from pathlib import Path
import json
import numpy as np
from PIL import Image
import sys

sys.path.insert(0, 'teamwork_projects/vegetation_library')
from vegetation_pipeline.validator import parse_glb_container, decode_glb_geometry

out_dir = Path('teamwork_projects/vegetation_library/output')
glb_files = sorted(out_dir.glob('*/*/*.glb'))
print(f'Total GLBs found: {len(glb_files)}')

glb_hashes = set()
metrics_table = []

for glb in glb_files:
    data = glb.read_bytes()
    md5 = hashlib.md5(data).hexdigest()
    glb_hashes.add(md5)

    gltf, bin_bytes = parse_glb_container(glb)
    geom = decode_glb_geometry(gltf, bin_bytes)
    pos = geom['positions']
    tri = geom['triangles']

    z_min = float(pos[:, 2].min())
    z_max = float(pos[:, 2].max())
    h = z_max - z_min
    spread = max(float(pos[:, 0].max() - pos[:, 0].min()), float(pos[:, 1].max() - pos[:, 1].min()))

    skins = gltf.get('skins') or []
    anims = gltf.get('animations') or []

    metrics_table.append({
        'species': glb.stem,
        'category': glb.parent.parent.name,
        'verts': len(pos),
        'faces': len(tri),
        'z_min': z_min,
        'height': h,
        'spread': spread,
        'skins': len(skins),
        'anims': len(anims),
        'md5': md5[:8]
    })

print(f'Distinct MD5 hashes count: {len(glb_hashes)} / 35')
print(f'All 35 GLBs have distinct MD5 hashes: {len(glb_hashes) == 35}')
print('-' * 115)
for m in metrics_table:
    sp = m['species']
    cat = m['category']
    v = m['verts']
    f = m['faces']
    h = m['height']
    zm = m['z_min']
    sk = m['skins']
    md5 = m['md5']
    print(f'{sp:<28} / {cat:<15} / Verts: {v:<5} / Faces: {f:<5} / H: {h:<5.2f}m / Zmin: {zm:<7.4f} / Skins: {sk} / MD5: {md5}')
print('-' * 115)