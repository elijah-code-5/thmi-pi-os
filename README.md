# T-HMI + Raspberry Pi 4 Hub

One system: a **Raspberry Pi 4** is the brain, a **LilyGO T-HMI** is the handheld touch controller, and the **robot** is driven by the Pi.

## Get it running (use the Installer app)

1. Open this repo's **Releases**, download **thmi-installer-x86_64.AppImage** (tag `installer-latest`), make it executable (right-click -> Properties -> Allow executing) and double-click it. Linux x86_64 only for now (no Windows/Mac build yet).
2. Pick **Raspberry Pi 4** or **LilyGO T-HMI**.
   - **Pi:** choose your own username, password, computer name, Wi-Fi and the apps to install (Nextcloud, Home Assistant, Jellyfin, Syncthing, Vaultwarden, Uptime Kuma, Portainer), then pick the SD card and press Write. The app downloads the newest image, asks for your administrator password to write the card, and stores your choices on the card; the Pi applies them on first boot.
   - **T-HMI:** plug it in with USB, pick the port, press Flash. Then join the `THMI-Setup` Wi-Fi from your phone to connect it.
3. Put the SD card in the Pi, power it on, open `http://<computer name>.local` from any device.

No terminal needed. (The old browser flasher and Raspberry Pi Imager route below still work as alternatives.)

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
