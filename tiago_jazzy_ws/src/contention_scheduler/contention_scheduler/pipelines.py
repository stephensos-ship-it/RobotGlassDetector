"""One robot's scan filter, local map and braking controller, executed directly."""

import math

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

CELL = 0.1         # local map grid size (m)
MAP_REACH = 3.0    # map reach ahead and to either side (m)
HALF_WIDTH = 0.35  # half the stopping zone's width (m)


class Pipeline(Node):
    """Run under a robot namespace, such as /tiago1 or /tiago2."""

    def __init__(self):
        super().__init__('pipeline')
        self.speed = self.declare_parameter('speed', 0.3).value
        self.stop_distance = self.declare_parameter('stop_distance', 1.0).value
        self.points = None
        self.cells = None
        self.cmd_vel = self.create_publisher(Twist, 'cmd_vel', 10)
        self.create_subscription(LaserScan, 'scan_raw', self.filter, qos_profile_sensor_data)
        self.create_timer(0.2, self.map)
        self.create_timer(0.05, self.control)

    def filter(self, scan):
        points = []
        for i, distance in enumerate(scan.ranges):
            if scan.range_min < distance < scan.range_max:
                angle = scan.angle_min + i * scan.angle_increment
                x, y = distance * math.cos(angle), distance * math.sin(angle)
                if x > 0:
                    points.append((x, y))
        self.points = points

    def map(self):
        if self.points is not None:
            self.cells = {
                (round(x / CELL), round(y / CELL))
                for x, y in self.points if x < MAP_REACH and abs(y) < MAP_REACH
            }

    def control(self):
        # Stay still until the first map is available.
        blocked = self.cells is None or any(
            0.0 < ahead * CELL < self.stop_distance and abs(left * CELL) < HALF_WIDTH
            for ahead, left in self.cells
        )
        command = Twist()
        command.linear.x = 0.0 if blocked else self.speed
        self.cmd_vel.publish(command)


def main():
    rclpy.init()
    node = Pipeline()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
