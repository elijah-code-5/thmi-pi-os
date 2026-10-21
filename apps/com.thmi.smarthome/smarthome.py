import json
import logging

import lvgl as lv

from mpos import Activity, Intent, SettingsActivity, SharedPreferences, TaskManager

import thmi_net
import thmi_ui

logger = logging.getLogger(__name__)


class SmartHome(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.smarthome")
        sc = thmi_ui.screen()
        thmi_ui.header(sc, "Smart Home", lv.SYMBOL.SETTINGS, self._settings)
        self.status = thmi_ui.status(sc, 34)
        self.box = thmi_ui.list_box(sc, 54, 0)
        self.setContentView(sc)

    def _settings(self, e):
        intent = Intent(activity_class=SettingsActivity)
        intent.putExtra("prefs", self.prefs)
        intent.putExtra("settings", [
            {"title": "Home Assistant address (blank = your Pi)", "key": "url", "ui": "textarea", "placeholder": "192.168.1.20:8123", "default_value": ""},
            {"title": "Access token (HA profile > Long-lived tokens)", "key": "token", "ui": "textarea", "placeholder": "paste token", "default_value": ""}])
        self.startActivity(intent)

    def onResume(self, screen):
        super().onResume(screen)
        TaskManager.create_task(self._load())

    async def _base(self):
        h = self.prefs.get_string("url", "").strip()
        if not h:
            pi = await thmi_net.pi_host()
            h = (thmi_net.clean_host(pi).split(":")[0] + ":8123") if pi else ""
        return h

    def _hdr(self):
        return {"Authorization": "Bearer " + self.prefs.get_string("token", "").strip(), "Content-Type": "application/json"}

    async def _load(self):
        if not self.prefs.get_string("token", "").strip():
            self.status.set_text("Tap the gear and paste your Home Assistant token.")
            return
        self.status.set_text("Loading...")
        try:
            self.base = await self._base()
            states = json.loads(await thmi_net.get(self.base, "/api/states", timeout=12, headers=self._hdr()))
        except Exception as e:
            logger.warning("ha: %s", e)
            self.status.set_text("Can't reach Home Assistant (check address and token)")
            return
        self.box.clean()
        n = 0
        for s in states:
            eid = s["entity_id"]
            if eid.split(".")[0] in ("light", "switch", "fan", "input_boolean"):
                n += 1
                name = s.get("attributes", {}).get("friendly_name", eid)
                b = thmi_ui.row(self.box, "%s  [%s]" % (name, s["state"]), lambda e: None)
                b.add_event_cb(lambda ev, eid=eid, b=b, name=name: TaskManager.create_task(self._toggle(eid, b, name)), lv.EVENT.CLICKED, None)
        self.status.set_text("%d devices. Tap to switch." % n)

    async def _toggle(self, eid, row, name):
        try:
            dom = eid.split(".")[0]
            await thmi_net.post(self.base, "/api/services/%s/toggle" % dom, json.dumps({"entity_id": eid}).encode(), headers=self._hdr())
            st = json.loads(await thmi_net.get(self.base, "/api/states/" + eid, timeout=8, headers=self._hdr()))
            row.get_child(0).set_text("%s  [%s]" % (name, st["state"]))
        except Exception as e:
            self.status.set_text("Failed: %s" % e)
