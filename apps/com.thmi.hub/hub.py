import json
import logging

import lvgl as lv

from mpos import Activity, Intent, SettingsActivity, SharedPreferences, TaskManager

import thmi_net

logger = logging.getLogger(__name__)
APP = "com.thmi.hub"


class Hub(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences(APP)
        self.screen = lv.obj()
        self.screen.remove_flag(lv.obj.FLAG.SCROLLABLE)
        self.screen.set_style_pad_all(4, lv.PART.MAIN)

        title = lv.label(self.screen)
        title.set_text("Pi Hub")
        title.set_style_text_font(lv.font_montserrat_20, lv.PART.MAIN)
        title.align(lv.ALIGN.TOP_LEFT, 4, 2)

        gear = lv.button(self.screen)
        gear.set_size(44, 36)
        gear.align(lv.ALIGN.TOP_RIGHT, -2, 0)
        gear.add_event_cb(self._open_settings, lv.EVENT.CLICKED, None)
        gl = lv.label(gear)
        gl.set_text(lv.SYMBOL.SETTINGS)
        gl.center()

        self.status = lv.label(self.screen)
        self.status.set_width(lv.pct(96))
        self.status.set_long_mode(lv.label.LONG_MODE.WRAP)
        self.status.align(lv.ALIGN.TOP_LEFT, 4, 38)

        self.list = lv.obj(self.screen)
        self.list.set_size(lv.pct(100), 230)
        self.list.align(lv.ALIGN.BOTTOM_MID, 0, 0)
        self.list.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        self.list.set_style_pad_all(2, lv.PART.MAIN)
        self.setContentView(self.screen)

    def onResume(self, screen):
        super().onResume(screen)
        TaskManager.create_task(self._load())

    def _open_settings(self, event):
        intent = Intent(activity_class=SettingsActivity)
        intent.putExtra("prefs", self.prefs)
        intent.putExtra("settings", [
            {"title": "Pi address (blank = find automatically)", "key": "pi_host", "ui": "textarea",
             "placeholder": "192.168.1.20", "default_value": ""},
        ])
        self.startActivity(intent)

    def _set_status(self, t):
        try:
            self.status.set_text(t)
        except Exception:
            pass

    async def _load(self):
        host = self.prefs.get_string("pi_host", "")
        if not host:
            self._set_status("Looking for your Pi...")
            host = await thmi_net.discover_pi()
            if host:
                self.prefs.edit().put_string("pi_host", host).commit()
        if not host:
            self._set_status("No Pi found. Check Wi-Fi, or tap the gear and type its address.")
            return
        try:
            items = await thmi_net.get_json(host, "/api/launchers", timeout=4)
        except Exception as e:
            logger.warning("hub list failed: %s", e)
            self._set_status("Can't reach %s" % host)
            return
        self._set_status("Pi: %s" % host)
        self.list.clean()
        for it in items:
            b = lv.button(self.list)
            b.set_size(lv.pct(100), 44)
            b.add_event_cb(lambda e, i=it["id"], n=it["name"]: TaskManager.create_task(self._launch(host, i, n)),
                           lv.EVENT.CLICKED, None)
            l = lv.label(b)
            l.set_text(it["name"])
            l.set_long_mode(lv.label.LONG_MODE.DOTS)
            l.set_width(lv.pct(95))
            l.center()

    async def _launch(self, host, lid, name):
        self._set_status("Starting %s..." % name)
        try:
            await thmi_net.get(host, "/api/launch?id=%s" % lid, timeout=5)
            self._set_status("Started: %s" % name)
        except Exception as e:
            self._set_status("Failed: %s" % e)
