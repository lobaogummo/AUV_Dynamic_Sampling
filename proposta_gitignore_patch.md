# Proposed .gitignore patch (not applied)

Goal: keep heavy data/results out of Git by default, while allowing manifests,
reports and scripts to be versioned explicitly.

Recommended conservative additions:

```gitignore
# Large project data should stay outside normal Git by default
data/dadosParaPedro_Fresnel/**

# Keep generated binary outputs out of normal Git unless explicitly force-added
results/**/*.nc
results/**/*.npz
results/**/*.out
results/**/*.mat

# Keep lightweight provenance files trackable
!results/**/*.md
!results/**/*.csv
!results/**/*.json
!results/**/*.py
!DATA_MANIFEST.md
!DATA_MANIFEST.csv
!sync_audit_report.md
!sync_audit_inventory.csv
!scripts/check_required_data.py
```

If you decide to use Git LFS for a small explicit subset, add `.gitattributes`
with targeted patterns/paths instead of unignoring all of `data/` or `results/`.
