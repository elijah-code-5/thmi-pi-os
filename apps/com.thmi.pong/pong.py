import random

import lvgl as lv

from mpos import Activity, InputManager

import thmi_ui

W, H = 240, 280
PW, PH, BS = 50, 8, 8


class Pong(Activity):

    def onCreate(self):
        sc = thmi_ui.screen()
        self.info = thmi_ui.text(sc, "", 6, 4, lv.font_montserrat_20, None, 228)
        self.field = thmi_ui.box(sc, 0, 36, W, H, 0x10202A)
        self.field.add_flag(lv.obj.FLAG.CLICKABLE)
        self.field.add_event_cb(self._drag, lv.EVENT.PRESSING, None)
        self.field.add_event_cb(self._drag, lv.EVENT.PRESSED, None)
        thmi_ui.box(self.field, 0, H // 2 - 1, W, 2, 0x35505F)
        self.me = thmi_ui.box(self.field, 95, H - 20, PW, PH, 0x2ECC71, 4)
        self.ai = thmi_ui.box(self.field, 95, 12, PW, PH, 0xE74C3C, 4)
        self.ball = thmi_ui.box(self.field, 0, 0, BS, BS, 0xFFFFFF, 4)
        self.msg = thmi_ui.text(self.field, "", 10, 110, lv.font_montserrat_20, 0xFFFFFF, 220, True)
        self.timer = None
        self.setContentView(sc)
        self.new_match()

    def new_match(self):
        self.s_me = self.s_ai = 0
        self.serve(1)
        self.over = False
        self.msg.set_text("")

    def serve(self, d):
        self.bx, self.by = W / 2, H / 2
        self.vx = random.choice((-2.0, 2.0))
        self.vy = 3.0 * d
        self.mx, self.ax = 95.0, 95.0
        self.info.set_text("You %d : %d T-HMI" % (self.s_me, self.s_ai))

    def onResume(self, screen):
        super().onResume(screen)
        if self.timer is None:
            self.timer = lv.timer_create(lambda t: self.tick(), 33, None)

    def onPause(self, screen):
        if self.timer is not None:
            self.timer.delete()
            self.timer = None
        super().onPause(screen)

    def _drag(self, e):
        x, _ = InputManager.pointer_xy()
        if self.over:
            if e.get_code() == lv.EVENT.PRESSED:
                self.new_match()
            return
        self.mx = max(0, min(W - PW, x - PW / 2))

    def tick(self):
        if self.over:
            return
        self.bx += self.vx
        self.by += self.vy
        if self.bx < 0 or self.bx > W - BS:
            self.vx = -self.vx
            self.bx = max(0, min(W - BS, self.bx))
        # AI paddle follows the ball, but a little slower than the ball moves
        target = self.bx - PW / 2
        self.ax += max(-2.2, min(2.2, target - self.ax))
        self.ax = max(0, min(W - PW, self.ax))
        # paddles
        if self.vy > 0 and H - 20 <= self.by + BS <= H - 12 and self.mx - BS <= self.bx <= self.mx + PW:
            self.vy = -min(6.5, abs(self.vy) * 1.06)
            self.vx += ((self.bx + BS / 2) - (self.mx + PW / 2)) / 12
        if self.vy < 0 and 12 <= self.by <= 20 and self.ax - BS <= self.bx <= self.ax + PW:
            self.vy = min(6.5, abs(self.vy) * 1.06)
            self.vx += ((self.bx + BS / 2) - (self.ax + PW / 2)) / 14
        if self.by < -10:
            self.s_me += 1
            self.point(1)
        elif self.by > H + 10:
            self.s_ai += 1
            self.point(-1)
        self.me.set_x(int(self.mx))
        self.ai.set_x(int(self.ax))
        self.ball.set_pos(int(self.bx), int(self.by))

    def point(self, d):
        if self.s_me >= 5 or self.s_ai >= 5:
            self.over = True
            self.msg.set_text("You win!\nTap to play again" if self.s_me >= 5 else "T-HMI wins\nTap to play again")
            self.msg.move_foreground()
            self.info.set_text("You %d : %d T-HMI" % (self.s_me, self.s_ai))
        else:
            self.serve(d)
