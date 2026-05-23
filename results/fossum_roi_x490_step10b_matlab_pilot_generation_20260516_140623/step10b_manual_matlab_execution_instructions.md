# Step10B Manual MATLAB Execution Instructions

MATLAB is not available on the shell PATH here, so run this in MATLAB GUI/Command Window.

```matlab
cd('C:/Users/E713181/Documents/Dados/FILIPA_DADOS/scripts/matlab_step10b_pilot')
cfg = step10b_pilot_config();
cfg.dry_run
step10b_run_pilot_generation
```

After dry-run succeeds, edit `step10b_pilot_config.m` and change:

```matlab
cfg.dry_run = false;
```

Then run again:

```matlab
cd('C:/Users/E713181/Documents/Dados/FILIPA_DADOS/scripts/matlab_step10b_pilot')
step10b_run_pilot_generation
```

Expected output folder: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step10b_matlab_pilot_generation_20260516_140623`

After MATLAB finishes, validate predModels from PowerShell:

```powershell
python scripts\10b_check_pilot_predmodels_generated.py --output "C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step10b_matlab_pilot_generation_20260516_140623"
```