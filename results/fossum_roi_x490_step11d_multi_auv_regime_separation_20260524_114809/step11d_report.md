# Step11D Multi-AUV Regime Separation

- Output: `C:\Users\pedro\Documents\Filipa_dados\results\fossum_roi_x490_step11d_multi_auv_regime_separation_20260524_114809`
- Planned runs/strategies: 11
- Vehicle-specific maps supported: `False`
- Overlap penalty supported: `False`
- Post-solver selection needed: `True`
- Best strategy by complementarity: `multi_boundary_alpha050`
- Verdict: `STEP11D_COMPLETED_WITH_POST_SOLVER_SELECTION`

## Answers
1. Vehicle-specific maps: `False`.
2. Real overlap penalty: `False`.
3. Post-solver selection: `True`.
4. Boundary-only juntou os veiculos? overlap=0.000; baseline overlap=0.000.
5. Vehicle-specific maps: see `step11d_fleet_level_metrics.csv` and selected pair summary.
6. Overlap/separation: see `step11d_overlap_and_separation_metrics.csv`.
7. Region coverage: see `fleet_region_A_coverage` and `fleet_region_B_coverage`.
8. Operational cost: compare `trajectory_length`/`mission_duration` in vehicle metrics.
9. Most promising strategy: `multi_boundary_alpha050`.
10. Compatibility: native shared-map multi-AUV is real planner behavior; vehicle-specific/sequential/post-solver parts are proxy/diagnostic wrappers.