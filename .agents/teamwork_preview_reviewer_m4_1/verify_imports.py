import itertools
import subprocess
import sys

modules = [
    'morphomesh.assembler.scene_builder',
    'morphomesh.assembler.pbr_baker',
    'morphomesh.assembler.packager',
    'morphomesh.assembler.assembler',
    'morphomesh.assembler',
    'morphomesh.character_assembler',
]

print("Testing individual clean imports...")
for mod in modules:
    res = subprocess.run([sys.executable, "-c", f"import {mod}; print('OK:', '{mod}')"], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FAILED importing {mod}: {res.stderr}")
        sys.exit(1)
    else:
        print(f"Clean import {mod}: SUCCESS")

print("\nTesting all permutation pairs...")
pairs = list(itertools.permutations(modules, 2))
failures = 0
for m1, m2 in pairs:
    code = f"import {m1}; import {m2}"
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FAILED pair {m1} -> {m2}: {res.stderr}")
        failures += 1

if failures == 0:
    print(f"\nALL {len(pairs)} pairwise permutations imported with ZERO circular imports!")
else:
    print(f"\nEncountered {failures} import failures!")
    sys.exit(1)
