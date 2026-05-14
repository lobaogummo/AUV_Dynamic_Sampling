# Step08 Final Descriptor Report

## A. Old Logic Audit
The old production descriptor logic was found in `scripts/11_prototype_characterization.py` and `scripts/prototype_characterization_utils.py`, with upstream CV labels from `scripts/10_seed11_cv_analysis.py`/`scripts/cv_seed11_utils.py` and notebook references. The reusable backbone is label-driven segmentation, gradient magnitude, boundary score, and pixel/region descriptor tables.

## B. Inputs Used
- Step00: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step00_dataset_20260509_232915`
- Step05: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755`
- Step07-CV: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step07_cv_notebook_faithful_20260514_150645`
- Step06: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\october_surface_temppred_std_roi_x490_20260511_155923` reference only, not used for calculations.

## C. Final Descriptor Definitions
- Regime/class descriptors summarize prototype distribution and CV regime label.
- Gradient descriptors measure spatial temperature transitions on the canonical prototype.
- Boundary/front descriptors reuse the old boundary-score idea: multi-regime interface plus proximity/gradient; single-gradient capped gradient proxy; homogeneous zero boundary.
- Heterogeneity descriptors combine local variance, roughness and canonical class std maps.
- Cold/warm/neutral segmentation uses Otsu-guided tertiles for multi-regime and tertiles otherwise.
- Residual descriptors use Step05 class members versus the class prototype.
- Planner maps are normalized to [0,1] over the Step00 mask.

## D. Ranking Classes
- gradient: [1, 5, 6, 2, 3, 4]
- boundary: [1, 5, 6, 2, 4, 3]
- heterogeneity: [2, 5, 1, 4, 6, 3]
- interest: [1, 6, 5, 2, 3, 4]
- cold_fraction: [2, 3, 5, 4, 1, 6]
- warm_fraction: [2, 3, 5, 4, 6, 1]

## E. Recommended Step09 Use
Classify October TEMPpred with the Step05 canonical model, assign each day the descriptor library of the predicted class, optionally compute direct TEMPpred descriptors as diagnostics, then combine STD with `step08_descriptor_interest_map.npy` in the planner step.

## F. Verdict
READY_FOR_STEP09_TEMPRED_CLASSIFICATION_AND_DESCRIPTOR_ASSIGNMENT