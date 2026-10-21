import random

import lvgl as lv

from mpos import Activity, SharedPreferences

import thmi_game
import thmi_ui

SYMS = ("A", "B", "C", "D", "E", "F", "G", "H")
COLS = (0xE74C3C, 0x3498DB, 0x2ECC71, 0xF1C40F, 0x9B59B6, 0xE67E22, 0x1ABC9C, 0xEC4899)


class Memory(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.memory")
        sc = thmi_ui.screen()
        self.info = thmi_ui.text(sc, "", 6, 6, lv.font_montserrat_20)
        self.cards = []
        for i in range(16):
            r, c = divmod(i, 4)
            b = lv.button(sc)
            b.set_size(54, 62)
            b.set_pos(8 + c * 58, 40 + r * 66)
            b.add_event_cb(lambda e, i=i: self.flip(i), lv.EVENT.CLICKED, None)
            l = lv.label(b)
            l.set_style_text_font(lv.font_montserrat_24, lv.PART.MAIN)
            l.center()
            self.cards.append((b, l))
        thmi_ui.btn(sc, "New game", 70, 296, 100, 22, lambda e: self.new_game())
        self.setContentView(sc)
        self.timer = None
        self.new_game()

    def new_game(self):
        vals = list(range(8)) * 2
        thmi_game.shuffle(vals)
        self.vals = vals
        self.up = [False] * 16
        self.done = [False] * 16
        self.first = None
        self.lock = False
        self.moves = 0
        self.refresh()

    def flip(self, i):
        if self.lock or self.up[i] or self.done[i]:
            return
        self.up[i] = True
        if self.first is None:
            self.first = i
        else:
            self.moves += 1
            a, b = self.first, i
            self.first = None
            if self.vals[a] == self.vals[b]:
                self.done[a] = self.done[b] = True
                if all(self.done):
                    best = self.prefs.get_int("best", 999)
                    if self.moves < best:
                        self.prefs.edit().put_int("best", self.moves).commit()
            else:
                self.lock = True
                self.timer = lv.timer_create(lambda t, a=a, b=b: self._hide(a, b), 700, None)
                self.timer.set_repeat_count(1)
        self.refresh()

    def _hide(self, a, b):
        self.up[a] = self.up[b] = False
        self.lock = False
        self.refresh()

    def refresh(self):
        best = self.prefs.get_int("best", 0)
        self.info.set_text("Moves %d%s" % (self.moves, ("   Best %d" % best) if best else ""))
        if all(self.done):
            self.info.set_text("Done in %d moves!" % self.moves)
        for i, (b, l) in enumerate(self.cards):
            if self.up[i] or self.done[i]:
                b.set_style_bg_color(lv.color_hex(COLS[self.vals[i]]), lv.PART.MAIN)
                l.set_text(SYMS[self.vals[i]])
            else:
                b.set_style_bg_color(lv.color_hex(0x445566), lv.PART.MAIN)
                l.set_text("?")
