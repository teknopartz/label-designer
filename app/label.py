from PIL import Image, ImageDraw, ImageFont

# 62mm continuous roll -> 696px printable width at 300 DPI (confirmed in AUDIT.md).
LABEL_WIDTH_PX = 696

MARGIN_TOP = 24
MARGIN_BOTTOM = 24
MARGIN_LEFT = 35
MARGIN_RIGHT = 35

DEFAULT_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def render_text_label(text, font_size=60, font_path=DEFAULT_FONT_PATH):
    """Phase 0: single font, single text block, left-aligned, on a 62mm endless label.
    Rich multi-element layout arrives in Phase 2 via the canvas editor."""
    font = ImageFont.truetype(font_path, font_size)

    scratch = Image.new('L', (10, 10), 'white')
    draw = ImageDraw.Draw(scratch)
    bbox = draw.multiline_textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    height = text_height + MARGIN_TOP + MARGIN_BOTTOM
    img = Image.new('RGB', (LABEL_WIDTH_PX, height), 'white')
    draw = ImageDraw.Draw(img)
    draw.multiline_text(
        (MARGIN_LEFT, MARGIN_TOP - bbox[1]),
        text,
        fill=(0, 0, 0),
        font=font,
    )
    return img
