import json
import os
import tkinter as tk

class NumbersModel:
    MIN_VALUE = 0
    MAX_VALUE = 100

    def __init__(self, file_name="numbers_model.json"):
        folder = os.path.dirname(os.path.abspath(__file__))
        self._file = os.path.join(folder, file_name)

        self._a, self._b, self._c = 0, 50, 100
        self._observers = []
        self._load()                    

    # -------------------- подписка / уведомления --------------------
    def add_observer(self, callback):
        self._observers.append(callback)

    def notify(self):
        for callback in self._observers:
            callback()

    # -------------------- чтение --------------------
    def get_a(self):
        return self._a

    def get_b(self):
        return self._b

    def get_c(self):
        return self._c

    def get_limits(self):
        """Границы модели - только здесь, форма их не выдумывает."""
        return self.MIN_VALUE, self.MAX_VALUE

    # -------------------- изменение --------------------
    def set_a(self, value):
        """Разрешающее поведение: A сохраняется, B и C подстраиваются."""
        new_a = self._clamp(value)
        new_b = max(self._b, new_a)
        new_c = max(self._c, new_b)
        return self._apply(new_a, new_b, new_c)

    def set_c(self, value):
        """Разрешающее поведение: C сохраняется, A и B подстраиваются."""
        new_c = self._clamp(value)
        new_b = min(self._b, new_c)
        new_a = min(self._a, new_b)
        return self._apply(new_a, new_b, new_c)

    def set_b(self, value):
        """Запрещающее поведение: если B выходит из [A, C] - откат."""
        value = self._clamp(value)
        if value < self._a or value > self._c:
            return False
        return self._apply(self._a, value, self._c)

    # -------------------- внутреннее --------------------
    def _clamp(self, value):
        return max(self.MIN_VALUE, min(self.MAX_VALUE, int(value)))

    def _apply(self, a, b, c):
        """Атомарное изменение: либо меняем все три сразу, либо ничего."""
        if (a, b, c) == (self._a, self._b, self._c):
            return False                    # ничего не изменилось - молчим
        self._a, self._b, self._c = a, b, c
        self._save()
        self.notify()                       # ровно ОДНО уведомление
        return True

    # -------------------- сохранение / загрузка --------------------
    def _save(self):
        try:
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump({"a": self._a, "b": self._b, "c": self._c}, f)
        except OSError:
            pass

    def _load(self):
        try:
            with open(self._file, "r", encoding="utf-8") as f:
                data = json.load(f)
            a = self._clamp(data["a"])
            b = self._clamp(data["b"])
            c = self._clamp(data["c"])
            if a > b:
                b = a
            if b > c:
                c = b
            self._a, self._b, self._c = a, b, c
        except (OSError, ValueError, KeyError, TypeError):
            pass                          

class App(tk.Tk):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.updating = False       # защита от рекурсии при обновлении виджетов
        self.refresh_count = 0

        self.title("ЛР3 ч.2 - MVC")
        self.resizable(False, False)

        lo, hi = model.get_limits()   # границы берём у модели

        self.entries = {}
        self.spins = {}
        self.scales = {}
        self.setters = {"a": model.set_a, "b": model.set_b, "c": model.set_c}

        rows = (("a", "A:"), ("b", "B:"), ("c", "C:"))
        for r, (key, title) in enumerate(rows):
            tk.Label(self, text=title, width=3, anchor="e").grid(row=r, column=0, padx=4, pady=4)

            e = tk.Entry(self, width=6, justify="center")
            e.grid(row=r, column=1, padx=4, pady=4)

            sp = tk.Spinbox(self, from_=lo, to=hi, width=6, justify="center",
                            command=lambda k=key: self._on_spin(k))
            sp.grid(row=r, column=2, padx=4, pady=4)

            sc = tk.Scale(self, from_=lo, to=hi, orient=tk.HORIZONTAL, length=230,
                          command=lambda v, k=key: self._on_scale(k, v))
            sc.grid(row=r, column=3, padx=4, pady=4)

            self.entries[key] = e
            self.spins[key] = sp
            self.scales[key] = sc

            for w in (e, sp):
                w.bind("<FocusOut>", lambda ev, k=key: self._on_entry(k))
                w.bind("<Return>", lambda ev, k=key: self._on_entry(k))

        self.counter = tk.Label(self, text="Обновлений формы: 0", anchor="w")
        self.counter.grid(row=3, column=0, columnspan=4, sticky="we", padx=4, pady=(2, 6))

        # подписываемся и просим у модели РОВНО ОДНО уведомление при запуске
        self.model.add_observer(self.refresh)
        self.model.notify()

    # ---------------- обработчики ввода ----------------
    def _on_entry(self, key):
        if self.updating:
            return
        text = self.entries[key].get().strip()
        try:
            value = int(text)
        except ValueError:              # пусто или не число - возвращаем как было
            self.refresh()
            return
        self._apply(key, value)

    def _on_spin(self, key):
        if self.updating:
            return
        try:
            value = int(float(self.spins[key].get()))
        except ValueError:
            self.refresh()
            return
        self._apply(key, value)

    def _on_scale(self, key, raw):
        if self.updating:
            return
        self._apply(key, int(float(raw)))

    def _apply(self, key, value):
        if not self.setters[key](value):
            # модель не изменилась (например, B вне [A, C]) - приводим виджеты к модели
            self.refresh()

    # ---------------- обновление формы ----------------
    def refresh(self):
        self.refresh_count += 1
        self.counter.config(text="Обновлений формы: %d" % self.refresh_count)

        self.updating = True
        try:
            values = (("a", self.model.get_a()),
                      ("b", self.model.get_b()),
                      ("c", self.model.get_c()))
            for key, value in values:
                e = self.entries[key]
                e.delete(0, tk.END)
                e.insert(0, str(value))

                sp = self.spins[key]
                sp.delete(0, tk.END)
                sp.insert(0, str(value))

                self.scales[key].set(value)
        finally:
            self.updating = False


if __name__ == "__main__":
    App(NumbersModel()).mainloop()
