#!/usr/bin/env python3
"""Runs as root (via pkexec). Writes a .img.xz to an SD card, then drops thmi-setup.json on its boot partition.
Usage: write_sd.py IMAGE.img.xz DEVICE SETUP.json
Prints lines: PROGRESS <0-100>, STATUS <text>, DONE, ERROR <text>.
If DEVICE is a regular file (testing), safety checks and the boot-partition step are skipped."""
import json, lzma, os, stat, subprocess, sys, tempfile, time

def say(*a):
    print(*a, flush=True)

def fail(msg):
    say("ERROR", msg); sys.exit(1)

def lsblk(dev):
    out = subprocess.run(["lsblk", "-J", "-o", "NAME,PATH,TYPE,RM,HOTPLUG,TRAN,MOUNTPOINTS", dev],
                         capture_output=True, text=True)
    return json.loads(out.stdout)["blockdevices"][0]

def mountpoints(node):
    mps = [m for m in (node.get("mountpoints") or []) if m]
    for c in node.get("children", []) or []:
        mps += mountpoints(c)
    return mps

def check_safe(dev):
    node = lsblk(dev)
    if node["type"] != "disk":
        fail("target is not a whole disk")
    removable = node.get("rm") in (True, "1", 1) or node.get("hotplug") in (True, "1", 1) or node.get("tran") in ("usb", "mmc")
    if not removable:
        fail("target is not a removable drive; refusing to write")
    for m in mountpoints(node):
        if m in ("/", "/boot", "/boot/efi", "/home", "/usr", "/var"):
            fail("target holds your system; refusing to write")
    return node

def part_path(dev, n):
    return f"{dev}p{n}" if dev[-1].isdigit() else f"{dev}{n}"

def main():
    if len(sys.argv) != 4:
        fail("usage: write_sd.py IMAGE DEVICE SETUP.json")
    img, dev, setup = sys.argv[1:]
    is_file = os.path.isfile(dev)
    if not is_file:
        if not stat.S_ISBLK(os.stat(dev).st_mode):
            fail("target is not a block device")
        node = check_safe(dev)
        for m in mountpoints(node):
            subprocess.run(["umount", m])
    total = os.path.getsize(img)
    say("STATUS Writing image (do not remove the card)")
    with open(img, "rb") as raw, lzma.LZMAFile(raw) as dec, open(dev, "r+b" if is_file else "wb") as out:
        last = -1
        while True:
            chunk = dec.read(4 * 1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            pct = int(raw.tell() * 100 / total)
            if pct != last:
                say("PROGRESS", pct); last = pct
        out.flush(); os.fsync(out.fileno())
    if is_file:
        say("DONE"); return
    say("STATUS Finishing")
    subprocess.run(["sync"])
    subprocess.run(["blockdev", "--rereadpt", dev])
    subprocess.run(["udevadm", "settle"])
    boot = part_path(dev, 1)
    for _ in range(20):
        if os.path.exists(boot):
            break
        time.sleep(0.5)
    else:
        fail("could not find the card's boot partition after writing")
    mnt = tempfile.mkdtemp(prefix="thmi-boot-")
    r = subprocess.run(["mount", "-t", "vfat", boot, mnt], capture_output=True, text=True)
    if r.returncode:
        fail("could not mount boot partition: " + r.stderr.strip())
    try:
        with open(os.path.join(mnt, "thmi-setup.json"), "w") as f:
            f.write(open(setup).read())
        os.chmod(os.path.join(mnt, "thmi-setup.json"), 0o600)
        open(os.path.join(mnt, "ssh"), "w").close()
    finally:
        subprocess.run(["sync"]); subprocess.run(["umount", mnt]); os.rmdir(mnt)
    say("PROGRESS 100"); say("DONE")

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        fail(str(e))
