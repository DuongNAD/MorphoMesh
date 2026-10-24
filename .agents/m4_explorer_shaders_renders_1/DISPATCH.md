# Task Dispatch — M4 Explorer 2 (Cycles Shaders & Multi-Angle Beauty Renders Strategy)

## Objective
Formulate the exact technical implementation strategy for Feature 16 (Cycles Principled BSDF v2 Random Walk SSS) and Feature 17 (Cycles AgX Studio Lighting & Beauty Renders):
1. Materials & Shaders (`src/morphomesh/human_materials.py`, `scripts/build_ultimate_yu_nian_an.py`):
   - Porcelain skin shader: Cycles Principled BSDF v2 Random Walk (Skin) Subsurface Scattering with warm epidermal radius $(1.0, 0.45, 0.25)$ and scale $0.002$.
   - Dual-chamber refractive eyes: Cornea IOR 1.376 with shadow bypass, Iris IOR 1.336 with centered radial stroma and pupil dilation.
   - Silk sheen fabric: Sundress WhiteSilk with sheen weight 0.60, roughness 0.25; Sash IceBlue with metallic gloss and high specular sheen.
   - Emission: Crimson marionette thread emission 6.5; Butterfly wings emission 3.2 with subsurface transmission.
2. Studio Lighting & Camera Rig (`src/morphomesh/camera_rig.py`, `scripts/build_ultimate_yu_nian_an.py`):
   - 3-point softbox studio lighting: Key light (5500K warm softbox at 45° front-right), Fill light (6500K cool softbox at 45° front-left), Rim/Hair light (4500K back-top overhead for angel-ring highlight).
   - Color Management: AgX view transform with High Contrast or Punchy look.
   - 5 Canonical Beauty Render Camera Viewpoints:
     1. Front View (`output/yu_nian_an/renders/beauty_front.png`)
     2. Three-Quarter Perspective View (`output/yu_nian_an/renders/beauty_three_quarter.png`)
     3. Side Profile View (`output/yu_nian_an/renders/beauty_side.png`)
     4. Back View (`output/yu_nian_an/renders/beauty_back.png`)
     5. Head/Portrait Close-Up View (`output/yu_nian_an/renders/beauty_close_up.png`)
3. Formulation of execution script or integration in `scripts/build_ultimate_yu_nian_an.py`.

## Reference Materials
- `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md` (Mandatory reading)
- `E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md`
- Concept Sheet: `media_1788716034772.jpg`

## Output
Write report to `E:\tool\mcp\MorphoMesh\.agents\m4_explorer_shaders_renders_1\handoff.md`
Notify orchestrator via `send_message` when done.

## 2026-09-08T03:09:10Z
You are M4 Explorer 2 (Cycles Shaders & Multi-Angle Beauty Renders Strategy).
Your identity: M4 Explorer 2 (Cycles Shaders & Multi-Angle Beauty Renders Strategy).
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\m4_explorer_shaders_renders_1
You MUST create your own BRIEFING.md and progress.md in your working directory.
MANDATORY FIRST STEP: Read the authoritative user request at:
E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
Also read your dispatch instructions at:
E:\tool\mcp\MorphoMesh\.agents\m4_explorer_shaders_renders_1\DISPATCH.md
and the master project specification at:
E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md

