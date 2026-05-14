# Data synchronization audit

Generated: 2026-05-14T10:56:14

## Git state

- Git root: `C:/Users/pedro/Documents/Filipa_dados`
- Branch: `master`
- Remote: `origin	https://github.com/lobaogummo/FILIPA_DADOS.git (fetch)`
- Latest commit: `a11738d Add notebook-faithful CV analysis for ROI x490`
- Working tree is dirty; there are local uncommitted Overleaf/results/scripts changes not included in this audit recommendation.

## Size and tracking summary

| Label | Path | Exists | Files | Size | Tracked files | Ignored sample count | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| repo_data_root | `data` | True | 10160 | 97.229 GB | 587 | 1855 |  |
| repo_results_root | `results` | True | 12779 | 1.213 GB | 11089 | 22 |  |
| raw_filipa_root | `data/dadosParaPedro_Fresnel` | True | 629 | 45.992 GB | 0 | 629 | Ignored by `data/**`; too large for normal Git. |
| step00 | `results/fossum_roi_x490_step00_dataset_20260509_232915` | True | 763 | 71.46 MB | 762 | 1 |  |
| step05 | `results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755` | True | 25 | 55.46 MB | 0 | 2 |  |
| step06 | `results/october_surface_temppred_std_roi_x490_20260511_155923` | True | 149 | 15.16 MB | 0 | 1 |  |
| pipeline_status_audit | `results/pipeline_status_audit_20260512_222930` | False | 0 | 0.0 MB | 0 | 0 | Missing on this PC. |
| step07_cv_notebook_faithful | `results/fossum_roi_x490_step07_cv_notebook_faithful_20260512_233154` | True | 48 | 1.08 MB | 48 | 0 |  |

## Important manifest

See `DATA_MANIFEST.csv` for file-level checks. Key finding: raw Filipa data are outside Git; selected current results are partly untracked and some binary files are ignored by `*.nc` / `*.npz`.

## Large files in essential paths (>10 MB)

| Size MB | Group | Path | Tracked | Ignored |
|---:|---|---|---:|---:|
| 224.61 | raw_filipa_root | `data/dadosParaPedro_Fresnel/01.Data/ALL/thetao_20260427.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_1.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_10.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_11.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_12.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_13.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_14.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_15.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_16.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_17.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_2.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_3.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_4.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_5.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_6.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_7.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_8.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20240930/01-10-2024_predModel_9.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_1.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_10.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_11.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_12.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_13.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_14.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_15.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_16.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_17.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_2.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_3.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_4.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_5.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_6.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_7.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_8.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241001/02-10-2024_predModel_9.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_1.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_10.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_11.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_12.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_13.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_14.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_15.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_16.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_17.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_2.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_3.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_4.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_5.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_6.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_7.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_8.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241002/03-10-2024_predModel_9.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241003/04-10-2024_predModel_1.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241003/04-10-2024_predModel_10.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241003/04-10-2024_predModel_11.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241003/04-10-2024_predModel_12.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241003/04-10-2024_predModel_13.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241003/04-10-2024_predModel_14.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241003/04-10-2024_predModel_15.nc` | False | True |
| 80.14 | raw_filipa_root | `data/dadosParaPedro_Fresnel/02.Simulations/HighRes/Daily_dpt_20241003/04-10-2024_predModel_16.nc` | False | True |

Only first 60 shown out of 620 large files.


## .gitignore findings

- `data/**` ignores new data folders, including `data/dadosParaPedro_Fresnel`.
- `*.nc`, `*.npz`, `*.mat`, `*.out`, compressed archives and model binaries are ignored globally.
- `*.npy`, `*.png`, `*.csv`, `*.json`, and `*.md` are not globally ignored, so they can be tracked unless under an ignored directory.
- `results/` itself is not globally ignored, but specific heavy extensions inside results may be ignored.

## What is missing from Git for another PC

- The full Filipa raw dataset: `data/dadosParaPedro_Fresnel` (~46 GB).
- The local audit folder `results/pipeline_status_audit_20260512_222930` is missing on this PC, so it cannot be pushed from here unless restored.
- Several required current result folders are present locally but not fully versioned; notably Step00/Step05/Step06 include binary arrays and `.nc`/`.npz` files, some of which are ignored.
- Step07 notebook-faithful output is already tracked/pushed from the prior commit.

## Recommendation

Recommended option: **Option 3 - keep large data outside Git**, plus commit lightweight manifests and this checker. The raw Filipa folder alone is ~46 GB and the full `data/` tree is ~97 GB, which is not appropriate for normal Git and likely exceeds practical GitHub LFS quota as well.

Use OneDrive/external disk/network storage for `data/dadosParaPedro_Fresnel` and any large generated results. Use Git for scripts, reports, manifests, and small reproducible outputs. If later you want selected binary outputs in Git, use Git LFS only for a small explicit subset, not the full raw dataset.

## Commands for recommended solution

On this PC, after reviewing files to commit:

```powershell
git add sync_audit_report.md DATA_MANIFEST.md DATA_MANIFEST.csv sync_audit_inventory.csv scripts/check_required_data.py proposta_gitignore_patch.md
git commit -m "Add data synchronization manifest and checker"
git push
```

No push was executed by this audit.

## How to prepare the other PC

```powershell
git pull
# Copy the external data/results folders listed in DATA_MANIFEST.md into the same relative paths.
python scripts/check_required_data.py
```

If using Git LFS later for selected binaries:

```powershell
git lfs install
git lfs pull
python scripts/check_required_data.py
```

## Manual copy list

- `data/dadosParaPedro_Fresnel`
- `results/fossum_roi_x490_step00_dataset_20260509_232915`
- `results/fossum_roi_x490_step05_canonical_patch40x24_dict4_sd25_20260512_181755`
- `results/october_surface_temppred_std_roi_x490_20260511_155923`
- `results/pipeline_status_audit_20260512_222930` if you can restore it from the PC where it exists
- Any future `results/*descriptor*`, `results/*step08*`, or later planner outputs needed for analysis

## Do not blindly add

- Do not `git add data/` or `git add results/` wholesale.
- Do not force-add `data/dadosParaPedro_Fresnel` to normal Git.
- Do not push large `.nc`, `.npz`, `.out`, `.mat` files without deciding between external storage and LFS.
