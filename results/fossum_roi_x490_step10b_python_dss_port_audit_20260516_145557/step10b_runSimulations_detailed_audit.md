# Step10B runSimulations Detailed Audit

## Scope
Audited `runSimulations.m` and helper functions in `00.Code/Functions` to assess a Python + DSS.C.64.exe port.

## Functions Audited

| function | port status | confidence | role |
| --- | --- | --- | --- |
| runSimulations.m | PARTIAL_PORTED | medium | Loops predDate/depth, writes hard data, calls parFileDSS, reads outputs, writes TEMPpred/STD |
| grid2gslib.m | PORTED | high | MATLAB column-major flatten via save_var |
| save_var.m | PORTED | high | Writes title, ncol, var headers, numeric rows |
| import_gslib.m | PORTED | high | Reads ncol header and reshapes numeric data |
| gslib2grid.m | PORTED | high | MATLAB reshape into nx,ny,nz |
| writealldata_naza.m | NOT_FULLY_PORTED | medium-low | Builds Real column/coordinates for output days |
| parFileDSS.m | PARTIAL_PORTED | medium | Writes DSS parameter file and calls executable |
| readoutput_AUV.m | PARTIAL_PORTED | medium | Reads realizations, computes mean/median/variance (called StDev) |
| giveCoordinateInformation_naza.m | PARTIAL_PORTED | medium | Injects TEMPpred/STD into predModel |

## Key Finding
The mechanical Python+DSS path is partially operational: DSS.C.64.exe was called successfully in a 1-realization October test and a NetCDF with `TEMPpred` and `STD` was written with shape `[2,180,240]`.

However, the scientific validation against official October predModel is not yet PASS. The test used 1 realization, while official predModels use 100 realizations; therefore Python STD is zero and comparison fails. Additionally, official DSS seeds are not recorded, so exact reproduction is not guaranteed even with 100 realizations.

## Validation Output
- Dry-run output: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step10b_python_dss_port_validation_20260516_145427`
- Mechanical DSS validation output: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step10b_python_dss_port_validation_20260516_145439`
- Validation verdict: `PYTHON_DSS_PORT_NEEDS_FIXES`

## October Metrics Snapshot
                                                                                                                                                                          candidate                                                                                                                                                            reference  candidate_exists  reference_exists TEMPpred_shape_candidate TEMPpred_shape_reference STD_shape_candidate STD_shape_reference  TEMPpred_n  TEMPpred_rmse  TEMPpred_mae  TEMPpred_pearson  TEMPpred_candidate_mean  TEMPpred_reference_mean  TEMPpred_candidate_std  TEMPpred_reference_std  STD_n  STD_rmse  STD_mae  STD_pearson  STD_candidate_mean  STD_reference_mean  STD_candidate_std  STD_reference_std       date validation_status
C:\Users\E713181\Documents\Dados\FILIPA_DADOS\results\fossum_roi_x490_step10b_python_dss_port_validation_20260516_145439\predmodels\2024-10-30\2024-10-30_python_dss_predModel_1.nc C:\Users\E713181\Documents\Dados\FILIPA_DADOS\data\dadosParaPedro_Fresnel\dadosParaPedro_Fresnel\02.Simulations\HighRes\Daily_dpt_20241029\30-10-2024_predModel_1.nc              True              True            [2, 180, 240]            [2, 180, 240]       [2, 180, 240]       [2, 180, 240]       53140       0.187472      0.104769           0.88322                17.830252                17.824877                0.399492                0.348512  53140    0.0531 0.035999          NaN                 0.0            0.035999                0.0           0.039034 2024-10-30              FAIL
