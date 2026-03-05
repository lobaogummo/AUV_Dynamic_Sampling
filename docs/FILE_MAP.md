# FILE MAP - FRESNEL / Nazare (C4 e D4)

## Pipeline (alto nivel)

```text
CMEMS original (20241029/20241030) -> HResNew (interpolado)
                                    -> Priori_Nazare_* (modelo a priori)
AUVdata (observacoes) -------------/ 
                                    -> Nazare_* (apos assimilacao)
                                    -> sim_*.out (realizacoes)
                                    -> GSLIB derivados (Median, StDev, IQD, scene_*)
                                    -> NetCDF predModel/AUVpredModel
```

## Pastas e papeis

| Pasta | Papel esperado |
|---|---|
| `data/20241029`, `data/20241030` | CMEMS original (grade maior, produto de download). |
| `data/HResNew` | CMEMS interpolado para a grade de simulacao local. |
| `data/TEST_C4`, `data/TEST_D4` | Estrutura dos testes, com pastas `Priori_Nazare_*` e `Nazare_*`. |
| `Nazare_*` | Resultado pos-assimilacao com observacoes AUV. |
| `Priori_Nazare_*` | Estado a priori / fundo antes de assimilacao. |
| `sim_*.out` | Realizacoes individuais (ASCII estilo GSLIB simplificado). |
| `*.gslib` | Grades e produtos derivados (temp, median, std, bathy, mask, scene). |
| `*_predModel_*.nc` | Versao NetCDF do modelo de previsao/background. |
| `*_AUVpredModel_*.nc` | Versao NetCDF apos assimilacao com AUV. |

## Convencoes de nomes

- `Nazare_DD-MM-YYYY_k`: caso/realizacao pos-assimilacao `k`.
- `Priori_Nazare_DD-MM-YYYY_k`: caso/realizacao a priori `k`.
- `sim_n.out`: realizacao `n` da simulacao.
- `DD-MM-YYYY_predModel_k.nc`: NetCDF de previsao/base.
- `DD-MM-YYYY_AUVpredModel_k.nc`: NetCDF atualizado por assimilacao AUV.

## Tabela rapida por pasta (contagens)

| Pasta | n_files | total_bytes |
|---|---:|---:|
| `data/2024` | 20 | 1596990313 |
| `data/20241029` | 5 | 89683810 |
| `data/AUVdata` | 4 | 28496324 |
| `data/HResNew` | 3 | 247903086 |
| `data/20241030` | 3 | 53810286 |
| `data` | 1 | 353 |

## Glossario

- **Variograma**: Funcao que descreve a continuidade espacial em funcao da distancia.
- **Sill**: Patamar do variograma associado a variancia total.
- **Range**: Distancia a partir da qual a correlacao espacial e fraca.
- **Nugget**: Componente de variancia a distancia zero (ruido/microescala).
- **Realizacao**: Uma simulacao possivel do campo aleatorio condicionado.
- **Ensemble**: Conjunto de realizacoes para quantificar incerteza.
- **Assimilacao**: Atualizacao do estado do modelo com observacoes.
- **A priori**: Estimativa antes de incorporar observacoes AUV.
- **A posteriori**: Estimativa apos incorporar observacoes AUV.
- **Kriging**: Estimador linear que minimiza variancia do erro.
- **Simulacao sequencial**: Geracao de realizacoes preservando estatisticas locais.
- **Grade**: Malha espacial onde variaveis sao representadas.
- **Bounding box**: Extremos min/max de latitude e longitude.
- **Resolucao**: Espacamento entre pontos de grade.
- **Pointwise std**: Desvio padrao por celula da grade.
- **Mediana**: Estatistica robusta do ensemble por celula.
- **Bathymetry/BATHY**: Profundidade do fundo oceânico.
- **TEMP**: Temperatura da agua do mar.
- **PSAL**: Salinidade pratica.
- **DEPT/Depth**: Nivel de profundidade vertical.
- **TIME**: Dimensao temporal do produto/modelo.
- **CMEMS**: Servico Copernicus de dados marinhos.
- **HRes**: Grade de maior resolucao para simulacao local.
- **Mask**: Indicador de celulas ativas/inativas.
- **IQD**: Produto derivado usado no pos-processamento geoestatistico.
- **scene_*.gslib**: Cenas/quadros usados para visualizacao ou etapas internas.
- **sim_*.out**: Realizacoes individuais da simulacao.
- **TEMPpred**: Campo de temperatura previsto no NetCDF de simulacao.
- **STD**: Incerteza (desvio padrao) por celula.
- **AUV track**: Trajetoria georreferenciada do veiculo.
