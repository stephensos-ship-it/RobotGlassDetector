#!/usr/bin/env bash

# Prepare and build the native Ubuntu 24.04 / ROS 2 Jazzy workspace.
set -o errexit
set -o nounset
set -o pipefail

usage() {
  printf '%s\n' \
    'Usage: ./setup.sh [colcon build arguments...]' \
    '       ./setup.sh --sources-only' \
    '' \
    'Imports pinned sources and applies the bundled port patches.' \
    'The default also resolves Jazzy dependencies and builds a native overlay.' \
    'Requires the tools listed in docs/ubuntu.md; no containers are used.'
}

sources_only=false
case "${1:-}" in
  --help|-h) usage; exit 0 ;;
  --sources-only)
    sources_only=true
    shift
    if [[ "$#" -ne 0 ]]; then usage >&2; exit 2; fi
    ;;
esac

workspace_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd "${workspace_dir}"

for tool in git python3; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    printf 'Missing %s. Install the prerequisites in docs/ubuntu.md.\n' "${tool}" >&2
    exit 1
  fi
done

if [[ "${sources_only}" == false ]]; then
  if [[ ! -r /opt/ros/jazzy/setup.bash ]]; then
    printf 'Install ROS 2 Jazzy first; see docs/ubuntu.md.\n' >&2
    exit 1
  fi
  set +o nounset
  source /opt/ros/jazzy/setup.bash
  set -o nounset
  for tool in rosdep colcon; do
    if ! command -v "${tool}" >/dev/null 2>&1; then
      printf 'Missing %s. Install the prerequisites in docs/ubuntu.md.\n' "${tool}" >&2
      exit 1
    fi
  done
  if [[ ! -r /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
    printf 'Initialize rosdep once with sudo rosdep init, then rerun this script.\n' >&2
    exit 1
  fi
fi

python3 -B tools/source_bundle.py prepare

if [[ "${sources_only}" == true ]]; then
  printf 'Pinned Jazzy sources prepared in %s/src.\n' "${workspace_dir}"
  exit 0
fi

rosdep update --rosdistro jazzy
rosdep install --from-paths src --ignore-src --rosdistro jazzy -r -y
export MAKEFLAGS="${MAKEFLAGS:--j2}"
colcon build --symlink-install --parallel-workers 2 "$@"
printf '\nBuild complete. Run: source install/setup.bash\n'
