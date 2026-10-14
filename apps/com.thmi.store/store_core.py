"""Shared by the Store screen and its background updater."""
import json
import logging

from mpos import AppManager, SharedPreferences, TaskManager

import thmi_net

logger = logging.getLogger(__name__)

DEFAULT_REPO = "elijah-code-5/thmi-pi-os"


def index_url():
    repo = SharedPreferences("com.thmi.store").get_string("repo", DEFAULT_REPO).strip() or DEFAULT_REPO
    return "https://github.com/%s/releases/download/apps-latest/app_index.json" % repo


async def fetch_index():
    from mpos import DownloadManager
    raw = await TaskManager.wait_for(DownloadManager.download_url(index_url()), 20)
    data = json.loads(raw)
    return data.get("apps", [])


def installed_version(fullname):
    app = AppManager.get(fullname)
    return app.version if app else None


def state_of(entry):
    cur = installed_version(entry["fullname"])
    if cur is None:
        return "install"
    return "update" if AppManager.compare_versions(entry["version"], cur) else "installed"


async def install(entry, progress=None):
    await AppManager.download_and_install_package(entry["url"], entry["fullname"], entry.get("size"), progress)
    AppManager.refresh_apps()


async def update_all():
    """Update every app we already have that has a newer version. Never installs new ones, never raises."""
    done = []
    try:
        for entry in await fetch_index():
            if entry["fullname"] == "com.thmi.store":
                pass
            if state_of(entry) == "update":
                try:
                    await install(entry)
                    done.append(entry["fullname"])
                except Exception as e:
                    logger.warning("update %s failed: %s", entry["fullname"], e)
    except Exception as e:
        logger.warning("update check failed: %s", e)
    return done
