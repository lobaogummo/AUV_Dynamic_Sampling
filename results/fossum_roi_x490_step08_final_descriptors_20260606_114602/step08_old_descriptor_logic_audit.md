# Step08 Old Descriptor Logic Audit

## Found Core Sources
- `scripts/09_export_cv_prototypes.py`
- `scripts/10_seed11_cv_analysis.py`
- `scripts/cv_seed11_utils.py`
- `scripts/11_prototype_characterization.py`
- `scripts/prototype_characterization_utils.py`
- `notebooks/seed11_computer_vision_colab.ipynb`
- `notebooks/seed11_computer_vision_colab.localrun.ipynb`
- `results/prototype_characterization_seed11/official_fixed_dictionary_seed11/official_pixelwise_v2_semantic/run_report.md`
- `results/prototype_characterization_seed11/official_fixed_dictionary_seed11/official_pixelwise_v2_semantic/pixel_descriptors_all.csv`
- `results/prototype_characterization_seed11/official_fixed_dictionary_seed11/official_pixelwise_v2_semantic/region_descriptors_all.csv`
- `results/validation_descriptor_audit_v2_20260403_215918/AUDIT_REPORT.md`

## Decisions
### CV prototype export
- Where: `scripts/09_export_cv_prototypes.py`
- Decision: **REUSE_WITH_ADAPTATION**
- Logic: exported prototype arrays and alpha-masked clean PNGs for downstream image-only CV.
- Adaptation: Step08 reads Step05 canonical_prototypes directly; clean PNG export remains methodological reference via Step07.

### Image-only CV labels
- Where: `scripts/10_seed11_cv_analysis.py, scripts/cv_seed11_utils.py, notebooks/seed11_computer_vision_colab.ipynb`
- Decision: **REUSE_WITH_ADAPTATION**
- Logic: Otsu on R-B score, region balance/coherence, gradient p90 and image-only regime labels.
- Adaptation: Step08 consumes the latest Step07-CV image-only CSV; it does not rerun CV.

### Pixel-wise prototype descriptors
- Where: `scripts/11_prototype_characterization.py, scripts/prototype_characterization_utils.py`
- Decision: **REUSE_WITH_ADAPTATION**
- Logic: multi_regime classes only: Otsu segmentation + interface boundary + distance-to-boundary + 0.65 gradient/0.35 proximity boundary_score; homogeneous classes: single region with zero boundary.
- Adaptation: Same segmentation/boundary backbone, adapted to 6 ROI x490 canonical classes, X/Y km grids, normalized maps, planner-ready interest map.

### Descriptor validation audit
- Where: `results/validation_descriptor_audit_v2_20260403_215918`
- Decision: **REUSE_AS_IS**
- Logic: boundary score, n_regions and region entropy were most discriminative; proxy top-k favored gradient/boundary-enriched maps.
- Adaptation: Use as evidence for retaining boundary, gradient, segmentation and entropy in final descriptors.

### TEMPpred/tempRes old branches
- Where: `legacy validation branches and tempRes-related outputs`
- Decision: **DO_NOT_REUSE**
- Logic: useful for historical validation only.
- Adaptation: Step08 does not use tempRes, TEMPpred, or STD for descriptor construction.

### Interest map
- Where: `No final reusable interest_map implementation found in scripts.`
- Decision: **REUSE_WITH_ADAPTATION**
- Logic: No stable old production logic found.
- Adaptation: Initial documented map: 0.4 boundary + 0.4 gradient + 0.2 heterogeneity; weights are not optimized.

## Direct Answers

- Logic location: scripts/11_prototype_characterization.py, scripts/prototype_characterization_utils.py, scripts/10_seed11_cv_analysis.py, scripts/cv_seed11_utils.py, notebooks/seed11_computer_vision_colab.ipynb
- Old outputs: pixel_descriptors_all.csv, region_descriptors_all.csv, boundary_score.npy, gradient_magnitude.npy, region_label_id.npy, distance_to_boundary.npy, prototype_summary.csv
- Thresholds: Otsu threshold for multi-regime prototype segmentation, gradient normalization p95, boundary proximity distance p75, no boundary proxy for homogeneous classes
- tempRes dependency: No reusable final descriptor logic requires tempRes; tempRes branches are diagnostic and excluded.

## Reuse Verdict
- REUSE_AS_IS: validation audit evidence that boundary/region entropy are useful.
- REUSE_WITH_ADAPTATION: image-only labels, Otsu segmentation, boundary score and gradient descriptors.
- DO_NOT_REUSE: tempRes/TEMPpred/STD/planner branches for this descriptor-library step.