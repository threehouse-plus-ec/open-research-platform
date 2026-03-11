"""
Atlas Generator: Pre-computed parameter space for the Launch Lab.

Runs a multi-dimensional sweep across key rocket parameters and stores
the results as a compact JSON atlas. The Launch Lab loads this on startup
and uses nearest-neighbour lookup to show pre-computed results instantly.

Atlas dimensions (with m0=5000, massFlow=50 fixed):
- angle:    20–85°     (20 points)
- vExhaust: 1000–4500  (12 points)
- mFuel:    1000–4000  (8 points)
- cD:       0.05–0.50  (6 points)
- T_ground: 250–310    (5 points)

Total: 20 × 12 × 8 × 6 × 5 = 57,600 simulations
Output: ~700 KB JSON atlas
"""

import json
import math
import time
from pathlib import Path

# Import ISA model and simulator from rocket_scan
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.jobs.rocket_scan.run import simulate_trajectory


def linspace(lo, hi, n):
    """Generate n evenly spaced values from lo to hi inclusive."""
    if n == 1:
        return [lo]
    return [lo + i * (hi - lo) / (n - 1) for i in range(n)]


def run(config: dict, output_dir: Path):
    """Generate the parameter atlas."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Atlas grid definition
    angles = linspace(
        config.get("angle_min", 20),
        config.get("angle_max", 85),
        config.get("n_angle", 20),
    )
    v_exhausts = linspace(
        config.get("vEx_min", 1000),
        config.get("vEx_max", 4500),
        config.get("n_vEx", 12),
    )
    m_fuels = linspace(
        config.get("mFuel_min", 1000),
        config.get("mFuel_max", 4000),
        config.get("n_mFuel", 8),
    )
    c_ds = linspace(
        config.get("cD_min", 0.05),
        config.get("cD_max", 0.50),
        config.get("n_cD", 6),
    )
    t_grounds = linspace(
        config.get("tG_min", 250),
        config.get("tG_max", 310),
        config.get("n_tG", 5),
    )

    # Fixed parameters
    m_0 = config.get("m_0", 5000.0)
    mass_flow = config.get("mass_flow", 50.0)

    total = len(angles) * len(v_exhausts) * len(m_fuels) * len(c_ds) * len(t_grounds)
    print(f"Atlas: {total} simulations across {len(angles)}×{len(v_exhausts)}×{len(m_fuels)}×{len(c_ds)}×{len(t_grounds)} grid")

    t0 = time.time()

    # Results stored as flat array: [range_m, maxAlt_m, maxSpeed, flightTime, impactSpeed]
    # Index order: angle (fastest) → vExhaust → mFuel → cD → T_ground (slowest)
    data = []
    count = 0

    for tg in t_grounds:
        for cd in c_ds:
            for mf in m_fuels:
                for ve in v_exhausts:
                    for angle in angles:
                        r = simulate_trajectory(
                            launch_angle_deg=angle,
                            v_exhaust=ve,
                            mass_flow=mass_flow,
                            m_0=m_0,
                            m_fuel=mf,
                            C_D=cd,
                            T_ground=tg,
                        )
                        data.extend([
                            round(r["range_m"], 1),
                            round(r["max_altitude_m"], 1),
                            round(r["max_speed_ms"], 1),
                            round(r["flight_time_s"], 1),
                            round(r["impact_speed_ms"], 1),
                        ])
                        count += 1
                        if count % 5000 == 0:
                            elapsed = time.time() - t0
                            rate = count / elapsed
                            eta = (total - count) / rate
                            print(f"  {count}/{total} ({count/total*100:.0f}%) — {rate:.0f} sim/s — ETA {eta:.0f}s")

    elapsed = time.time() - t0
    print(f"Atlas complete: {total} simulations in {elapsed:.1f}s ({total/elapsed:.0f} sim/s)")

    # Atlas schema
    atlas = {
        "version": "1.0.0",
        "description": "Pre-computed rocket trajectory parameter atlas",
        "atmosphere": "ISA (altitude-dependent density)",
        "fixed": {
            "m_0": m_0,
            "mass_flow": mass_flow,
        },
        "axes": {
            "angle":    {"min": angles[0], "max": angles[-1], "n": len(angles), "values": [round(a, 2) for a in angles]},
            "vExhaust": {"min": v_exhausts[0], "max": v_exhausts[-1], "n": len(v_exhausts), "values": [round(v, 1) for v in v_exhausts]},
            "mFuel":    {"min": m_fuels[0], "max": m_fuels[-1], "n": len(m_fuels), "values": [round(m, 1) for m in m_fuels]},
            "cD":       {"min": c_ds[0], "max": c_ds[-1], "n": len(c_ds), "values": [round(c, 4) for c in c_ds]},
            "T_ground": {"min": t_grounds[0], "max": t_grounds[-1], "n": len(t_grounds), "values": [round(t, 1) for t in t_grounds]},
        },
        "metrics": ["range_m", "maxAlt_m", "maxSpeed_ms", "flightTime_s", "impactSpeed_ms"],
        "metrics_per_point": 5,
        "index_order": ["T_ground", "cD", "mFuel", "vExhaust", "angle"],
        "total_points": total,
        "data": data,
    }

    # Write atlas
    atlas_path = output_dir / "atlas.json"
    with open(atlas_path, "w") as f:
        json.dump(atlas, f, separators=(',', ':'))  # compact

    size_kb = atlas_path.stat().st_size / 1024
    print(f"Atlas written: {atlas_path} ({size_kb:.0f} KB)")

    # Summary
    summary = {
        "job": "atlas_gen",
        "total_simulations": total,
        "compute_time_s": round(elapsed, 1),
        "atlas_size_kb": round(size_kb, 1),
        "grid_shape": {
            "angle": len(angles),
            "vExhaust": len(v_exhausts),
            "mFuel": len(m_fuels),
            "cD": len(c_ds),
            "T_ground": len(t_grounds),
        },
        "atmosphere": "ISA",
    }
    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
