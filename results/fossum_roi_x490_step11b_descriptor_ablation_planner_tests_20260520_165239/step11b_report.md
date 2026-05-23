# Step11B Descriptor Ablation Planner Tests

- Output: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_165239`
- Cases: C06_representative
- Runtime: 1 AUV(s), 12h
- Runs: 10/11 successful
- Best single-AUV descriptor in this run: `representative_zone`

## Descriptor Ranking
- representative_zone: mean trajectory diff=0.940, mean delta descriptor=-2.753, mean area=158.0
- boundary: mean trajectory diff=0.885, mean delta descriptor=-7.489, mean area=147.0
- interest: mean trajectory diff=0.823, mean delta descriptor=-69.412, mean area=153.0
- gradient: mean trajectory diff=0.802, mean delta descriptor=-116.244, mean area=150.5
- heterogeneity: mean trajectory diff=0.795, mean delta descriptor=-103.144, mean area=160.5

## Interpretation
- Each descriptor was tested separately; no descriptor mixing beyond STD + one descriptor.
- Boundary redundancy with STD can be assessed by comparing boundary rank and overlap/difference metrics.
- Multi-AUV recommendation is not inferred from this single-AUV ablation unless --auv-number 2 is used.

## Verdict
STEP11B_COMPLETED_WITH_WARNINGS