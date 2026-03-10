# Setup Guide

How to fork this platform and have your first provenance-tracked run within one afternoon.

## Prerequisites

- Python 3.10+
- Git
- A GitHub account (free tier is sufficient for Stage 0)
- Docker or Podman (recommended but optional for Stage 0)

## Stage 0: Local runs with GitHub hosted runners

### 1. Fork and clone

Fork this repository on GitHub, then:

```bash
git clone https://github.com/YOUR-USERNAME/open-research-platform.git
cd open-research-platform
```

### 2. Run the example job locally

```bash
python -m src.lib.runner --job example_scan --trigger local --visibility private
```

This will:
- Execute the damped oscillator parameter scan
- Generate outputs in `data/ephemeral/`
- Create a manifest with full provenance
- Validate the run (schema, hashes)
- Promote to `data/curated/` if valid

Check the results:

```bash
cat data/curated/*/manifest.json | python -m json.tool
```

### 3. Enable GitHub Actions

In your fork, go to **Settings → Actions → General** and ensure Actions are enabled.

The `run-job.yml` workflow will:
- Run automatically on push to `src/` or `environments/`
- Run on a weekly schedule (configurable)
- Accept manual dispatch with custom parameters

### 4. Deploy the dashboard (optional)

1. Go to **Settings → Pages**
2. Set source to **GitHub Actions**
3. Trigger the `deploy-dashboard.yml` workflow

The dashboard will be available at `https://YOUR-USERNAME.github.io/open-research-platform/`.

### 5. Publish a run

Once you have a curated run you want to make public:

1. Update the manifest's visibility to `"public"` in `data/curated/{run_id}/manifest.json`
2. Commit and push
3. Go to **Actions → Promote to Published** and enter the run_id
4. The dashboard will update automatically

## Stage 1: Self-hosted runner

When you outgrow the free runner minutes (~2000/month), add your own machine:

### 1. Set up the runner

On your Linux machine:

```bash
# Follow GitHub's instructions at:
# Settings → Actions → Runners → New self-hosted runner
# This gives you a one-line install command.
```

### 2. Update the workflow

In `.github/workflows/run-job.yml`, change:

```yaml
# From:
runs-on: ubuntu-latest

# To:
runs-on: [self-hosted, linux]
```

### 3. Enable containerised runs (recommended)

Install Docker or Podman on your machine, then uncomment the container steps in `run-job.yml`. This pins your environment to the Dockerfile digest.

## Adding your research code

### Replace the example job

1. Create `src/jobs/my_experiment/run.py`:

```python
def run(config: dict, output_dir):
    """Your research code here.
    
    Args:
        config: Parameters loaded from config.json
        output_dir: Write all output files here
    """
    # Do your computation
    results = your_computation(config)
    
    # Write outputs — the manifest will catalogue them automatically
    import csv
    with open(output_dir / "results.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerows(results)
```

2. Create `src/jobs/my_experiment/config.json`:

```json
{
    "param_a": 1.0,
    "param_b": 100,
    "method": "your_method"
}
```

3. Run it:

```bash
python -m src.lib.runner --job my_experiment --trigger local
```

### Add dependencies

1. Add packages to `environments/requirements.lock`:

```
numpy==1.26.4
scipy==1.13.0
```

2. If using containers, rebuild:

```bash
docker build -t orp-job -f environments/Dockerfile .
```

## Troubleshooting

**"No manifest.json found"** — The runner writes to `data/ephemeral/_current_run/` first, then renames. If a run crashed mid-way, clean up with `rm -rf data/ephemeral/_current_run/`.

**Workflow fails to push** — Ensure your workflow has write permissions: **Settings → Actions → General → Workflow permissions → Read and write**.

**Dashboard shows no runs** — Runs must pass both gates. Check that `data/published/index.json` exists and contains entries.
