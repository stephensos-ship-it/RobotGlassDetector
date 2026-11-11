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
The page clears stale readings when the monitor stops updating.

All percentages use the total Linux CPU capacity as their denominator: one fully busy
logical CPU on an eight-CPU system is 12.5%. Total system usage comes from `/proc/stat`;
each robot's user + kernel CPU time comes from `/proc/PID/stat`, including its threads.
The robot values measure only their pipeline processes. The system total also includes
Gazebo, rendering, the monitor, and other programs, so robot usage does not sum to it.
On Fedora Docker Engine, these are host-system counters; on Mac, they describe Docker's
Linux VM. They are not percentages of a Docker CPU quota.

`pipelines.py` contains the single-robot ROS node. `cpu_monitor.py` starts and monitors
the processes, then stops them when interrupted. `config/demo.yaml` sets speed and stop
distance. Low usage is expected for this small workload; no artificial CPU load is added.
No priorities, quotas, or allocation policy are set. The old `virtual_cpu.py` and its
tests remain as reference code and are not used by the launch.

After updating the package, rebuild it and source the overlay. For the root Docker helper:

```bash
./tiago-docker.sh setup --packages-select contention_scheduler
./tiago-docker.sh
```

These two helper commands run from the directory above the repository. CPU-accounting
checks run with `colcon test --packages-select contention_scheduler`.
