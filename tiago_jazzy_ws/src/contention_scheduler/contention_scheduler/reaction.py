"""Time how quickly a robot's pipeline reacts to an obstacle, on both clocks.

Reaction time runs from the first laser scan that shows an obstacle in the stopping zone,
since the robot last started driving, to the first stop command after it. It is measured
on two clocks, over nearly the same interval:

  sim   from the scan's timestamp (when Gazebo's laser took it) to the stop command, in
        the pipeline's ROS time (simulated time in Gazebo); the robot keeps driving this
        long before it starts braking. It moves in steps of the controller's period.
  real  from when the scan's ROS message was published (after Gazebo rendered it and the
        bridge converted it) to the stop command, in wall-clock time; this is where Linux
        scheduling delays happen

After the stop, the gap to the obstacle is followed until it stops shrinking, which says
where the robot came to rest. This module only does the bookkeeping, so it needs no ROS.
"""

from dataclasses import dataclass

NEAR_BAND = 0.1          # readings this close to the nearest one count toward the gap (m)
SETTLE_TIME = 0.5        # compare gaps from scans this far apart in simulated time (s)
SETTLE_TOLERANCE = 0.01  # the robot is at rest once the gap changes by less than this (m)


def gap_ahead(points, half_width):
    """Distance from the laser to the nearest obstacle in the robot's path (m), or None.

    Takes the median of the readings within 10 cm of the nearest one, so laser noise does not
    pull the gap below the obstacle's real distance.
    """
    ahead = sorted(x for x, y in points if abs(y) < half_width)
    if not ahead:
        return None
    near = [x for x in ahead if x < ahead[0] + NEAR_BAND]
    return near[len(near) // 2]


@dataclass
class Sighting:
    """The first scan that showed the obstacle."""

    stamp: float      # the scan's timestamp, simulated time (s)
    published: float  # when its ROS message was published, wall clock (s)
    received: float   # when the pipeline received it, wall clock (s)
    gap: float        # how far ahead the obstacle was (m)


class ReactionTimer:
    """Follow one robot from driving, to seeing an obstacle, to stopping, to resting."""

    def __init__(self):
        self.driving = False  # robots start standing still
        self.sighting = None  # first scan showing an obstacle since the robot started driving
        self.result = None    # the latest reaction, as a dict ready to log and display
        self.settling = None  # (scan timestamp, gap) to compare against while coming to rest

    @property
    def watching(self):
        """Does the pipeline need to check scans right now? Saves work while it doesn't."""
        return (self.driving and self.sighting is None) or self.settling is not None

    @property
    def needs_gap(self):
        """Does the next scan's gap matter, whatever it shows?"""
        return self.settling is not None

    def scan(self, obstacle, gap, stamp, published, received):
        """Note a checked scan. Returns 'rest' when the robot has just come to rest."""
        if self.driving and obstacle and self.sighting is None:
            self.sighting = Sighting(stamp, published, received, gap)
        if self.settling is None or self.result is None or gap is None:
            return None
        then, before = self.settling
        # Scan timestamps, not the node's clock: scans that queued up while the process
        # waited for the CPU still say when the laser took them.
        if before is not None and stamp - then < SETTLE_TIME:
            return None
        if before is not None and abs(gap - before) < SETTLE_TOLERANCE:
            self.settling = None
            self.result['rest_gap'] = gap
            return 'rest'
        self.settling = (stamp, gap)
        return None

    def command(self, stopping, now, wall):
        """Note a speed command just sent at simulated time `now` and wall-clock time `wall`.

        Returns 'stop' for the stop that ends a reaction, 'drive' when the robot starts
        driving again, and None otherwise.
        """
        event = None
        if stopping and self.driving and self.sighting is not None:
            seen = self.sighting
            self.result = {
                'reaction_sim': now - seen.stamp,
                'reaction_real': wall - seen.published,
                'delivery_real': seen.received - seen.published,
                'scan_stamp': seen.stamp,
                'stop_sim': now,
                'seen_gap': seen.gap,
                'rest_gap': None,
            }
            self.settling = (now, None)  # the first scan after the stop sets the reference
            event = 'stop'
        elif not stopping and not self.driving:
            # Moving again: time the next obstacle afresh. The last result stays until a new
            # stop replaces it, so a robot that creeps on into the obstacle doesn't erase it.
            self.sighting = self.settling = None
            event = 'drive'
        self.driving = not stopping
        return event
