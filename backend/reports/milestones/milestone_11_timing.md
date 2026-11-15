# Milestone 11 timing

Started: 2026-11-15T13:34:43.276205+00:00
Completed: 2026-11-15T13:39:26.809380+00:00

Durations below are measured. Planning allowances are labeled as estimates and are not substituted for a missing measurement.

## Host

- Physical cores: 12
- Logical processors: 20
- Physical memory: 34164097024 bytes
- Available physical memory at launch: 15197818880 bytes
- Free disk: 286620127232 bytes

## Concurrency

4 experiment processes may run at once. Available physical memory was 15197818880 bytes. Each process is planned below 2147483648 bytes. 6442450944 bytes stay in reserve. full_month_rebuild is not in this batch.

Processes launched together were capped at 4.

## Commands

| Command | Exit | Wall (s) | CPU (s) | Peak working set (bytes) | Rows read | Records processed | Records/s | Queue wait (s) | Output bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| checksum_before | 0 | 0.495 | n/a | n/a | n/a | n/a | n/a | 0.000 | 1012 |
| experiment_C_attempt_1 | 0 | 19.383 | 19.078 | n/a | 7985467 | 7985467 | 411976.7 | 0.012 | 565772 |
| experiment_A_attempt_1 | 1 | 24.020 | n/a | n/a | 0 | n/a | n/a | 0.004 | 0 |
| experiment_D_attempt_1 | 0 | 23.319 | 22.875 | n/a | 7985467 | 7985467 | 342442.5 | 0.017 | 386593 |
| experiment_B_attempt_1 | 0 | 28.910 | 28.234 | n/a | 7985467 | 7985467 | 276215.3 | 0.007 | 336273 |
| checksum_after | 0 | 0.494 | n/a | n/a | n/a | n/a | n/a | 0.000 | 0 |
| experiment_A_attempt_2 | 0 | 21.828 | 21.109 | n/a | 7985467 | 284355 | 13027.2 | n/a | n/a |
| experiment_A | 0 | 22.166 | 21.797 | 256012288 | 7985467 | 284355 | 12828.2 | 0.000 | 444520 |
| experiment_B | 0 | 29.243 | 28.656 | 505827328 | 7985467 | 7985467 | 273074.3 | 0.000 | 336277 |
| experiment_C | 0 | 19.108 | 18.719 | 116903936 | 7985467 | 7985467 | 417911.7 | 0.000 | 565773 |
| experiment_D | 0 | 23.274 | 22.828 | 494911488 | 7985467 | 7985467 | 343111.7 | 0.000 | 386605 |
| checksum_after_repeat | 0 | 0.489 | n/a | n/a | n/a | n/a | n/a | 0.000 | 0 |

Total wall clock: 283.533 seconds.
Active execution, summed across commands: 212.730 seconds.
Science-phase wall clock: 29.243 seconds.
Waiting time inside the science phase, summed across experiments: 0.000 seconds.
Retries: 1. Cancellations: 0.

Parallel efficiency is the sum of the four experiment wall clocks divided by four times the science-phase wall clock. That ratio is 0.802. A value near 1 means the four processes overlapped. It is not a claim about numerical speedup of one algorithm.

## Checksums

The July CSV SHA-256 values were measured before the experiments in 0.496 seconds and again after them in 0.489 seconds. Unchanged: True.

## Planning allowances

These were written down before the processes finished. They are not measurements.

- A: Representative dates only. The recorded full-month within-sensor analysis took 661.1942539000011 s after a 176.18339190000552 s load and is not repeated. Planning allowance: 900 s.
- B: One pass over the five satellite columns. Historical full-pass duration is unmeasured. Planning allowance: 600 s.
- C: One pass over acquisition dates and times. Planning allowance: 600 s.
- D: One pass for scan, track, and the degree grids. Planning allowance: 600 s.

## Attempts

The first processes recorded a null peak because psapi.GetProcessMemoryInfo was invoked without 64-bit argument types. The repeated execution used K32GetProcessMemoryInfo with declared argument types. science_phase_wall_clock_seconds is the span of that repeated execution.

- experiment_C_attempt_1: Completed. Peak working set was null because GetProcessMemoryInfo was called without 64-bit argument types.
- experiment_A_attempt_1: Failed while writing the figure because the factorial summary had no noise_share key. The error handler then raised NameError, so this manifest stayed at the prepared row count of 0. That zero is the unupdated manifest, not a measurement that no rows were read.
- experiment_D_attempt_1: Completed. Peak working set was null because GetProcessMemoryInfo was called without 64-bit argument types.
- experiment_B_attempt_1: Completed. Peak working set was null because GetProcessMemoryInfo was called without 64-bit argument types.
- experiment_A_attempt_2: First successful clustering run, read from its execution.json before that run directory was replaced. Peak working set was null for the same API reason. Started timestamp was not retained.
- experiment_A: Repeated after the working-set call was corrected. This is the record with a measured peak.
- experiment_B: Repeated after the working-set call was corrected. This is the record with a measured peak.
- experiment_C: Repeated after the working-set call was corrected. This is the record with a measured peak.
- experiment_D: Repeated after the working-set call was corrected. This is the record with a measured peak.
- checksum_after_repeat: SHA-256 of the four CSVs after the repeated execution.

