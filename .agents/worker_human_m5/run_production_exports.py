import json
import os
import sys
from morphomesh.character_assembler import export_production_assets

print("=== RUNNING FULL PRODUCTION ASSETS EXPORT ===")
result = export_production_assets(
    blend_path="output/yu_nian_an/Yu_Nian_An_Master.blend",
    output_dir="output/yu_nian_an",
    character_name="Yu_Nian_An",
    export_fbx=True,
    export_glb=True,
    generate_textures=True,
    generate_docs=True,
    texture_resolution=4096,
)

print("\n=== PRODUCTION EXPORT RESULT ===")
print(json.dumps(result, indent=2))

# Verify files on disk
print("\n=== VERIFYING PRODUCED FILES ===")
expected_files = [
    "output/yu_nian_an/Yu_Nian_An_Master.blend",
    "output/yu_nian_an/Yu_Nian_An.fbx",
    "output/yu_nian_an/Yu_Nian_An.glb",
    "output/yu_nian_an/README_EXPORT.md",
    "output/yu_nian_an/textures/Yu_Nian_An_BaseColor_4K.png",
    "output/yu_nian_an/textures/Yu_Nian_An_Normal_4K.png",
    "output/yu_nian_an/textures/Yu_Nian_An_Roughness_4K.png",
    "output/yu_nian_an/textures/Yu_Nian_An_Metallic_4K.png",
    "output/yu_nian_an/textures/Yu_Nian_An_SSS_4K.png",
    "output/yu_nian_an/textures/Yu_Nian_An_Alpha_4K.png",
    "output/yu_nian_an/textures/Yu_Nian_An_Height_4K.png",
]

all_exist = True
for f in expected_files:
    exists = os.path.exists(f)
    size = os.path.getsize(f) if exists else 0
    print(f"File: {f:<60} | Exists: {str(exists):<5} | Size: {size / 1024 / 1024:.2f} MB")
    if not exists or size == 0:
        all_exist = False

print(f"\nALL ASSETS PRESENT AND NON-ZERO: {all_exist}")
if not all_exist:
    sys.exit(1)
