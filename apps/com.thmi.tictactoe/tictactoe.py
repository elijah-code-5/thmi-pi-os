import lvgl as lv

from mpos import Activity, SharedPreferences

import thmi_ui
import ttt_logic as L


class TicTacToe(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.tictactoe")
        sc = thmi_ui.screen()
        self.info = thmi_ui.text(sc, "", 6, 6, lv.font_montserrat_20, None, 228)
        self.cells = []
        for i in range(9):
            r, c = divmod(i, 3)
            b = lv.button(sc)
            b.set_size(72, 72)
            b.set_pos(10 + c * 76, 44 + r * 76)
            b.add_event_cb(lambda e, i=i: self.play(i), lv.EVENT.CLICKED, None)
            l = lv.label(b)
            l.set_style_text_font(lv.font_montserrat_24, lv.PART.MAIN)
            l.center()
            self.cells.append((b, l))
        thmi_ui.btn(sc, "New game", 70, 282, 100, 30, lambda e: self.new_game())
        self.setContentView(sc)
        self.new_game()

    def new_game(self):
        self.b = [" "] * 9
        self.over = False
        self.refresh("Your turn (X)")

    def play(self, i):
        if self.over or self.b[i] != " ":
            return
        self.b[i] = "X"
        if not self.check():
            self.b[L.best_move(self.b, "O")] = "O"
            self.check()
        self.refresh()

    def check(self):
        w, line = L.winner(self.b)
        if w or L.full(self.b):
            self.over = True
            self.line = line
            res = "You win!" if w == "X" else ("T-HMI wins" if w == "O" else "Draw")
            self.msg = res
            key = {"You win!": "wins", "T-HMI wins": "losses", "Draw": "draws"}[res]
            self.prefs.edit().put_int(key, self.prefs.get_int(key, 0) + 1).commit()
            return True
        return False

    def refresh(self, text=None):
        if text is None:
            text = self.msg if self.over else "Your turn (X)"
        self.info.set_text(text if not self.over else "%s   %dW %dL %dD" % (text, self.prefs.get_int("wins", 0), self.prefs.get_int("losses", 0), self.prefs.get_int("draws", 0)))
        for i, (b, l) in enumerate(self.cells):
            l.set_text(self.b[i] if self.b[i] != " " else "")
            hot = self.over and self.line and i in self.line
            b.set_style_bg_color(lv.color_hex(0x2ECC71 if hot else 0x445566), lv.PART.MAIN)
