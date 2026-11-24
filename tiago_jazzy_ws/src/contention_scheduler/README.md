# contention_scheduler

Each robot has its own Python process running a scan filter (on each scan), local map
(5 Hz), and braking controller (20 Hz). Linux schedules the actual computation; results
take effect immediately after each step finishes. The robots drive at 0.3 m/s and stop
when an obstacle is inside the strip 1 m ahead of the laser and as wide as the robot.

Run it after the robots are up (`contention_world`):

```bash
ros2 launch contention_world two_tiagos.launch.py
ros2 launch contention_scheduler pipelines.launch.py                 # two pipeline processes
ros2 launch contention_scheduler pipelines.launch.py robots:=tiago1  # only tiago1's pipeline
ros2 run contention_world place_box 6.0 --hallway 1                  # a box ahead of tiago1
```

Choose one pipeline launch at a time. With `robots:=tiago1`, the second robot stays still.
On Docker, run ROS commands through `mac/tiago.sh shell -c '...'` from the repo root.

The monitor prints the pipeline PIDs and updates once per wall-clock second. Example:

```text
Total system: 28.40% | tiago1: 0.15% | tiago2: 0.12%
```

The same readings appear above the browser desktop opened by `mac/tiago.sh up`.
Alongside each robot's CPU usage, the page shows its `check_hazard` service result:
`Hazard detected`, `Path clear`, or `Unknown`. The monitor calls both services on
each CPU update, with a short timeout so an unavailable service does not hold up the
display. The page clears stale CPU readings and resets hazards to `Unknown` when the
monitor stops updating. These results describe the latest available map, not sensor
freshness. CPU allocation is unchanged.

Each pipeline also times its reaction to an obstacle (`reaction.py`). The clock starts at
the first laser scan that shows something in the stopping strip after the robot starts
driving, and stops when the pipeline sends its first stop command. It is reported on both
clocks, over nearly the same interval: simulated time from the scan's timestamp (when
Gazebo's laser took it), and real (wall-clock) time from when the scan's message was
published, after Gazebo rendered it and the bridge converted it. The simulated figure
moves in 50 ms steps, the controller's period, and changes from run to run with how the
timers line up (0.10 s or 0.20 s on the Mac). After the stop, the pipeline follows the
laser's distance to the obstacle until it stops shrinking, which is where the robot came
to rest. Each robot logs two lines per stop, for example (from a run on a Mac):

```text
[tiago1.pipeline]: Stop sent: reaction 0.100 s sim, 0.321 s real. Scan stamped 14.300 s sim, stop sent 14.400 s sim; the scan reached the pipeline 0.000 s real after it was published; obstacle 0.96 m ahead when first seen.
[tiago1.pipeline]: At rest 0.83 m from the obstacle.
```

The browser desktop shows the same next to each robot's CPU reading: `driving`, then
`reaction 0.10 s sim, 0.32 s real · stopped 0.83 m from the box`. If the robot drives on
(the box was moved, or it got within 5 cm, where the stopping zone doesn't reach), the
last reaction stays, with `driving again`, until the next stop replaces it. Distances are
from the laser, which sits about 2 cm behind the front of the base; in two runs on a Mac
they matched Gazebo's true positions to within 1 mm. The simulated figure uses the
pipeline's own ROS clock, which is only as current as the last `/clock` message it
handled, so it can read low when the process is kept waiting for the CPU; the real figure
has no such lag.

All percentages use the total Linux CPU capacity as their denominator: one fully busy
logical CPU on an eight-CPU system is 12.5%. Total system usage comes from `/proc/stat`;
each robot's user + kernel CPU time comes from `/proc/PID/stat`, including its threads.
The robot values measure only their pipeline processes. The system total also includes
Gazebo, rendering, the monitor, and other programs, so robot usage does not sum to it.
On Fedora Docker Engine, these are host-system counters; on Mac, they describe Docker's
Linux VM. They are not percentages of a Docker CPU quota.

`pipelines.py` contains the single-robot ROS node. `cpu_monitor.py` starts and monitors
the processes, passes each one's latest reaction to the browser desktop, then stops them
when interrupted. `config/demo.yaml` sets speed and stop
distance. Low usage is expected for this small workload; no artificial CPU load is added.
No priorities, quotas, or allocation policy are set. The old `virtual_cpu.py` and its
tests remain as reference code and are not used by the launch.

Each pipeline also provides a `check_hazard` ROS 2 service. With both pipelines running,
check either robot from another sourced ROS terminal:

```bash
ros2 service call /tiago1/check_hazard std_srvs/srv/Trigger '{}'
ros2 service call /tiago2/check_hazard std_srvs/srv/Trigger '{}'
```

The request is empty. `success: true` means the check completed; `message` is either
`Hazard detected` or `Path clear`. Before the first map, it returns `success: false`
and `No scan map available yet`. The service uses the latest available local map and
the same stopping strip as the braking controller; it does not check data freshness.
Existing braking continues independently of service calls. The callback has a TODO
for future CPU allocation; it does not change CPU allocation now.

After updating the package, rebuild it from the repository root on the host, then open
a new container shell with the updated overlay sourced:

```bash
mac/tiago.sh setup --packages-select contention_scheduler
mac/tiago.sh shell
```

For repeatable trials, follow the [trial instructions](../contention_world/README.md#repeatable-trials);
the trial launch starts both pipelines and the CPU monitor automatically, so each trial's
reaction times start fresh. CPU-accounting, hazard-service and reaction-timing checks run
inside the container with `colcon test --packages-select contention_scheduler`.
