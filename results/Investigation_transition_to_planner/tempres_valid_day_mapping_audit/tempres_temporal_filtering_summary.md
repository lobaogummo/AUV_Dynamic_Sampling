# tempRes Temporal Filtering Summary

- Output directory: `results/Investigation_transition_to_planner/tempres_valid_day_mapping_audit`
- Source GSLIB: `data/2024/tempIBHRes2024_1.gslib`
- n_original_days_found: `300`
- n_final_days: `300`
- filtering_detected: `False`
- z interpretation: `native_1_based_z_index; calendar_day_mapping_not_metadata_proven; valid_day_filtering_not_supported`
- date_for_z298 calendar hypothesis: `2024-10-24`
- date_for_z299 calendar hypothesis: `2024-10-25`
- date_for_z300 calendar hypothesis: `2024-10-26`

Direct answers:
1. Os 300 dias sao dias corridos ou dias validos apos filtragem? Nao ha prova de filtragem por dias validos; o caminho reprodutivel mostra z=1..300 nativo do GSLIB. A conversao para dias corridos e apenas hipotese porque nao ha time/date no GSLIB.
2. Houve remocao de dias nulos/NaN/invalidos? Nao foi detectada remocao de dias. Foram detectados NaNs espaciais constantes/mascara comum, isto e filtragem de pixels, nao de dias.
3. z=300 corresponde a que data real? Data real nao esta em metadata; na hipotese calendario desde 2024-01-01 corresponde a `2024-10-26`.
4. 29/10/2024 existe no tempRes? `NO` sob hipotese calendario; seria z=303 e esta fora de z=1..300.
5. 30/10/2024 existe no tempRes? `NO` sob hipotese calendario; seria z=304 e esta fora de z=1..300.
6. 31/10/2024 existe no tempRes? `NO` sob hipotese calendario; seria z=305 e esta fora de z=1..300.
7. As comparacoes anteriores com 30/10 e 31/10 estavam temporalmente corretas ou nao? Nao ficam temporalmente provadas. Se z for dia-do-ano, essas comparacoes nao estavam corretas; a melhoria numerica com z=300 deve ser tratada como matching de campo/produto, nao prova temporal.

The audit determines whether z in tempRes is a calendar-day index or a valid-day index after filtering.