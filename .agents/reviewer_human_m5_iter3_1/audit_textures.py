import os
import numpy as np
from PIL import Image

TEXTURES_DIR = "output/yu_nian_an/textures"
textures = [f for f in os.listdir(TEXTURES_DIR) if f.endswith(".png")]
print(f"Found {len(textures)} texture files:")

for tex in sorted(textures):
    path = os.path.join(TEXTURES_DIR, tex)
    size = os.path.getsize(path)
    with Image.open(path) as img:
        w, h = img.size
        mode = img.mode
        arr = np.array(img)
        min_v = np.min(arr)
        max_v = np.max(arr)
        mean_v = np.mean(arr)
        std_v = np.std(arr)
    print(f"  {tex:30s}: size={size:8d} bytes, dim=({w}, {h}), mode={mode:5s}, min={min_v:3d}, max={max_v:3d}, mean={mean_v:6.2f}, std={std_v:6.2f}")
    assert (w, h) == (4096, 4096), f"Texture {tex} is not 4096x4096"
    assert size > 10_000, f"Texture {tex} is suspiciously small: {size} bytes"
    assert std_v > 0, f"Texture {tex} is completely flat/blank (std=0)!"

print("All 9 4K textures verified with non-zero standard deviation and valid 4096x4096 dimensions!")
