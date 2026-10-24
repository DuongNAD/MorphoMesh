# Orchestration Plan: MorphoMesh Human Anatomy & Yu Nian An Character Realism Upgrade

## Project Objective
Deliver a medical-grade anatomical reconstruction and high-fidelity photorealistic upgrade of the Yu Nian An 3D digital human character in MorphoMesh and Blender, including medical-grade skeletal rig (Rigify 163 DEF) with biological pivots, organic cloth drape & tension folds for the dress with ice-blue sash, anatomically sculpted 5-toed feet with flat strappy sandals, signature red threads and glowing butterflies, PBR Cycles shaders (Random Walk SSS, silk/satin sheen), 3-point studio lighting, master production export (.blend, .glb, .fbx, renders), and 100% passing pytest suite.

---

## Phase 0: Survey & Scope Mapping (Current Phase)
- Dispatch 3 parallel Explorers:
  * **Explorer 1 (Anatomy & Rigging DEF)**: Investigate `human_generator.py`, `human_rigging.py`, `media_1788785935854.png`, clavicle/ribcage/pelvis/patella/ankle/5-toed foot geometry and Rigify 163 DEF weight preservation.
  * **Explorer 2 (Cloth Drapery & Wardrobe)**: Investigate `wardrobe.py`, `media_1788785935849.jpg`, `media_1788785935824.jpg`, organic cloth folds, teardrop breast profile, sweetheart scoop neckline, spaghetti straps, ice-blue sash & bow ribbons with zero Z-fighting.
  * **Explorer 3 (Footwear, Shaders, Lighting & Verification)**: Investigate flat strappy sandals, 10 red threads & glowing white butterflies, hime cut hair curves, PBR SSS skin & sheen shaders in `human_materials.py`, studio lighting, master export (`Yu_Nian_An_Master.blend`, `.glb`, `.fbx`), and existing test infrastructure.
- Synthesize findings into `PROJECT.md` Feature Inventory, Milestones, and Interface Contracts.

---

## Phase 1: Milestone M1 — Medical-Grade Human Anatomy & 163 DEF Rigging (R1)
- Specialized Role: Chuyên gia Giải phẫu & Khung xương chuẩn y khoa (Rigging DEF)
- Iteration Loop: 3 Explorers -> 1 Worker -> 2 Reviewers -> 2 Challengers -> 1 Forensic Auditor -> Gate.
- Deliverables: Anatomical torso/limbs, 5-toed feet with toenails and ankle malleoli, biological joint pivots, Rigify 163 DEF skinning with zero volume loss.

---

## Phase 2: Milestone M2 — Realistic Organic Dress Drapery & Ice-Blue Sash (R2)
- Specialized Role: Chuyên gia Điêu khắc & Nếp gấp vải hữu cơ (Cloth Drapery)
- Iteration Loop: 3 Explorers -> 1 Worker -> 2 Reviewers -> 2 Challengers -> 1 Forensic Auditor -> Gate.
- Deliverables: Organic gravity cloth folds, teardrop bust profile, sweetheart neckline, spaghetti straps, seamless ice-blue sash with natural bow tie and ribbons.

---

## Phase 3: Milestone M3 — Flat Strappy Sandals & Signature Props (R3)
- Specialized Role: Chuyên gia Chi tiết Cơ thể & Phụ kiện Đặc trưng
- Iteration Loop: 3 Explorers -> 1 Worker -> 2 Reviewers -> 2 Challengers -> 1 Forensic Auditor -> Gate.
- Deliverables: Flat strappy sandals exposing 5 toes, 10 red threads connected to fingertips, glowing white butterflies, flowing black hair with straight bangs.

---

## Phase 4: Milestone M4 — PBR Cycles Shaders, Studio Lighting, Master Export & E2E Tests (R4)
- Specialized Role: Chuyên gia Vật liệu PBR, Ánh sáng & Đóng gói Xuất xưởng
- Iteration Loop: 3 Explorers -> 1 Worker -> 2 Reviewers -> 2 Challengers -> 1 Forensic Auditor -> Gate.
- Deliverables: Random Walk SSS skin, sheen fabric materials, 3-point studio lighting rig, `Yu_Nian_An_Master.blend`, `.glb`, `.fbx`, beauty renders, 100% pytest pass rate.

---

## Phase 5: Adversarial Hardening & Final Victory Handoff
- White-box coverage audit, edge case verification, final report to Sentinel.
