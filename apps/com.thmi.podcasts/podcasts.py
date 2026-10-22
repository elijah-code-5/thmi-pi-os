import logging

import lvgl as lv

from mpos import Activity, Intent, SettingsActivity, SharedPreferences, TaskManager

import thmi_net
import thmi_ui

logger = logging.getLogger(__name__)


INTERNET_FEEDS = [("NPR Up First", "https://feeds.npr.org/510318/podcast.xml"),
                  ("BBC Global News", "https://podcasts.files.bbci.co.uk/p02nq0gn.rss")]


class Podcasts(Activity):

    def onCreate(self):
        self.host = None
        self.prefs = SharedPreferences("com.thmi.podcasts")
        screen = lv.obj()
        screen.remove_flag(lv.obj.FLAG.SCROLLABLE)
        screen.set_style_pad_all(0, lv.PART.MAIN)
        thmi_ui.header(screen, "Podcasts", lv.SYMBOL.SETTINGS, self._settings)
        self.status = thmi_ui.status(screen)
        self.box = thmi_ui.list_box(screen, 54, 44)
        thmi_ui.controls(screen, lambda: self.host, self._say)
        self.setContentView(screen)

    def onResume(self, screen):
        super().onResume(screen)
        TaskManager.create_task(self._feeds())

    def _settings(self, e):
        intent = Intent(activity_class=SettingsActivity)
        intent.putExtra("prefs", self.prefs)
        intent.putExtra("settings", [{"title": "My podcast feed (RSS link)", "key": "feed_url", "ui": "textarea",
                                      "placeholder": "https://example.com/feed.xml", "default_value": ""}])
        self.startActivity(intent)

    def _say(self, t):
        try:
            self.status.set_text(t)
        except Exception:
            pass

    async def _feeds(self):
        self._say("Loading...")
        try:
            if thmi_net.mode() == "internet":
                feeds = [{"i": u, "name": n} for n, u in INTERNET_FEEDS]
            else:
                if not self.host:
                    self.host = await thmi_net.pi_host()
                if not self.host:
                    self._say("No Pi found. Open Pi Hub (gear: choose Internet only to browse without a Pi).")
                    return
                feeds = await thmi_net.get_json(self.host, "/api/podcast/feeds")
        except Exception as e:
            logger.warning("feeds: %s", e)
            self._say("Can't reach the Pi")
            return
        self._say("Pick a podcast")
        self.box.clean()
        for f in feeds:
            thmi_ui.row(self.box, lv.SYMBOL.AUDIO + "  " + f["name"], lambda e, i=str(f["i"]), n=f["name"]: TaskManager.create_task(self._episodes(i, n)))
        mine = self.prefs.get_string("feed_url", "").strip()
        if mine:
            thmi_ui.row(self.box, lv.SYMBOL.PLUS + "  My feed", lambda e: TaskManager.create_task(self._episodes(thmi_net.quote(mine), "My feed")))

    async def _episodes(self, feed, name):
        self._say("Loading " + name + "...")
        try:
            if thmi_net.mode() == "internet":
                eps = thmi_net.parse_rss(await thmi_net.get_url(feed if feed.startswith("http") else thmi_net.unquote(feed), 25))
            else:
                eps = await thmi_net.get_json(self.host, "/api/podcast/episodes?feed=%s" % feed, timeout=25)
        except Exception as e:
            logger.warning("episodes: %s", e)
            self._say("Could not load that feed")
            return
        self._say(name)
        self.box.clean()
        thmi_ui.row(self.box, lv.SYMBOL.LEFT + "  All podcasts", lambda e: TaskManager.create_task(self._feeds()))
        for ep in eps:
            thmi_ui.row(self.box, ep["title"], lambda e, u=ep["url"], t=ep["title"]: TaskManager.create_task(self._play(u, t)), 46)

    async def _play(self, url, title):
        if thmi_net.mode() == "internet":
            self._say("Internet-only mode lists episodes. Playing needs your Pi.")
            return
        self._say("Playing: " + title)
        try:
            await thmi_net.get(self.host, "/api/play/url?u=%s" % thmi_net.quote(url), timeout=8)
        except Exception as e:
            self._say("Could not play: %s" % e)
