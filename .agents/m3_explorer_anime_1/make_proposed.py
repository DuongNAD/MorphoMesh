import os

src_path = r"E:\tool\mcp\MorphoMesh\.agents\m3_explorer_anime_1\test_all_4_actions.py"
dst_path = r"E:\tool\mcp\MorphoMesh\.agents\m3_explorer_anime_1\proposed_action_library.py"

header = '''"""
anime_pipeline/animation/action_library.py
Milestone 3 Feature F11: Programmatic Anime Action Library & Keyframes.

Authoritative Specification:
- F11: Four distinct programmatic anime actions matching aesthetic conventions:
    1. action_anime_idle_cute: 90 frames / 3.0s seamless loop @ 30 FPS
       - Contrapposto weight shift on right leg (hips shifted +0.035m, roll Z = -4.5 deg, yaw Y = +2.0 deg).
       - Breathing sway on spine (+/-1.5 deg) with double micro-bob on hips (+/-0.006m).
       - Cute head tilt (~4 deg) delayed from torso by ~11 frames (pi/4 phase lag).
       - Left hand resting on skirt/thigh, right hand bent gracefully near collarbone.
    2. action_anime_wave_greeting: 120 frames / 4.0s @ 30 FPS
       - Weight shift & recognition (frames 1-25).
       - Arm raise with forearm bent at 95 deg beside cheek (frames 26-45).
       - 3 energetic wave cycles (16 frames each, +/-18 deg forearm twist, +/-15 deg wrist yaw) with synchronous cheerful head bob (frames 46-95).
       - Settle & smooth ease-out return to idle (frames 96-120).
    3. action_anime_walk_cycle: 32 frames / 1.07s seamless loop @ 30 FPS
       - Tight narrow center-line footsteps (<= 0.08m lateral separation, pigeon-toed toe contact +1.5 deg).
       - Vertical bounce: down phase at frames 4 & 20 (hips sink -0.032m), passing phase at frames 8 & 24 (hips rise +0.025m).
       - Pelvic roll (+/-4 deg) & yaw (+/-6 deg) with counter-rotating thoracic shoulder balance (-3 deg to -4 deg roll, -4 deg to -5 deg yaw).
       - Natural tucked arm swing (forearms kept bent at 35-45 deg, never straight soldier swing).
    4. action_anime_jump_cheer: 75 frames / 2.5s @ 30 FPS
       - Anticipation squash (hips -0.14m, knees 65 deg, arms back +35 deg, spine +18 deg, frames 1-18).
       - Explosive upward leap (hips +0.35m, toes pointed down, arms overhead +145 deg, frames 19-28).
       - Joyful apex "anime hop" (knees bent backward cutely 85 deg, chest arched -12 deg, frames 29-42).
       - Landing compression (balls of feet touch first at frame 44, hips cushion -0.10m, knees 55 deg, frames 43-58).
       - Settle to upright standing pose (frames 59-75).
- All keyframe interpolation curves set to BEZIER for organic ease-in / ease-out.
- NLA (Non-Linear Animation) track registration preserving all 4 actions for Blender scenes and glTF / VRM export.
- Pure-Python compatible fallback dataclasses for headless non-Blender testing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import bpy
    import mathutils
    from mathutils import Euler, Matrix, Vector
    HAS_BPY = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    mathutils = None  # type: ignore[assignment]
    HAS_BPY = False
    Euler = Any  # type: ignore[misc,assignment]
    Matrix = Any  # type: ignore[misc,assignment]
    Vector = Any  # type: ignore[misc,assignment]


ACTION_NAMES: List[str] = [
    "action_anime_idle_cute",
    "action_anime_wave_greeting",
    "action_anime_walk_cycle",
    "action_anime_jump_cheer",
]

@dataclass
class ActionMetadata:
    """Metadata specification for an anime action."""
    name: str
    frame_start: int
    frame_end: int
    fps: int = 30
    is_looping: bool = False
    description: str = ""

    @property
    def duration_seconds(self) -> float:
        return (self.frame_end - self.frame_start + 1) / self.fps

    @property
    def total_frames(self) -> int:
        return self.frame_end - self.frame_start + 1


ACTION_METADATA_REGISTRY: Dict[str, ActionMetadata] = {
    "action_anime_idle_cute": ActionMetadata(
        name="action_anime_idle_cute",
        frame_start=1,
        frame_end=90,
        fps=30,
        is_looping=True,
        description="Contrapposto weight shift on right leg (+0.035m, roll -4.5 deg, yaw +2.0 deg), breathing spine sway +/-1.5 deg, double micro-bob +/-0.006m, cute delayed head tilt."
    ),
    "action_anime_wave_greeting": ActionMetadata(
        name="action_anime_wave_greeting",
        frame_start=1,
        frame_end=120,
        fps=30,
        is_looping=False,
        description="Weight shift, arm raise to cheek height at 95 deg flexion, 3 wave cycles (+/-18 deg forearm twist, +/-15 deg wrist yaw), head bob, settle."
    ),
    "action_anime_walk_cycle": ActionMetadata(
        name="action_anime_walk_cycle",
        frame_start=1,
        frame_end=32,
        fps=30,
        is_looping=True,
        description="Narrow center-line steps (<=0.08m separation), vertical bounce (-0.032m to +0.025m), pelvic roll +/-4 deg / yaw +/-6 deg, tucked arm swing."
    ),
    "action_anime_jump_cheer": ActionMetadata(
        name="action_anime_jump_cheer",
        frame_start=1,
        frame_end=75,
        fps=30,
        is_looping=False,
        description="Anticipation squash (hips -0.14m, knees 65 deg), explosive launch (+0.35m), apex anime hop (knees 85 deg, chest -12 deg), landing cushion (-0.10m), settle."
    ),
}

@dataclass
class ActionDefinition:
    """Pure-Python Action representation compatible with test fixtures."""
    name: str
    frame_start: int
    frame_end: int
    fps: int = 30
    curves: Dict[str, List[Tuple[int, float]]] = field(default_factory=dict)

    @property
    def total_frames(self) -> int:
        return self.frame_end - self.frame_start + 1

    @property
    def duration_seconds(self) -> float:
        return self.total_frames / self.fps
'''

with open(src_path, 'r', encoding='utf-8') as f:
    src_content = f.read()

start_idx = src_content.find('def ensure_animation_data')
end_idx = src_content.find('# Execute verification')
func_code = src_content[start_idx:end_idx]

canonical_fixtures_code = '''
def get_canonical_action_definitions() -> Dict[str, ActionDefinition]:
    """
    Returns pure-Python ActionDefinition objects matching test suite fixtures.
    Allows pytest and offline pipeline verification without running Blender.
    """
    actions: Dict[str, ActionDefinition] = {}

    actions["action_anime_idle_cute"] = ActionDefinition(
        name="action_anime_idle_cute",
        frame_start=1,
        frame_end=90,
        fps=30,
        curves={
            "Hips.loc_x": [(1, 0.035), (45, 0.035), (90, 0.035)],
            "Hips.loc_z": [(1, 0.0), (23, 0.006), (45, 0.0), (68, -0.006), (90, 0.0)],
            "Spine1.rot_x": [(1, 0.0), (23, 1.5), (45, 0.0), (68, -1.5), (90, 0.0)],
            "Head.rot_z": [(1, 4.0), (34, 5.2), (56, 4.0), (78, 2.8), (90, 4.0)],
        }
    )

    actions["action_anime_wave_greeting"] = ActionDefinition(
        name="action_anime_wave_greeting",
        frame_start=1,
        frame_end=120,
        fps=30,
        curves={
            "Hips.loc_x": [(1, 0.0), (25, -0.025), (95, -0.025), (120, 0.0)],
            "UpperArm.R.rot_x": [(1, 0.0), (45, -75.0), (95, -75.0), (120, 0.0)],
            "ForeArm.R.rot_x": [(1, 0.0), (45, -95.0), (95, -95.0), (120, 0.0)],
            "ForeArm.R.rot_y": [(46, 0.0), (50, 18.0), (58, -18.0), (66, 18.0), (74, -18.0), (82, 18.0), (90, -18.0), (95, 0.0)],
            "Hand.R.rot_z": [(46, 0.0), (48, 15.0), (56, -15.0), (64, 15.0), (72, -15.0), (80, 15.0), (88, -15.0), (95, 0.0)],
        }
    )

    actions["action_anime_walk_cycle"] = ActionDefinition(
        name="action_anime_walk_cycle",
        frame_start=1,
        frame_end=32,
        fps=30,
        curves={
            "Hips.loc_z": [(1, 0.0), (4, -0.032), (8, 0.025), (12, 0.008), (17, 0.0), (20, -0.032), (24, 0.025), (28, 0.008), (32, 0.0)],
            "Thigh.R.rot_x": [(1, -28.0), (8, 5.0), (17, 28.0), (24, -10.0), (32, -28.0)],
            "Thigh.L.rot_x": [(1, 28.0), (8, -10.0), (17, -28.0), (24, 5.0), (32, 28.0)],
            "Hips.rot_z": [(1, -4.0), (8, 2.0), (17, 4.0), (24, -2.0), (32, -4.0)],
            "ForeArm.R.rot_x": [(1, -40.0), (16, -40.0), (32, -40.0)],
            "ForeArm.L.rot_x": [(1, -40.0), (16, -40.0), (32, -40.0)],
        }
    )

    actions["action_anime_jump_cheer"] = ActionDefinition(
        name="action_anime_jump_cheer",
        frame_start=1,
        frame_end=75,
        fps=30,
        curves={
            "Hips.loc_z": [(1, 0.0), (16, -0.14), (28, 0.30), (35, 0.35), (44, 0.02), (50, -0.10), (75, 0.0)],
            "Shin.R.rot_x": [(1, 0.0), (16, 65.0), (35, 85.0), (50, 55.0), (75, 0.0)],
            "UpperArm.R.rot_x": [(1, 0.0), (16, 35.0), (35, -145.0), (50, -30.0), (75, 0.0)],
            "Spine1.rot_x": [(1, 0.0), (16, 18.0), (35, -12.0), (50, 10.0), (75, 0.0)],
            "Head.rot_x": [(1, 0.0), (35, -15.0), (75, 0.0)],
        }
    )

    return actions
'''

final_code = header + '\n' + func_code + '\n' + canonical_fixtures_code

with open(dst_path, 'w', encoding='utf-8') as f:
    f.write(final_code)

print("Successfully generated proposed_action_library.py, size:", os.path.getsize(dst_path))