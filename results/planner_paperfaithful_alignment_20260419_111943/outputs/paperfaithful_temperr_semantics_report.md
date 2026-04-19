# paperfaithful_temperr_semantics_report

## Inputs inspected
- source nc: `C:\Users\pedro\Documents\Filipa_dados\data\TEST_C4\HighRes\Daily_dpt_20241030_NewTest_1\31-10-2024_predModel_1.nc`
- current interface: `C:\Users\pedro\Documents\Filipa_dados\results\planner_paperfaithful_alignment_20260419_111943\inputs\31-10-2024_predModel_1_planner_interface_current.nc`
- paperfaithful interface: `C:\Users\pedro\Documents\Filipa_dados\results\planner_paperfaithful_alignment_20260419_111943\inputs\31-10-2024_predModel_1_planner_interface_paperfaithful.nc`

## Observed source fields
- `STD` exists and is 2D (`LAT`,`LON`) in this dataset.
- `TEMP` exists as 4D (`TIME`,`DEPT`,`LAT`,`LON`) but is not an uncertainty/error field by itself.

## Paper expectation
- Paper states the planner input is a 2D uncertainty/error map.
- For 3D models, paper describes deriving 2D by depth aggregation over covered levels.

## Classification
- Result: **PLAUSIBLE EQUIVALENT**
- Note: STD is already 2D; no explicit depth aggregation possible.

## Practical implication
- With currently available fields, using `STD` 2D is the closest defensible uncertainty input.
- Exact reproduction of depth-aggregation pathway is limited because no depth-resolved uncertainty field is available here.