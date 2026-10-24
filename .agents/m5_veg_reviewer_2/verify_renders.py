"""
Independent Render & Visual Showcase Verification
Executed by Reviewer 2.
"""
from pathlib import Path
import sys
from PIL import Image

OUTPUT_DIR = Path("E:/tool/mcp/MorphoMesh/teamwork_projects/vegetation_library/output")

def verify_renders():
    tt_files = list(OUTPUT_DIR.rglob("turntable_*.png"))
    thumb_files = list(OUTPUT_DIR.rglob("thumbnail.png"))
    
    print(f"Total turntable images found: {len(tt_files)}")
    print(f"Total thumbnail images found: {len(thumb_files)}")
    
    assert len(tt_files) == 140, f"Expected 140 turntable images, got {len(tt_files)}"
    assert len(thumb_files) == 35, f"Expected 35 thumbnail images, got {len(thumb_files)}"
    
    # Check turntable dimensions
    bad_tt = []
    for tt in tt_files:
        try:
            with Image.open(tt) as img:
                if img.size != (512, 512):
                    bad_tt.append((tt.name, img.size))
        except Exception as e:
            bad_tt.append((tt.name, str(e)))
            
    # Check thumbnail dimensions
    bad_thumb = []
    for th in thumb_files:
        try:
            with Image.open(th) as img:
                if img.size != (1024, 1024):
                    bad_thumb.append((th.parent.name, img.size))
        except Exception as e:
            bad_thumb.append((th.parent.name, str(e)))
            
    print(f"Bad turntable count: {len(bad_tt)}")
    print(f"Bad thumbnail count: {len(bad_thumb)}")
    
    if bad_tt:
        print("Bad turntables:", bad_tt[:5])
    if bad_thumb:
        print("Bad thumbnails:", bad_thumb[:5])
        
    return len(bad_tt) == 0 and len(bad_thumb) == 0

if __name__ == "__main__":
    ok = verify_renders()
    sys.exit(0 if ok else 1)
