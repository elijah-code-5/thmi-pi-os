import json

import lvgl as lv

from mpos import Activity, SharedPreferences

import thmi_ui

NAMES = ("Counter 1", "Counter 2", "Counter 3", "Counter 4")


class Tally(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.tally")
        try:
            self.vals = json.loads(self.prefs.get_string("vals", "[0,0,0,0]"))
        except Exception:
            self.vals = [0, 0, 0, 0]
        self.vals = (self.vals + [0] * 4)[:4]
        sc = thmi_ui.screen()
        thmi_ui.header(sc, "Tally")
        self.labels = []
        for i in range(4):
            y = 40 + i * 68
            thmi_ui.text(sc, NAMES[i], 8, y + 2, lv.font_montserrat_14)
            n = thmi_ui.text(sc, "0", 8, y + 20, lv.font_montserrat_24, None, 100)
            self.labels.append(n)
            thmi_ui.btn(sc, "-", 112, y + 6, 56, 48, lambda e, i=i: self.add(i, -1), lv.font_montserrat_24)
            thmi_ui.btn(sc, "+", 174, y + 6, 58, 48, lambda e, i=i: self.add(i, 1), lv.font_montserrat_24)
        self.setContentView(sc)
        self.draw()

    def add(self, i, d):
        self.vals[i] = max(0, self.vals[i] + d)
        self.prefs.edit().put_string("vals", json.dumps(self.vals)).commit()
        self.draw()

    def draw(self):
        for i, l in enumerate(self.labels):
            l.set_text(str(self.vals[i]))
