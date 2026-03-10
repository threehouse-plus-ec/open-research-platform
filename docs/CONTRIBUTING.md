# Contributing

## Adding a new job

1. Create a directory under `src/jobs/your_job_name/`.
2. Add `run.py` with a `run(config: dict, output_dir: Path)` function.
3. Add `config.json` with default parameters.
4. Test locally: `python -m src.lib.runner --job your_job_name`.

## Modifying the platform

- Changes to `src/lib/` affect the core pipeline. Test thoroughly before merging.
- Changes to `schemas/manifest.schema.json` require a schema version bump.
- Changes to workflows should be tested in a fork before merging to main.

## Code style

- Python: follow PEP 8.
- Use type hints where practical.
- Keep dependencies minimal — the platform should remain lightweight and forkable.

## Pull requests

- One logical change per PR.
- Include a clear description of what changed and why.
- For Stage 2+: all PRs to `main` require at least one review.
