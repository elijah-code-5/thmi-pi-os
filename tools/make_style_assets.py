#!/usr/bin/env python3
"""Generate wallpapers (240x320) and boot images (white on transparent, like the stock logo) into style/."""
import json, math, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 240, 320
os.makedirs(f"{ROOT}/style/wall", exist_ok=True)
os.makedirs(f"{ROOT}/style/boot", exist_ok=True)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def vgrad(c1, c2, stops=None):
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        d.line((0, y, W, y), fill=lerp(c1, c2, y / (H - 1)))
    return im


def save(im, kind, name):
    im.convert("RGB").save(f"{ROOT}/style/{kind}/{name}.png", optimize=True)


walls = []
GRADS = {"sunset": ("ff7e5f", "3a1c71"), "ocean": ("0f2027", "2c7da0"), "forest": ("0b3d2e", "6bbf59"), "grape": ("2d1b69", "b565e8"),
         "peach": ("ffb88c", "de6262"), "midnight": ("020024", "1b3a6b"), "mint": ("0f9b8e", "d3f8e2"), "ember": ("1a0000", "ff5e00"),
         "slate": ("1e2328", "4b5563"), "candy": ("ff9a9e", "a18cd1"), "sky": ("2b86c5", "dff3ff"), "lemon": ("f7971e", "ffd200")}
for n, (a, b) in GRADS.items():
    save(vgrad(hexc(a), hexc(b)), "wall", "grad-" + n); walls.append(("Gradient " + n, "grad-" + n))

random.seed(7)
# stripes
for n, (a, b) in {"stripes-blue": ("12263f", "1e4d7b"), "stripes-rose": ("3b1f2b", "7a2e4d"), "stripes-green": ("10281c", "1f5a3d")}.items():
    im = Image.new("RGB", (W, H), hexc(a)); d = ImageDraw.Draw(im)
    for i in range(-H, W, 28):
        d.polygon([(i, 0), (i + 14, 0), (i + 14 + H, H), (i + H, H)], fill=hexc(b))
    save(im, "wall", n); walls.append(("Stripes " + n.split("-")[1], n))
# dots
for n, (a, b) in {"dots-dark": ("14171c", "2a313b"), "dots-navy": ("0a1a33", "1d3f73"), "dots-warm": ("2a1a14", "6b3d28")}.items():
    im = Image.new("RGB", (W, H), hexc(a)); d = ImageDraw.Draw(im)
    for y in range(8, H, 20):
        for x in range(8 + (y // 20 % 2) * 10, W, 20):
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=hexc(b))
    save(im, "wall", n); walls.append(("Dots " + n.split("-")[1], n))
# grid
im = Image.new("RGB", (W, H), hexc("0b132b")); d = ImageDraw.Draw(im)
for x in range(0, W, 20): d.line((x, 0, x, H), fill=hexc("1c2d57"))
for y in range(0, H, 20): d.line((0, y, W, y), fill=hexc("1c2d57"))
save(im, "wall", "grid-blue"); walls.append(("Blueprint grid", "grid-blue"))
# waves
for n, (a, b, c) in {"waves-ocean": ("0a2540", "145374", "1f8ab0"), "waves-dusk": ("2b1055", "5b2a86", "d1478c")}.items():
    im = Image.new("RGB", (W, H), hexc(a)); d = ImageDraw.Draw(im)
    for k, col in enumerate((b, c)):
        base = 170 + k * 60
        pts = [(x, base + 16 * math.sin(x / 24 + k * 2)) for x in range(0, W + 1, 4)]
        d.polygon(pts + [(W, H), (0, H)], fill=hexc(col))
    save(im, "wall", n); walls.append(("Waves " + n.split("-")[1], n))
# sun / moon
im = vgrad(hexc("141e30"), hexc("243b55")); d = ImageDraw.Draw(im)
d.ellipse((140, 50, 200, 110), fill=hexc("f5f0d0"))
for _ in range(60):
    x, y = random.randrange(W), random.randrange(150); d.point((x, y), fill=(230, 230, 255))
save(im, "wall", "night-moon"); walls.append(("Night moon", "night-moon"))
im = vgrad(hexc("ff9966"), hexc("ff5e62")); d = ImageDraw.Draw(im)
d.ellipse((60, 150, 180, 270), fill=hexc("ffe29a")); d.rectangle((0, 230, W, H), fill=hexc("2b1d3a"))
save(im, "wall", "sunrise"); walls.append(("Sunrise", "sunrise"))
# mountains
im = vgrad(hexc("3a6073"), hexc("16222a")); d = ImageDraw.Draw(im)
for k, (col, amp, base) in enumerate((("2c3e50", 60, 200), ("1b2631", 50, 250))):
    pts = [(x, base - abs(math.sin(x / 38 + k)) * amp) for x in range(0, W + 1, 6)]
    d.polygon(pts + [(W, H), (0, H)], fill=hexc(col))
save(im, "wall", "mountains"); walls.append(("Mountains", "mountains"))
# plain dark / light
for n, c in {"black": "000000", "charcoal": "16181d", "paper": "f2efe6"}.items():
    save(Image.new("RGB", (W, H), hexc(c)), "wall", "solid-" + n); walls.append(("Solid " + n, "solid-" + n))

# ---- boot images: white on transparent ----
def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

boots = []
def boot(name, label, draw):
    im = Image.new("RGBA", (240, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    draw(d)
    im.save(f"{ROOT}/style/boot/{name}.png", optimize=True); boots.append((label, name))

def text(t, size=46):
    def f(d):
        fo = font(size); w = d.textlength(t, font=fo); d.text(((240 - w) / 2, 60 - size * 0.62), t, font=fo, fill=(255, 255, 255, 255))
    return f
for n, t, sz in (("thmi", "T-HMI", 52), ("hub", "HUB OS", 44), ("pixel", "PIXEL", 50), ("hello", "hello", 52), ("nova", "NOVA", 52), ("zen", "zen", 56)):
    boot("text-" + n, "Text: " + t, text(t, sz))
def rings(d):
    for r in (46, 34, 22, 10): d.ellipse((120 - r, 60 - r, 120 + r, 60 + r), outline=(255, 255, 255, 255), width=4)
boot("rings", "Rings", rings)
def tri(d):
    d.polygon([(120, 14), (176, 104), (64, 104)], outline=(255, 255, 255, 255), width=6)
boot("triangle", "Triangle", tri)
def blob(d):
    d.rounded_rectangle((84, 24, 156, 96), 24, fill=(255, 255, 255, 255)); d.ellipse((102, 48, 112, 60), fill=(0, 0, 0, 0)); d.ellipse((128, 48, 138, 60), fill=(0, 0, 0, 0))
boot("blob", "Blob", blob)
def bars(d):
    for i, h in enumerate((30, 60, 90, 60, 30)): d.rounded_rectangle((60 + i * 26, 105 - h, 76 + i * 26, 105), 6, fill=(255, 255, 255, 255))
boot("bars", "Bars", bars)
def robot(d):
    d.rounded_rectangle((70, 40, 170, 100), 16, outline=(255, 255, 255, 255), width=6); d.ellipse((92, 60, 108, 76), fill=(255, 255, 255, 255)); d.ellipse((132, 60, 148, 76), fill=(255, 255, 255, 255)); d.line((120, 40, 120, 18), fill=(255, 255, 255, 255), width=6)
boot("robot", "Robot", robot)

json.dump({"wallpapers": [{"name": n, "file": f + ".png"} for n, f in walls], "boot": [{"name": n, "file": f + ".png"} for n, f in boots]},
          open(f"{ROOT}/style/index.json", "w"), indent=1)
print(len(walls), "wallpapers,", len(boots), "boot images")
