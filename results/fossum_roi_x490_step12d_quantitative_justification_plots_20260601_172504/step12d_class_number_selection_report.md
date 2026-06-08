# Step12D class-number selection report

ICV supports the 6-class branch relative to the 5-class branch in the available Step04 evidence, but ICV must not be used alone because it naturally decreases when more classes are allowed.

The decision combines ICV, minimum class size, fragmentation risk, stability/qualitative notes where available, separation where available, interpretability, and runtime as a secondary criterion.

## Decision table
| n_classes | SD_fraction | ICV_mean | min_class_size | class_balance_score | number_of_small_classes | runtime_seconds | ranking_score | behavior_label | selected_flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4.000 | 0.350 | 2131.731 | 41.000 | 0.342 | 0.000 |  | 2.250 | plausivel | 0.000 |
| 4.000 | 0.400 | 2131.731 | 41.000 | 0.342 | 0.000 |  | 2.250 | plausivel | 0.000 |
| 5.000 | 0.300 | 1755.583 | 30.000 | 0.250 | 0.000 |  | 2.100 | plausivel | 0.000 |
| 6.000 | 0.250 | 1328.040 | 30.000 | 0.280 | 0.000 | 1525.718 | 1.950 | plausivel | 1.000 |
| 10.000 | 0.200 | 754.780 | 11.000 | 0.157 | 2.000 |  | 2.600 | fragmenta demais | 0.000 |


## Selected branch
| n_classes | SD_fraction | ICV_mean | min_class_size | class_balance_score | runtime_seconds | justification_note |
| --- | --- | --- | --- | --- | --- | --- |
| 6.000 | 0.250 | 1328.040 | 30.000 | 0.280 | 1525.718 | Selected canonical branch: lower ICV than 5 classes while avoiding the fragmentation seen at 10 classes. |


Runtime is secondary for class-number choice because the largest costs are feature extraction, dictionary learning, sparse coding, and clustering; the final cut between nearby class counts is not the dominant computational burden.
