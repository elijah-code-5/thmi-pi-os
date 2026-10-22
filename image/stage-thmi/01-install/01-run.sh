#!/bin/bash -e
install -d "${ROOTFS_DIR}/opt/thmi-hub" "${ROOTFS_DIR}/etc/thmi-hub" "${ROOTFS_DIR}/srv/roms" "${ROOTFS_DIR}/srv/thmi-hub"
cp -r files/* "${ROOTFS_DIR}/"
chmod +x "${ROOTFS_DIR}"/usr/local/bin/thmi-*
chown -R pi:pi "${ROOTFS_DIR}/opt/thmi-hub" 2>/dev/null || true
echo "thmi-hub" > "${ROOTFS_DIR}/etc/hostname"
# virtual memory: compressed RAM swap so 4 GB feels bigger
printf 'ALGO=zstd\nPERCENT=60\n' > "${ROOTFS_DIR}/etc/default/zramswap"
# virtual screen that the T-HMI streams (YouTube / games render here)
cat > "${ROOTFS_DIR}/etc/systemd/system/thmi-screen.service" <<'D'
[Unit]
Description=Virtual stream screen
[Service]
ExecStart=/usr/bin/Xvfb :1 -screen 0 1280x960x24
Restart=always
[Install]
WantedBy=multi-user.target
D
on_chroot << CHEOF
systemctl enable thmi-firstboot thmi-hub thmi-screen thmi-stack thmi-fix-cloud.timer thmi-ytdlp.timer thmi-net-watch thmi-omv avahi-daemon smbd nmbd zramswap docker
systemctl disable ssh 2>/dev/null || true
usermod -aG docker,bluetooth,audio pi
mkdir -p "${ROOTFS_DIR}/var/lib/systemd/linger" && touch "${ROOTFS_DIR}/var/lib/systemd/linger/pi"
chown -R pi:pi /srv/thmi-hub /srv/roms
echo "pi ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/010_pi-nopasswd
chmod 440 /etc/sudoers.d/010_pi-nopasswd
CHEOF
