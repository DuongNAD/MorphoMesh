# Dispatch Assignment: Explorer Survey 1 (Codebase & Blender Infrastructure)

**Identity**: teamwork_preview_explorer
**Assigned Task**: Codebase and Blender Bridge Survey for Armored War Bear Task
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_1`
**Authoritative Request**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md` (read section `## 2026-09-05T15:44:52Z` carefully)
**Project Root**: `/Users/duongnad/Documents/tool/MorphoMesh`

## Objectives
1. Read `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`.
2. Inspect the MorphoMesh codebase (`src/morphomesh/`, `blender_addon/`, `tests/`, `examples/`).
3. Determine how Blender is accessed and executed: check `blender_bridge.py`, MCP tools, CLI availability (`blender` command), python environment, and headless execution capabilities.
4. Check Blender version and API capabilities (specifically support for Curves / new Hair system vs legacy hair particles, Principled BSDF v2, glTF export).
5. Document all technical constraints, execution entry points, and dependencies.
6. Write a comprehensive report to `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_1/survey_report.md` and deliver `handoff.md`.

## 2026-09-05T15:46:54Z
You are Explorer 1 (Codebase & Blender Infrastructure Specialist) for the Armored War Bear task.
Your working directory is `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_1`.
Please read `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md` (specifically section `## 2026-09-05T15:44:52Z`) and your dispatch assignment at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_1/DISPATCH.md`.

Investigate:
1. The MorphoMesh repository structure, python environment, MCP tools, and `blender_bridge.py`.
2. Availability and version of Blender CLI (`blender` command), headless execution, python `bpy` capabilities.
3. Determine how scripts can be safely and reproducibly run in Blender to generate assets and tests.
4. Document all findings in `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_1/survey_report.md` and write a standard `handoff.md`.
Communicate back to orchestrator via send_message when done.

## 2026-09-05T15:48:04Z
**Sender**: 504d045c-25c5-48a2-a65a-2a5b368eafa7 (parent)
**Context**: Armored War Bear Task Scope Clarification
**Content**: Urgent scope clarification from User/Sentinel: The objective is NOT merely to create one static Armored War Bear model. The primary goal is to upgrade the MorphoMesh ENGINE ITSELF (`src/morphomesh/` - procedural mesh generators in `inference_adapter.py`, connectors like `anycreature_connector.py`, `trellis_connector.py`, `blender_bridge.py`, and fur/grooming pipelines) so that MorphoMesh can generate high-fidelity, photorealistic creatures in general! Key engine requirements: (1) Reusable Anatomy Generator with forward-curving claws and organic facial structures, (2) Volumetric Fur/Hair Curves pipeline in Blender bridge, (3) Organic PBR shader engine, (4) Armored War Bear as canonical test benchmark and demonstration. See `ORIGINAL_REQUEST.md` § 2026-09-05T15:47:35Z.
**Action**: Factor this engine-level architectural requirement into your investigation, findings, and survey report.


