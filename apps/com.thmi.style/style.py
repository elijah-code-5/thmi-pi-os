import json
import logging
import os

import lvgl as lv

from mpos import Activity, AppearanceManager, AppManager, DownloadManager, SharedPreferences, TaskManager

import store_core
import thmi_ui

logger = logging.getLogger(__name__)

REPO = "elijah-code-5/thmi-pi-os"
BASE = "https://raw.githubusercontent.com/%s/main/style/" % REPO
LAUNCHER = "com.micropythonos.launcher"
ACCENTS = ("EC048C", "E53935", "FB8C00", "FDD835", "43A047", "00897B", "039BE5", "1E88E5", "5E35B1", "8E24AA", "6D4C41", "546E7A")
GRADS = (("sunset", "ff7e5f", "3a1c71"), ("ocean", "0f2027", "2c7da0"), ("forest", "0b3d2e", "6bbf59"), ("grape", "2d1b69", "b565e8"),
         ("peach", "ffb88c", "de6262"), ("midnight", "020024", "1b3a6b"), ("mint", "0f9b8e", "d3f8e2"), ("ember", "1a0000", "ff5e00"),
         ("slate", "1e2328", "4b5563"), ("candy", "ff9a9e", "a18cd1"), ("sky", "2b86c5", "dff3ff"), ("lemon", "f7971e", "ffd200"))
TABS = ("Theme", "Wall", "Home", "Boot")


def mkdirs(path):
    acc = ""
    for part in path.split("/"):
        acc = (acc + "/" + part) if acc else part
        try:
            os.mkdir(acc)
        except OSError:
            pass


def swatch(parent, color, cb, w=36, h=36):
    b = lv.button(parent)
    b.set_size(w, h)
    b.set_style_bg_color(lv.color_hex(color), lv.PART.MAIN)
    b.add_event_cb(cb, lv.EVENT.CLICKED, None)
    return b


def text(parent, t, big=False):
    l = lv.label(parent)
    l.set_text(t)
    l.set_width(lv.pct(96))
    l.set_long_mode(lv.label.LONG_MODE.WRAP)
    l.set_style_text_font(lv.font_montserrat_16 if big else lv.font_montserrat_14, lv.PART.MAIN)
    return l


def button(parent, t, cb, w=lv.pct(46), h=38):
    b = lv.button(parent)
    b.set_size(w, h)
    b.add_event_cb(cb, lv.EVENT.CLICKED, None)
    l = lv.label(b)
    l.set_text(t)
    l.center()
    return b


class Style(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.style")
        self.sys_prefs = SharedPreferences("com.micropythonos.settings")
        self.index = None
        screen = lv.obj()
        screen.remove_flag(lv.obj.FLAG.SCROLLABLE)
        screen.set_style_pad_all(0, lv.PART.MAIN)
        thmi_ui.header(screen, "Style")
        self.status = thmi_ui.status(screen, 28)
        w = 58
        for i, t in enumerate(TABS):
            b = lv.button(screen)
            b.set_size(w, 30)
            b.align(lv.ALIGN.TOP_LEFT, 4 + i * (w + 2), 48)
            b.add_event_cb(lambda e, n=t: self.show_tab(n), lv.EVENT.CLICKED, None)
            l = lv.label(b)
            l.set_text(t)
            l.set_style_text_font(lv.font_montserrat_14, lv.PART.MAIN)
            l.center()
        self.body = lv.obj(screen)
        self.body.set_size(lv.pct(100), 320 - 84)
        self.body.align(lv.ALIGN.TOP_MID, 0, 84)
        self.body.set_flex_flow(lv.FLEX_FLOW.ROW_WRAP)
        self.body.set_style_pad_all(4, lv.PART.MAIN)
        self.body.set_style_pad_row(6, lv.PART.MAIN)
        self.body.set_style_pad_column(6, lv.PART.MAIN)
        self.setContentView(screen)
        self.show_tab("Theme")

    def say(self, t):
        try:
            self.status.set_text(t)
        except Exception:
            pass

    def show_tab(self, name):
        self.body.clean()
        self.say("")
        getattr(self, "tab_" + name.lower())()

    # ---------- Theme ----------
    def tab_theme(self):
        text(self.body, "Mode", True)
        button(self.body, "Light", lambda e: self.set_mode(True))
        button(self.body, "Dark", lambda e: self.set_mode(False))
        text(self.body, "Accent color", True)
        for c in ACCENTS:
            swatch(self.body, int(c, 16), lambda e, c=c: self.set_accent(int(c, 16)))

    def refresh_ui(self):
        try:
            lv.obj_report_style_change(None)
        except Exception as e:
            logger.info("restyle: %s", e)

    def set_mode(self, light):
        AppearanceManager.set_light_mode(light, self.sys_prefs)
        self.refresh_ui()
        self.say("Done. Applied everywhere.")

    def set_accent(self, color):
        AppearanceManager.set_primary_color(color, self.sys_prefs)
        self.refresh_ui()
        self.say("Done. Applied everywhere.")

    # ---------- Wallpaper ----------
    def put(self, key, value):
        self.prefs.edit().put_string(key, value).commit()

    def tab_wall(self):
        button(self.body, "No wallpaper", lambda e: self.set_wall(""), lv.pct(96))
        text(self.body, "Colors", True)
        for n, a, b in GRADS:
            sw = swatch(self.body, int(a, 16), lambda e, a=a, b=b: self.set_wall("grad:%s:%s" % (a, b)), 36, 48)
            sw.set_style_bg_grad_color(lv.color_hex(int(b, 16)), lv.PART.MAIN)
            sw.set_style_bg_grad_dir(lv.GRAD_DIR.VER, lv.PART.MAIN)
        text(self.body, "Pictures (downloaded once)", True)
        TaskManager.create_task(self.load_pictures("wallpapers", self.body, self.set_picture))

    def set_wall(self, value):
        self.put("wall", value)
        self.say("Wallpaper set. Go back to Home to see it.")

    def set_picture(self, entry):
        TaskManager.create_task(self.fetch_wall(entry))

    async def load_index(self):
        if self.index is None:
            raw = await TaskManager.wait_for(DownloadManager.download_url(BASE + "index.json"), 20)
            self.index = json.loads(raw)
        return self.index

    async def load_pictures(self, key, parent, cb):
        try:
            idx = await self.load_index()
        except Exception as e:
            logger.warning("style index: %s", e)
            self.say("Can't reach GitHub. Is Wi-Fi on?")
            return
        for it in idx.get(key, []):
            b = button(parent, it["name"], lambda e, it=it: cb(it), lv.pct(47), 34)
            b.get_child(0).set_style_text_font(lv.font_montserrat_12, lv.PART.MAIN)

    async def fetch_wall(self, it):
        mkdirs("data/images/wallpapers")
        dest = "data/images/wallpapers/" + it["file"]
        self.say("Downloading %s..." % it["name"])
        try:
            if not _exists(dest):
                await DownloadManager.download_url(BASE + "wall/" + it["file"], outfile=dest)
            self.put("wall", "img:" + dest)
            self.say("Wallpaper set. Go back to Home to see it.")
        except Exception as e:
            self.say("Failed: %s" % e)

    # ---------- Home ----------
    def tab_home(self):
        text(self.body, "Icon size", True)
        for n, v in (("Small", 48), ("Medium", 64), ("Large", 80)):
            button(self.body, n, lambda e, v=v: self.set_icon(v), lv.pct(30))
        text(self.body, "App names", True)
        button(self.body, "Show", lambda e: self.set_labels("on"))
        button(self.body, "Hide", lambda e: self.set_labels("off"))
        text(self.body, "Home screen", True)
        have = AppManager.is_installed_by_path("apps/" + LAUNCHER)
        text(self.body, "Custom home screen is " + ("ON" if have else "OFF (needed for wallpapers and icon size)"))
        if have:
            button(self.body, "Back to the standard one", lambda e: self.use_launcher(False), lv.pct(96))
        else:
            button(self.body, "Turn on custom home screen", lambda e: self.use_launcher(True), lv.pct(96))

    def set_icon(self, v):
        self.prefs.edit().put_int("icon", v).commit()
        self.say("Done. Go back to Home to see it.")

    def set_labels(self, v):
        self.put("labels", v)
        self.say("Done. Go back to Home to see it.")

    def use_launcher(self, on):
        TaskManager.create_task(self._launcher(on))

    async def _launcher(self, on):
        try:
            if on:
                self.say("Installing...")
                for e in await store_core.fetch_all():
                    if e["fullname"] == LAUNCHER:
                        await store_core.install(e)
                        break
                else:
                    self.say("Not found in the catalog")
                    return
            else:
                AppManager.uninstall_app(LAUNCHER)
            self.say("Done.")
            self.show_tab("Home")
            AppManager.restart_launcher()
        except Exception as e:
            logger.warning("launcher switch: %s", e)
            self.say("Failed: %s" % e)

    # ---------- Boot image ----------
    def tab_boot(self):
        text(self.body, "Picture shown while the T-HMI starts. It appears the next time you start it.")
        button(self.body, "Standard logo", lambda e: self.boot_default(), lv.pct(96))
        TaskManager.create_task(self.load_pictures("boot", self.body, lambda it: TaskManager.create_task(self.fetch_boot(it))))

    def boot_default(self):
        try:
            os.remove("data/images/boot_splash.png")
        except OSError:
            pass
        self.say("Standard logo will show at next start.")

    async def fetch_boot(self, it):
        mkdirs("data/images")
        self.say("Downloading %s..." % it["name"])
        try:
            await DownloadManager.download_url(BASE + "boot/" + it["file"], outfile="data/images/boot_splash.png")
            self.say("Boot image set. It shows at next start.")
        except Exception as e:
            self.say("Failed: %s" % e)


def _exists(p):
    try:
        os.stat(p)
        return True
    except OSError:
        return False
