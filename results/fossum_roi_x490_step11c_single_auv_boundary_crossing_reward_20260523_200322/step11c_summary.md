# Step11C Single-AUV Boundary Crossing Reward

- Output: `C:\Users\pedro\Documents\Filipa_dados\results\fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_200322`
- Runs: 7/7 successful
- Planner route-level reward available: `False`
- Implementation mode: `map_proxy_static_node_prize`
- Mask source: `Step09B cold_region_map/warm_region_map`
- Verdict: `STEP11C_COMPLETED_WITH_PROXY_LIMITATION`

## Primary 12h Results
- baseline_STD: crossing_count=0, regions=1, frac_A=1.000, frac_B=0.000, diff_baseline=0.000
- boundary_alpha050: crossing_count=6, regions=2, frac_A=0.843, frac_B=0.157, diff_baseline=0.928
- crossing_gamma025: crossing_count=10, regions=2, frac_A=0.823, frac_B=0.177, diff_baseline=0.934
- crossing_gamma050: crossing_count=2, regions=2, frac_A=0.929, frac_B=0.071, diff_baseline=0.932

## Questions
- O crossing reward aumentou o numero de regimes visitados? yes.
- A trajetoria atravessou mais claramente a boundary? yes.