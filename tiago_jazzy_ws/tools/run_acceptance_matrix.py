#!/usr/bin/env python3
"""Run the public-mode and pairwise robot-configuration acceptance matrix sequentially."""

import argparse
import json
from pathlib import Path
import subprocess
import time


CASES = {
    'default': ['--moveit', '--tuck-arm', '--snapshot'],
    'gripper-example': ['--gripper-only'],
    'standalone': [],
    'moveit': ['--moveit'],
    'navigation': ['--world', 'pal_office', '--navigation'],
    'slam': ['--world', 'pal_office', '--slam'],
    'combined': ['--world', 'pal_office', '--navigation', '--moveit'],
    'combined-slam': ['--world', 'pal_office', '--slam', '--moveit'],
    'no-arm': ['--no-arm', '--camera', 'no-camera', '--laser', 'no-laser'],
    'omni': ['--base', 'omni_base', '--moveit'],
    'hey5': ['--end-effector', 'pal-hey5', '--moveit', '--camera', 'asus-xtion',
             '--laser', 'hokuyo', '--ft-sensor', 'no-ft-sensor'],
    'robotiq85': ['--end-effector', 'robotiq-2f-85', '--moveit', '--laser', 'sick-551'],
    'robotiq140': ['--end-effector', 'robotiq-2f-140', '--moveit', '--wrist', 'wrist-2010',
                  '--arm-motor', 'ilm', '--camera', 'orbbec-astra-pro', '--laser', 'sick-561'],
    'no-effector': ['--end-effector', 'no-end-effector', '--ft-sensor', 'no-ft-sensor',
                    '--camera', 'no-camera', '--moveit'],
    'screen-tool': ['--screen', '--calibration', '--moveit'],
    'multi-control': ['--world', 'pal_office', '--multi'],
    'multi-navigation': ['--world', 'pal_office', '--multi', '--navigation'],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('log/acceptance'))
    parser.add_argument('--case', action='append', choices=CASES)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = {}
    for index, name in enumerate(args.case or CASES):
        start = time.monotonic()
        with (args.output / (name + '.txt')).open('w') as stream:
            result = subprocess.run([
                'ros2', 'run', 'tiago_jazzy_port', 'run_smoke.py', *CASES[name],
                '--duration', '60' if 'combined' in name else '15',
                '--domain', str(20 + index), '--log-dir', str(args.output / name),
            ], stdout=stream, stderr=subprocess.STDOUT)
        results[name] = {'returncode': result.returncode,
                         'seconds': round(time.monotonic() - start, 1)}
        print(name, 'PASS' if result.returncode == 0 else 'FAIL', flush=True)
        (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    return int(any(record['returncode'] for record in results.values()))


if __name__ == '__main__':
    raise SystemExit(main())
