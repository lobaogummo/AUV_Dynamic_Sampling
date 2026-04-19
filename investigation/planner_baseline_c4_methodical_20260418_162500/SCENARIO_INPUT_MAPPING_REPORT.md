# SCENARIO_INPUT_MAPPING_REPORT

## Executive summary
- All minimum planner inputs were mapped to concrete files/parameters in this repository.
- No mandatory input remains unresolved for the selected baseline scenario.
- A dedicated interface NetCDF was generated to provide exact variable names expected by the planner (`temperr`, `tbath`, `landt`, `lat`, `lon`).

## Mapping table (input -> concrete source)

| planner input | mapped source in this repo | status | notes |
|---|---|---|---|
| `temperr` | `STD` from `data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/31-10-2024_predModel_1.nc` | mapped | in interface file, invalid area is set to `-inf` |
| `tbath` | `-BATHY` from same NetCDF | mapped | sign follows baseline mask rule compatibility |
| `landt` | derived from finiteness of `temperr/tbath` | mapped | binary convention `1=sea`, `0=land` |
| `lat` | `LAT` axis from same NetCDF | mapped | exported as `lat` 1D |
| `lon` | `LON` axis from same NetCDF | mapped | exported as `lon` 1D |
| `land mask reference` | `data/TEST_C4/HighRes/Daily_dpt_20241030_NewTest_1/Nazare_31-10-2024_1/mask.out` | mapped | diagnostic agreement with `landt`: perfect for zero-as-sea convention |
| `operation bbox` | `OptimalPlanning_Lucrezia/Config_file.py` | mapped | crop result: `92 x 149` |
| `obstacles` | `OptimalPlanning_Lucrezia/Config_file.py` | mapped | applied in preplanner sanity and planner run |
| `starts/ends` | `OptimalPlanning_Lucrezia/Config_file.py` | mapped | validated on finite sea cells after all masks |
| `vehicle/solver params` | `OptimalPlanning_Lucrezia/Config_file.py` | mapped | used as-is in baseline |

## Validation facts
- Interface variable presence check: passed (`temperr`, `tbath`, `landt`, `lat`, `lon` present).
- Monotonic axes check: passed (`lat`, `lon` increasing).
- Land-mask agreement check:
`mask_out_zero_matches_landt_sea = 1.0`
- Preplanner sanity on operational crop:
`92 x 149`, finite cells after all masks `10750 / 13708`.
- Depot validity after all masks: all start/end points valid.

## Remaining caveats (non-blocking for this baseline run)
- Current Python/OS environment required compatibility adjustments in snapshot execution layer (no change to objective/cost logic).
- These adjustments are documented in the baseline working-state file and isolated to the scenario snapshot.

