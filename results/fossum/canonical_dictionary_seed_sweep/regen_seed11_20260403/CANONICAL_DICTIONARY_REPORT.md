# Canonical Dictionary Selection Report

## Sweep Configuration
- patch size: 72x40
- dictionary size: 4
- StandardScaler: True
- SD fraction evaluated: 0.30
- ranking_target_classes (04a): 5
- seeds tested: [11]
- fractions passed to 04a: [0.3]
- run root: `results/fossum/canonical_dictionary_seed_sweep/regen_seed11_20260403`

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
| 11 | success | 5 | 0 | 20 | 1601.534888 | 35.654169 | 0.420744 | True | 1.000000 |

## Canonical Seed
- selected seed: 11
- number_of_classes: 5
- singleton_count: 0
- min_class_size: 20
- mean_icv: 1601.534888
- weighted_mean_MPD: 35.654169
- weighted_mean_pairwise_SSIM: 0.420744
- canonical dictionary: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\fossum\canonical_dictionary\canonical_dictionary.npz`
- canonical manifest: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\fossum\canonical_dictionary\canonical_dictionary_manifest.json`