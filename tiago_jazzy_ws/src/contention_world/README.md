# contention_world

The hallway for the stopping-distance trials: 12 m long, 2 m wide, open at both ends,
with TIAGo (no arm) spawned at x = 1 m facing down it. A 0.4 m box waits behind the right
wall until it is moved into the robot's path.

```bash
ros2 launch contention_world hallway.launch.py          # add gzclient:=False for headless
ros2 run contention_world place_box 6.0                 # box centre at x = 6 m
ros2 run contention_world place_box --hide              # park it out of sight again
```

On a Mac, run these through `mac/tiago.sh shell -c '...'`. Nav2 is off, since our own
pipeline drives TIAGo: publish `geometry_msgs/Twist` on `/cmd_vel`. The laser is
`/scan_raw` (best-effort QoS) and the true pose is on `/ground_truth_odom`.
`colcon test --packages-select contention_world` checks the world's geometry.

Timing notes for the trials:

- A command on `/cmd_vel` passes through `twist_mux` and then the port's
  `simulation_adapter`, which forwards the latest command to the base controller every
  50 ms. So a stop command reaches the wheels 0–50 ms (simulated) after it is published.
  The adapter sends zero velocity for any command older than 250 ms, so publish at
  4 Hz or faster.
- `place_box` starts the `gz` command-line tool, so the moment the box appears is not
  precise. The trial runner should call `/world/hallway/set_pose` itself and record the
  simulated time it took effect. The moved box blocks TIAGo physically as well as
  showing up to the lidar.

This package lives in `src/` beside the pinned upstream checkouts. The repository's
`.gitignore` tracks `src/contention_*` and ignores everything else there.
