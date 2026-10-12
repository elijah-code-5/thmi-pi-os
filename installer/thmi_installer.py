#!/usr/bin/env python3
"""T-HMI Hub Installer: pick a device, choose your own password and apps, write the SD card or flash the T-HMI."""
import contextlib, io, json, os, queue, shutil, stat, subprocess, sys, tempfile, threading, urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

REPO = "elijah-code-5/thmi-pi-os"
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "thmi-installer")
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

def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "thmi-installer"})
    return json.load(urllib.request.urlopen(req, timeout=20))

def find_asset(tag_prefix, suffix):
    """Newest release whose tag starts with tag_prefix and that has an asset ending in suffix."""
    for rel in http_json(f"https://api.github.com/repos/{REPO}/releases?per_page=30"):
        if rel["tag_name"].startswith(tag_prefix):
            for a in rel["assets"]:
                if a["name"].endswith(suffix):
                    return a["browser_download_url"], a["name"]
    raise RuntimeError(f"No {suffix} found in {REPO} releases yet. Wait for the GitHub build to finish.")

def download(url, name, progress):
    os.makedirs(CACHE, exist_ok=True)
    dest = os.path.join(CACHE, name)
    req = urllib.request.Request(url, headers={"User-Agent": "thmi-installer"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest + ".part", "wb") as f:
        total = int(r.headers.get("Content-Length", 0)); got = 0
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b); got += len(b)
            if total:
                progress(int(got * 100 / total))
    os.replace(dest + ".part", dest)
    return dest

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
        ttk.Button(self.body, text="Next", command=lambda: self.page_pi() if self.device.get() == "pi" else self.page_thmi()).pack(anchor="e", pady=20)

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
                self.q.put(("status", "Finding the newest image...")); url, name = find_asset("image-", ".img.xz")
                cached = os.path.join(CACHE, name)
                if os.path.exists(cached): img = cached
                else:
                    self.q.put(("status", "Downloading image..."))
                    img = download(url, name, lambda p: self.q.put(("progress", p)))
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
            self.q.put(("error", str(e)))

    # ---------------- T-HMI ----------------
    def page_thmi(self):
        self.clear()
        ttk.Label(self.body, text="Flash the T-HMI", font=("", 14, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(self.body, text="Plug the T-HMI into this computer with USB.\nIf it isn't listed, hold BOOT while plugging in.").pack(anchor="w")
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
        try:
            self.q.put(("status", "Downloading firmware..."))
            url = f"https://github.com/{REPO}/releases/download/firmware-latest/thmi-firmware.bin"
            fw = download(url, "thmi-firmware.bin", lambda p: self.q.put(("progress", p)))
            import esptool
            class W(io.TextIOBase):
                def write(s, t): self.log_add(t); return len(t)
            self.q.put(("status", "Flashing... do not unplug"))
            with contextlib.redirect_stdout(W()), contextlib.redirect_stderr(W()):
                esptool.main(["--chip", "esp32s3", "--port", port, "--baud", "460800", "write-flash", "0x0", fw])
            self.q.put(("done", "T-HMI flashed. On your phone join the 'THMI-Setup' Wi-Fi to connect it."))
        except SystemExit as e:
            if e.code: self.q.put(("error", "Flashing failed. Check the log, hold BOOT while plugging in, and try again."))
            else: self.q.put(("done", "T-HMI flashed. On your phone join the 'THMI-Setup' Wi-Fi to connect it."))
        except Exception as e:
            self.q.put(("error", str(e)))

if __name__ == "__main__":
    App().mainloop()
