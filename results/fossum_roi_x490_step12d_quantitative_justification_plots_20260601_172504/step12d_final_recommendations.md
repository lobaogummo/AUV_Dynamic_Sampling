# Step12D final recommendations

Verdict: `QUANTITATIVE_JUSTIFICATION_READY`

1. The most useful weight plots are the Pareto plots: `single_auv_STD_loss_vs_regime_balance_pareto.png` and `multi_auv_STD_loss_vs_region_B_gain_pareto.png`.
2. The best single-AUV weight under the auxiliary score is listed in `step12d_single_auv_weight_decision_table.csv` with `selected_candidate_flag=True`.
3. The best multi-AUV weight under the auxiliary score is listed in `step12d_multi_auv_weight_decision_table.csv` with `selected_candidate_flag=True`.
4. Mission duration should be discussed as a sensitivity axis, because the same weights can behave differently under short and long missions.
5. Dominated configurations are those with `pareto_front_flag=False`; Pareto candidates are exported separately.
6. Runtime affects weight selection through `runtime_penalty`, but does not override scientific tradeoff metrics by itself.
7. Runtime has limited influence on class-number choice compared with ICV, class size, stability, separation, interpretability, and fragmentation risk.
8. The available ICV evidence supports 6 classes versus 5 classes, while the 10-class alternative illustrates why minimum ICV alone is not enough.
9. Yes, there is a real risk of choosing too many classes if ICV is minimized naively.
10. Thesis recommendation: present 6 classes as the canonical Fossum-style branch, and present planner weights as Pareto-supported tradeoffs rather than universal optima.
