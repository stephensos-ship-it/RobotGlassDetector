"""A model of one CPU core that every robot's tasks share, scheduled round robin.

Nothing here touches the real CPU. Each job states how many milliseconds of CPU time it
needs (its cost). The model hands out the core one millisecond (one tick) at a time, in
turn, and reports when each job would have finished. All times are simulated
milliseconds. There is no ROS in this file, so its tests run anywhere.
"""

from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass
class Job:
    robot: str          # whose pipeline the job belongs to, for example 'tiago1'
    task: str           # which step: 'filter', 'map' or 'control'
    cost: int           # CPU time it needs, in ticks (ms)
    release: int        # when it became ready, in simulated ms
    result: Any = None  # the step's answer, held back until the job finishes
    remaining: int = 0  # ticks still to run; set from cost
    finish: int = -1    # when it finished, once it has

    def __post_init__(self):
        if self.cost < 1:
            raise ValueError(f'{self.robot} {self.task}: a job needs at least 1 ms of CPU')
        self.remaining = self.cost


class RoundRobinCPU:
    """One core. Each tick, the job at the front of the line runs, then goes to the back."""

    def __init__(self, start_ms):
        self.now = start_ms    # every tick before this has been simulated
        self.line = deque()    # jobs waiting for the core, in turn order
        self.busy_ticks = 0    # ticks that ran a job, for the busy fraction

    def submit(self, job):
        """Put a newly released job at the back of the line."""
        if job.release != self.now:
            raise ValueError(f'run_until({job.release}) before submitting a job released then')
        self.line.append(job)

    def run_until(self, time_ms):
        """Simulate every tick from now up to time_ms; return the jobs that finished."""
        finished = []
        while self.now < time_ms:
            if self.line:
                job = self.line.popleft()
                job.remaining -= 1
                self.busy_ticks += 1
                if job.remaining == 0:
                    job.finish = self.now + 1
                    finished.append(job)
                else:
                    self.line.append(job)
            self.now += 1
        return finished
