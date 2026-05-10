# Step01b baseline cluster diagnostics report

## Inputs
- Step01: `C:\Users\pedro\Documents\Filipa_dados\results\fossum_roi_x490_step01_old_config_baseline_20260509_235101`
- Step00: `C:\Users\pedro\Documents\Filipa_dados\results\fossum_roi_x490_step00_dataset_20260509_232915`

## Original classes
{
  "class_01": 157,
  "class_02": 102,
  "class_03": 26,
  "class_04": 13,
  "class_05": 72
}

## C01/C04 diagnostics
{
  "c01_intra_mean_feature_distance": 45.97713517681836,
  "c04_intra_mean_feature_distance": 81.03473135106232,
  "c01_c04_between_mean_feature_distance": 133.39100882928753,
  "prototype_corr": 0.5925810286728003,
  "prototype_rmse_norm": 0.8695844411849976,
  "should_merge": false
}

## C01 internal split
{
  "sizes": [
    {
      "subcluster": "C01a",
      "n_days": 38
    },
    {
      "subcluster": "C01b",
      "n_days": 119
    }
  ],
  "mean_difference_norm": 0.6795346140861511,
  "has_internal_substructure": true
}

## Recommendation
Try 6-class interpretation/cut first, then run patch-size sensitivity to confirm C01 split stability.

## Top cut alternatives
| cut_name | n_classes | class_sizes | min_class_size | max_class_size | mean_class_size | size_cv | tiny_class_count_lt10 | mean_prototype_rmse | max_prototype_corr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| k4 | 4 | [157, 102, 26, 85] | 26 | 157 | 92.500000 | 0.505022 | 0 | 1.136173 | 0.990395 |
| sd0.40 | 4 | [157, 102, 26, 85] | 26 | 157 | 92.500000 | 0.505022 | 0 | 1.136173 | 0.990395 |
| k5 | 5 | [157, 102, 26, 13, 72] | 13 | 157 | 74.000000 | 0.707417 | 0 | 1.433672 | 0.990395 |
| sd0.30 | 5 | [157, 102, 26, 13, 72] | 13 | 157 | 74.000000 | 0.707417 | 0 | 1.433672 | 0.990395 |
| sd0.35 | 5 | [157, 102, 26, 13, 72] | 13 | 157 | 74.000000 | 0.707417 | 0 | 1.433672 | 0.990395 |
| k6 | 6 | [157, 102, 13, 13, 13, 72] | 13 | 157 | 61.666667 | 0.886404 | 0 | 1.307923 | 0.993432 |
| sd0.25 | 6 | [157, 102, 13, 13, 13, 72] | 13 | 157 | 61.666667 | 0.886404 | 0 | 1.307923 | 0.993432 |
| k7 | 7 | [38, 119, 102, 13, 13, 13, 72] | 13 | 119 | 52.857143 | 0.787966 | 0 | 1.312818 | 0.991723 |

The Step01 baseline clustering was diagnosed to determine whether the observed class issues are caused by the dendrogram cut or by the feature extraction configuration.
