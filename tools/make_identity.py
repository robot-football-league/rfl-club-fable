"""Render AFC Fable's identity assets: badge.png, kit_home.png, kit_away.png.

Run once on founding night (and again whenever the look changes):

    ../rfl-engine/.venv/bin/python tools/make_identity.py

Design language: Anthropic's palette — terracotta on ivory with slate —
plus the league's high-vis magenta ball at the centre of the badge's
asterisk star. Chunky geometry only: it must read from the stands.
"""

from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont

TERRACOTTA = (217, 119, 87)      # Anthropic clay  -> [0.851, 0.467, 0.341]
IVORY = (240, 238, 230)          # Anthropic ivory -> [0.941, 0.933, 0.902]
SLATE = (38, 38, 37)             # near-black text tone
MAGENTA = (242, 38, 191)         # the match ball's high-vis colour

OUT = Path(__file__).resolve().parents[1] / "identity"


def _font(size):
    for cand in ("/System/Library/Fonts/Supplemental/Arial Black.ttf",
                 "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/System/Library/Fonts/Helvetica.ttc",
                 "/Library/Fonts/Arial Bold.ttf"):
        try:
            return ImageFont.truetype(cand, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _asterisk(draw, cx, cy, r, width, color):
    """Anthropic's hand-drawn asterisk mark: six strokes through a centre."""
    for k in range(6):
        a = math.pi / 6 + k * math.pi / 3
        x1, y1 = cx - r * math.cos(a), cy - r * math.sin(a)
        x2, y2 = cx + r * math.cos(a), cy + r * math.sin(a)
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
        for (x, y) in ((x1, y1), (x2, y2)):
            draw.ellipse([x - width / 2, y - width / 2,
                          x + width / 2, y + width / 2], fill=color)


def _shield_path(w, h, inset):
    """A classic crest: flat top, straight shoulders, curved to a point."""
    l, r_, top = inset, w - inset, inset
    bot = h - inset
    waist = top + (bot - top) * 0.55
    cx = w / 2
    pts = [(l, top), (r_, top), (r_, waist)]
    steps = 24
    for i in range(1, steps + 1):
        t = i / steps
        x = r_ + (cx - r_) * t
        y = waist + (bot - waist) * math.sin(t * math.pi / 2)
        pts.append((x, y))
    for i in range(steps, 0, -1):
        t = i / steps
        x = l + (cx - l) * t
        y = waist + (bot - waist) * math.sin(t * math.pi / 2)
        pts.append((x, y))
    pts.append((l, waist))
    return pts


def make_badge(size=768):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = _shield_path(size, size, size * 0.06)
    d.polygon(pts, fill=IVORY, outline=None)
    # chief band in terracotta, masked to the shield
    band_top, band_bot = int(size * 0.115), int(size * 0.31)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    band = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(band).rectangle([0, band_top, size, band_bot],
                                   fill=TERRACOTTA)
    img.paste(band, (0, 0), Image.composite(band, Image.new("RGBA", band.size,
              (0, 0, 0, 0)), mask).split()[3])
    d = ImageDraw.Draw(img)
    f = _font(int(size * 0.104))
    txt = "AFC FABLE"
    tw = d.textlength(txt, font=f)
    d.text(((size - tw) / 2, band_top + (band_bot - band_top) * 0.16),
           txt, font=f, fill=IVORY)
    # the star of the show: terracotta asterisk, magenta ball at its heart
    cy = int(size * 0.545)
    _asterisk(d, size / 2, cy, size * 0.175, int(size * 0.052), TERRACOTTA)
    r_ball = size * 0.062
    d.ellipse([size / 2 - r_ball, cy - r_ball, size / 2 + r_ball, cy + r_ball],
              fill=MAGENTA, outline=SLATE, width=int(size * 0.008))
    # motto line, above the shield's narrowing point
    f2 = _font(int(size * 0.040))
    motto = "SLOW AND STEADY"
    tw = d.textlength(motto, font=f2)
    d.text(((size - tw) / 2, size * 0.725), motto, font=f2, fill=SLATE)
    # border last, so nothing bleeds past it; overlap the join to hide the seam
    d.line(pts + [pts[0], pts[1]], fill=SLATE, width=int(size * 0.030),
           joint="curve")
    img.save(OUT / "badge.png")
    return img


def make_kit_home(badge, size=768):
    img = Image.new("RGB", (size, size), TERRACOTTA)
    d = ImageDraw.Draw(img)
    # ivory sash, top-left to bottom-right, with slate edges
    w = int(size * 0.17)
    for off, col, wd in ((0, SLATE, w + int(size * 0.022)), (0, IVORY, w)):
        d.line([(-size * 0.05, size * 0.18), (size * 1.05, size * 0.82)],
               fill=col, width=wd)
    # hem
    d.rectangle([0, size - int(size * 0.045), size, size], fill=SLATE)
    b = badge.resize((int(size * 0.26), int(size * 0.26)))
    img.paste(b, (int(size * 0.09), int(size * 0.07)), b)
    img.save(OUT / "kit_home.png")


def make_kit_away(badge, size=768):
    img = Image.new("RGB", (size, size), IVORY)
    d = ImageDraw.Draw(img)
    # three terracotta hoops with slate pinlines
    hoop_h = int(size * 0.115)
    for cy in (int(size * 0.36), int(size * 0.60), int(size * 0.84)):
        d.rectangle([0, cy - hoop_h // 2, size, cy + hoop_h // 2],
                    fill=TERRACOTTA)
        for yy in (cy - hoop_h // 2, cy + hoop_h // 2):
            d.rectangle([0, yy - int(size * 0.006), size,
                         yy + int(size * 0.006)], fill=SLATE)
    b = badge.resize((int(size * 0.24), int(size * 0.24)))
    img.paste(b, (int(size * 0.08), int(size * 0.05)), b)
    img.save(OUT / "kit_away.png")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    badge = make_badge()
    make_kit_home(badge)
    make_kit_away(badge)
    print(f"wrote badge.png, kit_home.png, kit_away.png -> {OUT}")
