# tempRes Georeference From Axes Summary (day299)

- Output directory: `results/Investigation_transition_to_planner/georef_tempres_from_axes_day299`
- Best method: `CAND_B_REGISTRATION_TO_HRES_SUBAREA__EPSG_32629_UTM29N_formula__hres_crop_centers__x_normal__y_normal`
- Best projection: `EPSG_32629_UTM29N_formula`
- Confidence: `PLAUSIBLE BUT NOT PROVEN`
- Primary validation target: `D4_predModel_TEMPpred_day0`
- Best numeric RMSE: `0.697128`
- Best numeric Pearson: `0.349373`
- Recommended-transform RMSE: `0.708774`
- Recommended-transform Pearson: `0.017378`
- Best physical-axis candidate: `AXES_FILIPA_DISPLAY_CROP_AS_FULL__EPSG_32629_UTM29N_formula__centers__x_flipped__y_flipped` (rank `7`, Pearson `0.293573`)

Temperature validation used TEMP/TEMPpred fields only; STD was inventoried but not used as a temperature target.

Final verdict:
- tempRes axes found: YES
- axes interpreted as physical km: UNCERTAIN
- HResNew/planner projected to km: YES
- best projection: EPSG_32629_UTM29N_formula
- best transform: CAND_B_REGISTRATION_TO_HRES_SUBAREA__EPSG_32629_UTM29N_formula__hres_crop_centers__x_normal__y_normal
- tempRes contained in HResNew: YES
- temperature-vs-temperature validation available: YES
- best RMSE temperature: 0.697128
- best Pearson temperature: 0.349373
- georeference confidence: PLAUSIBLE BUT NOT PROVEN
- recommended transform for descriptor transfer: results/Investigation_transition_to_planner/georef_tempres_from_axes_day299/tempres_georef_transform.json

The tempRes georeferencing from physical axes is classified as PLAUSIBLE BUT NOT PROVEN, and the recommended transform for transferring descriptors to the planner grid is CAND_B_REGISTRATION_TO_HRES_SUBAREA__EPSG_32629_UTM29N_formula__hres_crop_centers__x_normal__y_normal, based on the evidence above.