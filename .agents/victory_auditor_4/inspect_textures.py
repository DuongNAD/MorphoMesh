import os
from PIL import Image
import numpy as np

tex_dir = 'E:/tool/mcp/MorphoMesh/output/yu_nian_an/textures'
files = sorted([f for f in os.listdir(tex_dir) if f.endswith('.png')])

print('=== 4K PBR TEXTURES FORENSIC INSPECTION ===')
print(f'Directory: {tex_dir}')
print(f'Total textures found: {len(files)}')

for fn in files:
    fp = os.path.join(tex_dir, fn)
    size = os.path.getsize(fp)
    with Image.open(fp) as img:
        width, height = img.size
        mode = img.mode
        arr = np.array(img)
        min_v = np.min(arr)
        max_v = np.max(arr)
        mean_v = np.mean(arr)
        std_v = np.std(arr)
        
        is_4k = (width == 4096 and height == 4096)
        is_dynamic = (std_v > 0.1)
        
        status = 'PASS' if (is_4k and is_dynamic) else 'WARN'
        print(f'{status} | {fn:32s} | Size: {size:8,d} B | Res: {width}x{height} | Mode: {mode:5s} | Min: {min_v:3d}, Max: {max_v:3d}, Mean: {mean_v:6.2f}, Std: {std_v:6.2f}')
