"""Check the round-robin core against schedules worked out by hand."""

import pytest

from contention_scheduler.virtual_cpu import Job, RoundRobinCPU


def finishes(cpu, until):
    return {job.robot + ' ' + job.task: job.finish for job in cpu.run_until(until)}


def test_a_job_alone_finishes_after_its_cost():
    cpu = RoundRobinCPU(start_ms=100)
    cpu.submit(Job('tiago1', 'filter', cost=3, release=100))
    assert finishes(cpu, 200) == {'tiago1 filter': 103}


def test_two_jobs_released_together_take_turns_one_tick_at_a_time():
    # Ticks 0-4 run: a b a b b. So a finishes at 3 and b at 5, not 2 and 5.
    cpu = RoundRobinCPU(start_ms=0)
    cpu.submit(Job('tiago1', 'map', cost=2, release=0))
    cpu.submit(Job('tiago2', 'map', cost=3, release=0))
    assert finishes(cpu, 10) == {'tiago1 map': 3, 'tiago2 map': 5}


def test_a_later_job_joins_the_back_of_the_line():
    # Tick 0 runs a. At 1, b arrives behind a, so ticks 1-3 run a b a.
    cpu = RoundRobinCPU(start_ms=0)
    cpu.submit(Job('tiago1', 'map', cost=3, release=0))
    assert cpu.run_until(1) == []
    cpu.submit(Job('tiago2', 'control', cost=1, release=1))
    assert finishes(cpu, 10) == {'tiago2 control': 3, 'tiago1 map': 4}


def test_competition_delays_a_job_that_would_otherwise_finish_sooner():
    alone = RoundRobinCPU(start_ms=0)
    alone.submit(Job('tiago1', 'filter', cost=4, release=0))
    shared = RoundRobinCPU(start_ms=0)
    shared.submit(Job('tiago1', 'filter', cost=4, release=0))
    shared.submit(Job('tiago2', 'filter', cost=4, release=0))
    assert finishes(alone, 20)['tiago1 filter'] == 4
    assert finishes(shared, 20)['tiago1 filter'] == 7


def test_idle_ticks_are_not_busy():
    cpu = RoundRobinCPU(start_ms=0)
    cpu.submit(Job('tiago1', 'control', cost=2, release=0))
    cpu.run_until(10)
    assert (cpu.now, cpu.busy_ticks) == (10, 2)


def test_a_job_must_be_submitted_at_the_cpus_current_time():
    cpu = RoundRobinCPU(start_ms=0)
    with pytest.raises(ValueError):
        cpu.submit(Job('tiago1', 'filter', cost=1, release=5))


def test_a_job_needs_some_cpu_time():
    with pytest.raises(ValueError):
        Job('tiago1', 'filter', cost=0, release=0)
