# Running the TIAGo simulator on a Mac

ROS 2 Jazzy and Gazebo Harmonic do not run natively on macOS, so this folder runs
[tiago_jazzy_ws](../tiago_jazzy_ws/README.md) in an Ubuntu 24.04 container. It is native
arm64 on Apple Silicon. Gazebo and RViz appear in a browser tab through noVNC.

Needs [Docker Desktop](https://www.docker.com/products/docker-desktop/) with about 8 GB of
memory (Settings, Resources, Memory). That is enough because `setup` compiles one package
at a time; compiling `ros_gz_bridge` and MoveIt together runs out of memory. With more
memory, `mac/tiago.sh setup --parallel-workers 2` is faster. From the repository root:

```bash
mac/tiago.sh image   # Jazzy, Harmonic and the workspace's dependencies (a few minutes)
mac/tiago.sh up      # start the container; prints the desktop link
mac/tiago.sh setup   # build the workspace into tiago_jazzy_ws/ (about 15 min on an M1 Max)
mac/tiago.sh sim     # launch TIAGo with Nav2, Gazebo and RViz
```

Open the link that `up` and `sim` print. It includes the container's random VNC password,
which keeps other web pages in your browser from connecting to the desktop.

The browser page shows total system CPU usage and each TIAGo pipeline's CPU usage above
the remote desktop. Start `contention_scheduler pipelines.launch.py` to populate these
readings; the page indicates when the monitor is not running. Gazebo's main window
opens maximized. Run `mac/tiago.sh up` to apply these desktop settings to an existing
container, then use its new `desktop.html` link. Restart the pipeline launch after
updating the code so it publishes CPU samples for the page; an image rebuild is not
required for an existing container.

`mac/tiago.sh sim world_name:=empty` passes extra launch arguments (see
[the launch reference](../tiago_jazzy_ws/docs/launch.md)). `mac/tiago.sh shell` opens a
shell with Jazzy and the overlay sourced, for `ros2 topic` and the like. `mac/tiago.sh down`
removes the container; the build in `tiago_jazzy_ws/` stays, so `up` and `sim` work again
without rebuilding. Rerun `image` after the source bundle changes; the next `up` replaces
the container with one from the new image.

Limits:

- Rendering is software (Mesa llvmpipe), because Docker on a Mac has no GPU access. With
  Gazebo and RViz open, the simulation ran at about a quarter of real time on an M1 Max.
  Sensor rates are in simulated time, so they stay correct, but timing results should
  still come from a Linux machine.
- The `build/` and `install/` directories this creates are for the container only. Do not
  copy them to an Ubuntu machine; build there with `./setup.sh` as usual.
