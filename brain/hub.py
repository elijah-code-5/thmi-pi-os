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
def sh(cmd, **kw):
    return subprocess.Popen(cmd, env={**os.environ, "DISPLAY": DISPLAY}, **kw)

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
    try:
        urlopen(Request(f"http://{ip}/cmd?c={cmd}"), timeout=2).read()
        return 200, b"ok"
    except Exception as e:
        return 502, str(e).encode()

def frame_rgb565():
    out = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "x11grab", "-i", DISPLAY, "-frames:v", "1",
         "-vf", "scale=320:240", "-pix_fmt", "rgb565le", "-f", "rawvideo", "-"],
        capture_output=True, timeout=5, env={**os.environ, "DISPLAY": DISPLAY})
    return out.stdout


import socket
def port_open(port):
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
        return True
    except OSError:
        return False

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
const apps=[['Cloud storage (Nextcloud)',8080,'Login: admin / thmihub-cloud (change it)'],['Home Assistant',8123,'First visit: create your account'],['Hub status',8765,'/health']];
async function go(){const r=await (await fetch('/api/status')).json();
document.getElementById('apps').innerHTML=apps.map(a=>{const up=r[a[1]];
return '<a class="c '+(up?'':'off')+'" href="http://'+h+':'+a[1]+'">'+a[0]+(up?'':' (starting, first boot takes ~10 min)')+'<small>'+a[2]+'</small></a>'}).join('')}
go();setInterval(go,5000);
</script></body></html>"""

MANIFEST = json.dumps({"name": "T-HMI Hub", "short_name": "Hub", "start_url": "/", "display": "standalone",
                       "background_color": "#ffffff", "theme_color": "#00bb66",
                       "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"}]}).encode()
ICON = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#0b6"/><text x="32" y="42" font-size="28" text-anchor="middle" fill="#fff" font-family="sans-serif">Hub</text></svg>'

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
    for port in (80,):
        try:
            srv = ThreadingHTTPServer(("0.0.0.0", port), H)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        except OSError:
            pass
    ThreadingHTTPServer(("0.0.0.0", 8765), H).serve_forever()
