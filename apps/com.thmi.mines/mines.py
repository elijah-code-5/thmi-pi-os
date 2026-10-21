import random

import lvgl as lv

from mpos import Activity

import thmi_game as g

COLS, ROWS, MINES, CS = 8, 8, 9, 30
NUMC = (0, 0x1E88E5, 0x43A047, 0xE53935, 0x5E35B1, 0x6D4C41, 0x00897B, 0x000000, 0x777777)


def neighbours(i):
    x, y = i % COLS, i // COLS
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if (dx or dy) and 0 <= x + dx < COLS and 0 <= y + dy < ROWS:
                yield (y + dy) * COLS + x + dx


class Mines(Activity):

    def onCreate(self):
        s = g.new_screen()
        self.info = g.label(s, "", 16, 8, 6)
        self.btns = []
        for i in range(COLS * ROWS):
            b = lv.button(s)
            b.set_size(CS - 2, CS - 2)
            b.set_pos((i % COLS) * CS + 1, 34 + (i // COLS) * CS)
            b.add_event_cb(lambda e, i=i: self.tap(i), lv.EVENT.CLICKED, None)
            l = lv.label(b)
            l.set_text("")
            l.center()
            self.btns.append((b, l))
        self.flag_mode = False
        self.mode_btn = g.button(s, "Dig", 8, 34 + ROWS * CS + 8, 100, 34, self.toggle, 16)
        g.button(s, "New game", 120, 34 + ROWS * CS + 8, 110, 34, lambda e: self.new_game(), 16)
        self.setContentView(s)
        self.new_game()

    def toggle(self, e):
        self.flag_mode = not self.flag_mode
        self.mode_btn.get_child(0).set_text("Flag" if self.flag_mode else "Dig")

    def new_game(self):
        self.mines = set()
        self.open = [False] * (COLS * ROWS)
        self.flag = [False] * (COLS * ROWS)
        self.first = True
        self.done = False
        self.flag_mode = False
        self.mode_btn.get_child(0).set_text("Dig")
        for b, l in self.btns:
            b.set_style_bg_color(lv.theme_get_color_primary(None), lv.PART.MAIN)
            l.set_text("")
        self.update_info()

    def update_info(self, text=None):
        self.info.set_text(text or "Mines left: %d" % (MINES - sum(self.flag)))

    def place(self, safe):
        cells = [i for i in range(COLS * ROWS) if i != safe and i not in neighbours(safe)]
        self.mines = set(g.sample(cells, MINES))

    def count(self, i):
        return sum(1 for n in neighbours(i) if n in self.mines)

    def tap(self, i):
        if self.done or self.open[i]:
            return
        if self.flag_mode:
            self.flag[i] = not self.flag[i]
            self.btns[i][1].set_text(lv.SYMBOL.WARNING if self.flag[i] else "")
            self.update_info()
            return
        if self.flag[i]:
            return
        if self.first:
            self.place(i)
            self.first = False
        if i in self.mines:
            self.lose(i)
            return
        self.reveal(i)
        if sum(self.open) == COLS * ROWS - MINES:
            self.done = True
            self.update_info("You win!")

    def reveal(self, start):
        stack = [start]
        while stack:
            i = stack.pop()
            if self.open[i] or self.flag[i]:
                continue
            self.open[i] = True
            b, l = self.btns[i]
            b.set_style_bg_color(lv.color_hex(0xDDDDDD), lv.PART.MAIN)
            n = self.count(i)
            if n:
                l.set_text(str(n))
                l.set_style_text_color(lv.color_hex(NUMC[n]), lv.PART.MAIN)
            else:
                stack.extend(neighbours(i))

    def lose(self, hit):
        self.done = True
        for m in self.mines:
            b, l = self.btns[m]
            b.set_style_bg_color(lv.color_hex(0xE53935 if m == hit else 0x999999), lv.PART.MAIN)
            l.set_text("*")
        self.update_info("Boom! Game over")
