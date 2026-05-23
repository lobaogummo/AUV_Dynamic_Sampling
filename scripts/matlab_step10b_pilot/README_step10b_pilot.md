# Step10B MATLAB Pilot

This folder contains non-destructive MATLAB adaptations of Filipa's scripts.

Default behavior is `dry_run = true` in `step10b_pilot_config.m`.

Run in MATLAB:

```matlab
cd('C:/Users/E713181/Documents/Dados/FILIPA_DADOS/scripts/matlab_step10b_pilot')
cfg = step10b_pilot_config();
step10b_run_pilot_generation
```

After the dry-run is checked, edit only `cfg.dry_run = false` in
`step10b_pilot_config.m` and run the same controller again.
