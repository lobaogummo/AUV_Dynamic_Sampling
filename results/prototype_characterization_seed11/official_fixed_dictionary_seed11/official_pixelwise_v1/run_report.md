# Prototype Characterization Run Report

- Generated UTC: 2026-04-03T12:53:37.287714+00:00
- Seed: 11
- Output dir: `C:\Users\E713181\OneDrive - EDP\Documents\Dados\FILIPA_DADOS\results\prototype_characterization_seed11\official_fixed_dictionary_seed11\official_pixelwise_v1`

## Coverage

- Prototypes processed: 7
- Global prototypes: 5
- Local class_02 prototypes: 2
- Pixel rows exported: 48475
- Region rows exported: 14

## Required Pixel Columns

- Present: True
- Columns: ['scope', 'prototype_key', 'prototype_name', 'row', 'col', 'lat', 'lon', 'temp_mean', 'temp_std', 'region_label', 'region_label_id', 'boundary_score', 'gradient_magnitude', 'gradient_direction', 'distance_to_boundary', 'region_id']

## Prototype Summary

- global | class_01 | valid_pixels=6925 | threshold=-1.251245 (otsu)
- global | class_02 | valid_pixels=6925 | threshold=-0.413019 (otsu)
- global | class_03 | valid_pixels=6925 | threshold=0.466601 (otsu)
- global | class_04 | valid_pixels=6925 | threshold=0.509220 (otsu)
- global | class_05 | valid_pixels=6925 | threshold=1.285742 (otsu)
- local_class02 | k2::subclass_01 | valid_pixels=6925 | threshold=-0.493241 (otsu)
- local_class02 | k2::subclass_02 | valid_pixels=6925 | threshold=0.078717 (otsu)

## Outputs

- `prototype_summary.csv`
- `pixel_descriptors_all.csv`
- `region_descriptors_all.csv`
- `manifest.json`
- `run_report.md`
- per-prototype maps and raster arrays (`segment_map`, `gradient`, `boundary`)
