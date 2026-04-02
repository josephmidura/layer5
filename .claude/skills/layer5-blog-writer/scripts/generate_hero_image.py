#!/usr/bin/env python3
"""
Layer5 Hero Image Generator

Creates branded 1200x630 hero images for Layer5 blog posts.
Output is an SVG file that embeds a cosmic PNG background and overlays
a real Five mascot SVG file (from the Layer5 repo), with Qanelas Soft typography.

Requirements: pip install Pillow

Usage:
    python3 generate_hero_image.py \\
        --title "Title" \\
        --subtitle "Optional subtitle" \\
        --category "Kubernetes" \\
        --output src/collections/blog/2026/04-01-my-post/hero-image.svg \\
        --repo-root /path/to/layer5/repo

    # If --repo-root is omitted, falls back to PNG-only output (no Five, system font)
"""

import argparse
import base64
import io
import math
import random
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("Error: Pillow is required. Run: pip install Pillow")
    sys.exit(1)

# Layer5 Brand Colors
TEAL    = (0, 179, 159)    # #00B39F
BG_VOID = (8, 10, 16)      # Deep space black
BG_DEEP = (14, 18, 30)     # Dark navy
WHITE   = (255, 255, 255)
SUBTLE  = (140, 148, 168)  # Muted grey

TEAL_HEX   = "#00B39F"
WHITE_HEX  = "#FFFFFF"
SUBTLE_HEX = "#8C94A8"

NEBULA_PALETTES = {
    "Kubernetes":           [(30, 60, 160),   (10, 30, 100)],
    "Meshery":              [(0, 100, 90),    (0, 60, 55)],
    "Kanvas":               [(60, 40, 140),   (30, 20, 90)],
    "AI":                   [(80, 30, 120),   (50, 10, 80)],
    "Engineering":          [(120, 50, 20),   (80, 30, 10)],
    "Platform Engineering": [(0, 80, 70),     (0, 50, 40)],
    "Cloud Native":         [(10, 80, 120),   (5, 50, 80)],
    "Docker":               [(10, 80, 140),   (5, 50, 90)],
    "Open Source":          [(0, 100, 90),    (0, 60, 55)],
    "Observability":        [(0, 90, 80),     (0, 55, 50)],
    "Community":            [(100, 60, 10),   (70, 40, 5)],
    "Events":               [(110, 20, 20),   (70, 10, 10)],
}
DEFAULT_NEBULA = [(20, 50, 80), (10, 30, 55)]


# ── Background raster helpers ──────────────────────────────────────────────

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def ease_inout(t):
    return t * t * (3 - 2 * t)

def clamp(v):
    return max(0, min(255, int(v)))

def noise_val(x, y, seed=42):
    n = math.sin(x * 127.1 + y * 311.7 + seed) * 43758.5453
    return n - math.floor(n)

def build_cosmic_bg(width, height, nebula_colors):
    nc1, nc2 = nebula_colors
    img = Image.new("RGB", (width, height))
    pixels = []
    for y in range(height):
        ty = y / height
        for x in range(width):
            tx = x / width
            base = lerp_color(BG_VOID, BG_DEEP, ease_inout(ty))
            dx1, dy1 = tx - 0.25, ty - 0.35
            d1 = math.sqrt(dx1**2 * 0.6 + dy1**2) * 2.0
            s1 = max(0.0, 1.0 - d1) ** 2.2 * 0.55
            # Nebula glow where Five will stand (right side)
            dx2, dy2 = tx - 0.82, ty - 0.58
            d2 = math.sqrt(dx2**2 * 0.9 + dy2**2 * 0.6) * 2.3
            s2 = max(0.0, 1.0 - d2) ** 2.5 * 0.38
            nv = noise_val(tx * 4.3, ty * 3.1) * 0.12 + noise_val(tx * 7.1, ty * 5.3, 13) * 0.05
            r = base[0] + clamp(nc1[0] * (s1 + nv)) + clamp(nc2[0] * s2 * 0.6)
            g = base[1] + clamp(nc1[1] * (s1 + nv)) + clamp(nc2[1] * s2 * 0.6)
            b = base[2] + clamp(nc1[2] * (s1 + nv)) + clamp(nc2[2] * s2 * 0.6)
            pixels.append((clamp(r), clamp(g), clamp(b)))
    img.putdata(pixels)
    return img.filter(ImageFilter.GaussianBlur(radius=2))

def draw_stars(draw, width, height, count=180, seed=42):
    rng = random.Random(seed)
    for _ in range(count):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        size = rng.choices([0, 0, 1, 1, 1, 2], k=1)[0]
        br = rng.randint(140, 255)
        tint = rng.choice([(br, br, br), (br, int(br*.9), int(br*.7)), (int(br*.8), br, int(br*.95))])
        if size == 0:
            draw.point((x, y), fill=tint)
        elif size == 1:
            draw.ellipse([x, y, x+1, y+1], fill=tint)
        else:
            draw.ellipse([x-1, y-1, x+1, y+1], fill=tint)
            draw.line([(x-2, y), (x+2, y)], fill=(*tint, 100), width=1)
            draw.line([(x, y-2), (x, y+2)], fill=(*tint, 100), width=1)


# ── Font helpers ───────────────────────────────────────────────────────────

def find_qanelas(repo_root, weight="Bold"):
    """Find Qanelas Soft font in the Layer5 repo."""
    if repo_root:
        font_dir = Path(repo_root).expanduser() / "static/fonts/qanelas-soft"
        candidate = font_dir / f"QanelasSoft{weight}.otf"
        if candidate.exists():
            return str(candidate)
    # System fallbacks
    fallbacks = {
        "Bold": [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ],
        "Regular": [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ],
    }
    for path in fallbacks.get(weight, fallbacks["Regular"]):
        if Path(path).exists():
            return path
    return None

def load_font(size, bold=False, repo_root=None):
    weight = "Bold" if bold else "Regular"
    path = find_qanelas(repo_root, weight)
    if path:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()

def b64_font(repo_root, weight="Bold"):
    path = find_qanelas(repo_root, weight)
    if path:
        return base64.b64encode(Path(path).read_bytes()).decode()
    return None

def text_dims(draw, text, font):
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0], b[3] - b[1]

def wrap_text(draw, text, font, max_w):
    words, lines, line = text.split(), [], []
    for word in words:
        test = " ".join(line + [word])
        w, _ = text_dims(draw, test, font)
        if w <= max_w:
            line.append(word)
        else:
            if line:
                lines.append(" ".join(line))
            line = [word]
    if line:
        lines.append(" ".join(line))
    return lines


# ── Five SVG helpers ───────────────────────────────────────────────────────

def find_five_svg(repo_root, seed=None):
    """
    Pick one of the simple standalone Five pose SVGs from src/assets/images/five/SVG/.

    Only the smaller numbered SVGs are used — these show Five as a clean standalone
    stick figure against a plain background, suitable for hero image overlays.
    The complex scene SVGs (vehicles, group scenes, environment props) are excluded
    because they extend outside the composition frame and look odd when cropped.

    Returns the file path or None.
    """
    if not repo_root:
        return None
    five_dir = Path(repo_root).expanduser() / "src/assets/images/five/SVG"

    # Curated list: simple standalone poses only.
    # Excluded: 1 (complex), 3 (scene), 4 (scene), 5 (car), 9 (scene),
    #           10 (complex), 13 (scene), 15 (complex), 16 (scene)
    SIMPLE_POSES = ["2", "6", "7", "8", "11", "12", "14", "17", "18", "19"]
    candidates = [five_dir / f"{n}.svg" for n in SIMPLE_POSES
                  if (five_dir / f"{n}.svg").exists()]
    if not candidates:
        # Fallback: any numbered SVG
        candidates = sorted(five_dir.glob("[0-9]*.svg"))
    if not candidates:
        return None
    rng = random.Random(seed)
    return rng.choice(candidates)

def extract_five_inner(svg_text):
    """
    Extract the inner SVG content (everything inside <svg>...</svg>) so we can
    inline it into our composite output SVG.

    Five's skeleton is always BLACK - never invert or recolor the figure.
    High contrast is achieved by placing a bright white glow BEHIND Five
    (see generate_hero_svg), not by changing Five's colors.

    Returns (viewBox, inner_xml_string).
    """
    # Get viewBox
    vb_match = re.search(r'viewBox=["\']([^"\']+)["\']', svg_text)
    viewbox = vb_match.group(1) if vb_match else "0 0 612 792"

    # Strip the outer <svg> wrapper only - preserve all fills as original
    inner = re.sub(r'<\?xml[^?]*\?>', '', svg_text)
    inner = re.sub(r'<svg[^>]*>', '', inner, count=1)
    inner = re.sub(r'</svg\s*>', '', inner)

    return viewbox, inner.strip()


# ── Freeform glow ─────────────────────────────────────────────────────────
#
# Layer5 brand palette used in the glow:
#   #FFFFFF        white (core highlight)
#   #E8F6F4        near-white with teal hint
#   #B3E8E3        very light teal
#   #71C6C1        medium-light teal
#   #00D3A9        bright teal (lighter than brand primary)
#   #00B39F        Layer5 primary teal
#
# The technique mimics Adobe Illustrator's Freeform Gradient: multiple color
# "point stops" placed at different positions in 2D space, each with its own
# hue, and all blended together through a heavy Gaussian blur.  The result is
# a complex, organic color field - not the uniform halo you get from a single
# radial gradient.

FREEFORM_BLOBS = [
    # (rel_x, rel_y, rx_factor, ry_factor, color, opacity)
    # Positions are relative to Five's visual center, scaled by the glow spread.
    # A blob at (0, 0) sits exactly at the center; (-0.3, -0.4) is upper-left, etc.
    (  0.00,  0.00, 1.00, 0.95, "#FFFFFF", 0.94),  # white core - main highlight
    (  0.00, -0.30, 0.58, 0.50, "#FFFFFF", 0.80),  # upper-body bright white
    (  0.00,  0.35, 0.62, 0.52, "#E8F6F4", 0.75),  # lower-body warm white
    ( -0.28,  0.05, 0.48, 0.58, "#B3E8E3", 0.62),  # left shoulder teal hint
    (  0.28, -0.18, 0.42, 0.42, "#71C6C1", 0.50),  # right upper mid-teal
    ( -0.15,  0.42, 0.38, 0.38, "#00D3A9", 0.30),  # lower-left bright teal
    (  0.22,  0.28, 0.34, 0.44, "#B3E8E3", 0.42),  # lower-right light teal
    (  0.00, -0.55, 0.30, 0.30, "#E8F6F4", 0.55),  # top head glow
    (  0.00,  0.00, 0.48, 0.58, "#FFFFFF", 0.50),  # secondary white center
    ( -0.38, -0.25, 0.28, 0.30, "#00B39F", 0.22),  # far-left brand teal accent
    (  0.38,  0.15, 0.26, 0.32, "#00D3A9", 0.22),  # far-right teal accent
]


def build_freeform_glow(filter_id, cx, cy, spread_x, spread_y):
    """
    Return (filter_def_svg, glow_group_svg) for a freeform-gradient-style light
    field behind Five.

    filter_def_svg  -- goes inside the top-level <defs> block
    glow_group_svg  -- goes into the SVG body, before the Five group
    """
    blur_std = max(spread_x, spread_y) * 0.085  # proportional blur radius

    filter_def = (
        f'<filter id="{filter_id}" x="-80%" y="-80%" width="260%" height="260%">\n'
        f'      <feGaussianBlur stdDeviation="{blur_std:.1f}"/>\n'
        f'    </filter>'
    )

    ellipses = []
    for rx_f, ry_f, rx2_f, ry2_f, color, opacity in FREEFORM_BLOBS:
        bx   = cx + rx_f  * spread_x
        by   = cy + ry_f  * spread_y
        brx  = rx2_f * spread_x
        bry  = ry2_f * spread_y
        ellipses.append(
            f'    <ellipse cx="{bx:.1f}" cy="{by:.1f}" '
            f'rx="{brx:.1f}" ry="{bry:.1f}" '
            f'fill="{color}" opacity="{opacity}"/>'
        )

    glow_group = (
        f'<!-- Freeform gradient glow - white + Layer5 brand tones, Gaussian-blended -->\n'
        f'  <g filter="url(#{filter_id})">\n'
        + "\n".join(ellipses)
        + "\n  </g>"
    )

    return filter_def, glow_group


# ── SVG hero image ─────────────────────────────────────────────────────────

def wrap_svg_text(text, max_chars=24):
    """Simple word-wrap for SVG text elements."""
    words = text.split()
    lines, line = [], []
    for word in words:
        if sum(len(w) + 1 for w in line) + len(word) <= max_chars:
            line.append(word)
        else:
            if line:
                lines.append(" ".join(line))
            line = [word]
    if line:
        lines.append(" ".join(line))
    return lines

def generate_hero_svg(title, subtitle, category, output_path, repo_root,
                      img_width=1200, img_height=630):
    """Generate SVG hero image with embedded cosmic background and real Five SVG."""
    nebula = NEBULA_PALETTES.get(category, DEFAULT_NEBULA)

    # Background PNG in memory
    bg_img = build_cosmic_bg(img_width, img_height, nebula)
    bg_draw = ImageDraw.Draw(bg_img, "RGBA")
    draw_stars(bg_draw, img_width, img_height)
    buf = io.BytesIO()
    bg_img.save(buf, "PNG")
    bg_b64 = base64.b64encode(buf.getvalue()).decode()

    # Qanelas font - embed as base64 so the SVG is portable
    bold_b64 = b64_font(repo_root, "Bold") or b64_font(repo_root, "ExtraBold")
    reg_b64  = b64_font(repo_root, "Regular") or b64_font(repo_root, "Medium")
    font_face_bold = (
        f"@font-face {{ font-family: 'QanelasSoft'; font-weight: bold; "
        f"src: url('data:font/otf;base64,{bold_b64}') format('opentype'); }}"
    ) if bold_b64 else ""
    font_face_reg = (
        f"@font-face {{ font-family: 'QanelasSoft'; font-weight: normal; "
        f"src: url('data:font/otf;base64,{reg_b64}') format('opentype'); }}"
    ) if reg_b64 else ""
    font_stack = "'QanelasSoft', 'Helvetica Neue', Arial, sans-serif"

    # Five mascot SVG (random pose, seeded by title for reproducibility)
    five_path = find_five_svg(repo_root, seed=hash(title))
    five_group_svg = ""
    freeform_filter_def = ""
    freeform_glow_svg = ""

    if five_path:
        try:
            viewbox, five_inner = extract_five_inner(five_path.read_text())
            # Five SVG viewBox is typically 0 0 612 792
            vb_parts = [float(x) for x in viewbox.split()]
            vb_w = vb_parts[2] if len(vb_parts) >= 3 else 612
            vb_h = vb_parts[3] if len(vb_parts) >= 4 else 792

            # Five is LARGE - 95% of image height, slightly clipped by canvas clipPath.
            # This makes the mascot the dominant visual element in the composition.
            target_h = img_height * 0.95
            scale = target_h / vb_h
            target_w = vb_w * scale

            # Position Five in the right ~42% of the image, centered vertically.
            right_zone_start = img_width * 0.57
            right_zone_w = img_width - right_zone_start
            x_pos = right_zone_start + max(0, (right_zone_w - target_w) / 2)
            y_pos = (img_height - target_h) / 2  # vertically centered (slight bleed ok)

            # Five's visual body center in canvas coordinates.
            # Horizontally: figures are near x=307 of the 612 viewBox.
            # Vertically: body occupies ~y=165-600 of the 792 viewBox; center ~y=380.
            five_center_x = x_pos + (vb_w * 0.50) * scale
            five_center_y = y_pos + (vb_h * 0.48) * scale

            # Glow spread - generous so blobs surround the full figure height
            glow_spread_x = target_w * 0.65
            glow_spread_y = target_h * 0.55

            # Freeform gradient glow (multi-blob, Layer5 brand colors + white)
            freeform_filter_def, freeform_glow_svg = build_freeform_glow(
                "fiveGlowBlur",
                five_center_x, five_center_y,
                glow_spread_x, glow_spread_y,
            )

            five_group_svg = (
                f"<!-- Five mascot (Layer5 intergalactic Cloud Native Hero) -->\n"
                f"  <!-- Source: {five_path.name} — colors preserved (black skeleton, teal accents) -->\n"
                f"  <g transform=\"translate({x_pos:.1f},{y_pos:.1f}) scale({scale:.4f})\">\n"
                f"    {five_inner}\n"
                f"  </g>"
            )
        except Exception as e:
            five_group_svg = f"<!-- Five SVG error: {e} -->"

    # Category pill
    cat_label = category.upper() if category else "LAYER5"
    margin = 52
    pill_y = 44
    pill_h = 28

    # Title lines (heuristic wrap for SVG)
    max_title_chars = 22  # at ~52px bold, fits ~680px
    title_lines = wrap_svg_text(title, max_title_chars)[:3]
    title_font_size = 52 if len(title_lines) <= 2 else 42

    title_y_start = 140
    line_height = title_font_size + 14
    title_block_h = len(title_lines) * line_height
    # Center vertically
    text_block_h = title_block_h + (50 if subtitle else 0)
    title_y_start = max(130, (img_height - text_block_h) // 2 - 10)

    title_svg = ""
    for i, line in enumerate(title_lines):
        y = title_y_start + i * line_height + title_font_size
        title_svg += f'\n  <text x="{margin}" y="{y}" font-family="{font_stack}" font-size="{title_font_size}" font-weight="bold" fill="{WHITE_HEX}">{line}</text>'

    subtitle_svg = ""
    if subtitle:
        sub_y = title_y_start + title_block_h + 28
        for i, sl in enumerate(wrap_svg_text(subtitle, 38)[:2]):
            subtitle_svg += f'\n  <text x="{margin}" y="{sub_y + i*30}" font-family="{font_stack}" font-size="21" fill="{SUBTLE_HEX}">{sl}</text>'

    footer_y = img_height - 15
    footer_text = "layer5.io  -  Making Engineers Expect More from Their Infrastructure"
    bar_top = img_height - 50

    # freeform_filter_def and freeform_glow_svg are already built above

    svg_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{img_width}" height="{img_height}" viewBox="0 0 {img_width} {img_height}">
  <defs>
    <style>
      {font_face_bold}
      {font_face_reg}
    </style>
    <clipPath id="canvas">
      <rect width="{img_width}" height="{img_height}"/>
    </clipPath>
    {freeform_filter_def}
  </defs>

  <!-- Cosmic background (Pillow-generated PNG) -->
  <image x="0" y="0" width="{img_width}" height="{img_height}"
         href="data:image/png;base64,{bg_b64}" clip-path="url(#canvas)"/>

  <!-- Orbital ring decorations (upper right) -->
  <ellipse cx="{img_width - 70}" cy="-50" rx="310" ry="310"
           fill="none" stroke="{TEAL_HEX}" stroke-opacity="0.07" stroke-width="1"/>
  <ellipse cx="{img_width - 70}" cy="-50" rx="360" ry="360"
           fill="none" stroke="{TEAL_HEX}" stroke-opacity="0.05" stroke-width="1"/>
  <ellipse cx="{img_width - 70}" cy="-50" rx="410" ry="410"
           fill="none" stroke="{TEAL_HEX}" stroke-opacity="0.03" stroke-width="1"/>

  <!-- Freeform gradient glow behind Five: multi-blob blend of white + Layer5 brand teal -->
  {freeform_glow_svg}

  <!-- Five mascot — black skeleton, teal accents, original colors preserved -->
  {five_group_svg}

  <!-- Left teal accent bar -->
  <rect x="0" y="0" width="5" height="{img_height}" fill="{TEAL_HEX}" opacity="0.92"/>

  <!-- Category pill -->
  <rect x="{margin}" y="{pill_y}" width="140" height="{pill_h}" rx="4"
        fill="{TEAL_HEX}" fill-opacity="0.14" stroke="{TEAL_HEX}" stroke-opacity="0.4" stroke-width="1"/>
  <text x="{margin + 12}" y="{pill_y + pill_h - 8}"
        font-family="{font_stack}" font-size="13" font-weight="bold"
        letter-spacing="2" fill="{TEAL_HEX}">{cat_label}</text>

  <!-- Separator -->
  <rect x="{margin}" y="{pill_y + pill_h + 12}" width="260" height="1"
        fill="{TEAL_HEX}" opacity="0.22"/>

  <!-- Title -->
  {title_svg}

  <!-- Subtitle -->
  {subtitle_svg}

  <!-- Bottom bar -->
  <rect x="0" y="{bar_top}" width="{img_width}" height="50" fill="#080A12"/>
  <rect x="0" y="{bar_top}" width="{img_width}" height="2" fill="{TEAL_HEX}" opacity="0.65"/>
  <text x="{margin}" y="{footer_y}"
        font-family="{font_stack}" font-size="13" fill="{SUBTLE_HEX}" opacity="0.7">
    {footer_text}
  </text>
</svg>"""

    out = Path(output_path).with_suffix(".svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg_content, encoding="utf-8")
    print(f"Hero image saved: {out}  ({img_width}x{img_height} SVG)")
    return str(out)


# ── PNG fallback (no repo, no Five) ───────────────────────────────────────

def generate_hero_png(title, subtitle, category, output_path, repo_root=None,
                      img_width=1200, img_height=630):
    """PNG-only fallback when repo_root is not available."""
    nebula = NEBULA_PALETTES.get(category, DEFAULT_NEBULA)
    img = build_cosmic_bg(img_width, img_height, nebula)
    draw = ImageDraw.Draw(img, "RGBA")
    draw_stars(draw, img_width, img_height)

    # Teal left bar
    draw.rectangle([0, 0, 5, img_height], fill=(*TEAL, 230))

    # Orbital ring
    cx, cy, cr = img_width - 70, -50, 310
    for r_off, alpha in [(0, 18), (50, 12), (100, 7)]:
        draw.ellipse([cx - cr - r_off, cy - cr - r_off, cx + cr + r_off, cy + cr + r_off],
                     outline=(*TEAL, alpha), width=1)

    margin, y = 52, 44
    if category:
        cat_font = load_font(15, bold=True, repo_root=repo_root)
        label = category.upper()
        lw, lh = text_dims(draw, label, cat_font)
        px0, py0 = margin, y
        px1, py1 = px0 + lw + 24, py0 + lh + 10
        draw.rounded_rectangle([px0, py0, px1, py1], radius=5,
                                fill=(*TEAL, 35), outline=(*TEAL, 100), width=1)
        draw.text((px0 + 12, py0 + 5), label, font=cat_font, fill=(*TEAL, 230))
        y = py1 + 16
    else:
        brand_font = load_font(18, bold=True, repo_root=repo_root)
        draw.text((margin, y), "LAYER5", font=brand_font, fill=(*TEAL, 210))
        y += 30

    draw.rectangle([margin, y, margin + 260, y + 1], fill=(*TEAL, 55))
    y += 18

    max_w = int(img_width * 0.62) - margin - 20
    title_font, title_lines = None, []
    for sz in [54, 46, 38, 32, 27]:
        title_font = load_font(sz, bold=True, repo_root=repo_root)
        title_lines = wrap_text(draw, title, title_font, max_w)
        if len(title_lines) <= 3:
            break

    _, lh = text_dims(draw, "Ag", title_font)
    line_h = lh + 12
    title_block_h = len(title_lines) * line_h
    sub_block_h = (20 + 40) if subtitle else 0
    title_y = max(y + 8, (img_height - title_block_h - sub_block_h) // 2 - 10)
    for i, line in enumerate(title_lines):
        draw.text((margin, title_y + i * line_h), line, font=title_font, fill=WHITE)
    if subtitle:
        sub_font = load_font(22, repo_root=repo_root)
        sub_y = title_y + title_block_h + 20
        for i, sl in enumerate(wrap_text(draw, subtitle, sub_font, max_w)[:2]):
            draw.text((margin, sub_y + i * 32), sl, font=sub_font, fill=SUBTLE)

    bar_h = 50
    draw.rectangle([0, img_height - bar_h, img_width, img_height], fill=(8, 10, 18))
    draw.rectangle([0, img_height - bar_h, img_width, img_height - bar_h + 2],
                   fill=(*TEAL, 160))
    footer_font = load_font(14, repo_root=repo_root)
    footer = "layer5.io  -  Making Engineers Expect More from Their Infrastructure"
    draw.text((margin, img_height - bar_h + 16), footer, font=footer_font, fill=(*SUBTLE, 170))

    out = Path(output_path)
    if out.suffix.lower() == ".svg":
        out = out.with_suffix(".png")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), "PNG", optimize=True)
    print(f"Hero image saved (PNG fallback): {out}  ({img_width}x{img_height}px)")
    return str(out)


# ── Entry point ────────────────────────────────────────────────────────────

def generate_hero_image(title, subtitle=None, category=None,
                        output_path="./hero-image.svg",
                        repo_root=None,
                        img_width=1200, img_height=630):
    """
    Main entry point. Uses SVG output with embedded Five mascot when repo_root
    is provided (recommended). Falls back to PNG if repo_root is absent.
    """
    if repo_root and Path(repo_root).expanduser().exists():
        return generate_hero_svg(title, subtitle, category, output_path,
                                 repo_root, img_width, img_height)
    else:
        return generate_hero_png(title, subtitle, category, output_path,
                                 repo_root, img_width, img_height)


def main():
    p = argparse.ArgumentParser(description="Layer5 blog hero image generator")
    p.add_argument("--title",     required=True, help="Blog post title")
    p.add_argument("--subtitle",  default=None,  help="Optional subtitle")
    p.add_argument("--category",  default=None,  help="Category (affects nebula color)")
    p.add_argument("--output",    default="./hero-image.svg", help="Output path")
    p.add_argument("--repo-root", default=None,
                   help="Path to Layer5 repo root (enables Five mascot + Qanelas font)")
    p.add_argument("--width",     type=int, default=1200)
    p.add_argument("--height",    type=int, default=630)
    args = p.parse_args()
    generate_hero_image(args.title, args.subtitle, args.category,
                        args.output, args.repo_root, args.width, args.height)

if __name__ == "__main__":
    main()
