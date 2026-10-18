"""Sanity checks: the synthetic hands are classified the way the tests assume."""

import config
from core.gestures.utils import dist3d, is_fist, is_open_palm, is_peace_sign
from tests.fixtures.hands import make_hand


def test_poses_match_existing_classifiers():
    assert is_open_palm(make_hand("open"))
    assert is_peace_sign(make_hand("peace"))
    assert is_fist(make_hand("fist"))
    point = make_hand("point")
    assert not is_fist(point) and not is_peace_sign(point) and not is_open_palm(point)


def test_pinches_cross_the_click_thresholds():
    relaxed = make_hand("point")
    assert dist3d(relaxed[4], relaxed[8]) > config.THUMB_INDEX_CLICK_DIST
    assert dist3d(relaxed[4], relaxed[12]) > config.THUMB_MIDDLE_CLICK_DIST

    index_pinch = make_hand("point", pinch="index")
    assert dist3d(index_pinch[4], index_pinch[8]) < config.THUMB_INDEX_CLICK_DIST
    assert dist3d(index_pinch[4], index_pinch[12]) > config.THUMB_MIDDLE_CLICK_DIST

    middle_pinch = make_hand("point", pinch="middle")
    assert dist3d(middle_pinch[4], middle_pinch[12]) < config.THUMB_MIDDLE_CLICK_DIST
    assert dist3d(middle_pinch[4], middle_pinch[8]) > config.THUMB_INDEX_CLICK_DIST
