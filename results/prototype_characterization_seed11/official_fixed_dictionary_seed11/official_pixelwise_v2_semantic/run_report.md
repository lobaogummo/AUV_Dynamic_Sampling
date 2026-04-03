# Prototype Characterization Run Report

- Generated UTC: 2026-04-03T15:40:12.418027+00:00
- Seed: 11
- Output dir: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\prototype_characterization_seed11\official_fixed_dictionary_seed11\official_pixelwise_v2_semantic`
- Image-only label run dir: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\computer_vision_seed11\official_fixed_dictionary_seed11\official_image_only_default`

## Coverage

- Prototypes processed: 7
- Global prototypes: 5
- Local class_02 prototypes: 2
- Pixel rows exported: 48475
- Region rows exported: 9
- Regime label counts: {'single_gradient': 3, 'homogeneous': 2, 'multi_regime': 2}

## Required Pixel Columns

- Present: True
- Columns: ['scope', 'prototype_key', 'prototype_name', 'prototype_regime_label', 'row', 'col', 'lat', 'lon', 'temp_mean', 'temp_std', 'region_label', 'region_label_id', 'boundary_score', 'gradient_magnitude', 'gradient_direction', 'distance_to_boundary', 'region_id']

## Prototype Summary

- global | class_01 | label=homogeneous | mode=image_only_homogeneous_single_region | valid_pixels=6925 | threshold=nan (label_driven_homogeneous)
- global | class_02 | label=single_gradient | mode=image_only_single_gradient_continuous | valid_pixels=6925 | threshold=nan (label_driven_single_gradient)
- global | class_03 | label=multi_regime | mode=image_only_multi_regime_discrete | valid_pixels=6925 | threshold=0.466601 (otsu)
- global | class_04 | label=homogeneous | mode=image_only_homogeneous_single_region | valid_pixels=6925 | threshold=nan (label_driven_homogeneous)
- global | class_05 | label=single_gradient | mode=image_only_single_gradient_continuous | valid_pixels=6925 | threshold=nan (label_driven_single_gradient)
- local_class02 | k2::subclass_01 | label=single_gradient | mode=image_only_single_gradient_continuous | valid_pixels=6925 | threshold=nan (label_driven_single_gradient)
- local_class02 | k2::subclass_02 | label=multi_regime | mode=image_only_multi_regime_discrete | valid_pixels=6925 | threshold=0.078717 (otsu)

## Semantic Checks

- homogeneous: n_regions[min=1, max=1, mean=1.00]
- multi_regime: n_regions[min=2, max=2, mean=2.00]
- single_gradient: n_regions[min=1, max=1, mean=1.00]
- homogeneous: boundary_score mean=0.0000, p95=0.0000
- single_gradient: boundary_score mean=0.2286, p95=0.3500
- multi_regime: boundary_score mean=0.6669, p95=0.9327

## Outputs

- `prototype_summary.csv`
- `pixel_descriptors_all.csv`
- `region_descriptors_all.csv`
- `manifest.json`
- `run_report.md`
- per-prototype maps and raster arrays (`segment_map`, `gradient`, `boundary`)
