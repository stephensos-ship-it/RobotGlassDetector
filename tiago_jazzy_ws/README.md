# TIAGo on ROS 2 Jazzy and Gazebo Harmonic

Tldr:

Run TIAGo in Gazebo with Rviz using the following command:

```bash
ros2 launch tiago_gazebo tiago_gazebo.launch.py \
  is_public_sim:=True \
  navigation:=True \
  moveit:=False \
  tuck_arm:=False \
  gzclient:=True \
  rviz:=True
```

Portable source workspace for Ubuntu 24.04. The simulator uses `ros_gz`,
`gz_ros2_control`, standard Jazzy controllers, MoveIt 2 and Nav2.

The current acceptance target is navigation, obstacle avoidance, base movement
and sensors. Arm planning remains available, with separate outstanding checks.

```bash
ros2 launch tiago_gazebo tiago_gazebo.launch.py \
  is_public_sim:=True navigation:=True moveit:=False tuck_arm:=False
```

Add `slam:=True` for mapping or `gzclient:=False rviz:=False` for headless use.

- [Native Ubuntu setup](docs/ubuntu.md)
- [Launch and robot configuration reference](docs/launch.md)
- [Two-robot pipelines and actual CPU usage](src/contention_scheduler/README.md)

Follow [the Ubuntu prerequisites](docs/ubuntu.md),
then prepare and build this workspace in place:

```bash
./setup.sh --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

Use `./setup.sh --sources-only` to reconstruct the pinned source tree without
installing dependencies or building. Sources and native build outputs are
ignored by the parent repository; the portable bundle is tracked instead.

`tiago_jazzy.repos` pins upstream revisions. `source_bundle/` contains the actual
port patches and new packages; importing upstream sources alone is insufficient.
After changing source, regenerate the bundle with:

```bash
python3 tools/source_bundle.py export
```

The exporter preserves upstream working trees and does not create commits.

