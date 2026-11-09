# contention_world

Two hallways side by side for the stopping-distance trials. Each is 12 m long, 2 m wide,
and open at both ends, and they share the middle wall. Hallway 1's centreline is y = 0 and
hallway 2's is y = 2.2. Each hallway has a 0.4 m box waiting behind its outer wall until it
is moved into the robot's path.

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
