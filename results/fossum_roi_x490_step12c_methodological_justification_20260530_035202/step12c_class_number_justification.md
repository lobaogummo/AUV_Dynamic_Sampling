# Step12C class-number justification

The canonical pipeline used SD=0.25 and 6 classes because this solution was the best automatic balanced candidate in Step04 and was then fixed in Step05 for the canonical descriptors.

Evidence:
- Step04 strict balanced-score best SD: `0.25`.
- Step04 strict balanced-score best number of classes: `6`.
- The 6-class solution had no singleton classes and a minimum class size of 30 days.
- SD=0.30 was retained as sensitivity/context, but the final canonical Step05 output is the SD=0.25 / 6-class branch.

## Step04 top candidates
| sd_fraction_of_max | number_of_classes | class_sizes | min_class_size | singleton_count | balanced_score |
| --- | --- | --- | --- | --- | --- |
| 0.250 | 6.000 | [41, 70, 50, 107, 30, 72] | 30.000 | 0.000 | 1.950 |
| 0.300 | 5.000 | [41, 120, 107, 30, 72] | 30.000 | 0.000 | 2.100 |
| 0.350 | 4.000 | [41, 120, 107, 102] | 41.000 | 0.000 | 2.250 |


## Step05 canonical class sizes
| class_id | n_days | percent_days | icv_sst_space |
| --- | --- | --- | --- |
| 1.000 | 41.000 | 11.081 | 1680.750 |
| 2.000 | 70.000 | 18.919 | 1474.508 |
| 3.000 | 50.000 | 13.514 | 1351.872 |
| 4.000 | 107.000 | 28.919 | 2005.192 |
| 5.000 | 30.000 | 8.108 | 326.411 |
| 6.000 | 72.000 | 19.459 | 1129.507 |
