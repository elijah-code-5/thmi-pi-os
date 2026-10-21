"""Pocket-calculator state machine (no screen code)."""


class Calc:
    def __init__(self):
        self.clear()

    def clear(self):
        self.cur, self.acc, self.op, self.fresh, self.error = "0", None, None, True, False

    def _val(self):
        return float(self.cur)

    @staticmethod
    def fmt(v):
        if v == int(v) and abs(v) < 1e12:
            return str(int(v))
        s = "%.8g" % v
        return s

    def digit(self, d):
        if self.error:
            self.clear()
        if self.fresh:
            self.cur, self.fresh = ("0." if d == "." else d), False
        elif d == "." and "." in self.cur:
            return
        else:
            self.cur += d
        if len(self.cur) > 12:
            self.cur = self.cur[:12]

    def _apply(self):
        if self.op is None or self.acc is None:
            return
        a, b = self.acc, self._val()
        try:
            r = {"+": a + b, "-": a - b, "*": a * b, "/": a / b}[self.op]
        except ZeroDivisionError:
            self.error, self.cur = True, "Error"
            return
        self.cur = self.fmt(r)

    def operator(self, op):
        if self.error:
            return
        if not self.fresh:
            self._apply()
        if self.error:
            return
        self.acc, self.op, self.fresh = self._val(), op, True

    def equals(self):
        if self.error:
            return
        self._apply()
        self.acc, self.op, self.fresh = None, None, True

    def negate(self):
        if not self.error and self.cur != "0":
            self.cur = self.cur[1:] if self.cur.startswith("-") else "-" + self.cur

    def percent(self):
        if not self.error:
            self.cur, self.fresh = self.fmt(self._val() / 100.0), True

    def backspace(self):
        if self.error:
            self.clear()
        elif not self.fresh:
            self.cur = self.cur[:-1] or "0"
            if self.cur == "-":
                self.cur = "0"
