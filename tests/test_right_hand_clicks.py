"""Click behaviour of the classic right-hand processor."""

import pytest

from core.display import TrackpadZone, VirtualDesktop
from core.gestures import right_hand
from core.gestures.right_hand import RightHandProcessor
from tests.fakes import FakeActuator, FakeClock
from tests.fixtures.hands import make_hand

FRAME = 1 / 75  # typical loop rate
MOVED = (0.53, 0.6)  # a slightly different hand position


@pytest.fixture
def rig(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(right_hand, "time", clock.as_time_module())
    actuator = FakeActuator()
    processor = RightHandProcessor(
        actuator,
        VirtualDesktop(total_width=1920, total_height=1080, monitor_count=1),
        TrackpadZone(x_min=100, x_max=1180, y_min=100, y_max=620),
    )
    return processor, actuator, clock


def hold(rig, seconds, **hand_kwargs):
    """Feed the same hand for `seconds` worth of frames."""
    processor, _, clock = rig
    hand = make_hand(**hand_kwargs)
    for _ in range(max(1, round(seconds / FRAME))):
        clock.advance(FRAME)
        processor.process(hand)


def tap(rig, finger="index", center=(0.5, 0.6), pinch_s=0.12):
    """Pinch for `pinch_s`, then release for one frame."""
    hold(rig, pinch_s, pinch=finger, center=center)
    hold(rig, FRAME, center=center)


def test_single_tap_is_one_left_click(rig):
    _, actuator, _ = rig
    hold(rig, 0.5)
    tap(rig)
    assert actuator.count("left_click") == 1
    assert actuator.count("double_click") == 0


def test_two_quick_taps_are_a_double_click_at_the_same_spot(rig):
    _, actuator, _ = rig
    hold(rig, 0.5)
    tap(rig)
    hold(rig, 0.12, center=MOVED)  # the hand drifts a little between taps
    tap(rig, center=MOVED)

    # The second click is sent at the first click's position, so Windows pairs
    # them into a double click. double_click() would add two more clicks on top
    # of the first one (a triple click).
    assert actuator.count("left_click") == 2
    assert actuator.count("double_click") == 0
    first, second = actuator.positions("left_click")
    assert second == first


def test_slow_taps_are_two_single_clicks(rig):
    _, actuator, _ = rig
    hold(rig, 0.5)
    tap(rig)
    hold(rig, 0.6, center=MOVED)
    tap(rig, center=MOVED)
    assert actuator.count("left_click") == 2
    first, second = actuator.positions("left_click")
    assert second != first


def test_pinch_jitter_does_not_double_fire(rig):
    _, actuator, _ = rig
    hold(rig, 0.5)
    hold(rig, 0.12, pinch="index")
    hold(rig, FRAME)                    # release → click
    hold(rig, FRAME, pinch="index")     # flicker across the threshold
    hold(rig, FRAME)
    assert actuator.count("left_click") == 1


def test_pinch_hold_still_drags(rig):
    _, actuator, _ = rig
    hold(rig, 0.5)
    hold(rig, 0.6, pinch="index")
    hold(rig, FRAME)
    assert actuator.count("drag_start") == 1
    assert actuator.count("drag_end") == 1
    assert actuator.count("left_click") == 0
    assert not actuator.held


def test_right_click_fires_once_while_held(rig):
    _, actuator, _ = rig
    hold(rig, 0.5)
    hold(rig, 2.0, pinch="middle")
    assert actuator.count("right_click") == 1


def test_right_click_rearms_after_release(rig):
    _, actuator, _ = rig
    hold(rig, 0.5)
    hold(rig, 0.2, pinch="middle")
    hold(rig, 0.5)
    hold(rig, 0.2, pinch="middle")
    assert actuator.count("right_click") == 2


def test_hand_lost_while_right_pinching_rearms(rig):
    processor, actuator, clock = rig
    hold(rig, 0.5)
    hold(rig, 0.2, pinch="middle")
    clock.advance(0.5)
    processor.process(None)  # hand leaves the frame mid-pinch
    hold(rig, 0.2, pinch="middle")
    assert actuator.count("right_click") == 2
