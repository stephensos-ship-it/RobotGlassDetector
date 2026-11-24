"""One robot's scan filter, local map and braking controller, executed directly."""

import json
import math
from pathlib import Path
import signal
import time

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_srvs.srv import Trigger

from contention_scheduler.reaction import gap_ahead, ReactionTimer

CELL = 0.1         # local map grid size (m)
MAP_REACH = 3.0    # map reach ahead and to either side (m)
HALF_WIDTH = 0.35  # half the stopping zone's width (m)


class Pipeline(Node):
    """Run under a robot namespace, such as /tiago1 or /tiago2."""

    def __init__(self):
        super().__init__('pipeline')
        self.speed = self.declare_parameter('speed', 0.3).value
        self.stop_distance = self.declare_parameter('stop_distance', 1.0).value
        # Where to share the latest reaction for the desktop display; empty means only log it.
        status_file = self.declare_parameter('status_file', '').value
        self.status_file = Path(status_file) if status_file else None
        self.reaction = ReactionTimer()
        self.warned_no_publish_time = False
        self.points = None
        self.cells = None
        self.cmd_vel = self.create_publisher(Twist, 'cmd_vel', 10)
        self.create_subscription(LaserScan, 'scan_raw', self.filter, qos_profile_sensor_data)
        self.create_service(Trigger, 'check_hazard', self.check_hazard)
        self.create_timer(0.2, self.map)
        self.create_timer(0.05, self.control)

    def filter(self, scan, info):
        received = time.time()  # wall clock, before any work on this scan
        points = []
        for i, distance in enumerate(scan.ranges):
            if scan.range_min < distance < scan.range_max:
                angle = scan.angle_min + i * scan.angle_increment
                x, y = distance * math.cos(angle), distance * math.sin(angle)
                if x > 0:
                    points.append((x, y))
        self.points = points
        if self.reaction.watching:
            self.watch(scan, info, received)

    def map(self):
        if self.points is not None:
            self.cells = {
                (round(x / CELL), round(y / CELL))
                for x, y in self.points if x < MAP_REACH and abs(y) < MAP_REACH
            }

    def blocks(self, ahead, left):
        """Is this map cell in the stopping zone, the strip just ahead of the laser?"""
        return 0.0 < ahead * CELL < self.stop_distance and abs(left * CELL) < HALF_WIDTH

    def has_hazard(self):
        # return True if an occupied map cell is inside the stopping strip; braking, the
        # hazard service and reaction timing all use this same test
        return any(self.blocks(ahead, left) for ahead, left in self.cells or ())

    def check_hazard(self, request, response):
        if self.cells is None:
            response.success = False
            response.message = 'No scan map available yet'
            return response

        hazard = self.has_hazard()
        # implement CPU allocation based on the hazard result here
        response.success = True  # message contains the result, complete
        response.message = 'Hazard detected' if hazard else 'Path clear'
        return response

    def control(self):
        # Stay still until the first map is available.
        blocked = self.cells is None or self.has_hazard()
        command = Twist()
        command.linear.x = 0.0 if blocked else self.speed
        self.cmd_vel.publish(command)
        was_driving = self.reaction.driving
        event = self.reaction.command(blocked, self.sim_now(), time.time())
        result = self.reaction.result
        if event == 'drive' and result is not None:
            self.get_logger().info('Driving again after a stop.')
        if event == 'stop' and result is not None:
            self.get_logger().info(
                f"Stop sent: reaction {result['reaction_sim']:.3f} s sim, "
                f"{result['reaction_real']:.3f} s real. Scan stamped {result['scan_stamp']:.3f} s "
                f"sim, stop sent {result['stop_sim']:.3f} s sim; the scan reached the pipeline "
                f"{result['delivery_real']:.3f} s real after it was published; obstacle "
                f"{result['seen_gap']:.2f} m ahead when first seen.")
        if self.reaction.driving != was_driving:
            self.share()

    # Reaction timing. These measure the pipeline; they do not change what the robot does.

    def sim_now(self):
        """ROS time in seconds: simulated time in Gazebo."""
        return self.get_clock().now().nanoseconds / 1e9

    def watch(self, scan, info, received):
        """Check a filtered scan for the obstacle, or for the robot having come to rest."""
        # The publisher's wall-clock timestamp, when the middleware provides one.
        published = info.get('source_timestamp', 0) / 1e9
        if not published:
            published = received
            if not self.warned_no_publish_time:
                self.warned_no_publish_time = True
                self.get_logger().warning(
                    'The middleware gives no publish time; real reaction times start when '
                    'the pipeline receives the scan.')
        stamp = scan.header.stamp.sec + scan.header.stamp.nanosec / 1e9
        points = self.points or []
        # The controller's own test, on the same cells the map would put these points in;
        # the first two comparisons only skip points that can't be in the stopping zone.
        obstacle = any(
            x < self.stop_distance + CELL and abs(y) < HALF_WIDTH + CELL
            and self.blocks(round(x / CELL), round(y / CELL))
            for x, y in points
        )
        gap = None
        if obstacle or self.reaction.needs_gap:
            gap = gap_ahead(points, HALF_WIDTH)
        if self.reaction.scan(obstacle, gap, stamp, published, received):
            self.get_logger().info(f'At rest {gap:.2f} m from the obstacle.')
            self.share()

    def share(self):
        """Write the latest reaction where the CPU monitor picks it up for the display."""
        if self.status_file is None:
            return
        status = {**(self.reaction.result or {}), 'driving': self.reaction.driving}
        try:
            temporary = self.status_file.with_suffix('.tmp')
            temporary.write_text(json.dumps(status))
            temporary.replace(self.status_file)
        except OSError as error:
            self.get_logger().warning(f'Could not share the reaction time: {error}')


def main():
    rclpy.init()
    node = Pipeline()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Ctrl-C arrives twice, from the terminal and again from the CPU monitor; ignore the
        # repeat so it doesn't interrupt the shutdown.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
