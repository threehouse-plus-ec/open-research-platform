"""
Manifest generation for the Open Research Platform.

Every completed run produces exactly one manifest — the atomic unit of provenance.
"""

import hashlib
import json
import os
import platform
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def generate_run_id(job_name: str, git_commit: str) -> str:
    """Generate a collision-resistant run ID.

    Format: {ISO-timestamp}_{job-name}_{short-commit}_{random-4hex}
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    short_commit = git_commit[:7]
    suffix = secrets.token_hex(2)  # 4 hex chars
    return f"{ts}_{job_name}_{short_commit}_{suffix}"


def hash_file(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_git_info() -> dict:
    """Gather Git provenance information."""
    def _run(cmd):
        try:
            return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    commit = _run(["git", "rev-parse", "HEAD"]) or "unknown"
    ref = _run(["git", "symbolic-ref", "HEAD"]) or "detached"
    dirty = _run(["git", "status", "--porcelain"])

    # Detect source mode
    if os.environ.get("GITHUB_ACTIONS") == "true":
        source_mode = "ci_checkout"
    elif os.environ.get("ORP_SOURCE_MODE"):
        source_mode = os.environ["ORP_SOURCE_MODE"]
    else:
        source_mode = "local_dev"

    return {
        "git_commit": commit,
        "git_ref": ref,
        "source_mode": source_mode,
        "workspace_dirty": bool(dirty),
        "untracked_files_present": any(
            line.startswith("??") for line in (dirty or "").splitlines()
        ),
    }


def get_resource_info() -> dict:
    """Gather machine resource information."""
    info = {
        "runner_label": os.environ.get("RUNNER_NAME", platform.node()),
        "os": platform.system().lower(),
        "arch": platform.machine(),
        "cpu_model": None,
        "cores_available": os.cpu_count(),
        "cores_used": int(os.environ.get("ORP_CORES_USED", os.cpu_count() or 1)),
        "ram_gb": None,
        "gpu": None,
    }

    # CPU model (Linux)
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    info["cpu_model"] = line.split(":")[1].strip()
                    break
    except FileNotFoundError:
        pass

    # RAM (Linux)
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    info["ram_gb"] = round(kb / 1048576, 1)
                    break
    except FileNotFoundError:
        pass

    return info


def get_environment_info() -> dict:
    """Gather environment specification information."""
    env_info = {
        "canonical_spec": "environments/Dockerfile",
        "image_digest": os.environ.get("ORP_IMAGE_DIGEST", "local-build"),
        "lockfile_hash": None,
        "base_image": None,
    }

    # Hash lockfile if it exists
    for lockfile in ["environments/requirements.lock", "environments/environment.yml"]:
        p = Path(lockfile)
        if p.exists():
            env_info["lockfile_hash"] = f"sha256:{hash_file(p)}"
            break

    return env_info


def create_manifest(
    job_name: str,
    trigger: str,
    parameters: dict,
    output_dir: Path,
    status: str = "success",
    status_detail: str | None = None,
    visibility: str = "private",
    start_time: datetime | None = None,
    notes: str = "",
) -> dict:
    """Create a complete manifest for a run.

    Args:
        job_name: Name of the job (must match a directory under src/jobs/).
        trigger: What initiated this run (schedule, workflow_dispatch, push, etc.).
        parameters: Job-specific input parameters.
        output_dir: Directory containing the run's output files.
        status: Final status of the run.
        status_detail: Diagnostic message for non-success statuses.
        visibility: Visibility classification (private, group, public).
        start_time: When the run started. Defaults to now if not provided.
        notes: Optional free-text notes.

    Returns:
        Complete manifest dictionary.
    """
    git_info = get_git_info()
    run_id = generate_run_id(job_name, git_info["git_commit"])

    # Catalogue output files
    outputs = []
    output_path = Path(output_dir)
    if output_path.exists():
        for f in sorted(output_path.iterdir()):
            if f.is_file() and f.name != "manifest.json":
                outputs.append({
                    "filename": f.name,
                    "sha256": hash_file(f),
                    "size_bytes": f.stat().st_size,
                })

    now = datetime.now(timezone.utc)
    manifest = {
        "schema_version": "2.0.0",
        "run_id": run_id,
        "job_name": job_name,
        "trigger": trigger,
        "timestamps": {
            "start": (start_time or now).isoformat(),
            "end": now.isoformat(),
        },
        "provenance": git_info,
        "environment": get_environment_info(),
        "resources": get_resource_info(),
        "parameters": parameters,
        "outputs": outputs,
        "status": status,
        "status_detail": status_detail,
        "visibility": visibility,
        "notes": notes,
    }

    return manifest


def write_manifest(manifest: dict, output_dir: Path) -> Path:
    """Write manifest to the output directory. Returns the path."""
    path = Path(output_dir) / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    return path
