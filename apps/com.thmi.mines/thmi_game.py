"""Helpers for small games/tools: screen setup, a ticking Activity, buttons, swipe detection (240x320 portrait)."""
import random

import lvgl as lv

from mpos import Activity, InputManager


def new_screen():
    s = lv.obj()
    s.remove_flag(lv.obj.FLAG.SCROLLABLE)
    s.set_style_pad_all(0, lv.PART.MAIN)
    return s


def box(parent, x, y, w, h, color, radius=0):
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


def label(parent, text="", size=14, x=None, y=None, align=None, color=None, width=None):
    l = lv.label(parent)
    l.set_text(text)
    l.set_style_text_font({12: lv.font_montserrat_12, 14: lv.font_montserrat_14, 16: lv.font_montserrat_16,
                           20: lv.font_montserrat_20, 24: lv.font_montserrat_24, 28: lv.font_montserrat_28}.get(size, lv.font_montserrat_14), lv.PART.MAIN)
    if color is not None:
        l.set_style_text_color(lv.color_hex(color), lv.PART.MAIN)
    if width:
        l.set_width(width)
        l.set_long_mode(lv.label.LONG_MODE.WRAP)
    if align is not None:
        l.align(align, x or 0, y or 0)
    elif x is not None:
        l.set_pos(x, y or 0)
    return l


def button(parent, text, x, y, w, h, cb, size=16, color=None, pressed=None):
    """cb(event) on click; pressed(True/False) if given, for hold-to-move controls."""
    b = lv.button(parent)
    b.set_size(w, h)
    b.set_pos(x, y)
    if color is not None:
        b.set_style_bg_color(lv.color_hex(color), lv.PART.MAIN)
    if cb:
        b.add_event_cb(cb, lv.EVENT.CLICKED, None)
    if pressed:
        b.add_event_cb(lambda e: pressed(True), lv.EVENT.PRESSED, None)
        b.add_event_cb(lambda e: pressed(False), lv.EVENT.RELEASED, None)
        b.add_event_cb(lambda e: pressed(False), lv.EVENT.PRESS_LOST, None)
    l = lv.label(b)
    l.set_text(text)
    l.set_style_text_font({12: lv.font_montserrat_12, 14: lv.font_montserrat_14, 16: lv.font_montserrat_16,
                           20: lv.font_montserrat_20, 24: lv.font_montserrat_24}.get(size, lv.font_montserrat_16), lv.PART.MAIN)
    l.center()
    return b


def on_swipe(obj, cb, min_px=18):
    """cb('l'|'r'|'u'|'d') when the finger is lifted after moving far enough over obj."""
    st = {"p": None}
    obj.add_flag(lv.obj.FLAG.CLICKABLE)

    def ev(e):
        c = e.get_code()
        if c == lv.EVENT.PRESSED:
            st["p"] = InputManager.pointer_xy()
        elif c == lv.EVENT.RELEASED and st["p"]:
            x0, y0 = st["p"]
            x1, y1 = InputManager.pointer_xy()
            st["p"] = None
            dx, dy = x1 - x0, y1 - y0
            if max(abs(dx), abs(dy)) >= min_px:
                cb(("r" if dx > 0 else "l") if abs(dx) > abs(dy) else ("d" if dy > 0 else "u"))
    obj.add_event_cb(ev, lv.EVENT.ALL, None)


class Ticker(Activity):
    """Activity with a timer: set TICK (ms) and implement tick(). The timer only runs while the app is on screen."""
    TICK = 100

    def onResume(self, screen):
        super().onResume(screen)
        if getattr(self, "_timer", None) is None:
            self._timer = lv.timer_create(lambda t: self.tick(), self.TICK, None)

    def onPause(self, screen):
        t = getattr(self, "_timer", None)
        if t is not None:
            try:
                t.delete()
            except Exception:
                pass
            self._timer = None
        super().onPause(screen)

    def tick(self):
        pass


def shuffle(lst):
    """MicroPython's random has no shuffle()."""
    for i in range(len(lst) - 1, 0, -1):
        j = random.randint(0, i)
        lst[i], lst[j] = lst[j], lst[i]


def sample(seq, k):
    pool = list(seq)
    shuffle(pool)
    return pool[:k]
