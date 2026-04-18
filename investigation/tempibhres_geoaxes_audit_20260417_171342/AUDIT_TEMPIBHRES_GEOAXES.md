# Auditoria de eixos geograficos - tempIBHRes2024_*

Data: 2026-04-17
Escopo: rastrear como as imagens derivadas de `tempIBHRes2024_*` receberam eixos/coordenadas geograficas.
Restricoes respeitadas: sem alterar codigo, sem regenerar pipeline completa, sem sobrescrever outputs oficiais.

## 1) Resumo executivo
- Conclusao principal: as imagens thesis de `tempIBHRes2024_*` em lat/lon usam **display mapping** para a bbox HRes local, nao uma georreferenciacao nativa lida do proprio `.gslib`.
- Prova forte: `load_physical_lon_lat(...)` reconstrui `lon/lat` por `np.linspace` a partir de `results/netcdf_files_summary.csv`, usando a linha `data/HResNew/CMEMSnaza_20241029_HResNew.nc` e metodo `linear_resample_from_hres_bbox`.
- O arquivo `tempIBHRes2024_1.gslib` observado tem colunas `x,y,z,temp` com valores indexados (ex.: `x=1`, `y=1`, `z=1`), sem lat/lon em graus no cabecalho.
- Para paineis comparativos: existe mistura explicita de sistemas de coordenadas (`latlon`, `metric`, `index`) e, em pelo menos um pacote de validacao, os scripts geradores nao estao rastreados no repo.

## 2) Cadeia de geracao (tempIBHRes -> arrays -> bbox/eixos -> PNG)

### Diagrama textual
```text
data/2024/tempIBHRes2024_1.gslib
  -> scripts/Old_Code/export_surface_2024_300_images.py
     - parse header x,y,z,temp
     - second_pass_build_grids() -> grids[300,64,112]
     - load_physical_lon_lat(ROOT,112,64)
         -> scripts/Old_Code/physical_coords.py
         -> read results/netcdf_files_summary.csv
         -> pick HRes row data/HResNew/CMEMSnaza_20241029_HResNew.nc
         -> lon/lat = linspace(HRes bbox -> target 112x64)
     - imshow(..., extent=[lon_min,lon_max,lat_min,lat_max])
     - axis labels: Longitude/Latitude
     - write color_scale.json + index.csv + PNGs

  -> scripts/Old_Code/01_build_fossum_surface_dataset.py
     - reusa second_pass_build_grids()
     - gera X_surface_300.npy, X_surface_300_norm.npy, mask_common.npy

  -> scripts/Old_Code/01b_export_normalized_surface_pngs.py
     - load_physical_lon_lat(...)
     - imshow(..., extent=lat/lon)
     - write color_scale_norm.json + index.csv + PNGs
```

### Evidencia chave da cadeia
- Fonte e shape base `300x64x112`: `scripts/Old_Code/01_build_fossum_surface_dataset.py:35-39`, `results/fossum/dataset_summary.json:2-7`.
- Export deterministico usa extent geografico: `scripts/Old_Code/export_surface_2024_300_images.py:206-219`.
- Eixos lat/lon sao carregados por funcao externa: `scripts/Old_Code/export_surface_2024_300_images.py:311`.
- Mapping linear para bbox HRes: `scripts/Old_Code/physical_coords.py:35-41`, `59-64`.
- Metadado persistido confirma metodo: `results/plots/deterministic_2024_surface_300_thesis/color_scale.json:9-20`, `results/plots/pngs_normalized_surface_300_thesis/color_scale_norm.json:6-17`.

## 3) Origem real das coordenadas usadas nas imagens

### 3.1 O `.gslib` tem coordenadas fisicas proprias?
Facto observado:
- Cabecalho de `data/2024/tempIBHRes2024_1.gslib` com 4 colunas: `x`, `y`, `z`, `temp`.
- Primeiras linhas com indices `1.000000 1.000000 1.000000 ...`.
- Referencias: `data/2024/tempIBHRes2024_1.gslib` (head), `scripts/Old_Code/export_surface_2024_300_images.py:88-95` e validacao de extents `x=1..112, y=1..64` em `149-152`.

Conclusao: nao ha prova de lat/lon nativo no `tempIBHRes2024_1.gslib` usado no fluxo thesis.

### 3.2 Onde o codigo atribui bbox/lat/lon?
- Chamada: `scripts/Old_Code/export_surface_2024_300_images.py:311`.
- Implementacao: `scripts/Old_Code/physical_coords.py:35-75`.
- Regra:
  - ler `results/netcdf_files_summary.csv` (`physical_coords.py:42`)
  - escolher HRes preferido `data/HResNew/CMEMSnaza_20241029_HResNew.nc` (`13`, `24-30`)
  - reconstruir `lon/lat` por `np.linspace` para `nx,ny` alvo (`59-60`)
  - registrar metodo `linear_resample_from_hres_bbox` (`63`).

### 3.3 A bbox vem de onde?
- Da linha HRes em `results/netcdf_files_summary.csv` (campos `lon_min/lon_max/lat_min/lat_max`).
- Nao e derivada diretamente do conteudo do `.gslib` de `tempIBHRes`.
- Documentacao explicita: `docs/THESIS_FIGURE_CONVENTIONS.md:10-15`.

### 3.4 Existe assuncao explicita de mesmo dominio fisico tempIBHRes==HRes?
Sim, no nivel de visualizacao.
- O codigo aplica bbox HRes ao grid `112x64` do tempIBHRes (`physical_coords.py:40`, `59-60`).
- Os metadados de output registram isto como metodo oficial (`color_scale*.json`).

## 4) Classificacao dos outputs (georef forte vs display mapping vs ambiguo)

| Output | Categoria | Evidencia | Leitura tecnica |
|---|---|---|---|
| `results/plots/deterministic_2024_surface_300_thesis/*.png` | display mapping | `color_scale.json` metodo `linear_resample_from_hres_bbox`; script usa `extent` com lon/lat | lat/lon aplicados externamente via bbox HRes para visualizacao comparativa |
| `results/plots/pngs_normalized_surface_300_thesis/*.png` | display mapping | `color_scale_norm.json` com mesmo metodo; script `01b...` usa `load_physical_lon_lat` | idem acima |
| `results/validation_visual_data_branches.../images/thermal/tempIBHRes2024_1/*.png` | display mapping | `image_manifest.csv` `coord_type=latlon` + bbox HRes (linhas 2,12,22) | tempIBHRes mostrado em lat/lon por mapping |
| `results/validation_visual_data_branches.../images/thermal/TestC4_scene_real/*.png` | georef forte (metrico) | `coord_type=metric` (linhas 4,14,24) e eixos X/Y metricos na figura | usa coordenadas metricas do produto scene |
| `results/validation_visual_data_branches.../images/thermal/Priori_Median*.png` e `.../uncertainty/Priori_StDev*.png` | nao georef (index) | `coord_type=index` (linhas 6,10,16,20,26,30) | eixo em indice de grelha |
| `results/validation_hres_surface_comparison.../images/tempIBHRes2024_1/*.png` | display mapping | imagem com eixos lon/lat + `grid_comparison.csv` nota "mapped linearly to HRes bbox" | mapping para comparacao |
| `results/validation_hres_surface_comparison.../images/hres_test_c4_scene_real/*.png` | provavel display mapping para lat/lon | `manifest.json` nota: extents lat/lon para HRes vindos de `netcdf_files_summary.csv` | sem script gerador no repo, mas evidencia aponta remapeamento para lon/lat |
| `results/validation_* /panels/*.png` | ambiguo (componente de display) | scripts geradores nao encontrados (`pipeline_stages.csv` STG18; `gaps_and_uncertainties.md`) | painel agrega fontes com sistemas diferentes; rastreio de subplot incompleto |

## 5) Auditoria especifica dos paineis comparativos

### 5.1 Como os eixos foram definidos nos subplots?
- No pacote `validation_visual_data_branches`, os outputs base por dataset trazem tipos distintos (`latlon`, `metric`, `index`) em `tables/image_manifest.csv`.
- O painel `panel_thermal_step_013.png` (inspecao visual) nao exibe eixos por subplot; atua como comparador visual de padrao.
- O painel `panel_uncertainty_step_013.png` idem, sem eixos explicitos por subplot.

### 5.2 tempIBHRes foi desenhado com bbox HRes por conveniencia?
- Sim, para os fluxos em lat/lon observados.
- Evidencia direta no ramo thesis e no `validation_hres_surface_comparison`.

### 5.3 Isso esta documentado no codigo?
- Documentado no codigo e metadados dos exports thesis (`physical_coords.py`, `color_scale*.json`, `THESIS_FIGURE_CONVENTIONS.md`).
- Para STG18 (paineis de validacao), os scripts geradores nao foram localizados; existe apenas documentacao de resultado (manifest/report/tables).

### 5.4 Erro metodologico, simplificacao consciente, ou escolha aceitavel?
- Avaliacao tecnica: **simplificacao consciente de visualizacao comparativa**, aceitavel se declarada explicitamente.
- Nao deve ser descrita como prova de georreferenciacao independente do `tempIBHRes` sem validacao adicional da fonte original.

## 6) O que pode e nao pode ser afirmado (A-E)

### A) Posso dizer que as imagens tempIBHRes tem georreferenciacao fisica propria e independente?
- Resposta: **nao com base na evidencia atual**.

### B) Devo dizer que foram mostradas na bbox HRes/local por conveniencia?
- Resposta: **sim** (formulacao metodologica segura).

### C) Existe prova forte de que tempIBHRes ocupa exatamente o mesmo dominio fisico do HRes?
- Resposta: **nao**. Existe compatibilidade de representacao, mas nao prova forte de igualdade fisica exata no repositorio auditado.

### D) Legendas/eixos de tempIBHRes sao defensaveis como coordenadas reais?
- Como "coordenadas nativas do dataset": **nao**.
- Como "display mapping comparativo para bbox HRes": **sim**, se declarado.

### E) Qual formulacao mais segura para a tese?
Sugestao de texto (segura):

> "As imagens de `tempIBHRes2024_*` foram representadas em eixos latitude/longitude por mapeamento linear do grid 112x64 para a bbox HRes local (`linear_resample_from_hres_bbox`, via `results/netcdf_files_summary.csv`). Esta representacao foi usada para comparacao visual com produtos HRes/CMEMS e nao constitui, por si so, prova de georreferenciacao nativa independente do `tempIBHRes`."

## 7) Factos observados vs inferencias vs pontos em aberto

### Factos observados (alta confianca)
- `tempIBHRes2024_1.gslib` tem colunas `x,y,z,temp` e indices observaveis.
- Exports thesis usam `load_physical_lon_lat` + `extent` lat/lon.
- `physical_coords.py` usa bbox HRes de `netcdf_files_summary.csv` e metodo `linear_resample_from_hres_bbox`.
- Metadados finais (`color_scale*.json`) guardam essa proveniencia.
- Em `validation_visual_data_branches`, ha mistura explicita de `coord_type` (`latlon`, `metric`, `index`).

### Inferencias provaveis (media/alta confianca)
- A georreferenciacao lat/lon do tempIBHRes nos PNGs e um display mapping para comparabilidade visual.
- `tempIBHRes` e tratado como produto local reduzido/downsampled relativo ao HRes 180x240.

### Pontos em aberto (media/baixa confianca)
- Scripts exatos que geraram STG18 (`validation_visual_data_branches` e `validation_hres_surface_comparison`) nao estao no repo; logo, a logica interna de cada subplot nao e 100% reproduzivel por codigo nesta auditoria.
- Nao foi encontrada prova independente, dentro do repositorio auditado, que estabeleca equivalencia fisica exata tempIBHRes==HRes alem do mapeamento por bbox.

## 8) Recomendacao final
- Corrigir a formulacao metodologica na tese para deixar explicito "display mapping para bbox HRes" quando falar dos eixos lat/lon de `tempIBHRes`.
- Evitar declarar georreferenciacao nativa independente do `tempIBHRes` sem evidencia adicional da fonte original.
- Em figuras comparativas, adicionar nota de legenda do tipo: "tempIBHRes mostrado em lat/lon por mapeamento linear para bbox HRes".
