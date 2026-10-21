import random

import lvgl as lv

from mpos import SharedPreferences

import thmi_game as g

W, H, GAP, PIPE_W, BX, BS = 240, 280, 78, 34, 60, 16


class Flap(g.Ticker):
    TICK = 33

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.flap")
        s = g.new_screen()
        self.info = g.label(s, "", 20, 8, 6)
        self.field = g.box(s, 0, 36, W, H, 0x70C5CE)
        self.field.add_flag(lv.obj.FLAG.CLICKABLE)
        self.field.add_event_cb(lambda e: self.flap(), lv.EVENT.PRESSED, None)
        g.box(self.field, 0, H - 20, W, 20, 0xDED895)
        self.bird = g.box(self.field, BX, 100, BS, BS, 0xF7D51D, 6)
        self.pipes = []
        for i in range(3):
            self.pipes.append([g.box(self.field, 0, 0, PIPE_W, 10, 0x4CAF50), g.box(self.field, 0, 0, PIPE_W, 10, 0x4CAF50), 0.0, 0, False])
        self.msg = g.label(self.field, "Tap to start", 24, align=lv.ALIGN.CENTER, y=-40, color=0xFFFFFF)
        self.setContentView(s)
        self.reset()

    def reset(self):
        self.y, self.vy, self.score, self.state = 100.0, 0.0, 0, "ready"
        for i, p in enumerate(self.pipes):
            p[2], p[3], p[4] = W + 60 + i * 130.0, random.randint(40, H - 20 - GAP - 30), False
        self.msg.set_text("Tap to start")
        self.draw()

    def flap(self):
        if self.state == "ready":
            self.state = "play"
            self.msg.set_text("")
        elif self.state == "dead":
            self.reset()
            return
        self.vy = -5.6

    def tick(self):
        if self.state != "play":
            return
        self.vy = min(self.vy + 0.42, 8)
        self.y += self.vy
        for p in self.pipes:
            p[2] -= 2.4
            if p[2] < -PIPE_W:
                p[2] = max(q[2] for q in self.pipes) + 130
                p[3] = random.randint(40, H - 20 - GAP - 30)
                p[4] = False
            if not p[4] and p[2] + PIPE_W < BX:
                p[4] = True
                self.score += 1
            if BX + BS > p[2] and BX < p[2] + PIPE_W and (self.y < p[3] or self.y + BS > p[3] + GAP):
                self.die()
        if self.y < 0 or self.y + BS > H - 20:
            self.die()
        self.draw()

    def die(self):
        self.state = "dead"
        best = self.prefs.get_int("best", 0)
        if self.score > best:
            self.prefs.edit().put_int("best", self.score).commit()
            best = self.score
        self.msg.set_text("Game over\nBest %d\nTap to retry" % best)
        self.msg.move_foreground()

    def draw(self):
        self.bird.set_y(int(self.y))
        for top, bot, x, gy, _ in self.pipes:
            top.set_pos(int(x), 0)
            top.set_height(max(1, gy))
            bot.set_pos(int(x), gy + GAP)
            bot.set_height(max(1, H - 20 - gy - GAP))
        self.info.set_text("Score %d" % self.score)
