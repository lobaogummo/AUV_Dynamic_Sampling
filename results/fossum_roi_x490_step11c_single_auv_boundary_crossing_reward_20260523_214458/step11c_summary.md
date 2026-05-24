# Step11C Single-AUV Boundary Crossing Reward

- Output: `C:\Users\pedro\Documents\Filipa_dados\results\fossum_roi_x490_step11c_single_auv_boundary_crossing_reward_20260523_214458`
- Runs: 8/8 successful
- Planner route-level reward available: `False`
- Implementation mode: `map_proxy_static_node_prize`
- Mask source: `see masks/ per case`
- Verdict: `STEP11C_COMPLETED_WITH_PROXY_LIMITATION`

## Primary 12h Results
- baseline_STD: crossing_count=3, regions=2, frac_A=0.994, frac_B=0.006, diff_baseline=0.000
- boundary_alpha050: crossing_count=6, regions=2, frac_A=0.979, frac_B=0.021, diff_baseline=0.937
- crossing_gamma025: crossing_count=3, regions=2, frac_A=0.987, frac_B=0.013, diff_baseline=0.878
- crossing_gamma050: crossing_count=9, regions=2, frac_A=0.967, frac_B=0.033, diff_baseline=0.920

## Questions
- O crossing reward aumentou o numero de regimes visitados? no/unchanged in this run.
- A trajetoria atravessou mais claramente a boundary? yes.