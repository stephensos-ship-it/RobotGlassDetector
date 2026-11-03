# Ubuntu 24.04, ROS 2 Jazzy and Gazebo Harmonic for running tiago_jazzy_ws on a Mac.
# Native arm64 on Apple Silicon (amd64 on Intel Macs). The desktop is served over
# noVNC on port 6080; rendering is software (Mesa llvmpipe), so expect it to be slower
# than a Linux machine with a GPU. Build from the repository root; see mac/README.md.
FROM ros:jazzy

ARG DEBIAN_FRONTEND=noninteractive

# The packages docs/ubuntu.md lists, plus a virtual display and a browser VNC viewer.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-desktop ros-jazzy-ros-gz ros-jazzy-gz-ros2-control \
      python3-colcon-common-extensions python3-vcstool python3-rosdep git build-essential \
      xvfb x11vnc novnc websockify openbox xterm mesa-utils \
    && rm -rf /var/lib/apt/lists/*

# Install the workspace's rosdep dependencies into the image, so a container can be
# recreated without reinstalling them. The pinned sources are fetched only to resolve
# dependencies and are then discarded; the real workspace is the mounted checkout.
COPY tiago_jazzy_ws/tools /tmp/tiago/tools
COPY tiago_jazzy_ws/source_bundle /tmp/tiago/source_bundle
RUN cd /tmp/tiago \
    && python3 -B tools/source_bundle.py prepare \
    && apt-get update \
    && rosdep update --rosdistro jazzy \
    && rosdep install --from-paths src --ignore-src --rosdistro jazzy -r -y \
    && rm -rf /tmp/tiago /var/lib/apt/lists/*

ENV DISPLAY=:1 \
    LIBGL_ALWAYS_SOFTWARE=1 \
    QT_X11_NO_MITSHM=1

RUN printf '%s\n' \
      'source /opt/ros/jazzy/setup.bash' \
      'if [ -f /ws/tiago_jazzy_ws/install/setup.bash ]; then source /ws/tiago_jazzy_ws/install/setup.bash; fi' \
      >> /root/.bashrc

COPY mac/entrypoint.sh /usr/local/bin/tiago-entrypoint
ENTRYPOINT ["/usr/local/bin/tiago-entrypoint"]
CMD ["sleep", "infinity"]
WORKDIR /ws/tiago_jazzy_ws
