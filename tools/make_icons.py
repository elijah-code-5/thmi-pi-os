#!/usr/bin/env python3
"""Draw the 64x64 launcher icons (icon_64x64.png, RGBA) for each app."""
import os
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 256  # draw big, shrink for smooth edges

def base(color):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((8, 8, S - 8, S - 8), 56, fill=color)
    return im, ImageDraw.Draw(im)

def robot():
    im, d = base((0, 150, 110, 255)); w = (255, 255, 255, 255)
    d.rounded_rectangle((60, 90, 196, 190), 22, fill=w)             # head
    d.ellipse((88, 120, 116, 148), fill=(0, 150, 110, 255)); d.ellipse((140, 120, 168, 148), fill=(0, 150, 110, 255))
    d.rectangle((120, 58, 136, 90), fill=w); d.ellipse((112, 44, 144, 76), fill=w)   # antenna
    d.rectangle((96, 162, 160, 172), fill=(0, 150, 110, 255))
    return im

def hub():
    im, d = base((30, 100, 220, 255)); w = (255, 255, 255, 255)
    d.rounded_rectangle((52, 64, 204, 160), 14, outline=w, width=12)     # screen
    d.rectangle((116, 160, 140, 190), fill=w); d.rounded_rectangle((84, 186, 172, 204), 8, fill=w)  # stand
    d.polygon([(112, 92), (112, 132), (148, 112)], fill=w)                # play
    return im

def store():
    im, d = base((240, 140, 20, 255)); w = (255, 255, 255, 255)
    d.rounded_rectangle((60, 92, 196, 196), 16, fill=w)                   # bag
    d.arc((96, 52, 160, 124), 180, 360, fill=w, width=12)                 # handle
    d.polygon([(128, 118), (128, 160), (108, 140)], fill=(240, 140, 20, 255))
    d.rectangle((120, 118, 136, 160), fill=(240, 140, 20, 255)); d.polygon([(104, 144), (152, 144), (128, 172)], fill=(240, 140, 20, 255))
    return im


W = (255, 255, 255, 255)

def tint(c, f=0.55):
    return tuple(int(x * f) for x in c[:3]) + (255,)

def txt(d, t, size, box=(S // 2, S // 2), fill=W):
    from PIL import ImageFont
    f = ImageFont.load_default(size=size)
    d.text(box, t, font=f, fill=fill, anchor="mm")

def simple(color, draw):
    def fn():
        im, d = base(color)
        draw(d, color)
        return im
    return fn

def g_music(d, c):
    d.ellipse((70, 150, 118, 190), fill=W); d.ellipse((146, 130, 194, 170), fill=W)
    d.rectangle((108, 70, 122, 170), fill=W); d.rectangle((184, 50, 198, 150), fill=W); d.polygon([(108, 70), (198, 50), (198, 82), (108, 102)], fill=W)

def g_podcast(d, c):
    d.rounded_rectangle((100, 50, 156, 140), 28, fill=W); d.arc((70, 90, 186, 190), 0, 180, fill=W, width=12)
    d.rectangle((122, 180, 134, 205), fill=W); d.rounded_rectangle((92, 200, 164, 212), 6, fill=W)

def g_files(d, c):
    d.rounded_rectangle((50, 80, 206, 190), 14, fill=W); d.rounded_rectangle((50, 64, 112, 100), 10, fill=W)
    d.rectangle((50, 100, 206, 110), fill=tint(c, 0.8))

def g_notes(d, c):
    d.rounded_rectangle((62, 56, 194, 200), 12, fill=W)
    for y in (96, 124, 152): d.rectangle((82, y, 174, y + 6), fill=tint(c, 0.8))
    d.polygon([(150, 210), (214, 100), (232, 112), (168, 222)], fill=tint(c, 0.6))

def g_runner(d, c):
    d.rounded_rectangle((70, 100, 186, 200), 36, fill=W)
    d.ellipse((94, 132, 118, 156), fill=tint(c)); d.ellipse((138, 132, 162, 156), fill=tint(c))
    d.rectangle((40, 205, 216, 222), fill=tint(c, 0.7))

def g_snake(d, c):
    d.line([(60, 190), (60, 120), (130, 120), (130, 70), (196, 70)], fill=W, width=26, joint="curve")
    d.ellipse((184, 56, 214, 86), fill=tint(c, 0.4))

def g_2048(d, c):
    d.rounded_rectangle((44, 60, 212, 196), 18, fill=tint(c, 0.8)); txt(d, "2048", 62, (128, 128))

def g_blockfall(d, c):
    for x, y in ((70, 70), (70, 110), (70, 150), (110, 150)): d.rounded_rectangle((x, y, x + 36, y + 36), 6, fill=W)
    for x, y in ((150, 110), (150, 150), (110, 110)): d.rounded_rectangle((x, y, x + 36, y + 36), 6, fill=tint(c, 0.5))

def g_pong(d, c):
    d.rounded_rectangle((52, 80, 72, 176), 8, fill=W); d.rounded_rectangle((184, 80, 204, 176), 8, fill=W); d.ellipse((112, 108, 144, 140), fill=W)

def g_mines(d, c):
    d.ellipse((78, 78, 178, 178), fill=W)
    for a in ((128, 52, 128, 204), (52, 128, 204, 128), (74, 74, 182, 182), (74, 182, 182, 74)): d.line(a, fill=W, width=12)
    d.ellipse((104, 104, 124, 124), fill=tint(c, 0.5))

def g_memory(d, c):
    for x, y in ((52, 60), (136, 60), (52, 140), (136, 140)): d.rounded_rectangle((x, y, x + 68, y + 64), 10, fill=W)
    txt(d, "?", 56, (86, 92), tint(c, 0.7)); txt(d, "?", 56, (170, 172), tint(c, 0.7))

def g_simon(d, c):
    for (x, y), col in zip(((54, 54), (134, 54), (54, 134), (134, 134)), ((230, 60, 60, 255), (60, 190, 90, 255), (240, 200, 40, 255), (60, 120, 230, 255))):
        d.rounded_rectangle((x, y, x + 68, y + 68), 14, fill=col)

def g_ttt(d, c):
    for a in ((96, 54, 96, 202), (160, 54, 160, 202), (54, 104, 202, 104), (54, 156, 202, 156)): d.line(a, fill=W, width=10)
    d.line((62, 62, 90, 92), fill=W, width=12); d.line((90, 62, 62, 92), fill=W, width=12); d.ellipse((112, 112, 148, 148), outline=W, width=10)

def g_dice(d, c):
    d.rounded_rectangle((52, 52, 204, 204), 28, fill=W)
    for x, y in ((88, 88), (168, 88), (128, 128), (88, 168), (168, 168)): d.ellipse((x - 14, y - 14, x + 14, y + 14), fill=tint(c, 0.7))

def g_calc(d, c):
    d.rounded_rectangle((60, 46, 196, 210), 16, fill=W); d.rectangle((76, 62, 180, 94), fill=tint(c, 0.8))
    for i in range(3):
        for j in range(3): d.rounded_rectangle((76 + i * 38, 110 + j * 30, 76 + i * 38 + 28, 110 + j * 30 + 22), 5, fill=tint(c, 0.7))

def g_timer(d, c):
    d.ellipse((52, 64, 204, 216), outline=W, width=14); d.rectangle((110, 40, 146, 58), fill=W)
    d.line((128, 140, 128, 96), fill=W, width=12); d.line((128, 140, 164, 150), fill=W, width=12)

def g_todo(d, c):
    for i, y in enumerate((70, 112, 154)):
        d.rounded_rectangle((60, y, 92, y + 32), 6, outline=W, width=8); d.rectangle((112, y + 10, 200, y + 22), fill=W)
    d.line((66, 126, 76, 138), fill=W, width=8); d.line((76, 138, 90, 116), fill=W, width=8)

def g_tally(d, c):
    for x in (70, 100, 130, 160): d.rounded_rectangle((x, 70, x + 10, 190), 5, fill=W)
    d.line((54, 170, 190, 90), fill=W, width=10)

def g_light(d, c):
    d.ellipse((76, 50, 180, 154), fill=(255, 235, 120, 255)); d.rounded_rectangle((100, 150, 156, 190), 8, fill=W); d.rectangle((108, 192, 148, 206), fill=W)

def g_weather(d, c):
    d.ellipse((60, 54, 130, 124), fill=(255, 220, 80, 255))
    d.ellipse((90, 110, 150, 170), fill=W); d.ellipse((130, 100, 200, 170), fill=W); d.rounded_rectangle((90, 130, 200, 180), 24, fill=W)

def g_pistats(d, c):
    for i, h in enumerate((60, 110, 80, 150)): d.rounded_rectangle((58 + i * 36, 206 - h, 84 + i * 36, 206), 6, fill=W)

def g_home(d, c):
    d.polygon([(128, 48), (216, 128), (40, 128)], fill=W); d.rectangle((66, 124, 190, 206), fill=W); d.rectangle((110, 156, 146, 206), fill=tint(c, 0.7))

def g_style(d, c):
    d.ellipse((46, 50, 210, 206), fill=W)
    for x, y, col in ((86, 96, (230, 60, 60, 255)), (128, 80, (250, 200, 40, 255)), (170, 100, (60, 170, 90, 255)), (96, 150, (60, 120, 230, 255))):
        d.ellipse((x - 16, y - 16, x + 16, y + 16), fill=col)
    d.ellipse((130, 140, 180, 190), fill=c)

def g_bt(d, c):
    d.arc((60, 70, 196, 206), 180, 360, fill=W, width=14); d.rounded_rectangle((50, 130, 80, 196), 10, fill=W); d.rounded_rectangle((176, 130, 206, 196), 10, fill=W)

def g_youtube(d, c):
    d.rounded_rectangle((40, 68, 216, 188), 34, fill=W); d.polygon([(110, 98), (110, 158), (164, 128)], fill=c)


def g_flap(d, c):
    d.ellipse((70, 90, 150, 170), fill=(247, 213, 29, 255)); d.ellipse((120, 108, 140, 128), fill=W); d.ellipse((128, 114, 136, 122), fill=(30, 30, 30, 255))
    d.polygon([(148, 126), (188, 138), (148, 150)], fill=(240, 120, 40, 255)); d.rounded_rectangle((176, 170, 216, 230), 4, fill=(76, 175, 80, 255)); d.rounded_rectangle((176, 20, 216, 90), 4, fill=(76, 175, 80, 255))

def g_breakout(d, c):
    for r, col in enumerate(((229, 57, 53, 255), (251, 140, 0, 255), (253, 216, 53, 255))):
        for k in range(4): d.rounded_rectangle((44 + k * 42, 54 + r * 26, 44 + k * 42 + 38, 54 + r * 26 + 20), 4, fill=col)
    d.ellipse((120, 150, 138, 168), fill=W); d.rounded_rectangle((88, 196, 168, 210), 7, fill=W)

def g_whack(d, c):
    d.ellipse((50, 150, 206, 214), fill=(60, 40, 30, 255)); d.ellipse((84, 70, 172, 170), fill=(46, 204, 113, 255))
    d.ellipse((106, 104, 122, 120), fill=W); d.ellipse((138, 104, 154, 120), fill=W); d.arc((108, 120, 148, 150), 20, 160, fill=W, width=6)

def g_lightsout(d, c):
    for i in range(3):
        for j in range(3):
            on = (i + j) % 2 == 0
            d.rounded_rectangle((52 + i * 52, 52 + j * 52, 52 + i * 52 + 44, 52 + j * 52 + 44), 8, fill=(255, 213, 79, 255) if on else (70, 90, 105, 255))

SPECS = {
    "com.thmi.music": ((142, 36, 170, 255), g_music), "com.thmi.podcasts": ((171, 71, 188, 255), g_podcast),
    "com.thmi.files": ((84, 110, 122, 255), g_files), "com.thmi.notes": ((92, 107, 192, 255), g_notes),
    "com.thmi.runner": ((46, 160, 90, 255), g_runner), "com.thmi.snake": ((60, 150, 60, 255), g_snake),
    "com.thmi.g2048": ((237, 160, 60, 255), g_2048), "com.thmi.blockfall": ((50, 90, 160, 255), g_blockfall),
    "com.thmi.pong": ((40, 40, 60, 255), g_pong), "com.thmi.mines": ((120, 120, 130, 255), g_mines),
    "com.thmi.memory": ((0, 150, 170, 255), g_memory), "com.thmi.simon": ((70, 70, 90, 255), g_simon),
    "com.thmi.tictactoe": ((200, 80, 90, 255), g_ttt), "com.thmi.dice": ((200, 60, 60, 255), g_dice),
    "com.thmi.calc": ((70, 80, 100, 255), g_calc), "com.thmi.timer": ((230, 120, 40, 255), g_timer),
    "com.thmi.todo": ((60, 150, 120, 255), g_todo), "com.thmi.tally": ((150, 100, 60, 255), g_tally),
    "com.thmi.light": ((40, 50, 80, 255), g_light), "com.thmi.weather": ((60, 140, 220, 255), g_weather),
    "com.thmi.pistats": ((190, 40, 90, 255), g_pistats), "com.thmi.smarthome": ((30, 130, 150, 255), g_home),
    "com.micropythonos.launcher": ((70, 90, 160, 255), g_home), "com.thmi.style": ((200, 70, 150, 255), g_style),
    "com.thmi.youtube": ((220, 40, 40, 255), g_youtube), "com.thmi.bluetooth": ((40, 90, 200, 255), g_bt),
    "com.thmi.flap": ((90, 170, 190, 255), g_flap), "com.thmi.breakout": ((30, 40, 70, 255), g_breakout),
    "com.thmi.whack": ((120, 90, 60, 255), g_whack), "com.thmi.lightsout": ((50, 60, 80, 255), g_lightsout),
}
for name, (color, draw) in SPECS.items():
    if os.path.isdir(os.path.join(ROOT, "apps", name)):
        simple(color, draw)().resize((64, 64), Image.LANCZOS).save(os.path.join(ROOT, "apps", name, "icon_64x64.png"))

for name, fn in (("com.thmi.robot", robot), ("com.thmi.hub", hub), ("com.thmi.store", store)):
    fn().resize((64, 64), Image.LANCZOS).save(os.path.join(ROOT, "apps", name, "icon_64x64.png"))
print("icons ok")
