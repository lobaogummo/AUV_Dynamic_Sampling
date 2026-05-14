# Step07-CV notebook-faithful report

The previous Step07-CV run added descriptor-oriented metrics that were not in
the original notebook. This run corrects that by following the notebook
structure directly.

## Main outputs

- `cv_features_global_seed11.csv`
- `cv_validation_seed11.csv`
- `cv_features_global_seed11_simple.csv`
- `cv_features_global_seed11_image_only.csv`
- empty local class02 CSVs for structural compatibility
- notebook-style figures for prototypes, splits, simple labels and image-only labels

## Regime labels

Simple arr+mask:

```text
    prototype_name    regime_label  std_temp  min_region_ratio  inter_region_diff  coherence_min  p90_grad  front_area_ratio
prototype_class_01 single_gradient  0.385417          0.415417           0.672307            1.0  0.018234          0.100075
prototype_class_02     homogeneous  0.157402          0.331834           0.290418            1.0  0.009840          0.100075
prototype_class_03     homogeneous  0.101411          0.176787           0.216237            1.0  0.012216          0.100075
prototype_class_04     homogeneous  0.105001          0.409920           0.180757            1.0  0.005160          0.100075
prototype_class_05 single_gradient  0.232050          0.443403           0.403082            1.0  0.010435          0.100075
prototype_class_06 single_gradient  0.191054          0.391929           0.336103            1.0  0.009006          0.100075
```

Image-only clean PNG:

```text
    prototype_name    regime_label  std_temp  min_region_ratio  inter_region_diff  coherence_min  p90_grad
prototype_class_01    multi_regime 49.511768          0.361694          89.834951            1.0  2.651905
prototype_class_02 single_gradient 15.934937          0.265117          31.437889            1.0  1.203553
prototype_class_03     homogeneous  2.121251          0.126937           5.466232            1.0  0.384638
prototype_class_04     homogeneous  6.487098          0.449900          11.124084            1.0  0.601325
prototype_class_05 single_gradient 25.276373          0.464393          43.777340            1.0  1.128757
prototype_class_06    multi_regime 24.737841          0.411669          42.982593            1.0  1.154716
```

## Final verdict

NOTEBOOK_FAITHFUL_CV_PORT_COMPLETE
