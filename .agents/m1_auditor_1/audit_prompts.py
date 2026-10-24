import json
from pathlib import Path

p = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\vegetation_pipeline\taxonomy_catalog.json")
with open(p, "r", encoding="utf-8") as f:
    data = json.load(f)

print("=== CHECKING PROMPTS AND NEGATIVE TOKENS ===")
tokens_56 = [
    "pot", "planter", "flowerpot", "flower pot", "plant pot", "terracotta", "container", "vase", "bowl",
    "bucket", "crate", "dish", "tray", "saucer", "pedestal", "base stand", "stand", "ground soil box",
    "square block", "platform", "roots in pot", "indoor room", "wall", "background", "floor", "furniture",
    "table", "human", "hands", "person", "people", "man", "woman", "character", "body", "face", "animal", "insect",
    "artificial plastic", "artificial grass", "low quality", "deformed", "floating leaves",
    "disconnected branches", "blurry", "cartoon", "toy", "miniature", "wireframe", "baked lighting shadow",
    "skeleton", "bones", "armature", "rig", "rigged", "rigging", "skinning", "joints", "watermark", "text", "logo"
]

all_negative_ok = True
for s in data["species"]:
    sp_id = s["species_id"]
    neg = s["meshy_spec"]["negative_prompt"].lower()
    missing = [t for t in tokens_56 if t not in neg]
    if missing:
        print(f"FAILED {sp_id}: missing negative tokens {missing}")
        all_negative_ok = False

print(f"All 35 species contain all 56 negative tokens: {all_negative_ok}")

print("\n=== CHECKING 6 GROUND-ANCHORING PROMPT ENHANCEMENTS ===")
anchor_targets = {
    "veg_tree_willow_01": "growing naturally from ground base",
    "veg_tree_beech_01": "rooted naturally at ground base",
    "veg_conifer_spruce_01": "growing naturally from forest ground base",
    "veg_conifer_cypress_01": "rooted directly in ground base",
    "veg_ground_moss_01": "resting naturally on forest ground base",
    "veg_epiphyte_spanishmoss_01": "rooted at ground base with vertical self-supporting form",
}

for sp_id, expected_anchor in anchor_targets.items():
    sp = next((s for s in data["species"] if s["species_id"] == sp_id), None)
    if sp:
        pos = sp["meshy_spec"]["positive_prompt"].lower()
        if expected_anchor.lower() in pos:
            print(f"PASS: {sp_id} has anchor '{expected_anchor}'")
        else:
            print(f"FAIL: {sp_id} MISSING anchor '{expected_anchor}'. Prompt snippet: {pos[:100]}...")
    else:
        print(f"FAIL: {sp_id} not found")

print("\n=== CHECKING PROMPT UNIQUENESS ===")
prompts = [s["meshy_spec"]["positive_prompt"] for s in data["species"]]
unique_prompts = set(prompts)
print(f"Total positive prompts: {len(prompts)}, Unique: {len(unique_prompts)}")
lengths = [len(p) for p in prompts]
print(f"Min length: {min(lengths)}, Max length: {max(lengths)}, Avg length: {sum(lengths)/len(lengths):.1f}")

print("\n=== SAMPLE POSITIVE PROMPTS (First 3) ===")
for s in data["species"][:3]:
    print(f"\n[{s['species_id']}]: {s['meshy_spec']['positive_prompt']}")
