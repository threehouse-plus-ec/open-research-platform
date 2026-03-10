"""
Publication gate for the Open Research Platform.

Promotes validated runs from curated/ to published/.
Enforces: append-forbidden semantics, hash re-verification, index update.
"""

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.lib.validate import validate_run


def load_index(published_dir: Path) -> list[dict]:
    """Load the published run index."""
    index_path = published_dir / "index.json"
    if index_path.exists():
        with open(index_path) as f:
            return json.load(f)
    return []


def save_index(published_dir: Path, index: list[dict]):
    """Write the published run index."""
    index_path = published_dir / "index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2, default=str)


def update_latest(published_dir: Path, run_id: str):
    """Update the latest.json pointer."""
    latest_path = published_dir / "latest.json"
    with open(latest_path, "w") as f:
        json.dump({
            "latest_run_id": run_id,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
        }, f, indent=2)


def promote_run(
    curated_dir: Path,
    published_dir: Path,
    run_id: str,
    force: bool = False,
) -> tuple[bool, str]:
    """Promote a curated run to published.

    Args:
        curated_dir: Path to data/curated/
        published_dir: Path to data/published/
        run_id: The run_id to promote.
        force: Skip re-validation (not recommended).

    Returns:
        (success, message)
    """
    source = curated_dir / run_id
    dest = published_dir / "runs" / run_id

    # Check source exists
    if not source.exists():
        return False, f"Curated run not found: {source}"

    # Append-forbidden: refuse to overwrite
    if dest.exists():
        return False, f"Published run already exists: {dest} (append-forbidden)"

    # Load manifest
    manifest_path = source / "manifest.json"
    if not manifest_path.exists():
        return False, f"No manifest.json in curated run: {source}"

    with open(manifest_path) as f:
        manifest = json.load(f)

    # Check status
    if manifest.get("status") != "success":
        return False, f"Only 'success' runs can be published (status: {manifest.get('status')})"

    # Check visibility
    visibility = manifest.get("visibility", "private")
    if visibility not in ("public", "group"):
        return False, f"Run visibility is '{visibility}' — set to 'public' or 'group' before publishing"

    # Re-validate (independent hash verification)
    if not force:
        is_valid, errors = validate_run(source)
        if not is_valid:
            return False, f"Re-validation failed: {'; '.join(errors)}"

    # Copy to published
    published_dir.joinpath("runs").mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dest)

    # Update index
    index = load_index(published_dir)
    index.append({
        "run_id": run_id,
        "job_name": manifest["job_name"],
        "status": manifest["status"],
        "visibility": visibility,
        "timestamp": manifest["timestamps"]["end"],
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "outputs": [o["filename"] for o in manifest.get("outputs", [])],
        "superseded_by": None,
    })
    save_index(published_dir, index)

    # Update latest pointer
    update_latest(published_dir, run_id)

    return True, f"Promoted {run_id} to published/"


def main():
    """CLI entry point for promotion."""
    if len(sys.argv) != 2:
        print("Usage: python -m src.lib.promote <run_id>")
        sys.exit(1)

    run_id = sys.argv[1]
    curated_dir = Path("data/curated")
    published_dir = Path("data/published")

    success, message = promote_run(curated_dir, published_dir, run_id)
    if success:
        print(f"✓ {message}")
        sys.exit(0)
    else:
        print(f"✗ {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
