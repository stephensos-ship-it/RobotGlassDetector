# Native Ubuntu 24.04 setup

Use a fresh Noble installation with a UTF-8 locale and the Ubuntu Universe
repository enabled. Configure the official ROS apt repository using the
[`ros2-apt-source` instructions](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html).
Keep `noble-updates` and `noble-backports` enabled, and update the system before
installing ROS. Only the official ROS and Ubuntu repositories are needed.

```bash
sudo apt update
sudo apt install ros-jazzy-desktop ros-jazzy-ros-gz ros-jazzy-gz-ros2-control \
  python3-colcon-common-extensions python3-vcstool python3-rosdep git build-essential
source /opt/ros/jazzy/setup.bash
```

Jazzy's `ros_gz` installs Harmonic through official ROS vendor packages, as
documented in the [Gazebo installation guide](https://gazebosim.org/docs/harmonic/ros_installation/).

## Prepare the portable sources

From a RobotGlassDetector checkout, build directly in its workspace:

```bash
cd RobotGlassDetector/tiago_jazzy_ws
# Once per new machine; omit init if already initialized.
sudo rosdep init
./setup.sh --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

The script imports pinned sources from the bundle's lock file, applies the
bundle, runs rosdep and builds. Imports use Git directly; vcstool is optional.
Existing checkouts are preserved and checked against the pinned revisions.
Each Ubuntu machine must build its own overlay; do not copy another machine's
`build/` or `install/` directories.

To run the steps manually instead:

```bash
python3 tools/source_bundle.py prepare
```

For a completely empty `src/`, the equivalent vcstool workflow is
`vcs import --shallow src < source_bundle/tiago_jazzy.repos` followed by
`python3 tools/source_bundle.py apply`. The preparation command also handles
existing pinned checkouts without fetching or changing their selected revisions.

The preparation step verifies commit IDs and patch checksums, applies the port,
and installs the two new source packages. It also configures explicit sparse
checkouts: only `moveit_ros_planning`, `moveit_ros_move_group`, `ros_gz_bridge` and `ros_gz_image`
are overlaid from their corresponding upstream repositories. The remaining
MoveIt and `ros_gz` packages come from Jazzy apt packages. These source overrides
fix shutdown bugs and must match the pinned Jazzy versions; review the patches
when updating them.

```bash
# Once per new machine; omit init if already initialized.
sudo rosdep init
rosdep update --rosdistro jazzy
rosdep install --from-paths src --ignore-src --rosdistro jazzy -r -y
MAKEFLAGS=-j2 colcon build --symlink-install --parallel-workers 2 \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

Use a clean shell sourced only with Jazzy when building. The low make parallelism
limits memory used by the MoveIt C++ sources; increase it if memory permits.

## Run and verify

```bash
ros2 launch tiago_gazebo tiago_gazebo.launch.py \
  is_public_sim:=True navigation:=True moveit:=False tuck_arm:=False
```

The [launch reference](launch.md) covers standalone, localization, mapping,
MoveIt, combined modes and multiple robots. Source `install/setup.bash` in each
terminal. To run headlessly, add `gzclient:=False rviz:=False`.

```bash
colcon test --executor sequential --event-handlers console_cohesion+
colcon test-result --verbose
ros2 run tiago_jazzy_port run_smoke.py --duration 30 --log-dir log/smoke/default
ros2 run tiago_jazzy_port run_smoke.py --world pal_office --navigation --moveit \
  --duration 60 --domain 72 --log-dir log/smoke/combined-localization
ros2 run tiago_jazzy_port run_smoke.py --world pal_office --slam --moveit \
  --duration 60 --domain 73 --log-dir log/smoke/combined-mapping
```

Run smoke tests consecutively, or assign each a unique `--domain`. Their Gazebo
transport partitions are isolated automatically. Software rendering can be
selected with `LIBGL_ALWAYS_SOFTWARE=1`; sensor rates are measured in simulation
time, and software rendering can run slower than real time.

