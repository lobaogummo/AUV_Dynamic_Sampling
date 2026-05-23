# Step10B MATLAB Original Scripts Audit

## Original Scripts
- `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\data\dadosParaPedro_Fresnel\dadosParaPedro_Fresnel\00.Code\write14days.m`
- `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\data\dadosParaPedro_Fresnel\dadosParaPedro_Fresnel\00.Code\runSimulations.m`

## Hardcoded Paths/Dates
- `write14days.m`: local source/output paths and October 31-day loop.
- `runSimulations.m`: local source/output paths, October HRes folder, and two hardcoded prediction days.

## Adaptation
- New MATLAB scripts are written under `scripts/matlab_step10b_pilot`.
- Original scripts were not edited.
- Pilot dates live in `step10b_pilot_config.m`.
- `dry_run = true` by default.
- New scripts use local repo paths and output only inside the Step10B output folder.
- HRes windows needed for the pilot are target date minus 1 day and target date plus 1 day, matching the original simulation and validation lookup pattern.