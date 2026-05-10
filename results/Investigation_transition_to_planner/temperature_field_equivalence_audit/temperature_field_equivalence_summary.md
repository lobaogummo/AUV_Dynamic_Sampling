# Temperature Field Equivalence Audit Summary

- Output directory: `results/Investigation_transition_to_planner/temperature_field_equivalence_audit`
- Fixed transform: `CAND_B_REGISTRATION_TO_HRES_SUBAREA__EPSG_32629_UTM29N_formula__hres_crop_centers__x_normal__y_normal`
- Best pair overall: `{'source_tempres_z': 300, 'target_family': 'C4_predModel', 'target_file': 'data/Test_C4/Priori_Nazare_30-10-2024_1/30-10-2024_predModel_1.nc', 'target_variable': 'TEMPpred', 'target_day_index': 1, 'target_date_inferred': '2024-10-30', 'domain_tested': 'operational_roi', 'rank': 1, 'rmse': 0.4535396109236697, 'pearson': 0.6836446724069731, 'notes': 'Temperature validation target.'}`
- Best apriori pair: `{'source_tempres_z': 300, 'target_family': 'C4_predModel', 'target_file': 'data/Test_C4/Priori_Nazare_30-10-2024_1/30-10-2024_predModel_1.nc', 'target_variable': 'TEMPpred', 'target_day_index': 1, 'target_date_inferred': '2024-10-30', 'domain_tested': 'operational_roi', 'rank': 1, 'rmse': 0.4535396109236697, 'pearson': 0.6836446724069731, 'notes': 'Temperature validation target.'}`
- STD control rows retained separately: `120`

Direct answers:
1. Qual tempRes z corresponde melhor ao dia 30? `300`
2. Qual tempRes z corresponde melhor ao dia 31? `300`
3. C4 ou D4 corresponde melhor ao tempRes? `tie_C4_D4_indistinguishable`
4. day0 ou day1 corresponde melhor? `day1`
5. HResNew TEMP corresponde melhor do que TEMPpred? `False`
6. O AUVpredModel confirma ou diverge, sabendo que e assimilado? AUV best control pair: `{'source_tempres_z': 300, 'target_family': 'C4_AUVpredModel', 'target_file': 'data/Test_C4/HighRes/Daily_dpt_20241030_NewTest_1/31-10-2024_AUVpredModel_1.nc', 'target_variable': 'TEMPpred', 'target_day_index': '', 'target_date_inferred': '2024-10-31', 'domain_tested': 'operational_roi', 'rank': 11, 'rmse': 0.8028442922613285, 'pearson': 0.5689936706736575, 'notes': 'Assimilated/control temperature target.'}`. It is assimilated/control, not a primary validation target.
7. A diferenca principal parece vir de georreferencia ou incompatibilidade entre produtos? A auditoria testa a georreferencia fixa; a variacao entre TEMPpred, HResNew e AUV indica uma componente forte de compatibilidade campo/produto, nao apenas geometria.

The audit identifies the most coherent temperature-to-temperature pair for validating the tempRes-to-HRes/planner georeferencing, without mixing temperature and STD fields.