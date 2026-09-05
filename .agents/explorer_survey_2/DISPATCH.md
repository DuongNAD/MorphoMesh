# Survey Explorer 2 Dispatch

Assigned Role: Survey Explorer (R2 Architecture & R4 Implementation focus)
Working Directory: /Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_2
Original Request: /Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md

## 2026-09-05T11:23:40Z
You are Survey Explorer 2 for the MorphoMesh project.
Your working directory is: /Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_2
The authoritative user request is: /Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md
Please read ORIGINAL_REQUEST.md first!

Your mission:
Survey and investigate the system architecture, component boundaries, and implementation strategy for R2 (System Architecture & Pipeline Specification) and R4 (Runnable PoC & Blender Bridge):
1. macOS client environment (Apple Silicon M-series) interacting with Blender and Remote GPU backends.
2. Blender Communication layer:
   - Bidirectional socket/IPC client and headless `bpy` script runner.
   - Design safe protocol: localhost TCP socket or Unix domain socket vs headless CLI execution.
   - Security validation for Python scripts/commands before execution in Blender.
   - Command serialization format (JSON-RPC 2.0 style or structured JSON actions).
3. AI Inference layer:
   - Plug-and-play `inference_adapter.py` design supporting Mock/Offline mode (deterministic procedural mesh generation/test assets) and Remote GPU backends (Replicate, HuggingFace Inference Endpoints, custom Linux GPU server).
   - Local fallback capabilities on Apple Silicon (preprocessing, remeshing, mock testing).
4. Detailed 5-stage End-to-End Dataflow:
   Stage 1: Prompt Engineering & Concept Gen
   Stage 2: Single-image to 3D Generation
   Stage 3: Topology Optimization
   Stage 4: Skeleton & Rigging Automation
   Stage 5: Blender Scene Assembly
5. Blender Addon structure (`blender_addon/`) and packaging.

Write your comprehensive architectural survey to `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_2/survey_arch_report.md` and update your `progress.md` and `handoff.md`.
Communicate your completion back to the parent orchestrator via `send_message`.
Remember: Read-only exploration. Do not modify or create source code files.
