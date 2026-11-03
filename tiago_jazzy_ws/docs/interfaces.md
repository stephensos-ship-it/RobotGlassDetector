# ROS interface compatibility

Names below are relative to the robot namespace, except the shared `/clock`.
The runtime snapshot tool records discovered types, services/actions, TF parent
links, sensor headers and observed rates as JSON. Run it separately in Humble and
Jazzy and compare reports offline; no cross-distribution DDS is needed.

```bash
ros2 run tiago_jazzy_port snapshot_interfaces.py --duration 20 --output jazzy.json
```

| Interface | ROS type / behavior | Compatibility |
| --- | --- | --- |
| `/clock` | `rosgraph_msgs/msg/Clock` | Shared advancing simulation clock |
| `joint_states` | `sensor_msgs/msg/JointState` | Preserved; passive Hey5/Robotiq joints also reported |
| `tf`, `tf_static` | `tf2_msgs/msg/TFMessage` | Local frame names; isolated topics per robot |
| `cmd_vel`, `cmd_vel_muxed`, `key_vel` | `geometry_msgs/msg/Twist` | Existing command/mux paths retained |
| `mobile_base_controller/cmd_vel` | `geometry_msgs/msg/TwistStamped` | Native Jazzy change; adapter accepts unstamped commands on compatibility inputs |
| `mobile_base_controller/odom` | `nav_msgs/msg/Odometry` | Preserved for both bases |
| `ground_truth_odom` | `nav_msgs/msg/Odometry` | Native 3D world odometry, 100 Hz configured |
| `scan_raw` | `sensor_msgs/msg/LaserScan` | Native lidar; omni dual scans merged |
| `scan_front_raw`, `scan_rear_raw` | `sensor_msgs/msg/LaserScan` | Omni per-sensor streams remain available |
| `sonar_base` | `sensor_msgs/msg/Range` | Public PMB2 range stream, frame identifies each sonar |
| `imu_sensor_broadcaster/imu` | `sensor_msgs/msg/Imu` | Native sensor through ros2_control broadcaster |
| `ft_sensor_controller/wrench` | `geometry_msgs/msg/WrenchStamped` | Preserved, physical nonzero forces verified |
| `head_front_camera/rgb/image_raw` | `sensor_msgs/msg/Image` | Compatibility alias of native RGB image |
| `head_front_camera/depth_registered/image_raw` | `sensor_msgs/msg/Image` | Compatibility alias of native depth image |
| `head_front_camera/{rgb,depth_registered}/camera_info` | `sensor_msgs/msg/CameraInfo` | Compatibility aliases |
| `head_front_camera/depth_registered/points` | `sensor_msgs/msg/PointCloud2` | Compatibility alias of native RGB-D cloud |
| `controller_manager/*` | Standard controller-manager services | Controller lifecycle and list interfaces retained |
| `{arm,torso,head,gripper,hand}_controller/follow_joint_trajectory` | `control_msgs/action/FollowJointTrajectory` | Preserved where configured |
| `play_motion2` | `play_motion2_msgs/action/PlayMotion2` | Public motion library retained |
| `play_motion2/raw` | `play_motion2_msgs/action/PlayMotion2Raw` | Official PAL raw-motion API retained |
| `move_action` | `moveit_msgs/action/MoveGroup` | Native Jazzy planning and execution |
| `navigate_to_pose` | `nav2_msgs/action/NavigateToPose` | Native Jazzy navigation |
| `map` | `nav_msgs/msg/OccupancyGrid` | Map server or SLAM output |

Native RGB-D topic names (`head_front_camera/image`, `depth_image`, `camera_info`,
`points`) are additive. Sensor frame IDs and rates must be read from the saved
comparison reports for each configured model; wall-clock rates depend on the
real-time factor. A headless camera still uses rendering.

Current PAL depth aliases `head_front_camera/depth/{image_raw,camera_info}` and
`head_front_camera/depth/rgb/points` are retained as well as the older
`depth_registered` aliases. Registered sensor headers use
`head_front_camera_color_optical_frame`; its transform is identical to the RGB
optical frame. The IMU header identifies `base_imu_link`, correcting Classic's
`base_footprint` header for a sensor mounted in a different frame.

The rendered reference snapshot contains 14 actions and 54 TF frame names. All
are present in the Jazzy comparison; common topic types and controller-manager
service types match. `tools/compare_interfaces.py` compares saved reports and
can require robot-interface parity. Classic sensor-plugin parameter services
move to the native bridge/controller nodes. RViz's optional
`motion_plan_request` publisher and Classic `performance_metrics` are not robot
control interfaces.

Classic-specific `gazebo_msgs` world/model services are replaced by Harmonic's
Gazebo Transport UserCommands APIs and `ros_gz_interfaces` bridges. They are not
controller-manager or robot motion services, and are not required for the public
robot control paths. ROS 1 wrapper actions and XML launch syntax are archival;
the package matrix lists their native replacements.

