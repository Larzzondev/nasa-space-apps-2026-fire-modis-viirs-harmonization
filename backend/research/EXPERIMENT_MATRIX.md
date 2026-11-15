# Experiment matrix

The four experiments share one July 2024 input and write four different outputs. None of them is a harmonization.

## Specification

| | A. Clustering | B. Measurements | C. Overpasses | D. Resolution |
| --- | --- | --- | --- | --- |
| Configuration | `research/examples/experiment_a.json` | `research/examples/experiment_b.json` | `research/examples/experiment_c.json` | `research/examples/experiment_d.json` |
| Output | `experiments/A/runs/<run_id>/` | `experiments/B/runs/<run_id>/` | `experiments/C/runs/<run_id>/` | `experiments/D/runs/<run_id>/` |
| Completed report it cites | Within-sensor analysis | Monthly EDA and nearest neighbors | Temporal coverage, coverage investigation, candidate pairs | Monthly EDA and within-sensor scan/track |
| First-batch work | Representative dates only, plus the published full-month settings | Conditional quantiles in one pass | Acquisition-minute distributions in one pass | `scan * track` and existing degree grids |
| Satellites | Terra, Aqua, S-NPP, NOAA-20, and NOAA-21 kept separate | Same, with published MODIS pair labels kept when cited | Same | Same |
| Same-fire | `not_assessed` | `not_assessed` | `not_assessed` | `not_assessed` |
| Coefficient | Not estimated | Explicitly forbidden | Not estimated | Not estimated |
| H3 | Not used | Not used | Not used | Candidate only, not selected |
| Missing S-NPP dates | Left out of denominators | Left out of denominators | Left out of comparisons | Left out of denominators |
| Can run with the others | Yes | Yes | Yes | Yes |

The input contract on every row is `data/raw/monthly_2024_07`, access `read_only`, 7,985,467 expected rows, and the four checksums in the schema.

## Acceptance criteria

A run of an experiment is acceptable only when its manifest validates against `#/$defs/experimentRun` and the experiment-specific locks in [`EXPERIMENT_DESIGN.md`](EXPERIMENT_DESIGN.md) still hold. In addition:

- A does not add partition cluster counts into a monthly fire total, and it does not call a component a fire.
- B does not fit a slope, intercept, or other coefficient, and it does not drop non-positive FRP from a distribution that claims to describe all rows.
- C does not fill 10–15 or 25–28 July, does not repair 16, 24, or 29 July, and does not treat a 50-minute NOAA-20/NOAA-21 gap as a spatial miss.
- D does not treat a search radius as a footprint, does not treat equal-degree cells as equal-area cells, and does not select an H3 resolution.

This milestone's own acceptance is the schema and prepare tests, not a scientific execution. Those commands are in the design document.

## Resource bounds from recorded runs

The numbers below are copied from the performance objects of completed reports. They are not new timings. Derived rates divide 7,985,467 rows by the recorded load time. They describe those past loads only.

| Recorded run | Load (s) | Analysis or match (s) | Load plus that stage (s) | Traced Python peak (bytes) | Working set peak (bytes) | Derived load rate (rows/s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Within-sensor, milestone 9 | 176.18339190000552 | 661.1942539000011 | 837.3776458000066 | 1,900,924,045 | null | 45,324.74323421032 |
| Nearest neighbor | 168.90355260000797 | 1,347.4298895999964 | 1,516.3334422000044 | 1,684,953,502 | 1,897,316,352 | 47,278.26547799696 |
| Candidate pairs | 181.8602064000006 | 111.33626359999471 | 293.1964699999953 | 1,119,952,034 | null | 43,909.919372003824 |

Monthly EDA and the temporal-coverage scan do not have a performance object in their JSON reports. Their wall time, CPU, and memory are unmeasured. Experiment B, C, and D full-pass durations are therefore unmeasured until those experiments run. This matrix does not substitute an estimate for those missing measurements.

If Experiment A is later switched to `full_month_rebuild`, the planning bound is the recorded within-sensor run: 661.1942539000011 s of analysis after a load of 176.18339190000552 s, with a traced peak of 1,900,924,045 bytes. That is the same class of work. It is not a prediction that a new process will take the same number of seconds.

The nearest-neighbor working set of 1,897,316,352 bytes is the recorded peak for that cross-sensor index. Two full indexes of that class on one machine are a memory question the first batch avoids by not rebuilding them.

## Recommended first batch

Run A, B, C, and D together.

- A uses `published_baseline_plus_representative_date`. The representative dates contain 6,162 Terra rows, 15,517 Aqua rows, 82,443 S-NPP rows, 92,596 NOAA-20 rows, and 87,637 NOAA-21 rows. Those counts are the published date totals, not a new measurement of runtime.
- B, C, and D are specified as single passes or as citations. They do not rebuild the 5 km pair index.
- Leave `full_month_rebuild` off in this batch. That scope can follow after the representative-date stability result exists, and it should not share the machine with a second full-table spatial index.

No experiment in this batch waits for another experiment's new files. The joint review waits until all four manifests exist, and even then it does not authorize a coefficient.

## Isolation

| Rule | Enforcement |
| --- | --- |
| Read-only inputs | Schema `access` is `read_only`. Preparation opens no CSV. |
| Separate directories | Schema constants `experiments/A/runs` through `experiments/D/runs`. |
| No overwrite | `overwrite` is false, and `prepare` fails if the run directory exists. |
| Protected reports | The schema lists the ingestion, coverage, EDA, candidate-pair, nearest-neighbor, and within-sensor reports. The run path cannot be `reports/`. |
| Worktrees | Each worktree prepares one experiment id. Gitignored CSVs stay in the original data directory. |
| Versions | The manifest records Python and the four package versions, and the git commit when the command returns one. |
