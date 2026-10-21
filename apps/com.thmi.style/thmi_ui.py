"""Small LVGL helpers so every T-HMI app looks the same (240x320 portrait)."""
import lvgl as lv

from mpos import TaskManager

import thmi_net


def header(screen, title, right_symbol=None, right_cb=None):
    t = lv.label(screen)
    t.set_text(title)
    t.set_style_text_font(lv.font_montserrat_20, lv.PART.MAIN)
    t.align(lv.ALIGN.TOP_LEFT, 4, 4)
    if right_symbol:
        b = lv.button(screen)
        b.set_size(44, 34)
        b.align(lv.ALIGN.TOP_RIGHT, -2, 0)
        b.add_event_cb(right_cb, lv.EVENT.CLICKED, None)
        l = lv.label(b)
        l.set_text(right_symbol)
        l.center()
    return t


def status(screen, y=34):
    s = lv.label(screen)
    s.set_width(lv.pct(96))
    s.set_long_mode(lv.label.LONG_MODE.DOTS)
    s.set_style_text_font(lv.font_montserrat_14, lv.PART.MAIN)
    s.align(lv.ALIGN.TOP_LEFT, 4, y)
    return s


def list_box(screen, top=56, bottom=0):
    box = lv.obj(screen)
    box.set_size(lv.pct(100), 320 - top - bottom)
    box.align(lv.ALIGN.TOP_MID, 0, top)
    box.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    box.set_style_pad_all(2, lv.PART.MAIN)
    box.set_style_pad_row(3, lv.PART.MAIN)
    return box


def row(box, text, cb, h=40):
    b = lv.button(box)
    b.set_size(lv.pct(100), h)
    b.add_event_cb(cb, lv.EVENT.CLICKED, None)
    l = lv.label(b)
    l.set_text(text)
    l.set_long_mode(lv.label.LONG_MODE.DOTS)
    l.set_width(lv.pct(94))
    l.set_style_text_font(lv.font_montserrat_14, lv.PART.MAIN)
    l.align(lv.ALIGN.LEFT_MID, 0, 0)
    return b


def controls(screen, host_getter, on_status=None):
    """Bottom bar that controls whatever the Pi is playing: prev, seek back, pause, seek fwd, next, vol-, vol+, stop."""
    items = ((lv.SYMBOL.PREV, "prev"), (lv.SYMBOL.PLAY + lv.SYMBOL.PAUSE, "pause"), (lv.SYMBOL.NEXT, "next"),
             (lv.SYMBOL.VOLUME_MID, "vol-"), (lv.SYMBOL.VOLUME_MAX, "vol+"), (lv.SYMBOL.STOP, "stop"))
    w = 240 // len(items)
    for i, (txt, cmd) in enumerate(items):
        b = lv.button(screen)
        b.set_size(w - 2, 40)
        b.align(lv.ALIGN.BOTTOM_LEFT, i * w + 1, -1)
        b.add_event_cb(lambda e, c=cmd: TaskManager.create_task(_ctl(host_getter(), c, on_status)), lv.EVENT.CLICKED, None)
        l = lv.label(b)
        l.set_text(txt)
        l.set_style_text_font(lv.font_montserrat_14, lv.PART.MAIN)
        l.center()


async def _ctl(host, cmd, on_status):
    if not host:
        return
    try:
        if cmd in ("vol-", "vol+"):
            await thmi_net.get(host, "/api/volume?d=%s" % ("-" if cmd == "vol-" else "+"), timeout=3)
        else:
            await thmi_net.get(host, "/api/media/ctl?c=%s" % cmd, timeout=3)
    except Exception as e:
        if on_status:
            on_status("Nothing playing" if "409" in str(e) else "Can't reach the Pi")


def box(parent, x, y, w, h, color, radius=0):
    """A plain colored rectangle (no border, not clickable)."""
    o = lv.obj(parent)
    o.set_size(w, h)
    o.set_pos(x, y)
    o.set_style_bg_color(lv.color_hex(color), lv.PART.MAIN)
    o.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
    o.set_style_border_width(0, lv.PART.MAIN)
    o.set_style_radius(radius, lv.PART.MAIN)
    o.set_style_pad_all(0, lv.PART.MAIN)
    o.remove_flag(lv.obj.FLAG.SCROLLABLE)
    o.remove_flag(lv.obj.FLAG.CLICKABLE)
    return o


def btn(parent, text, x, y, w, h, cb, font=None):
    """A button at an exact position. cb gets the event."""
    b = lv.button(parent)
    b.set_size(w, h)
    b.set_pos(x, y)
    b.add_event_cb(cb, lv.EVENT.CLICKED, None)
    l = lv.label(b)
    l.set_text(text)
    if font:
        l.set_style_text_font(font, lv.PART.MAIN)
    l.center()
    return b


def hold_btn(parent, text, x, y, w, h, on_change, font=None):
    """A button that reports True while pressed and False when let go: on_change(bool)."""
    b = lv.button(parent)
    b.set_size(w, h)
    b.set_pos(x, y)
    for ev, v in ((lv.EVENT.PRESSED, True), (lv.EVENT.RELEASED, False), (lv.EVENT.PRESS_LOST, False)):
        b.add_event_cb(lambda e, v=v: on_change(v), ev, None)
    l = lv.label(b)
    l.set_text(text)
    if font:
        l.set_style_text_font(font, lv.PART.MAIN)
    l.center()
    return b


def text(parent, s, x, y, font=None, color=None, w=None, center=False):
    l = lv.label(parent)
    l.set_text(s)
    if font:
        l.set_style_text_font(font, lv.PART.MAIN)
    if color is not None:
        l.set_style_text_color(lv.color_hex(color), lv.PART.MAIN)
    if w:
        l.set_width(w)
    if center:
        l.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.PART.MAIN)
    l.set_pos(x, y)
    return l


def screen():
    s = lv.obj()
    s.remove_flag(lv.obj.FLAG.SCROLLABLE)
    s.set_style_pad_all(0, lv.PART.MAIN)
    return s
