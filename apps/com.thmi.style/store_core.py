"""Shared by the Store screen and its background updater.
Catalog sources (nothing is stored on the device except the apps you install):
  1. your own GitHub repo  (releases/apps-latest/app_index.json)
  2. the official MicroPythonOS catalog (apps.micropythonos.com)
  3. any extra app_index.json links you add in My Apps > gear
"""
import json
import logging
import os
import shutil

from mpos import AppManager, SharedPreferences, TaskManager

logger = logging.getLogger(__name__)

DEFAULT_REPO = "elijah-code-5/thmi-pi-os"
OFFICIAL = "https://apps.micropythonos.com/app_index.json"
CATS = {"game": "Games", "games": "Games", "media": "Media", "music": "Media", "video": "Media",
        "customize": "Customize", "settings": "Customize", "launcher": "Customize", "utilities": "Tools", "utility": "Tools", "productivity": "Tools"}
FILTERS = ("All", "Games", "Media", "Tools", "Customize", "Installed", "Updates")


def prefs():
    return SharedPreferences("com.thmi.store")


def my_index_url():
    repo = prefs().get_string("repo", DEFAULT_REPO).strip() or DEFAULT_REPO
    return "https://github.com/%s/releases/download/apps-latest/app_index.json" % repo


def extra_sources():
    raw = prefs().get_string("sources", "").replace(",", "\n").split()
    return [u for u in raw if u.startswith("http")]


def _norm(e, src, default=False):
    """Make every catalog entry look the same."""
    url = e.get("url") or e.get("download_url")
    if not url or not e.get("fullname"):
        return None
    return {"fullname": e["fullname"], "name": e.get("name", e["fullname"]), "version": str(e.get("version", "0")),
            "cat": CATS.get(str(e.get("category", "")).lower(), "Tools"), "desc": e.get("description") or e.get("short_description", ""),
            "url": url, "size": e.get("size"), "src": src, "default": default}


async def _fetch(url, timeout=25):
    from mpos import DownloadManager
    raw = await TaskManager.wait_for(DownloadManager.download_url(url), timeout)
    data = json.loads(raw)
    return data.get("apps", []) if isinstance(data, dict) else data


async def fetch_all():
    """Merged catalog. A source that fails is skipped. Order = priority when the same app is in two places."""
    out, seen = [], set()
    for src, url, default in (("mine", my_index_url(), True), ("official", OFFICIAL, False)) + tuple(("custom", u, False) for u in extra_sources()):
        try:
            for e in await _fetch(url):
                n = _norm(e, src, default)
                if n and n["fullname"] not in seen:
                    seen.add(n["fullname"])
                    out.append(n)
        except Exception as ex:
            logger.warning("catalog %s failed: %s", src, ex)
    out.sort(key=lambda a: a["name"].lower())
    return out


def installed_version(fullname):
    app = AppManager.get(fullname)
    return app.version if app else None


def state_of(entry):
    cur = installed_version(entry["fullname"])
    if cur is None:
        return "install"
    try:
        return "update" if AppManager.compare_versions(entry["version"], cur) else "open"
    except Exception:
        return "open"


def apply_filter(apps, flt):
    if flt == "All":
        return apps
    if flt == "Installed":
        return [a for a in apps if installed_version(a["fullname"]) is not None]
    if flt == "Updates":
        return [a for a in apps if state_of(a) == "update"]
    return [a for a in apps if a["cat"] == flt]


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _rmtree(path):
    try:
        shutil.rmtree(path)
    except Exception:
        pass


def recover():
    """MicroPythonOS deletes an app BEFORE downloading its update, so a Wi-Fi hiccup or power cut used to leave
    the app (even this Store) gone. install() now keeps the old copy in bak/; put back anything left over."""
    try:
        if not _exists("bak"):
            return []
        back = []
        for name in os.listdir("bak"):
            if not _exists("apps/" + name):
                os.rename("bak/" + name, "apps/" + name)
                back.append(name)
            else:
                _rmtree("bak/" + name)
        if back:
            AppManager.refresh_apps()
        return back
    except Exception as e:
        logger.warning("recover failed: %s", e)
        return []


async def install(entry, progress=None):
    """Install or update an app without ever losing the working copy: the old one is parked in bak/ and
    put back if the download or unpacking fails."""
    fn = entry["fullname"]
    dest, bak = "apps/" + fn, "bak/" + fn
    had = _exists(dest)
    if had:
        if not _exists("bak"):
            os.mkdir("bak")
        _rmtree(bak)
        os.rename(dest, bak)
    try:
        await AppManager.download_and_install_package(entry["url"], fn, entry.get("size"), progress)
    except Exception:
        _rmtree(dest)
        if had:
            os.rename(bak, dest)
        AppManager.refresh_apps()
        raise
    if had:
        _rmtree(bak)
    AppManager.refresh_apps()


async def maintain():
    """Background job: update what is installed; install new default apps from your own repo. Never raises."""
    done = recover()
    p = prefs()
    auto_new = p.get_string("auto_install", "yes") != "no"
    skip = set(p.get_string("ignore", "").replace(",", " ").split())
    try:
        for e in await fetch_all():
            if e["fullname"] in skip:
                continue
            st = state_of(e)
            if st == "update" or (st == "install" and auto_new and e["default"] and e["fullname"] != "com.micropythonos.launcher"):
                try:
                    await install(e)
                    done.append(e["fullname"])
                    await TaskManager.sleep_ms(200)
                except Exception as ex:
                    logger.warning("auto %s failed: %s", e["fullname"], ex)
    except Exception as ex:
        logger.warning("maintain failed: %s", ex)
    return done
