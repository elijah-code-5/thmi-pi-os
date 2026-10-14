# Run with HEAPSIZE=32M. Runs under the MicroPythonOS *unix* binary:  lvgl_micropy_unix mkfs_image.py STAGE_DIR OUT.bin
# Packs STAGE_DIR into a LittleFS image for the T-HMI "vfs" partition (0x720000, 0x8e0000 bytes, 4096-byte blocks).
import os, sys, vfs

BLOCK, COUNT = 4096, 2272


class Dev:
    def __init__(self):
        self.d = bytearray(BLOCK * COUNT)
    def readblocks(self, n, buf, off=0):
        o = n * BLOCK + off
        buf[:] = self.d[o:o + len(buf)]
    def writeblocks(self, n, buf, off=None):
        o = n * BLOCK + (off or 0)
        self.d[o:o + len(buf)] = buf
    def ioctl(self, op, arg):
        if op == 4:
            return COUNT
        if op == 5:
            return BLOCK
        if op == 6:
            o = arg * BLOCK
            self.d[o:o + BLOCK] = b"\xff" * BLOCK
        return 0


def copy_tree(fs_root, src, dst):
    for name in sorted(os.listdir(src)):
        s, d = src + "/" + name, dst + "/" + name
        if os.stat(s)[0] & 0x4000:
            os.mkdir(d)
            copy_tree(fs_root, s, d)
        else:
            with open(s, "rb") as f, open(d, "wb") as g:
                while True:
                    c = f.read(2048)
                    if not c:
                        break
                    g.write(c)


stage, out = sys.argv[1], sys.argv[2]
dev = Dev()
dev.d[:] = b"\xff" * len(dev.d)
vfs.VfsLfs2.mkfs(dev, readsize=256, progsize=256)
fs = vfs.VfsLfs2(dev, readsize=256, progsize=256)
vfs.mount(fs, "/img")
copy_tree("/img", stage, "/img")
vfs.umount("/img")
with open(out, "wb") as f:
    f.write(dev.d)
# verify by mounting the written bytes again
fs2 = vfs.VfsLfs2(dev, readsize=256, progsize=256)
vfs.mount(fs2, "/chk")
print("IMAGE OK:", sorted(os.listdir("/chk")), len(dev.d), "bytes")
