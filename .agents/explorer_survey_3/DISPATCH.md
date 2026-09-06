# Dispatch Assignment: Explorer Survey 3 (Fur, Shading, Armor & Verification)

**Identity**: teamwork_preview_explorer
**Assigned Task**: Fur, Shading, War Armor, and Verification Infrastructure Survey
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_3`
**Authoritative Request**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md` (read section `## 2026-09-05T15:44:52Z` carefully)
**Project Root**: `/Users/duongnad/Documents/tool/MorphoMesh`

## Objectives
1. Read `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`.
2. Investigate R2 (Volumetric Fur & Grooming):
   - Multi-layer volumetric hair curves / particles (>= 10,000 strands, dense undercoat + coarse guard hairs).
   - Biological growth flow along dorsal spine radiating down torso, shoulders, and limbs.
   - Thickness, clumping, tapering in Blender.
3. Investigate R3 (PBR Material Suite & War Armor):
   - 4-channel PBR setup (Albedo, Normal/Displacement, Roughness, Metallic) in Blender Principled BSDF.
   - Distinct material slots for fur, skin/nose/eyes, claws (keratin), weathered metallic armor (steel plates + brass/gold accents).
   - Armor geometry fitting dorsal shoulders and wrists without degenerate self-intersection.
4. Investigate R4 (Multi-Angle Verification & Production Export):
   - Programmatic inspection script `verify_bear_anatomy.py` (has it been drafted? where should it live? what are the exact assertion formulas?).
   - Rendering setup (camera angles: Front 3/4, Head close-up, Paw/claw close-up, Full body; lighting, resolution).
   - Export pipeline for `examples/Armored_War_Bear_HD.glb` and `.blend` scene.
5. Write a comprehensive report to `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_3/survey_report.md` and deliver `handoff.md`.

## 2026-09-05T15:46:54Z

Investigate:
1. R2 Volumetric Fur & Hair Grooming: how to create >= 10,000 strands in Blender (dense undercoat + coarse guard hairs) with biological flow along the spine/torso, realistic clumping, tapering, and thickness.
2. R3 4-channel PBR material setup (Albedo, Normal/Displacement, Roughness, Metallic) for fur, skin/nose, claws, and weathered steel/brass war armor fitted to shoulders and wrists.
3. R4 Production export (`examples/Armored_War_Bear_HD.glb`, `.blend` scene) and automated verification script `verify_bear_anatomy.py` (exact mathematical assertion checks for claw orientation, feature vertex groups, fur density).
4. Camera viewpoints and rendering pipeline for the 4 required beauty renders (Front 3/4 perspective, Head close-up, Paw/claw close-up, Full body).
5. Document all findings in `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_3/survey_report.md` and write a standard `handoff.md`.
Communicate back to orchestrator via send_message when done.

## 2026-09-05T15:48:14Z
**Sender**: 504d045c-25c5-48a2-a65a-2a5b368eafa7 (parent)
**Context**: Armored War Bear Task Scope Clarification
**Content**: Urgent scope clarification from User/Sentinel: The objective is NOT merely to create one static Armored War Bear model. The primary goal is to upgrade the MorphoMesh ENGINE ITSELF (`src/morphomesh/` - procedural mesh generators in `inference_adapter.py`, connectors like `anycreature_connector.py`, `trellis_connector.py`, `blender_bridge.py`, and fur/grooming pipelines) so that MorphoMesh can generate high-fidelity, photorealistic creatures in general! Key engine requirements: (1) Reusable Anatomy Generator, (2) Reusable Volumetric Fur/Hair Curves pipeline in MorphoMesh Blender bridge/pipeline, (3) Organic PBR shader engine, (4) Armored War Bear as canonical test benchmark and demonstration. See `ORIGINAL_REQUEST.md` § 2026-09-05T15:47:35Z.
**Action**: Factor this engine-level architectural requirement into your investigation, findings, and survey report. Focus on how hair curves, PBR materials, and verification are built as reusable engine modules in `src/morphomesh/`.

