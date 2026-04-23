# CAND_B Day299 Forensic Summary

- Baseline independent recomputation from numeric z299 source matches saved CAND_B planner-aligned array on shape, mask, and values.
- Wrong-day, swapped/flipped orientation, and off-by-one controls all diverge significantly from saved output.
- Plotting settings (origin/aspect/transpose/normalization) visibly change appearance even with identical underlying arrays.
- Interpolation-choice controls indicate expected smoothing effects without geometric misalignment.

Final verdict:
- source day verified: YES
- numerical source used: YES
- planner mask correctly applied: YES
- grid mapping geometrically consistent: YES
- major bug found: NO
- main explanation of visible differences: Differences are expected from interpolation smoothness, planner mask layout, and plotting/aspect choices; no geometric/day-index misalignment bug was detected.

The investigation concludes that the visible discrepancy is expected due to regridding/masking/plotting, based on the evidence above.
