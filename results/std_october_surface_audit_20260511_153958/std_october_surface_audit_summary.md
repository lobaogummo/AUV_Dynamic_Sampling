# October Surface STD Audit Summary

Output folder: `C:\Users\pedro\Documents\Filipa_dados\results\std_october_surface_audit_20260511_153958`

1. Existem 31 mapas STD surface para outubro?
   - Sim: foram encontrados 31 de 31.
2. Todos os ficheiros predModel_1 foram encontrados?
   - Sim.
3. A variavel STD existe em todos?
   - Sim.
4. Qual slice do eixo day contem o STD valido?
   - Slice `1`.
5. O primeiro slice esta realmente zero/degenarado?
   - Sim: 31 de 31 dias estao degenerados/zero no slice 0.
6. O segundo slice esta valido?
   - Sim: 31 de 31 dias validos no slice 1.
7. O mesmo slice valido e usado em todos os dias?
   - Sim.
8. Os STD tem shape 180 x 240?
   - Sim.
9. Ha mapas em branco?
   - Nenhum.
10. Ha mapas STD totalmente zero?
   - Nenhum.
11. Ha dias suspeitos?
   - Nenhum.
12. Quais dias tem maior STD media/maxima?
   - Maior media:
- 2024-10-31: mean=0.0739105, max=0.166256, p99=0.1213
- 2024-10-30: mean=0.0719986, max=0.148002, p99=0.112444
- 2024-10-29: mean=0.0643899, max=0.116516, p99=0.0956473
- 2024-10-16: mean=0.0518793, max=0.098673, p99=0.078299
- 2024-10-15: mean=0.0509959, max=0.096533, p99=0.0788137
   - Maior maxima:
- 2024-10-31: max=0.166256, mean=0.0739105, p99=0.1213
- 2024-10-30: max=0.148002, mean=0.0719986, p99=0.112444
- 2024-10-20: max=0.12646, mean=0.0463099, p99=0.10415
- 2024-10-21: max=0.126327, mean=0.0382155, p99=0.0969567
- 2024-10-23: max=0.122091, mean=0.0440731, p99=0.0909502
13. Os mapas STD estao prontos para aplicar o ROI x490?
   - Sim, numericamente parecem prontos para aplicar o ROI x490, mantendo a convencao de slice identificada.
14. Que pontos ainda devem ser confirmados com a Filipa?
   - Confirmar formalmente que `predModel_1` corresponde sempre a surface (~0.494025 m).
   - Confirmar que o slice `1` do eixo `day` e a convencao correta para todos os mapas STD de outubro.
   - Confirmar se zeros no slice 0 sao preenchimento/placeholder esperado e nao informacao fisica.

Final verdict: READY_FOR_ROI_X490: all October surface STD maps passed the audit.

The October surface STD maps were audited and the valid day-slice convention was identified before applying the FRESNEL x490 ROI.
