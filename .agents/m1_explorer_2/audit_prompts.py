import json
from pathlib import Path

catalog_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")
with open(catalog_path, encoding="utf-8") as f:
    data = json.load(f)

print(f"Auditing prompt conditioning for {len(data['species'])} species:\n")

ground_anchor_keywords = ["ground", "root", "soil", "base", "earth", "freestanding", "growing from", "anchored"]
standalone_keywords = ["standalone", "single", "isolated", "individual"]
pot_blacklist_keywords = ["pot", "planter", "flowerpot", "terracotta", "container", "vase", "pedestal", "base stand", "platform"]
human_blacklist_keywords = ["human", "person", "hands", "people"]

flagged = []

for idx, sp in enumerate(data["species"], 1):
    sp_id = sp["species_id"]
    pos = sp["meshy_spec"]["positive_prompt"]
    neg = sp["meshy_spec"]["negative_prompt"]
    pos_l = pos.lower()
    neg_l = neg.lower()
    
    # 1. Ground base check
    found_ground = [k for k in ground_anchor_keywords if k in pos_l]
    # 2. Standalone check
    found_standalone = [k for k in standalone_keywords if k in pos_l]
    # 3. Negative pot blacklist
    missing_pot_black = [k for k in pot_blacklist_keywords if k not in neg_l]
    # 4. Negative human blacklist
    missing_human_black = [k for k in human_blacklist_keywords if k not in neg_l]
    
    status = "OK"
    issues = []
    if not found_ground:
        issues.append("Missing explicit ground anchor keyword")
    if not found_standalone:
        issues.append("Missing standalone keyword")
    if missing_pot_black:
        issues.append(f"Missing pot blacklist tokens: {missing_pot_black}")
    if missing_human_black:
        issues.append(f"Missing human blacklist tokens: {missing_human_black}")
        
    print(f"[{idx:02d}] {sp_id} ({sp['common_name']}):")
    print(f"     Ground keywords: {found_ground}")
    print(f"     Standalone keywords: {found_standalone}")
    print(f"     Prompt: {pos[:110]}...")
    if issues:
        print(f"     WARNING: {issues}")
        flagged.append((sp_id, issues, pos))
    else:
        print(f"     Status: FULLY COMPLIANT")
    print()

print(f"Summary: {len(data['species']) - len(flagged)} fully compliant, {len(flagged)} flagged with potential improvements.")
if flagged:
    print("\nFlagged entries:")
    for f_id, f_iss, f_prompt in flagged:
        print(f"- {f_id}: {f_iss}")
        print(f"  Current prompt: {f_prompt}")
