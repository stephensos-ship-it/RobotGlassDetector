# Licensing and upstream attribution

This workspace preserves each upstream repository's license, copyright notices,
authors, package maintainers and asset attribution. The top-level Apache-2.0
license applies to new port integration code. It does not relicense upstream
code, meshes, textures or world assets.

- PAL Robotics provides the original TIAGo, PMB2, gripper/Hey5/Robotiq models,
  controllers, launch files, motion libraries and world/navigation assets.
  Source repositories and exact revisions are recorded in `tiago_jazzy.repos`.
- The Tiago-Harmonic community provides the Jazzy migration baseline and forks.
  Its authors include Juan Carlos Manzanares Serrano, Francisco Martín Rico and
  Juan Sebastián Cely Gutiérrez. Original package attribution is retained.
- MoveIt is provided by the MoveIt community and its upstream contributors;
  the overlaid source files retain their BSD notices and package licenses.
- `ros_gz` and Gazebo are provided by Open Robotics / Open Source Robotics
  Foundation and contributors under their upstream licenses.
- Nav2, ROS 2, ros2_control and other apt dependencies retain their own licenses.

The native underactuation system uses reductions and gains from PAL's public
Hey5 configuration. The new implementation is Apache-2.0 port code. Updated PAL
gripper geometry/inertia and torso screen assets came from the preserved public
PAL Humble source, without changing that reference workspace.

The source bundle contains binary-capable Git patches and the new packages,
with pinned revisions and SHA-256 hashes. It preserves upstream license files;
distribute those files and notices with the source and corresponding binaries.
World and mesh assets may carry additional notices in their original directories.

