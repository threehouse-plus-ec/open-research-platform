# Governance

## Data separation policy

**Git tracks provenance, not bulk data.**

Committed to Git (the permanent scientific record):
- `manifest.json` — full provenance for every curated and published run
- `summary.json` — compact results summary
- `index.json`, `latest.json` — run catalogue
- All source code, configs, schemas, documentation

Not committed (stored as GitHub Release assets):
- `results.csv`, `trajectories.svg`, `atlas.json` — heavy outputs
- Any generated file that can be reproduced from the manifest

Every published run is tagged `run/{run_id}`. Heavy artefacts are uploaded as release assets on that tag, giving them permanent URLs. The manifest is the guarantee of reproducibility; the data file is a convenience cache.

## Data classification

Every data object carries two independent classifications.

### Retention class

| Class | Retention | Location |
|-------|-----------|----------|
| Ephemeral | Garbage-collected after 30 days (configurable) | `data/ephemeral/` |
| Curated | Retained indefinitely | `data/curated/` |
| Published | Permanent, append-forbidden once promoted | `data/published/` |

### Visibility class

| Class | Who can see it | Default for |
|-------|---------------|-------------|
| Private | Repository owner/team only | All new runs |
| Group | Named collaborators | Shared results not yet public |
| Public | Anyone | Dashboard-facing results |

Retention and visibility are independent. A run can be curated + private (kept for the lab, not published) or published + public (on the dashboard, fully open).

## Two-gate promotion

### Validation gate (ephemeral → curated)

Automated. Checks:
- Manifest conforms to `schemas/manifest.schema.json`
- All declared output files exist
- SHA-256 hashes match
- Status is `success` or `validation_failed`

### Publication gate (curated → published)

Deliberate. Requires:
- Status is `success`
- Visibility is `public` (or `group` for group-facing dashboards)
- Output hashes re-verified independently
- Explicit trigger (workflow dispatch or PR merge)

## Immutability

Published runs are append-forbidden. If a published run is later found to be erroneous:
- It is **not deleted**.
- A new run is published with `"supersedes": "{old_run_id}"` in its manifest.
- The old run's index entry is annotated with `"superseded_by": "{new_run_id}"`.
- Old artefacts remain addressable at their original path.

## Adding collaborators

At Stage 2+, use GitHub Teams to manage group access. The visibility class in the manifest controls which runs are eligible for the publication gate.
