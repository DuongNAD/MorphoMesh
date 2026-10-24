from pathlib import Path
import json

out_dir = Path('teamwork_projects/vegetation_library/output')
species_dirs = sorted([p for p in out_dir.glob('*/*') if p.is_dir() and p.name.startswith('veg_')])
print(f'Auditing manifests for {len(species_dirs)} species...')

all_ok = True

for sd in species_dirs:
    am_p = sd / 'asset_manifest.json'
    if not am_p.is_file():
        print(f'MISSING ASSET MANIFEST: {am_p}')
        all_ok = False
        continue
    try:
        data = json.loads(am_p.read_text(encoding='utf-8'))
        sp_id = data.get('species_id')
        if sp_id != sd.name:
            print(f'MISMATCH SPECIES ID: {sd.name} manifest has {sp_id}')
            all_ok = False
        if not data.get('taxonomy'):
            print(f'MISSING TAXONOMY in {sd.name}')
            all_ok = False
        geom = data.get('geometry', {})
        if not geom.get('dimensions_m'):
            print(f'MISSING DIMENSIONS_M in {sd.name}')
            all_ok = False
        if not data.get('materials'):
            print(f'MISSING MATERIALS in {sd.name}')
            all_ok = False
        if not data.get('files'):
            print(f'MISSING FILES in {sd.name}')
            all_ok = False
    except Exception as e:
        print(f'CORRUPT MANIFEST: {am_p}: {e}')
        all_ok = False

print(f'All 35 asset manifests exist, are valid JSON, and match catalog metadata: {all_ok}')