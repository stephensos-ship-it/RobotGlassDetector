"""Check the reaction-time bookkeeping without ROS."""

import pytest

from contention_scheduler.reaction import gap_ahead, ReactionTimer


def test_gap_is_the_nearest_obstacle_in_the_robots_path():
    points = [(0.5, 0.6),                       # beside the path, ignored
              (0.80, 0.0), (0.81, 0.1), (0.79, -0.2), (0.82, 0.3), (0.795, 0.05),
              (4.0, 0.0)]                       # the far wall, beyond the 10 cm band
    assert gap_ahead(points, half_width=0.35) == pytest.approx(0.80)
    assert gap_ahead([(0.5, 0.6)], half_width=0.35) is None


def test_reaction_on_both_clocks_and_rest():
    timer = ReactionTimer()
    assert not timer.watching  # standing still at the start
    assert timer.command(stopping=True, now=1.0, wall=100.0) is None
    assert timer.command(stopping=False, now=1.05, wall=100.2) == 'drive'
    assert timer.watching

    timer.scan(obstacle=False, gap=None, stamp=9.9, published=110.0, received=110.01)
    timer.scan(obstacle=True, gap=0.94, stamp=10.0, published=110.5, received=110.52)
    assert not timer.watching  # the first sighting is kept; later scans are not checked
    assert timer.command(stopping=False, now=10.05, wall=110.7) is None  # not reacted yet

    assert timer.command(stopping=True, now=10.2, wall=111.4) == 'stop'
    result = timer.result
    assert result is not None
    assert result['reaction_sim'] == pytest.approx(0.2)
    assert result['reaction_real'] == pytest.approx(0.9)
    assert result['delivery_real'] == pytest.approx(0.02)
    assert result['seen_gap'] == 0.94 and result['rest_gap'] is None
    assert timer.command(stopping=True, now=10.25, wall=111.6) is None  # only the first stop

    # Settling goes by the scans' own timestamps, so scans that queued up while the
    # pipeline waited for the CPU are compared by when the laser took them.
    assert timer.needs_gap
    assert timer.scan(False, 0.85, 10.3, 0, 0) is None   # the reference
    assert timer.scan(False, 0.84, 10.4, 0, 0) is None   # too soon to compare
    assert timer.scan(False, 0.80, 10.8, 0, 0) is None   # moved 5 cm: still braking
    assert timer.scan(False, 0.797, 11.1, 0, 0) is None  # too soon after that
    assert timer.scan(False, 0.795, 11.3, 0, 0) == 'rest'
    assert result['rest_gap'] == 0.795
    assert not timer.watching

    # Driving again (the box was moved, or the robot crept into it): the last result stays
    # until a new stop replaces it.
    assert timer.command(stopping=False, now=20.0, wall=150.0) == 'drive'
    assert timer.result is result and timer.watching
    timer.scan(True, 0.9, 30.0, 160.0, 160.0)
    assert timer.command(stopping=True, now=30.05, wall=160.2) == 'stop'
    assert timer.result is not result and timer.result['reaction_sim'] == pytest.approx(0.05)


def test_a_stop_without_a_timed_scan_is_not_a_reaction():
    timer = ReactionTimer()
    timer.command(stopping=False, now=1.0, wall=100.0)
    assert timer.command(stopping=True, now=2.0, wall=101.0) is None
    assert timer.result is None
