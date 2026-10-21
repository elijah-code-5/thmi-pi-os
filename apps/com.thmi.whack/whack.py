import random

import lvgl as lv

from mpos import SharedPreferences

import thmi_game as g

CS = 72
SECS = 30


class Whack(g.Ticker):
    TICK = 100

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.whack")
        s = g.new_screen()
        self.info = g.label(s, "", 16, 8, 6)
        self.holes = []
        for i in range(9):
            o = g.box(s, 6 + (i % 3) * 78, 44 + (i // 3) * 78, CS, CS, 0x5D4037, 36)
            blob = g.box(o, 14, 14, 44, 44, 0x2ECC71, 22)
            blob.add_flag(lv.obj.FLAG.HIDDEN)
            o.add_flag(lv.obj.FLAG.CLICKABLE)
            o.add_event_cb(lambda e, i=i: self.hit(i), lv.EVENT.PRESSED, None)
            self.holes.append([o, blob, 0])
        self.msg = g.label(s, "", 20, align=lv.ALIGN.BOTTOM_MID, y=-14, width=230)
        self.msg.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.PART.MAIN)
        self.setContentView(s)
        self.state = "idle"
        self.msg.set_text("Tap a blob to start")
        self.info.set_text("Whack-a-Blob")

    def start(self):
        self.score, self.left, self.state = 0, SECS * 10, "play"
        for h in self.holes:
            h[1].add_flag(lv.obj.FLAG.HIDDEN)
            h[2] = 0
        self.msg.set_text("")

    def hit(self, i):
        if self.state != "play":
            if self.state in ("idle", "over"):
                self.start()
            return
        h = self.holes[i]
        if h[2] > 0:
            h[2] = 0
            h[1].add_flag(lv.obj.FLAG.HIDDEN)
            self.score += 1

    def tick(self):
        if self.state != "play":
            return
        self.left -= 1
        for h in self.holes:
            if h[2] > 0:
                h[2] -= 1
                if h[2] == 0:
                    h[1].add_flag(lv.obj.FLAG.HIDDEN)
        if random.randint(0, 3) == 0:
            h = random.choice(self.holes)
            if h[2] == 0:
                h[2] = random.randint(6, 12)
                h[1].remove_flag(lv.obj.FLAG.HIDDEN)
        self.info.set_text("Score %d    Time %d" % (self.score, self.left // 10))
        if self.left <= 0:
            self.state = "over"
            best = self.prefs.get_int("best", 0)
            if self.score > best:
                self.prefs.edit().put_int("best", self.score).commit()
                best = self.score
            for h in self.holes:
                h[1].add_flag(lv.obj.FLAG.HIDDEN)
            self.msg.set_text("Score %d   Best %d\nTap to play again" % (self.score, best))
