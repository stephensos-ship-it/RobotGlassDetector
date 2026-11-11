"""Start a separate pipeline process per robot and print actual CPU usage."""

from pathlib import Path
import sys

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    settings = Path(get_package_share_directory('contention_scheduler')) / 'config' / 'demo.yaml'
    return LaunchDescription([
        DeclareLaunchArgument(
            'robots', default_value='tiago1 tiago2',
            description='Robots to control and monitor, separated by spaces',
        ),
        ExecuteProcess(
            cmd=[
                sys.executable, '-m', 'contention_scheduler.cpu_monitor',
                '--robots', LaunchConfiguration('robots'), '--params-file', str(settings),
            ],
            output='screen',
        ),
    ])
