# tempRes Georeference Forensic Audit

Generated at UTC: `2026-04-22T19:16:36.632104+00:00`

## 1. Problema
Recuperar ou provar a georreferenciacao da grelha `tempIBHRes2024_1.gslib`, ou estabelecer transformacoes justificadas para a grelha oficial do planner.

## 2. Evidencia encontrada no repositorio
- Registos de evidencia indexados: **224**
- Inventarios de artefactos analisados: **8**
- Evidencia-chave observada: `tempIBHRes` nativo indexado (`x,y,z,temp`), mapping de display por bbox HRes, e registo quantitativo tempRes->HRes por busca controlada.
- Trechos-chave:
  - `docs/THESIS_FIGURE_CONVENTIONS.md:13` -> - Metodo aplicado: `linear_resample_from_hres_bbox`
  - `investigation/tempibhres_geoaxes_audit_20260417_171342/AUDIT_TEMPIBHRES_GEOAXES.md:9` -> - Prova forte: `load_physical_lon_lat(...)` reconstrui `lon/lat` por `np.linspace` a partir de `results/netcdf_files_summary.csv`, usando a linha `data/HResNew/CMEMSnaza_20241029_HResNew.nc` e metodo `linear_resample_from_hres_bbox`.
  - `investigation/tempibhres_geoaxes_audit_20260417_171342/AUDIT_TEMPIBHRES_GEOAXES.md:10` -> - O arquivo `tempIBHRes2024_1.gslib` observado tem colunas `x,y,z,temp` com valores indexados (ex.: `x=1`, `y=1`, `z=1`), sem lat/lon em graus no cabecalho.
  - `investigation/tempibhres_geoaxes_audit_20260417_171342/AUDIT_TEMPIBHRES_GEOAXES.md:19` -> - parse header x,y,z,temp
  - `investigation/tempibhres_geoaxes_audit_20260417_171342/AUDIT_TEMPIBHRES_GEOAXES.md:64` -> - registrar metodo `linear_resample_from_hres_bbox` (`63`).
  - `investigation/tempibhres_geoaxes_audit_20260417_171342/AUDIT_TEMPIBHRES_GEOAXES.md:80` -> | `results/plots/deterministic_2024_surface_300_thesis/*.png` | display mapping | `color_scale.json` metodo `linear_resample_from_hres_bbox`; script usa `extent` com lon/lat | lat/lon aplicados externamente via bbox HRes para visualizacao comparativa |
  - `investigation/tempibhres_geoaxes_audit_20260417_171342/TRACE_EVIDENCE_COORDS.csv:9` -> E08,FILIPA_DADOS/scripts/Old_Code/physical_coords.py,63,Metadata method is linear_resample_from_hres_bbox,Display mapping is explicit in code,high
  - `investigation/tempibhres_hres_registration_controlled_v4/figures_inferred_axes_km/deterministic_tempibhres/index.csv:2` -> 1,investigation/tempibhres_hres_registration_controlled_v4/figures_inferred_axes_km/deterministic_tempibhres/TEMP_surface_2024_z001.png,458.70812265264726,487.870002888995,4369.93390206069,4389.257784651033,x,y,inferred by registration to physically anchore...
  - `investigation/tempibhres_hres_registration_controlled_v4/figures_inferred_axes_km/deterministic_tempibhres/index.csv:3` -> 2,investigation/tempibhres_hres_registration_controlled_v4/figures_inferred_axes_km/deterministic_tempibhres/TEMP_surface_2024_z002.png,458.70812265264726,487.870002888995,4369.93390206069,4389.257784651033,x,y,inferred by registration to physically anchore...
  - `investigation/tempibhres_hres_registration_controlled_v4/figures_inferred_axes_km/deterministic_tempibhres/index.csv:4` -> 3,investigation/tempibhres_hres_registration_controlled_v4/figures_inferred_axes_km/deterministic_tempibhres/TEMP_surface_2024_z003.png,458.70812265264726,487.870002888995,4369.93390206069,4389.257784651033,x,y,inferred by registration to physically anchore...

## 3. Artefactos relevantes localizados
- `investigation/tempibhres_geoaxes_audit_20260417_171342`: 3 files; top types -> .csv:2; .md:1
- `investigation/tempibhres_hres_registration_controlled_v4`: 623 files; top types -> .png:606; .csv:14; .json:1; .md:1; .npz:1
- `results/plots/tempibhres_indexed_axes_fix_20260417_185500`: 0 files; top types -> none
- `results/plots/tempibhres_relative_km_display_assumed_20260418_0001`: 0 files; top types -> none
- `results/plots/tempibhres_relative_km_display_assumed_user_style_test_v3`: 6 files; top types -> .csv:2; .png:2; .json:1; .md:1
- `results/plots/tempibhres_relative_km_display_assumed_filipa_xy_km_cropped_v1`: 604 files; top types -> .png:600; .csv:2; .json:1; .md:1
- `results/plots/deterministic_2024_surface_300_thesis_indexed_axes`: 302 files; top types -> .png:300; .csv:1; .json:1
- `results/plots/pngs_normalized_surface_300_thesis_indexed_axes`: 302 files; top types -> .png:300; .csv:1; .json:1

## 4. Hipoteses de georreferencia / transformacao
- `CAND_A_DISPLAY_BBOX_HRES`: method=linear_index_to_hres_bbox; frame=lon_lat; lon[-9.555555,-8.916667] lat[39.388889,39.861111]; proof_status=display_mapping_only.
- `CAND_B_REGISTRATION_TO_HRES_SUBAREA`: method=registration_best_axis_aligned_crop_resample; frame=lon_lat; lon[-9.480707,-9.141214] lat[39.478584,39.652701]; proof_status=registration_derived_not_native.
- `CAND_C1_RELATIVE_KM_DISPLAY`: method=relative_km_display_assumed; frame=local_km; x[462.0,516.8543862149527] y[4376.0,4428.429515261849]; proof_status=display_axes_local_frame_only.
- `CAND_C2_RELATIVE_KM_DISPLAY`: method=relative_km_display_assumed; frame=local_km; x[462.0,516.8543862149527] y[4376.0,4428.429515261849]; proof_status=display_axes_local_frame_only.

## 5. Testes de alinhamento feitos
- Planner full bbox: lon[-9.555555,-8.916667] lat[39.388889,39.861111]
- Planner ROI bbox: lon[-9.432590,-9.036959] lat[39.510242,39.750310]
- `CAND_A_DISPLAY_BBOX_HRES`: inside_full=True; intersects_roi=True; roi_iou=0.3148; roi_coverage=1.0000; res_ratio_x=2.1531531531531534; res_ratio_y=2.8412698412698414
- `CAND_B_REGISTRATION_TO_HRES_SUBAREA`: inside_full=True; intersects_roi=True; roi_iou=0.3687; roi_coverage=0.4370; res_ratio_x=1.145120865441822; res_ratio_y=1.047619213192948
- `CAND_C1_RELATIVE_KM_DISPLAY`: frame local_km; nao comparavel diretamente em lon/lat sem passo adicional de CRS.
- `CAND_C2_RELATIVE_KM_DISPLAY`: frame local_km; nao comparavel diretamente em lon/lat sem passo adicional de CRS.
- Overlays gerados: `results/tempres_georef_candidate_overlay_1.png` e `results/tempres_georef_candidate_overlay_2.png`

## 6. Grau de confianca
- Georreferencia nativa tempRes provada: **nao**.
- Mapeamento de display (bbox HRes -> tempRes): **sim, fortemente documentado** (codigo, manifests e relatorios).
- Transformacao por registo controlado: **forte para plausibilidade espacial**, mas explicitamente inferida (nao metadata nativa do GSLIB).
- Coerencia espacial com planner: existe para hipoteses candidatas, mas a prova de origem geodesica nativa da tempRes continua ausente.

## 7. Conclusao final
`TRANSFORMATION PLAUSIBLE BUT NOT PROVEN`

A tempRes pode ser alinhada de forma plausivel com a grelha do planner, mas nao pode ser alinhada de forma auditavelmente provada com a evidencia atual.

## 8. Recomendacao para o passo seguinte
Adotar oficialmente a grelha do planner interface como referencia operacional, e transferir regimes/descriptors apenas com uma transformacao explicitamente etiquetada como inferida (nao como georreferencia nativa recuperada), preservando rastreabilidade dos artefactos usados.
