# Task Assignment: Worker M4-2 (Milestone 4 Finalization & Verification)

## Context
Milestone 4: Character Assembler & Visual Quality Critic Subsystems Modularization.
Worker M4-1 has already created the modular files:
- `src/morphomesh/assembler/` (`__init__.py`, `assembler.py`, `packager.py`, `pbr_baker.py`, `scene_builder.py`)
- `src/morphomesh/critic/` (`__init__.py`, `bvh.py`, `deformation.py`, `geometry_math.py`, `penetration.py`, `proportions.py`, `reporter.py`)
- Root facades `src/morphomesh/character_assembler.py` and `src/morphomesh/visual_critic.py`

## Mission
1. Inspect the modular code and facades created in `assembler/` and `critic/`.
2. Verify that 100% of symbols are re-exported by the facades with exact `__all__` parity and object identity.
3. Check for circular imports across all modules:
   `uv run python -c "import morphomesh.assembler, morphomesh.critic, morphomesh.character_assembler, morphomesh.visual_critic; print('M4 imports verified!')"`
4. Run the test suites:
   `uv run pytest tests/test_character_assembler.py tests/test_adversarial_character_assembler.py tests/test_visual_critic.py tests/test_adversarial_critic_benchmark.py tests/test_adversarial_bvh_penetration.py -v`
   `uv run pytest tests/test_production_exports.py tests/test_e2e_final_pipeline.py -v`
5. If any test or import fails, make any necessary adjustments to the modular files or facades.
6. MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work.
7. Record your findings, test logs, and formal verification in `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m4_2\handoff.md`.
8. Send a message to orchestrator when finished.
