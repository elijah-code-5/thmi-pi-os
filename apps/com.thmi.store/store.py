import logging

import lvgl as lv

from mpos import Activity, AppManager, Intent, MposKeyboard, SettingsActivity, SharedPreferences, TaskManager

import store_core
import thmi_ui

logger = logging.getLogger(__name__)
PAGE = 6
TAG = {"install": "Install", "update": "Update", "open": "Open"}
KEEP = ("com.thmi.store",)          # never offered for removal


class Store(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.store")
        self.apps = []
        self.cats = list(store_core.FILTERS)
        self.cat = "All"
        self.query = ""
        self.page = 0
        self.armed = None
        screen = lv.obj()
        screen.remove_flag(lv.obj.FLAG.SCROLLABLE)
        screen.set_style_pad_all(0, lv.PART.MAIN)

        thmi_ui.header(screen, "Apps", lv.SYMBOL.REFRESH, lambda e: TaskManager.create_task(self._load(True)))
        self.status = thmi_ui.status(screen, 30)

        self.dd = lv.dropdown(screen)
        self.dd.set_size(112, 34)
        self.dd.align(lv.ALIGN.TOP_LEFT, 4, 50)
        self.dd.set_options("\n".join(store_core.FILTERS))
        self.dd.add_event_cb(self._cat_changed, lv.EVENT.VALUE_CHANGED, None)

        self.ta = lv.textarea(screen)
        self.ta.set_one_line(True)
        self.ta.set_placeholder_text("Search")
        self.ta.set_size(112, 34)
        self.ta.align(lv.ALIGN.TOP_RIGHT, -4, 50)
        self.ta.add_event_cb(self._search, lv.EVENT.VALUE_CHANGED, None)
        self.ta.add_event_cb(lambda e: self.kb.add_flag(lv.obj.FLAG.HIDDEN), lv.EVENT.READY, None)

        self.box = thmi_ui.list_box(screen, 88, 44)

        bar = ((lv.SYMBOL.LEFT, 36, self._prev), ("", 52, None), (lv.SYMBOL.RIGHT, 36, self._next), ("Community apps", 112, self._community))
        x = 2
        self.page_label = None
        for txt, w, cb in bar:
            if cb is None:
                self.page_label = lv.label(screen)
                self.page_label.set_text("1/1")
                self.page_label.align(lv.ALIGN.BOTTOM_LEFT, x + 4, -14)
            else:
                b = lv.button(screen)
                b.set_size(w, 40)
                b.align(lv.ALIGN.BOTTOM_LEFT, x, -2)
                b.add_event_cb(cb, lv.EVENT.CLICKED, None)
                l = lv.label(b)
                l.set_text(txt)
                l.set_style_text_font(lv.font_montserrat_12, lv.PART.MAIN)
                l.center()
            x += w + 2
        self.kb = MposKeyboard(screen)
        self.kb.set_textarea(self.ta)
        self.kb.add_flag(lv.obj.FLAG.HIDDEN)
        self.setContentView(screen)

    def onResume(self, screen):
        super().onResume(screen)
        TaskManager.create_task(self._load(False))

    def _say(self, t):
        try:
            self.status.set_text(t)
        except Exception:
            pass

    async def _load(self, force):
        self._say("Checking GitHub and the community catalog...")
        try:
            self.apps = await store_core.fetch_all()
        except Exception as e:
            logger.warning("catalog failed: %s", e)
            self._say("Can't reach the catalog. Wi-Fi on?")
            return
        if not self.apps:
            self._say("Catalog empty or offline. Try 'Community apps'.")
        else:
            self._say("%d apps available" % len(self.apps))
        self._render()

    def _filtered(self):
        q = self.query.lower()
        items = store_core.apply_filter(self.apps, self.cat)
        return [a for a in items if not q or q in a["name"].lower() or q in a.get("desc", "").lower()]

    def _render(self):
        items = self._filtered()
        pages = max(1, (len(items) + PAGE - 1) // PAGE)
        self.page = max(0, min(self.page, pages - 1))
        self.page_label.set_text("%d/%d" % (self.page + 1, pages))
        self.box.clean()
        for a in items[self.page * PAGE:(self.page + 1) * PAGE]:
            st = store_core.state_of(a)
            txt = "%s  v%s  [%s]\n%s" % (a["name"], a["version"], TAG[st], a.get("desc", ""))
            b = thmi_ui.row(self.box, txt, lambda e, en=a: TaskManager.create_task(self._tap(en)), 46)
            b.add_event_cb(lambda e, en=a: self._hold(en), lv.EVENT.LONG_PRESSED, None)
        if not items:
            self._say("Nothing matches")

    def _cat_changed(self, e):
        self.cat = self.cats[self.dd.get_selected()]
        self.page = 0
        self._render()

    def _search(self, e):
        self.query = self.ta.get_text().strip()
        self.page = 0
        self._render()

    def _prev(self, e):
        self.page -= 1
        self._render()

    def _next(self, e):
        self.page += 1
        self._render()

    def _community(self, e):
        """The built-in MicroPythonOS store (BadgeHub): hundreds of community apps."""
        try:
            AppManager.start_app("com.micropythonos.appstore")
        except Exception as ex:
            self._say("Community store failed: %s" % ex)

    def _hold(self, entry):
        fn = entry["fullname"]
        if fn in KEEP or store_core.installed_version(fn) is None:
            return
        if self.armed == fn:
            AppManager.uninstall_app(fn)
            self.armed = None
            self._say("Removed %s" % entry["name"])
            self._render()
        else:
            self.armed = fn
            self._say("Hold again to remove %s" % entry["name"])

    async def _tap(self, entry):
        self.armed = None
        st = store_core.state_of(entry)
        if st == "open":
            AppManager.start_app(entry["fullname"])
            return
        self._say("%s %s..." % ("Updating" if st == "update" else "Installing", entry["name"]))

        async def prog(p):
            self._say("%s: %d%%" % (entry["name"], int(p)))
        try:
            await store_core.install(entry, prog)
            self._say("Installed %s. It is on your home screen." % entry["name"])
        except Exception as e:
            logger.warning("install failed: %s", e)
            self._say("Failed: %s" % e)
        self._render()
