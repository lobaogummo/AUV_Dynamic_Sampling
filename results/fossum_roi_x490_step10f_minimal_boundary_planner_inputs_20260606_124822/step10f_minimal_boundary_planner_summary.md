# Step10F Minimal Boundary Planner Inputs

- Output: `C:\Users\pedro\Documents\Filipa_dados\results\fossum_roi_x490_step10f_minimal_boundary_planner_inputs_20260606_124822`
- Baseline: `information_map = STD_norm`
- Enriched alpha 0.25: `0.75 * STD_norm + 0.25 * boundary_score_norm`
- Enriched alpha 0.50: `0.50 * STD_norm + 0.50 * boundary_score_norm`
- Descriptor used: boundary only

## Cases
- C01_representative: 2024-08-24, predicted C01, confidence=0.257, STD_mean=0.16547
- C06_representative: 2023-12-22, predicted C06, confidence=0.679, STD_mean=0.01697
- October_control: 2024-10-30, predicted C02, confidence=0.340, STD_mean=0.06713

## Recommendation
Use C06_representative (2023-12-22, C06) first: it has the strongest classification confidence among the three selected cases. Then compare against the high-STD C01 case to test whether boundary enrichment changes planner behavior.

MINIMAL_BOUNDARY_PLANNER_INPUTS_READY