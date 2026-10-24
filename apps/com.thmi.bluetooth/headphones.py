import json
import logging

import lvgl as lv

from mpos import Activity, TaskManager

import thmi_net
import thmi_ui

logger = logging.getLogger(__name__)


class Headphones(Activity):

    def onCreate(self):
        self.host = None
        self.busy = False
        sc = thmi_ui.screen()
        thmi_ui.header(sc, "Headphones")
        self.status = thmi_ui.status(sc, 34)
        self.status.set_long_mode(lv.label.LONG_MODE.WRAP)
        self.status.set_height(40)
        self.scan_btn = lv.button(sc)
        self.scan_btn.set_size(228, 38)
        self.scan_btn.align(lv.ALIGN.TOP_MID, 0, 78)
        self.scan_btn.add_event_cb(lambda e: TaskManager.create_task(self._scan()), lv.EVENT.CLICKED, None)
        sl = lv.label(self.scan_btn)
        sl.set_text(lv.SYMBOL.REFRESH + "  Search for headphones")
        sl.set_style_text_font(lv.font_montserrat_14, lv.PART.MAIN)
        sl.center()
        self.box = thmi_ui.list_box(sc, 122, 0)
        self.setContentView(sc)

    def onResume(self, screen):
        super().onResume(screen)
        TaskManager.create_task(self._refresh())

    def _say(self, t):
        try:
            self.status.set_text(t)
        except Exception:
            pass

    async def _server(self):
        if not self.host:
            self.host = await thmi_net.pi_host()
        if not self.host:
            self._say("No server found. Is the hub running (command: thmi-hub) on the same Wi-Fi?")
        return self.host

    def _show_connected(self, st):
        self.box.clean()
        for d in st.get("connected", []):
            thmi_ui.row(self.box, lv.SYMBOL.AUDIO + "  " + d["name"] + "  (tap to disconnect)",
                        lambda e, m=d["mac"]: TaskManager.create_task(self._disconnect(m)), 44)

    async def _refresh(self):
        self._say("Checking...")
        if not await self._server():
            return
        try:
            st = await thmi_net.get_json(self.host, "/api/bt/status", timeout=10)
        except Exception as e:
            logger.warning("bt status: %s", e)
            self._say("Can't reach the server")
            return
        if not st.get("available"):
            self._say(st.get("note") or "Bluetooth is not available on that server")
            return
        con = st.get("connected", [])
        self._say(("Connected: " + ", ".join(d["name"] for d in con) + ". Sound plays there.") if con
                  else "No headphones connected. Tap Search.")
        self._show_connected(st)

    async def _scan(self):
        if self.busy:
            return
        if not await self._server():
            return
        self.busy = True
        self._say("Searching for about 10 seconds...")
        try:
            res = await thmi_net.get_json(self.host, "/api/bt/scan", timeout=40)
        except Exception as e:
            logger.warning("bt scan: %s", e)
            self._say("Search failed. Is Bluetooth on at the server?")
            self.busy = False
            return
        self.busy = False
        self._say("%d found. Tap one to connect." % len(res) if res else "None found. Put them in pairing mode and search again.")
        self.box.clean()
        for d in res:
            mark = lv.SYMBOL.OK + "  " if d.get("connected") else ""
            thmi_ui.row(self.box, mark + d["name"], lambda e, m=d["mac"], n=d["name"]: TaskManager.create_task(self._connect(m, n)), 44)

    async def _connect(self, mac, name):
        self._say("Connecting to %s..." % name)
        try:
            await thmi_net.get(self.host, "/api/bt/connect?mac=%s" % mac, timeout=60)
        except Exception as e:
            logger.warning("bt connect: %s", e)
            self._say("Could not connect. Put %s in pairing mode and try again." % name)
            return
        await self._refresh()

    async def _disconnect(self, mac):
        self._say("Disconnecting...")
        try:
            await thmi_net.get(self.host, "/api/bt/disconnect?mac=%s" % mac, timeout=15)
        except Exception as e:
            logger.warning("bt disc: %s", e)
        await self._refresh()
