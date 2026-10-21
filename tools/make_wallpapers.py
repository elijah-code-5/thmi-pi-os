#!/usr/bin/env python3
"""Draw the wallpaper gallery (240x320, RGB565 raw) and write dist/content_index.json. Needs Pillow."""
import json, math, os, random, sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 240, 320


def grad(top, bottom, diag=False):
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        for x in range(W):
            t = (y / (H - 1)) if not diag else ((x / W + y / H) / 2)
            px[x, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return im


def ocean():
    im = grad((10, 40, 90), (0, 160, 170)); d = ImageDraw.Draw(im, "RGBA")
    for i in range(6):
        y0 = 150 + i * 28
        pts = [(x, y0 + 9 * math.sin(x / 22 + i)) for x in range(0, W + 6, 6)] + [(W, H), (0, H)]
        d.polygon(pts, fill=(255, 255, 255, 14))
    return im


def sunset():
    im = grad((255, 140, 50), (90, 30, 120)); d = ImageDraw.Draw(im, "RGBA")
    d.ellipse((70, 110, 170, 210), fill=(255, 230, 150, 230))
    d.rectangle((0, 210, W, H), fill=(40, 15, 70, 255))
    for i in range(5):
        d.rectangle((0, 214 + i * 16, W, 217 + i * 16), fill=(255, 140, 50, 70))
    return im


def forest():
    im = grad((25, 70, 60), (10, 35, 30)); d = ImageDraw.Draw(im, "RGBA"); r = random.Random(3)
    for layer in range(3):
        base = 150 + layer * 55; col = (10 + layer * 8, 70 - layer * 14, 45 - layer * 8, 255)
        for x in range(-10, W + 20, 26):
            h = r.randint(60, 110) - layer * 8
            d.polygon([(x, base), (x + 13, base - h), (x + 26, base)], fill=col)
        d.rectangle((0, base, W, H), fill=col)
    return im


def aurora():
    im = grad((5, 10, 35), (10, 40, 50)); d = ImageDraw.Draw(im, "RGBA")
    for i, col in enumerate(((60, 255, 160), (90, 140, 255), (200, 90, 255))):
        for x in range(0, W, 2):
            y = 90 + i * 24 + 26 * math.sin(x / 38 + i * 1.4)
            d.line((x, y, x, y + 70), fill=col + (22,), width=2)
    r = random.Random(1)
    for _ in range(50):
        d.point((r.randint(0, W - 1), r.randint(0, H // 2)), fill=(255, 255, 255, 255))
    return im


def midnight():
    im = grad((2, 5, 20), (25, 20, 60)); d = ImageDraw.Draw(im); r = random.Random(7)
    for _ in range(140):
        x, y = r.randint(0, W - 1), r.randint(0, H - 1); b = r.randint(120, 255)
        d.point((x, y), fill=(b, b, 255))
    d.ellipse((150, 40, 200, 90), fill=(240, 240, 220)); d.ellipse((165, 35, 215, 85), fill=(8, 10, 30))
    return im


def candy():
    im = grad((255, 120, 190), (110, 150, 255), diag=True); d = ImageDraw.Draw(im, "RGBA"); r = random.Random(4)
    for _ in range(14):
        x, y, s = r.randint(0, W), r.randint(0, H), r.randint(14, 46)
        d.ellipse((x - s, y - s, x + s, y + s), fill=(255, 255, 255, 40))
    return im


def mono():
    im = grad((60, 60, 66), (14, 14, 18)); d = ImageDraw.Draw(im, "RGBA")
    for i in range(7):
        d.ellipse((120 - i * 34, 160 - i * 34, 120 + i * 34, 160 + i * 34), outline=(255, 255, 255, 26), width=2)
    return im


def mountains():
    im = grad((255, 190, 140), (255, 235, 210)); d = ImageDraw.Draw(im, "RGBA"); r = random.Random(11)
    for layer, col in enumerate(((150, 120, 150), (110, 90, 130), (60, 50, 90))):
        pts = [(0, H)]; y = 150 + layer * 40
        for x in range(0, W + 30, 30):
            y2 = y + r.randint(-35, 20); pts.append((x, y2))
        pts.append((W, H)); d.polygon(pts, fill=col + (255,))
    return im


def waves():
    im = grad((0, 40, 80), (0, 20, 40)); d = ImageDraw.Draw(im, "RGBA")
    for i in range(14):
        pts = [(x, 40 + i * 20 + 14 * math.sin(x / 30 + i * 0.7)) for x in range(0, W + 4, 4)]
        d.line(pts, fill=(80, 200, 255, 70), width=2)
    return im


def geometric():
    im = Image.new("RGB", (W, H), (30, 30, 50)); d = ImageDraw.Draw(im); r = random.Random(5)
    for y in range(0, H, 40):
        for x in range(0, W, 40):
            c = r.choice(((52, 152, 219), (155, 89, 182), (26, 188, 156), (241, 196, 15), (231, 76, 60)))
            c = tuple(int(v * 0.6) for v in c)
            d.polygon([(x, y), (x + 40, y), (x + 40, y + 40)], fill=c)
            d.polygon([(x, y), (x, y + 40), (x + 40, y + 40)], fill=tuple(int(v * 0.8) for v in c))
    return im


def neon():
    im = grad((20, 0, 40), (90, 0, 90)); d = ImageDraw.Draw(im, "RGBA")
    d.ellipse((60, 60, 180, 180), fill=(255, 90, 160, 255)); d.rectangle((0, 150, W, H), fill=(15, 0, 30, 255))
    for i in range(10):
        y = 150 + i * i * 2 + 4
        d.line((0, y, W, y), fill=(0, 255, 230, 160), width=1)
    for i in range(-8, 9):
        d.line((120, 150, 120 + i * 40, H), fill=(0, 255, 230, 120), width=1)
    return im


def bokeh():
    im = grad((20, 25, 45), (45, 25, 55)); d = ImageDraw.Draw(im, "RGBA"); r = random.Random(9)
    for _ in range(26):
        x, y, s = r.randint(0, W), r.randint(0, H), r.randint(8, 34)
        c = r.choice(((255, 200, 120), (120, 200, 255), (255, 140, 200)))
        d.ellipse((x - s, y - s, x + s, y + s), fill=c + (r.randint(30, 80),))
    return im


def dunes():
    im = grad((250, 200, 130), (255, 235, 190)); d = ImageDraw.Draw(im, "RGBA")
    for i, col in enumerate(((220, 150, 80), (190, 120, 60), (150, 90, 50))):
        pts = [(x, 170 + i * 45 + 28 * math.sin(x / 55 + i * 2)) for x in range(0, W + 6, 6)] + [(W, H), (0, H)]
        d.polygon(pts, fill=col + (255,))
    return im


def city():
    im = grad((20, 30, 70), (240, 120, 120)); d = ImageDraw.Draw(im, "RGBA"); r = random.Random(2)
    x = 0
    while x < W:
        w, h = r.randint(18, 38), r.randint(60, 190)
        d.rectangle((x, H - h, x + w, H), fill=(15, 15, 35, 255))
        for wy in range(H - h + 6, H - 6, 12):
            for wx in range(x + 4, x + w - 4, 8):
                if r.random() < 0.4:
                    d.rectangle((wx, wy, wx + 3, wy + 5), fill=(255, 220, 120, 230))
        x += w + 2
    return im


def black():
    return Image.new("RGB", (W, H), (0, 0, 0))


def paper():
    im = grad((250, 248, 240), (232, 228, 214)); d = ImageDraw.Draw(im, "RGBA")
    for y in range(20, H, 24):
        d.line((0, y, W, y), fill=(120, 140, 170, 40))
    return im


WALLS = (
    ("ocean", "Ocean", "dark", ocean, (10, 90, 130)), ("sunset", "Sunset", "dark", sunset, (255, 140, 50)),
    ("forest", "Forest", "dark", forest, (25, 90, 60)), ("aurora", "Aurora", "dark", aurora, (60, 200, 160)),
    ("midnight", "Midnight stars", "dark", midnight, (20, 20, 60)), ("candy", "Candy", "light", candy, (255, 120, 190)),
    ("mono", "Mono rings", "dark", mono, (60, 60, 66)), ("mountains", "Mountains", "light", mountains, (150, 120, 150)),
    ("waves", "Deep waves", "dark", waves, (0, 60, 100)), ("geometric", "Geometric", "dark", geometric, (60, 60, 100)),
    ("neon", "Neon grid", "dark", neon, (255, 90, 160)), ("bokeh", "Bokeh", "dark", bokeh, (80, 60, 110)),
    ("dunes", "Dunes", "light", dunes, (220, 150, 80)), ("city", "City dusk", "dark", city, (150, 70, 110)),
    ("black", "Pure black", "dark", black, (0, 0, 0)), ("paper", "Paper", "light", paper, (240, 236, 224)),
)

PRESETS = (
    {"id": "ocean-calm", "name": "Ocean Calm", "wall": "ocean", "accent": "0x1E88E5", "light": False, "bg": "0x0A2A4A", "boot_text": "Welcome back"},
    {"id": "sunset-glow", "name": "Sunset Glow", "wall": "sunset", "accent": "0xF39C12", "light": False, "bg": "0x3A1C4A", "boot_text": "Good evening"},
    {"id": "forest-walk", "name": "Forest Walk", "wall": "forest", "accent": "0x2ECC71", "light": False, "bg": "0x0B2A20", "boot_text": "Hello"},
    {"id": "aurora-night", "name": "Aurora Night", "wall": "aurora", "accent": "0x8E44AD", "light": False, "bg": "0x05102A", "boot_text": "Aurora"},
    {"id": "neon-grid", "name": "Neon Grid", "wall": "neon", "accent": "0xEC048C", "light": False, "bg": "0x14002A", "boot_text": "T-HMI", "dim": "10"},
    {"id": "candy-pop", "name": "Candy Pop", "wall": "candy", "accent": "0xEC048C", "light": True, "bg": "0xFFB0D8", "boot_text": "Hi!", "dim": "0"},
    {"id": "paper-light", "name": "Paper Light", "wall": "paper", "accent": "0x607D8B", "light": True, "bg": "0xF5F2E8", "boot_text": "", "dim": "0", "icon": "64"},
    {"id": "mono-focus", "name": "Mono Focus", "wall": "black", "accent": "0x607D8B", "light": False, "bg": "0x000000", "boot_text": "", "icon": "48", "dim": "0"},
)


def rgb565(im):
    px = im.convert("RGB").tobytes()
    out = bytearray(W * H * 2)
    for i in range(W * H):
        r, g, b = px[i * 3], px[i * 3 + 1], px[i * 3 + 2]
        v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        out[i * 2] = v & 0xFF
        out[i * 2 + 1] = v >> 8
    return bytes(out)


def build(repo, out):
    os.makedirs(out, exist_ok=True)
    walls = []
    for wid, name, tone, fn, sw in WALLS:
        fname = "wall_%s_240x320_RGB565.raw" % wid
        open(os.path.join(out, fname), "wb").write(rgb565(fn()))
        Image.open if False else None
        fn().save(os.path.join(out, "preview_%s.png" % wid)) if os.environ.get("PREVIEWS") else None
        walls.append({"id": wid, "name": name, "tone": tone, "swatch": "0x%02X%02X%02X" % sw,
                      "url": "https://github.com/%s/releases/download/apps-latest/%s" % (repo, fname)})
    json.dump({"wallpapers": walls, "presets": list(PRESETS)}, open(os.path.join(out, "content_index.json"), "w"), indent=1)
    return len(walls)


if __name__ == "__main__":
    print("wallpapers:", build(sys.argv[1] if len(sys.argv) > 1 else "elijah-code-5/thmi-pi-os", sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "dist")))
