# Verification and current acceptance status

Acceptance is focused on navigation, obstacle avoidance, base motion and sensors,
as requested. Arm perfection is outside this acceptance target. A successful
build or action return code alone does not establish physical simulation parity.
See [remaining issues](remaining-issues.md) for the final handoff and limitations.

The final `navigation-rpp` run passed PAL-office localization and the physical
obstacle test (0.634 m clearance, 0.930 m detour), including clean shutdown.
SLAM's map and goal checks passed, but its overall case failed because Gazebo
required forced termination. The latest source/launch and navigation lint JUnit
results contain 56 passing testcases and no failure/error entries.

## Automated checks

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
colcon test --executor sequential --event-handlers console_cohesion+
colcon test-result --verbose
```

Sequential execution prevents upstream launch tests using the same controller
names and ROS domain from interfering. The source audit checks all package
manifests for Classic dependencies, rejects ignored packages, expands the robot
configuration matrix and constructs every maintained Python launch file.

The black-box smoke harness checks sensor payloads, physical FT measurements,
advancing time, TF, active controllers, base displacement and actual joint
displacement. Optional checks plan/execute a MoveIt motion, complete a Nav2 goal,
and receive a SLAM map. It retains launch and verification logs, runs a stability
interval, signals launch, and fails on crashes, failed plugins, Python tracebacks,
fatal bridge messages or forced process termination.

```bash
ros2 run tiago_jazzy_port run_smoke.py --help
ros2 run tiago_jazzy_port run_smoke.py --end-effector pal-hey5 --domain 74
ros2 run tiago_jazzy_port run_smoke.py --base omni_base --domain 75
ros2 run tiago_jazzy_port run_smoke.py --no-arm --camera no-camera --laser no-laser --domain 76
ros2 run tiago_jazzy_port run_smoke.py --multi --domain 77
ros2 run tiago_jazzy_port run_smoke.py --obstacle-check --snapshot --domain 85
python3 tools/run_acceptance_matrix.py --output log/navigation-check \
  --case navigation --case slam --case multi-navigation
```

Smoke tests serialize themselves because controller spawners share a ROS_HOME
lock even across DDS domains. Software-rendered tests
measure motion duration in simulation time and use bounded wall-clock deadlines.
Tests configure no skipped source packages. Ubuntu's cppcheck 2.13 is skipped
automatically by the upstream ament checker because of documented performance
problems; these reported test skips do not omit packages or runtime tests.

## GUI checklist

On a desktop launch the default world with `gzclient:=True`. Check the complete
robot, screen/tool variants, shadows, mesh textures, ground contact and joint
motion. Open MoveIt RViz, add the robot and planning-scene displays, plan and
execute a safe arm motion. For navigation, check map, both costmaps, lidar and
the map/odom/base TF chain; send a 2D goal and observe completion. During SLAM,
drive through unexplored space and confirm map growth and saved-map reload.
Close launch with Ctrl+C and check that its Gazebo and ROS children have exited.

## Acceptance evidence and remaining scope

Historical development logs are kept outside this portable checkout. The paths
below identify those runs; rerunning the documented commands creates local
`log/` output. Generated build/install/log directories are not distributed.

`log/acceptance-current/results.json` records passing measured control for
standalone TIAGo, Hey5, both Robotiq variants, no arm, no end effector and the omni
base. `log/acceptance-isolation/results.json` records passing PAL-office
localization, SLAM, screen/tool control, base control and Nav2 with MoveIt;
its failed cases remain visible. Later focused runs are under
`log/navigation-rpp/`. Inspect each case's verification and launch logs;
the harness rejects errors and failed shutdowns even if the goal succeeds.

The obstacle check uses an 8 m square mapped room. After a first goal it creates
a physical 0.4 m square box, requires lidar detection, then sends another goal
behind it. It records the driven detour and checks clearance against the
configured 0.275 m circular navigation footprint. The original run reached the
goal with 0.326 m clearance but required progress recoveries; it is retained as a
failure. PMB2 now uses Jazzy's Regulated Pure Pursuit path tracker; the previous
DWB configuration is retained as an alternative. Angular/acceleration limits
match the simulated base rather than predicting impossible 5 rad/s turns. The
robot initializes with PAL's arm/torso home posture for navigation without MoveIt.

Live image, cloud, lidar and IMU bridges use sensor-data QoS; clock uses clock
QoS. Select Best Effort reliability in sensor subscribers such as custom RViz
displays. These streams prioritize current samples over retransmitting old
clouds. Fast DDS is the current default. A multi-process lifecycle response race
was observed and is also reported in
[rmw_fastrtps #842](https://github.com/ros2/rmw_fastrtps/issues/842).
Shutdown clients are now created at startup so both request and reply endpoints
have time to discover each other. Navigation and localization/SLAM are stopped
before launch signals the simulator and TF publishers.

Cyclone DDS was also evaluated. Large-stream timing failures occurred in these
tests; it is not the default acceptance configuration. An optional
`tiago_jazzy_port/config/cyclonedds.xml` increases its participant-index limit
for multi-robot experiments. All terminals must use the same middleware choice.

Gazebo and MoveIt RViz rendering and normal window closure passed in
`log/gui-window-close/`. The stock MoveIt panel probes an optional
`recognize_objects` action that public TIAGo does not provide; this is reported
separately from planning/execution checks.

The source graph contains 57 packages. Rosdep resolved successfully in the rebuilt
Noble/Jazzy dependency image. An earlier 56-package source reconstruction built
cleanly; the final 57-package clean rebuild was interrupted and is not claimed
as complete. The full suite previously reported 1,934 tests without failures;
the latest full-suite rerun contains two failure entries for the arm-tuck launch
test. This is deferred arm work, not a passing full-migration acceptance result.
Archival demo worlds with embedded Classic actor/REEM systems are explicitly
rejected rather than silently loaded.

