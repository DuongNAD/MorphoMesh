import json
from pathlib import Path

source_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")
target_path = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\vegetation_pipeline\taxonomy_catalog.json")

with open(source_path, "r", encoding="utf-8") as f:
    catalog = json.load(f)

# 56-token universal negative prompt blacklist
UNIVERSAL_NEGATIVE_BLACKLIST = (
    "pot, planter, flowerpot, flower pot, plant pot, terracotta, container, vase, bowl, "
    "bucket, crate, dish, tray, saucer, pedestal, base stand, stand, ground soil box, "
    "square block, platform, roots in pot, indoor room, wall, background, floor, furniture, "
    "table, human, hands, person, people, man, woman, character, body, face, animal, insect, "
    "artificial plastic, artificial grass, low quality, deformed, floating leaves, "
    "disconnected branches, blurry, cartoon, toy, miniature, wireframe, baked lighting shadow, "
    "skeleton, bones, armature, rig, rigged, rigging, skinning, joints, watermark, text, logo"
)

# 6 prompt grounding fixes from M1 Explorer 2
PROMPT_FIXES = {
    "veg_tree_willow_01": (
        "Standalone 3D model of a majestic Weeping Willow tree (Salix babylonica), "
        "single isolated tree growing naturally from ground base, thick twisted dark-gray furrowed trunk, "
        "wide sweeping crown with long curtain-like pendulous branches cascading vertically towards the ground, "
        "dense flowing foliage of narrow lanceolate pale silvery-green leaves, soft organic weeping canopy silhouette, "
        "realistic botanical PBR texturing, clean natural structure, 8k resolution."
    ),
    "veg_tree_beech_01": (
        "Standalone 3D botanical asset of a stately European Beech tree (Fagus sylvatica), "
        "single mature tree growing naturally from ground base, smooth pale silver-gray elephantine bark trunk, "
        "wide rounded dome canopy with fan-like tiered horizontal branches, glossy elliptical wavy-edged deep-green leaves "
        "arranged in dense layered planes, natural organic canopy volume, photorealistic PBR material, "
        "realistic wood and leaf shaders, clean quad geometry."
    ),
    "veg_conifer_spruce_01": (
        "Standalone 3D model of an authentic Norway Spruce tree (Picea abies), "
        "single conical conifer tree rooted naturally at ground base, straight central trunk spire with flaky reddish-brown bark, "
        "tiered whorled horizontal branches with graceful drooping pendulous side twigs, dense dark-green needle foliage, "
        "hanging cylindrical pine cones, photorealistic conifer botanical asset, high fidelity PBR texture maps, realistic pine needle depth."
    ),
    "veg_conifer_cypress_01": (
        "Standalone 3D botanical model of an Italian Cypress (Cupressus sempervirens), "
        "single slender columnar evergreen tree growing naturally from ground base, pencil-thin flame silhouette, "
        "fibrous bark trunk anchored at ground level, tightly packed vertical branches, rich deep-green scale-like foliage texture "
        "with subtle surface depth, photorealistic Mediterranean vegetation, PBR materials, clean geometry."
    ),
    "veg_ground_moss_01": (
        "Standalone 3D model of a Forest Cushion Moss mound (Leucobryum glaucum), "
        "single rounded hemispherical dome of dense velvety pincushion moss resting naturally on forest ground base, "
        "micro-textured surface of millions of tiny packed emerald and glaucous-green moss leaflets, subtle organic surface undulations, "
        "photorealistic woodland groundcover, PBR normal and displacement maps, clean 3D geometry."
    ),
    "veg_epiphyte_spanishmoss_01": (
        "Standalone 3D botanical model of a cascading Spanish Moss cluster (Tillandsia usneoides), "
        "single dense epiphyte beard drapery cluster rooted at ground base with vertical self-supporting form, "
        "intricate zigzagging silvery-gray tendril strands, soft velvety micro-scale texture, "
        "authentic southern coastal swamp epiphyte, photorealistic botanical PBR materials, clean organic topology."
    )
}

# Apply updates
for sp in catalog["species"]:
    sp_id = sp["species_id"]
    # 1. Update negative prompt
    sp["meshy_spec"]["negative_prompt"] = UNIVERSAL_NEGATIVE_BLACKLIST
    # 2. Update positive prompt if in PROMPT_FIXES
    if sp_id in PROMPT_FIXES:
        sp["meshy_spec"]["positive_prompt"] = PROMPT_FIXES[sp_id]

target_path.parent.mkdir(parents=True, exist_ok=True)
with open(target_path, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

print(f"Successfully generated {target_path} with {len(catalog['species'])} species.")
