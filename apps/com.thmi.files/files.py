import logging

import lvgl as lv

from mpos import Activity, TaskManager

import thmi_net
import thmi_ui

logger = logging.getLogger(__name__)
MEDIA = (".mp3", ".flac", ".ogg", ".opus", ".m4a", ".wav", ".mp4", ".mkv", ".webm", ".avi", ".mov")
TEXT = (".txt", ".md", ".log", ".json", ".csv")


class Files(Activity):

    def onCreate(self):
        self.host = None
        self.path = ""
        screen = lv.obj()
        screen.remove_flag(lv.obj.FLAG.SCROLLABLE)
        screen.set_style_pad_all(0, lv.PART.MAIN)
        thmi_ui.header(screen, "Pi Files")
        self.status = thmi_ui.status(screen)
        self.box = thmi_ui.list_box(screen, 54, 44)
        thmi_ui.controls(screen, lambda: self.host, self._say)
        self.setContentView(screen)

    def onResume(self, screen):
        super().onResume(screen)
        TaskManager.create_task(self._open(self.path))

    def _say(self, t):
        try:
            self.status.set_text(t)
        except Exception:
            pass

    async def _open(self, path):
        self._say("Loading...")
        try:
            if not self.host:
                self.host = await thmi_net.pi_host()
            if not self.host:
                self._say("No server found. Is the hub running (command: thmi-hub) on the same Wi-Fi?")
                return
            data = await thmi_net.get_json(self.host, "/api/files/list?path=%s" % thmi_net.quote(path))
        except Exception as e:
            logger.warning("files list: %s", e)
            self._say("Can't load files from the Pi")
            return
        self.path = data["path"]
        self._say("/" + self.path)
        self.box.clean()
        if self.path:
            up = self.path.rsplit("/", 1)[0] if "/" in self.path else ""
            thmi_ui.row(self.box, lv.SYMBOL.LEFT + "  Back", lambda e, p=up: TaskManager.create_task(self._open(p)))
        for d in data["dirs"]:
            full = (self.path + "/" + d) if self.path else d
            thmi_ui.row(self.box, lv.SYMBOL.DIRECTORY + "  " + d, lambda e, p=full: TaskManager.create_task(self._open(p)))
        for f in data["files"]:
            n = f["name"]
            full = (self.path + "/" + n) if self.path else n
            low = n.lower()
            sym = lv.SYMBOL.AUDIO if low.endswith(MEDIA) else lv.SYMBOL.FILE
            thmi_ui.row(self.box, "%s  %s" % (sym, n), lambda e, p=full, nm=n: TaskManager.create_task(self._tap(p, nm)))
        if not data["dirs"] and not data["files"]:
            self._say("Empty. Upload files with Nextcloud or the Pi.")

    async def _tap(self, path, name):
        low = name.lower()
        try:
            if low.endswith(MEDIA):
                self._say("Playing " + name)
                await thmi_net.get(self.host, "/api/files/play?path=%s" % thmi_net.quote(path), timeout=5)
            elif low.endswith(TEXT):
                raw = await thmi_net.get(self.host, "/api/files/text?path=%s" % thmi_net.quote(path), timeout=6)
                self.box.clean()
                thmi_ui.row(self.box, lv.SYMBOL.LEFT + "  Back", lambda e: TaskManager.create_task(self._open(self.path)))
                t = lv.label(self.box)
                t.set_width(lv.pct(96))
                t.set_long_mode(lv.label.LONG_MODE.WRAP)
                t.set_style_text_font(lv.font_montserrat_14, lv.PART.MAIN)
                t.set_text(raw.decode("utf-8", "replace"))
                self._say(name)
            else:
                self._say("Can't open this type here")
        except Exception as e:
            self._say("Failed: %s" % e)
