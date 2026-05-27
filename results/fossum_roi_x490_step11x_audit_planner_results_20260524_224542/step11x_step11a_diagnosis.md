# Step11A diagnosis

- Boundary-only maps changed the sampled-cell set in 100% of enriched comparisons by the saved overlap metric.
- The change often carried an STD cost: 78% of enriched comparisons lost collected STD relative to baseline.
- Boundary collection improved in 67% of enriched comparisons, so the descriptor had signal but was not always aligned with preserving STD.

## Runtime coverage

- 2auv_12h: 9 metric rows
- unknown_runtime: 18 metric rows

## Key table

| runtime_label | case_id | formulation | alpha | trajectory_difference_from_baseline | delta_collected_STD_score | delta_collected_boundary_score | solver_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2auv_12h | C01_representative | enriched_boundary_alpha025 | 0.250 | 0.876 | -6.475 | 3.078 | SUCCESS |
| 2auv_12h | C01_representative | enriched_boundary_alpha050 | 0.500 | 0.891 | -16.344 | -8.541 | SUCCESS |
| 2auv_12h | C06_representative | enriched_boundary_alpha025 | 0.250 | 0.828 | -1.271 | 9.250 | SUCCESS |
| 2auv_12h | C06_representative | enriched_boundary_alpha050 | 0.500 | 0.906 | -6.444 | 36.553 | SUCCESS |
| 2auv_12h | October_control | enriched_boundary_alpha025 | 0.250 | 0.907 | -3.755 | 2.053 | SUCCESS |
| 2auv_12h | October_control | enriched_boundary_alpha050 | 0.500 | 0.985 | -60.468 | 122.187 | SUCCESS |
| unknown_runtime | C01_representative | enriched_boundary_alpha025 | 0.250 | 0.856 | 0.913 | 0.886 | SUCCESS |
| unknown_runtime | C01_representative | enriched_boundary_alpha025 | 0.250 | 0.927 | -4.152 | -5.150 | SUCCESS |
| unknown_runtime | C01_representative | enriched_boundary_alpha050 | 0.500 | 0.928 | -4.626 | -5.726 | SUCCESS |
| unknown_runtime | C01_representative | enriched_boundary_alpha050 | 0.500 | 0.867 | -8.304 | -6.341 | SUCCESS |
| unknown_runtime | C06_representative | enriched_boundary_alpha025 | 0.250 | 0.892 | -1.501 | -0.297 | SUCCESS |
| unknown_runtime | C06_representative | enriched_boundary_alpha025 | 0.250 | 0.907 | 0.629 | 21.343 | SUCCESS |
| unknown_runtime | C06_representative | enriched_boundary_alpha050 | 0.500 | 0.918 | 1.891 | 5.889 | SUCCESS |
| unknown_runtime | C06_representative | enriched_boundary_alpha050 | 0.500 | 0.961 | -3.017 | 20.887 | SUCCESS |
| unknown_runtime | October_control | enriched_boundary_alpha025 | 0.250 | 0.860 | 4.910 | 0.854 | SUCCESS |
| unknown_runtime | October_control | enriched_boundary_alpha025 | 0.250 | 0.880 | -12.741 | -1.806 | SUCCESS |
| unknown_runtime | October_control | enriched_boundary_alpha050 | 0.500 | 0.993 | -10.683 | 24.022 | SUCCESS |
| unknown_runtime | October_control | enriched_boundary_alpha050 | 0.500 | 0.997 | -47.119 | 77.174 | SUCCESS |

## STD-boundary redundancy

Mean Pearson correlation STD vs boundary_score across Step10F cases: 0.042.
Mean top-10% Jaccard overlap: 0.109.
This supports treating boundary_score as partly redundant only in a broad spatial-gradient sense; hotspot overlap is not uniformly high.

## Interpretation

- Step11A worked as a first integration test: the planner received different static prize maps and returned feasible routes.
- It did not prove that boundary_score alone solves regime-aware planning. The response is mixed: some boundary gains are small, and higher alpha can reduce STD sharply.
- The 2-AUV 12h run should be interpreted as shared-map fleet behavior, not true vehicle specialization.