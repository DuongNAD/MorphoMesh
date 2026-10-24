import json
import numpy as np
from pathlib import Path
from itertools import combinations
import sys

repo_root = Path(r'E:\tool\mcp\MorphoMesh')
subproject = repo_root / 'teamwork_projects' / 'vegetation_library'
sys.path.insert(0, str(subproject))

from vegetation_pipeline.validator import parse_glb_container, decode_glb_geometry

out = subproject / 'output'

print('=== CHECK 1: PROVENANCE FORENSICS ACROSS ALL 35 ASSETS ===')
manifests = sorted(list(out.glob('*/*/asset_manifest.json')))
print(f'Total asset_manifest.json found: {len(manifests)}')

meshy_assets = []
procedural_assets = []
other_assets = []
asset_data = {}

for m in manifests:
    with open(m, 'r', encoding='utf-8') as f:
        d = json.load(f)
    sid = d.get('species_id')
    prov = d.get('provenance', {})
    src = prov.get('source')
    tid = prov.get('task_id')
    model_urls = prov.get('model_urls', {})
    geom = d.get('geometry', {})
    vc = geom.get('vertex_count', 0)
    fc = geom.get('face_count', 0)
    entry = {
        'species_id': sid,
        'source': src,
        'task_id': tid,
        'model_urls': model_urls,
        'vertex_count': vc,
        'face_count': fc,
        'path': m.parent
    }
    asset_data[sid] = entry
    if src == 'meshy':
        meshy_assets.append(entry)
    elif src == 'procedural':
        procedural_assets.append(entry)
    else:
        other_assets.append(entry)

print(f'Meshy Assets: {len(meshy_assets)}/35 ({len(meshy_assets)/35*100:.1f} pct)')
print(f'Procedural Assets: {len(procedural_assets)}/35 ({len(procedural_assets)/35*100:.1f} pct)')
print(f'Other Assets: {len(other_assets)}/35')

print('\nProcedural Assets List:')
for a in procedural_assets:
    print(f"  - {a['species_id']}: {a['vertex_count']} verts, {a['face_count']} faces, task_id={a['task_id']}")

print('\n=== CHECK 2: GEOMETRIC CLONE AND TOPOLOGY ANALYSIS ===')
succulents = ['veg_succulent_agave_01', 'veg_succulent_aloe_01', 'veg_succulent_barrel_01', 'veg_succulent_echeveria_01']
succ_geoms = {}
for sid in succulents:
    glb_file = asset_data[sid]['path'] / f'{sid}.glb'
    gltf, bb = parse_glb_container(glb_file)
    succ_geoms[sid] = decode_glb_geometry(gltf, bb)

tri_agave = succ_geoms['veg_succulent_agave_01']['triangles']
for sid in succulents[1:]:
    tri_other = succ_geoms[sid]['triangles']
    tri_match = np.array_equal(tri_agave, tri_other)
    pos_diff = float(np.max(np.abs(succ_geoms['veg_succulent_agave_01']['positions'] - succ_geoms[sid]['positions'])))
    print(f"  Triangles match agave vs {sid}: {tri_match}, max pos diff: {pos_diff:.6f}")

vines = ['veg_vine_ivy_01', 'veg_vine_wisteria_01', 'veg_vine_bougainvillea_01', 'veg_epiphyte_spanishmoss_01', 'veg_vine_pothos_01']
vine_geoms = {}
for sid in vines:
    glb_file = asset_data[sid]['path'] / f'{sid}.glb'
    gltf, bb = parse_glb_container(glb_file)
    vine_geoms[sid] = decode_glb_geometry(gltf, bb)

tri_ivy = vine_geoms['veg_vine_ivy_01']['triangles']
for sid in vines[1:]:
    tri_other = vine_geoms[sid]['triangles']
    tri_match = np.array_equal(tri_ivy, tri_other)
    pos_diff = float(np.max(np.abs(vine_geoms['veg_vine_ivy_01']['positions'] - vine_geoms[sid]['positions'])))
    print(f"  Triangles match ivy vs {sid}: {tri_match}, max pos diff: {pos_diff:.6f}")

print('\n=== CHECK 3: PAIRWISE VERTEX COLLISION RATE ===')
pairs = list(combinations(asset_data.values(), 2))
total_pairs = len(pairs)
collisions = [p for p in pairs if p[0]['vertex_count'] == p[1]['vertex_count']]
print(f'Total pairs: {total_pairs}')
print('Colliding pairs: {len(collisions)}')
print(f'Collision rate: {len(collisions)/total_pairs*100:.2f} pct')

print('\n=== CHECK 4: MASTER MANIFEST.JSON SYNCHRONIZATION ===')
with open(out / 'manifest.json', 'r', encoding='utf-8') as f:
    master = json.load(f)

print(f"Master indexed: {master.get('indexed_species_count')}")
print(f"Master passed: {master.get('passed_validation_count')}")
print(f"Master failed: {master.get('failed_validation_count')}")
master_assets = master.get('assets', {})
oak = master_assets.get('veg_tree_oak_01', {})
print("Oak provenance in master manifest:", oak.get("provenance"))
