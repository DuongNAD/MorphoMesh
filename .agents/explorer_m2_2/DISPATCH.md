## 2026-09-07T14:21:35Z
You are an Explorer subagent (Explorer M2.2: Bodice & Cleavage Sculpting Investigator) for MorphoMesh Milestone M2.
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\explorer_m2_2

MANDATORY FIRST STEP:
You MUST read the following authoritative specification files:
1. ORIGINAL_REQUEST.md at: E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
2. PROJECT.md at: E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_anatomy_gen2\PROJECT.md

YOUR OBJECTIVE:
Investigate `src/morphomesh/wardrobe.py` upper bodice sculpting and compare against `src/morphomesh/human_generator.py` body geometry to design a bodice conforming to the teardrop breast profile, natural cleavage indent, sweetheart scoop neckline, and 3D spaghetti straps.

SPECIFIC INVESTIGATION TASKS:
1. Inspect the existing bodice generation in `src/morphomesh/wardrobe.py` and the female torso/bust geometry in `src/morphomesh/human_generator.py` (including clavicle slope, teardrop bust profile, chest apex, cleavage hollow).
2. Design the upper bodice geometric contour:
   - Bilateral teardrop breast cups matching the body's teardrop profile with gentle slope from clavicle and distinct fullness at lower/lateral quadrant.
   - Natural cleavage indentation between breasts without clipping or gap.
   - Sweetheart scoop neckline contour across Z=1.185m to Z=1.255m.
   - Delicate 3D conforming spaghetti straps arching over the shoulders and connecting to the back bodice.
3. Calculate precise clearance offsets (+1.5mm to +2.0mm outward from body skin) to guarantee 100% zero penetration/clipping with the underlying anatomical body mesh across all bust parameters.
4. Formulate an exact mathematical and vertex generation plan for the Worker to implement in `src/morphomesh/wardrobe.py`.
