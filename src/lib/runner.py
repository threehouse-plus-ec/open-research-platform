#!/usr/bin/env python3
"""
Run a job and produce a validated manifest.

Usage:
    python -m src.lib.runner --job example_scan [--trigger local] [--visibility private]

This script:
1. Loads the job configuration.
2. Executes the job, writing outputs to a temporary directory.
3. Generates a manifest.
4. Runs the validation gate.
5. If valid, copies to data/curated/{run_id}/.
"""

import argparse
import importlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.lib.manifest import create_manifest, write_manifest
from src.lib.validate import validate_run


def main():
    parser = argparse.ArgumentParser(description="Run a job with full provenance.")
    parser.add_argument("--job", required=True, help="Job name (directory under src/jobs/)")
    parser.add_argument("--trigger", default="local", help="Trigger type")
    parser.add_argument("--visibility", default="private", choices=["private", "group", "public"])
    parser.add_argument("--promote-to-curated", action="store_true", default=True,
                        help="Automatically promote valid runs to curated/ (default: True)")
    parser.add_argument("--no-promote", dest="promote_to_curated", action="store_false",
                        help="Keep outputs in ephemeral/ only")
    args = parser.parse_args()

    job_name = args.job
    job_module_path = f"src.jobs.{job_name}.run"
    config_path = Path(f"src/jobs/{job_name}/config.json")

    # Load config
    if config_path.exists():
        with open(config_path) as f:
            parameters = json.load(f)
    else:
        parameters = {}

    # Create ephemeral output directory (temporary — will be renamed with run_id)
    ephemeral_base = Path("data/ephemeral")
    ephemeral_base.mkdir(parents=True, exist_ok=True)
    tmp_dir = ephemeral_base / "_current_run"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir()

    start_time = datetime.now(timezone.utc)
    status = "success"
    status_detail = None

    # Execute the job
    try:
        job_module = importlib.import_module(job_module_path)
        job_module.run(parameters, tmp_dir)
    except Exception as e:
        status = "runtime_failed"
        status_detail = str(e)
        print(f"✗ Job failed: {e}", file=sys.stderr)

    # Generate manifest
    manifest = create_manifest(
        job_name=job_name,
        trigger=args.trigger,
        parameters=parameters,
        output_dir=tmp_dir,
        status=status,
        status_detail=status_detail,
        visibility=args.visibility,
        start_time=start_time,
    )

    run_id = manifest["run_id"]
    write_manifest(manifest, tmp_dir)

    # Rename ephemeral dir to run_id
    run_dir = ephemeral_base / run_id
    tmp_dir.rename(run_dir)

    print(f"Run {run_id}: status={status}")

    # Validation gate
    is_valid, errors = validate_run(run_dir)
    if is_valid:
        print(f"✓ Validation passed")
    else:
        print(f"✗ Validation failed:")
        for err in errors:
            print(f"  - {err}")

    # Promote to curated if valid and requested
    if is_valid and args.promote_to_curated:
        curated_dir = Path("data/curated") / run_id
        curated_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(run_dir, curated_dir)
        print(f"✓ Promoted to curated: {curated_dir}")

    # Output run_id for downstream use (e.g., GitHub Actions)
    github_output = Path(os.environ.get("GITHUB_OUTPUT", "/dev/null"))
    try:
        with open(github_output, "a") as f:
            f.write(f"run_id={run_id}\n")
    except Exception:
        pass

    sys.exit(0 if is_valid else 1)


import os  # noqa: E402 — needed for GITHUB_OUTPUT

if __name__ == "__main__":
    main()
