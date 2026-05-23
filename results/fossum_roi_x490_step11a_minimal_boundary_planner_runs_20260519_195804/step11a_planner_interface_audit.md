# Step11A Planner Interface Audit

- Planner: `C:\Users\E713181\Documents\Dados\FILIPA_DADOS\OptimalPlanning_Lucrezia`
- Information map enters as NetCDF variable `temperr`.
- With `MODEL_HOPS=True`, `OptimalPlanning.py` reads `netcdf_file.temperr.to_numpy()`.
- The planner maximizes route prize/value: `Utils.get_nodes_prize()` converts `temperr` values at POIs into integer prizes for PyVRP.
- Baseline/enriched substitution is done by writing a different `temperr` map; constraints and penalties remain in the copied runtime config.
- Step11A uses normalized [0,1] maps, which is appropriate because the solver uses relative prize levels.
- Runtime is single-AUV using the first original AUV start/end/duration; original planner files are not edited.