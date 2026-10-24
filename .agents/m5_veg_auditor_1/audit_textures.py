from pathlib import Path
import numpy as np
from PIL import Image

out_dir = Path('teamwork_projects/vegetation_library/output')
tex_dirs = sorted(out_dir.glob('*/*/textures'))
print(f'Total texture directories found: {len(tex_dirs)}')

channels = ['albedo', 'normal', 'roughness', 'metallic']
all_valid = True
sample_metrics = []

for td in tex_dirs:
    sp_name = td.parent.name
    for ch in channels:
        p = td / f'{ch}.png'
        if not p.is_file():
            print(f'MISSING TEXTURE: {sp_name} missing {ch}.png')
            all_valid = False
            continue
        try:
            img = Image.open(p)
            img.load()
            w, h = img.size
            if w < 256 or h < 256:
                print(f'LOW RES: {sp_name} {ch}.png resolution {w}x{h} < 256x256')
                all_valid = False
        except Exception as e:
            print(f'CORRUPT IMAGE: {sp_name} {ch}.png: {e}')
            all_valid = False

    alb = np.array(Image.open(td / 'albedo.png').convert('RGB'), dtype=np.float32) / 255.0
    norm = np.array(Image.open(td / 'normal.png').convert('RGB'), dtype=np.float32) / 255.0
    rough = np.array(Image.open(td / 'roughness.png').convert('L'), dtype=np.float32) / 255.0
    metal = np.array(Image.open(td / 'metallic.png').convert('L'), dtype=np.float32) / 255.0

    alb_mean = float(np.mean(alb))
    alb_std = float(np.mean(np.std(alb, axis=(0, 1))))
    nz_mean = float(np.mean(2.0 * norm[:, :, 2] - 1.0))
    rough_mean = float(np.mean(rough))
    metal_max = float(np.max(metal))

    if alb_mean <= 0.05 or alb_std <= 0.02:
        print(f'INVALID ALBEDO: {sp_name} mean={alb_mean}, std={alb_std}')
        all_valid = False
    if not (0.5 <= nz_mean <= 1.0):
        print(f'INVALID NORMAL: {sp_name} nz_mean={nz_mean}')
        all_valid = False
    if not (0.20 <= rough_mean <= 0.95):
        print(f'INVALID ROUGHNESS: {sp_name} rough_mean={rough_mean}')
        all_valid = False
    if metal_max > 0.05:
        print(f'INVALID METALLIC: {sp_name} metal_max={metal_max}')
        all_valid = False

    sample_metrics.append((sp_name, alb_mean, alb_std, nz_mean, rough_mean, metal_max))

print(f'All 140 PBR textures present, readable, sized >=256x256, and physically plausible: {all_valid}')
print('\nTexture metric samples (first 7 species across biomes):')
for m in sample_metrics[:7]:
    print(f'{m[0]:<25} / Alb mean: {m[1]:.3f}, std: {m[2]:.3f} / Norm nz: {m[3]:.3f} / Rough: {m[4]:.3f} / Metal max: {m[5]:.3f}')