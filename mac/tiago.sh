#!/usr/bin/env bash

# Run tiago_jazzy_ws on a Mac inside an Ubuntu 24.04 / ROS 2 Jazzy container.
set -o errexit
set -o nounset
set -o pipefail

image=tiago-jazzy-mac
container=tiago-jazzy
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

usage() {
  printf '%s\n' \
    'Usage: mac/tiago.sh <command> [arguments...]' \
    '' \
    '  image   build the container image (once, and again after the source bundle changes)' \
    '  up      start the container (recreated if the image changed) and print the desktop link' \
    '  setup   build the workspace inside the container (runs ./setup.sh; colcon arguments are passed on)' \
    '  sim     launch TIAGo with Nav2, Gazebo and RViz; extra launch arguments are passed on' \
    '  shell   open a shell in the container with Jazzy and the overlay sourced' \
    '  down    stop and remove the container (the build stays in the checkout)'
}

# The desktop link carries the container's random VNC password.
desktop_url() {
  printf 'Desktop: http://localhost:6080/vnc.html?autoconnect=1&resize=scale&password=%s\n' \
    "$(docker exec "${container}" printenv VNC_PASSWORD)"
}

# Allocate a terminal only when there is one, so the commands also work from scripts.
exec_flags=(-i)
if [[ -t 0 && -t 1 ]]; then exec_flags=(-it); fi

command="${1:-}"
if [[ "$#" -gt 0 ]]; then shift; fi
case "${command}" in
  image)
    docker build -f "${repo_dir}/mac/Dockerfile" -t "${image}" "${repo_dir}"
    ;;
  up)
    current="$(docker image inspect -f '{{.Id}}' "${image}")"
    if [[ "$(docker container inspect -f '{{.Image}}' "${container}" 2>/dev/null)" == "${current}" ]]; then
      docker start "${container}" >/dev/null
    else
      docker rm -f "${container}" >/dev/null 2>&1 || true
      docker run -d --init --name "${container}" --shm-size=2g -p 127.0.0.1:6080:6080 \
        -e VNC_PASSWORD="$(openssl rand -hex 4)" -v "${repo_dir}:/ws" "${image}" >/dev/null
    fi
    desktop_url
    ;;
  setup)
    # One package at a time: ros_gz_bridge and MoveIt compiling together exceed 8 GB
    # and the compiler is killed. Passing --cmake-args replaces the Release default.
    # The image drops apt's package lists, so refresh them for any new dependency.
    docker exec "${container}" apt-get update -qq
    docker exec "${exec_flags[@]}" "${container}" \
      ./setup.sh --parallel-workers 1 "$@" --cmake-args -DCMAKE_BUILD_TYPE=Release
    ;;
  sim)
    desktop_url
    docker exec "${exec_flags[@]}" "${container}" bash -ic \
      'ros2 launch tiago_gazebo tiago_gazebo.launch.py is_public_sim:=True \
         navigation:=True moveit:=False tuck_arm:=False gzclient:=True rviz:=True "$@"' \
      bash "$@"
    ;;
  shell)
    docker exec "${exec_flags[@]}" "${container}" bash -i "$@"
    ;;
  down)
    docker rm -f "${container}" >/dev/null 2>&1 || true
    ;;
  --help|-h|'')
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
