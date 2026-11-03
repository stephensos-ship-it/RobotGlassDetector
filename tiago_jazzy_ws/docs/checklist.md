# Migration acceptance checklist

The current user acceptance scope is navigation, obstacle avoidance, base motion
and sensors. Full arm parity is deferred. Runtime evidence is recorded in
`log/` and summarized in `docs/testing.md`; build success alone is insufficient.

- [x] Isolated Jazzy source workspace; Humble reference preserved.
- [x] Official Ubuntu Noble/Jazzy development image; rosdep baseline resolves.
- [x] All 57 current packages discovered; no COLCON_IGNORE.
- [x] Headless Harmonic server, robot spawn, clock, odometry TF, lidar payload.
- [x] Pinned source manifest and distributable patch bundle.
- [x] Current PAL office world and public Nav2 configuration.
- [ ] Clean startup and shutdown; investigate all warnings.
- [x] Configuration matrix: omni base, no arm, all exposed end-effector models.
- [x] Measured base displacement, watchdog stop and representative joint actions.
- [x] RGB, depth, point cloud, IMU, FT payloads and sensor TF verified.
- [x] Representative MoveIt planning/execution (outside current acceptance scope).
- [x] Nav2 localization and representative goal completion.
- [x] Physical obstacle detection and measured Nav2 detour with clean shutdown.
- [x] SLAM map publication and goal completion.
- [ ] Combined modes stability and multi-robot isolation.
- [ ] Full colcon test suite passes.
- [ ] Clean rebuild and rosdep on fresh source import.
- [x] Native Ubuntu guide, Fedora guide, compatibility and attribution.

The full-suite and clean-rebuild boxes concern the original full migration.
The latest full-suite failure entries are from the arm-tuck launch test.
Navigation-specific tests are reported separately; they must pass without
excluding sensor, controller, TF or navigation errors.
The final localization and physical-obstacle cases pass. SLAM's functional
checks pass, but its shutdown remains an explicit failing acceptance case.
See `docs/remaining-issues.md` for details and reproduction commands.

Classic actor-library and embedded REEM demo worlds remain unported. They are
explicitly rejected. PAL office, empty worlds and the native physical-obstacle
acceptance room use Harmonic systems throughout.
