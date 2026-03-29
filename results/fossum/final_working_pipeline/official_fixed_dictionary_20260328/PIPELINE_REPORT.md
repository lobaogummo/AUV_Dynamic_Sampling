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
- seeds requested: [11, 23, 37, 53, 71]
- fractions passed to global stage: [0.3]
- ranking_target_classes: 5
- local refinement enabled: True
- local k values: [2]
- run root: `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328`
- manifest: `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/pipeline_manifest.json`
- dictionary mode: fixed
- dictionary path: `C:\Users\pedro\Documents\Filipa_dados\results\fossum\canonical_dictionary\canonical_dictionary.npz`

## Stage Status By Seed
| seed | global status | local status | global dir | local dir |
| --- | --- | --- | --- | --- |
| 11 | success | success | `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/seed11/global` | `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/seed11/local_class02` |
| 23 | success | success | `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/seed23/global` | `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/seed23/local_class02` |
| 37 | success | success | `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/seed37/global` | `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/seed37/local_class02` |
| 53 | success | success | `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/seed53/global` | `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/seed53/local_class02` |
| 71 | success | success | `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/seed71/global` | `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/seed71/local_class02` |

## Notes
- `global/` contains promoted SD30 artifacts plus `runs.csv`, `ranking.csv`, and `REPORT.md`.
- `local_class02/` contains class_02 refinement outputs from script 06.
- If any stage failed, check `pipeline_manifest.json` for error details and missing-artifact checks.