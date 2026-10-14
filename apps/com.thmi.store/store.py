import logging

import lvgl as lv

from mpos import Activity, Intent, SettingsActivity, SharedPreferences, TaskManager

import store_core

logger = logging.getLogger(__name__)
LABEL = {"install": "Install", "update": "Update", "installed": "Installed"}


class Store(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.store")
        self.screen = lv.obj()
        self.screen.remove_flag(lv.obj.FLAG.SCROLLABLE)
        self.screen.set_style_pad_all(4, lv.PART.MAIN)

        t = lv.label(self.screen)
        t.set_text("My Apps")
        t.set_style_text_font(lv.font_montserrat_20, lv.PART.MAIN)
        t.align(lv.ALIGN.TOP_LEFT, 4, 2)

        g = lv.button(self.screen)
        g.set_size(44, 36)
        g.align(lv.ALIGN.TOP_RIGHT, -2, 0)
        g.add_event_cb(self._settings, lv.EVENT.CLICKED, None)
        gl = lv.label(g)
        gl.set_text(lv.SYMBOL.SETTINGS)
        gl.center()

        self.status = lv.label(self.screen)
        self.status.set_width(lv.pct(96))
        self.status.set_long_mode(lv.label.LONG_MODE.WRAP)
        self.status.align(lv.ALIGN.TOP_LEFT, 4, 38)

        self.list = lv.obj(self.screen)
        self.list.set_size(lv.pct(100), 240)
        self.list.align(lv.ALIGN.BOTTOM_MID, 0, 0)
        self.list.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        self.list.set_style_pad_all(2, lv.PART.MAIN)
        self.setContentView(self.screen)

    def onResume(self, screen):
        super().onResume(screen)
        TaskManager.create_task(self._load())

    def _settings(self, e):
        intent = Intent(activity_class=SettingsActivity)
        intent.putExtra("prefs", self.prefs)
        intent.putExtra("settings", [{"title": "GitHub repo (owner/name)", "key": "repo", "ui": "textarea",
                                      "placeholder": store_core.DEFAULT_REPO, "default_value": store_core.DEFAULT_REPO}])
        self.startActivity(intent)

    def _say(self, text):
        try:
            self.status.set_text(text)
        except Exception:
            pass

    async def _load(self):
        self._say("Checking GitHub...")
        try:
            apps = await store_core.fetch_index()
        except Exception as e:
            logger.warning("index failed: %s", e)
            self._say("Can't reach GitHub. Is Wi-Fi connected? (Settings > Wi-Fi)")
            return
        self._say("%d apps available" % len(apps))
        self.list.clean()
        for entry in apps:
            self._row(entry)

    def _row(self, entry):
        st = store_core.state_of(entry)
        b = lv.button(self.list)
        b.set_size(lv.pct(100), 48)
        l = lv.label(b)
        l.set_text("%s  v%s\n%s" % (entry["name"], entry["version"], LABEL[st]))
        l.set_style_text_font(lv.font_montserrat_14, lv.PART.MAIN)
        l.center()
        if st != "installed":
            b.add_event_cb(lambda ev, en=entry, lab=l: TaskManager.create_task(self._do(en, lab)), lv.EVENT.CLICKED, None)

    async def _do(self, entry, label):
        label.set_text("%s\nInstalling..." % entry["name"])

        async def prog(pct):
            try:
                label.set_text("%s\n%d%%" % (entry["name"], int(pct)))
            except Exception:
                pass
        try:
            await store_core.install(entry, prog)
            label.set_text("%s  v%s\nInstalled" % (entry["name"], entry["version"]))
        except Exception as e:
            logger.warning("install failed: %s", e)
            label.set_text("%s\nFailed, tap to retry" % entry["name"])
