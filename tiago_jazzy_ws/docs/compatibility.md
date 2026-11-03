# Upstream compatibility matrix

The audit follows PAL's public
[`tiago_public.repos`](https://github.com/pal-robotics/tiago_tutorials/blob/humble-devel/tiago_public.repos).
The manifest currently names 15 repositories. Every one is represented below.
Exact imported commits and local patch hashes are in
`source_bundle/sources.lock.json`; upstream sources alone do not contain this port.

| Public upstream repository | Disposition | Jazzy implementation |
| --- | --- | --- |
| `urdf_test` | Patched for Jazzy | ament test helpers, public Xacro/description tests |
| `pal_urdf_utils` | Migrated to Harmonic | Community Jazzy branch; public meshes/materials and URDF helpers retained |
| `launch_pal` | Patched for Jazzy | Argument forwarding, scoped namespace/remapping isolation, Python/API fixes and regression tests |
| `pal_gazebo_worlds` | Migrated to Harmonic | Native SDF office/empty worlds and native world-system loader; static Classic-format world assets can be loaded without Classic runtime |
| `play_motion2` | Patched for Jazzy | Jazzy actions/controllers, explicit description parameters, namespaced planning and controller interfaces |
| `pmb2_robot` | Migrated to Harmonic | Native IMU/lidar/range descriptions, gz_ros2_control-compatible wheel state, standard diff-drive controller |
| `pmb2_navigation` | Patched for Jazzy | Source retained and built; public sensor configuration, legacy RGB-D runtime replaced by native sensor bridging |
| `pal_navigation_cfg_public` | Replaced by Jazzy-native Nav2 | Configuration packages retained; public bringup entry point delegates to maintained Jazzy navigation |
| `tiago_robot` | Migrated to Harmonic | Native control hardware, ordered controller spawning, complete robot arguments, screen/calibration assets and sensor compatibility |
| `tiago_navigation` | Replaced by Jazzy-native Nav2 | Public localization, mapping, costmaps, planning, control and RViz integration |
| `tiago_simulation` | Migrated to Harmonic | ros_gz spawn/bridges, native world ownership, combined launch modes and ROS 2 multi-robot support |
| `pal_hey5` | Migrated to Harmonic | Force-driven native underactuation system; measured passive finger state and native trajectory controller |
| `pal_gripper` | Migrated to Harmonic | Native trajectory controller, updated public geometry/inertia and standalone ros_gz spawn |
| `pal_robotiq_gripper` | Migrated to Harmonic | 85/140 descriptions and native mimic control; obsolete ROS 1 wrappers retained as archives |
| `tiago_moveit_config` | Patched for Jazzy | Explicit URDF, SRDF, planning/kinematics configuration, native controller actions and RViz builder API |

Additional pinned sources are the community `tiago_harmonic` metapackage,
`br2_gazebo_worlds`, `pal_maps`, omni-base descriptions/controllers, and the
explicit MoveIt/ros_gz source overrides. `tiago_gz_plugins` and
`tiago_jazzy_port` are new portable packages.

## Previously ignored package directories

No `COLCON_IGNORE` is used in `src/`. All source packages are discovered.

| Package | Explicit disposition |
| --- | --- |
| `pal_gripper_gazebo` | ament compatibility package; ROS 1 XML launch files are archival, ROS 2 users use `pal_gripper_simulation` |
| `pal_parallel_gripper_wrapper` | Config-only ament package; ROS 1 rospy controller wrapper replaced by standard trajectory actions |
| `pal_robotiq_gripper_wrapper` | Config-only ament package; ROS 1 wrapper replaced by native ros2_control mimic/action interfaces |
| `pal_robotiq_epick_description`, `pal_robotiq_epick_gripper` | ament description/metapackage retained; ePick is not an exposed public TIAGo end-effector choice. Its legacy vacuum demo is archival, not a supported TIAGo runtime |
| `pmb2_rgbd_sensors` | Config-only compatibility package; simulation uses ros_gz RGB-D bridges rather than old hardware camera launch files |
| `tiago_multi` | Migrated from ROS 1 XML examples to native ROS 2 namespaces, controller/sensor isolation and a shared Harmonic world |

Legacy REEM demonstration worlds embedding Classic robot controllers and custom
Classic actor libraries are not silently loaded: the loader reports the exact
unported embedded plugin. They are separate robot/demo applications, not TIAGo
robot configurations. Their current status remains an explicit limitation in
the acceptance checklist. Standard PAL office and empty worlds use native SDF.

