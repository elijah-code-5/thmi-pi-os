#!/usr/bin/env python3
"""Pi 4 brain: the one service the T-HMI, phone and robot talk to. Port 8765, LAN only."""
import json, os, subprocess, shutil, ipaddress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen, Request

CONF = os.environ.get("HUB_CONFIG", "/etc/thmi-hub/config.json")
DATA = "/srv/thmi-hub"
os.makedirs(DATA + "/uploads", exist_ok=True)
DISPLAY = os.environ.get("STREAM_DISPLAY", ":0")

def conf():
    try:
        return json.load(open(CONF))
    except Exception:
        return {}

player = {"p": None}
def sh(cmd, env=None, **kw):
    return subprocess.Popen(cmd, env=env or {**os.environ, "DISPLAY": DISPLAY}, **kw)

def stop_audio():
    if player["p"] and player["p"].poll() is None:
        player["p"].terminate()
    player["p"] = None

MPV_SOCK = "/tmp/thmi-mpv.sock"

def play_file(path, video=False, ytdl_format=None):
    """Play a file or URL on the Pi (its Bluetooth headphones / speakers). Controllable through MPV_SOCK."""
    stop_audio()
    cmd = ["mpv", "--really-quiet", "--input-ipc-server=" + MPV_SOCK]
    cmd += ["--fs"] if video else ["--no-video"]
    if ytdl_format:
        cmd += ["--ytdl-format=" + ytdl_format]
    player["p"] = sh(cmd + [path])

def play_list(paths):
    stop_audio()
    player["p"] = sh(["mpv", "--really-quiet", "--no-video", "--input-ipc-server=" + MPV_SOCK] + list(paths))

def mpv_ctl(c):
    """pause | next | prev | stop | seekf | seekb | vol+ | vol-"""
    if c == "stop":
        stop_audio(); return 200, b"stopped"
    cmds = {"pause": ["cycle", "pause"], "next": ["playlist-next"], "prev": ["playlist-prev"],
            "seekf": ["seek", 30], "seekb": ["seek", -15]}
    if c in ("vol+", "vol-"):
        return set_volume(c[-1])
    if c not in cmds:
        return 400, b"bad control"
    import socket as _s
    try:
        k = _s.socket(_s.AF_UNIX, _s.SOCK_STREAM); k.settimeout(1); k.connect(MPV_SOCK)
        k.sendall((json.dumps({"command": cmds[c]}) + "\n").encode()); k.close()
        return 200, b"ok"
    except Exception as e:
        return 409, ("nothing playing: %s" % e).encode()

def set_volume(d):
    step = "5%+" if d == "+" else "5%-"
    for cmd in (["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", step],
                ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%" if d == "+" else "-5%"],
                ["amixer", "-q", "sset", "Master", "5%+" if d == "+" else "5%-"]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, timeout=3); return 200, b"ok"
    return 501, b"no mixer found"

def safe_join(base, rel):
    base = os.path.realpath(base)
    p = os.path.realpath(os.path.join(base, rel.lstrip("/")))
    return p if p == base or p.startswith(base + os.sep) else None

AUDIO = (".mp3", ".flac", ".ogg", ".opus", ".m4a", ".wav", ".aac", ".wma")
VIDEO = (".mp4", ".mkv", ".webm", ".avi", ".mov")
TEXT = (".txt", ".md", ".log", ".json", ".csv")

def listing(base, rel, media_only=False):
    p = safe_join(base, rel)
    if not p or not os.path.isdir(p):
        return 404, b"no such folder"
    dirs, files = [], []
    for n in sorted(os.listdir(p), key=str.lower):
        if n.startswith("."):
            continue
        full = os.path.join(p, n)
        if os.path.isdir(full):
            dirs.append(n)
        elif not media_only or n.lower().endswith(AUDIO):
            files.append({"name": n, "size": os.path.getsize(full)})
    rel_p = os.path.relpath(p, os.path.realpath(base))
    return 200, {"path": "" if rel_p == "." else rel_p, "dirs": dirs, "files": files}

def music_dir(): return conf().get("music_dir", "/srv/music")
def files_dir(): return conf().get("files_dir", DATA + "/files")
def notes_dir(): return DATA + "/notes"
for _d in (DATA + "/files", DATA + "/notes"):
    try: os.makedirs(_d, exist_ok=True)
    except OSError: pass

DEFAULT_PODCASTS = [
    {"name": "NPR Up First", "url": "https://feeds.npr.org/510318/podcast.xml"},
    {"name": "BBC Global News", "url": "https://podcasts.files.bbci.co.uk/p02nq0gn.rss"},
    {"name": "99% Invisible", "url": "https://feeds.simplecast.com/BqbsxVfO"},
]
def podcasts(): return conf().get("podcasts") or DEFAULT_PODCASTS

def podcast_episodes(idx_or_url):
    import xml.etree.ElementTree as ET
    url = idx_or_url
    if idx_or_url.isdigit():
        try: url = podcasts()[int(idx_or_url)]["url"]
        except Exception: return 404, b"unknown podcast"
    if not url.startswith(("http://", "https://")):
        return 400, b"bad url"
    req = Request(url, headers={"User-Agent": "thmi-hub"})
    root = ET.fromstring(urlopen(req, timeout=15).read())
    out = []
    for it in root.iter("item"):
        enc = it.find("enclosure")
        if enc is None or not enc.get("url"):
            continue
        out.append({"title": (it.findtext("title") or "?").strip()[:90], "date": (it.findtext("pubDate") or "")[:16], "url": enc.get("url")})
        if len(out) >= 25:
            break
    return 200, out

def robot_cmd(cmd):
    ip = conf().get("robot_ip")
    if not ip or cmd not in ("forward", "back", "left", "right", "stop"):
        return 400, b"robot_ip not set or bad command"
    code = {"forward": "f", "back": "b", "left": "l", "right": "r", "stop": "s"}[cmd]
    err = b""
    for path in (f"/d?a={code}", f"/drive?d={code}", f"/cmd?c={cmd}"):
        try:
            urlopen(Request(f"http://{ip}{path}"), timeout=2).read()
            return 200, b"ok"
        except Exception as e:
            err = str(e).encode()
    return 502, err

def frame_rgb565():
    out = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "x11grab", "-i", DISPLAY, "-frames:v", "1",
         "-vf", "scale=240:-2,pad=240:320:0:(oh-ih)/2", "-pix_fmt", "rgb565le", "-f", "rawvideo", "-"],
        capture_output=True, timeout=5, env={**os.environ, "DISPLAY": DISPLAY})
    return out.stdout


import socket
def port_open(port):
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
        return True
    except OSError:
        return False

def apps_info():
    base = "/opt/thmi-hub"
    try:
        cat = json.load(open(base + "/apps/catalog.json"))
    except Exception:
        cat = []
    try:
        en = open(base + "/enabled-apps").read().split()
    except Exception:
        en = ["nextcloud", "homeassistant"]
    return [dict(a, up=port_open(a["port"])) for a in cat if a["id"] in en]

DASH = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<link rel=manifest href=/manifest.webmanifest><title>T-HMI Hub</title>
<style>body{font-family:system-ui;max-width:520px;margin:30px auto;padding:0 14px}
a.c{display:block;padding:16px;margin:10px 0;border-radius:10px;background:#0b6;color:#fff;text-decoration:none;font-size:1.2em}
a.off{background:#999}small{display:block;font-size:.7em;opacity:.85}</style></head><body>
<h1>T-HMI Hub</h1><p id=ip></p><div id=apps>Loading...</div>
<p><small>Laptop: install the Nextcloud desktop app from nextcloud.com/install and connect it to the Cloud address above.</small></p>
<script>
const h=location.hostname;
document.getElementById('ip').textContent='Address: '+h;
async function go(){const r=await (await fetch('/api/apps')).json();
document.getElementById('apps').innerHTML=r.map(a=>{
return '<a class="c '+(a.up?'':'off')+'" href="http://'+h+':'+a.port+'">'+a.name+(a.up?'':' (starting, first boot takes ~10 min)')+'<small>'+a.note+'</small></a>'}).join('')}
go();setInterval(go,5000);
</script></body></html>"""

MANIFEST = json.dumps({"name": "T-HMI Hub", "short_name": "Hub", "start_url": "/", "display": "standalone",
                       "background_color": "#ffffff", "theme_color": "#00bb66",
                       "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"}]}).encode()
ICON = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#0b6"/><text x="32" y="42" font-size="28" text-anchor="middle" fill="#fff" font-family="sans-serif">Hub</text></svg>'

DEFAULT_LAUNCHERS = [
    {"id": "supertuxkart", "name": "SuperTuxKart (kart racing)", "cmd": ["supertuxkart"]},
    {"id": "retroarch", "name": "RetroArch (your own games)", "cmd": ["retroarch", "-f"]},
    {"id": "youtube", "name": "YouTube on the Pi screen", "cmd": ["chromium", "--kiosk", "https://www.youtube.com/tv"]},
    {"id": "music-stop", "name": "Stop music", "action": "stop"},
    {"id": "bt-pair", "name": "Pair Bluetooth headphones", "action": "bt-pair"},
]

def launchers():
    return conf().get("launchers") or DEFAULT_LAUNCHERS

def run_launcher(lid):
    for l in launchers():
        if l.get("id") == lid:
            if l.get("action") == "stop":
                stop_audio(); return 200, b"stopped"
            if l.get("action") == "bt-pair":
                subprocess.Popen(["/usr/local/bin/thmi-bt-pair"]); return 200, b"pairing"
            cmd = l.get("cmd")
            if isinstance(cmd, list) and cmd:
                sh(cmd, env={**os.environ, "DISPLAY": conf().get("desktop_display", ":0")})
                return 200, b"started"
    return 404, b"unknown launcher"

def discovery_responder():
    """The T-HMI shouts THMI? on UDP 8766 and we answer, so it finds the Pi without typing an IP."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 8766))
    while True:
        try:
            data, addr = s.recvfrom(64)
            if data.strip() == b"THMI?":
                s.sendto(b"THMI-HUB", addr)
        except Exception:
            pass

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def allowed(self):
        ip = ipaddress.ip_address(self.client_address[0])
        return ip.is_private or ip.is_loopback

    def reply(self, code=200, body=b"", ctype="text/plain"):
        if isinstance(body, (dict, list)):
            body, ctype = json.dumps(body).encode(), "application/json"
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def media_routes(self, u, q):
        a = lambda k, d="": q.get(k, [d])[0]
        p = u.path
        if p == "/api/music/list":     return listing(music_dir(), a("path"), True)
        if p == "/api/music/play":
            f = safe_join(music_dir(), a("path"))
            if not f or not os.path.exists(f): return 404, b"not found"
            if os.path.isdir(f):
                tracks = sorted(os.path.join(f, n) for n in os.listdir(f) if n.lower().endswith(AUDIO))
                if not tracks: return 404, b"no music here"
                play_list(tracks); return 200, b"playing folder"
            folder = os.path.dirname(f)
            tracks = sorted(os.path.join(folder, n) for n in os.listdir(folder) if n.lower().endswith(AUDIO))
            play_list(tracks[tracks.index(f):] + tracks[:tracks.index(f)]); return 200, b"playing"
        if p == "/api/yt/search":
            q_ = a("q").strip()[:100]
            if not q_: return 400, b"empty search"
            if not shutil.which("yt-dlp"): return 501, b"yt-dlp is not installed on the Pi"
            out = subprocess.run(["yt-dlp", "--flat-playlist", "-J", "--no-warnings", "ytsearch10:" + q_],
                                 capture_output=True, timeout=40)
            if out.returncode != 0: return 502, out.stderr[-200:]
            res = []
            for e in json.loads(out.stdout).get("entries", []):
                d = int(e.get("duration") or 0)
                res.append({"id": e.get("id"), "title": (e.get("title") or "?")[:80],
                            "by": (e.get("channel") or e.get("uploader") or "")[:30],
                            "len": "%d:%02d" % (d // 60, d % 60) if d else ""})
            return 200, res
        if p == "/api/yt/play":
            vid = a("id")
            if not vid.replace("-", "").replace("_", "").isalnum() or len(vid) > 20: return 400, b"bad id"
            url = "https://www.youtube.com/watch?v=" + vid
            if a("audio") == "1" or a("mode") == "audio":
                play_file(url, ytdl_format="bestaudio")                 # sound only, through the Pi's Bluetooth
            else:
                play_file(url, video=True, ytdl_format="best[height<=720]")
            return 200, b"playing"
        if p == "/api/media/ctl":      return mpv_ctl(a("c"))
        if p == "/api/volume":         return set_volume(a("d", "+"))
        if p == "/api/stats":
            st = {}
            try:
                with open("/proc/loadavg") as f: st["load"] = float(f.read().split()[0])
                with open("/proc/uptime") as f: st["up_h"] = round(float(f.read().split()[0]) / 3600, 1)
                mem = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo")}
                st["mem_pct"] = round(100 * (1 - mem["MemAvailable"] / mem["MemTotal"]))
                du = shutil.disk_usage("/")
                st["disk_pct"] = round(100 * du.used / du.total)
                st["disk_free_gb"] = round(du.free / 1e9, 1)
                st["cpus"] = os.cpu_count()
            except Exception:
                pass
            try:
                with open("/sys/class/thermal/thermal_zone0/temp") as f: st["temp_c"] = round(int(f.read()) / 1000, 1)
            except Exception:
                pass
            st["playing"] = bool(player["p"] and player["p"].poll() is None)
            return 200, st
        if p == "/api/image/raw":
            src = a("url")
            if src:
                if not src.startswith(("http://", "https://")): return 400, b"need http(s) url"
            else:
                src = safe_join(files_dir(), a("path"))
                if not src or not os.path.isfile(src): return 404, b"not found"
            w, h = int(a("w", "240")), int(a("h", "320"))
            r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-frames:v", "1",
                                "-vf", "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d" % (w, h, w, h),
                                "-pix_fmt", "rgb565le", "-f", "rawvideo", "-"], capture_output=True, timeout=40)
            if r.returncode != 0 or len(r.stdout) != w * h * 2: return 502, (r.stderr or b"conversion failed")[-200:]
            return 200, r.stdout, "application/octet-stream"
        if p == "/api/podcast/feeds":  return 200, [{"i": i, "name": x["name"]} for i, x in enumerate(podcasts())]
        if p == "/api/podcast/episodes": return podcast_episodes(a("feed", "0"))
        if p == "/api/play/url":
            if not a("u").startswith(("http://", "https://")): return 400, b"need http(s) url"
            play_file(a("u")); return 200, b"playing"
        if p == "/api/files/list":     return listing(files_dir(), a("path"))
        if p == "/api/files/play":
            f = safe_join(files_dir(), a("path"))
            if not f or not os.path.isfile(f): return 404, b"not found"
            if f.lower().endswith(AUDIO + VIDEO):
                play_file(f, video=f.lower().endswith(VIDEO)); return 200, b"playing"
            return 415, b"not a media file"
        if p == "/api/files/text":
            f = safe_join(files_dir(), a("path"))
            if not f or not os.path.isfile(f) or not f.lower().endswith(TEXT): return 404, b"not a text file"
            return 200, open(f, "rb").read(4000)
        if p == "/api/notes/list":
            return 200, sorted(n for n in os.listdir(notes_dir()) if not n.startswith("."))
        if p == "/api/notes/get":
            f = safe_join(notes_dir(), a("name"))
            if not f or not os.path.isfile(f): return 404, b"not found"
            return 200, open(f, "rb").read(), "application/octet-stream"
        return None

    def do_GET(self):
        if not self.allowed(): return self.reply(403)
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == "/":
            return self.reply(200, DASH.encode(), "text/html")
        if u.path == "/manifest.webmanifest":
            return self.reply(200, MANIFEST, "application/manifest+json")
        if u.path == "/icon.svg":
            return self.reply(200, ICON, "image/svg+xml")
        if u.path == "/api/launchers":
            return self.reply(200, [{"id": l["id"], "name": l["name"]} for l in launchers()])
        if u.path == "/api/launch":
            code, body = run_launcher(q.get("id", [""])[0]); return self.reply(code, body)
        if u.path.startswith("/api/robot/"):
            code, body = robot_cmd(u.path.rsplit("/", 1)[1]); return self.reply(code, body)
        if u.path == "/api/play/stop":
            stop_audio(); return self.reply(200, b"stopped")
        try:
            r = self.media_routes(u, q)
        except Exception as e:
            return self.reply(500, str(e).encode())
        if r is not None:
            return self.reply(*r)
        if u.path == "/api/apps":
            return self.reply(200, apps_info())
        if u.path == "/api/status":
            return self.reply(200, {str(p): port_open(p) for p in (8080, 8123, 8765)})
        if u.path == "/health":
            return self.reply(200, {"ok": True, "uploads": len(os.listdir(DATA + "/uploads"))})
        if u.path == "/stream/frame":
            try: return self.reply(200, frame_rgb565(), "application/octet-stream")
            except Exception as e: return self.reply(500, str(e).encode())
        if u.path == "/api/youtube":
            url = q.get("url", [""])[0]
            if not url.startswith("https://"): return self.reply(400, b"need https url")
            stop_audio()
            player["p"] = sh(["mpv", "--fs", "--ytdl-format=best[height<=480]", url])
            return self.reply(200, b"playing")
        if u.path == "/api/game":
            rom = q.get("rom", [""])[0]
            roms = conf().get("rom_dir", "/srv/roms")
            path = os.path.realpath(os.path.join(roms, rom))
            if not path.startswith(os.path.realpath(roms) + os.sep) or not os.path.isfile(path):
                return self.reply(404, b"rom not found")
            sh(["retroarch", "-f", path])
            return self.reply(200, b"started")
        self.reply(404)

    def do_POST(self):
        if not self.allowed(): return self.reply(403)
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == "/api/play/upload":
            name = os.path.basename(q.get("name", ["track"])[0]) or "track"
            n = int(self.headers.get("Content-Length", 0))
            dest = os.path.join(DATA, "uploads", name)
            with open(dest, "wb") as f:
                left = n
                while left > 0:
                    b = self.rfile.read(min(65536, left))
                    if not b: break
                    f.write(b); left -= len(b)
            play_file(dest)
            return self.reply(200, b"playing")
        if u.path in ("/api/notes/upload", "/api/files/upload"):
            base = notes_dir() if "notes" in u.path else files_dir()
            name = os.path.basename(q.get("name", ["note"])[0]) or "note"
            n = int(self.headers.get("Content-Length", 0))
            if n > 8_000_000: return self.reply(413, b"too big")
            open(os.path.join(base, name), "wb").write(self.rfile.read(n))
            return self.reply(200, b"saved")
        if u.path == "/api/play/stop":
            stop_audio(); return self.reply(200, b"stopped")
        if u.path == "/api/bluetooth/pair":
            # Put headphones in pairing mode first; scans 10 s and connects the first audio device.
            subprocess.Popen(["/usr/local/bin/thmi-bt-pair"])
            return self.reply(200, b"pairing")
        if u.path.startswith("/api/robot/"):
            code, body = robot_cmd(u.path.rsplit("/", 1)[1])
            return self.reply(code, body)
        self.reply(404)

if __name__ == "__main__":
    import threading
    threading.Thread(target=discovery_responder, daemon=True).start()
    for port in (80,):
        try:
            srv = ThreadingHTTPServer(("0.0.0.0", port), H)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        except OSError:
            pass
    ThreadingHTTPServer(("0.0.0.0", 8765), H).serve_forever()
