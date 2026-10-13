#!/usr/bin/env python3
"""T-HMI Hub Installer: pick a device, choose your own password and apps, write the SD card or flash the T-HMI."""
import contextlib, io, json, ssl, time, os, queue, shutil, stat, subprocess, sys, tempfile, threading, traceback, urllib.request, webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

REPO = "elijah-code-5/thmi-pi-os"
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "thmi-installer")
LOG = os.path.join(CACHE, "log.txt")
REL = f"https://github.com/{REPO}/releases/download"
IMAGE_URL = f"{REL}/image-latest/thmi-pi-os.img.xz"       # fixed names: no GitHub search needed
HUB_FW_URL = f"{REL}/firmware-latest/thmi-firmware.bin"
FACTORY_URL = "https://raw.githubusercontent.com/Xinyuan-LilyGO/T-HMI/main/firmware/HMI_factory_251202.bin"   # LilyGO known-good image
MPOS_URL = "https://github.com/MicroPythonOS/MicroPythonOS/releases/download/0.16.1/MicroPythonOS_esp32s3_0.16.1.bin"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"

def log(msg):
    try:
        os.makedirs(CACHE, exist_ok=True)
        with open(LOG, "a") as f:
            f.write(msg.rstrip() + "\n")
    except OSError:
        pass
HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

APPS = [  # keep in sync with image/.../apps/catalog.json
    ("nextcloud", "Cloud storage (Nextcloud)", True),
    ("homeassistant", "Home Assistant", True),
    ("jellyfin", "Jellyfin media server", False),
    ("syncthing", "Syncthing folder sync", False),
    ("vaultwarden", "Vaultwarden passwords", False),
    ("uptime-kuma", "Uptime Kuma monitoring", False),
    ("portainer", "Portainer (manage Docker)", False),
]

def clean_env():
    """PyInstaller points LD_LIBRARY_PATH at its own libs, which breaks system tools like lsblk and pkexec."""
    env = dict(os.environ)
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
    elif getattr(sys, "frozen", False):
        env.pop("LD_LIBRARY_PATH", None)
    return env

_CTX = None
def ssl_ctx():
    """Trusted certificates. The bundled Python cannot find the system ones, so try several sources."""
    global _CTX
    if _CTX:
        return _CTX
    cands = [os.environ.get("SSL_CERT_FILE")]
    try:
        import certifi
        cands.append(certifi.where())
    except Exception:
        pass
    cands += ["/etc/ssl/certs/ca-certificates.crt", "/etc/ca-certificates/extracted/tls-ca-bundle.pem",
              "/etc/pki/tls/certs/ca-bundle.crt", "/etc/ssl/cert.pem"]
    for c in cands:
        if c and os.path.exists(c):
            try:
                _CTX = ssl.create_default_context(cafile=c)
                log(f"using certificates from {c}")
                return _CTX
            except Exception as e:
                log(f"bad cert file {c}: {e!r}")
    _CTX = ssl.create_default_context()
    return _CTX

def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "thmi-installer"})
    return json.load(urllib.request.urlopen(req, timeout=20, context=ssl_ctx()))

def find_asset(tag_prefix, suffix):
    """Fallback only: search GitHub releases for the newest matching file."""
    for rel in http_json(f"https://api.github.com/repos/{REPO}/releases?per_page=30"):
        if rel["tag_name"].startswith(tag_prefix):
            for a in rel["assets"]:
                if a["name"].endswith(suffix):
                    return a["browser_download_url"], a["name"]
    raise RuntimeError(f"No {suffix} found in {REPO} releases yet.")

def download(url, name, progress, retries=3):
    os.makedirs(CACHE, exist_ok=True)
    dest = os.path.join(CACHE, name)
    last = None
    for attempt in range(1, retries + 1):
        try:
            log(f"download {url} (try {attempt})")
            req = urllib.request.Request(url, headers={"User-Agent": "thmi-installer"})
            with urllib.request.urlopen(req, timeout=60, context=ssl_ctx()) as r, open(dest + ".part", "wb") as f:
                total = int(r.headers.get("Content-Length", 0)); got = 0
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b); got += len(b)
                    if total:
                        progress(int(got * 100 / total))
            if total and got != total:
                raise IOError(f"incomplete download ({got} of {total} bytes)")
            os.replace(dest + ".part", dest)
            return dest
        except Exception as e:
            last = e; log(f"download failed: {e!r}")
    raise RuntimeError(f"Could not download {url}\n\nReason: {last}\n\n"
                       f"Check your internet connection. If the build has not finished yet, wait a few minutes. "
                       f"You can also download the file yourself from {RELEASES_PAGE} and use 'Use my own image file'.")

def get_image(progress):
    cached = os.path.join(CACHE, "thmi-pi-os.img.xz")
    try:
        return download(IMAGE_URL, "thmi-pi-os.img.xz", progress)
    except Exception as first:
        log(f"fixed image URL failed: {first}")
        try:
            url, name = find_asset("image-", ".img.xz")
            return download(url, name, progress)
        except Exception:
            if os.path.exists(cached):
                return cached
            raise first

def list_drives():
    out = subprocess.run(["lsblk", "-J", "-b", "-o", "PATH,SIZE,MODEL,TYPE,RM,HOTPLUG,TRAN"],
                         capture_output=True, text=True, env=clean_env())
    drives = []
    for d in json.loads(out.stdout)["blockdevices"]:
        removable = d.get("rm") in (True, "1", 1) or d.get("hotplug") in (True, "1", 1) or d.get("tran") in ("usb", "mmc")
        if d["type"] == "disk" and removable and int(d["size"] or 0) > 0:
            gb = int(d["size"]) / 1e9
            drives.append((d["path"], f'{d["path"]}  {gb:.1f} GB  {(d.get("model") or "").strip()}'))
    return drives

def list_serial():
    try:
        from serial.tools import list_ports
        return [(p.device, f"{p.device}  {p.description}") for p in list_ports.comports()]
    except Exception:
        return []

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("T-HMI Hub Installer")
        self.geometry("560x560")
        self.q = queue.Queue()
        self.device = tk.StringVar(value="pi")
        self.vars = {k: tk.StringVar() for k in ("user", "pw", "pw2", "host", "ssid", "wpw", "country")}
        self.vars["user"].set("pi"); self.vars["host"].set("thmi-hub"); self.vars["country"].set("US")
        self.apps = {a[0]: tk.BooleanVar(value=a[2]) for a in APPS}
        self.drive = tk.StringVar(); self.port = tk.StringVar()
        self.image_file = None
        self.body = ttk.Frame(self, padding=14); self.body.pack(fill="both", expand=True)
        self.status = ttk.Label(self, text="", padding=(14, 4)); self.status.pack(fill="x")
        self.bar = ttk.Progressbar(self, maximum=100); self.bar.pack(fill="x", padx=14, pady=(0, 10))
        self.after(100, self.pump)
        self.page_device()

    def pump(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "status": self.status.config(text=val)
                elif kind == "progress": self.bar["value"] = val
                elif kind == "error": messagebox.showerror("Problem", val); self.status.config(text="Stopped.")
                elif kind == "done": messagebox.showinfo("Finished", val); self.status.config(text=val)
                elif kind == "call": val()
        except queue.Empty:
            pass
        self.after(100, self.pump)

    def clear(self):
        for w in self.body.winfo_children():
            w.destroy()

    def row(self, label, key, show=None):
        f = ttk.Frame(self.body); f.pack(fill="x", pady=3)
        ttk.Label(f, text=label, width=22).pack(side="left")
        ttk.Entry(f, textvariable=self.vars[key], show=show or "").pack(side="left", fill="x", expand=True)

    def page_device(self):
        self.clear()
        ttk.Label(self.body, text="What do you want to set up?", font=("", 14, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Radiobutton(self.body, text="Raspberry Pi 4 (writes an SD card)", variable=self.device, value="pi").pack(anchor="w", pady=4)
        ttk.Radiobutton(self.body, text="LilyGO T-HMI (flash over USB)", variable=self.device, value="thmi").pack(anchor="w", pady=4)
        ttk.Radiobutton(self.body, text="Manage my Pi (open apps, see what is running)", variable=self.device, value="manage").pack(anchor="w", pady=4)
        ttk.Button(self.body, text="Next", command=lambda: {"pi": self.page_pi, "thmi": self.page_thmi, "manage": self.page_manage}[self.device.get()]()).pack(anchor="e", pady=20)
        ttk.Button(self.body, text="Open problem log", command=self.show_log).pack(anchor="w")

    def show_log(self):
        try:
            text = open(LOG).read()[-3000:] or "(log is empty)"
        except OSError:
            text = "(no log yet)"
        messagebox.showinfo("Log: " + LOG, text)

    # ---------------- Manager ----------------
    def page_manage(self):
        self.clear()
        self.addr = tk.StringVar(value=self.vars["host"].get() + ".local")
        ttk.Label(self.body, text="Manage my Pi", font=("", 14, "bold")).pack(anchor="w", pady=(0, 8))
        f = ttk.Frame(self.body); f.pack(fill="x")
        ttk.Label(f, text="Pi address").pack(side="left")
        ttk.Entry(f, textvariable=self.addr, width=30).pack(side="left", padx=6)
        ttk.Button(f, text="Check", command=self.check_pi_status).pack(side="left")
        self.apps_box = ttk.Frame(self.body); self.apps_box.pack(fill="both", expand=True, pady=10)
        ttk.Button(self.body, text="Open Hub page in browser", command=lambda: webbrowser.open("http://" + self.addr.get())).pack(anchor="w")
        ttk.Button(self.body, text="Back", command=self.page_device).pack(anchor="w", pady=10)
        self.check_pi_status()

    def check_pi_status(self):
        def work():
            try:
                apps = http_json("http://" + self.addr.get() + "/api/apps")
                self.q.put(("call", lambda: self.show_apps(apps)))
                self.q.put(("status", "Connected."))
            except Exception as e:
                log(f"manage: {e!r}")
                self.q.put(("status", "Cannot reach the Pi at " + self.addr.get() + ". Is it on and on the same Wi-Fi? Try its IP address instead."))
        threading.Thread(target=work, daemon=True).start()

    def show_apps(self, apps):
        for w in self.apps_box.winfo_children():
            w.destroy()
        for a in apps:
            row = ttk.Frame(self.apps_box); row.pack(fill="x", pady=2)
            ttk.Label(row, text=("[running] " if a.get("up") else "[starting] ") + a["name"], width=40).pack(side="left")
            ttk.Button(row, text="Open", command=lambda p=a["port"]: webbrowser.open(f"http://{self.addr.get()}:{p}")).pack(side="left")

    # ---------------- Raspberry Pi ----------------
    def page_pi(self):
        self.clear()
        ttk.Label(self.body, text="Your Pi settings", font=("", 14, "bold")).pack(anchor="w", pady=(0, 8))
        self.row("Username", "user"); self.row("Password", "pw", "*"); self.row("Repeat password", "pw2", "*")
        self.row("Computer name", "host"); self.row("Wi-Fi name (optional)", "ssid")
        self.row("Wi-Fi password", "wpw", "*"); self.row("Wi-Fi country (e.g. US)", "country")
        f = ttk.Frame(self.body); f.pack(fill="x", pady=10)
        ttk.Button(f, text="Back", command=self.page_device).pack(side="left")
        ttk.Button(f, text="Next", command=self.check_pi).pack(side="right")

    def check_pi(self):
        v = {k: x.get() for k, x in self.vars.items()}
        if not v["user"].isalnum() or not v["user"].islower():
            return messagebox.showwarning("Username", "Use only lowercase letters and numbers for the username.")
        if len(v["pw"]) < 8 or v["pw"] != v["pw2"]:
            return messagebox.showwarning("Password", "Password must be at least 8 characters and match both times.")
        if v["ssid"] and len(v["wpw"]) < 8:
            return messagebox.showwarning("Wi-Fi", "Wi-Fi passwords are at least 8 characters. Leave the name empty to use a cable.")
        self.page_apps()

    def page_apps(self):
        self.clear()
        ttk.Label(self.body, text="Choose apps to install", font=("", 14, "bold")).pack(anchor="w", pady=(0, 8))
        for aid, name, _ in APPS:
            ttk.Checkbutton(self.body, text=name, variable=self.apps[aid]).pack(anchor="w", pady=2)
        f = ttk.Frame(self.body); f.pack(fill="x", pady=14)
        ttk.Button(f, text="Back", command=self.page_pi).pack(side="left")
        ttk.Button(f, text="Next", command=self.page_write).pack(side="right")

    def page_write(self):
        self.clear()
        ttk.Label(self.body, text="Choose the SD card", font=("", 14, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(self.body, text="Plug the card into this computer, then press Refresh.\nEverything on the card will be erased.").pack(anchor="w")
        self.combo = ttk.Combobox(self.body, textvariable=self.drive, state="readonly", width=60); self.combo.pack(pady=10, anchor="w")
        ttk.Button(self.body, text="Refresh", command=self.refresh_drives).pack(anchor="w")
        ttk.Button(self.body, text="Use my own image file instead...", command=self.pick_image).pack(anchor="w", pady=6)
        f = ttk.Frame(self.body); f.pack(fill="x", pady=14)
        ttk.Button(f, text="Back", command=self.page_apps).pack(side="left")
        ttk.Button(f, text="Write SD card", command=self.start_write).pack(side="right")
        self.refresh_drives()

    def refresh_drives(self):
        self.drives = list_drives()
        self.combo["values"] = [d[1] for d in self.drives]
        self.combo.set(self.drives[0][1] if self.drives else "")

    def pick_image(self):
        p = filedialog.askopenfilename(title="Image (.img.xz)", filetypes=[("xz image", "*.xz")])
        if p: self.image_file = p; self.q.put(("status", "Using " + os.path.basename(p)))

    def start_write(self):
        sel = [d for d in self.drives if d[1] == self.drive.get()]
        if not sel:
            return messagebox.showwarning("SD card", "No SD card selected.")
        if not messagebox.askyesno("Erase card?", f"ERASE everything on:\n{sel[0][1]}\n\nContinue?"):
            return
        threading.Thread(target=self.write_worker, args=(sel[0][0],), daemon=True).start()

    def write_worker(self, dev):
        try:
            img = self.image_file
            if not img:
                self.q.put(("status", "Downloading the Pi image (about 1.2 GB)..."))
                img = get_image(lambda p: self.q.put(("progress", p)))
            cfg = {"username": self.vars["user"].get(), "password": self.vars["pw"].get(), "hostname": self.vars["host"].get(),
                   "wifi_ssid": self.vars["ssid"].get(), "wifi_password": self.vars["wpw"].get(),
                   "wifi_country": self.vars["country"].get(), "apps": [k for k, v in self.apps.items() if v.get()]}
            tmp = tempfile.mkdtemp(prefix="thmi-")
            os.chmod(tmp, 0o700)
            setup = os.path.join(tmp, "setup.json"); helper = os.path.join(tmp, "write_sd.py")
            with open(setup, "w") as f: json.dump(cfg, f)
            shutil.copy(os.path.join(HERE, "write_sd.py"), helper)
            cmd = [shutil.which("python3") or "python3", helper, img, dev, setup]
            if os.geteuid() != 0:
                if not shutil.which("pkexec"):
                    raise RuntimeError("Needs 'pkexec' (polkit) to write the card. Install polkit or run the app as administrator.")
                cmd = ["pkexec"] + cmd
            self.q.put(("status", "Waiting for your administrator password..."))
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=clean_env())
            err = None
            for line in p.stdout:
                a = line.strip().split(" ", 1)
                if a[0] == "PROGRESS": self.q.put(("progress", int(a[1])))
                elif a[0] == "STATUS": self.q.put(("status", a[1]))
                elif a[0] == "ERROR": err = a[1]
            p.wait()
            shutil.rmtree(tmp, ignore_errors=True)
            if err or p.returncode:
                raise RuntimeError(err or "The writer stopped (administrator login cancelled?).")
            self.q.put(("done", "Done! Put the card in the Pi and power it on. First start takes a few minutes. "
                                "Then open http://" + self.vars["host"].get() + ".local on any device."))
        except Exception as e:
            log(traceback.format_exc())
            self.q.put(("error", str(e)))

    # ---------------- T-HMI ----------------
    def page_thmi(self):
        self.clear()
        ttk.Label(self.body, text="Flash the T-HMI", font=("", 14, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(self.body, text="1. Plug the T-HMI into this computer with USB.\n2. Hold BOOT, tap RESET, let go of BOOT (screen goes dark = flash mode).\n3. Press Refresh, pick the port, press Flash.").pack(anchor="w")
        self.fw = getattr(self, "fw", None) or tk.StringVar(value="hub")
        ttk.Radiobutton(self.body, text="T-HMI Hub firmware (touch menu, works with the Pi)", variable=self.fw, value="hub").pack(anchor="w")
        ttk.Radiobutton(self.body, text="MicroPythonOS (official, app store, Python apps)", variable=self.fw, value="mpos").pack(anchor="w")
        ttk.Radiobutton(self.body, text="Restore LilyGO factory firmware (fixes a board that will not start)", variable=self.fw, value="factory").pack(anchor="w")
        self.pcombo = ttk.Combobox(self.body, textvariable=self.port, state="readonly", width=60); self.pcombo.pack(pady=10, anchor="w")
        ttk.Button(self.body, text="Refresh", command=self.refresh_ports).pack(anchor="w")
        self.log = tk.Text(self.body, height=12); self.log.pack(fill="both", expand=True, pady=8)
        f = ttk.Frame(self.body); f.pack(fill="x")
        ttk.Button(f, text="Back", command=self.page_device).pack(side="left")
        ttk.Button(f, text="Flash", command=self.start_flash).pack(side="right")
        self.refresh_ports()

    def refresh_ports(self):
        self.ports = list_serial()
        self.pcombo["values"] = [p[1] for p in self.ports]
        self.pcombo.set(self.ports[0][1] if self.ports else "")

    def start_flash(self):
        sel = [p for p in self.ports if p[1] == self.port.get()]
        if not sel:
            return messagebox.showwarning("Port", "No T-HMI port selected.")
        if not messagebox.askyesno("Flash?", "This replaces the firmware on the T-HMI. Continue?"):
            return
        threading.Thread(target=self.flash_worker, args=(sel[0][0],), daemon=True).start()

    def log_add(self, s):
        self.q.put(("call", lambda: (self.log.insert("end", s), self.log.see("end"))))

    def flash_worker(self, port):
        text = []
        OK_MSG = ("T-HMI flashed. Now UNPLUG the USB cable, wait 3 seconds and plug it back in (or press RESET). "
                  "Then join the 'THMI-Setup' Wi-Fi on your phone.")
        try:
            self.q.put(("status", "Downloading firmware..."))
            url, fname = {"mpos": (MPOS_URL, "MicroPythonOS_esp32s3.bin"), "factory": (FACTORY_URL, "HMI_factory.bin")}.get(self.fw.get(), (HUB_FW_URL, "thmi-firmware.bin"))
            fw = download(url, fname, lambda p: self.q.put(("progress", p)))
            import esptool
            class W(io.TextIOBase):
                def write(s, t): text.append(t); self.log_add(t); return len(t)
            self.q.put(("status", "Flashing slowly and safely... do not unplug"))
            err = None
            # Native-USB ESP32-S3 boards fail with 'error 71' on some Linux setups depending on how the reset is done,
            # so try several ways in turn. 1: you already put the board in flash mode. 2/3: let esptool reset it.
            attempts = [
                ["--before", "no-reset", "--after", "no-reset", "--baud", "115200"],
                ["--before", "usb-reset", "--after", "no-reset", "--no-stub", "--baud", "115200"],
                ["--before", "default-reset", "--after", "no-reset", "--no-stub", "--baud", "115200"],
            ]
            for i, opts in enumerate(attempts, 1):
                self.log_add(f"\n--- attempt {i} of {len(attempts)}: {' '.join(opts)} ---\n")
                self.q.put(("status", f"Flashing, attempt {i} of {len(attempts)}... do not unplug"))
                err = None
                try:
                    with contextlib.redirect_stdout(W()), contextlib.redirect_stderr(W()):
                        esptool.main(["--chip", "esp32s3", "--port", port] + opts + ["write-flash", "0x0", fw])
                except SystemExit as e:
                    err = e.code
                except OSError as e:
                    err = e
                except Exception as e:
                    err = e
                if err in (None, 0) or "Hash of data verified" in "".join(text):
                    break
                log(f"attempt {i} failed: {err!r}")
                time.sleep(2)
            full = "".join(text)
            log(full[-3000:])
            if "Hash of data verified" in full:
                self.q.put(("done", OK_MSG)); return        # the flash itself worked, whatever happened afterwards
            if err in (None, 0):
                self.q.put(("done", OK_MSG)); return
            raise RuntimeError(
                "Flashing did not finish (error: %s).\n\nPut the board in flash mode BY HAND, then press Refresh and Flash again:\n"
                "1. Hold the BOOT button. 2. Tap RESET (or plug in the cable while holding BOOT). 3. Let go of BOOT.\n"
                "The screen stays dark in this mode, and the port name may change, so press Refresh.\n\n"
                "Also try:\n"
                "- Plug straight into the laptop, not a hub, and try another port.\n"
                "4. Linux often blocks the port with 'ModemManager'. In a terminal run once: sudo systemctl stop ModemManager\n"
                "5. Add yourself to the serial group (Arch 'uucp', Debian 'dialout'), then log out and in." % (err,))
        except Exception as e:
            log(traceback.format_exc())
            self.q.put(("error", str(e)))

def selftest():
    """Used by CI against the packaged app: can it download from GitHub over HTTPS?"""
    r = urllib.request.urlopen(urllib.request.Request(HUB_FW_URL, headers={"User-Agent": "thmi-installer"}), timeout=60, context=ssl_ctx())
    n = len(r.read(2_000_000))
    print("selftest ok", r.status, n)

def main():
    if "--selftest" in sys.argv:
        selftest(); return
    try:
        App().mainloop()
    except Exception:
        msg = traceback.format_exc()
        log(msg)
        sys.stderr.write(msg)
        try:
            r = tk.Tk(); r.withdraw()
            messagebox.showerror("T-HMI Installer could not start", msg[-1200:] + "\n\nLog: " + LOG)
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
