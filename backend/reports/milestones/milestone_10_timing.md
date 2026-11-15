# Milestone 10 timing

No July scientific analysis was rerun. Source rows scanned by the experiment runner: 0. Records processed by an experiment execution: 0. `same_fire` remains `not_assessed`. Throughput for a new scientific scan was not measured, so it is not reported as a rate.

The request timestamp is 2026-11-15T06:54:00-06:00, which is the minute shown on the request and not a stopwatch. The first measured clock is 2026-11-15T06:57:09.8607747-06:00. The traced validation ended at 2026-11-15T07:12:50.7690061-06:00. The span between those two clocks is 940.908232 s, from `datetime.total_seconds()`. That span includes authoring that was not timed as its own process. It is not a sum of the task times below.

## Validation

The framework tests reported `9 passed in 0.41s`. The tool-reported elapsed time for that command was 9,205 ms, which includes shell startup.

Two untraced full suites:

| Start | End | Wall clock (s) | Pytest report | Exit | CPU (s) | Peak working set |
| --- | --- | ---: | --- | --- | --- | --- |
| 2026-11-15T07:05:03.3493844-06:00 | 2026-11-15T07:05:49.6267199-06:00 | 46.2773355 | 121 passed in 45.30s | 0 | null | null |
| 2026-11-15T07:06:09.8884084-06:00 | 2026-11-15T07:06:55.3558192-06:00 | 45.467410799999996 | 121 passed in 44.83s | null | null | null |

The first process handle returned 0.015625 s of processor time after exit. That does not account for a 46 s wall clock, so it is not the test CPU. The second handle's polled peak was 4,448,256 bytes. A direct query of the Python process in the traced run showed a much larger working set, so the small peak is the launcher handle, not the interpreter.

## Traced run

Tracing was turned on because the post-exit counters were empty. The suite still passed, and it was slower.

| Quantity | Value |
| --- | --- |
| Python PID | 40460 |
| Wall clock of the whole script | 331.50384479999997 s |
| Pytest report | 121 passed in 329.34s (0:05:29) |
| `perf_counter` around pytest | 330.0008746999956 s |
| Traced Python peak | 464,695,929 bytes |
| Traced Python current at stop | 71,273,207 bytes |
| Schema validation and four prepares | 0.21214240000699647 s |
| Traced Python peak of that step | 1,778,256 bytes |
| CPU at an in-run sample | 305.109375 s |
| Working set at that sample | 352,612,352 bytes |
| Peak working set at that sample | 1,747,030,016 bytes |
| Paged memory at that sample | 1,652,215,808 bytes |
| CPU after exit | null |

The sample was taken while PID 40460 was still running. Processor time was not readable after exit, so 305.109375 s is not a final total. The Start-Process handle itself peaked at 4,534,272 bytes across 1,583 samples. That handle was not the interpreter.

The four configurations validated, and four run directories were prepared under the temporary path `C:\Users\ADMINI~1\AppData\Local\Temp\m10-prepare-si6byhxi`. Those directories are outside the repository. Preparation read 0 source rows.

## Retry and waiting

No test run failed. Two extra full suites were executed to obtain counters: one untraced wall clock of 45.467410799999996 s and the traced wall clock of 331.50384479999997 s. The traced duration is the cost of allocation tracing. It is not a replacement for the 45.30 s untraced result.

Waiting time as a separate counter was not measured. The traced process was left running when it passed two minutes, because its output was still advancing. It was not cancelled. Its wall clock is the 331.50384479999997 s figure.

## Contract confirmation

Four monthly headers and four first data rows were read to confirm the stored instrument text. The first-row command's tool-reported elapsed time was 7,997 ms, including shell startup. That interval is not a read rate. Bytes read were not measured. The remaining 7,985,467 rows were not scanned.

## Bounds carried forward from earlier reports

These are copied from the completed JSON reports. They were not remeasured.

| Run | Load (s) | Following stage (s) | Traced Python peak (bytes) | Working set peak (bytes) | Derived load rate (rows/s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Within-sensor | 176.18339190000552 | 661.1942539000011 analysis | 1,900,924,045 | null | 45,324.74323421032 |
| Nearest neighbor | 168.90355260000797 | 1,347.4298895999964 analysis | 1,684,953,502 | 1,897,316,352 | 47,278.26547799696 |
| Candidate pairs | 181.8602064000006 | 111.33626359999471 match | 1,119,952,034 | null | 43,909.919372003824 |

Monthly EDA and the temporal-coverage scan still have no stored duration. Experiment B, C, and D execution times remain unmeasured until those experiments run.
