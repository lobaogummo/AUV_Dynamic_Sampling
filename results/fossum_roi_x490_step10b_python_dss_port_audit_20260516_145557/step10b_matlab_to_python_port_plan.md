# Step10B MATLAB To Python Port Plan

1. Keep using existing Python HRes arrays; do not regenerate HRes.
2. Validate GSLIB orientation against official October intermediate files, if available.
3. Run Python+DSS for one October date with 100 realizations and a fixed seed; compare broad statistics to official predModel.
4. If metrics are acceptable, run a second October validation date.
5. Only after validation PASS/WARNING accepted, enable C01/C06 pilot generation.
6. If exact reproduction is required, ask Filipa/Renato for original DSS seeds and any generated `ssdir.par` files.
