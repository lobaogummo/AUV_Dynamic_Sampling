# Exhaustive Temperature Transform Summary (day299)

- source variable verified as temperature: `YES`
- target variable verified as temperature: `YES`
- same day confirmed: `YES`

Final verdict:
- source variable verified as temperature: YES
- target variable verified as temperature: YES
- same day confirmed: YES
- exact transform found: NO
- near-perfect transform found: NO
- best method: dense_optical_flow_tvl1
- best interpolation: linear
- best domain: roi/masked
- best RMSE: 0.699406
- best Pearson: 0.776598
- main residual explanation: target temperature field appears not to be an exact transformed copy of tempRes; residuals are mainly explained by field-content differences plus interpolation/crop effects.

The exhaustive investigation on temperature fields concludes that no exact transform exists, with the best alignment obtained using dense_optical_flow_tvl1.
