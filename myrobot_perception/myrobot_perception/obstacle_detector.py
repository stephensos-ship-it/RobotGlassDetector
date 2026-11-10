import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool


class ObstacleDetector(Node):
    def __init__(self):
        super().__init__('obstacle_detector')

        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('threshold', 0.5)

        scan_topic = self.get_parameter('scan_topic').value
        self.threshold = self.get_parameter('threshold').value
        
        self.was_obstacle_detected = False

        self.subscription = self.create_subscription(
            LaserScan,
            scan_topic,
            self.scan_callback,
            qos_profile_sensor_data
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

        timestamp = self.get_clock().now().to_msg()
        time_seconds = timestamp.sec + timestamp.nanosec / 1e9

        result = Bool()
        result.data = detected
        self.publisher.publish(result)

        if detected and not self.was_obstacle_detected:
            self.get_logger().warn(
                f'OBSTACLE FIRST DETECTED | '
                f'Time: {time_seconds:.3f} s | '
                f'Distance: {closest:.2f} m'
            )

        elif not detected and self.was_obstacle_detected:
            self.get_logger().info(
                f'OBSTACLE CLEARED | Time: {time_seconds:.3f} s'
            )

        self.was_obstacle_detected = detected


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