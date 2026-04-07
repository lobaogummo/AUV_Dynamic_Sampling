# Reconstrucao forense do pipeline real do repositorio

## Escopo e metodo usado
- Objetivo: reconstruir o workflow realmente executado, sem inventar etapas nem ficheiros.
- Metodo: leitura de scripts, manifests, relatorios e CSVs ja existentes, priorizando outputs historicos em `results/`.
- Politica de execucao: nao foram feitos reruns pesados de clustering; apenas leitura de artefactos e geracao desta pasta `results/pipeline_visual/`.

## Pipeline principal recomendado (estado atual)
Sequencia principal (ramo oficial):

1. `STG01 -> STG02`: build do dataset de superficie + normalizacao/mask comum.
2. `STG05/STG06/STG07/STG08`: exploracao de hiperparametros e SD para consolidar configuracao.
3. `STG09 -> STG10 -> STG11`: consolidacao working + refinamento local + dicionario canonico.
4. `STG13`: pipeline oficial congelado em `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328`.
5. `STG14 -> STG15 -> STG16 -> STG17`: compact model, export CV, downstream image-only e caracterizacao pixel-wise semantica.
6. `STG18`: auditorias/validacoes complementares.

Configuracao oficial congelada (evidencia: `configs/thesis_official_state.json`):
- patch size: `72x40`
- dictionary size: `4`
- StandardScaler: `ON`
- separation distance fracao oficial: `0.30`
- classes globais alvo: `5`
- refinamento local: `class_02` com `k=2`
- seed de referencia para artefactos oficiais downstream: `11`

## Lista ordenada de etapas (com estado)
| stage_id | etapa | estado | output ancora | decisao suportada |
| --- | --- | --- | --- | --- |
| STG01_BUILD_SURFACE_DATASET | Build dataset de superficie (300 dias) | working | `results/plots/X_surface_300.npy` | fixar base numerica comum |
| STG02_NORMALIZE_COMMON_MASK | Normalizacao global + mascara comum | working | `results/plots/X_surface_300_norm.npy` | padronizar entrada para clustering |
| STG03_EXPORT_NORMALIZED_PNGS | Export PNGs normalizados | working | `results/plots/pngs_normalized_surface_300_thesis/index.csv` | suporte visual/reprodutivel |
| STG04_INITIAL_VISUAL_EXPLORATION | Exploracao visual inicial | exploratory | `results/plots/deterministic_2024_surface_300_thesis/index.csv` | diagnostico inicial do ramo de dados |
| STG05_PATCH_SIZE_SENSITIVITY | Patch-size sensitivity | exploratory | `results/fossum/faithful_initial_patch_size_sensitivity_spread/ranking.csv` | informar escolha de patch |
| STG06_DICTIONARY_SIZE_SENSITIVITY | Dictionary-size sensitivity | exploratory | `results/fossum/faithful_initial_dictionary_size_sensitivity_spread/ranking.csv` | informar escolha de dicionario |
| STG07_SD_PROBE_AND_SCALER_COMPARISON | SD probe + scaler/no-scaler | exploratory | `results/fossum/faithful_initial_sd_autoprobe/.../comparison_summary.json` | suportar scaler ON e SD30 |
| STG08_SD_REFINED_LOCAL_PROBE | Probe refinado de fracoes SD por seed | exploratory | `results/fossum/faithful_initial_sd_refined_local_probe/summary_fraction_profile_20260325.csv` | estabilizar numero de classes alvo |
| STG09_SD30_WORKING_CONFIG_SUMMARY | Consolidacao working SD30 | working | `results/fossum/faithful_initial_sd_working_config/summary_final_sd30_all_seeds_20260325.csv` | fixar base para refinamento local |
| STG10_CLASS02_LOCAL_REFINEMENT_KSWEEP | Refinamento local class_02 (k=2,3) | working | `results/fossum/class02_local_refinement_sd30_20260326/refined_class02_summary.csv` | escolher split local default k=2 |
| STG11_CANONICAL_DICTIONARY_SELECTION | Selecao dicionario canonico | final | `results/fossum/canonical_dictionary/canonical_dictionary_manifest.json` | fixar artefacto reutilizavel oficial |
| STG12_E2E_WORKING_PRE_OFFICIAL | Runs E2E pre-oficial | working | `results/fossum/final_working_pipeline/e2e_fixed_seed11_20260328/pipeline_manifest.json` | consolidar runner antes da versao oficial |
| STG13_OFFICIAL_FROZEN_PIPELINE | Pipeline oficial congelado | final | `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/pipeline_manifest.json` | estabelecer ramo principal da tese |
| STG14_BUILD_COMPACT_MODEL | Build compact model final | final | `results/fossum/compact_model/v0_base/compact_model_manifest.json` | empacotar prototipos globais oficiais |
| STG15_EXPORT_CV_PROTOTYPES | Export prototipos para CV | final | `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/computer_vision_exports_seed11/manifest_cv_exports.json` | bridge para pipeline CV |
| STG16_CV_IMAGE_ONLY_DOWNSTREAM | Downstream CV image-only | final | `results/computer_vision_seed11/official_fixed_dictionary_seed11/official_image_only_default/manifest.json` | classificar padroes visuais de prototipos |
| STG17_PIXELWISE_CHARACTERIZATION_V2 | Caracterizacao pixel-wise semantica | final | `results/prototype_characterization_seed11/official_fixed_dictionary_seed11/official_pixelwise_v2_semantic/manifest.json` | descritores finais para analise/tese |
| STG18_VALIDATION_AND_AUDITS | Auditorias e validacoes complementares | diagnostic | `results/validation_descriptor_audit_v2_20260403_215918/AUDIT_REPORT.md` | checar robustez sem alterar pipeline core |

## Etapas principais vs auxiliares

Etapas principais (mostrar no diagrama principal):
- `STG01`, `STG02`, `STG09`, `STG10`, `STG11`, `STG13`, `STG14`, `STG15`, `STG16`, `STG17`

Etapas auxiliares exploratorias (mostrar como ramos secundarios):
- `STG04`, `STG05`, `STG06`, `STG07`, `STG08`, `STG12`

Etapas diagnosticas (mostrar como camada de validacao):
- `STG18`

## Decisoes reconstruidas por fase (evidencia direta)

1. Escolha de configuracao global congelada:
- Evidencia: `configs/thesis_official_state.json` e `THESIS_OFFICIAL_PIPELINE.md`.
- Decisao: `patch72x40`, `dict4`, `scaler ON`, `SD=0.30`, `target=5 classes`.

2. Escolha do refinamento local:
- Evidencia: `results/fossum/class02_local_refinement_sd30_20260326/refined_class02_summary.csv`.
- Decisao: manter refinamento local em `class_02` com `k=2` como default oficial.

3. Escolha de dicionario fixo:
- Evidencia: `results/fossum/canonical_dictionary_seed_sweep/canonical_full_20260328/CANONICAL_DICTIONARY_REPORT.md` + `results/fossum/canonical_dictionary/canonical_dictionary_manifest.json`.
- Decisao: seed canonica `11`, dicionario fixo para runs oficiais.

4. Escolha do ramo final para governanca:
- Evidencia: `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/pipeline_manifest.json`.
- Decisao: tratar esta arvore como ramo oficial principal (em vez das variantes pre-oficiais).

5. Cadeia downstream final:
- Evidencia:
  - export CV: `.../computer_vision_exports_seed11/manifest_cv_exports.json`
  - CV image-only: `results/computer_vision_seed11/official_fixed_dictionary_seed11/official_image_only_default/manifest.json`
  - caracterizacao v2: `results/prototype_characterization_seed11/official_fixed_dictionary_seed11/official_pixelwise_v2_semantic/manifest.json`
- Decisao: pipeline final nao termina no clustering; inclui etapa CV e caracterizacao semantica.

## O que e superseded / legado
- Scripts em `scripts/Old_Code/` continuam relevantes para rastreio historico, mas nao sao o conjunto oficial atual.
- Arvore `results/final_working_pipeline/final_working_20260328` e tratada como pre-oficial face a `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328`.
- `docs/FOSSUM_READY_STATE.md` esta desatualizado em pontos criticos (mask/tensor), devendo ser lido apenas como contexto historico.

## Recomendacao objetiva para apresentacao
- Usar `pipeline_overview.mmd` como figura principal (alto nivel, legivel em slide).
- Usar `pipeline_detailed.mmd` como figura tecnica de backup (anexo/appendix).
- Ancorar narracao nos artefactos oficiais:
  - `configs/thesis_official_state.json`
  - `results/fossum/final_working_pipeline/official_fixed_dictionary_20260328/pipeline_manifest.json`
  - `results/fossum/compact_model/v0_base/compact_model_manifest.json`
  - `results/computer_vision_seed11/official_fixed_dictionary_seed11/official_image_only_default/manifest.json`
  - `results/prototype_characterization_seed11/official_fixed_dictionary_seed11/official_pixelwise_v2_semantic/manifest.json`
