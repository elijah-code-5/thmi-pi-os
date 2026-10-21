import random

import lvgl as lv

from mpos import Activity, SharedPreferences

import block_logic as L
import thmi_ui

CELL = 15
COLORS = (0x16212B, 0x00BCD4, 0xF1C40F, 0x9B59B6, 0x2ECC71, 0xE74C3C, 0x3498DB, 0xE67E22)


class Blockfall(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.blockfall")
        sc = thmi_ui.screen()
        self.info = thmi_ui.text(sc, "", 160, 10, lv.font_montserrat_14, None, 78)
        self.field = thmi_ui.box(sc, 4, 4, L.COLS * CELL + 2, L.ROWS * CELL + 2, 0x0B1218)
        self.objs = []
        for r in range(L.ROWS):
            for c in range(L.COLS):
                self.objs.append(thmi_ui.box(self.field, 1 + c * CELL, 1 + r * CELL, CELL - 1, CELL - 1, COLORS[0]))
        self.shown = [0] * (L.ROWS * L.COLS)
        self.msg = thmi_ui.text(sc, "", 4, 100, lv.font_montserrat_20, 0xFFFFFF, 152, True)
        y = 252
        thmi_ui.btn(sc, lv.SYMBOL.LEFT, 4, y, 56, 30, lambda e: self.move(-1))
        thmi_ui.btn(sc, lv.SYMBOL.RIGHT, 64, y, 56, 30, lambda e: self.move(1))
        thmi_ui.btn(sc, lv.SYMBOL.REFRESH, 124, y, 56, 30, lambda e: self.rot())
        thmi_ui.btn(sc, lv.SYMBOL.DOWN, 184, y, 52, 30, lambda e: self.drop())
        thmi_ui.btn(sc, "New game", 70, 286, 100, 28, lambda e: self.new_game())
        self.timer = None
        self.setContentView(sc)
        self.new_game()

    def new_game(self):
        self.board = [[0] * L.COLS for _ in range(L.ROWS)]
        self.score = self.lines = 0
        self.over = False
        self.msg.set_text("")
        self.next = random.randrange(7)
        self.spawn()

    def spawn(self):
        self.kind = self.next
        self.next = random.randrange(7)
        self.cells = list(L.SHAPES[L.NAMES[self.kind]])
        self.ox, self.oy = 3, -1
        if not L.fits(self.board, self.cells, self.ox, self.oy):
            self.over = True
            best = self.prefs.get_int("best", 0)
            if self.score > best:
                self.prefs.edit().put_int("best", self.score).commit()
            self.msg.set_text("Game over")
            self.msg.move_foreground()
        self.draw()

    def onResume(self, screen):
        super().onResume(screen)
        if self.timer is None:
            self.timer = lv.timer_create(lambda t: self.tick(), 500, None)

    def onPause(self, screen):
        if self.timer is not None:
            self.timer.delete()
            self.timer = None
        super().onPause(screen)

    def tick(self):
        if self.over:
            return
        if L.fits(self.board, self.cells, self.ox, self.oy + 1):
            self.oy += 1
        else:
            self.land()
        self.draw()

    def land(self):
        L.lock(self.board, self.cells, self.ox, self.oy, self.kind + 1)
        self.board, n = L.clear_lines(self.board)
        self.lines += n
        self.score += L.SCORES[n]
        if self.timer is not None:
            self.timer.set_period(max(120, 500 - 30 * (self.lines // 5)))
        self.spawn()

    def move(self, d):
        if not self.over and L.fits(self.board, self.cells, self.ox + d, self.oy):
            self.ox += d
            self.draw()

    def rot(self):
        if self.over:
            return
        r = L.rotate(self.cells)
        for kick in (0, -1, 1, -2, 2):
            if L.fits(self.board, r, self.ox + kick, self.oy):
                self.cells, self.ox = r, self.ox + kick
                break
        self.draw()

    def drop(self):
        if self.over:
            return
        while L.fits(self.board, self.cells, self.ox, self.oy + 1):
            self.oy += 1
        self.land()
        self.draw()

    def draw(self):
        self.info.set_text("Score\n%d\nLines\n%d\n\nBest\n%d" % (self.score, self.lines, max(self.prefs.get_int("best", 0), self.score)))
        cur = {}
        if not self.over:
            for x, y in self.cells:
                if 0 <= y + self.oy < L.ROWS:
                    cur[(y + self.oy) * L.COLS + x + self.ox] = self.kind + 1
        for i, o in enumerate(self.objs):
            r, c = divmod(i, L.COLS)
            v = cur.get(i, self.board[r][c])
            if v != self.shown[i]:
                self.shown[i] = v
                o.set_style_bg_color(lv.color_hex(COLORS[v]), lv.PART.MAIN)
