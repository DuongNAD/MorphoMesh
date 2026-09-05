## 2026-09-05T12:58:27Z

You are the 5 SOTA Models Spec Miner for MorphoMesh Phase 2: Open-Source Integration Hub.
Your working directory is: /Users/duongnad/Documents/tool/MorphoMesh/.agents/spec_miner_models_1
Project root: /Users/duongnad/Documents/tool/MorphoMesh

MANDATORY FIRST STEP: Read /Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md.

Task:
Provide exhaustive, deep technical analysis and specification mining for the 5 target open-source repositories to form the foundation of R1 (`docs/OPEN_SOURCE_INTEGRATION_PLAYBOOK.md`):

1. **Microsoft TRELLIS / TRELLIS.2** (MIT):
   - Architecture: O-Voxel representation, DiT (Diffusion Transformer) backbone, flow matching, sparse voxels.
   - PBR extraction pipeline: mesh extraction (Marching Cubes / Dual Contouring on signed distance / density fields), UV unwrapping (xatlas / blender smart UV), texture baking (Albedo, Normal, Roughness, Metallic).
   - Inference optimization (FlashAttention-2, torch.compile, FP16/BF16), serving via Gradio / ComfyUI headless node / custom FastAPI.

2. **3DAnimals / MagicPony / SMAL** (Research):
   - Parametric animal model SMAL (Skinned Multi-Animal Linear model): shape parameters beta in R^40, pose parameters theta in R^{35x3}, joint regression matrix.
   - Quadruped joint hierarchy and landmarks (35-37 joints: hips, spine, neck, head, jaw, shoulders, elbows, wrists, paws/hooves, tail).
   - Transformation matrix math: Coordinate system alignment (e.g., PyTorch3D / OpenCV Y-up/Z-forward vs Blender Z-up/-Y-forward), bone vector calculations, mapping to Blender Rigify standard quadruped armature (`metarig.animals.quadruped`).
   - Skinning weights transfer: nearest vertex / heat diffusion / linear blend skinning (LBS).

3. **anyCreature** (Engine Procedural):
   - Prompt-to-JSON specification format: body graph syntax, segment definitions (head, neck, spine_segments, limbs, wings, tails), attachment points, proportions, procedural joint constraints (hinge, ball-and-socket, limits).
   - Procedural mesh generation algorithms (metaballs, lofting, subdivision) and real-time animation clip binding (procedural gait generation, inverse kinematics).

4. **MeshAnything V2** (Apache-2.0):
   - Autoregressive sequence model over 3D coordinates and polygon tokens (vertex tokens, face tokens).
   - Sequence length vs face count budget: generating clean artist-like quad meshes under 1600 faces for game engines.
   - Input/Output data representations (dense triangle mesh -> normalized point/voxel prompt -> autoregressive quad sequence -> OBJ/GLB quad mesh).

5. **Tencent Hunyuan3D-2.1** (Community License):
   - High-fidelity mesh generation, 2-stage pipeline (shape generation + texture synthesis), PBR material synthesis.
   - Model weights and VRAM optimization (FP16, NF4 quantization).
   - Containerization strategy: isolated Docker container, REST API endpoint.

6. **Cross-Cutting Standards**:
   - Checkpoints & Weights management: HF Hub caching (HF_HUB_ENABLE_HF_TRANSFER=1, cache layout, symlinks), git LFS, local cache directory structure, quantization tradeoffs (FP16, BF16, INT8, NF4/bitsandbytes, AWQ), VRAM requirements table across all 5 models.
   - Serving & Containerization: Docker Compose templates, microservice architectures, API client patterns ensuring complete separation from macOS client.
   - Licensing Governance: Deep legal analysis of MIT (TRELLIS.2), Apache-2.0 (MeshAnything V2), Academic/Research (SMAL/MagicPony), and Community Licenses (Tencent Hunyuan3D Community License, Stability AI Community License). Process & Network Boundary Isolation pattern (subprocesses, HTTP/gRPC API barriers, clean-room interface contracts) to guarantee MorphoMesh remains strictly compliant and permissively open.

Constraints:
- You are a read-only spec miner. Write only to your directory: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/spec_miner_models_1/`.
- Deliverables:
  * Comprehensive technical report at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/spec_miner_models_1/report.md`
  * Standard `handoff.md` with Observation, Logic Chain, Caveats, Conclusion, Verification Method.
- Send message back to parent when done.
