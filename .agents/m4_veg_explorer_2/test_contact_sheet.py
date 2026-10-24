import os
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image, ImageDraw, ImageFont

def create_contact_sheet(
    image_paths: List[Path],
    output_path: Path,
    title: str = "Fan Palm",
    scientific_name: str = "Livistona chinensis",
    category: str = "Tropical Foliage",
    height_m: float = 5.5,
    polycount: int = 2442,
    resolution: int = 1024,
) -> Path:
    """
    Creates a 1024x1024 2x2 contact sheet montage with metadata banner,
    clean borders, and viewpoint badges.
    """
    canvas = Image.new("RGBA", (resolution, resolution), (245, 247, 250, 255))
    draw = ImageDraw.Draw(canvas)

    # 1. Top Header Banner
    header_h = 72
    # Gradient or solid dark charcoal header
    header_color = (20, 24, 33, 255)
    draw.rectangle([(0, 0), (resolution, header_h)], fill=header_color)

    # Accent divider stripe (botanical green)
    accent_color = (46, 160, 67, 255)
    draw.rectangle([(0, header_h - 3), (resolution, header_h)], fill=accent_color)

    # Header text
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 22)
        font_sub = ImageFont.truetype("ariali.ttf", 14)
        font_meta = ImageFont.truetype("arial.ttf", 13)
        font_badge = ImageFont.truetype("arialbd.ttf", 11)
        font_footer = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = font_title
        font_meta = font_title
        font_badge = font_title
        font_footer = font_title

    # Title & scientific name
    draw.text((20, 14), title, fill=(255, 255, 255, 255), font=font_title)
    draw.text((20, 42), scientific_name, fill=(160, 175, 195, 255), font=font_sub)

    # Metadata pills on right
    meta_text = f"{category}   |   Height: {height_m:.1f}m   |   Faces: {polycount:,}"
    draw.text((resolution - 380, 28), meta_text, fill=(210, 220, 235, 255), font=font_meta)

    # 2. Bottom Footer Bar
    footer_h = 32
    footer_y = resolution - footer_h
    draw.rectangle([(0, footer_y), (resolution, resolution)], fill=(28, 32, 42, 255))
    footer_text = "MorphoMesh Vegetation Library   •   Verified Static Mesh (0 Bones)   •   Z_min = 0.000m   •   4-Channel PBR"
    draw.text((24, footer_y + 9), footer_text, fill=(140, 155, 175, 255), font=font_footer)

    # 3. 2x2 Grid Layout
    grid_top = header_h
    grid_bottom = footer_y
    grid_w = resolution
    grid_h = grid_bottom - grid_top

    # 4 cell rectangles with 8px margins/padding
    pad = 8
    cell_w = (grid_w - pad * 3) // 2
    cell_h = (grid_h - pad * 3) // 2

    view_labels = [
        "1. HERO 3/4 (25°/45°)",
        "2. FRONT ELEVATION (0°/0°)",
        "3. SIDE ELEVATION (0°/90°)",
        "4. TOP CROWN (85°/0°)",
    ]

    cell_coords = [
        (pad, grid_top + pad),                           # Top-left (Hero)
        (pad * 2 + cell_w, grid_top + pad),               # Top-right (Front)
        (pad, grid_top + pad * 2 + cell_h),               # Bottom-left (Side)
        (pad * 2 + cell_w, grid_top + pad * 2 + cell_h),   # Bottom-right (Top)
    ]

    for idx in range(4):
        cx, cy = cell_coords[idx]
        cw, ch = cell_w, cell_h

        # Cell background card with subtle border
        draw.rectangle([(cx, cy), (cx + cw, cy + ch)], fill=(255, 255, 255, 255), outline=(220, 225, 232, 255), width=1)

        # Paste render image if available
        if idx < len(image_paths) and image_paths[idx].is_file():
            img = Image.open(image_paths[idx]).convert("RGBA")
            # Fit inside cell with 4px inner padding
            inner_pad = 4
            target_w = cw - inner_pad * 2
            target_h = ch - inner_pad * 2
            img_thumb = img.copy()
            img_thumb.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)

            # Center inside cell
            offset_x = cx + (cw - img_thumb.width) // 2
            offset_y = cy + (ch - img_thumb.height) // 2
            canvas.alpha_composite(img_thumb, (offset_x, offset_y))

        # View badge overlay in top-left of each cell
        badge_text = view_labels[idx]
        badge_x = cx + 10
        badge_y = cy + 10
        # Pill badge background
        draw.rounded_rectangle([(badge_x, badge_y), (badge_x + 160, badge_y + 20)], radius=4, fill=(35, 40, 52, 220))
        draw.text((badge_x + 8, badge_y + 4), badge_text, fill=(240, 245, 255, 255), font=font_badge)

    # Save contact sheet
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG", quality=95)
    print(f"Contact sheet saved to {output_path} ({os.path.getsize(output_path)} bytes)")
    return output_path

if __name__ == "__main__":
    test_dir = Path(r"E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_2\test_turntable_cycles")
    imgs = [
        test_dir / "turntable_01.png",
        test_dir / "turntable_02.png",
        test_dir / "turntable_03.png",
        test_dir / "turntable_04.png",
    ]
    out_sheet = Path(r"E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_2\test_turntable_cycles\thumbnail.png")
    create_contact_sheet(imgs, out_sheet)
