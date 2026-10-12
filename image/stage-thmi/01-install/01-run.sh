#!/bin/bash -e
install -d "${ROOTFS_DIR}/opt/thmi-hub" "${ROOTFS_DIR}/etc/thmi-hub" "${ROOTFS_DIR}/srv/roms" "${ROOTFS_DIR}/srv/thmi-hub"
cp -r files/* "${ROOTFS_DIR}/"
chmod +x "${ROOTFS_DIR}"/usr/local/bin/thmi-*
echo "thmi-hub" > "${ROOTFS_DIR}/etc/hostname"
# virtual memory: compressed RAM swap so 4 GB feels bigger
printf 'ALGO=zstd\nPERCENT=60\n' > "${ROOTFS_DIR}/etc/default/zramswap"
# show the IP address automatically at desktop start
mkdir -p "${ROOTFS_DIR}/etc/xdg/autostart"
cat > "${ROOTFS_DIR}/etc/xdg/autostart/thmi-show-ip.desktop" <<'D'
[Desktop Entry]
Type=Application
Name=Show IP
Exec=/usr/local/bin/thmi-show-ip
D
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
systemctl enable thmi-hub thmi-screen thmi-stack thmi-fix-cloud.timer avahi-daemon zramswap ssh docker
usermod -aG docker,bluetooth,audio pi
mkdir -p "${ROOTFS_DIR}/var/lib/systemd/linger" && touch "${ROOTFS_DIR}/var/lib/systemd/linger/pi"
chown -R pi:pi /srv/thmi-hub /srv/roms
CHEOF
