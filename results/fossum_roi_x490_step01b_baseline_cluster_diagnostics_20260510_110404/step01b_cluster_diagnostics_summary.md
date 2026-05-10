# Step01b baseline cluster diagnostics summary

1. C04 está realmente próxima de C01? parcialmente. Correlação dos protótipos=0.5926; RMSE=0.8696.
2. C04 deveria ser fundida com C01? não de forma automática; é visualmente próxima mas a distância em features ainda separa o grupo.
3. C01 tem subestrutura interna visível? sim.
4. As imagens azul claro da C01 formam um subgrupo coerente? sim, preliminarmente.
5. O problema parece vir do corte SD=0.30? Parcialmente; cortes alternativos alteram a granularidade, mas a estrutura C01/C04 sugere também limitação da configuração de features.
6. Número de classes mais adequado entre 4-8: 4.
7. SD fraction mais adequada entre as testadas: 0.40.
8. Devemos ajustar apenas o corte ou avançar para patch-size sensitivity? Avançar para patch-size sensitivity, usando estes cortes como referência diagnóstica.
9. A configuração antiga continua aceitável como baseline? Sim, como baseline inicial, mas não como configuração final sem sensitivity.
10. Próxima etapa recomendada: Try 6-class interpretation/cut first, then run patch-size sensitivity to confirm C01 split stability.

The Step01 baseline clustering was diagnosed to determine whether the observed class issues are caused by the dendrogram cut or by the feature extraction configuration.
