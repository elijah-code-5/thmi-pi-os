# T-HMI + Raspberry Pi 4 Hub

One system: a **Raspberry Pi 4** is the brain, a **LilyGO T-HMI** is the handheld touch controller, and the **robot** is driven by the Pi.

## Get it running (Installer app)

**Linux laptop (Arch, Ubuntu, etc.).** From this repo's **Releases** page, open **"Installer app (latest)"** and download one of:
- `thmi-installer-linux-x86_64.tar.gz` - **use this first.** Extract it, double-click `START-INSTALLER.sh` (choose "Run" if asked). Needs nothing extra.
- `thmi-installer-x86_64.AppImage` - single file, but needs FUSE2 (`sudo pacman -S fuse2` on Arch, `sudo apt install libfuse2` on Ubuntu) and "Allow executing".

In the app:
- **Raspberry Pi 4:** choose username, password, computer name, Wi-Fi and apps, pick the SD card, press Write. It downloads the image itself, asks for your administrator password, writes the card, and the Pi applies your choices on first boot.
- **LilyGO T-HMI:** plug in with USB, choose **T-HMI Hub firmware** or **MicroPythonOS** (official, supports the T-HMI, has an app store), pick the port, press Flash.
- **Manage my Pi:** shows which apps are running and opens them.

If something fails the app shows the reason; **Open problem log** shows details (also in `~/.cache/thmi-installer/log.txt`).

The Pi disk image (`thmi-pi-os.img.xz`, Releases -> "Pi 4 image (latest)") is the "ISO" for the Pi; it can also be written with Raspberry Pi Imager. There is no x86 PC ISO yet.

## One-click Pi installer (inside Raspberry Pi Imager)
In Raspberry Pi Imager open *App Options -> Content Repository -> Use custom repository* and paste
`https://github.com/elijah-code-5/thmi-pi-os/releases/latest/download/os-list.json`.
"T-HMI Hub (Pi 4)" then appears in the OS list and Imager downloads and flashes it, including your Wi-Fi settings.
(Or download the image from Releases and use *Use custom*.)

## Cloud storage, Home Assistant, laptop app
After the Pi boots, open `http://thmi-hub.local` (or the IP shown on its desktop) on any device. This is the Hub page: it links to
- **Cloud storage (Nextcloud)**, port 8080, login `admin` / `thmihub-cloud` (change it)
- **Home Assistant**, port 8123 (create your account on first visit)

First boot downloads about 1.5 GB, so those two show "starting" for ~10 minutes. A background job re-adds the Pi's current IP to Nextcloud's trusted addresses every 2 minutes, which fixes the usual "untrusted domain / IP not working" error.
Laptop: open the Hub page in Chrome/Edge and choose *Install app*, and install the official Nextcloud desktop app (nextcloud.com/install) to sync folders. Phones: Nextcloud and Home Assistant apps.

## What works / honest status
Everything here is **untested on real hardware**: expect first-run fixes.

| Feature | How |
| --- | --- |
| Music from microSD | T-HMI sends the file to the Pi; the Pi plays it to Bluetooth headphones (the T-HMI's ESP32-S3 has no classic Bluetooth). |
| File storage | Browse the SD card on the T-HMI; Samba share on the Pi. |
| Notes | Finger drawing on the T-HMI, saved as pages on the SD card (raw images, not handwriting recognition). |
| YouTube / video | Pi plays on a virtual screen; T-HMI shows it at 320x240 (`/api/youtube?url=`). |
| Games | RetroArch on the Pi, ROMs in `/srv/roms` (`/api/game?rom=`); streaming works, touch controls from T-HMI are not wired yet. |
| Robot | T-HMI buttons call the Pi, which calls the robot at `robot_ip` (set in `/etc/thmi-hub/config.json`). The robot needs firmware answering `/cmd?c=forward|back|left|right|stop`. |
| Virtual memory | zram swap on the Pi; PSRAM frame buffers on the T-HMI. |
| Nextcloud, Home Assistant | Run in Docker on the Pi (see above). Open Media Vault is not included (Nextcloud + Samba cover storage). |

## Check first
`firmware/src/pins.h` was written from memory of the T-HMI schematic. If touch, SD or power fail, compare it with LilyGO's official pin file.


## Phone OS for the T-HMI (recommended)

The installer's default T-HMI option flashes MicroPythonOS 0.20.0 plus three apps already installed:
**Robot** (hold the arrows to drive; gear = robot address), **Pi Hub** (finds the Pi by itself, starts games/YouTube/music)
and **My Apps** (installs and auto-updates apps published in this repo's `apps-latest` release).
Join Wi-Fi once in Settings > Wi-Fi on the device. Apps live in `apps/<name>/`; push a change (bump `version` in
`MANIFEST.JSON`) and the `apps` workflow republishes them; devices pick it up on the next boot with Wi-Fi. No reflashing.
The stock MicroPythonOS app store (BadgeHub) is there too for community apps.
