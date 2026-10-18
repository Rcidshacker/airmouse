"""Test doubles for the gesture processors."""

from __future__ import annotations

from types import SimpleNamespace


class FakeClock:
    """Manually advanced replacement for ``time.perf_counter``."""

    def __init__(self, start: float = 100.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds

    def as_time_module(self) -> SimpleNamespace:
        """Object to monkeypatch over a module's ``time`` import."""
        return SimpleNamespace(perf_counter=self)


class FakeActuator:
    """
    Records every call a gesture processor makes, in order, together with the
    cursor position at that moment. Tracks held buttons/keys so tests can
    assert that nothing is left pressed.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, tuple[int, int]]] = []
        self.pos: tuple[int, int] = (0, 0)
        self.held: set[str] = set()

    def _record(self, name: str, *args) -> None:
        self.calls.append((name, args, self.pos))

    # ── Movement / stateful actions ──────────────────────────────────────────
    def move(self, x: int, y: int) -> None:
        self.pos = (x, y)
        self._record("move", x, y)

    def drag_start(self) -> None:
        self.held.add("mouse_left")
        self._record("drag_start")

    def drag_end(self) -> None:
        self.held.discard("mouse_left")
        self._record("drag_end")

    def ctrl_down(self) -> None:
        self.held.add("ctrl")
        self._record("ctrl_down")

    def ctrl_up(self) -> None:
        self.held.discard("ctrl")
        self._record("ctrl_up")

    @property
    def is_dragging(self) -> bool:
        return "mouse_left" in self.held

    # ── Query helpers ────────────────────────────────────────────────────────
    def count(self, name: str) -> int:
        return sum(1 for call in self.calls if call[0] == name)

    def positions(self, name: str) -> list[tuple[int, int]]:
        """Cursor position at the moment of each call to ``name``."""
        return [pos for call_name, _, pos in self.calls if call_name == name]


# One-shot actions: recorded, no state.
_ONE_SHOT_ACTIONS = (
    "left_click", "right_click", "double_click", "scroll",
    "win_d", "alt_tab", "win_tab", "win_key", "alt_left", "win_l",
    "win_snap_left", "win_snap_right", "zoom_in", "zoom_out",
)

for _name in _ONE_SHOT_ACTIONS:
    setattr(FakeActuator, _name, lambda self, *args, _n=_name: self._record(_n, *args))
