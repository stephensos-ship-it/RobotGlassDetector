"""Launch tiago1 in hallway 1 and tiago2 in hallway 2: Gazebo Harmonic, no arms, no Nav2.

Each robot's topics live under its name, for example /tiago1/scan_raw and /tiago1/cmd_vel.
"""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

# Hallway centrelines from worlds/hallway.sdf.
ROBOTS = [('tiago1', '0.0'), ('tiago2', '2.2')]


def generate_launch_description():
    world = Path(get_package_share_directory('contention_world')) / 'worlds' / 'hallway.sdf'
    tiago = Path(get_package_share_directory('tiago_gazebo')) / 'launch' / 'tiago_gazebo.launch.py'
    actions = [
        DeclareLaunchArgument(
            'gzclient', default_value='True', choices=['True', 'False'],
            description='Open the Gazebo window',
        ),
    ]
    for index, (name, y) in enumerate(ROBOTS):
        first = index == 0
        actions.append(IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(tiago)),
            launch_arguments={
                'robot_name': name,
                'namespace': name,
                # The first robot starts Gazebo and publishes /clock; the second joins it.
                'launch_world': str(first),
                'publish_clock': str(first),
                'is_public_sim': 'True',
                'world_name': str(world),
                'navigation': 'False',
                'moveit': 'False',
                'arm_type': 'no-arm',
                'tuck_arm': 'False',
                'rviz': 'False',
                'gzclient': LaunchConfiguration('gzclient'),
                'x': '1.0',
                'y': y,
                'yaw': '0.0',
            }.items(),
        ))
    return LaunchDescription(actions)
