"""Every robot's navigation pipeline, all sharing one virtual CPU core.

Each robot runs three steps, at fixed rates like a real navigation stack:

  filter   on every laser scan (10 Hz): keep valid readings ahead, as (x, y) points in metres
  map      every 200 ms: the set of 10 cm grid cells those points fall in
  control  every 50 ms: stop if any occupied cell is in the stopping zone, else drive

A step computes its answer as soon as it fires, then hands the virtual CPU a job carrying
that answer. The answer takes effect only when the CPU model says the job would have
finished; until then the robot keeps acting on the previous one. That is how competition
for the core becomes reaction delay, in simulated time, without loading the real CPU.
"""

import math

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

from contention_scheduler.virtual_cpu import Job, RoundRobinCPU

CELL = 0.1          # local map grid size (m)
MAP_REACH = 3.0     # the map covers this far ahead and to each side (m)
HALF_WIDTH = 0.35   # half the stopping zone's width: TIAGo's radius plus a margin (m)
TASKS = ['filter', 'map', 'control']


def cell(x, y):
    """The map cell a point falls in, as (column ahead, row to the left)."""
    return round(x / CELL), round(y / CELL)


class Robot:
    """One robot's topics and the latest answer each of its steps has published."""

    def __init__(self, name):
        self.name = name
        self.points = None      # filter's latest answer; None until its first job finishes
        self.cells = None       # map's latest answer; None until it has had points to map
        self.stopped = True     # what control last told the wheels; robots start standing still
        self.x = float('nan')   # true position along the hallway, for the status line
        self.seen_ms = None     # when a scan first showed something in the stopping zone
        self.cmd_vel = None
        self.waits = {task: [] for task in TASKS}  # release-to-finish times since the last report


class Pipelines(Node):

    def __init__(self):
        super().__init__('pipelines')
        names = self.declare_parameter('robots', 'tiago1 tiago2').value.split()
        self.speed = self.declare_parameter('speed', 0.3).value
        self.stop_distance = self.declare_parameter('stop_distance', 1.0).value
        self.costs = {task: self.declare_parameter(f'cost_{task}_ms', 1).value for task in TASKS}
        self.cpu = None  # created once simulated time is running
        self.robots = {}
        for name in names:
            robot = Robot(name)
            self.robots[name] = robot
            robot.cmd_vel = self.create_publisher(Twist, f'/{name}/cmd_vel', 10)
            self.create_subscription(LaserScan, f'/{name}/scan_raw',
                                     lambda msg, r=robot: self.filter(r, msg),
                                     qos_profile_sensor_data)
            self.create_subscription(Odometry, f'/{name}/ground_truth_odom',
                                     lambda msg, r=robot: self.track(r, msg),
                                     qos_profile_sensor_data)
            self.create_timer(0.2, lambda r=robot: self.map(r))
            self.create_timer(0.05, lambda r=robot: self.control(r))
        self.create_timer(0.001, lambda: self.advance(self.now_ms()))
        self.create_timer(2.0, self.report)
        self.last_report = (0, 0)  # (CPU time, busy ticks) at the previous status line
        self.get_logger().info(f'robots {names}, costs (ms) {self.costs}, speed {self.speed} m/s')

    # The three steps. Each computes its answer now and hands it to the CPU as a job.

    def filter(self, robot, scan):
        points = []
        for i, distance in enumerate(scan.ranges):
            if scan.range_min < distance < scan.range_max:
                angle = scan.angle_min + i * scan.angle_increment
                x, y = distance * math.cos(angle), distance * math.sin(angle)
                if x > 0:
                    points.append((x, y))
        if robot.seen_ms is None and any(self.blocks(cell(x, y)) for x, y in points):
            robot.seen_ms = self.now_ms()  # the reaction-time clock starts here
        self.run(robot, 'filter', points)

    def map(self, robot):
        if robot.points is None:
            return  # no filtered scan yet
        cells = {cell(x, y) for x, y in robot.points if x < MAP_REACH and abs(y) < MAP_REACH}
        self.run(robot, 'map', cells)

    def control(self, robot):
        # With no map yet the robot can't know the path is clear, so it stays put.
        blocked = robot.cells is None or any(self.blocks(c) for c in robot.cells)
        command = Twist()
        command.linear.x = 0.0 if blocked else self.speed
        self.run(robot, 'control', command)

    def track(self, robot, odometry):
        """Not a pipeline step: the robot's true position, only for the status line."""
        robot.x = odometry.pose.pose.position.x

    def blocks(self, map_cell):
        """Is this cell in the stopping zone, the strip just ahead of the laser?"""
        ahead, left = map_cell[0] * CELL, map_cell[1] * CELL
        return 0.0 < ahead < self.stop_distance and abs(left) < HALF_WIDTH

    # The virtual CPU.

    def now_ms(self):
        return self.get_clock().now().nanoseconds // 1_000_000

    def run(self, robot, task, answer):
        """Hand a step's answer to the CPU as a job released now."""
        now = self.now_ms()
        self.advance(now)
        if self.cpu is not None:
            self.cpu.submit(Job(robot.name, task, self.costs[task], now, answer))

    def advance(self, now):
        """Bring the CPU model up to the current time and apply the jobs that finished."""
        if now == 0:
            return  # simulated time hasn't started yet
        if self.cpu is None:
            self.cpu = RoundRobinCPU(start_ms=now)
            self.last_report = (now, 0)
        for job in self.cpu.run_until(now):
            self.finish(job)

    def finish(self, job):
        """A job is done: its answer now takes effect."""
        robot = self.robots[job.robot]
        robot.waits[job.task].append(job.finish - job.release)
        if job.task == 'filter':
            robot.points = job.result
        elif job.task == 'map':
            robot.cells = job.result
        else:
            robot.cmd_vel.publish(job.result)
            stopping = job.result.linear.x == 0.0
            if stopping and not robot.stopped and robot.seen_ms is not None:
                self.get_logger().info(
                    f'{robot.name} stopping at x={robot.x:.2f} m: obstacle first in a scan at '
                    f'{robot.seen_ms / 1000:.3f} s, stop sent at {job.finish / 1000:.3f} s, '
                    f'reaction {job.finish - robot.seen_ms} ms')
            if robot.stopped and not stopping:
                robot.seen_ms = None  # moving again; time the next obstacle afresh
            robot.stopped = stopping

    def report(self):
        """Every 2 s: how busy the core was, and each step's average release-to-finish time."""
        then, busy_then = self.last_report
        if self.cpu is None or self.cpu.now - then < 1000:
            return  # nothing to report yet
        busy = 100 * (self.cpu.busy_ticks - busy_then) / max(1, self.cpu.now - then)
        self.last_report = (self.cpu.now, self.cpu.busy_ticks)
        parts = [f't={self.cpu.now / 1000:.1f} s, core {busy:.0f}% busy']
        for robot in self.robots.values():
            waits = ', '.join(f'{task} {sum(w) / len(w):.0f}' if w else f'{task} -'
                              for task, w in robot.waits.items())
            state = 'stopped' if robot.stopped else 'driving'
            parts.append(f'{robot.name} x={robot.x:.2f} m {state} (ms: {waits})')
            robot.waits = {task: [] for task in TASKS}
        self.get_logger().info(' | '.join(parts))


def main():
    rclpy.init()
    node = Pipelines()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
