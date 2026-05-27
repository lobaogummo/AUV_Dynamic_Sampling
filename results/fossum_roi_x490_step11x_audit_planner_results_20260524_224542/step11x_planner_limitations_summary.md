# Planner limitations summary

## Observed capabilities

- Static prize by node: supported through `information_map`.
- Native multi-AUV with a shared prize map: supported.
- Baseline STD objective: supported.
- Enriched static map `(1-alpha)*STD + alpha*descriptor`: supported as a wrapper/input-map change.

## Current limitations

- Route-level reward: not supported in the observed Step11C runs; crossing reward was implemented as a static-map proxy.
- Vehicle-specific prize maps: not supported natively in the observed Step11D runs; vehicle-specific strategies were proxy/post-solver constructions.
- Overlap/proximity penalty: not supported directly in the native objective; sequential/post-solver variants are wrappers.
- Sequential planning: usable as an external wrapper, not a native joint objective.

## Consequence

The planner can test whether descriptors make good static prize maps, but it cannot yet express the two most interesting behavioral objectives directly: "cross this boundary along the route" and "assign different regime roles to different vehicles".
