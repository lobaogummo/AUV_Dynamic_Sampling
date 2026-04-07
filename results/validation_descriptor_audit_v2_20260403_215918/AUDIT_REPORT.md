# Descriptor Audit Report (v2 semantic)

- Official characterization source: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\prototype_characterization_seed11\official_fixed_dictionary_seed11\official_pixelwise_v2_semantic`
- Validation output root: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\validation_descriptor_audit_v2_20260403_215918`

## 1) Executive summary
- Verdict: descriptors are **corretos mas ainda com fragilidades pontuais**.

## 2) Semantic/visual validity
- Prototype interpretative classes: {'faz sentido': 7}
- image_only label coherence: 7/7
- Visual evidence: figures in `figures/semantic/`.

## 3) Discriminative capacity
- Top descriptors by Fisher: [{'descriptor': 'n_regions', 'fisher_score': 714285714285.7145}, {'descriptor': 'region_area_entropy', 'fisher_score': 44759.72101725753}, {'descriptor': 'min_region_area_fraction', 'fisher_score': 1442.5268476149995}, {'descriptor': 'max_region_area_fraction', 'fisher_score': 925.619828647133}, {'descriptor': 'boundary_score_avg', 'fisher_score': 176.766503820012}]
- Ablation results: [{'setup': 'full', 'features': 'temp_std_avg|boundary_score_avg|gradient_magnitude_avg|n_regions|inter_region_temp_contrast', 'separability_score': 3.5189337440682893, 'silhouette': 0.1454499717707481, 'delta_sep_vs_full': 0.0, 'delta_sil_vs_full': 0.0}, {'setup': 'without_boundary_score_avg', 'features': 'temp_std_avg|gradient_magnitude_avg|n_regions|inter_region_temp_contrast', 'separability_score': 3.0330126764782186, 'silhouette': -0.0163521188460977, 'delta_sep_vs_full': -0.4859210675900707, 'delta_sil_vs_full': -0.1618020906168458}, {'setup': 'without_temp_std_avg', 'features': 'boundary_score_avg|gradient_magnitude_avg|n_regions|inter_region_temp_contrast', 'separability_score': 8.170367046578114, 'silhouette': 0.5223387227340206, 'delta_sep_vs_full': 4.651433302509825, 'delta_sil_vs_full': 0.3768887509632724}, {'setup': 'without_gradient_magnitude_avg', 'features': 'temp_std_avg|boundary_score_avg|n_regions|inter_region_temp_contrast', 'separability_score': 3.404408188229956, 'silhouette': 0.1634500542174181, 'delta_sep_vs_full': -0.1145255558383331, 'delta_sil_vs_full': 0.01800008244667}]
- Descriptor usefulness tags: [{'descriptor': 'min_region_area_fraction', 'audit_tag': 'redundant'}, {'descriptor': 'max_region_area_fraction', 'audit_tag': 'redundant'}, {'descriptor': 'boundary_score_avg', 'audit_tag': 'redundant'}, {'descriptor': 'inter_region_temp_contrast', 'audit_tag': 'redundant'}, {'descriptor': 'gradient_magnitude_avg', 'audit_tag': 'redundant'}, {'descriptor': 'n_regions', 'audit_tag': 'useful'}, {'descriptor': 'region_area_entropy', 'audit_tag': 'useful'}, {'descriptor': 'temp_std_avg', 'audit_tag': 'weak'}, {'descriptor': 'temp_mean_avg', 'audit_tag': 'weak'}]

## 4) Operational proxy (top-k=20)
- Mean enriched-baseline deltas: {'delta__transition_top_decile_coverage': 0.45714285714285713, 'delta__high_gradient_decile_coverage': 0.6928571428571428, 'delta__region_coverage_ratio': 0.07142857142857142, 'delta__region_balance_min_share': -0.1357142857142857, 'delta__informative_union_p75_coverage': 0.0, 'delta__spatial_spread_norm': 0.08452320099873532}
- Proxy maps: `figures/proxy_topk/`.

## 5) Technical integrity
- Integrity pass rate: 0.947
- Failed checks: [{'check': 'raster_vs_pixel_all_fields_match', 'detail': 'rows=56'}]

## 6) Facts, inferences, limitations
- Facts observed: all CSV/fig outputs in this folder and integrity tables.
- Probable inferences: descriptors capture regime semantics and provide useful signal for downstream feature engineering.
- Limitations: only 7 prototypes; proxy heuristic is not planner-level validation.
