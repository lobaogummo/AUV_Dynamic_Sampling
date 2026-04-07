# Gaps e incertezas (forensic)

## 1) Geracao exata dos arrays oficiais em `results/plots` - incerto
- Facto: o estado oficial usa `results/plots/X_surface_300.npy`, `results/plots/X_surface_300_norm.npy` e `results/plots/mask_common.npy`.
- Facto: o script que explicita esta geracao esta em `scripts/Old_Code/01_build_fossum_surface_dataset.py` e por default escreve em `results/fossum/`.
- Incerteza: nao foi encontrado no diretorio `scripts/` um script atual equivalente que explique diretamente a materializacao final em `results/plots`.
- Validacao manual sugerida: confirmar no historico Git qual comando/run moveu ou regenerou estes ficheiros em `results/plots`.

## 2) Export de PNGs normalizados: script legado vs output oficial - incerto
- Facto: existem PNGs oficiais em `results/plots/pngs_normalized_surface_300_thesis/`.
- Facto: `scripts/Old_Code/01b_export_normalized_surface_pngs.py` aponta por default para `results/fossum/pngs_normalized_surface_300`.
- Incerteza: nao foi encontrado um wrapper atual (fora de `Old_Code`) que fixe explicitamente o output `..._thesis`.
- Validacao manual sugerida: localizar comando de execucao com `--out-dir results/plots/pngs_normalized_surface_300_thesis`.

## 3) Orquestracao da etapa `faithful_initial_sd_refined_local_probe` - incerto
- Facto: existem outputs completos em `results/fossum/faithful_initial_sd_refined_local_probe/`.
- Facto: as metricas batem com execucoes repetidas do `scripts/04a_separation_distance_probe_fossum_faithful_initial.py`.
- Incerteza: nao foi encontrado um script dedicado de orquestracao batch dentro de `scripts/`.
- Validacao manual sugerida: verificar shell history/notebooks externos usados no dia da execucao.

## 4) Duplicacao de arvores de resultado final - parcialmente incerto
- Facto: coexistem `results/final_working_pipeline/final_working_20260328` e `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328`.
- Facto: o estado oficial centralizado (2026-04-03) aponta para a arvore sob `results/fossum/.../official_fixed_dictionary_20260328`.
- Incerteza: criterio operacional exato usado para manter ambas as arvores no repositorio nao esta documentado num unico ficheiro.

## 5) Etapas de validacao complementar sem script rastreado - incerto
- Facto: existem relatorios e manifestos em:
  - `results/validation_descriptor_audit_v2_20260403_215918`
  - `results/validation_visual_data_branches_20260405_193102`
  - `results/validation_hres_surface_comparison_20260405_130636`
- Incerteza: nao foram encontrados scripts correspondentes dentro de `scripts/` por pesquisa textual.
- Validacao manual sugerida: identificar scripts externos ou runs ad-hoc que geraram estes outputs.

## 6) Paths absolutos antigos em manifests - conhecido, nao bloqueante
- Facto: varios JSON/MD guardam paths absolutos de outro ambiente (`C:\Users\E713181\OneDrive - EDP\...`).
- Impacto: reduz portabilidade e dificulta rastreio automatico puro por path no ambiente atual.
- Mitigacao usada aqui: priorizacao de paths relativos existentes no repo para reconstruir dependencias.

## 7) Documento historico desatualizado - conhecido
- Facto: `docs/FOSSUM_READY_STATE.md` declara ausencia de mask/tensor salvos.
- Facto atual: esses artefactos existem (`results/plots/X_surface_300.npy`, `results/plots/X_surface_300_norm.npy`, `results/plots/mask_common.npy`).
- Conclusao: usar `THESIS_OFFICIAL_PIPELINE.md` + `configs/thesis_official_state.json` como verdade atual.
