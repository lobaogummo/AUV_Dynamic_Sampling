# October Surface TEMPpred/STD ROI x490 Summary

Output folder: `C:\Users\pedro\Documents\Filipa_dados\results\october_surface_temppred_std_roi_x490_20260511_155923`

1. Os 31 mapas TEMPpred/STD surface foram encontrados?
   - Sim.
2. Qual slice do eixo day foi usado?
   - Slice `1`.
3. O slice 0 foi ignorado?
   - Sim.
4. O ROI aplicado e exatamente o mesmo ROI x490 dos 370 mapas HRes?
   - Sim; foram usados os indices `{'row_min': 55, 'row_max': 126, 'col_min': 47, 'col_max': 163}` do metadata de referencia.
5. Qual shape final dos arrays?
   - TEMPpred: `[31, 72, 117]`; STD: `[31, 72, 117]`.
6. TEMPpred e STD ficaram com shape [31, 72, 117]?
   - Sim.
7. LAT/LON/BATHY/MASK ficaram consistentes com o ROI de referencia?
   - LAT/LON: `True`; BATHY: `True`; MASK: `True`.
8. Quantos PNGs STD foram gerados?
   - 31 normais + 31 clean.
9. Quantos PNGs TEMPpred foram gerados?
   - 31 normais + 31 clean.
10. Houve algum dia falhado ou suspeito?
   - Nenhum.
11. Os outputs estao prontos para integracao com descriptors e planner?
   - Sim, os outputs estao prontos para integracao com descriptors e planner.

Final verdict: READY_FOR_DESCRIPTORS_AND_PLANNER: October surface TEMPpred and STD ROI x490 outputs passed all checks.

The October surface TEMPpred and STD maps were cropped to the same FRESNEL x490 ROI used by the 370-day HRes temperature dataset, using the validated day-slice convention.
