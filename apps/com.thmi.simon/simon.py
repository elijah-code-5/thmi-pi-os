import random

import lvgl as lv

from mpos import Activity, SharedPreferences

import thmi_ui

COLS = ((0xC0392B, 0xFF6B5B), (0x27AE60, 0x6BFF9B), (0x2980B9, 0x6BB8FF), (0xB7950B, 0xFFE34D))


class Simon(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.simon")
        sc = thmi_ui.screen()
        self.info = thmi_ui.text(sc, "", 6, 6, lv.font_montserrat_20, None, 228)
        self.pads = []
        for i in range(4):
            r, c = divmod(i, 2)
            b = lv.button(sc)
            b.set_size(112, 112)
            b.set_pos(6 + c * 116, 44 + r * 116)
            b.set_style_bg_color(lv.color_hex(COLS[i][0]), lv.PART.MAIN)
            b.add_event_cb(lambda e, i=i: self.press(i), lv.EVENT.CLICKED, None)
            self.pads.append(b)
        thmi_ui.btn(sc, "Start", 70, 282, 100, 30, lambda e: self.start())
        self.timer = None
        self.seq, self.pos, self.state = [], 0, "idle"
        self.setContentView(sc)
        self.info.set_text("Tap Start")

    def start(self):
        self.seq = [random.randrange(4)]
        self.play_seq()

    def play_seq(self):
        self.state = "show"
        self.step = 0
        self.info.set_text("Watch... (%d)" % len(self.seq))
        self._cancel()
        self.timer = lv.timer_create(lambda t: self._show(), 600, None)

    def _cancel(self):
        if self.timer is not None:
            try:
                self.timer.delete()
            except Exception:
                pass
            self.timer = None

    def _show(self):
        # even ticks light a pad, odd ticks turn it off again
        if self.step % 2 == 0 and self.step // 2 < len(self.seq):
            self.light(self.seq[self.step // 2], True)
        else:
            for i in range(4):
                self.light(i, False)
            if self.step // 2 >= len(self.seq):
                self._cancel()
                self.state, self.pos = "input", 0
                self.info.set_text("Your turn")
                return
        self.step += 1

    def light(self, i, on):
        self.pads[i].set_style_bg_color(lv.color_hex(COLS[i][1] if on else COLS[i][0]), lv.PART.MAIN)

    def press(self, i):
        if self.state != "input":
            return
        if i != self.seq[self.pos]:
            best = self.prefs.get_int("best", 0)
            score = len(self.seq) - 1
            if score > best:
                self.prefs.edit().put_int("best", score).commit()
                best = score
            self.state = "idle"
            self.info.set_text("Wrong! Score %d  Best %d" % (score, best))
            return
        self.pos += 1
        if self.pos == len(self.seq):
            self.seq.append(random.randrange(4))
            self.play_seq()

    def onPause(self, screen):
        self._cancel()
        super().onPause(screen)
