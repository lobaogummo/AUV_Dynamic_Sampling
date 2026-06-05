# Step12A Boundary Distance Results Report

Input folder: `results/fossum_roi_x490_step12a_single_auv_weight_duration_sensitivity_20260605_152501`

## Scope

This report interprets the completed Step12A C01 12h alpha sweep for old `boundary_score`, pure boundary-distance bands `r1/r3/r5`, and `interest_map`.

Language is intentionally limited to reward-map sensitivity, potential informativeness, accumulated uncertainty proxy, boundary/regime coverage, and operational efficiency. No actual data-assimilation uncertainty reduction is claimed.

## 1. Main CSV And Columns

`step12a_single_auv_metrics.csv` is the main metrics table. It contains one logical row per descriptor-alpha combination, including repeated alpha=0 baseline rows for each descriptor family.

Important column groups:

- run identity: `case_id`, `date`, `descriptor`, `alpha`, `run_name`, `physical_run_id`;
- solver diagnostics: `solver_status`, `solver_runtime`, `solver_gap`, `solver_returncode`, `run_dir`;
- route properties: `trajectory_length`, `mission_duration`, `number_of_valid_cells_sampled`;
- rewards: `collected_STD`, `collected_descriptor`, `collected_information_score`;
- coverage/proxy metrics: `percentage_path_in_top10_STD`, `percentage_path_in_top10_descriptor`, `regions_visited`, `crossing_count`, `fraction_path_region_A`, `fraction_path_region_B`;
- baseline comparison: `trajectory_overlap_ratio_with_baseline`, `path_difference_from_baseline`, `STD_retention`, `recommendation_score`.

Derived columns in `step12a_boundary_distance_results_summary.csv` add `reward_per_km`, `std_per_km`, `descriptor_per_km`, deltas relative to baseline, and multi-criteria ranking columns.

## 2. Planner Success Check

- Solver diagnostics rows: `21`
- Successful runs: `21/21`
- Failed runs: `0`
- Checks verdict: `STEP12_SENSITIVITY_COMPLETED_FINAL_WEIGHTS_RECOMMENDED`

All physical planner runs succeeded. The failure summary is empty.

## 3. Baseline

The STD-only baseline has collected STD/information reward `94.367`, route length `36.655 km`, and reward efficiency `2.574 reward/km`.

It is the reference for `STD_retention`, route difference, and reward-efficiency deltas.

## 4. Descriptor-Alpha Results

| descriptor | alpha | collected_information_score | collected_STD | collected_descriptor | trajectory_length | reward_per_km | solver_runtime | percentage_path_in_top10_descriptor | STD_retention | path_difference_from_baseline | rank_overall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boundary_distance_score_r1_cells | 0 | 94.37 | 94.37 | 24.49 | 36.66 | 2.574 | 398.1 | 0.391 | 1 | 0 |  |
| boundary_distance_score_r1_cells | 0.25 | 99.54 | 96.88 | 49.44 | 38.22 | 2.604 | 358 | 0.625 | 1.027 | 0.9215 | 13 |
| boundary_distance_score_r1_cells | 0.5 | 87.24 | 87.73 | 69.78 | 38.8 | 2.248 | 309.6 | 0.6267 | 0.9297 | 0.9338 | 15 |
| boundary_distance_score_r1_cells | 0.75 | 76.16 | 91.64 | 66.06 | 38.88 | 1.959 | 159.6 | 0.6667 | 0.9711 | 0.9278 | 14 |
| boundary_distance_score_r1_cells | 1 | 80.02 | 52.74 | 80.02 | 38.93 | 2.055 | 91.49 | 1 | 0.5589 | 0.9711 | 12 |
| boundary_distance_score_r3_cells | 0 | 94.37 | 94.37 | 55.56 | 36.66 | 2.574 | 398.1 | 0.391 | 1 | 0 |  |
| boundary_distance_score_r3_cells | 0.25 | 106.1 | 87.32 | 115.8 | 38.21 | 2.777 | 351.7 | 0.9865 | 0.9254 | 0.922 | 7 |
| boundary_distance_score_r3_cells | 0.5 | 123.3 | 96.74 | 125.9 | 38.52 | 3.2 | 316.8 | 0.9512 | 1.025 | 0.9298 | 5 |
| boundary_distance_score_r3_cells | 0.75 | 129.7 | 88.14 | 135.2 | 39.98 | 3.244 | 179.4 | 1 | 0.934 | 0.9315 | 4 |
| boundary_distance_score_r3_cells | 1 | 142.1 | 93.86 | 142.1 | 40.11 | 3.543 | 89.57 | 1 | 0.9947 | 0.9259 | 2 |
| boundary_distance_score_r5_cells | 0 | 94.37 | 94.37 | 76.25 | 36.66 | 2.574 | 398.1 | 0.391 | 1 | 0 |  |
| boundary_distance_score_r5_cells | 0.25 | 105.6 | 87.5 | 120.6 | 38.51 | 2.743 | 370.9 | 0.7986 | 0.9273 | 0.9247 | 9 |
| boundary_distance_score_r5_cells | 0.5 | 125.2 | 95.86 | 135.8 | 38.25 | 3.274 | 311.4 | 0.7607 | 1.016 | 0.9259 | 6 |
| boundary_distance_score_r5_cells | 0.75 | 135.8 | 92.4 | 141.5 | 38.93 | 3.489 | 189.2 | 0.9618 | 0.9792 | 0.917 | 3 |
| boundary_distance_score_r5_cells | 1 | 149.7 | 93.69 | 149.7 | 39.25 | 3.815 | 92.59 | 1 | 0.9928 | 0.9437 | 1 |
| boundary_score | 0 | 94.37 | 94.37 | 116.2 | 36.66 | 2.574 | 398.1 | 0.03846 | 1 | 0 |  |
| boundary_score | 0.25 | 102.5 | 94.88 | 130.5 | 37.99 | 2.697 | 337.2 | 0.1987 | 1.005 | 0.8975 | 16 |
| boundary_score | 0.5 | 117.3 | 91.25 | 138.6 | 38.19 | 3.07 | 239.2 | 0.2642 | 0.967 | 0.9773 | 10 |
| boundary_score | 0.75 | 119.6 | 81.38 | 126.1 | 37.6 | 3.182 | 203.8 | 0.2483 | 0.8624 | 0.9173 | 11 |
| boundary_score | 1 | 134.9 | 79.61 | 134.9 | 37.62 | 3.586 | 113.7 | 0.1603 | 0.8436 | 0.9459 | 8 |
| interest_map | 0 | 94.37 | 94.37 | 54.29 | 36.66 | 2.574 | 398.1 | 0 | 1 | 0 |  |
| interest_map | 0.25 | 94.14 | 93.93 | 54.57 | 37.7 | 2.497 | 366.8 | 0 | 0.9954 | 0.8519 | 20 |
| interest_map | 0.5 | 98.72 | 87.34 | 57.78 | 37.17 | 2.656 | 289.5 | 0.12 | 0.9255 | 0.911 | 17 |
| interest_map | 0.75 | 81.25 | 83.14 | 60.24 | 38.72 | 2.098 | 279.1 | 0.2282 | 0.8811 | 0.9555 | 19 |
| interest_map | 1 | 62.33 | 83.85 | 62.33 | 37.35 | 1.669 | 98.4 | 0.2792 | 0.8885 | 0.9667 | 18 |


## 5. Best Configuration Per Descriptor

| descriptor | alpha | collected_information_score | collected_STD | collected_descriptor | trajectory_length | reward_per_km | percentage_path_in_top10_descriptor | STD_retention | solver_runtime | thesis_ranking_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| boundary_distance_score_r5_cells | 1 | 149.7 | 93.69 | 149.7 | 39.25 | 3.815 | 1 | 0.9928 | 92.59 | 0.9853 |
| boundary_distance_score_r3_cells | 1 | 142.1 | 93.86 | 142.1 | 40.11 | 3.543 | 1 | 0.9947 | 89.57 | 0.9488 |
| boundary_score | 1 | 134.9 | 79.61 | 134.9 | 37.62 | 3.586 | 0.1603 | 0.8436 | 113.7 | 0.7004 |
| boundary_distance_score_r1_cells | 1 | 80.02 | 52.74 | 80.02 | 38.93 | 2.055 | 1 | 0.5589 | 91.49 | 0.6364 |
| interest_map | 0.5 | 98.72 | 87.34 | 57.78 | 37.17 | 2.656 | 0.12 | 0.9255 | 289.5 | 0.5173 |


## 6. Overall Ranking

| rank_overall | descriptor | alpha | collected_information_score | reward_per_km | STD_retention | percentage_path_in_top10_descriptor | solver_runtime | thesis_ranking_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | boundary_distance_score_r5_cells | 1 | 149.7 | 3.815 | 0.9928 | 1 | 92.59 | 0.9853 |
| 2 | boundary_distance_score_r3_cells | 1 | 142.1 | 3.543 | 0.9947 | 1 | 89.57 | 0.9488 |
| 3 | boundary_distance_score_r5_cells | 0.75 | 135.8 | 3.489 | 0.9792 | 0.9618 | 189.2 | 0.8926 |
| 4 | boundary_distance_score_r3_cells | 0.75 | 129.7 | 3.244 | 0.934 | 1 | 179.4 | 0.8607 |
| 5 | boundary_distance_score_r3_cells | 0.5 | 123.3 | 3.2 | 1.025 | 0.9512 | 316.8 | 0.8152 |
| 6 | boundary_distance_score_r5_cells | 0.5 | 125.2 | 3.274 | 1.016 | 0.7607 | 311.4 | 0.7776 |
| 7 | boundary_distance_score_r3_cells | 0.25 | 106.1 | 2.777 | 0.9254 | 0.9865 | 351.7 | 0.7286 |
| 8 | boundary_score | 1 | 134.9 | 3.586 | 0.8436 | 0.1603 | 113.7 | 0.7004 |
| 9 | boundary_distance_score_r5_cells | 0.25 | 105.6 | 2.743 | 0.9273 | 0.7986 | 370.9 | 0.6706 |
| 10 | boundary_score | 0.5 | 117.3 | 3.07 | 0.967 | 0.2642 | 239.2 | 0.639 |


The ranking score combines reward efficiency, STD preservation, descriptor/boundary coverage, solver runtime, and operational feasibility. It is an interpretive thesis aid, not a planner objective.

## 7. Descriptor Comparison

### Old boundary_score

Best old `boundary_score`: alpha `1.00`. It increases descriptor/front reward relative to the STD-only route, but the best row keeps STD_retention `0.844` and reward efficiency `3.586`. It remains a blended gradient-plus-proximity descriptor, not pure distance-to-boundary.

### Pure boundary distance r1

Best `r1`: alpha `1.00`, STD_retention `0.559`, descriptor top-10 coverage `1.000`, reward efficiency `2.055`. r1 behaves as the narrowest boundary band: it reaches high top-10% descriptor coverage at higher alpha, but its collected descriptor score remains much lower than r3/r5 because the reward band is spatially tight.

### Pure boundary distance r3

Best `r3`: alpha `1.00`, STD_retention `0.995`, descriptor top-10 coverage `1.000`, reward efficiency `3.543`. r3 is a useful compromise: it preserves STD almost as well as the baseline while increasing descriptor coverage and producing high reward efficiency without being as spatially broad as r5.

### Pure boundary distance r5

Best `r5`: alpha `1.00`, STD_retention `0.993`, descriptor top-10 coverage `1.000`, reward efficiency `3.815`. r5 behaves as the broadest tested band: it gives the highest accumulated descriptor/proximity reward and a strong efficiency score, but it is less spatially selective than r1/r3, so it should be interpreted as broader boundary-neighborhood preference rather than exact boundary following.

### interest_map

Best `interest_map`: alpha `0.50`, STD_retention `0.926`, descriptor top-10 coverage `0.120`, reward efficiency `2.656`. It is a composite sensitivity descriptor, useful as a broad diagnostic but less explicit than the pure boundary-distance bands.

## 8. Narrow/Broad Radius Interpretation

- `r1` is likely too narrow as a final descriptor by itself: it is very selective around the boundary and can under-reward nearby but operationally useful boundary-neighborhood cells.
- `r5` is likely broad: it gives strong accumulated proximity reward and efficient routes, but it relaxes the boundary preference into a wider band.
- `r3` is the most thesis-friendly compromise among the tested pure-distance descriptors: it is explicit, interpretable, and preserves the STD proxy well while producing strong boundary-band coverage.

## 9. Recommendation

Recommended primary configuration from the multi-criteria ranking: `boundary_distance_score_r5_cells` with alpha `1.00`.

This row has collected information-map reward `149.732`, STD_retention `0.993`, reward efficiency `3.815`, descriptor top-10 coverage `1.000`, and solver runtime `92.594 s`.

For thesis framing, I would describe this as the best operational reward-map sensitivity result in this C01/12h test, while also reporting `r3` as the most interpretable radius compromise if the goal is a clean distance-to-boundary descriptor rather than maximal broad-band reward.

## 10. Generated Plots

- `figures/step12a_boundary_distance_alpha_vs_reward.png`
- `figures/step12a_boundary_distance_alpha_vs_route_length.png`
- `figures/step12a_boundary_distance_alpha_vs_reward_efficiency.png`
- `figures/step12a_boundary_distance_descriptor_ranking.png`
- `figures/step12a_boundary_distance_STD_retention_vs_descriptor_coverage.png`