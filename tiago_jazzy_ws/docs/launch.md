# Launch and configuration reference

All commands assume the native overlay has been sourced. The primary entry point
retains the public PAL package and filename:

```bash
ros2 launch tiago_gazebo tiago_gazebo.launch.py --show-args
```

| Mode | Arguments after `is_public_sim:=True` |
| --- | --- |
| Standalone controls | `moveit:=False tuck_arm:=False` |
| MoveIt planning and execution | `moveit:=True` |
| Nav2 localization | `navigation:=True moveit:=False` |
| Nav2 and SLAM | `navigation:=True slam:=True moveit:=False` |
| Nav2 and MoveIt | `navigation:=True moveit:=True` |
| Nav2, SLAM and MoveIt | `navigation:=True slam:=True moveit:=True` |
| PAL office | `world_name:=pal_office` (default) |
| Empty test world | `world_name:=empty` |
| No arm | `arm_type:=no-arm` |
| Headless | `gzclient:=False rviz:=False` |
| Custom spawn | `x:=1.0 y:=0.0 yaw:=1.57` |

`advanced_navigation:=True` selects the public Nav2 replacement. PAL's private
advanced-navigation implementation is not included in the public distribution.
For navigation and obstacle-avoidance experiments, use `moveit:=False
tuck_arm:=False`. The robot and its RGB-D, lidar, IMU, sonar and odometry sensors
remain available. `docking` is retained as a legacy private-navigation argument;
public Nav2 exposes its native docking server, which needs a dock pose or database.
`gazebo_version:=gazebo` selects Harmonic; the old `classic` value is rejected.
The simulated arm and torso start in PAL's folded home posture, so disabling
arm planning does not leave an extended arm outside the navigation footprint.

```bash
ros2 launch tiago_multi multitiago_gazebo.launch.py gzclient:=False
```

This spawns `tiago1` and `tiago2` at y=-1 and y=1 in one world. Controllers,
sensors and TF topics are namespaced; frame names remain local within each TF
topic. Consumers must remap `/tf` and `/tf_static` to their robot's topics.

## Robot choices

| Argument | Choices | Default |
| --- | --- | --- |
| `base_type` | `pmb2`, `omni_base` | `pmb2` |
| `arm_type` | `tiago-arm`, `no-arm` | `tiago-arm` |
| `arm_motor_model` | `parker`, `ilm` | `parker` |
| `wrist_model` | `wrist-2010`, `wrist-2017` | `wrist-2017` |
| `ft_sensor` | `schunk-ft`, `no-ft-sensor` | `schunk-ft` |
| `end_effector` | `pal-gripper`, `pal-hey5`, `robotiq-2f-85`, `robotiq-2f-140`, `no-end-effector`, `custom` | `pal-gripper` |
| `camera_model` | `orbbec-astra`, `orbbec-astra-pro`, `asus-xtion`, `no-camera` | `orbbec-astra` |
| `laser_model` | `sick-571`, `sick-561`, `sick-551`, `hokuyo`, `no-laser` | `sick-571` |
| `has_screen` | `False`, `True` | `False` |
| `calibration_tool` | `False`, `True` (PAL gripper) | `False` |

Motor models share simulated kinematics; their physical motor/gravity-control
differences concern hardware. `custom` reserves the upstream attachment point
and creates no end-effector controller. A custom tool requires its own model and
controller configuration. No-arm mode omits arm, FT and end-effector hardware.
Camera and laser disabling also disables their bridges.

## Public command interfaces

```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.1}}'
ros2 control list_controllers
ros2 action list -t
ros2 launch tiago_moveit_config moveit_rviz.launch.py use_sim_time:=True
```

Unstamped base commands are accepted on `cmd_vel`, `cmd_vel_muxed`, and
`mobile_base_controller/cmd_vel_unstamped`. Native Jazzy's stamped interface is
`mobile_base_controller/cmd_vel`. Stop publishing to trigger the 250 ms command
watchdog. Use `key_vel` for keyboard teleoperation through the priority mux.

For a previously saved map, launch navigation separately with
`ros2 launch tiago_2dnav tiago_nav_bringup.launch.py map:=/absolute/path/map.yaml`.
Save SLAM output using `ros2 run nav2_map_server map_saver_cli -f ~/my_map`.
The main simulation launch also accepts `map:=/absolute/path/map.yaml`.
An unknown localization world fails with an explicit missing-map error; map new
worlds with `slam:=True` first.

