# Executive Summary (Mask/Plot Investigation)

1. O excesso de preto não veio de um erro no sinal da batimetria.
2. O teste H1 confirmou que `tbath = -BATHY` é a convenção correta neste planner.
3. Se usar `tbath = +BATHY`, a máscara de profundidade elimina 100% da área válida.
4. O `landt` atual não diverge de `mask.out` para este cenário.
5. A convenção observada em `mask.out` é `0 = mar`, `-1 = terra`.
6. A concordância `landt` vs `mask.out` (0=mar) foi de 100%.
7. A máscara final científica mantém 78.42% de células válidas no crop operacional.
8. Há 21.58% de células inválidas reais (terra + depth < 40 m + obstáculos).
9. O aspeto “poluído” vinha principalmente da visualização (`matplotlib` stateful).
10. O plot antigo acumulava `imshow/colorbar` sem reset de figura.
11. Também mostrava `-inf` como cor mais baixa (escuro/preto), ampliando o efeito visual.
12. A correção aplicada foi apenas de plotting (mínima e não científica).
13. Foi introduzido `fig, ax = plt.subplots`, `cmap.set_bad("white")`, `plt.close(fig)`.
14. Não houve alteração de função custo, lógica VRP, planner ou máscaras científicas.
15. O rerun terminou com `exit_code=0` e manteve a solução (rotas iguais, salvo timestamp).
16. Resultado final: plot limpo e rastreável, sem sobreposição de colorbars.
