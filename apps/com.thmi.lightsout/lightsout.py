import random

import lvgl as lv

from mpos import Activity

import thmi_game as g

N, CS = 5, 44
ON, OFF = 0xFFD54F, 0x37474F


class LightsOut(Activity):

    def onCreate(self):
        s = g.new_screen()
        self.info = g.label(s, "", 16, 8, 6)
        self.cells = []
        for i in range(N * N):
            b = lv.button(s)
            b.set_size(CS - 4, CS - 4)
            b.set_pos(10 + (i % N) * CS, 50 + (i // N) * CS)
            b.add_event_cb(lambda e, i=i: self.press(i), lv.EVENT.CLICKED, None)
            self.cells.append(b)
        g.button(s, "New game", 60, 50 + N * CS + 14, 120, 40, lambda e: self.new_game(), 16)
        self.setContentView(s)
        self.new_game()

    def flip(self, i):
        x, y = i % N, i // N
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            if 0 <= x + dx < N and 0 <= y + dy < N:
                j = (y + dy) * N + x + dx
                self.on[j] = not self.on[j]

    def new_game(self):
        self.on = [False] * (N * N)
        for _ in range(10):                      # presses from a solved board, so it can always be solved
            self.flip(random.randint(0, N * N - 1))
        if not any(self.on):
            self.flip(12)
        self.moves = 0
        self.paint()

    def press(self, i):
        if not any(self.on):
            return
        self.flip(i)
        self.moves += 1
        self.paint()

    def paint(self):
        for b, v in zip(self.cells, self.on):
            b.set_style_bg_color(lv.color_hex(ON if v else OFF), lv.PART.MAIN)
        self.info.set_text("Moves %d" % self.moves if any(self.on) else "Solved in %d moves!" % self.moves)
