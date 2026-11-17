# contention_world

Two hallways side by side for the stopping-distance trials. Each is 12 m long and 2 m
wide. They share a middle wall and an end wall at x = 12 m. Green finish markings at
x = 10 m are visual only, so they do not block lidar or movement. Hallway centrelines
are y = 0 and y = 2.2. Each hallway has a 0.4 m box parked behind its outer wall.

## Repeatable trials

From the repository root on the host, rebuild this package after updating it and open
a container shell (the workspace must already be set up):

```bash
mac/tiago.sh up
mac/tiago.sh setup --packages-select contention_world
mac/tiago.sh shell
```

Inside the container, run one of these commands:

```bash
# No obstacles: both robots finish at x = 10 m
ros2 launch contention_world trial.launch.py scenario:=clear

# Obstacle in hallway 1
ros2 launch contention_world trial.launch.py scenario:=obstacle hallway:=1

# Obstacle in hallway 2
ros2 launch contention_world trial.launch.py scenario:=obstacle hallway:=2
```

Add `gzclient:=False` to any trial command to run without the Gazebo window. These ROS
commands also work in a native ROS shell with the workspace sourced.

Each command starts a fresh world, controllers, both pipeline processes, and the CPU
monitor. Run one trial at a time; no separate world or pipeline launch is needed. It holds
the robots at x = 1 m until both have odometry, scans, and pipeline commands, then warms
up for one simulated second before releasing them. A finish stop remains latched until
the trial ends, even if the measured position fluctuates around the finish line.

In the obstacle scenario, the selected robot crossing x = 4 m triggers placement of its
box at x = 6 m. The other robot continues to the finish. The selected robot must publish
a zero forward command and remain below 0.01 m/s and 0.01 rad/s for 0.5 simulated seconds
to satisfy its obstacle stopping condition. The runner then holds it there while both
pipelines continue processing until the other robot finishes. Finish stops must also be
confirmed from ground-truth velocity. Contacts with any trial wall or box fail the run.
The running phase times out after 45 simulated seconds; wall-clock guards catch missing
startup data or a stalled simulation.

The runner prints PASS or FAIL and ends the launch after stopping both robots. Failed
trials return a nonzero exit status. Rerunning the command resets all simulation and
pipeline state; do not run a trial alongside an existing manual simulation.

The runner is entirely in this package. It uses the existing higher-priority `key_vel`
input for start, finish, and terminal holds. During the obstacle approach it does not
override braking or change `/cmd_vel`; perception and pipeline code are unchanged.
`/trial/status` publishes the latest lifecycle state for other tools. BOX_PLACED means
Gazebo acknowledged the request, not an exact timestamp of the physical placement.
Reaction-time measurement belongs to the separate logger; none is calculated here.
That logger should also restart per trial because simulation time starts over.

## Manual world

One robot, in hallway 1 (topics without a namespace: `/scan_raw`, `/cmd_vel`):

```bash
ros2 launch contention_world hallway.launch.py          # add gzclient:=False for headless
```

Two robots, `tiago1` in hallway 1 and `tiago2` in hallway 2 (topics under each name, for
example `/tiago1/scan_raw` and `/tiago2/cmd_vel`):

```bash
ros2 launch contention_world two_tiagos.launch.py       # add gzclient:=False for headless
```

Both start at x = 1 m facing down their hallway, with no arm and no Nav2. To drive them,
start the pipelines (`contention_scheduler`). Moving the boxes:

```bash
ros2 run contention_world place_box 6.0                 # hallway 1's box at x = 6 m
ros2 run contention_world place_box 6.0 --hallway 2     # hallway 2's box at x = 6 m
ros2 run contention_world place_box --hide              # park hallway 1's box again
```

On a Mac, run these through `mac/tiago.sh shell -c '...'`. Each robot's laser is
`scan_raw` (best-effort QoS), its velocity input is `cmd_vel` (`geometry_msgs/Twist`), and
its true pose is on `ground_truth_odom`. `colcon test --packages-select contention_world`
checks the world's geometry, and that `place_box` and the two-robot launch agree with it.
These manual launches do not run the trial supervisor; use `trial.launch.py` for the
automatic finish stop and repeatable scenarios.

Timing notes for the trials:

- A command on `cmd_vel` passes through `twist_mux` and then the port's
  `simulation_adapter`, which forwards the latest command to the base controller every
  50 ms. So a stop command reaches the wheels 0–50 ms (simulated) after it is published.
  The adapter sends zero velocity for any command older than 250 ms, so publish at
  4 Hz or faster.
- `place_box` starts the `gz` command-line tool, so the moment the box appears is not
  precise. The trial runner should call `/world/hallway/set_pose` itself and record the
  simulated time it took effect. A moved box blocks the robot physically as well as
  showing up to the lidar.
- On a Mac, two robots run at about 0.18 of real time with no Gazebo window.

This package lives in `src/` beside the pinned upstream checkouts. The repository's
`.gitignore` tracks `src/contention_*` and ignores everything else there.
