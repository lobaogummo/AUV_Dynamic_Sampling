# Step11B logic report

Step11B did use descriptors in the objective. The source script constructs `information_map = (1-alpha) * STD_norm + alpha * descriptor_norm` and saves `step11b_information_maps_by_descriptor.npz`.

Why some maps look like STD: the descriptor trajectory panel uses diagnostic background panels, including STD and descriptor maps. These backgrounds are not always the exact blended information_map used by the planner.

Conclusion: Step11B is valid as descriptor-ablation diagnostics, but thesis figures should use the regenerated information_map panels or captions that clearly separate objective map from visualization background.

| descriptor | tested_alpha_values | planner_used_descriptor | recommended_use |
| --- | --- | --- | --- |
| boundary | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| gradient | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| heterogeneity | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| interest | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| representative_zone | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| boundary | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| gradient | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| heterogeneity | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| interest | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| representative_zone | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| boundary | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| gradient | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| heterogeneity | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| interest | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
| representative_zone | 0.25,0.5 | True | diagnostic; use regenerated information_map figure for thesis objective explanation |
