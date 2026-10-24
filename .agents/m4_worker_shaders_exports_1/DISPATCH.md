# Task Dispatch — M4 Worker (Cycles Shaders, Full Repo Tests Remediation & Master Deliverables)

## Objective
Implement Features 16, 17, 18, 19, and 20 of Milestone 4 for MorphoMesh:
1. **Feature 16: Cycles Principled BSDF v2 Random Walk SSS & Shaders** (`src/morphomesh/human_materials.py`, `scripts/build_ultimate_yu_nian_an.py`):
   - Porcelain skin: `subsurface_method = 'RANDOM_WALK_SKIN'`, warm epidermal radius $(1.0, 0.45, 0.25)$, scale $0.002$ ($2\text{ mm}$), roughness $0.35$.
   - Dual-chamber refractive eyes: Cornea IOR $1.376$ with `ShaderNodeLightPath` transparent shadow bypass (`Is Shadow Ray` -> `MixShader` with `BsdfTransparent`); Iris IOR $1.336$ with centered radial stroma.
   - Silk sheen fabric: WhiteSilk sundress with sheen weight $0.60$, roughness $0.25$; IceBlue satin sash with metallic $0.08$, specular IOR $0.75$, sheen $0.90$, roughness $0.18$.
   - Emission: Crimson marionette strings emission $6.5$; Glowing butterflies emission $3.2$ with subsurface transmission $0.55$.
2. **Feature 17: Cycles AgX Studio Lighting & 5 Canonical Beauty Renders** (`scripts/build_ultimate_yu_nian_an.py`, `src/morphomesh/camera_rig.py`):
   - 3-Point Softbox Lighting: Key light $5500\text{ K}$ warm softbox ($120\text{ W}$, $(1.8, -2.0, 2.2)$); Fill light $6500\text{ K}$ cool softbox ($60\text{ W}$, $(-1.8, -1.9, 1.6)$); Rim/Hair light $4500\text{ K}$ ($110\text{ W}$, overhead at $(-0.35, 1.65, 2.35)$).
   - AgX view transform with High Contrast look.
   - Render the 5 canonical high-resolution beauty shots into `output/yu_nian_an/renders/`:
     1. `beauty_front.png`
     2. `beauty_three_quarter.png`
     3. `beauty_side.png`
     4. `beauty_back.png`
     5. `beauty_close_up.png`
3. **Feature 18: Strict Quality Verification** (`scripts/build_ultimate_yu_nian_an.py`):
   - Automated quality assertions: 0 signed distance penetrations between wardrobe and body mesh ($s_i \ge -0.0005$m), 100% outward normals ($c_x n_x + c_y n_y > 0$), 100% quads in deforming joints, and 0.000mm cord snapping.
4. **Feature 19: Full Repository Pytest Suite Remediation**:
   - Apply the drop-in patches documented in `E:\tool\mcp\MorphoMesh\.agents\m4_explorer_repo_tests_1\handoff.md` across the 5 root causes:
     - Group A: In `src/morphomesh/human_generator.py:resolve_human_anatomy_config()`, preserve Pydantic bypass when a config instance is passed or allow custom height bounds without re-validation error.
     - Group B: In `tests/test_adversarial_human_m3.py`, update float planar slicing to robust slice band `abs(z - 1.05*s) < 0.015*s` and canonical waist clearance assertion.
     - Group C: In `tests/test_adversarial_m2_iter2_empirics.py`, adapt finger vertex filter to resolve via landmark `joint-l-finger-1-1` or bounding box under `arm_span = 1.0`.
     - Group D: In `tests/test_e2e_human_anatomy.py`, fix olecranon protrusion sign/coordinate check and chin projection threshold.
     - Group E: In `tests/test_empiric_m1_rigging.py`, update literal count assertion (`plantar_arch_L in (40, 51)`).
   - Verify that 100% of all tests in `tests/` pass with exit code 0.
5. **Feature 20: Multi-Format Production Master Deliverables** (`output/yu_nian_an/`):
   - Re-export and verify master assets:
     - `output/yu_nian_an/Yu_Nian_An_Master.blend`
     - `output/yu_nian_an/Yu_Nian_An.glb`
     - `output/yu_nian_an/Yu_Nian_An.fbx`
     - 9 uncompressed 4K PBR textures in `output/yu_nian_an/textures/` (Skin Albedo/Normal/Roughness, Dress Albedo/Normal/Sheen, Sash Albedo/Metallic/Roughness).

## Reference Materials
- `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md` (Mandatory reading)
- `E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md`
- `E:\tool\mcp\MorphoMesh\.agents\m4_explorer_repo_tests_1\handoff.md`
- `E:\tool\mcp\MorphoMesh\.agents\m4_explorer_shaders_renders_1\handoff.md`
- `E:\tool\mcp\MorphoMesh\.agents\m4_explorer_master_exports_1\handoff.md`

## Verification Commands
- `uv run pytest tests/ -q` (Target: 100% pass, 0 failures)
- `uv run python scripts/build_ultimate_yu_nian_an.py`
- Verify existence of all master files and 5 render PNGs in `output/yu_nian_an/`
