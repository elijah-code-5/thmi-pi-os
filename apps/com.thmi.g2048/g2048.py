import random

import lvgl as lv

from mpos import Activity, SharedPreferences

import thmi_game as g

COLORS = {0: 0xCDC1B4, 2: 0xEEE4DA, 4: 0xEDE0C8, 8: 0xF2B179, 16: 0xF59563, 32: 0xF67C5F, 64: 0xF65E3B,
          128: 0xEDCF72, 256: 0xEDCC61, 512: 0xEDC850, 1024: 0xEDC53F, 2048: 0xEDC22E}


def slide_row(row):
    """Slide one row to the left; returns (new_row, points)."""
    vals = [v for v in row if v]
    out, pts, i = [], 0, 0
    while i < len(vals):
        if i + 1 < len(vals) and vals[i] == vals[i + 1]:
            out.append(vals[i] * 2)
            pts += vals[i] * 2
            i += 2
        else:
            out.append(vals[i])
            i += 1
    return out + [0] * (4 - len(out)), pts


def move(board, d):
    """board: 16 ints row-major. d in l r u d. Returns (new_board, points, moved)."""
    b = [board[i * 4:(i + 1) * 4] for i in range(4)]
    if d in "ud":
        b = [list(c) for c in zip(*b)]
    if d in "rd":
        b = [r[::-1] for r in b]
    pts = 0
    nb = []
    for r in b:
        nr, p = slide_row(r)
        nb.append(nr)
        pts += p
    if d in "rd":
        nb = [r[::-1] for r in nb]
    if d in "ud":
        nb = [list(c) for c in zip(*nb)]
    flat = [v for r in nb for v in r]
    return flat, pts, flat != list(board)


def can_move(board):
    return any(move(board, d)[2] for d in "lrud")


class Game2048(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.g2048")
        self.best = self.prefs.get_int("best", 0)
        s = g.new_screen()
        self.score_l = g.label(s, "", 16, 8, 6)
        self.best_l = g.label(s, "", 14, align=lv.ALIGN.TOP_RIGHT, x=-8, y=8)
        self.board_obj = g.box(s, 8, 40, 224, 224, 0xBBADA0, 8)
        self.cells = []
        for i in range(16):
            x, y = 6 + (i % 4) * 54, 6 + (i // 4) * 54
            c = g.box(self.board_obj, x, y, 50, 50, 0xCDC1B4, 5)
            l = g.label(c, "", 20, align=lv.ALIGN.CENTER)
            self.cells.append((c, l))
        g.on_swipe(s, self.swipe)
        for t, x, y, d in ((lv.SYMBOL.UP, 100, 272, "u"), (lv.SYMBOL.LEFT, 56, 296, "l"), (lv.SYMBOL.DOWN, 100, 296, "d"), (lv.SYMBOL.RIGHT, 144, 296, "r")):
            g.button(s, t, x, y, 40, 22, lambda e, d=d: self.swipe(d), 14)
        g.button(s, "New", 8, 280, 44, 36, lambda e: self.new_game(), 14)
        self.msg = g.label(s, "", 20, align=lv.ALIGN.TOP_MID, y=140, color=0x333333)
        self.setContentView(s)
        self.new_game()

    def new_game(self):
        self.b = [0] * 16
        self.score = 0
        self.over = False
        self.msg.set_text("")
        self.spawn()
        self.spawn()
        self.draw()

    def spawn(self):
        free = [i for i, v in enumerate(self.b) if v == 0]
        if free:
            self.b[random.choice(free)] = 4 if random.random() < 0.1 else 2

    def swipe(self, d):
        if self.over:
            return
        nb, pts, moved = move(self.b, d)
        if not moved:
            return
        self.b, self.score = nb, self.score + pts
        self.spawn()
        if self.score > self.best:
            self.best = self.score
            self.prefs.edit().put_int("best", self.best).commit()
        if not can_move(self.b):
            self.over = True
            self.msg.set_text("Game over")
        self.draw()

    def draw(self):
        self.score_l.set_text("Score %d" % self.score)
        self.best_l.set_text("Best %d" % self.best)
        for (c, l), v in zip(self.cells, self.b):
            c.set_style_bg_color(lv.color_hex(COLORS.get(v, 0x3C3A32)), lv.PART.MAIN)
            l.set_text(str(v) if v else "")
            l.set_style_text_color(lv.color_hex(0x776E65 if v <= 4 else 0xF9F6F2), lv.PART.MAIN)
