# FOSSUM_BASELINE_VS_FAITHFUL_INITIAL

## Baseline historico (congelado)
- `scripts/02a_patch_size_sensitivity_fossum_rerun_corrected.py`
- `scripts/03_dictionary_size_sensitivity_fossum.py`

Esses scripts permanecem executaveis e reproduziveis como baseline da variante antiga.

## Faithful initial (em construcao)
- `scripts/fossum_faithful_initial_utils.py`
- `scripts/fossum_faithful_initial_smoke.py`
- `scripts/02b_patch_size_sensitivity_fossum_faithful_initial.py`
- `scripts/03a_dictionary_size_sensitivity_fossum_faithful_initial.py`

## Diferencas metodologicas da faithful initial
- patch vector com mascara valida concatenada: `[patch_temp_filled, patch_valid_mask]`
- treino do dicionario sem embaralhar ordem de imagens ou patches
- `MiniBatchDictionaryLearning` com `shuffle=False`
- variabilidade entre runs vinda apenas do `random_state=seed` do dicionario
- feature por imagem baseada no sparse code completo por patch (flatten em ordem deterministica)
- sem agregacao default `mean(abs(codes)) + std(abs(codes))`

## Fora de escopo nesta fase
- separation distance / corte de dendrograma
- secondary classification
- sweeps finais paper-aligned
