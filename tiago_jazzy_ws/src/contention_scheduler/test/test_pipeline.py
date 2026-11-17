"""Drive the pipeline node with made-up scans: it brakes for an obstacle and times it."""

import json
import math
import time

import pytest
import rclpy
from sensor_msgs.msg import LaserScan

from contention_scheduler.pipelines import Pipeline


def scan_of_wall(node, distance):
    """A scan of a flat wall straight across the robot's path, `distance` m ahead."""
    scan = LaserScan()
    scan.header.stamp = node.get_clock().now().to_msg()
    scan.angle_min, scan.angle_increment = -0.5, 0.01
    scan.range_min, scan.range_max = 0.05, 25.0
    scan.ranges = [distance / math.cos(scan.angle_min + i * scan.angle_increment)
                   for i in range(101)]
    return scan


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    status_file = tmp_path / 'reaction.json'
    rclpy.init(args=['--ros-args', '-p', f'status_file:={status_file}'])
    node = Pipeline()
    sent = []
    monkeypatch.setattr(node.cmd_vel, 'publish', sent.append)
    try:
        yield node, sent, status_file
    finally:
        node.destroy_node()
        rclpy.shutdown()


def step(node, scan, info):
    """One scan through all three steps, in order."""
    node.filter(scan, info)
    node.map()
    node.control()


def test_pipeline_brakes_and_times_its_reaction(pipeline):
    node, sent, status_file = pipeline

    node.control()
    assert sent[-1].linear.x == 0.0  # no map yet: stay still
    assert not status_file.exists()  # and that is not a reaction

    step(node, scan_of_wall(node, 3.0), {})  # path clear; no publish time from the middleware
    assert sent[-1].linear.x == pytest.approx(0.3)
    assert json.loads(status_file.read_text()) == {'driving': True}

    step(node, scan_of_wall(node, 0.8), {'source_timestamp': time.time_ns()})
    assert sent[-1].linear.x == 0.0
    status = json.loads(status_file.read_text())
    assert status['driving'] is False
    assert 0.0 <= status['reaction_sim'] < 1.0
    assert 0.0 <= status['delivery_real'] <= status['reaction_real'] < 1.0
    assert status['seen_gap'] == pytest.approx(0.8)
    assert status['rest_gap'] is None

    step(node, scan_of_wall(node, 0.795), {})  # the reference for coming to rest
    time.sleep(0.6)  # scans are stamped from the system clock here; pass the settling time
    step(node, scan_of_wall(node, 0.795), {})
    assert json.loads(status_file.read_text())['rest_gap'] == pytest.approx(0.795)

    # Under 5 cm the laser reads nothing (its minimum range) and the nearest map cell isn't in
    # the stopping zone, so the controller drives on: an existing blind spot. The page keeps
    # the last reaction and says the robot is driving.
    step(node, scan_of_wall(node, 0.04), {})
    status = json.loads(status_file.read_text())
    assert sent[-1].linear.x == pytest.approx(0.3)
    assert status['driving'] is True and status['rest_gap'] == pytest.approx(0.795)
