import logging

import lvgl as lv

from mpos import Activity, Intent, SettingsActivity, SharedPreferences, TaskManager

import thmi_net

logger = logging.getLogger(__name__)

APP = "com.thmi.robot"
CODES = {"forward": "f", "back": "b", "left": "l", "right": "r", "stop": "s"}
# Your robot firmware versions: /d?a=f (robot_alarm_clock_v5) and /drive?d=f (arduino-sketch). Tried in this order.
ROUTES = (("d", "/d?a=%s"), ("drive", "/drive?d=%s"))
PULSE_MS = 140


class Robot(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences(APP)
        self.held = None
        self.busy = False
        self.timer = None
        self.stop_pending = False

        screen = lv.obj()
        screen.remove_flag(lv.obj.FLAG.SCROLLABLE)
        screen.set_style_pad_all(4, lv.PART.MAIN)

        title = lv.label(screen)
        title.set_text("Robot")
        title.set_style_text_font(lv.font_montserrat_20, lv.PART.MAIN)
        title.align(lv.ALIGN.TOP_LEFT, 4, 2)

        gear = lv.button(screen)
        gear.set_size(44, 36)
        gear.align(lv.ALIGN.TOP_RIGHT, -2, 0)
        gear.add_event_cb(self._open_settings, lv.EVENT.CLICKED, None)
        gl = lv.label(gear)
        gl.set_text(lv.SYMBOL.SETTINGS)
        gl.center()

        self.status = lv.label(screen)
        self.status.set_width(lv.pct(96))
        self.status.set_long_mode(lv.label.LONG_MODE.WRAP)
        self.status.set_style_text_font(lv.font_montserrat_14, lv.PART.MAIN)
        self.status.align(lv.ALIGN.TOP_LEFT, 4, 34)

        # D-pad: hold to drive, let go to stop
        for name, label, dx, dy in (("forward", lv.SYMBOL.UP, 0, -52), ("left", lv.SYMBOL.LEFT, -72, 20),
                                    ("right", lv.SYMBOL.RIGHT, 72, 20), ("back", lv.SYMBOL.DOWN, 0, 92)):
            self._pad_button(screen, name, label, dx, dy)
        stop = lv.button(screen)
        stop.set_size(70, 70)
        stop.align(lv.ALIGN.CENTER, 0, 20)
        stop.set_style_bg_color(lv.palette_main(lv.PALETTE.RED), lv.PART.MAIN)
        stop.add_event_cb(lambda e: self._stop_now(), lv.EVENT.CLICKED, None)
        sl = lv.label(stop)
        sl.set_text("STOP")
        sl.center()

        self.setContentView(screen)

    def _pad_button(self, screen, name, text, dx, dy):
        b = lv.button(screen)
        b.set_size(70, 70)
        b.align(lv.ALIGN.CENTER, dx, dy)
        b.add_event_cb(lambda e, n=name: self._press(n), lv.EVENT.PRESSED, None)
        b.add_event_cb(lambda e: self._release(), lv.EVENT.RELEASED, None)
        b.add_event_cb(lambda e: self._release(), lv.EVENT.PRESS_LOST, None)
        l = lv.label(b)
        l.set_text(text)
        l.set_style_text_font(lv.font_montserrat_24, lv.PART.MAIN)
        l.center()

    # ---- lifecycle ----
    def onResume(self, screen):
        super().onResume(screen)
        if self.timer is None:
            self.timer = lv.timer_create(self._tick, PULSE_MS, None)
        self._show_ready()

    def onPause(self, screen):
        self._stop_now()
        if self.timer is not None:
            try:
                self.timer.delete()
            except Exception:
                pass
            self.timer = None
        super().onPause(screen)

    def onDestroy(self, screen):
        self._stop_now()

    # ---- settings ----
    def _open_settings(self, event):
        intent = Intent(activity_class=SettingsActivity)
        intent.putExtra("prefs", self.prefs)
        intent.putExtra("settings", [
            {"title": "Robot address", "key": "robot_host", "ui": "textarea",
             "placeholder": "192.168.1.50", "default_value": ""},
            {"title": "Drive via the Pi hub instead", "key": "via_hub", "ui": "radiobuttons",
             "default_value": "no", "ui_options": [("No, talk to the robot directly", "no"), ("Yes, go through the Pi", "yes")]},
        ])
        self.startActivity(intent)

    def _target(self):
        """Returns (mode, host). mode is 'hub' or 'direct'; host may be ''."""
        if self.prefs.get_string("via_hub", "no") == "yes":
            return "hub", SharedPreferences("com.thmi.hub").get_string("pi_host", "")
        return "direct", self.prefs.get_string("robot_host", "")

    def _show_ready(self):
        mode, host = self._target()
        if not host:
            self._set_status("Tap the gear and enter your robot's address." if mode == "direct"
                             else "Open Pi Hub once so the Pi is found.")
        else:
            self._set_status("%s: %s" % ("Pi" if mode == "hub" else "Robot", thmi_net.clean_host(host)))

    def _set_status(self, text):
        try:
            self.status.set_text(text)
        except Exception:
            pass

    # ---- driving ----
    def _press(self, name):
        self.held = name
        self._tick(None)

    def _release(self):
        if self.held is not None:
            self.held = None
            self._send_stop()

    def _stop_now(self):
        self.held = None
        self._send_stop()

    def _tick(self, timer):
        if self.held and not self.busy:
            TaskManager.create_task(self._send(self.held))

    def _send_stop(self):
        TaskManager.create_task(self._send("stop", force=True))

    async def _send(self, name, force=False):
        if self.busy and not force:
            return
        mode, host = self._target()
        if not host:
            self._show_ready()
            return
        self.busy = True
        try:
            if mode == "hub":
                await thmi_net.get(host, "/api/robot/%s" % name, timeout=2)
            else:
                await self._send_direct(host, CODES[name])
            if name != "stop":
                self._set_status("Driving %s" % name)
            else:
                self._show_ready()
        except Exception as e:
            logger.warning("robot send failed: %s", e)
            self._set_status("Can't reach %s" % thmi_net.clean_host(host))
        finally:
            self.busy = False

    async def _send_direct(self, host, code):
        known = self.prefs.get_string("proto", "")
        order = sorted(ROUTES, key=lambda r: 0 if r[0] == known else 1)
        last = None
        for key, route in order:
            try:
                await thmi_net.get(host, route % code, timeout=2)
                if key != known:
                    self.prefs.edit().put_string("proto", key).commit()
                return
            except RuntimeError as e:      # HTTP 404 etc.: wrong firmware style, try the next one
                last = e
                continue
        raise last or RuntimeError("no route")
