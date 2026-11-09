import math

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool


class ObstacleDetector(Node):
    def __init__(self):
        super().__init__('obstacle_detector')

        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('threshold', 0.5)

        scan_topic = self.get_parameter('scan_topic').value
        self.threshold = self.get_parameter('threshold').value

        self.subscription = self.create_subscription(
            LaserScan,
            scan_topic,
            self.scan_callback,
            10
        )

        self.publisher = self.create_publisher(
            Bool,
            'obstacle_detected',
            10
        )

        self.get_logger().info('Obstacle detector started')

    def scan_callback(self, msg):
        front_ranges = []

        for i, distance in enumerate(msg.ranges):
            angle = msg.angle_min + i * msg.angle_increment
            front_angle = math.atan2(math.sin(angle), math.cos(angle))

            if abs(front_angle) <= math.radians(30):
                if math.isfinite(distance) and msg.range_min <= distance <= msg.range_max:
                    front_ranges.append(distance)

        if not front_ranges:
            self.get_logger().warn('No valid front LiDAR readings')
            return

        closest = min(front_ranges)
        detected = closest < self.threshold

        result = Bool()
        result.data = detected
        self.publisher.publish(result)

        if detected:
            self.get_logger().warn(
                f'OBSTACLE DETECTED! Distance: {closest:.2f} m'
            )
        else:
            self.get_logger().info(
                f'Path clear. Distance: {closest:.2f} m'
            )


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleDetector()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()