import random

import lvgl as lv

from mpos import Activity

import thmi_ui


class Dice(Activity):

    def onCreate(self):
        sc = thmi_ui.screen()
        self.big = thmi_ui.text(sc, "?", 4, 60, lv.font_montserrat_24, None, 232, True)
        self.sub = thmi_ui.text(sc, "Tap a button", 4, 120, lv.font_montserrat_20, None, 232, True)
        for i, (name, fn) in enumerate((("d6", lambda: self.roll(6)), ("d20", lambda: self.roll(20)), ("Coin", self.coin), ("1-100", lambda: self.roll(100)))):
            thmi_ui.btn(sc, name, 10 + (i % 2) * 118, 190 + (i // 2) * 60, 108, 52, lambda e, fn=fn: fn(), lv.font_montserrat_20)
        self.setContentView(sc)

    def roll(self, n):
        self.big.set_text(str(random.randint(1, n)))
        self.sub.set_text("1 to %d" % n)

    def coin(self):
        self.big.set_text(random.choice(("Heads", "Tails")))
        self.sub.set_text("Coin flip")
