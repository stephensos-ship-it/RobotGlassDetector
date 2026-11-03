#!/usr/bin/env python3
"""Exercise Gazebo and MoveIt RViz on a virtual X display and retain evidence."""

import argparse
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log-dir', type=Path, default=Path('log/gui'))
    parser.add_argument('--domain', type=int, default=112)
    args = parser.parse_args()
    output = args.log_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    lock = open(Path(tempfile.gettempdir()) / 'tiago-jazzy-smoke.lock', 'w')
    fcntl.flock(lock, fcntl.LOCK_EX)
    signal.signal(signal.SIGINT, signal.default_int_handler)
    environment = os.environ.copy()
    environment.update(DISPLAY=':99', QT_QPA_PLATFORM='xcb', LIBGL_ALWAYS_SOFTWARE='1',
                       ROS_DOMAIN_ID=str(args.domain), GZ_PARTITION=f'tiago_gui_{os.getpid()}')
    processes = []
    streams = []
    status = 0

    def start(name, command):
        stream = (output / (name + '.log')).open('w')
        streams.append(stream)
        process = subprocess.Popen(command, env=environment, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        processes.append((name, process))
        return process

    try:
        start('display', ['Xvfb', ':99', '-screen', '0', '1440x1000x24'])
        time.sleep(1)
        start('window-manager', ['openbox', '--sm-disable'])
        time.sleep(1)
        start('simulation', ['ros2', 'launch', 'tiago_gazebo', 'tiago_gazebo.launch.py',
              'is_public_sim:=True', 'world_name:=pal_office', 'moveit:=True',
              'tuck_arm:=False', 'gzclient:=True', 'rviz:=False'])
        start('rviz', ['ros2', 'launch', 'tiago_moveit_config', 'moveit_rviz.launch.py',
                      'use_sim_time:=True'])
        with (output / 'verification.log').open('w') as stream:
            result = subprocess.run(
                ['ros2', 'run', 'tiago_jazzy_port', 'verify_runtime.py',
                 '--moveit', '--skip-motion'], env=environment, stdout=stream,
                stderr=subprocess.STDOUT, timeout=240)
        status = result.returncode
        if status == 0:
            time.sleep(10)
            subprocess.run(['import', '-window', 'root', str(output / 'desktop.png')],
                           env=environment, check=True, timeout=15)
            windows = subprocess.check_output(['wmctrl', '-l'], env=environment, text=True)
            for line in windows.splitlines():
                window = line.split()[0]
                if 'Gazebo' in line or 'RViz' in line or 'rviz' in line:
                    label = 'gazebo' if 'Gazebo' in line else 'rviz'
                    subprocess.run(['import', '-window', window, str(output / (label + '.png'))],
                                   env=environment, check=True, timeout=15)
            subprocess.run(['ros2', 'run', 'tiago_jazzy_port', 'snapshot_interfaces.py',
                            '--duration', '15', '--output', str(output / 'interfaces.json')],
                           env=environment, check=True, timeout=40)
        if any(process.poll() is not None for _, process in processes):
            status = 1
    except (subprocess.SubprocessError, KeyboardInterrupt):
        status = 1
    finally:
        # Close Qt windows through their window manager, as a desktop user
        # would. RViz's event loop need not finish on a ROS SIGINT alone.
        try:
            windows = subprocess.check_output(['wmctrl', '-l'], env=environment, text=True)
            for line in windows.splitlines():
                if 'Gazebo' in line or 'RViz' in line or 'rviz' in line:
                    subprocess.run(['wmctrl', '-ic', line.split()[0]], env=environment,
                                   check=True, timeout=5)
            time.sleep(2)
        except (subprocess.SubprocessError, OSError):
            status = 1
        for name, process in reversed(processes):
            if process.poll() is None:
                process.send_signal(signal.SIGTERM if name == 'window-manager' else signal.SIGINT)
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                print(f'FAIL: {name} required forced termination')
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                status = 1
        for stream in streams:
            stream.close()
    for name in ['simulation', 'rviz']:
        for line in (output / (name + '.log')).read_text().splitlines():
            if 'Action server: /recognize_objects not available' in line:
                # MoveIt's stock panel probes this optional perception action.
                # Public TIAGo does not launch an object-recognition server;
                # planning and execution are verified independently above.
                print('Optional RViz perception panel: no object-recognition server configured')
                continue
            if any(marker in line for marker in ['[ERROR]', '[FATAL]', '[Err]',
                                                'process has died', 'Traceback']):
                print(line)
                status = 1
    print(f'GUI check: {"PASS" if status == 0 else "FAIL"}; evidence: {output}')
    return status


if __name__ == '__main__':
    raise SystemExit(main())
