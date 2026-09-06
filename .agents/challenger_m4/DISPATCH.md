# Task Assignment: Challenger M4 (Milestone M4 Adversarial Empirical Verification)

## Mission
Perform adversarial empirical stress-testing on Milestone M4 deliverables.

## Adversarial Verification Tasks
1. Execute `python3 verify_bear_anatomy.py` and `/Applications/Blender.app/Contents/MacOS/Blender --background examples/Armored_War_Bear_HD.blend --python verify_bear_anatomy.py`. Assert exit code 0.
2. Adversarially verify claw orientation math across all 20 claws: assert $\vec{d}_{\text{claw}} \cdot \vec{u}_{\text{fwd}} > 0.60$ and $d_z < 0$.
3. Adversarially verify all 18 vertex groups in Blender: assert genuine non-zero vertex allocations.
4. Adversarially verify armor clearance $d_{\min} \ge 0.015\text{m}$ across all 6 plates in the saved master `.blend` file.
5. Audit glTF binary structure of `examples/Armored_War_Bear_HD.glb` (glTF 2.0 chunk headers, meshes, materials).
6. Run `pytest -v tests/test_bear_anatomy.py`.
7. 

## 2026-09-05T21:26:38Z
You are Challenger M4 for Milestone M4 (Scene Assembly, Production Export, Verification Suite & Beauty Renders).
Your working directory is `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_m4`.
Read your dispatch at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_m4/DISPATCH.md`, `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md`, `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`, and Worker M4's handoff at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m4/handoff.md`.

Perform adversarial empirical verification:
1. Execute `python3 verify_bear_anatomy.py` and `/Applications/Blender.app/Contents/MacOS/Blender --background examples/Armored_War_Bear_HD.blend --python verify_bear_anatomy.py`. Assert exit code 0.
2. Adversarially verify claw orientation math across all 20 claws: assert dot product with forward axis > 0.60 and dz < 0.
3. Adversarially verify all 18 standardized vertex groups in Blender: assert genuine non-zero vertex allocations.
4. Adversarially verify armor clearance d_min >= 0.015m across all 6 plates in the saved master .blend file.
5. Audit glTF binary structure of `examples/Armored_War_Bear_HD.glb` (glTF 2.0 chunk headers, meshes, materials).
6. Run `pytest -v tests/test_bear_anatomy.py`.
Deliver your verdict (APPROVE or REJECT) in `handoff.md` and message orchestrator.
