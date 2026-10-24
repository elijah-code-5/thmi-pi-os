import logging

import lvgl as lv

from mpos import Activity, MposKeyboard, TaskManager

import thmi_net
import thmi_ui

logger = logging.getLogger(__name__)


class YouTube(Activity):

    def onCreate(self):
        self.host = None
        screen = lv.obj()
        screen.remove_flag(lv.obj.FLAG.SCROLLABLE)
        screen.set_style_pad_all(0, lv.PART.MAIN)
        self.screen = screen
        thmi_ui.header(screen, "YouTube")
        self.status = thmi_ui.status(screen, 30)

        self.ta = lv.textarea(screen)
        self.ta.set_one_line(True)
        self.ta.set_placeholder_text("Search YouTube")
        self.ta.set_size(170, 36)
        self.ta.align(lv.ALIGN.TOP_LEFT, 4, 50)
        self.ta.add_event_cb(lambda e: self._go(), lv.EVENT.READY, None)

        go = lv.button(screen)
        go.set_size(60, 36)
        go.align(lv.ALIGN.TOP_RIGHT, -4, 50)
        go.add_event_cb(lambda e: self._go(), lv.EVENT.CLICKED, None)
        gl = lv.label(go)
        gl.set_text(lv.SYMBOL.EYE_OPEN if hasattr(lv.SYMBOL, "EYE_OPEN") else "Go")
        gl.center()

        self.audio = lv.checkbox(screen)
        self.audio.set_text("Sound only")
        self.audio.set_style_text_font(lv.font_montserrat_14, lv.PART.MAIN)
        self.audio.align(lv.ALIGN.TOP_LEFT, 6, 90)

        self.box = thmi_ui.list_box(screen, 114, 44)
        thmi_ui.controls(screen, lambda: self.host, self._say)
        self.kb = MposKeyboard(screen)
        self.kb.set_textarea(self.ta)
        self.kb.add_flag(lv.obj.FLAG.HIDDEN)
        self.setContentView(screen)

    def onResume(self, screen):
        super().onResume(screen)
        TaskManager.create_task(self._connect())

    def _say(self, t):
        try:
            self.status.set_text(t)
        except Exception:
            pass

    async def _connect(self):
        if not self.host:
            self.host = await thmi_net.pi_host()
        self._say((thmi_net.problem(True) or "Type what you want to watch") if self.host else "No server found. Is the hub running (command: thmi-hub) on the same Wi-Fi?")

    def _go(self):
        q = self.ta.get_text().strip()
        if not q:
            return
        try:
            self.kb.add_flag(lv.obj.FLAG.HIDDEN)
        except Exception:
            pass
        TaskManager.create_task(self._search(q))

    async def _search(self, q):
        if not self.host:
            await self._connect()
            if not self.host:
                return
        self._say("Searching...")
        try:
            res = await thmi_net.get_json(self.host, "/api/yt/search?q=%s" % thmi_net.quote(q), timeout=45)
        except Exception as e:
            logger.warning("yt search: %s", e)
            self._say("Search failed (is yt-dlp on the Pi?)")
            return
        self._say("%d results" % len(res))
        self.box.clean()
        for r in res:
            t = "%s\n%s  %s" % (r["title"], r["by"], r["len"])
            b = thmi_ui.row(self.box, t, lambda e, i=r["id"], n=r["title"]: TaskManager.create_task(self._play(i, n)), 48)

    async def _play(self, vid, title):
        audio = "1" if self.audio.get_state() & lv.STATE.CHECKED else "0"
        self._say("Playing: " + title)
        try:
            await thmi_net.get(self.host, "/api/yt/play?id=%s&audio=%s" % (vid, audio), timeout=15)
        except Exception as e:
            self._say("Could not play: %s" % e)
