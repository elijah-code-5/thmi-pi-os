import json
import logging
import os

import lvgl as lv

from mpos import Activity, InputManager, TaskManager

import thmi_net
import thmi_ui

logger = logging.getLogger(__name__)

DIR = "data/com.thmi.notes"
CANVAS_Y = 36
CANVAS_H = 244
COLORS = (("Pen", 0x000000, 2), ("Blue", 0x1E50DC, 2), ("Red", 0xDC2828, 2), ("Erase", 0xFFFFFF, 9))


def _mkdirs(path):
    acc = ""
    for part in path.split("/"):
        acc = (acc + "/" + part) if acc else part
        try:
            os.mkdir(acc)
        except OSError:
            pass


class Notes(Activity):

    def onCreate(self):
        _mkdirs(DIR)
        self.pages = self._list_pages()
        self.cur = 0
        self.strokes = []
        self.pen = COLORS[0]
        self.active = None
        self.last = None
        self.syncing = False
        self.host = None

        screen = lv.obj()
        screen.remove_flag(lv.obj.FLAG.SCROLLABLE)
        screen.set_style_pad_all(0, lv.PART.MAIN)

        self.title = lv.label(screen)
        self.title.set_style_text_font(lv.font_montserrat_20, lv.PART.MAIN)
        self.title.align(lv.ALIGN.TOP_LEFT, 4, 6)
        for i, (sym, cb) in enumerate(((lv.SYMBOL.LEFT, self._prev), (lv.SYMBOL.RIGHT, self._next), (lv.SYMBOL.PLUS, self._new))):
            b = lv.button(screen)
            b.set_size(44, 32)
            b.align(lv.ALIGN.TOP_RIGHT, -2 - (2 - i) * 46, 2)
            b.add_event_cb(cb, lv.EVENT.CLICKED, None)
            l = lv.label(b)
            l.set_text(sym)
            l.center()

        self.canvas = lv.canvas(screen)
        self.canvas.set_size(240, CANVAS_H)
        self.canvas.align(lv.ALIGN.TOP_LEFT, 0, CANVAS_Y)
        self.buf = bytearray(240 * CANVAS_H * 4)
        self.canvas.set_buffer(self.buf, 240, CANVAS_H, lv.COLOR_FORMAT.NATIVE)
        self.canvas.fill_bg(lv.color_white(), lv.OPA.COVER)
        self.canvas.add_flag(lv.obj.FLAG.CLICKABLE)
        self.canvas.add_event_cb(self._touch, lv.EVENT.ALL, None)
        self.layer = lv.layer_t()
        self.canvas.init_layer(self.layer)

        # toolbar: 4 pens + undo + clear
        w = 40
        tools = [(c[0], (lambda e, c=c: self._set_pen(c))) for c in COLORS] + [(lv.SYMBOL.LOOP, self._undo), (lv.SYMBOL.TRASH, self._clear)]
        for i, (txt, cb) in enumerate(tools):
            b = lv.button(screen)
            b.set_size(w - 2, 38)
            b.align(lv.ALIGN.BOTTOM_LEFT, i * w + 1, -1)
            b.add_event_cb(cb, lv.EVENT.CLICKED, None)
            l = lv.label(b)
            l.set_text(txt)
            l.set_style_text_font(lv.font_montserrat_14, lv.PART.MAIN)
            l.center()
        self.setContentView(screen)
        if not self.pages:
            self._new(None)
        else:
            self._load(0)

    # ---- pages ----
    def _list_pages(self):
        try:
            return sorted(n for n in os.listdir(DIR) if n.endswith(".json"))
        except OSError:
            return []

    def _path(self):
        return DIR + "/" + self.pages[self.cur]

    def _load(self, idx):
        self.cur = idx
        self.strokes = []
        try:
            with open(self._path()) as f:
                self.strokes = json.load(f).get("strokes", [])
        except Exception as e:
            logger.warning("load page: %s", e)
        self._title()
        self._redraw()

    def _title(self):
        self.title.set_text("Notes %d/%d" % (self.cur + 1, len(self.pages)))

    def _save(self):
        try:
            with open(self._path(), "w") as f:
                json.dump({"strokes": self.strokes}, f)
        except Exception as e:
            logger.warning("save page: %s", e)
        if not self.syncing:
            TaskManager.create_task(self._sync())

    async def _sync(self):
        """Copy the current page to the Pi (best effort, silent)."""
        self.syncing = True
        try:
            if not self.host:
                self.host = await thmi_net.pi_host()
            if self.host:
                name = self.pages[self.cur]
                await thmi_net.post(self.host, "/api/notes/upload?name=%s" % thmi_net.quote(name), json.dumps({"strokes": self.strokes}).encode())
        except Exception as e:
            logger.info("notes sync skipped: %s", e)
        finally:
            self.syncing = False

    def _new(self, e):
        n = 1
        for p in self.pages:
            try:
                n = max(n, int(p.split("-")[1].split(".")[0]) + 1)
            except Exception:
                pass
        self.pages.append("note-%03d.json" % n)
        self.pages.sort()
        self.cur = self.pages.index("note-%03d.json" % n)
        self.strokes = []
        self._save()
        self._title()
        self._redraw()

    def _prev(self, e):
        if self.cur > 0:
            self._load(self.cur - 1)

    def _next(self, e):
        if self.cur < len(self.pages) - 1:
            self._load(self.cur + 1)

    # ---- tools ----
    def _set_pen(self, c):
        self.pen = c

    def _undo(self, e):
        if self.strokes:
            self.strokes.pop()
            self._redraw()
            self._save()

    def _clear(self, e):
        self.strokes = []
        self._redraw()
        self._save()

    # ---- drawing ----
    def _dot(self, x, y, color, r):
        d = lv.draw_rect_dsc_t()
        lv.draw_rect_dsc_t.init(d)
        d.bg_color = lv.color_hex(color)
        d.bg_opa = lv.OPA.COVER
        d.radius = lv.RADIUS_CIRCLE
        d.border_width = 0
        a = lv.area_t()
        a.x1 = x - r
        a.y1 = y - r
        a.x2 = x + r
        a.y2 = y + r
        lv.draw_rect(self.layer, d, a)

    def _segment(self, x0, y0, x1, y1, color, r):
        n = max(abs(x1 - x0), abs(y1 - y0)) // 2 + 1
        for i in range(n + 1):
            self._dot(x0 + (x1 - x0) * i // n, y0 + (y1 - y0) * i // n, color, r)

    def _redraw(self):
        self.canvas.fill_bg(lv.color_white(), lv.OPA.COVER)
        for color, r, pts in self.strokes:
            if len(pts) == 2:
                self._dot(pts[0], pts[1], color, r)
            for i in range(2, len(pts), 2):
                self._segment(pts[i - 2], pts[i - 1], pts[i], pts[i + 1], color, r)
        self.canvas.finish_layer(self.layer)

    def _touch(self, event):
        code = event.get_code()
        if code not in (lv.EVENT.PRESSED, lv.EVENT.PRESSING, lv.EVENT.RELEASED, lv.EVENT.PRESS_LOST):
            return
        if code in (lv.EVENT.RELEASED, lv.EVENT.PRESS_LOST):
            if self.active is not None:
                self.active = None
                self.last = None
                self._save()
            return
        x, y = InputManager.pointer_xy()
        y -= CANVAS_Y
        if x < 0 or y < 0 or y >= CANVAS_H:
            return
        if code == lv.EVENT.PRESSED or self.active is None:
            self.active = [self.pen[1], self.pen[2], [x, y]]
            self.strokes.append(self.active)
            self.last = (x, y)
            self._dot(x, y, self.pen[1], self.pen[2])
        else:
            lx, ly = self.last
            if abs(x - lx) + abs(y - ly) < 2:
                return
            self._segment(lx, ly, x, y, self.pen[1], self.pen[2])
            self.active[2].extend((x, y))
            self.last = (x, y)
        self.canvas.finish_layer(self.layer)
