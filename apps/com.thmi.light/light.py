import lvgl as lv

from mpos import Activity

import thmi_ui

COLORS = (0xFFFFFF, 0xFFE9B0, 0xFFB347, 0xFF4040, 0x40FF80, 0x4080FF, 0xFF40FF)


class Light(Activity):

    def onCreate(self):
        sc = thmi_ui.screen()
        sc.set_style_bg_color(lv.color_hex(COLORS[0]), lv.PART.MAIN)
        sc.add_flag(lv.obj.FLAG.CLICKABLE)
        self.i = 0
        self.sc = sc
        self.hint = thmi_ui.text(sc, "Tap to change color", 10, 140, lv.font_montserrat_20, 0x808080, 220, True)
        sc.add_event_cb(self.tap, lv.EVENT.CLICKED, None)
        self.setContentView(sc)

    def tap(self, e):
        self.i = (self.i + 1) % len(COLORS)
        self.sc.set_style_bg_color(lv.color_hex(COLORS[self.i]), lv.PART.MAIN)
        self.hint.set_text("")
