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

for name, fn in (("com.thmi.robot", robot), ("com.thmi.hub", hub), ("com.thmi.store", store)):
    fn().resize((64, 64), Image.LANCZOS).save(os.path.join(ROOT, "apps", name, "icon_64x64.png"))
print("icons ok")
