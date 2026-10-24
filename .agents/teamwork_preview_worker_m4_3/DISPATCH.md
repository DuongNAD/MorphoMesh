# Task Assignment: Worker M4-3 (Milestone 4 Iteration 2 Remediation)

## Context
Milestone 4: Character Assembler & Visual Quality Critic Subsystems Modularization.
Challenger M4-2 and Auditor M4-1 discovered missing imports in `src/morphomesh/critic/`.

## Authoritative Feedback from Challenger M4-2 & Auditor M4-1
1. `src/morphomesh/critic/penetration.py` (lines 143, 168, 373, 394, 409):
   References `HAS_BLENDER` and `bpy` without importing them.
   Fix: Add `from .bvh import HAS_BLENDER, bpy`
2. `src/morphomesh/critic/proportions.py` (line 124):
   References `HAS_BLENDER` and `bpy` without importing them.
   Fix: Add `from .bvh import HAS_BLENDER, bpy`
3. `src/morphomesh/critic/deformation.py` (line 309):
   References `HAS_BLENDER` and `bpy` without importing them.
   Fix: Add `from .bvh import HAS_BLENDER, bpy`
4. `src/morphomesh/critic/reporter.py` (line 406):
   Calls `evaluate_rig_skinning_pinch` without importing it from `.deformation`.
   Fix: Add `evaluate_rig_skinning_pinch` to `from .deformation import ...` in `reporter.py`.

## Verification Commands
After applying these 4 fixes, run the reproduction commands:
```bash
# Verify no NameError on fallback object lookup:
uv run python -c "from morphomesh.critic.penetration import evaluate_mesh_penetration; res = evaluate_mesh_penetration('Body', ['Garment']); assert res == []; print('Penetration check passed!')"
uv run python -c "from morphomesh.critic.proportions import evaluate_body_proportions; res = evaluate_body_proportions('Body'); print('Proportions check passed!')"
uv run python -c "from morphomesh.critic.deformation import evaluate_rig_skinning_pinch; res = evaluate_rig_skinning_pinch('Rig', 'Mesh'); assert res == []; print('Deformation check passed!')"
uv run python -c "from morphomesh.critic.reporter import run_visual_critique; print('Reporter imports check passed!')"

# Run all critic test suites:
uv run pytest tests/test_visual_critic.py tests/test_adversarial_critic_benchmark.py tests/test_adversarial_bvh_penetration.py tests/test_challenger_m4_critic_stress.py -v

# Run full M4 regression:
uv run pytest tests/test_character_assembler.py tests/test_adversarial_character_assembler.py tests/test_production_exports.py tests/test_challenger_m4_1_assembler_adversarial.py -v
```

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work.

Record your work in `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_worker_m4_3\handoff.md`.
Send message to orchestrator when finished.
