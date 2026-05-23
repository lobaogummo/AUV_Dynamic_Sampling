# writing_auxiliar figures fix report

## Scope

Only commented `\includegraphics` commands in `overleaf/Dissertation_Lobão_extracted/writing_auxiliar.tex` were treated. No dissertation prose, captions, labels, citations, equations, tables, or chapter structure were edited.

## Direct answers

1. Quantos `\includegraphics` comentados foram encontrados em `writing_auxiliar.tex`?
   9.

2. Quantos foram descomentados?
   4.

3. Quantas imagens foram encontradas no projeto?
   4 images were matched safely in existing project result folders and copied to `overleaf/Dissertation_Lobão_extracted/figures/results/`.

4. Quantas imagens foram extraídas do `.docx`?
   1 image was available/extracted under `overleaf/Dissertation_Lobão_extracted/figures/writing_auxiliar/docx_image_01.png`, but it did not match any of the 9 referenced figure filenames.

5. Quantas imagens continuam em falta?
   5.

6. Que paths foram corrigidos?
   No `\includegraphics` paths were rewritten. Instead, matching project images were copied to the paths already referenced by `writing_auxiliar.tex`:
   - `figures/results/grid_validation_roi_overlay.png`
   - `figures/results/regime_prototypes.png`
   - `figures/results/regime_variability_maps.png`
   - `figures/results/baseline_route_selected_day.png`

7. Algum texto foi alterado?
   No. Only four leading `%` comment markers before `\includegraphics` commands were removed.

8. Alguma caption foi alterada?
   No.

9. Algum label foi alterado?
   No.

10. O PDF compilou depois da correção?
    Yes. `meec_thesis.pdf` compiled successfully after running `biber` and `pdflatex`.

11. As imagens do `writing_auxiliar` aparecem agora no PDF?
    The 4 restored images appear in the PDF. The LaTeX log confirms inclusion of:
    - `figures/results/grid_validation_roi_overlay.png`
    - `figures/results/regime_prototypes.png`
    - `figures/results/regime_variability_maps.png`
    - `figures/results/baseline_route_selected_day.png`

## Images restored

| Referenced path | Source used |
| --- | --- |
| `figures/results/grid_validation_roi_overlay.png` | `results/Investigation_transition_to_planner/300/planner_operational_roi_fullgrid.png` |
| `figures/results/regime_prototypes.png` | `results/fossum_roi_x490_step01_old_config_baseline_20260509_235101/step01_old_config_class_prototypes_panel.png` |
| `figures/results/regime_variability_maps.png` | `results/fossum_roi_x490_step01_old_config_baseline_20260509_235101/step01_old_config_class_std_maps_panel.png` |
| `figures/results/baseline_route_selected_day.png` | `results/planner_baseline_scenario_c4_methodical_20260418_162500/outputs/final_rerun_surface_day1_20260419_144145/planner_run/planner_plot_surface_day1_final.png` |

## Images still missing

These `\includegraphics` commands remain commented because no safe matching existing image was identified:

- `figures/results/descriptor_maps_selected_day.png`
- `figures/results/baseline_vs_enriched_routes.png`
- `figures/results/sensitivity_heatmaps.png`
- `figures/results/single_auv_comparison.png`
- `figures/results/multi_auv_comparison.png`

## Compilation notes

Compilation succeeded and produced `overleaf/Dissertation_Lobão_extracted/meec_thesis.pdf`.

Remaining warnings were not introduced by this figure relinking step and were left unchanged:

- duplicate label: `sec:objectives`;
- missing bibliography entries: `toth2014vehicle`, `vidal2013hybrid`, `eidsvik2015value`;
- some undefined references and overfull/underfull boxes.

## Preservation confirmation

The only changes to `writing_auxiliar.tex` were uncommenting four existing `\includegraphics` lines. Captions, labels, citations, equations, tables, figure environments, and prose text were preserved.

The content from `writing_auxiliar.docx` was not rewritten or modified.

The figures referenced in writing_auxiliar.tex were restored by uncommenting and relinking includegraphics commands without modifying the original text.
