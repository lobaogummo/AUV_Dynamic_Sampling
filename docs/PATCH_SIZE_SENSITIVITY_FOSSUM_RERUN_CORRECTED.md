# PATCH_SIZE_SENSITIVITY_FOSSUM_RERUN_CORRECTED

## Correcoes aplicadas
- random_state=seed no MiniBatchDictionaryLearning
- shuffle=True no dicionario
- ordem das imagens embaralhada por seed
- ordem dos patches embaralhada por seed
- partial_fit em mini-batches

## Inputs numericos
- `results/fossum/X_surface_300.npy` (SST/original, usado para ICV)
- `results/fossum/X_surface_300_norm.npy`
- `results/fossum/mask_common.npy`

## Distincao metodologica
- dictionary learning, sparse coding e clustering: feitos em `X_surface_300_norm.npy`
- ICV: calculada em `X_surface_300.npy` (temperatura SST/original) usando os labels do clustering em normalizado
- definicao ICV por classe: soma da variancia pixel-a-pixel sobre a mascara valida

## PNGs
- PNGs nao foram usados para calculo numerico.
- PNGs usados apenas para paineis de classe: `results/fossum/pngs_normalized_surface_300_thesis`

## Configuracao
- xds=4, N_CLASSES=4, stride=1, todos os patches possiveis
- patch sizes: (16,16), (24,16), (32,20), (40,24), (48,32), (56,32), (64,36), (72,40), (80,44)
- seeds: 11, 23, 37, 53, 71

## Variabilidade entre seeds
- patch sizes com mean_icv_std > 0: 9 / 9

## Summary
| patch_w | patch_h | executed_runs | mean_icv_mean | mean_icv_std | std_icv_mean | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 16.000000 | 16.000000 | 5.000000 | 11649.325464 | 2899.457240 | 9104.366133 | 18.000000 | 283.455284 |
| 24.000000 | 16.000000 | 5.000000 | 11371.592096 | 4471.365759 | 9945.084846 | 16.000000 | 286.330545 |
| 32.000000 | 20.000000 | 5.000000 | 12715.284949 | 1590.623911 | 9731.600161 | 30.000000 | 272.647335 |
| 40.000000 | 24.000000 | 5.000000 | 9933.445761 | 1824.977347 | 9387.712727 | 13.000000 | 253.351062 |
| 48.000000 | 32.000000 | 5.000000 | 11790.838757 | 3107.064177 | 9723.541398 | 26.000000 | 200.698215 |
| 56.000000 | 32.000000 | 5.000000 | 9208.564365 | 3119.893631 | 8705.151162 | 18.000000 | 174.304405 |
| 64.000000 | 36.000000 | 5.000000 | 9755.023383 | 2374.741648 | 8881.648921 | 18.000000 | 144.072330 |
| 72.000000 | 40.000000 | 5.000000 | 7900.322852 | 2142.315309 | 7674.836339 | 19.000000 | 110.464553 |
| 80.000000 | 44.000000 | 5.000000 | 8771.832721 | 2695.508627 | 8756.886343 | 21.000000 | 77.350588 |

## Ranking atualizado (balanced)
| patch_w | patch_h | balanced_score | mean_icv_mean | mean_icv_std | std_icv_mean | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 72.000000 | 40.000000 | 2.100000 | 7900.322852 | 2142.315309 | 7674.836339 | 19.000000 | 110.464553 |
| 80.000000 | 44.000000 | 2.900000 | 8771.832721 | 2695.508627 | 8756.886343 | 21.000000 | 77.350588 |
| 64.000000 | 36.000000 | 4.100000 | 9755.023383 | 2374.741648 | 8881.648921 | 18.000000 | 144.072330 |
| 56.000000 | 32.000000 | 4.300000 | 9208.564365 | 3119.893631 | 8705.151162 | 18.000000 | 174.304405 |
| 32.000000 | 20.000000 | 5.400000 | 12715.284949 | 1590.623911 | 9731.600161 | 30.000000 | 272.647335 |
| 40.000000 | 24.000000 | 5.500000 | 9933.445761 | 1824.977347 | 9387.712727 | 13.000000 | 253.351062 |
| 48.000000 | 32.000000 | 6.100000 | 11790.838757 | 3107.064177 | 9723.541398 | 26.000000 | 200.698215 |
| 16.000000 | 16.000000 | 6.100000 | 11649.325464 | 2899.457240 | 9104.366133 | 18.000000 | 283.455284 |
| 24.000000 | 16.000000 | 7.900000 | 11371.592096 | 4471.365759 | 9945.084846 | 16.000000 | 286.330545 |

## Melhores candidatos finais
| patch_w | patch_h | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 72.000000 | 40.000000 | 2.100000 | 7900.322852 | 2142.315309 | 19.000000 | 110.464553 |
| 80.000000 | 44.000000 | 2.900000 | 8771.832721 | 2695.508627 | 21.000000 | 77.350588 |
| 64.000000 | 36.000000 | 4.100000 | 9755.023383 | 2374.741648 | 18.000000 | 144.072330 |

## Caminhos de outputs
- runs: `results/fossum/patch_size_sensitivity_fossum_rerun_corrected/runs.csv`
- summary: `results/fossum/patch_size_sensitivity_fossum_rerun_corrected/summary.csv`
- plots: `results/fossum/patch_size_sensitivity_fossum_rerun_corrected/plots`
- prototipos: `results/fossum/patch_size_sensitivity_fossum_rerun_corrected/prototypes_wXX_hYY_seedSS`
- paineis de classe: `results/fossum/patch_size_sensitivity_fossum_rerun_corrected/class_members_wXX_hYY_seedSS`