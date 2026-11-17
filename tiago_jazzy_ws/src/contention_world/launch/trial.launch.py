"""One fresh world and pipeline pair per trial; shut everything down when it ends."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription, RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def end_trial(event, context):
    if context.is_shutdown:
        return []
    if event.returncode:
        raise RuntimeError('Trial failed; see the run_trial output above.')
    return [EmitEvent(event=Shutdown(reason='Trial completed'))]


def generate_launch_description():
    world = Path(get_package_share_directory('contention_world'))
    pipelines = Path(get_package_share_directory('contention_scheduler'))
    runner = Node(
        package='contention_world', executable='run_trial', output='screen',
        parameters=[{'use_sim_time': True, 'scenario': LaunchConfiguration('scenario'),
                     'hallway': LaunchConfiguration('hallway')}],
    )
    return LaunchDescription([
        DeclareLaunchArgument('scenario', default_value='clear', choices=['clear', 'obstacle']),
        DeclareLaunchArgument('hallway', default_value='1', choices=['1', '2']),
        DeclareLaunchArgument('gzclient', default_value='True', choices=['True', 'False']),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(world / 'launch/two_tiagos.launch.py')),
            launch_arguments={'gzclient': LaunchConfiguration('gzclient')}.items(),
        ),
        Node(package='ros_gz_bridge', executable='parameter_bridge', output='screen',
             arguments=['/trial/contacts@ros_gz_interfaces/msg/Contacts[gz.msgs.Contacts']),
        RegisterEventHandler(OnProcessExit(
            target_action=runner, on_exit=end_trial)),
        runner,
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(pipelines / 'launch/pipelines.launch.py')),
        ),
    ])
