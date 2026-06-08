# Step11Y rerun recommendation

Verdict: `MIXED_INPUTS_PARTIAL_RERUN_RECOMMENDED`

Rerun recommended because some region/crossing or vehicle-specific maps were derived through a TEMPpred fallback rather than the Step08 prototype descriptors assigned by predicted class.

## Minimal sequence

A. Single-AUV:
- 2024-08-24, 12h
- baseline_STD
- prototype_boundary_alpha050
- crossing_gamma025 using prototype regions

B. Multi-AUV:
- 2024-08-24, 2 AUVs, 12h
- baseline_STD
- prototype_vehicle_specific_maps

C. Repeat after C01 for:
- 2023-12-22
- 2024-10-30