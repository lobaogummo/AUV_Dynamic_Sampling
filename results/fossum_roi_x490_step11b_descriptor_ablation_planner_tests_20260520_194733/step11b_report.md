# Step11B Descriptor Ablation Planner Tests

- Output: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_194733`
- Cases: October_control
- Runtime: 1 AUV(s), 12h
- Runs: 8/11 successful
- Best single-AUV descriptor in this run: `representative_zone`

## Descriptor Ranking
- representative_zone: mean trajectory diff=0.948, mean delta descriptor=87.811, mean area=158.0
- gradient: mean trajectory diff=0.906, mean delta descriptor=-29.574, mean area=153.5
- boundary: mean trajectory diff=0.864, mean delta descriptor=37.930, mean area=157.5
- heterogeneity: mean trajectory diff=0.853, mean delta descriptor=11.492, mean area=150.5
- interest: mean trajectory diff=0.649, mean delta descriptor=-20.525, mean area=157.0

## Interpretation
- Each descriptor was tested separately; no descriptor mixing beyond STD + one descriptor.
- Boundary redundancy with STD can be assessed by comparing boundary rank and overlap/difference metrics.
- Multi-AUV recommendation is not inferred from this single-AUV ablation unless --auv-number 2 is used.

## Verdict
STEP11B_COMPLETED_WITH_WARNINGS