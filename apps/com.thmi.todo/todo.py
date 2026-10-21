import json

import lvgl as lv

from mpos import Activity, MposKeyboard, SharedPreferences

import thmi_ui


class Todo(Activity):

    def onCreate(self):
        self.prefs = SharedPreferences("com.thmi.todo")
        try:
            self.items = json.loads(self.prefs.get_string("items", "[]"))
        except Exception:
            self.items = []
        sc = thmi_ui.screen()
        thmi_ui.header(sc, "To-Do", lv.SYMBOL.TRASH, lambda e: self.clean())
        self.input = lv.textarea(sc)
        self.input.set_one_line(True)
        self.input.set_placeholder_text("New task...")
        self.input.set_size(232, 36)
        self.input.set_pos(4, 36)
        self.input.add_event_cb(lambda e: self.kb.remove_flag(lv.obj.FLAG.HIDDEN), lv.EVENT.CLICKED, None)
        self.box = thmi_ui.list_box(sc, 78, 0)
        self.kb = MposKeyboard(sc)
        self.kb.set_textarea(self.input)
        self.kb.add_event_cb(self._add, lv.EVENT.READY, None)
        self.kb.add_flag(lv.obj.FLAG.HIDDEN)
        self.setContentView(sc)
        self.draw()

    def save(self):
        self.prefs.edit().put_string("items", json.dumps(self.items)).commit()

    def _add(self, e):
        t = self.input.get_text().strip()
        self.kb.add_flag(lv.obj.FLAG.HIDDEN)
        if t:
            self.items.append([t, 0])
            self.input.set_text("")
            self.save()
            self.draw()

    def clean(self):
        self.items = [i for i in self.items if not i[1]]
        self.save()
        self.draw()

    def tick(self, i):
        self.items[i][1] = 0 if self.items[i][1] else 1
        self.save()
        self.draw()

    def draw(self):
        self.box.clean()
        for i, (t, done) in enumerate(self.items):
            thmi_ui.row(self.box, ("%s  %s" % (lv.SYMBOL.OK, t)) if done else ("o  " + t), lambda e, i=i: self.tick(i))
        if not self.items:
            thmi_ui.text(self.box, "Nothing to do. Type a task above.", 0, 0, lv.font_montserrat_14)
