# Architecture and migration notes

## Runtime

`tiago_gazebo.launch.py` creates a Harmonic server and a namespaced group for
robot state publication, spawning, sensor bridges, controllers and optional
MoveIt/Nav2 nodes. `pal_gazebo_worlds` installs the required native physics,
sensor, IMU, force-torque, contact, scene and world-command systems. The server
is executed directly, so launch owns its PID and can shut it down reliably.

The robot uses `gz_ros2_control/GazeboSimSystem`. One ordered spawner initializes
the joint-state broadcaster, base, IMU, torso, head, arm, FT and end-effector
controllers. PMB2 uses `diff_drive_controller`; the omni base uses Jazzy's
`mecanum_drive_controller`. Its reference, odometry and TF topics are remapped
to the PAL-facing names. Wheel radius and wheel positions come from the public
model. Fixed-joint reduction is preserved except at the FT sensor attachment.

`simulation_adapter.py` supplies the compatibility functions that previously
belonged to Classic ROS plugins:

- Unstamped Twist inputs become native stamped controller commands, with a
  simulation-time 250 ms watchdog.
- RGB-D streams receive the existing PAL/OpenNI topic aliases.
- Native sonar LaserScan data becomes `sensor_msgs/Range`.
- The omni base's front and rear scans are transformed into a merged 360-degree
  scan in `base_footprint`.
- A latched `robot_description_sim` is derived from the original URDF for spawning.

The spawn description removes duplicate SDF mimic constraints because Jazzy's
`gz_ros2_control` implements them itself, while Harmonic's default DART backend
does not implement those physics constraints. It also adds 0.0001 units of
physics-only clearance at zero hard stops. Runtime tests demonstrated that a
motor initialized exactly at a DART zero stop could accept a trajectory without
moving. The original URDF, controller limits, TF and MoveIt model retain their
public ranges. Acceptance requires measured displacement, not just an action's
success status.

The simulated arm and torso initialize in PAL's final `home` posture. This keeps
the physical arm folded for navigation when MoveIt and the startup arm motion
are disabled. Initializing every joint at zero leaves the arm outside the
compact navigation footprint and can obstruct a valid base-only detour.
Trajectory controllers remain available to move the arm explicitly.

Hey5's underactuated mechanism is represented by the new `tiago_gz_plugins`
force-driven system. Its follower reductions and PID gains come from PAL's
public model. Passive finger positions are exported through ros2_control, so
the physical hand and TF agree. Contact response remains physical; it does not
teleport finger links. Robotiq uses Jazzy's native mimic support and state-only
interfaces for its five actual follower joints.

## Planning and navigation

MoveIt uses the public SRDF, KDL configuration and standard
`MoveItSimpleControllerManager` trajectory actions. Robot configuration choices
are passed to both the simulation model and planning model. `play_motion2` keeps
the public motion library, receives explicit robot and kinematics parameters,
and uses namespaced joint, controller and planning interfaces. With MoveIt
disabled, unplanned motions remain available using `skip_planning: true`.

Nav2 uses official Jazzy localization, SLAM and navigation launch files in
separate scopes. The port copies inherited remap lists at launch scope
boundaries: Jazzy's `SetRemap` mutates inherited lists, which otherwise leaked
SLAM's `/map -> map` remap into costmap child namespaces. Map and sensor topics
are resolved per robot, and AMCL starts at the requested simulated spawn pose.
The public `advanced_navigation` flag selects the standard public Nav2 pipeline;
PAL's private navigation software is outside the public source distribution.

PMB2 uses Jazzy's
[Regulated Pure Pursuit controller](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/controller_plugins/configuring_regulated_pp/)
for path tracking, with global obstacle-layer replanning and collision monitoring.
DWB is retained as an alternative parameter block. Controller and smoothing
limits are bounded by the differential-drive controller's actual limits.
Live sensor bridges use sensor-data QoS to avoid
queuing lidar behind reliable retransmissions of large point clouds. Clock uses
the dedicated clock QoS profile. Shutdown service clients are created during
startup, allowing DDS request and reply discovery to settle before teardown;
navigation and localization/SLAM are shut down while TF and sensors remain live.

## Source overrides and shutdown

MoveIt 2.12.4 planning and move_group are explicitly overlaid to correct shared
library lifetimes during teardown. Controller-manager instances and callback
nodes are released before their plugin loaders; capability libraries remain
loaded until their ROS node has been destroyed. These fixes were driven by
observed shutdown backtraces, including the issues discussed upstream in
[MoveIt #3721](https://github.com/moveit/moveit2/issues/3721).

The pinned `ros_gz` source overrides stop transport subscriptions before ROS
publisher, factory and context teardown. The image bridge previously allowed a
callback to publish through a destroyed image_transport publisher. The parameter
bridge also retained a node/handle ownership cycle until process exit. Native
ROS pre-shutdown callbacks disconnect transport while its publishers are valid.

## Warning review

The remaining warning inventory must be checked against each acceptance log.
Controller update rate 100 Hz versus physics 1000 Hz is intentional. Temporary
resource-manager initialization messages occur before the ordered spawner can
activate controllers. The Jazzy system hardware plugin does not implement the
newer hardware statistics interfaces; that warning does not affect control.
`gz_frame_id` is the Gazebo sensor extension used to preserve ROS frame names.

The public model omits separate collision geometry for sensors, caster forks
and a decorative base cover. These parts are contained by the base collision
envelope; this must be considered when comparing the public model's collision
fidelity. FT inertia previously contained zero tensors; the port uses a uniform
cylinder approximation from the public masses and dimensions. It is a simulation
approximation, not a measured hardware inertia.

No crash, failed plugin load, inactive controller, missing TF, invalid sensor
payload or forced termination is an acceptable warning. The smoke runner fails
on these log signatures and retains the complete logs.

