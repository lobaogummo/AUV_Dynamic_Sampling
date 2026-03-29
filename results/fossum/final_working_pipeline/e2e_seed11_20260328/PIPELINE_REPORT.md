# Faithful Pipeline End-to-End Report

## Frozen Working Configuration
- patch size: 72x40
- dictionary size: 4
- StandardScaler before Ward: True
- official global SD fraction: 0.30
- official global class structure target: 5
- local refinement target class: class_02
- local refinement default split: 2 subclasses

## Runtime Parameters
- seeds requested: [11]
- fractions passed to global stage: [0.3]
- ranking_target_classes: 5
- local refinement enabled: True
- local k values: [2]
- run root: `results/fossum/final_working_pipeline/e2e_seed11_20260328`
- manifest: `results/fossum/final_working_pipeline/e2e_seed11_20260328/pipeline_manifest.json`

## Stage Status By Seed
| seed | global status | local status | global dir | local dir |
| --- | --- | --- | --- | --- |
| 11 | success | success | `results/fossum/final_working_pipeline/e2e_seed11_20260328/seed11/global` | `results/fossum/final_working_pipeline/e2e_seed11_20260328/seed11/local_class02` |

## Notes
- `global/` contains promoted SD30 artifacts plus `runs.csv`, `ranking.csv`, and `REPORT.md`.
- `local_class02/` contains class_02 refinement outputs from script 06.
- If any stage failed, check `pipeline_manifest.json` for error details and missing-artifact checks.