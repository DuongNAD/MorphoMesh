"""
Empirical Texture Suite Stress Test & Channel Analysis
Verifies:
1. Exactly 9 textures present in output/yu_nian_an/textures/
2. Strictly 4096 x 4096 resolution for all 9 maps
3. Detailed statistical channel distribution of ORM and MaskMap
4. Cross-map channel mathematical coherence (UE ORM vs Unity MaskMap)
5. Normal map tangent-space vector validity
"""
from pathlib import Path
from PIL import Image
import numpy as np

tex_dir = Path("output/yu_nian_an/textures")
assert tex_dir.exists(), f"Directory not found: {tex_dir}"

expected_textures = [
    "Yu_Nian_An_BaseColor_4K.png",
    "Yu_Nian_An_Normal_4K.png",
    "Yu_Nian_An_Roughness_4K.png",
    "Yu_Nian_An_Metallic_4K.png",
    "Yu_Nian_An_SSS_4K.png",
    "Yu_Nian_An_Alpha_4K.png",
    "Yu_Nian_An_Height_4K.png",
    "Yu_Nian_An_ORM_4K.png",
    "Yu_Nian_An_MaskMap_4K.png"
]

all_pngs = sorted(list(tex_dir.glob("*.png")))
print(f"Found {len(all_pngs)} PNG textures in {tex_dir}")
assert len(all_pngs) == 9, f"Expected exactly 9 textures, found {len(all_pngs)}: {[p.name for p in all_pngs]}"

for exp_name in expected_textures:
    p = tex_dir / exp_name
    assert p.exists(), f"Missing texture: {exp_name}"

print("\n--- RESOLUTION & MODE INSPECTION ---")
texture_images = {}
for p in all_pngs:
    img = Image.open(p)
    w, h = img.size
    print(f"  {p.name:30s} | Size: {w:4d}x{h:4d} | Mode: {img.mode:5s} | FileSize: {p.stat().st_size:,} bytes")
    assert w == 4096 and h == 4096, f"Texture {p.name} has invalid dimensions: {w}x{h}"
    texture_images[p.name] = img

# Channel analysis for ORM
print("\n--- ORM (UNREAL ENGINE) CHANNEL DISTRIBUTION ---")
orm_img = texture_images["Yu_Nian_An_ORM_4K.png"]
assert orm_img.mode in ("RGBA", "RGB"), f"Unexpected ORM mode: {orm_img.mode}"
orm_arr = np.array(orm_img)

ao_ch = orm_arr[:, :, 0]
rough_ch = orm_arr[:, :, 1]
metal_ch = orm_arr[:, :, 2]
sss_ch = orm_arr[:, :, 3] if orm_arr.shape[2] > 3 else None

print(f"  R (Ambient Occlusion): min={ao_ch.min()}, max={ao_ch.max()}, mean={ao_ch.mean():.2f}, std={ao_ch.std():.2f}")
print(f"  G (Roughness)        : min={rough_ch.min()}, max={rough_ch.max()}, mean={rough_ch.mean():.2f}, std={rough_ch.std():.2f}")
print(f"  B (Metallic)         : min={metal_ch.min()}, max={metal_ch.max()}, mean={metal_ch.mean():.2f}, std={metal_ch.std():.2f}")
if sss_ch is not None:
    print(f"  A (SSS Mask)         : min={sss_ch.min()}, max={sss_ch.max()}, mean={sss_ch.mean():.2f}, std={sss_ch.std():.2f}")

# Sanity assertions on ORM
assert ao_ch.min() < 100, f"Expected deep occlusion in crevices, but min AO is {ao_ch.min()}"
assert ao_ch.max() == 255, f"Expected full exposure in open areas, but max AO is {ao_ch.max()}"
assert rough_ch.min() > 0 and rough_ch.max() < 255, f"Roughness extreme values abnormal: min={rough_ch.min()}, max={rough_ch.max()}"
assert metal_ch.mean() < 50, f"Character mostly dielectric skin/fabric, metallic mean unexpectedly high: {metal_ch.mean()}"
if sss_ch is not None:
    assert sss_ch.max() > 150, f"Expected strong SSS on ears/nose, but max SSS is {sss_ch.max()}"

# Channel analysis for MaskMap
print("\n--- MASKMAP (UNITY HDRP) CHANNEL DISTRIBUTION ---")
mask_img = texture_images["Yu_Nian_An_MaskMap_4K.png"]
assert mask_img.mode in ("RGBA", "RGB"), f"Unexpected MaskMap mode: {mask_img.mode}"
mask_arr = np.array(mask_img)

m_metal_ch = mask_arr[:, :, 0]
m_ao_ch = mask_arr[:, :, 1]
m_detail_ch = mask_arr[:, :, 2]
m_smooth_ch = mask_arr[:, :, 3] if mask_arr.shape[2] > 3 else None

print(f"  R (Metallic)         : min={m_metal_ch.min()}, max={m_metal_ch.max()}, mean={m_metal_ch.mean():.2f}, std={m_metal_ch.std():.2f}")
print(f"  G (Ambient Occlusion): min={m_ao_ch.min()}, max={m_ao_ch.max()}, mean={m_ao_ch.mean():.2f}, std={m_ao_ch.std():.2f}")
print(f"  B (Detail / SSS)     : min={m_detail_ch.min()}, max={m_detail_ch.max()}, mean={m_detail_ch.mean():.2f}, std={m_detail_ch.std():.2f}")
if m_smooth_ch is not None:
    print(f"  A (Smoothness)       : min={m_smooth_ch.min()}, max={m_smooth_ch.max()}, mean={m_smooth_ch.mean():.2f}, std={m_smooth_ch.std():.2f}")

# Cross-coherence check between ORM and MaskMap
print("\n--- CROSS-MAP MATHEMATICAL COHERENCE ---")
metal_diff = np.abs(m_metal_ch.astype(int) - metal_ch.astype(int)).max()
ao_diff = np.abs(m_ao_ch.astype(int) - ao_ch.astype(int)).max()
print(f"  Max absolute difference (MaskMap.R vs ORM.B - Metallic) : {metal_diff}")
print(f"  Max absolute difference (MaskMap.G vs ORM.R - AO)       : {ao_diff}")
assert metal_diff == 0, f"Metallic channels differ between MaskMap and ORM: diff={metal_diff}"
assert ao_diff == 0, f"AO channels differ between MaskMap and ORM: diff={ao_diff}"

if sss_ch is not None and m_detail_ch is not None:
    sss_diff = np.abs(m_detail_ch.astype(int) - sss_ch.astype(int)).max()
    print(f"  Max absolute difference (MaskMap.B vs ORM.A - SSS)      : {sss_diff}")
    assert sss_diff == 0, f"SSS channels differ between MaskMap and ORM: diff={sss_diff}"

    # Smoothness is computed as clip((1.0 - roughness) * 255) vs uint8 roughness.
    # Due to floating point truncation (e.g. 0.38*255=96.9 -> 96 and 0.62*255=158.1 -> 158), sum can be 254 (diff=1).
    smooth_expected = 255 - rough_ch.astype(int)
    smooth_diff = np.abs(m_smooth_ch.astype(int) - smooth_expected).max()
    print(f"  Max absolute difference (MaskMap.A vs (255 - ORM.G))    : {smooth_diff} (acceptable <= 1 due to float truncation)")
    assert smooth_diff <= 1, f"Smoothness channel does not match (255 - Roughness): diff={smooth_diff}"

# Normal Map Tangent Space Validation
print("\n--- NORMAL MAP TANGENT SPACE VALIDATION ---")
norm_img = texture_images["Yu_Nian_An_Normal_4K.png"]
norm_arr = np.array(norm_img).astype(np.float32)
# Normal vector in [-1, 1]
norm_vec = (norm_arr / 255.0) * 2.0 - 1.0
lengths = np.sqrt(np.sum(norm_vec**2, axis=-1))
print(f"  Normal lengths: min={lengths.min():.4f}, max={lengths.max():.4f}, mean={lengths.mean():.4f}")
print(f"  Normal Z (blue channel) min={norm_arr[:,:,2].min()}, max={norm_arr[:,:,2].max()}, mean={norm_arr[:,:,2].mean():.2f}")
assert norm_arr[:,:,2].mean() > 200, f"Normal map Z mean is unexpectedly low: {norm_arr[:,:,2].mean()}"

print("\n=== TEXTURE SUITE STRESS TEST: ALL CHECKS PASSED PERFECTLY ===")
