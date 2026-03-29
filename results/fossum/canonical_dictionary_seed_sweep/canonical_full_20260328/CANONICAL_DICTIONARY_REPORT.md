# Canonical Dictionary Selection Report

## Sweep Configuration
- patch size: 72x40
- dictionary size: 4
- StandardScaler: True
- SD fraction evaluated: 0.30
- ranking_target_classes (04a): 5
- seeds tested: [11, 23, 37, 53, 71, 7, 19, 41, 83, 97]
- fractions passed to 04a: [0.3]
- run root: `results/fossum/canonical_dictionary_seed_sweep/canonical_full_20260328`

## Metric Definitions
- `mean_icv`: from current 04a output (SST-space ICV diagnostics).
- `weighted_mean_MPD`: pair-count-weighted mean of within-class pairwise Euclidean distances on normalized SST vectors over the common valid mask.
- `weighted_mean_pairwise_SSIM`: pair-count-weighted mean of within-class pairwise SSIM (global SSIM formula per image pair on normalized SST vectors over the common valid mask).
- Mask/NaN handling: only common-mask pixels are used; masked pixels are excluded from MPD/SSIM vectors.

## Selection Policy
- Primary eligibility: `number_of_classes == 5`, `singleton_count == 0`, `min_class_size >= 20`.
- Composite ranking on eligible seeds: 0.30 rank(mean_icv) + 0.30 rank(weighted_mean_MPD) + 0.30 rank(weighted_mean_pairwise_SSIM, descending) + 0.10 rank(min_class_size, descending).
- Selection filter: n_classes==5, singleton_count==0, min_class_size>=20.

## Per-Seed Results
| seed | status | number_of_classes | singleton_count | min_class_size | mean_icv | weighted_mean_MPD | weighted_mean_pairwise_SSIM | eligible_for_selection | composite_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11 | success | 5 | 0 | 20 | 1570.662854 | 35.277387 | 0.437128 | True | 1.500000 |
| 53 | success | 5 | 0 | 29 | 1368.818164 | 36.204111 | 0.365657 | True | 1.900000 |
| 23 | success | 5 | 0 | 23 | 1932.898938 | 36.638705 | 0.423565 | True | 2.600000 |
| 97 | success | 6 | 0 | 17 | 1463.172719 | 33.463364 | 0.515538 | False | nan |
| 19 | success | 6 | 0 | 6 | 1311.266327 | 33.837572 | 0.467624 | False | nan |
| 83 | success | 7 | 0 | 9 | 1264.266872 | 34.155390 | 0.546771 | False | nan |
| 7 | success | 5 | 0 | 18 | 1984.194849 | 34.353703 | 0.489095 | False | nan |
| 41 | success | 6 | 0 | 17 | 1650.684128 | 34.947317 | 0.512500 | False | nan |
| 71 | success | 4 | 0 | 19 | 1701.556976 | 39.492070 | 0.423512 | False | nan |
| 37 | success | 6 | 0 | 14 | 1481.916534 | 42.307750 | 0.401288 | False | nan |

## Canonical Seed
- selected seed: 11
- number_of_classes: 5
- singleton_count: 0
- min_class_size: 20
- mean_icv: 1570.662854
- weighted_mean_MPD: 35.277387
- weighted_mean_pairwise_SSIM: 0.437128
- canonical dictionary: `C:\Users\pedro\Documents\Filipa_dados\results\fossum\canonical_dictionary\canonical_dictionary.npz`
- canonical manifest: `C:\Users\pedro\Documents\Filipa_dados\results\fossum\canonical_dictionary\canonical_dictionary_manifest.json`