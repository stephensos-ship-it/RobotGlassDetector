"""Check Linux CPU accounting and the monitor's process lifecycle."""

import io
import json
from pathlib import Path
import signal
import subprocess
import sys

import rclpy
from std_srvs.srv import Trigger

from contention_scheduler import cpu_monitor


def test_system_ticks_do_not_count_guest_time_twice(monkeypatch):
    monkeypatch.setattr('builtins.open', lambda _: io.StringIO(
        'cpu 100 20 30 400 50 6 7 8 60 10\ncpu0 0 0 0 0\n'))
    assert cpu_monitor.system_ticks() == (621, 450)


def test_process_ticks_handle_spaces_and_parentheses_in_names(monkeypatch):
    fields = ['S'] + ['0'] * 10 + ['30', '12', '999', '999']
    monkeypatch.setattr(Path, 'read_text', lambda _: '42 (a process) name) ' + ' '.join(fields))
    assert cpu_monitor.process_ticks(42) == 42  # child CPU fields are excluded


def test_hazard_services_report_each_robot_and_clear_unavailable_results():
    rclpy.init(args=[])
    node = rclpy.create_node('hazard_display_test')
    states = {'tiago1': 'Hazard detected', 'tiago2': 'Path clear'}

    def respond(name, response):
        response.success = states[name] is not None
        response.message = states[name] or 'No scan map available yet'
        return response

    clients = {}
    try:
        for name in states:
            service = f'/hazard_display_test/{name}/check_hazard'
            node.create_service(Trigger, service,
                                lambda request, response, name=name: respond(name, response))
            clients[name] = node.create_client(Trigger, service)
            assert clients[name].wait_for_service(timeout_sec=5.0)

        clients['missing'] = node.create_client(Trigger, '/hazard_display_test/missing')
        assert cpu_monitor.check_hazards(node, clients) == {
            'tiago1': 'Hazard detected', 'tiago2': 'Path clear', 'missing': 'Unknown',
        }

        states.update(tiago1='Path clear', tiago2='Hazard detected')
        assert cpu_monitor.check_hazards(node, clients) == {
            'tiago1': 'Path clear', 'tiago2': 'Hazard detected', 'missing': 'Unknown',
        }

        states['tiago2'] = None
        assert cpu_monitor.check_hazards(node, clients)['tiago2'] == 'Unknown'
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


def test_usage_reporting_and_shutdown(monkeypatch, capsys, tmp_path):
    first = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    second = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    processes = iter([first, second])
    system = iter([(1000, 500), (2000, 1100)])
    ticks = iter([10, 20, 110, 220])
    sleeps = iter([None, KeyboardInterrupt()])

    def sleep(_):
        result = next(sleeps)
        if isinstance(result, KeyboardInterrupt):
            raise result

    monkeypatch.setattr(sys, 'argv', ['cpu_monitor'])
    monkeypatch.setattr(cpu_monitor.subprocess, 'Popen', lambda _: next(processes))
    monkeypatch.setattr(cpu_monitor, 'system_ticks', lambda: next(system))
    monkeypatch.setattr(cpu_monitor, 'process_ticks', lambda _: next(ticks))
    monkeypatch.setattr(cpu_monitor, 'sleep', sleep)
    monkeypatch.setattr(cpu_monitor, 'check_hazards', lambda node, clients: {
        'tiago1': 'Hazard detected', 'tiago2': 'Path clear',
    })
    status_file = tmp_path / 'cpu-usage.json'
    monkeypatch.setattr(cpu_monitor, 'STATUS_FILE', status_file)
    # Restore the handler after main so this test does not affect the test runner.
    previous_handler = signal.getsignal(signal.SIGTERM)
    try:
        assert cpu_monitor.main() == 0
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
        for process in [first, second]:
            if process.poll() is None:
                process.kill()
            process.wait()

    output = capsys.readouterr().out
    assert f'tiago1 pipeline PID: {first.pid}' in output
    assert f'tiago2 pipeline PID: {second.pid}' in output
    assert 'Total system: 40.00% | tiago1: 10.00% | tiago2: 20.00%' in output
    sample = json.loads(status_file.read_text())
    assert sample['system'] == 40.0
    assert sample['robots'] == {'tiago1': 10.0, 'tiago2': 20.0}
    assert sample['hazards'] == {'tiago1': 'Hazard detected', 'tiago2': 'Path clear'}
    assert sample['time'] > 0
    assert first.returncode is not None and second.returncode is not None
