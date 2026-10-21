import logging

import lvgl as lv

from mpos import Activity, TaskManager

import thmi_net
import thmi_ui

logger = logging.getLogger(__name__)


class PiStats(Activity):

    def onCreate(self):
        self.host = None
        self.alive = False
        sc = thmi_ui.screen()
        thmi_ui.header(sc, "Pi Stats")
        self.status = thmi_ui.status(sc, 34)
        self.bars = {}
        for i, (key, name) in enumerate((("load", "CPU load"), ("temp", "Temperature"), ("mem", "Memory"), ("disk", "Disk"))):
            thmi_ui.text(sc, name, 8, 62 + i * 58, lv.font_montserrat_14)
            bar = lv.bar(sc)
            bar.set_size(224, 16)
            bar.set_pos(8, 82 + i * 58)
            bar.set_range(0, 100)
            val = thmi_ui.text(sc, "", 150, 62 + i * 58, lv.font_montserrat_14, None, 82)
            val.set_style_text_align(lv.TEXT_ALIGN.RIGHT, lv.PART.MAIN)
            self.bars[key] = (bar, val)
        self.foot = thmi_ui.text(sc, "", 8, 296, lv.font_montserrat_14, None, 224)
        self.setContentView(sc)

    def onResume(self, screen):
        super().onResume(screen)
        self.alive = True
        TaskManager.create_task(self._loop())

    def onPause(self, screen):
        self.alive = False
        super().onPause(screen)

    async def _loop(self):
        while self.alive:
            try:
                if not self.host:
                    self.host = await thmi_net.pi_host()
                if not self.host:
                    self.status.set_text("No Pi found. Open Pi Hub first.")
                else:
                    st = await thmi_net.get_json(self.host, "/api/stats", timeout=5)
                    self.status.set_text("Pi: %s" % self.host)
                    cpus = st.get("cpus") or 4
                    self._set("load", min(100, int(100 * st.get("load", 0) / cpus)), "%.2f" % st.get("load", 0))
                    self._set("temp", min(100, int(st.get("temp_c", 0))), "%s C" % st.get("temp_c", "?"))
                    self._set("mem", st.get("mem_pct", 0), "%d%%" % st.get("mem_pct", 0))
                    self._set("disk", st.get("disk_pct", 0), "%d%%  %s GB free" % (st.get("disk_pct", 0), st.get("disk_free_gb", "?")))
                    self.foot.set_text("Up %s h   %s" % (st.get("up_h", "?"), "Playing now" if st.get("playing") else "Quiet"))
            except Exception as e:
                logger.info("stats: %s", e)
                self.status.set_text("Can't reach the Pi")
            await TaskManager.sleep(4)

    def _set(self, key, pct, text):
        bar, val = self.bars[key]
        bar.set_value(pct, False)
        val.set_text(text)
