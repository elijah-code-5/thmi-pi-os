import time

import lvgl as lv

from mpos import Activity

import thmi_ui


def fmt(ms):
    s = ms // 1000
    return "%02d:%02d.%d" % (s // 60, s % 60, (ms % 1000) // 100)


class Timer(Activity):

    def onCreate(self):
        sc = thmi_ui.screen()
        self.sc = sc
        self.mode = "watch"
        self.big = thmi_ui.text(sc, "00:00.0", 4, 50, lv.font_montserrat_24, None, 232, True)
        self.big.set_style_text_font(lv.font_montserrat_24, lv.PART.MAIN)
        self.laps_l = thmi_ui.text(sc, "", 10, 130, lv.font_montserrat_14, None, 220)
        self.tab = thmi_ui.btn(sc, "Stopwatch / Countdown", 10, 4, 220, 34, lambda e: self.switch())
        self.b1 = thmi_ui.btn(sc, "Start", 10, 236, 108, 44, lambda e: self.toggle(), lv.font_montserrat_20)
        self.b2 = thmi_ui.btn(sc, "Lap", 122, 236, 108, 44, lambda e: self.second(), lv.font_montserrat_20)
        self.presets = []
        for i, m in enumerate((1, 5, 10, 25)):
            self.presets.append(thmi_ui.btn(sc, "%dm" % m, 6 + i * 59, 186, 55, 40, lambda e, m=m: self.preset(m)))
        self.timer = None
        self.running = False
        self.elapsed = 0
        self.t0 = 0
        self.target = 5 * 60 * 1000
        self.laps = []
        self.setContentView(sc)
        self.render()

    def onResume(self, screen):
        super().onResume(screen)
        if self.timer is None:
            self.timer = lv.timer_create(lambda t: self.render(), 100, None)

    def onPause(self, screen):
        if self.timer is not None:
            self.timer.delete()
            self.timer = None
        super().onPause(screen)

    def now(self):
        return self.elapsed + (time.ticks_diff(time.ticks_ms(), self.t0) if self.running else 0)

    def switch(self):
        self.mode = "down" if self.mode == "watch" else "watch"
        self.running, self.elapsed, self.laps = False, 0, []
        self.render()

    def preset(self, m):
        self.target = m * 60 * 1000
        self.running, self.elapsed = False, 0
        self.render()

    def toggle(self):
        if self.running:
            self.elapsed = self.now()
            self.running = False
        else:
            if self.mode == "down" and self.elapsed >= self.target:
                self.elapsed = 0
            self.t0 = time.ticks_ms()
            self.running = True
        self.render()

    def second(self):
        if self.mode == "watch":
            if self.running:
                self.laps.insert(0, fmt(self.now()))
                self.laps = self.laps[:6]
        else:
            self.running, self.elapsed = False, 0
        self.render()

    def render(self):
        n = self.now()
        if self.mode == "down":
            left = max(0, self.target - n)
            self.big.set_text(fmt(left))
            if left == 0 and self.running:
                self.running, self.elapsed = False, self.target
                self.big.set_text("Time is up!")
        else:
            self.big.set_text(fmt(n))
        self.b1.get_child(0).set_text("Pause" if self.running else "Start")
        self.b2.get_child(0).set_text("Lap" if self.mode == "watch" else "Reset")
        self.laps_l.set_text("\n".join("%d. %s" % (len(self.laps) - i, l) for i, l in enumerate(self.laps)) if self.mode == "watch" else "Pick a time, then Start")
        for b in self.presets:
            (b.add_flag if self.mode == "watch" else b.remove_flag)(lv.obj.FLAG.HIDDEN)
