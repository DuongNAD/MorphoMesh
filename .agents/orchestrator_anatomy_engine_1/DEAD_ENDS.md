# DEAD ENDS LOG

| Iteration | Approach Tried | Why It Failed | Files Touched |
|-----------|---------------|---------------|---------------|
| M2-Iter1 | Blanket 6-connected voxel dilation in `_build_voxel_grid` | Dilating solid voxels by 1 cell across the entire volume bridges narrow air gaps (1.5 - 2.5 cm) between opposing surfaces (axilla and inner thighs), fusing them into solid flesh and allowing geodesic diffusion to cross empty air. | `src/morphomesh/anatomy/skinning.py` |
| M2-Iter1 | Naive Euclidean fallback for unweighted/disconnected surface vertices (`geo_dist == inf`) | When surface voxels disconnect from bone seeds, falling back to minimum Euclidean distance assigns lateral torso vertices (x = 0.10m) to upper arm (x = 0.165m, dist 0.065m) instead of spine (dist 0.10m), resulting in 100% weight stealing. | `src/morphomesh/anatomy/skinning.py` |
| M2-Iter2 | Running experimental/prototype recreation scripts (`scripts/test_beauty_recreation.py`) that write directly to `output/yu_nian_an/` | Overwrites master production deliverables (`Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, `Yu_Nian_An.fbx`) with prototype objects (`Beauty_Armature`, missing 163 DEF bones and 52 shape keys), causing 17 test regressions in production export suites. Must quarantine prototype exports to `output/beauty_test/` and regenerate master deliverables via canonical `CharacterAssembler().assemble_and_export()`. | `scripts/test_beauty_recreation.py`, `output/yu_nian_an/` |

