# Step11B Descriptor Ablation Planner Tests

- Output: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step11b_descriptor_ablation_planner_tests_20260520_160652`
- Cases: C01_representative
- Runtime: 1 AUV(s), 12h
- Runs: 11/11 successful
- Best single-AUV descriptor in this run: `heterogeneity`

## Descriptor Ranking
- heterogeneity: mean trajectory diff=0.946, mean delta descriptor=-70.541, mean area=154.5
- boundary: mean trajectory diff=0.942, mean delta descriptor=16.802, mean area=155.0
- representative_zone: mean trajectory diff=0.896, mean delta descriptor=11.771, mean area=152.5
- gradient: mean trajectory diff=0.894, mean delta descriptor=-113.353, mean area=147.5
- interest: mean trajectory diff=0.893, mean delta descriptor=-54.851, mean area=158.5

## Interpretation
- Each descriptor was tested separately; no descriptor mixing beyond STD + one descriptor.
- Boundary redundancy with STD can be assessed by comparing boundary rank and overlap/difference metrics.
- Multi-AUV recommendation is not inferred from this single-AUV ablation unless --auv-number 2 is used.

## Verdict
STEP11B_DESCRIPTOR_ABLATION_COMPLETED