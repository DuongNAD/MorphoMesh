# Handoff Report — Survey Explorer 1 (MorphoMesh R1)

**Date**: 2026-09-05T11:30:00Z  
**Agent**: Survey Explorer 1 (`explorer_survey_1`)  
**Target Milestone**: R1 (Comprehensive Research & Benchmark Docs)  
**Primary Output**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_1/survey_models_report.md`  

---

## 1. Observation

1. **User Request & Acceptance Criteria**:
   - `ORIGINAL_REQUEST.md:12-20`: Specifies requirement R1:
     > "Nghiên cứu, đánh giá và lập ma trận so sánh chi tiết ít nhất 20 mô hình và framework mã nguồn mở SOTA chia làm 3 nhóm chính: 1. Chuyên biệt Động vật & Khớp nối (Articulated Animals) ... 2. Tạo 3D tổng quát chất lượng cao cho Creature ... 3. Tái cấu trúc lưới & Rigging tự động ..."
     > "Phân tích chi tiết theo các tiêu chí: License, Yêu cầu phần cứng & VRAM, Độ trung thực hình học, Định dạng xuất, Trạng thái xương/rigging, và Khả năng triển khai (Local vs Cloud API)."
     > "Đưa ra khuyến nghị lộ trình kết hợp tối ưu cho 3 use-case: (A) Fantasy Creature đa dạng, (B) Động vật thực tế có animation/rig, (C) Game-ready low-poly asset."
2. **Category 1 (Articulated Animals) Coverage**:
   - Analyzed 13 distinct research projects and tools: 3DAnimals suite (MagicPony, 3D Fauna, Ponymation), 4D-Animal/Animal4D, Animal Avatar, YouDream, GART, LASSIE / Hi-LASSIE, SAOR, BARC, BITE, anyCreature, Meow-Generator, AnimalClub, and Muses (CVPR 2026).
   - Observed that SMAL, D-SMAL, and SBSM (Semantic Bank of Skinned Models in 3D Fauna) provide canonical quadruped skeletons (24–35 joints) with LBS weights, but are strictly limited to quadruped mammal topologies. Muses provides the only known skeleton-driven generative pipeline tailored for nonexistent fantasy creatures.
3. **Category 2 (General High-Quality 3D) Coverage**:
   - Analyzed 12 major models: TRELLIS / TRELLIS.2 (4B O-Voxel), Hunyuan3D-2 / 2.1, Step1X-3D (4.8B), Hi3DGen / Stable3DGen, SPAR3D, Stable Fast 3D (SF3D), TripoSR, InstantMesh, Unique3D, OpenLRM, LGM, CRM.
   - Observed that TRELLIS.2 (4B) and Hunyuan3D-2.1 are the only models producing complete production-grade PBR material maps (Albedo, Normal, Roughness, Metallic) with watertight high-genus mesh geometry.
   - Observed that TripoSR and SF3D are the only models capable of sub-second inference and runnable on lightweight hardware (TripoSR runnable on Apple Silicon MPS/CPU).
4. **Category 3 (Retopology & Rigging) Coverage**:
   - Analyzed MeshAnything / MeshAnything V2, Mesh2Motion, SMAL / SMALify, and Blender Rigify procedural creatures.
   - Observed that MeshAnything V2 (Adjacent Mesh Tokenization) allows specifying target face counts (e.g., 800–3,000 faces) producing clean quad-dominant artist topology.
   - Observed that Blender Rigify is native to Blender 4.x/5.x, requires 0 GPU VRAM, runs via `bpy` on Apple Silicon, and contains built-in metarigs for `quadruped`/`wolf`, `cat`, `horse`, `bird`, and `shark`.
5. **Hardware Constraints**:
   - macOS Apple Silicon (MPS) lacks native CUDA libraries (`spconv`, `nvdiffrast`, `flash-attn`). Running 4B models on Mac CPU causes 100x slowdown (15–45 min per asset), while remote GPU (RTX 4090 / A10G) generates in 10–25 seconds.

---

## 2. Logic Chain

1. **From Observation 1 & 2 to Animal Articulation Selection**:
   - Because real-world animals have strict biomechanical constraints, generative meshes from unconditioned models frequently produce collapsing joints or asymmetric limbs during animation.
   - Parametric animal models (SMAL, D-SMAL in BARC and BITE, SBSM in 3D Fauna) provide mathematically verified 35-joint skeletons and canonical quad topologies. Therefore, for real-world animals (Use-Case B), combining a single-image parametric prior (or Hunyuan3D-2.1 aligned to SMAL) with Blender Rigify yields the highest physical plausibility.
2. **From Observation 1 & 3 to Fantasy Creature Selection**:
   - Fantasy creatures (dragons, chimeras, multi-limbed monsters) violate canonical quadruped topologies. Models locked into SMPL/SMAL fail completely.
   - TRELLIS.2 (4B O-Voxel) and Hunyuan3D-2.1 are the only surveyed models capable of reconstructing thin membranes (wings), complex horns, and separate limb branches with complete PBR textures.
   - Therefore, Use-Case A requires TRELLIS.2/Hunyuan3D-2.1 as the 3D backbone, followed by MeshAnything V2 for quad retopology and procedural modular Rigify metarig assembly in Blender.
3. **From Observation 1 & 4 to Game-Ready Low-Poly Selection**:
   - Game engines strictly reject raw marching-cubes triangular soup (50k–200k faces).
   - MeshAnything V2 is uniquely capable of generating Artist-Created Meshes (AM) under an exact face budget (<2,000 quads), and Blender's normal baker can transfer high-frequency details from the original mesh to the low-poly UV map.
   - Therefore, Use-Case C is optimally solved by SF3D/TripoSR $\to$ MeshAnything V2 $\to$ Normal Baking $\to$ Rigify $\to$ GLB export.
4. **From Observation 5 to Hybrid Architecture**:
   - Since Apple Silicon cannot run `spconv`/`nvdiffrast` CUDA kernels without unacceptable latency, but Blender runs with native Metal acceleration on macOS, the system must split responsibilities: Remote GPU Cloud API for heavy 3D inference and Local macOS for Blender Python execution, topology processing, and Rigify armature binding.

---

## 3. Caveats

- **API Commercial Costs**: Hosting TRELLIS.2 or Hunyuan3D-2.1 on Replicate or dedicated GPU instances incurs per-inference or hourly hosting costs (~$0.01–$0.05 per generation or ~$0.60–$1.20/hr on RunPod/A10G).
- **Muses Availability**: Muses is a CVPR 2026 paper; while its skeleton-driven latent assembly method is documented, its official weights may require community replication or waiting for full public release.
- **Extreme Fantasy Morphologies**: For non-standard creatures with >6 limbs or unusual appendages (e.g., centaurs, octopoids), automated Rigify assembly requires procedural python rule stitching in `blender_bridge.py`.

---

## 4. Conclusion

- A total of **29 unique models/frameworks (33 variants)** were deeply investigated across all 6 required criteria, satisfying and exceeding the R1 requirement of at least 20 models.
- The complete authoritative survey has been compiled and saved to `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_1/survey_models_report.md`.
- Recommended core production stack for MorphoMesh:
  - **Inference Engine**: TRELLIS.2 (4B) & Hunyuan3D-2.1 (Remote Cloud GPU), with TripoSR (Local Apple Silicon fallback).
  - **Retopology Engine**: MeshAnything V2 (Remote Cloud) and Blender QuadriFlow/Decimate (Local `bpy`).
  - **Rigging Engine**: Blender Rigify with automated animal metarig alignment (`wolf`, `cat`, `horse`, `bird`, `shark`, and modular chimeras).
  - **Bridge Architecture**: Hybrid local client (Antigravity + MCP + Blender) communicating with Remote GPU endpoints.

---

## 5. Verification Method

1. **File Integrity Verification**:
   - Inspect `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_1/survey_models_report.md`.
   - Verify table completeness: 33 evaluated model rows across 10 columns covering Category 1 (15 rows), Category 2 (14 rows), Category 3 (4 rows).
   - Check presence of 3 explicit Use-Case sections: Section 6.1 (Fantasy), Section 6.2 (Realistic), Section 6.3 (Game-ready Low-poly).
2. **Invalidation Conditions**:
   - Invalidation occurs if any evaluated model lacks license classification, VRAM specification, or rigging status.
   - Invalidation occurs if local Apple Silicon deployment claims full CUDA-speed execution for TRELLIS or Hunyuan3D without remote GPU offloading.
