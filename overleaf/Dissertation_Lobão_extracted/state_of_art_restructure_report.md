# State of the Art Restructure Report

Date: 2026-04-30  
Input chapter inspected: `chapter3.tex`  
New chapter created: `state_of_art_restructured.tex`  
Old chapter preserved: yes. `chapter3.tex` was not modified.

## Objective

The old State of the Art chapter was restructured into a coherent academic chapter aligned with the current thesis:

> Integration of spatial regimes/descriptors extracted from ocean temperature maps with an adaptive AUV planner based on STD uncertainty maps, using the Nazaré Canyon as a case study.

The new chapter focuses on:

1. Adaptive sampling with AUVs.
2. Model-driven ocean sampling.
3. Uncertainty-driven trajectory planning.
4. Geostatistical uncertainty maps.
5. Spatial regime discovery and compact models.
6. Research gap and positioning of the thesis.

## Main Changes

### 1. Shifted the narrative away from the previous topic

The old chapter was centred on dynamic sampling with multi-agent AUVs using machine learning, with substantial emphasis on:

- multi-agent coordination;
- intermittent communication;
- GMM/PCM/HMM regime inference;
- T/S/depth profile classification;
- assimilation/update logic;
- Douro plume examples.

The new chapter reduces these topics and reframes the literature around the current pipeline:

- model-derived TEMP and STD maps;
- uncertainty-driven planning;
- geostatistical uncertainty maps;
- spatial temperature regimes;
- descriptors such as `boundary_score` and `gradient_magnitude`;
- baseline STD-driven planner vs descriptor-enriched planner.

### 2. Rebuilt the chapter as a connected argument

The new chapter avoids a list-of-papers style. Each section builds towards the identified gap:

- adaptive sampling motivates why AUVs need value-driven planning;
- model-driven sampling explains how ocean model products become planner inputs;
- uncertainty-driven planning explains why STD maps are useful as rewards;
- geostatistical maps provide the practical uncertainty-map basis;
- regime discovery explains why temperature structure can add information beyond uncertainty;
- the final gap section connects these strands to the thesis contribution.

### 3. Preserved valid existing references

No new bibliographic keys were invented. Citations were reused only from `bibliography.bib`.

Main reused references:

| Topic | References reused |
|---|---|
| AUV adaptive sampling and surveys | `curtin2009aosn`, `hwang2019auvreview` |
| Adaptive modelling / adaptive sampling | `lermusiaux2007adaptive` |
| Model-driven robotic exploration | `mendes2025oceanmodeldriven` |
| Closing the loop / route planning from uncertainty | `bernacchi2025closingloop` |
| Geostatistical uncertainty maps | `duarte2025geostatistical` |
| Optimal sampling beyond grid surveys | `frolov2014grid` |
| Flow-aware trajectory optimisation | `aguiar2018trajectoryopt` |
| Feature-driven sampling | `das2012coordinated`, `fossum2018informationdriven`, `fossum2019phytoplankton` |
| Compact models / sparse representations | `fossum2020compact` |
| Water-mass classification and regime belief | `ge2023watermasses` |

## Structure of the New Chapter

```text
\chapter{Related Work and the State of the Art}

1. Adaptive sampling with AUVs
2. Model-driven ocean sampling
3. Uncertainty-driven trajectory planning
4. Geostatistical uncertainty maps
5. Spatial regime discovery and compact models
6. Identified gap
```

## Identified Gap Included

The final section explicitly states the required gap:

> The literature uses uncertainty to guide planning, but there is an opportunity to complement uncertainty maps with descriptors derived from spatial temperature regimes.

The gap is expressed in thesis-specific terms:

- STD maps provide uncertainty-driven rewards.
- TEMP maps contain spatial structure that may not be captured by STD alone.
- `boundary_score` and `gradient_magnitude` can encode thermal boundaries and regime transitions.
- The thesis evaluates whether an enriched planner improves over a baseline STD-driven planner in the Nazaré Canyon case study.

## TODOs Left Intentionally

The following TODOs were inserted because the corresponding references are not currently present in `bibliography.bib`, and the instruction was not to invent references:

1. CMEMS/IBI product documentation or peer-reviewed reference.

   Location: `Model-driven ocean sampling`

   Reason: the current thesis uses CMEMS/IBI data, but the `.bib` file does not contain a dedicated CMEMS/IBI source.

2. Temperature-front detection or image-gradient descriptors.

   Location: `Spatial regime discovery and compact models`

   Reason: if `boundary_score` or `gradient_magnitude` are based on established methods beyond standard finite differences, those methods should be cited.

3. Nazaré Canyon oceanographic case-study references.

   Location: `Identified gap`

   Reason: the case study is central to the current thesis, but no Nazaré Canyon reference appears in the existing `.bib`.

## Content Removed or Reduced Compared with the Old Chapter

The new chapter deliberately reduces:

- long taxonomy tables;
- large TikZ conceptual diagrams;
- detailed multi-agent communication discussion;
- extensive flow-diagnostics discussion;
- data assimilation/update gating as a central contribution;
- Douro plume and multi-agent RL emphasis;
- deep latent models and broad ML discussion;
- long lists of strengths and limitations per individual paper.

This material can still be reused elsewhere if needed, but it is not central to the current State of the Art.

## Integration Recommendation

Recommended next step:

1. Review `state_of_art_restructured.tex` for supervisor-specific terminology.
2. Add missing references to `bibliography.bib` for:
   - CMEMS/IBI;
   - Nazaré Canyon;
   - temperature-front or gradient-based descriptors, if needed.
3. Replace `\include{chapter3}` with `\include{state_of_art_restructured}` in `meec_thesis.tex` only after the new chapter has been reviewed.
4. Keep `chapter3.tex` as a backup until the final structure is stable.

## Quality Notes

- The new chapter is written in academic English with British spelling, including `modelling`, `favour`, `behaviour`, and `emphasise`.
- Existing LaTeX citation style was preserved using `\parencite` and `\textcite`.
- No `.tex` source file from the old project was modified.
- The new chapter does not require the old figures, which makes it lighter and easier to integrate.
