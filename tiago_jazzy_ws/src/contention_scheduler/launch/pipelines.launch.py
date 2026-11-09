"""Start every robot's pipeline on one virtual CPU core. Start the robots first.

  ros2 launch contention_scheduler pipelines.launch.py                 both robots compete
  ros2 launch contention_scheduler pipelines.launch.py robots:=tiago1  tiago1 has the core alone
"""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    settings = Path(get_package_share_directory('contention_scheduler')) / 'config' / 'demo.yaml'
    return LaunchDescription([
        DeclareLaunchArgument(
            'robots', default_value='tiago1 tiago2',
            description='Robots whose pipelines run on the core, separated by spaces',
        ),
        Node(
            package='contention_scheduler',
            executable='pipelines',
            parameters=[
                str(settings),
                {'use_sim_time': True, 'robots': LaunchConfiguration('robots')},
            ],
            output='screen',
        ),
    ])
