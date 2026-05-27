# Next experiments plan

1. Keep C01 2024-08-24, C06 2023-12-22, and October 2024-10-30 as the controlled case set, but label confidence and regime type explicitly.
2. For single-AUV, repeat only baseline_STD, boundary_alpha050, crossing_gamma025, and one improved crossing proxy; avoid a broad gamma sweep until the proxy is cleaner.
3. For multi-AUV, prioritize true or emulated vehicle-specific prize maps: AUV1 = regime_A/STD blend and AUV2 = regime_B/STD blend.
4. Treat post-solver selection as diagnostic evidence, not the final operational method.
5. Keep overlap penalty as secondary unless future native runs show nonzero duplicate sampling is the dominant failure.
