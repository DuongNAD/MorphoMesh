## 2026-09-05T13:30:43Z

You are the Connectors & Math Challenger for MorphoMesh Phase 2: Open-Source Integration Hub.
Your working directory is: /Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_connectors_1
Project root: /Users/duongnad/Documents/tool/MorphoMesh

MANDATORY FIRST STEP: Read /Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md.

Task:
Empirically stress-test the mathematical, geometric, and structural correctness of the Phase 2 connectors:
1. Coordinate Transformation Matrix Verification:
   - Test `Animals3DConnector`'s $R_x(+90^\circ)$ matrix: Verify $R \cdot R^T = I$, $\det(R) = +1.0$ (proper rotation, no reflection or parity inversion), and that PyTorch canonical points $[x, y, z]$ map exactly to Blender $[x, -z, y]$.
   - Test bone vector orientation, bone length positivity, and roll alignment logic.
   - Test that all 35 SMAL landmarks map without missing keys to Rigify Wolf deformation bones.
2. Face Budget & Topology Verification:
   - Test `MeshAnythingConnector` across multiple input geometries: verify that the generated quad-dominant meshes strictly satisfy the game-ready polygon budget $< 1600$ faces and $\ge 90\%$ quad face ratio.
3. Procedural DAG & Morphological Schema Verification:
   - Test `AnyCreatureConnector` with complex, adversarial, and edge-case creature prompts (e.g. multi-limbed, winged serpents, exotic hybrids). Verify generated JSON conforms to Pydantic schemas, builds non-empty manifold geometry, and maps valid animation clips.
4. PBR Texture Map Verification:
   - Verify `TrellisConnector` and `HunyuanConnector` produce all 4 distinct texture channels (Albedo, Tangent Normal, Roughness, Metallic) with valid PNG headers and correct pixel dimensions.
5. Write your empirical challenge harness and test scripts within your working directory: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_connectors_1/`.
6. Document findings and state an unambiguous verdict (`APPROVE` or `CHALLENGE_FAILED`) in `/Users/duongnad/Documents/tool/MorphoMesh/.agents/challenger_connectors_1/handoff.md`.
7. Send message back to parent.
