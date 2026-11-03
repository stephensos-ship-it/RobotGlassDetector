#!/usr/bin/env python3
"""Export or apply the pinned, portable TIAGo source changes without committing repositories."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile


SPARSE = {
    'moveit2': ['moveit_ros/planning', 'moveit_ros/move_group'],
    'ros_gz': ['ros_gz_bridge', 'ros_gz_image'],
}
LOCAL = ['tiago_gz_plugins', 'tiago_jazzy_port']


def git(directory, *args, check=True):
    return subprocess.run(['git', '-C', str(directory), *args], check=check,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def eligible(path):
    return not any(part in {'.git', '__pycache__', '.pytest_cache', '.ruff_cache'}
                   for part in path.parts) and path.suffix != '.pyc'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def export(workspace, bundle):
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / 'patches').mkdir(exist_ok=True)
    lock = {'repositories': {}, 'sparse': SPARSE, 'local': LOCAL}
    manifest = ['repositories:']
    for repo in sorted((workspace / 'src').iterdir()):
        if not (repo / '.git').exists():
            continue
        revision = git(repo, 'rev-parse', 'HEAD').stdout.decode().strip()
        url = git(repo, 'remote', 'get-url', 'origin').stdout.decode().strip()
        patch = git(repo, 'diff', '--binary', '--full-index', 'HEAD').stdout
        untracked = git(repo, 'ls-files', '--others', '--exclude-standard', '-z').stdout
        for filename in untracked.decode().split('\0'):
            if filename and eligible(Path(filename)):
                result = git(repo, 'diff', '--no-index', '--binary', '--full-index',
                             '--', '/dev/null', filename, check=False)
                if result.returncode != 1:
                    raise RuntimeError(f'Cannot export {repo.name}/{filename}')
                patch += result.stdout
        patch_name = 'patches/' + repo.name + '.patch'
        (bundle / patch_name).write_bytes(patch)
        lock['repositories'][repo.name] = {
            'url': url, 'revision': revision, 'patch': patch_name, 'sha256': digest(patch),
        }
        manifest.extend([f'  {repo.name}:', '    type: git', f'    url: {url}',
                         f'    version: {revision}'])
    # Keep local packages archived so colcon never discovers duplicate source
    # packages in the distribution bundle beside the workspace's src tree.
    with tarfile.open(bundle / 'local.tar.gz', 'w:gz') as archive:
        for name in LOCAL:
            root = workspace / 'src' / name
            for path in sorted(root.rglob('*')):
                if path.is_file() and eligible(path):
                    archive.add(path, arcname=str(Path(name) / path.relative_to(root)))
    lock['local_sha256'] = digest((bundle / 'local.tar.gz').read_bytes())
    if (bundle / 'local').exists():
        shutil.rmtree(bundle / 'local')
    (bundle / 'sources.lock.json').write_text(json.dumps(lock, indent=2) + '\n')
    (workspace / 'tiago_jazzy.repos').write_text('\n'.join(manifest) + '\n')
    shutil.copy2(workspace / 'tiago_jazzy.repos', bundle / 'tiago_jazzy.repos')


def apply(workspace, bundle):
    lock = json.loads((bundle / 'sources.lock.json').read_text())
    for name, record in lock['repositories'].items():
        repo = workspace / 'src' / name
        revision = git(repo, 'rev-parse', 'HEAD').stdout.decode().strip()
        if revision != record['revision']:
            raise RuntimeError(f'{name}: expected {record["revision"]}, got {revision}')
        if name in lock['sparse']:
            git(repo, 'sparse-checkout', 'set', *lock['sparse'][name])
        patch = bundle / record['patch']
        if digest(patch.read_bytes()) != record['sha256']:
            raise RuntimeError(f'Patch checksum mismatch: {patch}')
        if patch.stat().st_size:
            # Idempotent for an already prepared tree. Never reset user files.
            if git(repo, 'apply', '--reverse', '--check', str(patch), check=False).returncode:
                git(repo, 'apply', '--check', str(patch))
                git(repo, 'apply', str(patch))
    archive_path = bundle / 'local.tar.gz'
    if digest(archive_path.read_bytes()) != lock['local_sha256']:
        raise RuntimeError('Local package archive checksum mismatch')
    with tempfile.TemporaryDirectory() as temporary:
        with tarfile.open(archive_path) as archive:
            archive.extractall(temporary, filter='data')
        for name in lock['local']:
            source = Path(temporary) / name
            target = workspace / 'src' / name
            if target.exists():
                for path in source.rglob('*'):
                    if path.is_file():
                        existing = target / path.relative_to(source)
                        if not existing.is_file() or existing.read_bytes() != path.read_bytes():
                            raise RuntimeError(f'Local package differs: {target}; use a fresh workspace')
            else:
                shutil.copytree(source, target)


def prepare(workspace, bundle):
    """Import missing pinned repositories without fetching or resetting existing ones."""
    lock = json.loads((bundle / 'sources.lock.json').read_text())
    source = workspace / 'src'
    source.mkdir(parents=True, exist_ok=True)
    # Validate existing checkouts before making any source changes.
    for name, record in lock['repositories'].items():
        repo = source / name
        if repo.exists():
            revision = git(repo, 'rev-parse', 'HEAD').stdout.decode().strip()
            if revision != record['revision']:
                raise RuntimeError(f'{name}: expected {record["revision"]}, got {revision}')
    for name, record in lock['repositories'].items():
        repo = source / name
        if repo.exists():
            continue
        # An interrupted download must not leave a partial repository at src/name.
        with tempfile.TemporaryDirectory(prefix='.import-', dir=source) as temporary:
            checkout = Path(temporary) / name
            subprocess.run([
                'git', 'clone', '--filter=blob:none', '--no-checkout', '--depth', '1',
                record['url'], str(checkout),
            ], check=True)
            git(checkout, 'fetch', '--depth', '1', 'origin', record['revision'])
            if name in lock['sparse']:
                git(checkout, 'sparse-checkout', 'set', *lock['sparse'][name])
            git(checkout, 'checkout', '--detach', record['revision'])
            checkout.rename(repo)
    apply(workspace, bundle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['export', 'apply', 'prepare'])
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--bundle', type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    bundle = (args.bundle or Path(__file__).resolve().parents[1] / 'source_bundle').resolve()
    {'export': export, 'apply': apply, 'prepare': prepare}[args.operation](workspace, bundle)
    print(f'{args.operation}: {workspace} ({bundle})')


if __name__ == '__main__':
    main()
