import logging

import lvgl as lv

from mpos import Activity, TaskManager

import thmi_net
import thmi_ui

logger = logging.getLogger(__name__)


class Music(Activity):

    def onCreate(self):
        self.host = None
        self.path = ""
        screen = lv.obj()
        screen.remove_flag(lv.obj.FLAG.SCROLLABLE)
        screen.set_style_pad_all(0, lv.PART.MAIN)
        thmi_ui.header(screen, "Music")
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
            data = await thmi_net.get_json(self.host, "/api/music/list?path=%s" % thmi_net.quote(path))
        except Exception as e:
            logger.warning("music list: %s", e)
            self._say("Can't load music from the Pi")
            return
        self.path = data["path"]
        self._say(thmi_net.problem() or ("/" + self.path if self.path else "All music"))
        self.box.clean()
        if self.path:
            up = self.path.rsplit("/", 1)[0] if "/" in self.path else ""
            thmi_ui.row(self.box, lv.SYMBOL.LEFT + "  Back", lambda e, p=up: TaskManager.create_task(self._open(p)))
            thmi_ui.row(self.box, lv.SYMBOL.PLAY + "  Play this folder",
                        lambda e, p=self.path: TaskManager.create_task(self._play(p)))
        for d in data["dirs"]:
            full = (self.path + "/" + d) if self.path else d
            thmi_ui.row(self.box, lv.SYMBOL.DIRECTORY + "  " + d, lambda e, p=full: TaskManager.create_task(self._open(p)))
        for f in data["files"]:
            full = (self.path + "/" + f["name"]) if self.path else f["name"]
            thmi_ui.row(self.box, lv.SYMBOL.AUDIO + "  " + f["name"], lambda e, p=full, n=f["name"]: TaskManager.create_task(self._play(p, n)))
        if not data["dirs"] and not data["files"]:
            self._say("Empty. Put music in /srv/music on the Pi.")

    async def _play(self, path, name=None):
        self._say("Playing " + (name or "folder"))
        try:
            await thmi_net.get(self.host, "/api/music/play?path=%s" % thmi_net.quote(path), timeout=5)
        except Exception as e:
            self._say("Could not play: %s" % e)
