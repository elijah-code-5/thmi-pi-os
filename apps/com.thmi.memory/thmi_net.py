"""Tiny LAN helpers shared by the T-HMI apps (HTTP GET with a hard timeout, find the Pi, URL-encode)."""
import json
import socket

from mpos import DownloadManager, SharedPreferences, TaskManager


def clean_host(text):
    """'192.168.1.5', ' http://robot.local:8080/ ' -> 'robot.local:8080' (no scheme, no slashes)."""
    t = (text or "").strip()
    for p in ("http://", "https://"):
        if t.lower().startswith(p):
            t = t[len(p):]
    return t.strip("/ ")


def quote(s):
    """Percent-encode for a URL query value."""
    out = []
    for b in str(s).encode("utf-8"):
        c = chr(b)
        if c.isalpha() and b < 128 or c.isdigit() or c in "-_.~/":
            out.append(c)
        else:
            out.append("%%%02X" % b)
    return "".join(out)


async def get(host, path, timeout=3, headers=None):
    """GET http://host/path and return the body bytes. Raises on timeout, no connection or HTTP error."""
    url = "http://%s%s" % (clean_host(host), path)
    return await TaskManager.wait_for(DownloadManager.download_url(url, headers=headers), timeout)


async def get_url(url, timeout=15, headers=None):
    """GET a full http(s) URL (internet APIs)."""
    return await TaskManager.wait_for(DownloadManager.download_url(url, headers=headers), timeout)


async def get_json(host, path, timeout=4):
    return json.loads(await get(host, path, timeout))


async def post(host, path, data, timeout=10, headers=None):
    url = "http://%s%s" % (clean_host(host), path)
    return await TaskManager.wait_for(DownloadManager.post_url(url, data=data, headers=headers), timeout)


async def discover_pi(timeout_ms=1500, port=8766):
    """Shout 'THMI?' on the LAN; the Pi hub answers 'THMI-HUB'. Returns the Pi's IP address or None."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception:
            pass
        s.setblocking(False)
        try:
            s.sendto(b"THMI?", ("255.255.255.255", port))
        except Exception:
            pass
        waited = 0
        while waited < timeout_ms:
            try:
                data, addr = s.recvfrom(64)
                if data.strip() == b"THMI-HUB":
                    return addr[0]
            except OSError:
                pass
            await TaskManager.sleep_ms(50)
            waited += 50
    except Exception:
        pass
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass
    return None


async def pi_host():
    """The Pi's address: saved by the Pi Hub app, else found automatically (and saved)."""
    prefs = SharedPreferences("com.thmi.hub")
    host = prefs.get_string("pi_host", "")
    if not host:
        host = await discover_pi()
        if host:
            prefs.edit().put_string("pi_host", host).commit()
    return host or None
