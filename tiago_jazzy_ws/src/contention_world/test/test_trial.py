"""Trial boundaries and outcomes; no perception or reaction-time measurements."""

import importlib.machinery
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest
import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from ros_gz_interfaces.msg import Contact, Contacts

path = Path(__file__).resolve().parents[1] / 'scripts/run_trial'
loader = importlib.machinery.SourceFileLoader('run_trial', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)


@pytest.fixture
def trial(request, monkeypatch):
    scenario = getattr(request, 'param', 'clear')
    rclpy.init(args=['--ros-args', '-p', f'scenario:={scenario}'])
    clock = {'sim': 0.0, 'wall': 0.0}
    monkeypatch.setattr(module, 'monotonic', lambda: clock['wall'])
    node = module.Trial()
    node.now = lambda: clock['sim']
    node.stops = {name: Mock() for name in node.names}
    for name in node.names:
        odometry = Odometry()
        odometry.pose.pose.position.x = 1.0
        node.track(name, odometry)
        node.scans.add(name)
        node.commands[name] = Twist()
        node.commands[name].linear.x = 0.3
    node.tick()
    clock['sim'] = 1.0
    node.tick()
    assert node.started == 1.0
    for publisher in node.stops.values():
        publisher.reset_mock()
    yield node, clock
    node.destroy_node()
    rclpy.try_shutdown()


def test_finish_stop_is_latched_and_waits_for_actual_velocity(trial):
    node, clock = trial
    for name in node.names:
        node.odometry[name].twist.twist.linear.x = 0.3
    node.odometry['tiago1'].pose.pose.position.x = 10.0
    node.tick()
    assert node.result is None
    node.stops['tiago1'].publish.assert_called_once()
    node.stops['tiago2'].publish.assert_not_called()
    node.odometry['tiago1'].pose.pose.position.x = 9.99
    node.tick()
    assert node.stops['tiago1'].publish.call_count == 2
    node.odometry['tiago2'].pose.pose.position.x = 10.0
    for odometry in node.odometry.values():
        odometry.twist.twist.linear.x = 0.0
    node.tick()
    assert node.result is None
    clock['sim'] += 0.6
    node.tick()
    assert node.result.startswith('PASS') and node.done


@pytest.mark.parametrize('trial', ['obstacle'], indirect=True)
def test_obstacle_trigger_and_pipeline_stop_are_independent(trial, monkeypatch):
    node, clock = trial
    placement = Mock()
    placement.poll.return_value = 0
    start = Mock(return_value=placement)
    monkeypatch.setattr(module.subprocess, 'Popen', start)
    node.odometry['tiago1'].pose.pose.position.x = 3.99
    node.odometry['tiago1'].twist.twist.linear.x = 0.3
    node.tick()
    start.assert_not_called()
    node.odometry['tiago1'].pose.pose.position.x = 4.0
    node.tick()
    node.tick()
    start.assert_called_once()
    assert node.box_placed
    node.stops['tiago1'].publish.assert_not_called()
    node.odometry['tiago1'].twist.twist.linear.x = 0.0
    node.tick()
    clock['sim'] += 0.6
    node.tick()
    assert not node.obstacle_stopped  # a watchdog stop is not an explicit pipeline stop
    node.commands['tiago1'].linear.x = 0.0
    node.tick()
    assert node.obstacle_stopped
    assert node.result is None  # wait for the other robot, keeping both pipelines alive


def test_contact_fails_the_trial_and_holds_both_robots(trial):
    node, _ = trial
    node.contact(Contacts(contacts=[Contact()]))
    node.tick()
    assert node.result.startswith('FAIL: collision')
    assert all(publisher.publish.called for publisher in node.stops.values())


def test_trial_timeout(trial):
    node, clock = trial
    clock['sim'] += 46.0
    node.tick()
    assert node.result.startswith('FAIL: trial timeout')


def test_startup_timeout_even_when_data_arrives_but_clock_does_not_advance(trial):
    node, clock = trial
    node.started = None
    clock['wall'] = 121.0
    node.tick()
    assert node.result == 'FAIL: startup timeout'
