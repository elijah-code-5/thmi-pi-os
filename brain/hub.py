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

def play_file(path):
    stop_audio()
    player["p"] = sh(["mpv", "--no-video", "--really-quiet", path])

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
