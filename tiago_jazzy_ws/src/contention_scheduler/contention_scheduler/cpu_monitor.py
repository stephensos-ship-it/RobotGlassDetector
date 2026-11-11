"""Start one pipeline process per robot and report actual Linux CPU usage."""

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from time import sleep, time

STATUS_FILE = Path(os.environ.get('TIAGO_CPU_STATUS_FILE', '/tmp/tiago-cpu-usage.json'))


def publish_usage(system, robots):
    """Share the latest sample with the browser desktop, replacing it atomically."""
    try:
        temporary = STATUS_FILE.with_suffix('.tmp')
        temporary.write_text(json.dumps({'time': time(), 'system': system, 'robots': robots}))
        temporary.replace(STATUS_FILE)
    except OSError as error:
        print(f'Could not update the desktop CPU display: {error}', file=sys.stderr)


def system_ticks():
    """Return total and idle ticks across all CPUs; guest time is already included."""
    with open('/proc/stat') as stream:
        ticks = [int(value) for value in stream.readline().split()[1:9]]
    return sum(ticks), ticks[3] + ticks[4]  # idle plus I/O wait


def process_ticks(pid):
    """Read user + kernel CPU time for a process, including its threads."""
    # The process name is parenthesized and may itself contain spaces or ')'.
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    return int(fields[11]) + int(fields[12])  # fields 14 and 15 of /proc/PID/stat


def stop(signum, frame):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--robots', default='tiago1 tiago2', help='Space-separated robot names')
    parser.add_argument('--params-file', help='ROS parameter file for each pipeline')
    args = parser.parse_args()
    names = args.robots.split()
    if not names or len(names) != len(set(names)):
        parser.error('Provide at least one robot name, without duplicates.')

    signal.signal(signal.SIGTERM, stop)
    processes = {}
    try:
        for name in names:
            command = [
                sys.executable, '-m', 'contention_scheduler.pipelines',
                '--ros-args', '-r', f'__ns:=/{name}', '-p', 'use_sim_time:=true',
            ]
            if args.params_file:
                command += ['--params-file', args.params_file]
            processes[name] = subprocess.Popen(command)
            print(f'{name} pipeline PID: {processes[name].pid}', flush=True)

        print('Actual CPU usage (% of total Linux CPU capacity); robots = pipeline processes.',
              flush=True)
        total_before, idle_before = system_ticks()
        before = {name: process_ticks(p.pid) for name, p in processes.items()}
        while True:
            sleep(1)  # wall time, independent of Gazebo's simulation clock
            for name, process in processes.items():
                if process.poll() is not None:
                    print(f'{name} pipeline exited ({process.returncode}).', file=sys.stderr)
                    return 1
            total, idle = system_ticks()
            current = {name: process_ticks(p.pid) for name, p in processes.items()}
            elapsed = total - total_before
            if elapsed > 0:
                system_usage = 100 * (1 - (idle - idle_before) / elapsed)
                robot_usage = {name: 100 * (current[name] - before[name]) / elapsed
                               for name in names}
                usage = [f'Total system: {system_usage:.2f}%']
                usage += [f'{name}: {value:.2f}%' for name, value in robot_usage.items()]
                print(' | '.join(usage), flush=True)
                publish_usage(system_usage, robot_usage)
            total_before, idle_before, before = total, idle, current
    except KeyboardInterrupt:
        pass
    except (FileNotFoundError, ProcessLookupError):
        print('A pipeline exited while sampling CPU usage.', file=sys.stderr)
        return 1
    finally:
        for process in processes.values():
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
        for process in processes.values():
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    return 0


if __name__ == '__main__':
    sys.exit(main())
