"""The desktop must leave busy state even if an Excel export fails."""
from pathlib import Path
from types import SimpleNamespace

import polished_gui


class FakeWorkbench:
    _busy = False

    def __init__(self, path: Path):
        self.characteristics = [object()]
        self.path = path
        self.messages = []
        self.callbacks = []

    def _validate_inputs(self):
        return self.path / "print.pdf", self.path / "template.xlsx", self.path

    def set_busy(self, busy):
        self._busy = busy

    def log(self, message):
        self.messages.append(message)

    def after(self, delay, callback):
        self.callbacks.append(callback)

    def _show_error(self, title, message):
        self.set_busy(False)
        self.messages.append(f"{title}: {message}")


def test_export_exception_is_delivered_after_worker_exception_scope_closes(monkeypatch, tmp_path):
    """Tk callbacks run later, after Python clears captured exception names."""
    app = FakeWorkbench(tmp_path)

    def fail(*_args, **_kwargs):
        raise ValueError("synthetic template capacity error")

    monkeypatch.setattr(polished_gui, "fill_fai_template_pages", fail)
    # Make thread work synchronous while deferring the Tk callback.
    monkeypatch.setattr(
        polished_gui.threading, "Thread",
        lambda target, daemon: SimpleNamespace(start=target),
    )

    polished_gui.EzFairApp.generate_outputs(app)
    assert app._busy
    assert len(app.callbacks) == 1
    app.callbacks.pop()()
    assert not app._busy
    assert any("synthetic template capacity error" in text for text in app.messages)
