import random

import lvgl as lv

from mpos import InputManager

import thmi_game as g

W, H, PW, PH, BS = 240, 280, 52, 8, 8
COLS, ROWS, BW, BH = 6, 5, 38, 14
COLORS = (0xE53935, 0xFB8C00, 0xFDD835, 0x43A047, 0x1E88E5)


class Breakout(g.Ticker):
    TICK = 33

    def onCreate(self):
        s = g.new_screen()
        self.info = g.label(s, "", 16, 8, 6)
        self.field = g.box(s, 0, 36, W, H, 0x101820)
        self.field.add_flag(lv.obj.FLAG.CLICKABLE)
        for ev in (lv.EVENT.PRESSING, lv.EVENT.PRESSED):
            self.field.add_event_cb(self.drag, ev, None)
        self.bricks = []
        for r in range(ROWS):
            for c in range(COLS):
                self.bricks.append([g.box(self.field, 4 + c * (BW + 1), 30 + r * (BH + 2), BW, BH, COLORS[r], 3), True])
        self.pad = g.box(self.field, 94, H - 24, PW, PH, 0xFFFFFF, 4)
        self.ball = g.box(self.field, 0, 0, BS, BS, 0xFFFFFF, 4)
        self.msg = g.label(self.field, "", 20, align=lv.ALIGN.CENTER, y=40, color=0xFFFFFF)
        self.setContentView(s)
        self.new_game()

    def new_game(self):
        self.lives, self.score = 3, 0
        for b in self.bricks:
            b[1] = True
            b[0].remove_flag(lv.obj.FLAG.HIDDEN)
        self.serve()

    def serve(self):
        self.px = 94.0
        self.bx, self.by = W / 2, H - 40.0
        self.vx, self.vy = random.choice((-2.4, 2.4)), -3.6
        self.state = "play"
        self.msg.set_text("")
        self.hud()

    def hud(self):
        self.info.set_text("Score %d   Lives %d" % (self.score, self.lives))

    def drag(self, e):
        if self.state != "play":
            if e.get_code() == lv.EVENT.PRESSED:
                self.new_game()
            return
        x, _ = InputManager.pointer_xy()
        self.px = max(0, min(W - PW, x - PW / 2))

    def tick(self):
        if self.state != "play":
            return
        self.bx += self.vx
        self.by += self.vy
        if self.bx < 0 or self.bx > W - BS:
            self.vx = -self.vx
            self.bx = max(0, min(W - BS, self.bx))
        if self.by < 0:
            self.vy = abs(self.vy)
        if self.vy > 0 and H - 24 <= self.by + BS <= H - 14 and self.px - BS <= self.bx <= self.px + PW:
            self.vy = -min(7, abs(self.vy) * 1.03)
            self.vx += ((self.bx + BS / 2) - (self.px + PW / 2)) / 10
            self.vx = max(-4.5, min(4.5, self.vx))
        for b in self.bricks:
            if b[1]:
                o = b[0]
                x, y = o.get_x(), o.get_y()
                if x - BS < self.bx < x + BW and y - BS < self.by < y + BH:
                    b[1] = False
                    o.add_flag(lv.obj.FLAG.HIDDEN)
                    self.vy = -self.vy
                    self.score += 10
                    self.hud()
                    break
        if not any(b[1] for b in self.bricks):
            self.state = "over"
            self.msg.set_text("You win!\nTap to play again")
        elif self.by > H:
            self.lives -= 1
            if self.lives <= 0:
                self.state = "over"
                self.msg.set_text("Game over\nTap to play again")
                self.hud()
            else:
                self.serve()
        self.pad.set_x(int(self.px))
        self.ball.set_pos(int(self.bx), int(self.by))
