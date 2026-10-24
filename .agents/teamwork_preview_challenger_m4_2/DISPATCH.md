# Task Assignment: Challenger M4-2 (Adversarial PurePythonBVHTree & Visual Critic Stress Testing)

## Context
Milestone 4: Character Assembler & Visual Quality Critic Subsystems Modularization.

## Mission
Adversarially challenge and stress-test the visual quality critic subsystem:
1. Stress test `src/morphomesh/critic/`:
   - `PurePythonBVHTree`: construction on empty/point/collinear meshes, ray casting edge cases, nearest-neighbor searches, degenerate triangles.
   - Geometry math: Möller–Trumbore ray-triangle intersections, Eberly point-triangle distances, unit normal and barycentric coordinates under extreme scale perturbations.
   - Defect evaluators: cloth-body penetration, proportion metrics (golden ratio, head-to-body ratios), extreme deformation volume loss.
   - Benchmark defect detection and quality reporter generation.
2. Run test suites:
   `uv run pytest tests/test_visual_critic.py tests/test_adversarial_critic_benchmark.py tests/test_adversarial_bvh_penetration.py -v`
3. Issue formal verdict: CONFIRM_CORRECTNESS or REJECT.

## Deliverables
Save stress test report and verdict to `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_challenger_m4_2\handoff.md`.
Send message to orchestrator when finished.

## 2026-09-09T07:46:12Z
You are Challenger M4-2 for Milestone 4. Your working directory is E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_challenger_m4_2. Read your task assignment in E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_challenger_m4_2\DISPATCH.md, PROJECT.md at E:\tool\mcp\MorphoMesh\.agents\orchestrator_modularization_1\PROJECT.md, and ORIGINAL_REQUEST.md at E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md. Adversarially challenge PurePythonBVHTree, Möller-Trumbore ray tracing, penetration detection, and proportion metrics. Run test suites. Record test logs and verdict (CONFIRM_CORRECTNESS / REJECT) in handoff.md. Send a message to orchestrator when finished.
