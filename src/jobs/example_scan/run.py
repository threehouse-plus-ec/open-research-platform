"""
Example job: Damped harmonic oscillator parameter scan.

Scans damping ratio ζ across a range and records the transient response
characteristics (settling time, overshoot, final amplitude).

This is a toy numerical job to demonstrate the platform pipeline.
Replace it with your actual research code.
"""

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path


def simulate_damped_oscillator(
    zeta: float,
    omega_n: float = 1.0,
    t_max: float = 30.0,
    dt: float = 0.01,
) -> dict:
    """Simulate a damped harmonic oscillator and extract characteristics.

    x'' + 2ζω_n x' + ω_n² x = 0, with x(0) = 1, x'(0) = 0.

    Returns dict with settling_time, peak_overshoot, final_amplitude.
    """
    omega_d = omega_n * math.sqrt(abs(1 - zeta**2)) if abs(zeta) < 1 else 0

    steps = int(t_max / dt)
    x, v = 1.0, 0.0
    peak = x
    settling_time = t_max

    for i in range(steps):
        t = i * dt
        # Euler integration (adequate for a demo)
        a = -2 * zeta * omega_n * v - omega_n**2 * x
        v += a * dt
        x += v * dt

        if abs(x) > abs(peak):
            peak = x

        # Settling time: last time |x| > 2% of initial
        if abs(x) > 0.02:
            settling_time = t

    return {
        "zeta": round(zeta, 4),
        "settling_time": round(settling_time, 4),
        "peak_overshoot": round(abs(peak) - 1.0, 6),
        "final_amplitude": round(abs(x), 6),
    }


def load_config(config_path: Path) -> dict:
    """Load job configuration."""
    with open(config_path) as f:
        return json.load(f)


def run(config: dict, output_dir: Path):
    """Execute the parameter scan."""
    output_dir.mkdir(parents=True, exist_ok=True)

    zeta_min = config.get("zeta_min", 0.01)
    zeta_max = config.get("zeta_max", 2.0)
    steps = config.get("steps", 50)
    omega_n = config.get("omega_n", 1.0)

    # Generate scan points
    zetas = [zeta_min + i * (zeta_max - zeta_min) / (steps - 1) for i in range(steps)]

    # Run simulations
    results = []
    for zeta in zetas:
        result = simulate_damped_oscillator(zeta=zeta, omega_n=omega_n)
        results.append(result)

    # Write CSV
    csv_path = output_dir / "results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["zeta", "settling_time", "peak_overshoot", "final_amplitude"])
        writer.writeheader()
        writer.writerows(results)

    # Write summary JSON
    summary = {
        "job": "example_scan",
        "parameter_range": {"zeta_min": zeta_min, "zeta_max": zeta_max, "steps": steps},
        "critical_damping_zeta": 1.0,
        "min_settling_time": min(r["settling_time"] for r in results),
        "optimal_zeta": min(results, key=lambda r: r["settling_time"])["zeta"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = output_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Scan complete: {steps} points, results in {output_dir}")
    return results


def main():
    """CLI entry point."""
    # Default config
    config_path = Path("src/jobs/example_scan/config.json")
    if config_path.exists():
        config = load_config(config_path)
    else:
        config = {"zeta_min": 0.01, "zeta_max": 2.0, "steps": 50, "omega_n": 1.0}

    # Output to ephemeral by default; the workflow will set this
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/ephemeral/current_run")

    run(config, output_dir)


if __name__ == "__main__":
    main()
