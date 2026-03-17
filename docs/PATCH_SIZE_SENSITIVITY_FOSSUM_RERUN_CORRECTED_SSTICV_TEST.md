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
- patch sizes: (72,40)
- seeds: 11, 23

## Variabilidade entre seeds
- patch sizes com mean_icv_std > 0: 1 / 1

## Summary
| patch_w | patch_h | executed_runs | mean_icv_mean | mean_icv_std | std_icv_mean | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 72.000000 | 40.000000 | 2.000000 | 8771.985168 | 2846.888119 | 8327.124362 | 19.000000 | 119.848998 |

## Ranking atualizado (balanced)
| patch_w | patch_h | balanced_score | mean_icv_mean | mean_icv_std | std_icv_mean | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 72.000000 | 40.000000 | 1.000000 | 8771.985168 | 2846.888119 | 8327.124362 | 19.000000 | 119.848998 |

## Melhores candidatos finais
| patch_w | patch_h | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 72.000000 | 40.000000 | 1.000000 | 8771.985168 | 2846.888119 | 19.000000 | 119.848998 |

## Caminhos de outputs
- runs: `results/fossum/patch_size_sensitivity_fossum_rerun_corrected_ssticv_test/runs.csv`
- summary: `results/fossum/patch_size_sensitivity_fossum_rerun_corrected_ssticv_test/summary.csv`
- plots: `results/fossum/patch_size_sensitivity_fossum_rerun_corrected_ssticv_test/plots`
- prototipos: `results/fossum/patch_size_sensitivity_fossum_rerun_corrected_ssticv_test/prototypes_wXX_hYY_seedSS`
- paineis de classe: `results/fossum/patch_size_sensitivity_fossum_rerun_corrected_ssticv_test/class_members_wXX_hYY_seedSS`