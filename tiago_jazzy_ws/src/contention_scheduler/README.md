# contention_scheduler

Every robot's navigation pipeline, all running on one virtual CPU core that hands out
time round robin. Two files hold all of it:

- `contention_scheduler/virtual_cpu.py`: the core. Jobs wait in one line; each simulated
  millisecond, the job at the front runs for one tick and goes to the back. It reports
  when each job would have finished. Plain Python, no ROS.
- `contention_scheduler/pipelines.py`: the ROS node. For each robot it runs a scan filter
  (on every scan, 10 Hz), a local map (5 Hz), and a braking controller (20 Hz). Each step
  computes its answer at once, but the answer only takes effect when the core says the
  job would have finished. So competition for the core becomes reaction delay in
  simulated time, without loading the real CPU.

Run it after the robots are up (`contention_world`):

```bash
ros2 launch contention_world two_tiagos.launch.py
ros2 launch contention_scheduler pipelines.launch.py                 # both robots compete
ros2 launch contention_scheduler pipelines.launch.py robots:=tiago1  # tiago1 has the core alone
ros2 run contention_world place_box 6.0 --hallway 1                  # a box ahead of tiago1
```

The robots drive at 0.3 m/s and stop when anything is inside the strip 1 m ahead of the
laser and as wide as the robot. Every 2 s (simulated) the node logs how busy the core was,
each robot's position, and each step's average time from release to finish. When a robot
stops for an obstacle, it logs the reaction time, from the first scan that showed it to
the stop command.

**The task costs in `config/demo.yaml` are placeholders**, picked so that two robots keep
the core about 90% busy and visibly slow each other. Measure each step on the lab machine
before any real trials. Not built yet: the priority rule, phantom robots, and dropping
stale jobs when the core is overloaded.

`colcon test --packages-select contention_scheduler` checks the core against schedules
worked out by hand.
