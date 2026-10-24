#!/usr/bin/env python3
"""Pi 4 brain: the one service the T-HMI, phone and robot talk to. Port 8765, LAN only."""
import json, os, subprocess, shutil, ipaddress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen, Request

CONF = os.environ.get("HUB_CONFIG", "/etc/thmi-hub/config.json")
DATA = os.environ.get("THMI_DATA", "/srv/thmi-hub")        # laptop mode: ~/.local/share/thmi-hub
BASE = os.environ.get("THMI_BASE", "/opt/thmi-hub")        # holds .env (login), catalog and enabled-apps on the Pi
os.makedirs(DATA + "/uploads", exist_ok=True)
DISPLAY = os.environ.get("STREAM_DISPLAY", ":1")

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

def bt_pair():
    exe = shutil.which("thmi-bt-pair") or "/usr/local/bin/thmi-bt-pair"
    if not os.path.exists(exe):
        return 501, b"Pair Bluetooth headphones in this computer's own Bluetooth settings"
    subprocess.Popen([exe]); return 200, b"pairing"

def diag():
    """What this server can do right now (so the T-HMI can say exactly what is missing)."""
    def ver(cmd):
        try: return subprocess.run(cmd, capture_output=True, text=True, timeout=8).stdout.strip().splitlines()[0]
        except Exception: return None
    return {"server": socket.gethostname(), "mpv": bool(shutil.which("mpv")), "ffmpeg": bool(shutil.which("ffmpeg")),
            "yt_dlp": ver(["yt-dlp", "--version"]) if shutil.which("yt-dlp") else None,
            "js_runtime": bool(shutil.which("node") or shutil.which("deno")),
            "music_dir": os.path.isdir(music_dir()), "files_dir": os.path.isdir(files_dir()), "podcasts": len(podcasts())}

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

def podcast_search(term):
    """Apple Podcasts directory (the iTunes Search API): any podcast, no feed link needed."""
    from urllib.parse import quote
    d = json.loads(urlopen(Request("https://itunes.apple.com/search?media=podcast&limit=15&term=" + quote(term),
                                   headers={"User-Agent": "thmi-hub"}), timeout=12).read())
    return [{"name": (r.get("collectionName") or "?")[:70], "feed": r["feedUrl"]} for r in d.get("results", []) if r.get("feedUrl")]

WEB = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>T-HMI Player</title>
<style>body{font-family:system-ui;max-width:640px;margin:16px auto;padding:0 12px}input{padding:9px;font-size:1em;width:62%}button{padding:9px 13px;font-size:1em}
.r{display:block;width:100%;text-align:left;margin:5px 0;padding:11px;border:0;border-radius:9px;background:#e8eef2}small{opacity:.7}</style>
<h2>Play on the server</h2><p><button onclick="m='yt'">YouTube</button> <button onclick="m='pod'">Podcasts (Apple)</button>
<button onclick="c('pause')">Pause</button> <button onclick="c('stop')">Stop</button> <button onclick="c('vol-')">Vol -</button> <button onclick="c('vol+')">Vol +</button></p>
<input id=q placeholder="Search" onkeydown="if(event.key=='Enter')go()"> <button onclick="go()">Search</button><p id=s></p><div id=o></div>
<script>let m='yt';const E=encodeURIComponent;
function c(x){fetch('/api/media/ctl?c='+E(x))}
function show(a){o.innerHTML='';a.forEach(x=>{const b=document.createElement('button');b.className='r';b.textContent=x[0];b.onclick=x[1];o.appendChild(b)})}
async function go(){s.textContent='Searching...';try{
if(m=='yt'){const r=await(await fetch('/api/yt/search?q='+E(q.value))).json();s.textContent=r.length+' results';
show(r.map(v=>[v.title+'  -  '+v.by+'  '+v.len,()=>{fetch('/api/yt/play?id='+v.id+'&audio=0');s.textContent='Playing '+v.title}]))}
else{const r=await(await fetch('/api/podcast/search?q='+E(q.value))).json();s.textContent=r.length+' podcasts';
show(r.map(p=>[p.name,async()=>{const e=await(await fetch('/api/podcast/episodes?feed='+E(p.feed))).json();s.textContent=p.name;
show(e.map(x=>[x.title,()=>{fetch('/api/play/url?u='+E(x.url));s.textContent='Playing '+x.title}]))}]))}}catch(e){s.textContent='Failed: '+e}}
</script>"""

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

def services():
    """Things you already run elsewhere (Jellyfin, Immich, Nextcloud...): [{'name','url'}] from the config."""
    return [x for x in conf().get("services", []) if isinstance(x, dict) and x.get("url")]

def services_save(lst):
    c = conf(); c["services"] = lst
    os.makedirs(os.path.dirname(CONF), exist_ok=True)
    json.dump(c, open(CONF, "w"), indent=2)

def url_up(url):
    from urllib.parse import urlparse as _u
    u = _u(url if "//" in url else "http://" + url)
    try:
        socket.create_connection((u.hostname, u.port or (443 if u.scheme == "https" else 80)), timeout=0.7).close()
        return True
    except Exception:
        return False

def apps_info():
    base = BASE
    try:
        cat = json.load(open(base + "/apps/catalog.json"))
    except Exception:
        cat = []
    try:
        en = open(base + "/enabled-apps").read().split()
    except Exception:
        en = ["nextcloud", "homeassistant"]
    out = []
    for a in cat:
        if a["id"] not in en:
            continue
        a = dict(a, up=port_open(a["port"]))
        if a["id"] == "omv":
            try: a["note"] = open("/var/lib/thmi-hub/omv.status").read().strip() or a["note"]
            except Exception: pass
        out.append(a)
    for i, sv in enumerate(services()):
        url = sv["url"] if "//" in sv["url"] else "http://" + sv["url"]
        out.append({"id": "svc%d" % i, "name": sv.get("name") or url, "url": url, "port": 0, "up": url_up(url),
                    "note": "Your own server: " + url, "svc": i})
    return out

DASH = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<link rel=manifest href=/manifest.webmanifest><title>T-HMI Hub</title>
<style>body{font-family:system-ui;max-width:560px;margin:24px auto;padding:0 14px;background:#f4f6f5;color:#123}
h1{margin:.2em 0}a.c{display:block;padding:14px 16px;margin:9px 0;border-radius:12px;background:#0b6;color:#fff;text-decoration:none;font-size:1.15em}
a.off{background:#8a9a93}small{display:block;font-size:.72em;opacity:.9}.box{background:#fff;border-radius:12px;padding:12px 16px;margin:12px 0;box-shadow:0 1px 3px #0002}
.row a,.row button{display:inline-block;margin:4px 6px 4px 0;padding:9px 14px;border-radius:9px;background:#1e64dc;color:#fff;border:0;font-size:1em;text-decoration:none}
button.red{background:#c0392b}td{padding:2px 14px 2px 0}</style></head><body>
<h1>T-HMI Hub</h1><div class=box id=sys>Loading...</div><div id=apps></div>
<div class=box><a href=/web>Open YouTube / Podcast search in this browser</a></div><div class=box id=addbox><b>Add something you already run</b> (Jellyfin, Immich, Nextcloud...)<div class=row>
<input id=sn placeholder="Name, e.g. Jellyfin" size=14> <input id=su placeholder="http://192.168.1.50:8096" size=24> <button onclick="addsvc()">Add</button></div></div>
<div class=box id=pibox><b>This Pi</b><div class=row><a href=/wifi>Wi-Fi setup</a><button onclick="act('/api/bluetooth/pair','Put your headphones in pairing mode first. Pairing...')">Pair Bluetooth</button>
<button class=red onclick="if(confirm('Restart the Pi?'))act('/api/system/reboot','Restarting...')">Restart</button>
<button class=red onclick="if(confirm('Shut the Pi down? You will need to unplug and replug it to start it again.'))act('/api/system/shutdown','Shutting down...')">Shut down</button></div><p id=note></p></div>
<p><small>Laptop: install the Nextcloud desktop app from nextcloud.com/install and connect it to the Cloud address above.</small></p>
<script>
const h=location.hostname;
async function addsvc(){if(!su.value)return;await fetch('/api/services/add?name='+encodeURIComponent(sn.value)+'&url='+encodeURIComponent(su.value),{method:'POST'});sn.value=su.value='';go()}
async function delsvc(i){await fetch('/api/services/del?i='+i,{method:'POST'});go()}
fetch('/api/mode').then(r=>r.json()).then(m=>{if(m.pkg)pibox.style.display='none'});
function act(u,m){note.textContent=m;fetch(u,{method:'POST'}).then(r=>r.text()).then(t=>note.textContent=m+' '+t)}
async function info(){try{const i=await (await fetch('/api/system/info')).json();
sys.innerHTML='<table><tr><td>Name</td><td><b>'+i.hostname+'.local</b></td></tr><tr><td>Address</td><td>'+i.ip+'</td></tr><tr><td>Wi-Fi</td><td>'+(i.ssid||'cable or none')+'</td></tr><tr><td>Temperature</td><td>'+i.temp_c+' C</td></tr><tr><td>Memory used</td><td>'+i.mem_used_pct+'%</td></tr><tr><td>Disk used</td><td>'+i.disk_used_pct+'%</td></tr><tr><td>Up for</td><td>'+i.uptime_min+' min</td></tr></table>'}catch(e){sys.textContent='Status needs the login you chose in the installer.'}}
async function go(){const r=await (await fetch('/api/apps')).json();
apps.innerHTML=r.map(a=>'<a class="c '+(a.up?'':'off')+'" href="'+(a.url||'http://'+h+':'+a.port)+'">'+a.name+(a.up?'':(a.svc!=null?' (not answering)':' (starting, the first start can take 10-20 minutes)'))+'<small>'+a.note+'</small></a>'+(a.svc!=null?'<small><a href=# onclick="delsvc('+a.svc+');return false">remove '+a.name+'</a></small>':'')').join('')}
info();go();setInterval(go,5000);setInterval(info,15000);
</script></body></html>"""

MANIFEST = json.dumps({"name": "T-HMI Hub", "short_name": "Hub", "start_url": "/", "display": "standalone",
                       "background_color": "#ffffff", "theme_color": "#00bb66",
                       "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"}]}).encode()
ICON = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#0b6"/><text x="32" y="42" font-size="28" text-anchor="middle" fill="#fff" font-family="sans-serif">Hub</text></svg>'


import base64, threading, time as _time

def admin_creds():
    """ADMIN_USER / ADMIN_PASSWORD written by the first-boot script (the login you chose in the installer)."""
    env = {}
    try:
        for line in open(BASE + "/.env"):
            if "=" in line:
                k, v = line.rstrip("\n").split("=", 1); env[k] = v
    except Exception:
        pass
    return env.get("ADMIN_USER"), env.get("ADMIN_PASSWORD")

def nm(*args, timeout=25):
    r = subprocess.run(["nmcli", *args], capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()

def wifi_scan():
    rc, out = nm("-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "auto")
    seen = {}
    for line in out.splitlines():
        parts = line.replace("\\:", "\0").split(":")
        if len(parts) < 3 or not parts[0]:
            continue
        ssid = parts[0].replace("\0", ":")
        try: sig = int(parts[1])
        except ValueError: sig = 0
        if ssid not in seen or sig > seen[ssid]["signal"]:
            seen[ssid] = {"ssid": ssid, "signal": sig, "secure": bool(parts[2].strip())}
    return sorted(seen.values(), key=lambda x: -x["signal"])

def wifi_connect(ssid, password):
    def work():
        _time.sleep(1.5)                      # let the web page get its answer before the connection changes
        args = ["dev", "wifi", "connect", ssid] + (["password", password] if password else [])
        rc, out = nm(*args, timeout=60)
        if rc:                                # could not join: make a saved profile so it retries by itself
            nm("connection", "delete", ssid)
            nm("connection", "add", "type", "wifi", "con-name", ssid, "ssid", ssid, "connection.autoconnect", "yes",
               *(["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password] if password else []))
    threading.Thread(target=work, daemon=True).start()

def system_info():
    def rd(path, default=""):
        try: return open(path).read().strip()
        except Exception: return default
    ip = ""
    try:
        ip = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=3).stdout.split()[0]
    except Exception:
        pass
    temp = rd("/sys/class/thermal/thermal_zone0/temp")
    try: mem = {k: int(v.split()[0]) for k, v in (l.split(":") for l in open("/proc/meminfo") if l.split(":")[0] in ("MemTotal", "MemAvailable"))}
    except Exception: mem = {}
    du = shutil.disk_usage("/")
    return {"hostname": socket.gethostname(), "ip": ip, "temp_c": round(int(temp) / 1000, 1) if temp.isdigit() else None,
            "mem_used_pct": round(100 - 100 * mem["MemAvailable"] / mem["MemTotal"]) if mem else None,
            "disk_used_pct": round(100 * du.used / du.total), "uptime_min": int(float(rd("/proc/uptime", "0 0").split()[0]) // 60),
            "ssid": nm("-t", "-g", "GENERAL.CONNECTION", "dev", "show", "wlan0")[1] if shutil.which("nmcli") else ""}

def power(action):
    cmd = ["sudo", "-n", "systemctl", "reboot" if action == "reboot" else "poweroff"]
    threading.Timer(2.0, lambda: subprocess.Popen(cmd)).start()

WIFI_PAGE = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Wi-Fi</title>
<style>body{font-family:system-ui;max-width:520px;margin:30px auto;padding:0 14px}input,select,button{font-size:1.1em;padding:10px;margin:6px 0;width:100%;box-sizing:border-box}
button{background:#0b6;color:#fff;border:0;border-radius:8px}</style></head><body>
<h1>Connect to Wi-Fi</h1><p id=msg>Looking for networks...</p>
<select id=list onchange="ssid.value=this.value"></select>
<input id=ssid placeholder="Network name"><input id=pw type=password placeholder="Wi-Fi password">
<button onclick="go()">Connect</button><p><a href="/">Back</a></p>
<script>
fetch('/api/wifi/scan').then(r=>r.json()).then(l=>{msg.textContent=l.length?'Pick your network or type it:':'No list available (type the name).';
list.innerHTML='<option value="">-- networks --</option>'+l.map(n=>'<option>'+n.ssid.replace(/</g,'')+'</option>').join('')}).catch(()=>msg.textContent='Type the network name.');
function go(){fetch('/api/wifi/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ssid:ssid.value,password:pw.value})})
.then(r=>r.text()).then(t=>msg.textContent='Connecting... If this page stops responding, reconnect your phone to your normal Wi-Fi and open http://'+location.hostname.replace(/^10\\.42\\.0\\.1$/,'thmi-hub.local')+' in a minute or two.')}
</script></body></html>"""

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
                return bt_pair()
            cmd = l.get("cmd")
            if isinstance(cmd, list) and cmd:
                sh(cmd, env={**os.environ, "DISPLAY": conf().get("desktop_display", DISPLAY)})
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
        if p == "/api/diag":           return 200, diag()
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
        if p == "/api/podcast/search":
            return 200, podcast_search(a("q"))
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

    PROTECTED = ("/wifi", "/api/wifi/", "/api/system/", "/api/services/")

    def authed(self, path):
        """Wi-Fi and power controls ask for the username and password you chose in the installer (browser pop-up)."""
        if not path.startswith(self.PROTECTED):
            return True
        user, pw = admin_creds()
        if not pw:
            return True
        try:
            got = base64.b64decode(self.headers.get("Authorization", "Basic ")[6:]).decode()
        except Exception:
            got = ""
        if got == "%s:%s" % (user, pw):
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="T-HMI Hub"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def do_GET(self):
        if not self.allowed(): return self.reply(403)
        u = urlparse(self.path); q = parse_qs(u.query)
        if not self.authed(u.path): return
        if u.path == "/wifi":
            return self.reply(200, WIFI_PAGE.encode(), "text/html")
        if u.path == "/api/wifi/scan":
            try: return self.reply(200, wifi_scan())
            except Exception as e: return self.reply(200, [])
        if u.path == "/api/system/info":
            return self.reply(200, system_info())
        if u.path == "/":
            return self.reply(200, DASH.encode(), "text/html")
        if u.path == "/web":
            return self.reply(200, WEB.encode(), "text/html")
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
        if u.path == "/api/mode":
            return self.reply(200, {"pkg": bool(os.environ.get("THMI_PKG"))})
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
        if not self.authed(u.path): return
        if u.path == "/api/wifi/connect":
            try:
                d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                if not d.get("ssid"): return self.reply(400, b"need a network name")
                wifi_connect(d["ssid"], d.get("password", "")); return self.reply(200, b"connecting")
            except Exception as e: return self.reply(400, str(e).encode())
        if u.path == "/api/services/add":
            name, url = q.get("name", [""])[0].strip()[:40], q.get("url", [""])[0].strip()
            if not url.lower().startswith(("http://", "https://")) and "//" in url: return self.reply(400, b"bad address")
            services_save(services() + [{"name": name, "url": url}]); return self.reply(200, b"added")
        if u.path == "/api/services/del":
            lst = services()
            try: lst.pop(int(q.get("i", ["-1"])[0]))
            except Exception: return self.reply(400, b"bad number")
            services_save(lst); return self.reply(200, b"removed")
        if u.path in ("/api/system/reboot", "/api/system/shutdown"):
            power(u.path.rsplit("/", 1)[1]); return self.reply(200, b"ok")
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
            return self.reply(*bt_pair())
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
