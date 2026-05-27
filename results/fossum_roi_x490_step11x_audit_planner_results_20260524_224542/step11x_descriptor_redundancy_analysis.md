# Descriptor redundancy analysis

| descriptor | mean_pearson | mean_spearman | mean_top10_jaccard | mean_hotspot_distance |
| --- | --- | --- | --- | --- |
| representative_zone | 0.263 | 0.236 | 0.039 | 26.380 |
| boundary_score | 0.042 | 0.066 | 0.109 | 37.787 |
| interest_map | 0.035 | 0.066 | 0.102 | 35.682 |
| heterogeneity | 0.017 | 0.032 | 0.066 | 36.885 |
| warm_region | -0.065 | -0.064 | 0.090 | 38.366 |
| gradient | -0.086 | -0.022 | 0.072 | 40.634 |
| cold_region | -0.238 | -0.225 | 0.075 | 41.462 |

- boundary_score is not fully redundant by top-hotspot overlap, but it often follows broad high-value spatial structures and can still pull vehicles toward similar areas.
- Lower-redundancy descriptors worth testing first: cold_region, gradient, warm_region.
- For multi-AUV separation, cold/warm or representative-zone maps are more directly role-defining than boundary_score.