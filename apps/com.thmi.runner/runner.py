import logging

import lvgl as lv

from mpos import Activity, SharedPreferences

logger = logging.getLogger(__name__)

T = 16                      # tile size in pixels
ROWS = 12                   # level height in tiles (192 px)
VIEW_W, VIEW_H = 240, 192
PW, PH = 12, 14             # player box
SPEED, GRAV, JUMP, MAXFALL = 2.2, 0.5, -6.6, 8.0
GROUND = 10                 # first ground row

# gaps, platforms (row, c0, c1), coins (row, c0, c1), enemies (col, row), spikes (col), flag col
LEVELS = (
    dict(w=70, gaps=((24, 26), (46, 48)), plats=((7, 12, 15), (6, 31, 35), (7, 52, 56)),
         coins=((6, 12, 15), (5, 31, 35), (8, 18, 20), (6, 52, 56), (8, 40, 42)),
         enemies=((20, 9), (38, 9), (58, 9)), spikes=(), flag=66),
    dict(w=90, gaps=((14, 16), (30, 32), (52, 54), (70, 72)),
         plats=((7, 8, 11), (6, 20, 23), (5, 36, 40), (7, 45, 48), (6, 60, 64), (7, 76, 80)),
         coins=((6, 8, 11), (5, 20, 23), (4, 36, 40), (6, 45, 48), (5, 60, 64), (6, 76, 80), (8, 28, 29)),
         enemies=((5, 9), (22, 9), (42, 9), (58, 9), (84, 9)), spikes=(26, 27, 38, 66), flag=86),
    dict(w=110, gaps=((10, 12), (22, 24), (38, 40), (50, 52), (66, 68), (84, 86), (96, 98)),
         plats=((7, 15, 18), (6, 27, 30), (5, 43, 47), (7, 56, 60), (6, 72, 76), (5, 90, 94)),
         coins=((6, 15, 18), (5, 27, 30), (4, 43, 47), (6, 56, 60), (5, 72, 76), (4, 90, 94), (8, 23, 24)),
         enemies=((6, 9), (13, 9), (32, 9), (45, 9), (61, 9), (74, 9), (90, 9), (102, 9)), spikes=(35, 64, 80), flag=106),
)


def build_grid(spec):
    """Return a list of ROWS strings. '#' ground, '=' brick platform, '^' spike, ' ' air."""
    w = spec["w"]
    g = [[" "] * w for _ in range(ROWS)]
    for r in (GROUND, GROUND + 1):
        for c in range(w):
            g[r][c] = "#"
    for c0, c1 in spec["gaps"]:
        for r in (GROUND, GROUND + 1):
            for c in range(c0, c1 + 1):
                g[r][c] = " "
    for r, c0, c1 in spec["plats"]:
        for c in range(c0, c1 + 1):
            g[r][c] = "="
    for c in spec["spikes"]:
        g[GROUND - 1][c] = "^"
    return ["".join(row) for row in g]


def _box(parent, x, y, w, h, color, radius=0):
    o = lv.obj(parent)
    o.set_size(w, h)
    o.set_pos(x, y)
    o.set_style_bg_color(lv.color_hex(color), lv.PART.MAIN)
    o.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
    o.set_style_border_width(0, lv.PART.MAIN)
    o.set_style_radius(radius, lv.PART.MAIN)
    o.set_style_pad_all(0, lv.PART.MAIN)
    o.remove_flag(lv.obj.FLAG.SCROLLABLE)
    o.remove_flag(lv.obj.FLAG.CLICKABLE)
    return o


class Runner(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.runner")
        self.timer = None
        self.left = self.right = self.jump_down = False
        self.jump_req = False
        self.level = 0
        self.lives = 3
        self.coins = 0
        self.world = None
        self.state = "play"

        screen = lv.obj()
        screen.remove_flag(lv.obj.FLAG.SCROLLABLE)
        screen.set_style_pad_all(0, lv.PART.MAIN)
        self.screen = screen

        self.hud = lv.label(screen)
        self.hud.set_style_text_font(lv.font_montserrat_14, lv.PART.MAIN)
        self.hud.align(lv.ALIGN.TOP_LEFT, 4, 4)

        self.view = _box(screen, 0, 24, VIEW_W, VIEW_H, 0x8CD2F5)
        self.msg = lv.label(self.view)
        self.msg.set_width(220)
        self.msg.set_long_mode(lv.label.LONG_MODE.WRAP)
        self.msg.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.PART.MAIN)
        self.msg.set_style_text_font(lv.font_montserrat_20, lv.PART.MAIN)
        self.msg.align(lv.ALIGN.CENTER, 0, 0)

        self._button(screen, lv.SYMBOL.LEFT, 4, 70, "left")
        self._button(screen, lv.SYMBOL.RIGHT, 78, 70, "right")
        self._button(screen, "JUMP", 156, 80, "jump")
        self.start_level(0)
        self.setContentView(screen)

    def _button(self, screen, text, x, w, name):
        b = lv.button(screen)
        b.set_size(w, 90)
        b.set_pos(x, 224)
        for ev, val in ((lv.EVENT.PRESSED, True), (lv.EVENT.RELEASED, False), (lv.EVENT.PRESS_LOST, False)):
            b.add_event_cb(lambda e, n=name, v=val: self._set(n, v), ev, None)
        l = lv.label(b)
        l.set_text(text)
        l.set_style_text_font(lv.font_montserrat_24, lv.PART.MAIN)
        l.center()

    def _set(self, name, val):
        if name == "left":
            self.left = val
        elif name == "right":
            self.right = val
        else:
            if val and not self.jump_down:
                self.jump_req = True
            self.jump_down = val

    # ---- lifecycle ----
    def onResume(self, screen):
        super().onResume(screen)
        if self.timer is None:
            self.timer = lv.timer_create(lambda t: self.step(), 33, None)

    def onPause(self, screen):
        self.left = self.right = self.jump_down = False
        if self.timer is not None:
            try:
                self.timer.delete()
            except Exception:
                pass
            self.timer = None
        super().onPause(screen)

    # ---- level ----
    def start_level(self, n):
        self.level = n
        spec = LEVELS[n]
        self.grid = build_grid(spec)
        self.W = spec["w"]
        if self.world is not None:
            self.world.delete()
        self.world = _box(self.view, 0, 0, self.W * T, VIEW_H, 0x8CD2F5)
        self.msg.move_foreground()
        # ground and brick runs become single wide boxes
        for r, line in enumerate(self.grid):
            c = 0
            while c < self.W:
                ch = line[c]
                if ch in "#=":
                    c0 = c
                    while c < self.W and line[c] == ch:
                        c += 1
                    _box(self.world, c0 * T, r * T, (c - c0) * T, T, 0x8B5A2B if ch == "#" else 0xD08030)
                    if ch == "#" and r == GROUND:
                        _box(self.world, c0 * T, r * T, (c - c0) * T, 4, 0x3CB043)
                else:
                    if ch == "^":
                        _box(self.world, c * T + 1, r * T + 6, T - 2, 10, 0x777777)
                    c += 1
        self.coin_list = []
        for r, c0, c1 in spec["coins"]:
            for c in range(c0, c1 + 1):
                o = _box(self.world, c * T + 4, r * T + 4, 8, 8, 0xFFC800, 4)
                self.coin_list.append([c * T + 4, r * T + 4, o, True])
        self.enemies = []
        for c, r in spec["enemies"]:
            o = _box(self.world, c * T + 1, r * T + 2, 14, 14, 0x7030A0, 5)
            self.enemies.append([c * T + 1.0, r * T + 2.0, -0.6, o, True])
        fx = spec["flag"] * T
        _box(self.world, fx + 6, GROUND * T - 48, 3, 48, 0xEEEEEE)
        _box(self.world, fx + 9, GROUND * T - 48, 14, 10, 0xE03030)
        self.flag_x = fx
        self.player = _box(self.world, 0, 0, PW, PH, 0x2ECC71, 5)
        for ex in (2, 8):
            _box(self.player, ex, 3, 3, 3, 0xFFFFFF, 1)
        self.respawn()
        self.show("Level %d" % (n + 1), 900)
        self.hud_update()

    def respawn(self):
        self.px, self.py = 2 * T + 2.0, (GROUND - 1) * T - 2.0
        self.vx = self.vy = 0.0
        self.on_ground = False
        self.invuln = 40
        self.state = "play"

    def show(self, text, ms=0):
        self.msg.set_text(text)
        self.msg_frames = ms // 33 if ms else -1

    def hud_update(self):
        self.hud.set_text("Level %d/3   Coins %d   Lives %d" % (self.level + 1, self.coins, self.lives))

    # ---- physics ----
    def solid(self, cx, cy):
        if cx < 0 or cx >= self.W:
            return True
        if cy < 0 or cy >= ROWS:
            return False
        return self.grid[cy][cx] in "#="

    def step(self):
        if self.msg_frames > 0:
            self.msg_frames -= 1
            if self.msg_frames == 0:
                self.msg.set_text("")
        if self.state == "over":
            if self.jump_req:
                self.jump_req = False
                self.lives, self.coins = 3, 0
                self.start_level(0)
            return
        if self.state == "won":
            if self.jump_req:
                self.jump_req = False
                self.lives, self.coins = 3, 0
                self.start_level(0)
            return
        if self.invuln > 0:
            self.invuln -= 1
        # horizontal
        self.vx = (SPEED if self.right else 0) - (SPEED if self.left else 0)
        if self.jump_req:
            if self.on_ground:
                self.vy = JUMP
            self.jump_req = False
        if not self.jump_down and self.vy < -2.5:
            self.vy = -2.5                      # short hop when the button is let go
        self.vy = min(self.vy + GRAV, MAXFALL)
        # move x
        nx = self.px + self.vx
        if self.vx != 0:
            edge = int(nx + PW - 0.01) if self.vx > 0 else int(nx)
            for cy in range(int(self.py) // T, int(self.py + PH - 0.01) // T + 1):
                if self.solid(edge // T, cy):
                    nx = (edge // T) * T - PW if self.vx > 0 else (edge // T + 1) * T
                    break
        self.px = nx
        # move y
        ny = self.py + self.vy
        self.on_ground = False
        if self.vy > 0:
            by = int(ny + PH - 0.01) // T
            for cx in range(int(self.px) // T, int(self.px + PW - 0.01) // T + 1):
                if self.solid(cx, by):
                    ny = by * T - PH
                    self.vy = 0.0
                    self.on_ground = True
                    break
        elif self.vy < 0:
            ty = int(ny) // T
            for cx in range(int(self.px) // T, int(self.px + PW - 0.01) // T + 1):
                if self.solid(cx, ty):
                    ny = (ty + 1) * T
                    self.vy = 0.0
                    break
        self.py = ny
        if self.py > VIEW_H + 8:
            return self.hurt()
        # spikes
        cx0, cx1 = int(self.px) // T, int(self.px + PW - 0.01) // T
        cy = int(self.py + PH - 0.01) // T
        if 0 <= cy < ROWS:
            for cx in range(cx0, cx1 + 1):
                if 0 <= cx < self.W and self.grid[cy][cx] == "^" and self.py + PH > cy * T + 7:
                    return self.hurt()
        # coins
        for c in self.coin_list:
            if c[3] and abs(c[0] - self.px) < 10 and abs(c[1] - self.py) < 12:
                c[3] = False
                c[2].add_flag(lv.obj.FLAG.HIDDEN)
                self.coins += 1
                self.hud_update()
        # enemies
        for e in self.enemies:
            if not e[4]:
                continue
            nxe = e[0] + e[2]
            ahead = int(nxe + (14 if e[2] > 0 else 0)) // T
            if self.solid(ahead, int(e[1] + 7) // T) or not self.solid(ahead, int(e[1] + 15) // T):
                e[2] = -e[2]
            else:
                e[0] = nxe
            e[3].set_pos(int(e[0]), int(e[1]))
            if abs(e[0] + 7 - (self.px + PW / 2)) < 11 and abs(e[1] + 7 - (self.py + PH / 2)) < 11:
                if self.vy > 0.5 and self.py + PH - 6 < e[1] + 7:
                    e[4] = False
                    e[3].add_flag(lv.obj.FLAG.HIDDEN)
                    self.vy = -4.5
                    self.coins += 1
                    self.hud_update()
                elif self.invuln == 0:
                    return self.hurt()
        # flag
        if self.px + PW > self.flag_x and self.px < self.flag_x + 24:
            return self.finish_level()
        # draw
        self.player.set_pos(int(self.px), int(self.py))
        self.player.set_style_bg_opa(lv.OPA._50 if self.invuln % 6 > 2 else lv.OPA.COVER, lv.PART.MAIN)
        cam = max(0, min(int(self.px) - 100, self.W * T - VIEW_W))
        self.world.set_x(-cam)

    def hurt(self):
        self.lives -= 1
        self.hud_update()
        if self.lives <= 0:
            self.state = "over"
            self.show("Game over\nTap JUMP to play again")
        else:
            self.respawn()
        return None

    def finish_level(self):
        best = self.prefs.get_int("best", 0)
        if self.level + 1 > best:
            self.prefs.edit().put_int("best", self.level + 1).commit()
        if self.level + 1 < len(LEVELS):
            self.start_level(self.level + 1)
        else:
            self.state = "won"
            self.show("You win!\nCoins: %d\nTap JUMP to replay" % self.coins)
