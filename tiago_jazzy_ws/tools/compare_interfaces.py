#!/usr/bin/env python3
"""Compare saved Humble and Jazzy graphs offline, without cross-distro DDS."""

import argparse
import json
from pathlib import Path


def graph_difference(reference, candidate):
    return {
        'missing': {name: value for name, value in reference.items() if name not in candidate},
        'added': {name: value for name, value in candidate.items() if name not in reference},
        'types_changed': {
            name: {'humble': value, 'jazzy': candidate[name]}
            for name, value in reference.items()
            if name in candidate and set(value) != set(candidate[name])
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('humble', type=Path)
    parser.add_argument('jazzy', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-robot-parity', action='store_true')
    args = parser.parse_args()
    reference = json.loads(args.humble.read_text())
    candidate = json.loads(args.jazzy.read_text())
    report = {key: graph_difference(reference[key], candidate[key])
              for key in ('topics', 'services', 'actions')}
    before, after = reference['tf'] or {}, candidate['tf'] or {}
    report['tf'] = {
        'missing': sorted(set(before) - set(after)),
        'added': sorted(set(after) - set(before)),
        'parent_changed': {
            name: {'humble': value['parent'], 'jazzy': after[name]['parent']}
            for name, value in before.items()
            if name in after and value['parent'] != after[name]['parent']
        },
    }
    report['observations'] = {
        name: {'humble': reference['observations'].get(name),
               'jazzy': candidate['observations'].get(name)}
        for name in sorted(set(reference['observations']) | set(candidate['observations']))
    }
    # RViz publishes motion_plan_request only when its interactive panel is
    # present. Classic performance metrics have no robot control contract.
    optional_topics = {'/motion_plan_request', '/performance_metrics'}
    missing_topics = set(report['topics']['missing']) - optional_topics
    robot_services = {
        name for name in report['services']['missing']
        if name.startswith(('/controller_manager/', '/play_motion2/'))
    }
    report['robot_parity_passed'] = not any((
        missing_topics, robot_services, report['topics']['types_changed'],
        report['actions']['missing'], report['actions']['types_changed'],
        report['tf']['missing'],
    ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    for key in ('topics', 'services', 'actions'):
        value = report[key]
        print(f'{key}: {len(value["missing"])} missing, {len(value["added"])} added, '
              f'{len(value["types_changed"])} types changed')
    print(f'Robot interface parity: {report["robot_parity_passed"]}')
    return int(args.require_robot_parity and not report['robot_parity_passed'])


if __name__ == '__main__':
    raise SystemExit(main())
