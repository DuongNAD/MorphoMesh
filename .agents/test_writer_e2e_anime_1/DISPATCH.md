# Dispatch for test_writer_e2e_anime_1

## 2026-09-09T14:54:27Z
You are test_writer_e2e_anime_1, the E2E Test Track Architect & Writer for the Anime Character Pipeline project.

Working Directory: E:\tool\mcp\MorphoMesh\.agents\test_writer_e2e_anime_1
Target Project Directory: E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\ORIGINAL_REQUEST.md
Project Scope Document: E:\tool\mcp\MorphoMesh\.agents\orchestrator_anime_1\PROJECT.md

YOUR TASK:
1. Read ORIGINAL_REQUEST.md and PROJECT.md carefully. Understand the 4 requirements R1, R2, R3, R4 and features F01-F23.
2. Formulate the E2E Test Suite Architecture following the 4-tier methodology:
   - Tier 1: Feature Coverage (isolated verification of each feature)
   - Tier 2: Boundary Value Analysis & Corner Cases (joint rotation limits, volume preservation thresholds, extreme inputs)
   - Tier 3: Cross-Feature Interactions (pairwise combinations: mesh+rig, rig+twist+DQS, animation+skirt physics, shading+outline)
   - Tier 4: Real-World Workload Scenarios (Full Game-Ready asset export, headless Full HD 1080p MP4 render, rig quality audit, volume deformation audit)
3. Create TEST_INFRA.md at `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\TEST_INFRA.md`.
4. Implement the test files in `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\tests\`:
   - `test_tier1_features.py`
   - `test_tier2_boundaries.py`
   - `test_tier3_interactions.py`
   - `test_tier4_workloads.py`
5. Test suite must be runnable via `uv run pytest` from `E:\tool\mcp\MorphoMesh`. Provide clean mock / progressive testability so tests can run as milestones complete.
6. Once the test infrastructure and test suites are written and verified, create `TEST_READY.md` at `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\TEST_READY.md`.
7. Write `progress.md` and a complete `handoff.md` in your working directory. Notify your parent when complete.

CONSTRAINTS:
- Do NOT write or modify pipeline implementation code (`anime_pipeline/*`). You only author tests and test documentation.
- Maintain strict integrity. Every test must genuinely verify requirements.
