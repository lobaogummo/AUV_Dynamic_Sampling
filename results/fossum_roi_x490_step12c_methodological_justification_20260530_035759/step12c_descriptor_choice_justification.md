# Step12C descriptor-choice justification

The descriptors tested in Step12 are the descriptors most directly tied to the planner question.

- `boundary_score`: tests whether rewarding transition/frontier structure changes the path relative to STD-only planning.
- `representative_zone` / `region_A` / `region_B`: supports regime-role assignment, especially for multi-AUV planning where different vehicles should cover different regime structures.
- `interest_map`: a composite/proxy descriptor useful as sensitivity evidence because it mixes several prototype characteristics.

Other descriptors such as `gradient` and `heterogeneity` remain useful ablation diagnostics from Step11B, but Step12 focuses on the smaller set that is easiest to defend as a cost-function choice.

Important methodological constraint: all descriptors used here come from the predicted prototype class. They are not recomputed from the day-specific TEMPpred field.
