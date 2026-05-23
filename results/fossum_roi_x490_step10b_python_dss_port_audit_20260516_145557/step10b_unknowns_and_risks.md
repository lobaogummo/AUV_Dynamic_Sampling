# Step10B Unknowns And Risks

- Original MATLAB `parFileDSS.m` uses `rand*1000000` for the DSS seed; official seeds are not stored in predModel NetCDFs.
- `readoutput_AUV.m` computes `var`, not standard deviation, but writes it as `StDev`/`STD`.
- Exact DSS output may depend on random path, seed, executable version, and parameter-file formatting.
- `writealldata_naza.m` and `giveCoordinateInformation_naza.m` include scene/coordinate side-products; Python port writes predModel directly and does not fully reproduce `scene.gslib` yet.
- The 1-realization test confirms execution mechanics only; it is not scientific validation.
