import difflib
import sys
from pathlib import Path

orig_path = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\anime_pipeline\animation\action_library.py")
work_dir = Path(r"E:\tool\mcp\MorphoMesh\.agents\m3_explorer_remediation_1")

orig_text = orig_path.read_text(encoding="utf-8")
lines = orig_text.splitlines(keepends=True)

new_lines = []
for line in lines:
    # 1. Idle cute
    if "pb['ForeArm.L'].rotation_euler = Euler((math.radians(-38.0), 0.0, 0.0), 'XYZ')" in line:
        line = line.replace("-38.0", "38.0")
    elif "pb['ForeArm.R'].rotation_euler = Euler((math.radians(-65.0), 0.0, 0.0), 'XYZ')" in line:
        line = line.replace("-65.0", "65.0")
    # 2. Wave greeting
    elif "pb['ForeArm.R'].rotation_euler = Euler((math.radians(-95.0), 0.0, 0.0), 'XYZ')" in line:
        line = line.replace("-95.0", "95.0")
    elif "pb['ForeArm.R'].rotation_euler = Euler((math.radians(-95.0), forearm_twist, 0.0), 'XYZ')" in line:
        line = line.replace("-95.0", "95.0")
    elif "fore_flex = (1.0 - fac) * math.radians(-95.0)" in line:
        line = line.replace("-95.0", "95.0")
    # 3. Walk cycle
    elif "forearm_bent = math.radians(-40.0) # tucked forearm bend (35-45°)" in line:
        line = line.replace("-40.0", "40.0")
    # 4. Jump cheer timeline
    elif "(1,   0.0,    0.0,   0.0,   0.0,    15.0,  -20.0)" in line:
        line = line.replace("-20.0", "20.0")
    elif "(8,  -0.08,   10.0,  35.0,  20.0,   12.0,  -25.0)" in line:
        line = line.replace("-25.0", "25.0")
    elif "(16, -0.14,   18.0,  65.0,  35.0,   10.0,  -35.0)" in line:
        line = line.replace("-35.0", "35.0")
    elif "(22,  0.05,    5.0,  15.0, -45.0,   25.0,  -20.0)" in line:
        line = line.replace("-20.0", "20.0")
    elif "(28,  0.30,  -10.0,  60.0, -120.0,  35.0,  -30.0)" in line:
        line = line.replace("-30.0", "30.0")
    elif "(35,  0.35,  -12.0,  85.0, -145.0,  40.0,  -35.0)" in line:
        line = line.replace("-35.0", "35.0")
    elif "(42,  0.25,   -5.0,  70.0, -130.0,  35.0,  -30.0)" in line:
        line = line.replace("-30.0", "30.0")
    elif "(44,  0.02,    0.0,  20.0,  -80.0,  25.0,  -30.0)" in line:
        line = line.replace("-30.0", "30.0")
    elif "(50, -0.10,   10.0,  55.0,  -30.0,  20.0,  -40.0)" in line:
        line = line.replace("-40.0", "40.0")
    elif "(62, -0.02,    3.0,  10.0,  -10.0,  18.0,  -25.0)" in line:
        line = line.replace("-25.0", "25.0")
    elif "(75,  0.0,     0.0,   0.0,    0.0,  15.0,  -20.0)" in line:
        line = line.replace("-20.0", "20.0")
    # 5. Canonical curves
    elif '"ForeArm.R.rot_x": [(1, 0.0), (45, -95.0), (95, -95.0), (120, 0.0)],' in line:
        line = line.replace("-95.0", "95.0")
    elif '"ForeArm.R.rot_x": [(1, -40.0), (16, -40.0), (32, -40.0)],' in line:
        line = line.replace("-40.0", "40.0")
    elif '"ForeArm.L.rot_x": [(1, -40.0), (16, -40.0), (32, -40.0)],' in line:
        line = line.replace("-40.0", "40.0")
    
    # Adding canonical curves for idle and jump cheer
    if '"Head.rot_z": [(1, 4.0), (34, 5.2), (56, 4.0), (78, 2.8), (90, 4.0)],' in line:
        new_lines.append(line)
        new_lines.append('            "ForeArm.L.rot_x": [(1, 38.0), (45, 38.0), (90, 38.0)],\n')
        new_lines.append('            "ForeArm.R.rot_x": [(1, 65.0), (45, 65.0), (90, 65.0)],\n')
        continue

    if '"Head.rot_x": [(1, 0.0), (35, -15.0), (75, 0.0)],' in line:
        new_lines.append(line)
        new_lines.append('            "ForeArm.R.rot_x": [(1, 20.0), (16, 35.0), (35, 35.0), (50, 40.0), (75, 20.0)],\n')
        new_lines.append('            "ForeArm.L.rot_x": [(1, 20.0), (16, 35.0), (35, 35.0), (50, 40.0), (75, 20.0)],\n')
        continue

    new_lines.append(line)

patched_text = "".join(new_lines)
patched_path = work_dir / "action_library_patched.py"
patched_path.write_text(patched_text, encoding="utf-8")

patch = list(difflib.unified_diff(
    lines,
    new_lines,
    fromfile="a/anime_pipeline/animation/action_library.py",
    tofile="b/anime_pipeline/animation/action_library.py",
))
patch_text = "".join(patch)
patch_path = work_dir / "remediation_forearm.patch"
patch_path.write_text(patch_text, encoding="utf-8")
print(f"Generated patch at {patch_path} ({len(patch)} diff lines)")
