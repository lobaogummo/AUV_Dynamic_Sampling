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
- dictionary sizes (xds): 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
- seeds: 11, 23, 37, 53, 71

## Variabilidade entre seeds
- dictionary sizes com mean_icv_std > 0: 11 / 11

## Summary
| dictionary_size | executed_runs | mean_icv_mean | mean_icv_std | std_icv_mean | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 2.000000 | 5.000000 | 8360.786743 | 2421.553808 | 7969.245286 | 18.000000 | 74.107273 |
| 3.000000 | 5.000000 | 9623.787128 | 2655.825713 | 8682.481266 | 22.000000 | 112.448819 |
| 4.000000 | 5.000000 | 7900.322852 | 2142.315309 | 7674.836339 | 19.000000 | 126.746420 |
| 5.000000 | 5.000000 | 10275.662341 | 3735.679326 | 9624.146929 | 16.000000 | 135.446767 |
| 6.000000 | 5.000000 | 11105.379883 | 3184.758564 | 10180.935715 | 26.000000 | 139.139143 |
| 7.000000 | 5.000000 | 9744.855576 | 3327.426821 | 9346.653220 | 20.000000 | 146.032596 |
| 8.000000 | 5.000000 | 10886.647955 | 3111.945844 | 10276.841482 | 26.000000 | 154.088888 |
| 9.000000 | 5.000000 | 9852.592755 | 3393.706802 | 9324.273210 | 21.000000 | 157.425550 |
| 10.000000 | 5.000000 | 10178.456647 | 2512.399689 | 9013.329715 | 31.000000 | 156.058962 |
| 11.000000 | 5.000000 | 10918.664838 | 2507.134792 | 10636.140578 | 30.000000 | 158.705584 |
| 12.000000 | 5.000000 | 10760.444330 | 3304.502846 | 10202.864243 | 20.000000 | 157.634986 |

## Ranking atualizado (balanced)
| dictionary_size | balanced_score | mean_icv_mean | mean_icv_std | std_icv_mean | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 4.000000 | 2.800000 | 7900.322852 | 2142.315309 | 7674.836339 | 19.000000 | 126.746420 |
| 2.000000 | 3.500000 | 8360.786743 | 2421.553808 | 7969.245286 | 18.000000 | 74.107273 |
| 3.000000 | 3.700000 | 9623.787128 | 2655.825713 | 8682.481266 | 22.000000 | 112.448819 |
| 10.000000 | 4.400000 | 10178.456647 | 2512.399689 | 9013.329715 | 31.000000 | 156.058962 |
| 7.000000 | 6.200000 | 9744.855576 | 3327.426821 | 9346.653220 | 20.000000 | 146.032596 |
| 9.000000 | 6.600000 | 9852.592755 | 3393.706802 | 9324.273210 | 21.000000 | 157.425550 |
| 8.000000 | 7.200000 | 10886.647955 | 3111.945844 | 10276.841482 | 26.000000 | 154.088888 |
| 11.000000 | 7.300000 | 10918.664838 | 2507.134792 | 10636.140578 | 30.000000 | 158.705584 |
| 6.000000 | 7.400000 | 11105.379883 | 3184.758564 | 10180.935715 | 26.000000 | 139.139143 |
| 12.000000 | 8.200000 | 10760.444330 | 3304.502846 | 10202.864243 | 20.000000 | 157.634986 |
| 5.000000 | 8.300000 | 10275.662341 | 3735.679326 | 9624.146929 | 16.000000 | 135.446767 |

## Melhores candidatos finais
| dictionary_size | balanced_score | mean_icv_mean | mean_icv_std | min_class_size_min | runtime_mean_seconds |
| --- | --- | --- | --- | --- | --- |
| 4.000000 | 2.800000 | 7900.322852 | 2142.315309 | 19.000000 | 126.746420 |
| 2.000000 | 3.500000 | 8360.786743 | 2421.553808 | 18.000000 | 74.107273 |
| 3.000000 | 3.700000 | 9623.787128 | 2655.825713 | 22.000000 | 112.448819 |

## Check xds=4
- xds=4 continua a melhor escolha.

## Caminhos de outputs
- runs: `results/fossum/dictionary_size_sensitivity_fossum/runs.csv`
- summary: `results/fossum/dictionary_size_sensitivity_fossum/summary.csv`
- plots: `results/fossum/dictionary_size_sensitivity_fossum/plots`
- prototipos: `results/fossum/dictionary_size_sensitivity_fossum/prototypes_xdsXX_seedSS`
- paineis de classe: `results/fossum/dictionary_size_sensitivity_fossum/class_members_xdsXX_seedSS`