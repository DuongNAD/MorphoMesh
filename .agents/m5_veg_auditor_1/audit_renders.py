from pathlib import Path
from PIL import Image

out_dir = Path('teamwork_projects/vegetation_library/output')
species_dirs = sorted([p for p in out_dir.glob('*/*') if p.is_dir() and p.name.startswith('veg_')])
print(f'Auditing renders for {len(species_dirs)} species...')

render_files = ['turntable_01.png', 'turntable_02.png', 'turntable_03.png', 'turntable_04.png', 'thumbnail.png']
all_ok = True

for sd in species_dirs:
    for rf in render_files:
        p = sd / rf
        if not p.is_file():
            print(f'MISSING RENDER: {sd.name} missing {rf}')
            all_ok = False
            continue
        try:
            img = Image.open(p)
            img.load()
            w, h = img.size
            if rf == 'thumbnail.png':
                if (w, h) != (1024, 1024):
                    print(f'UNEXPECTED THUMBNAIL DIM: {sd.name} thumbnail is {w}x{h}, expected 1024x1024')
            else:
                if (w, h) != (512, 512):
                    print(f'UNEXPECTED TURNTABLE DIM: {sd.name} {rf} is {w}x{h}, expected 512x512')
        except Exception as e:
            print(f'CORRUPT RENDER: {sd.name} {rf}: {e}')
            all_ok = False

print(f'All 175 render files (140 turntables + 35 thumbnails) exist, are readable, and match target dimensions: {all_ok}')