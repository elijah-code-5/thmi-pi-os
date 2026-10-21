import lvgl as lv

from mpos import Activity

import thmi_ui
from calc_logic import Calc as Engine


class Calc(Activity):

    def onCreate(self):
        self.e = Engine()
        sc = thmi_ui.screen()
        self.disp = thmi_ui.text(sc, "0", 8, 14, lv.font_montserrat_24, None, 224)
        self.disp.set_style_text_align(lv.TEXT_ALIGN.RIGHT, lv.PART.MAIN)
        rows = (("C", "+/-", "%", "/"), ("7", "8", "9", "*"), ("4", "5", "6", "-"), ("1", "2", "3", "+"), ("<", "0", ".", "="))
        for r, row in enumerate(rows):
            for c, k in enumerate(row):
                b = thmi_ui.btn(sc, {"*": "x", "/": ":"}.get(k, k), 4 + c * 59, 56 + r * 52, 55, 48, lambda ev, k=k: self.key(k), lv.font_montserrat_20)
                if k in "+-*/=":
                    b.set_style_bg_color(lv.color_hex(0xF39C12), lv.PART.MAIN)
        self.setContentView(sc)

    def key(self, k):
        e = self.e
        if k.isdigit() or k == ".":
            e.digit(k)
        elif k in "+-*/":
            e.operator(k)
        elif k == "=":
            e.equals()
        elif k == "C":
            e.clear()
        elif k == "+/-":
            e.negate()
        elif k == "%":
            e.percent()
        elif k == "<":
            e.backspace()
        self.disp.set_text(e.cur)
