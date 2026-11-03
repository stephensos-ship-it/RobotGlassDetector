# Remaining issues and verified navigation scope

This handoff focuses on navigation, obstacle avoidance, base movement and
sensors. It is not a claim that the original full migration acceptance matrix
is complete.

The quoted results are historical development measurements. Raw build products
and execution logs are not distributed in this repository. The commands below
regenerate verification logs locally under `log/` on an Ubuntu machine.

## Verified

- PAL-office localization and a Nav2 goal pass with MoveIt disabled, including
  clean shutdown: `log/navigation-rpp/navigation/`.
- The physical obstacle scenario passes: lidar detects a newly inserted box,
  Nav2 reaches the goal behind it, measured clearance is **0.634 m** and the
  lateral detour is **0.930 m**. Startup, the stability interval and shutdown
  produce no error signatures: `log/navigation-rpp/obstacle/`.
- RGB, depth, camera info, point cloud, lidar, IMU, odometry, sensor transforms,
  advancing clock and active controllers pass the runtime verifier.
- The latest stored regression results contain 51 passing source/launch cases
  in `tiago_jazzy_port` and five passing lint cases in `tiago_2dnav`, with no
  failure/error entries. These are JUnit testcase counts, excluding CTest's
  additional result entries.
- Rosdep reports all current source dependencies satisfied. The exported bundle
  contains 21 pinned repositories and two local packages with verified hashes.

Recommended launch after sourcing Jazzy and the overlay:

```bash
ros2 launch tiago_gazebo tiago_gazebo.launch.py \
  is_public_sim:=True navigation:=True moveit:=False tuck_arm:=False
```

PMB2 now uses Jazzy's Regulated Pure Pursuit tracker, with DWB retained as an
alternative parameter block. The simulated arm/torso initialize in PAL's folded
home posture, so navigation does not require an arm-planning process.

## 1. SLAM shutdown remains an acceptance failure

Mapping and the navigation goal pass. Both navigation and SLAM lifecycle
shutdown services report success. Gazebo subsequently fails to exit after
SIGINT/SIGTERM and launch escalates to SIGKILL. This is a real cleanup issue,
not a harmless warning; the smoke harness correctly returns failure.

Evidence: `log/navigation-rpp/slam/verification.log`, `launch.log`, and
`log/navigation-rpp/results.json`. The latter records localization as passing
and SLAM as failing because of shutdown.

```bash
ros2 run tiago_jazzy_port run_smoke.py --world pal_office --slam \
  --duration 15 --domain 81 --log-dir log/slam-shutdown-repro
```

Next diagnostic: capture the Gazebo server's thread backtraces during the
shutdown stall, before launch's forced termination. The remaining blocker is
server teardown; the latest run did receive a map and complete its goal.

## 2. Multi-robot navigation is experimental

Earlier runs completed goals for both robots, and measured control/sensor
binding isolation passed. Subsequent runs intermittently stalled during Nav2
lifecycle activation. One map-server response was lost with Fast DDS; this
matches the symptoms described in
[rmw_fastrtps #842](https://github.com/ros2/rmw_fastrtps/issues/842), though that
does not establish the cause of every failed run.

Creating shutdown clients at startup fixed the tested single-robot teardown
path. The final Regulated Pure Pursuit configuration has not received a passing
multi-robot acceptance rerun. Use the single-robot launch for the verified scope.

```bash
python3 tools/run_acceptance_matrix.py --output log/multi-repro \
  --case multi-navigation
```

Cyclone DDS comparisons also exposed sensor/TF timing failures. It is not the
recommended runtime here. Its optional configuration file increases the
participant-index limit, but does not constitute passing multi-robot acceptance.

## 3. RGB-D throughput and Nav2 sensor integration

The software-rendered obstacle snapshot observed these receive rates per second
of simulation time: lidar 10.0, RGB 23.45, depth 20.28, registered cloud 1.86,
IMU 77.38 and odometry 49.85. These are observed subscriber rates, not guaranteed
publisher frequencies or hardware-rendering benchmarks. The snapshot is saved
at `log/navigation-rpp/obstacle/interfaces.json`.

The cloud is valid and its optical frame resolves, but high-rate 3D avoidance
has not been performance-qualified. Test it on the intended GPU/workload before
depending on a higher cloud rate. Live sensor topics use Best Effort sensor-data
QoS; custom subscribers must choose compatible QoS.

Nav2's current costmaps use lidar. RGB-D streams are available for perception
or a separately configured depth observation source; depth-cloud obstacle
integration is not claimed as tested. Direct manual velocity commands also do
not acquire Nav2's path planning and collision-monitor behavior.

## 4. Deferred full-migration work

- The final 57-package build from a fresh source reconstruction was interrupted.
  An earlier 56-package reconstruction built, and the current development
  overlay builds, but this is not a completed final clean-build certification.
- The latest full-suite rerun retained two failure entries from the arm-tuck
  launch test. Representative arm/MoveIt actions passed earlier; full arm
  acceptance and additional end-effector reruns are deferred.
- Historical GUI rendering/window-close checks passed. They were not repeated
  after the final navigation tracker and sensor-QoS changes.
- Classic worlds with private/random-actor libraries or embedded REEM robot
  systems remain unported and are explicitly rejected. PAL office, empty and
  the native physical-obstacle test room are supported paths.

No failing acceptance cases were removed or relabeled as passing. Historical
runs are retained in `log/`; use the paths above for the final navigation scope.
