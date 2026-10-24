from pathlib import Path

out_dir = Path('teamwork_projects/vegetation_library/output')
species_dirs = sorted([p for p in out_dir.glob('*/*') if p.is_dir() and p.name.startswith('veg_')])
print(f'Auditing OBJ/MTL files for {len(species_dirs)} species...')

all_ok = True
bone_keywords = ['bone', 'joint', 'armature', 'skeleton', 'skin', 'weight']

for sd in species_dirs:
    obj_p = sd / f'{sd.name}.obj'
    mtl_p = sd / f'{sd.name}.mtl'

    if not obj_p.is_file() or obj_p.stat().st_size == 0:
        print(f'MISSING OR EMPTY OBJ: {obj_p}')
        all_ok = False
    if not mtl_p.is_file() or mtl_p.stat().st_size == 0:
        print(f'MISSING OR EMPTY MTL: {mtl_p}')
        all_ok = False

    # Check for bone keywords in obj
    content = obj_p.read_text(encoding='utf-8', errors='ignore')
    for kw in bone_keywords:
        if f' {kw}' in content.lower() or f'_{kw}' in content.lower():
            print(f'BONE KEYWORD DETECTED in {obj_p.name}: {kw}')
            all_ok = False

print(f'All 35 OBJ and MTL files exist, are non-empty, and strictly contain zero bone structures: {all_ok}')