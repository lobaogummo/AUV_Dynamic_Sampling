# Step09B Top20 C01/C06 TEMPpred Classification Report

## Method
The 20 Step10E TEMPpred ROI maps were normalized with Step00 global mean/std, encoded with the fixed Step05 dictionary, scaled with mean/std reconstructed from the Step05 canonical feature matrix, and classified by nearest canonical class centroid. STD/variance was used only for diagnostic overlap with Step08 descriptor maps.

## Expected vs Predicted
- C01 -> C01: 5
- C01 -> C02: 4
- C01 -> C06: 1
- C06 -> C02: 1
- C06 -> C06: 9

- C01 preserved: 5/10
- C06 preserved: 9/10

## Mismatches
- 2024-06-18: C01 -> C06, confidence=0.1135
- 2024-06-20: C01 -> C02, confidence=0.4341
- 2024-06-29: C01 -> C02, confidence=0.5276
- 2024-07-03: C01 -> C02, confidence=0.6920
- 2024-07-26: C01 -> C02, confidence=0.3620
- 2024-06-12: C06 -> C02, confidence=0.5938

## Low Confidence Days
- 2024-06-18: predicted C06, confidence=0.1135, nearest=76.309
- 2024-06-27: predicted C01, confidence=0.1161, nearest=139.112
- 2024-07-04: predicted C01, confidence=0.2183, nearest=75.976
- 2024-05-22: predicted C06, confidence=0.0320, nearest=96.867
- 2024-06-15: predicted C06, confidence=0.0195, nearest=108.779

## Planner-Oriented Recommendations
- 2023-12-22: expected C06, predicted C06, score=0.445, STD_mean=0.0170
- 2023-12-21: expected C06, predicted C06, score=0.421, STD_mean=0.0150
- 2023-12-19: expected C06, predicted C06, score=0.358, STD_mean=0.0155
- 2024-07-03: expected C01, predicted C02, score=0.353, STD_mean=0.0639
- 2023-12-18: expected C06, predicted C06, score=0.346, STD_mean=0.0138

## Interpretation
Class changes should be read as a diagnostic of how the geostatistical TEMPpred field moved in the Step05 sparse-code feature space, not as a new ground-truth label. Higher STD-interest overlap is useful for the next STD + descriptor fusion step.

## Verdict
STEP09B_COMPLETED_WITH_WARNINGS_REVIEW_MISMATCHES