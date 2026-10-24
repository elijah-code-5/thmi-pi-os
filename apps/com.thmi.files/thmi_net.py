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


async def _discover_ips(timeout_ms=1500, port=8766):
    """Shout 'THMI?' on the LAN; every Pi / laptop running the hub answers 'THMI-HUB'. Returns all their IPs."""
    found = []
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
                if data.strip() == b"THMI-HUB" and addr[0] not in found:
                    found.append(addr[0])
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
    return found


def mode():
    """'pi' (default: use my Raspberry Pi) or 'internet' (no Pi: only things the T-HMI can do over the internet)."""
    return SharedPreferences("com.thmi.hub").get_string("source", "pi")


last_diag = {}


async def _probe(ip):
    """Which address really answers for this machine ('IP' on port 80, or 'IP:8765'), and what it can do."""
    for h in ((ip, ip + ":8765") if ":" not in ip else (ip,)):
        try:
            return h, await get_json(h, "/api/diag", timeout=2)
        except Exception:
            pass
    return None, {}


async def discover_pi(timeout_ms=1500, port=8766):
    """Find the best server: if several answer (Pi, laptop...), the one that has a speaker wins."""
    best = None
    for ip in await _discover_ips(timeout_ms, port):
        h, d = await _probe(ip)
        if not h:
            continue
        if d.get("audio"):
            last_diag.clear(); last_diag.update(d)
            return h
        if best is None:
            best = (h, d)
    if best:
        last_diag.clear(); last_diag.update(best[1])
        return best[0]
    return None


async def pi_host():
    """The server's address: the typed/saved one if it answers and can play sound, else found automatically
    (a better one wins). Returns None in internet mode or when nothing answers."""
    if mode() == "internet":
        return None
    prefs = SharedPreferences("com.thmi.hub")
    saved = prefs.get_string("pi_host", "")
    if saved:
        h, d = await _probe(saved)
        if h and d.get("audio", True):
            last_diag.clear(); last_diag.update(d)
            return h
    found = await discover_pi()
    if found:
        if not saved:
            prefs.edit().put_string("pi_host", found).commit()
        return found
    if saved:
        h, d = await _probe(saved)
        if h:
            last_diag.clear(); last_diag.update(d)
            return h
    return None


def problem(for_video=False):
    """Plain-words reason why playing may not work on the server found last, or '' if all is fine."""
    d = last_diag
    if not d:
        return ""
    if not d.get("audio"):
        return "Found your server, but it has no speaker or headphones connected."
    if not d.get("mpv"):
        return "The server is missing the player (mpv)."
    if for_video and not d.get("yt_dlp"):
        return "The server is missing YouTube support (yt-dlp)."
    return ""


def parse_rss(body, limit=25):
    """Very small RSS reader for internet mode: [{'title','url'}] of the episodes with audio."""
    txt = body.decode("utf-8", "ignore") if isinstance(body, (bytes, bytearray)) else body
    out = []
    for chunk in txt.split("<item")[1:]:
        t0 = chunk.find("<title>")
        t1 = chunk.find("</title>")
        e0 = chunk.find("<enclosure")
        if t0 < 0 or e0 < 0:
            continue
        title = chunk[t0 + 7:t1].replace("<![CDATA[", "").replace("]]>", "").strip()
        u0 = chunk.find('url="', e0)
        if u0 < 0:
            continue
        u0 += 5
        out.append({"title": title[:90], "url": chunk[u0:chunk.find('"', u0)]})
        if len(out) >= limit:
            break
    return out


def unquote(s):
    """Reverse of quote()."""
    out = bytearray()
    i = 0
    b = str(s).encode("utf-8")
    while i < len(b):
        if b[i] == 37 and i + 2 < len(b) + 0 and i + 2 <= len(b) - 1:
            try:
                out.append(int(b[i + 1:i + 3], 16)); i += 3; continue
            except ValueError:
                pass
        out.append(b[i]); i += 1
    return out.decode("utf-8", "ignore")
