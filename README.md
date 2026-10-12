# T-HMI + Raspberry Pi 4 Hub

One system: a **Raspberry Pi 4** is the brain, a **LilyGO T-HMI** is the handheld touch controller, and the **robot** is driven by the Pi.

## Get it running (no terminal)

**1. Flash the T-HMI** – open the flasher page (GitHub Pages for this repo, `https://elijah-code-5.github.io/thmi-pi-os/`) in Chrome, plug in the T-HMI, click the button.
First time only: in the repo go to *Settings → Pages → Source: GitHub Actions*.

**2. Flash the Pi** – open the repo's *Releases*, download the newest `thmi-pi-os` image, write it with Raspberry Pi Imager (*Use custom*). Put your Wi-Fi in Imager's settings. Boot it: the desktop shows its IP address.

**3. Set up the T-HMI Wi-Fi** – on your phone join the `THMI-Setup` Wi-Fi and choose your home network.

Default Pi login: user `pi`, password `thmihub` (change it).

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
