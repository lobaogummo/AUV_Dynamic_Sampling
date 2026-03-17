# DICTIONARY_SIZE_SENSITIVITY_FOSSUM

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
- patch size fixo: (72,40)
- dictionary sizes (xds): 4
- seeds: 11

## Variabilidade entre seeds
- dictionary sizes com mean_icv_std > 0: 0 / 1

## Summary
| dictionary_size | executed_runs | mean_icv_mean | mean_icv_std | std_icv_mean | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 4.000000 | 1.000000 | 10785.039062 | nan | 9373.693103 | 66.000000 | 105.739583 |

## Ranking atualizado (balanced)
| dictionary_size | balanced_score | mean_icv_mean | mean_icv_std | std_icv_mean | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 4.000000 | nan | 10785.039062 | nan | 9373.693103 | 66.000000 | 105.739583 |

## Melhores candidatos finais
| dictionary_size | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- |
| 4.000000 | nan | 10785.039062 | nan | 66.000000 | 105.739583 |

## Check xds=4
- xds=4 continua a melhor escolha.

## Caminhos de outputs
- runs: `results/fossum/dictionary_size_sensitivity_fossum_smoketest/runs.csv`
- summary: `results/fossum/dictionary_size_sensitivity_fossum_smoketest/summary.csv`
- plots: `results/fossum/dictionary_size_sensitivity_fossum_smoketest/plots`
- prototipos: `results/fossum/dictionary_size_sensitivity_fossum_smoketest/prototypes_xdsXX_seedSS`
- paineis de classe: `results/fossum/dictionary_size_sensitivity_fossum_smoketest/class_members_xdsXX_seedSS`