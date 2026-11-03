"""Launch TIAGo at the start of the trial hallway: Gazebo Harmonic, no arm, no Nav2."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    world = Path(get_package_share_directory('contention_world')) / 'worlds' / 'hallway.sdf'
    tiago = Path(get_package_share_directory('tiago_gazebo')) / 'launch' / 'tiago_gazebo.launch.py'
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(tiago)),
        launch_arguments={
            'is_public_sim': 'True',
            'world_name': str(world),
            # Our own pipeline drives TIAGo. Nav2 would also need a hallway map.
            'navigation': 'False',
            'moveit': 'False',
            # Only the base matters here; dropping the arm keeps the simulation light.
            'arm_type': 'no-arm',
            'tuck_arm': 'False',
            'gzclient': LaunchConfiguration('gzclient'),
            'x': LaunchConfiguration('x'),
            'y': '0.0',
            'yaw': '0.0',
        }.items(),
    )
    return LaunchDescription([
        DeclareLaunchArgument(
            'gzclient', default_value='True', choices=['True', 'False'],
            description='Open the Gazebo window',
        ),
        DeclareLaunchArgument(
            'x', default_value='1.0', description="TIAGo's start, in metres along the hallway",
        ),
        simulation,
    ])
