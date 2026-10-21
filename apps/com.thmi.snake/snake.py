import random

import lvgl as lv

from mpos import SharedPreferences

import thmi_game as g

CELL, COLS, ROWS = 16, 15, 17          # 240 x 272 playfield
DIRS = {"l": (-1, 0), "r": (1, 0), "u": (0, -1), "d": (0, 1)}
OPP = {"l": "r", "r": "l", "u": "d", "d": "u"}


class Snake(g.Ticker):
    TICK = 170

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.snake")
        self.best = self.prefs.get_int("best", 0)
        s = g.new_screen()
        self.score_l = g.label(s, "", 14, 6, 2)
        self.field = g.box(s, 0, 22, COLS * CELL, ROWS * CELL, 0x1F2A1F)
        self.cells = []
        for i in range(COLS * ROWS):
            self.cells.append(g.box(self.field, (i % COLS) * CELL, (i // COLS) * CELL, CELL - 1, CELL - 1, 0x1F2A1F, 3))
        g.on_swipe(self.field, self.turn)
        pad = (("u", lv.SYMBOL.UP, 100, 298), ("l", lv.SYMBOL.LEFT, 56, 298), ("d", lv.SYMBOL.DOWN, 144, 298), ("r", lv.SYMBOL.RIGHT, 188, 298))
        for d, t, x, y in pad:
            g.button(s, t, x, y, 40, 20, lambda e, d=d: self.turn(d), 12)
        g.button(s, "New", 6, 296, 44, 22, lambda e: self.new_game(), 12)
        self.msg = g.label(s, "", 20, align=lv.ALIGN.TOP_MID, y=130, color=0xFFFFFF)
        self.setContentView(s)
        self.new_game()

    def new_game(self):
        self.body = [(7, 8), (6, 8), (5, 8)]
        self.dir = self.nd = "r"
        self.score = 0
        self.alive = True
        self.msg.set_text("")
        self.food = None
        self.place_food()
        for c in self.cells:
            c.set_style_bg_color(lv.color_hex(0x1F2A1F), lv.PART.MAIN)
        self.paint()

    def place_food(self):
        while True:
            f = (random.randrange(COLS), random.randrange(ROWS))
            if f not in self.body:
                self.food = f
                return

    def turn(self, d):
        if d != OPP[self.dir]:
            self.nd = d

    def idx(self, p):
        return p[1] * COLS + p[0]

    def paint(self):
        self.score_l.set_text("Score %d   Best %d" % (self.score, self.best))

    def tick(self):
        if not self.alive:
            return
        self.dir = self.nd
        dx, dy = DIRS[self.dir]
        hx, hy = self.body[0]
        nh = (hx + dx, hy + dy)
        if not (0 <= nh[0] < COLS and 0 <= nh[1] < ROWS) or nh in self.body[:-1]:
            self.alive = False
            self.msg.set_text("Game over")
            return
        self.body.insert(0, nh)
        self.cells[self.idx(nh)].set_style_bg_color(lv.color_hex(0x5CD65C), lv.PART.MAIN)
        if nh == self.food:
            self.score += 1
            if self.score > self.best:
                self.best = self.score
                self.prefs.edit().put_int("best", self.best).commit()
            self.place_food()
            self.paint()
        else:
            t = self.body.pop()
            self.cells[self.idx(t)].set_style_bg_color(lv.color_hex(0x1F2A1F), lv.PART.MAIN)
        self.cells[self.idx(self.food)].set_style_bg_color(lv.color_hex(0xE53935), lv.PART.MAIN)
