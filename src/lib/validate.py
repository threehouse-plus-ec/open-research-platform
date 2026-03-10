"""
Validation gate for the Open Research Platform.

Checks manifest schema compliance, output file existence, and hash integrity.
This is the first gate: ephemeral → curated.
"""

import hashlib
import json
import sys
from pathlib import Path


def hash_file(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_manifest_schema(manifest: dict) -> list[str]:
    """Check manifest has all required fields and correct types.

    Returns a list of error messages (empty if valid).
    For full JSON Schema validation, use jsonschema against schemas/manifest.schema.json.
    This is a lightweight built-in check for environments without jsonschema installed.
    """
    errors = []

    required_fields = [
        "schema_version", "run_id", "job_name", "trigger",
        "timestamps", "provenance", "environment", "parameters",
        "outputs", "status", "visibility",
    ]
    for field in required_fields:
        if field not in manifest:
            errors.append(f"Missing required field: {field}")

    if manifest.get("schema_version") != "2.0.0":
        errors.append(f"Unsupported schema version: {manifest.get('schema_version')}")

    valid_statuses = {"success", "validation_failed", "runtime_failed",
                      "environment_failed", "cancelled"}
    if manifest.get("status") not in valid_statuses:
        errors.append(f"Invalid status: {manifest.get('status')}")

    valid_visibilities = {"private", "group", "public"}
    if manifest.get("visibility") not in valid_visibilities:
        errors.append(f"Invalid visibility: {manifest.get('visibility')}")

    valid_source_modes = {"ci_checkout", "local_dev", "manual_snapshot"}
    prov = manifest.get("provenance", {})
    if prov.get("source_mode") not in valid_source_modes:
        errors.append(f"Invalid source_mode: {prov.get('source_mode')}")

    if not isinstance(manifest.get("outputs"), list):
        errors.append("'outputs' must be a list")
    else:
        for i, out in enumerate(manifest["outputs"]):
            for key in ("filename", "sha256", "size_bytes"):
                if key not in out:
                    errors.append(f"Output [{i}] missing '{key}'")

    return errors


def validate_output_integrity(manifest: dict, run_dir: Path) -> list[str]:
    """Verify all declared outputs exist and their hashes match.

    Returns a list of error messages (empty if valid).
    """
    errors = []

    for out in manifest.get("outputs", []):
        filepath = run_dir / out["filename"]
        if not filepath.exists():
            errors.append(f"Output file missing: {out['filename']}")
            continue

        actual_hash = hash_file(filepath)
        if actual_hash != out["sha256"]:
            errors.append(
                f"Hash mismatch for {out['filename']}: "
                f"expected {out['sha256'][:16]}..., got {actual_hash[:16]}..."
            )

        actual_size = filepath.stat().st_size
        if actual_size != out["size_bytes"]:
            errors.append(
                f"Size mismatch for {out['filename']}: "
                f"expected {out['size_bytes']}, got {actual_size}"
            )

    return errors


def validate_run(run_dir: Path) -> tuple[bool, list[str]]:
    """Run the full validation gate on a completed run directory.

    Args:
        run_dir: Path to the run directory (must contain manifest.json).

    Returns:
        (is_valid, list_of_errors)
    """
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        return False, ["No manifest.json found in run directory"]

    with open(manifest_path) as f:
        manifest = json.load(f)

    errors = []

    # Schema check
    errors.extend(validate_manifest_schema(manifest))

    # Only check output integrity if status suggests outputs should exist
    if manifest.get("status") in ("success", "validation_failed"):
        errors.extend(validate_output_integrity(manifest, run_dir))

    return len(errors) == 0, errors


def main():
    """CLI entry point for validation."""
    if len(sys.argv) != 2:
        print(f"Usage: python -m src.lib.validate <run_directory>")
        sys.exit(1)

    run_dir = Path(sys.argv[1])
    is_valid, errors = validate_run(run_dir)

    if is_valid:
        print(f"✓ Validation passed: {run_dir}")
        sys.exit(0)
    else:
        print(f"✗ Validation failed: {run_dir}")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
