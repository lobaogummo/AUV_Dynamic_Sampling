# Step11D Multi-AUV Planner Capability Audit

- Multi-AUV support: `True` via `AUV_NUMBER`, `MISSION_DURATIONS`, and PyVRP `VehicleType`.
- Vehicle-specific maps supported: `False`.
- Vehicle-specific prizes supported: `False`.
- Real overlap penalty supported: `False`.
- Same-node duplicate handling: `True`. Single shared client set means exact duplicate POI visits are not expected inside one VRP solution; path overlap between segments is not explicitly penalized.
- Sequential planning viable: `False`.
- Post-solver selection needed: `True`.
- Recommended mode: `native_shared_map_plus_1auv_candidates_post_solver_selection`.