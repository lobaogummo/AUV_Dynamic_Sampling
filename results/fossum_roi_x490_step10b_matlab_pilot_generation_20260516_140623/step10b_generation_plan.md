# Step10B MATLAB Pilot Generation Plan

1. Run MATLAB dry-run with the generated config.
2. Confirm planned HRes and predModel paths.
3. Set `cfg.dry_run = false` in `step10b_pilot_config.m`.
4. Generate only the 4 pilot dates.
5. Run `python scripts/10b_check_pilot_predmodels_generated.py --output <output_folder>`.
6. Only after checks pass, create Step10C ROI x490 extraction.