# RobotGlassDetector

The TIAGo simulator workspace is in [tiago_jazzy_ws](tiago_jazzy_ws/README.md).
It targets **native Ubuntu 24.04, ROS 2 Jazzy and Gazebo Harmonic**. No container
or host-specific development scripts are required.

Install Jazzy and the build tools using the
[Ubuntu setup guide](tiago_jazzy_ws/docs/ubuntu.md), then run from this checkout:

```bash
cd tiago_jazzy_ws
./setup.sh --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
ros2 launch tiago_gazebo tiago_gazebo.launch.py \
  is_public_sim:=True navigation:=True moveit:=False tuck_arm:=False
```

`setup.sh` imports pinned upstream sources, applies the included migration
patches, resolves dependencies with rosdep and builds the workspace. Each machine
builds its own overlay. The upstream `src/` checkouts and generated build outputs
are ignored by Git; the tracked manifest, patch bundle, tools and documentation
are sufficient to reconstruct the simulator on another machine.

Single-robot navigation, sensors and physical obstacle avoidance have passing
checks. See [remaining issues](tiago_jazzy_ws/docs/remaining-issues.md) for SLAM
shutdown, multi-robot and broader migration limitations.

The repository's existing license is retained. The simulator integration and
upstream packages have their own licenses; see
[simulator attribution](tiago_jazzy_ws/docs/attribution.md).
