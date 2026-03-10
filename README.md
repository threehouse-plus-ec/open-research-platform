# Rocket Science — Open Research Platform

A forkable, free, open-source platform for **reproducible research execution with provenance**.

Fork this repo → connect a runner (or use GitHub's free runners) → run your first job with full provenance in one afternoon.

**Showcase:** The included `rocket_scan` job simulates single-stage rocket trajectories across a launch angle sweep — complete with an SVG trajectory plot, performance table, and full manifest provenance. It is not rocket science. Well, actually it is.

## What this gives you

- **Four-layer architecture:** repository of record → execution plane → data products → optional publication layer
- **Manifest-based provenance:** every run produces a signed manifest recording code version, environment, parameters, outputs, and machine resources
- **Two-gate quality control:** automated validation gate (technical correctness) + deliberate publication gate (visibility approval)
- **Static dashboard:** GitHub Pages site that reads only from published results — zero server cost
- **Forkable template:** replace the example job with your research code; everything else works as-is

## Quick start

```bash
# 1. Fork this repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR-USERNAME/open-research-platform.git
cd open-research-platform

# 3. Run the rocket trajectory scan
python -m src.lib.runner --job rocket_scan --trigger local --visibility private

# 4. Check the results
cat data/curated/*/manifest.json
# → full provenance: commit, environment, parameters, output hashes
ls data/curated/*/
# → results.csv, trajectories.svg, summary.json, manifest.json
```

For the full setup guide (including GitHub Actions, self-hosted runners, and dashboard deployment), see [`docs/SETUP.md`](docs/SETUP.md).

## Architecture at a glance

```
Layer 4  Publication (optional)   Static dashboard on GitHub Pages
Layer 3  Data Products            ephemeral → [validation gate] → curated → [publication gate] → published
Layer 2  Execution Plane          GitHub Actions runners + Docker containers
Layer 1  Repository of Record     Source code, configs, workflows, manifests, documentation
```

The **validation gate** checks schema compliance, file existence, and hash integrity.
The **publication gate** checks visibility classification and requires explicit approval.

Only published results reach the dashboard. The dashboard reads only from `data/published/`.

## Repository structure

```
src/jobs/           Your research jobs (includes rocket_scan/ and example_scan/)
src/lib/            Platform library (manifest, validate, promote, runner)
schemas/            Formal JSON Schema for run manifests
environments/       Dockerfile (canonical) + dependency lockfiles
data/               Ephemeral → curated → published pipeline
dashboard/          Static site source (Rocket Science mission control)
docs/               Architecture, setup, governance, security, data policy
.github/workflows/  CI/CD pipeline definitions
```

## Adding your own job

1. Create a directory under `src/jobs/your_job_name/`
2. Add a `run.py` with a `run(config, output_dir)` function
3. Add a `config.json` with your parameters
4. Run: `python -m src.lib.runner --job your_job_name`

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — full architectural blueprint
- [`docs/SETUP.md`](docs/SETUP.md) — fork-and-run guide
- [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md) — data classification and promotion rules
- [`docs/SECURITY.md`](docs/SECURITY.md) — threat model and access controls
- [`docs/DATA_POLICY.md`](docs/DATA_POLICY.md) — data ownership and privacy
- [`docs/RETENTION.md`](docs/RETENTION.md) — ephemeral cleanup policy

## Licence

MIT — see [LICENSE](LICENSE).
