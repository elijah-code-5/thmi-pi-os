# T-HMI + Raspberry Pi 4 Hub

One system: a **Raspberry Pi 4** is the brain, a **LilyGO T-HMI** is the handheld touch controller, and the **robot** is driven by the Pi.

## Get it running (no terminal)

**1. Flash the T-HMI** – open the flasher page (GitHub Pages for this repo, `https://elijah-code-5.github.io/thmi-pi-os/`) in Chrome, plug in the T-HMI, click the button.
First time only: in the repo go to *Settings → Pages → Source: GitHub Actions*.

**2. Flash the Pi** – open the repo's *Releases*, download the newest `thmi-pi-os` image, write it with Raspberry Pi Imager (*Use custom*). Put your Wi-Fi in Imager's settings. Boot it: the desktop shows its IP address.

**3. Set up the T-HMI Wi-Fi** – on your phone join the `THMI-Setup` Wi-Fi and choose your home network.

Default Pi login: user `pi`, password `thmihub` (change it).

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
| Home Assistant, Open Media Vault, Nextcloud | **Not in this first version.** Docker is installed so they can be added next. |

## Check first
`firmware/src/pins.h` was written from memory of the T-HMI schematic. If touch, SD or power fail, compare it with LilyGO's official pin file.
