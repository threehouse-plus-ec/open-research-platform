# Retention Policy

## Ephemeral data

- **Default retention:** 30 days from run completion.
- **What is deleted:** Output files and logs in `data/ephemeral/{run_id}/`.
- **What is preserved:** The manifest file (`manifest.json`) is kept for 90 days even after output deletion, to allow post-hoc diagnosis of failed runs.
- **Trigger:** The `health-check.yml` workflow can be extended to perform garbage collection, or run manually:

```bash
# Delete ephemeral runs older than 30 days
find data/ephemeral -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +
```

- **Override:** To preserve an ephemeral run, move it to `data/curated/` before the retention period expires.

## Curated data

- Retained indefinitely by default.
- The repository owner may delete curated runs at their discretion.
- No automated garbage collection.

## Published data

- Permanent. Append-forbidden once promoted.
- Corrections via supersession only (see [`GOVERNANCE.md`](GOVERNANCE.md)).
- Manual deletion of published data requires explicit justification and should be documented in a commit message.
