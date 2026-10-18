"""LEFT_HAND_ENABLED / TWO_HAND_GESTURES_ENABLED / MP_MAX_HANDS are honoured."""

import pytest

from core.display import TrackpadZone, VirtualDesktop
from core.gestures import left_hand, right_hand, two_hand
from core.gestures.orchestrator import GestureOrchestrator
from core.tracker import HandsResult, resolve_num_hands
from tests.fakes import FakeActuator, FakeClock
from tests.fixtures.hands import make_hand

FRAME = 1 / 75


@pytest.fixture
def clock(monkeypatch):
    clock = FakeClock()
    for module in (right_hand, left_hand, two_hand):
        monkeypatch.setattr(module, "time", clock.as_time_module())
    return clock


def build(left: bool, two: bool) -> tuple[GestureOrchestrator, FakeActuator]:
    actuator = FakeActuator()
    orchestrator = GestureOrchestrator(
        actuator,
        VirtualDesktop(total_width=1920, total_height=1080, monitor_count=1),
        TrackpadZone(x_min=100, x_max=1180, y_min=100, y_max=620),
        left_hand_enabled=left,
        two_hand_enabled=two,
    )
    return orchestrator, actuator


def run(orchestrator, clock, hands: HandsResult, seconds: float) -> None:
    for _ in range(max(1, round(seconds / FRAME))):
        clock.advance(FRAME)
        orchestrator.process(hands)


@pytest.mark.parametrize(
    "max_hands, left, two, expected",
    [
        (2, True, True, 2),
        (2, True, False, 2),
        (2, False, True, 2),
        (2, False, False, 1),
        (1, True, True, 1),
        (0, True, False, 1),
    ],
)
def test_resolve_num_hands(max_hands, left, two, expected):
    assert resolve_num_hands(max_hands, left, two) == expected


def test_left_hand_layer_on_holds_ctrl_for_left_fist(clock):
    orchestrator, actuator = build(left=True, two=False)
    run(orchestrator, clock, HandsResult(left=make_hand("fist")), 0.2)
    assert actuator.count("ctrl_down") == 1
    run(orchestrator, clock, HandsResult(), 0.1)
    assert "ctrl" not in actuator.held


def test_left_hand_layer_off_ignores_left_hand(clock):
    orchestrator, actuator = build(left=False, two=False)
    run(orchestrator, clock, HandsResult(left=make_hand("fist")), 0.2)
    run(orchestrator, clock, HandsResult(left=make_hand("open")), 0.6)
    assert actuator.count("ctrl_down") == 0
    assert actuator.count("win_d") == 0


def test_two_hand_layer_off_never_locks_screen(clock):
    orchestrator, actuator = build(left=True, two=False)
    both_fists = HandsResult(left=make_hand("fist"), right=make_hand("fist"))
    run(orchestrator, clock, both_fists, 1.5)
    assert actuator.count("win_l") == 0


def test_two_hand_layer_works_without_left_hand_layer(clock):
    orchestrator, actuator = build(left=False, two=True)
    both_fists = HandsResult(left=make_hand("fist"), right=make_hand("fist"))
    run(orchestrator, clock, both_fists, 1.5)
    assert actuator.count("win_l") == 1
    assert actuator.count("ctrl_down") == 0
