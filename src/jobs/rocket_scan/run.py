"""
Rocket Science: Single-stage rocket trajectory parameter scan.

Simulates 2D rocket trajectories under constant thrust, gravity, and
quadratic drag, scanning across launch angles. Produces trajectory data,
performance metrics, and an SVG trajectory plot.

Physics:
    m(t) = m_0 - ṁt                   (mass decreases during burn)
    F_thrust = v_e × ṁ                 (thrust from exhaust velocity × mass flow)
    F_drag = ½ ρ C_D A v²              (quadratic drag)
    F_gravity = m(t) × g               (constant gravity, flat Earth approx.)

This is a toy model — good enough to produce visually compelling results
and demonstrate the platform pipeline.
"""

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def isa_density(h: float, T_ground: float = 288.15) -> float:
    """International Standard Atmosphere density model.

    Troposphere (0–11 km): linear temperature lapse, power-law density.
    Stratosphere (11–25 km): isothermal, exponential density.
    Above 25 km: returns near-zero (negligible drag).

    Args:
        h: altitude in metres (clamped to >= 0)
        T_ground: ground-level temperature in Kelvin (default 288.15 K = 15°C)

    Returns:
        air density in kg/m³
    """
    if h < 0:
        h = 0

    g = 9.81
    R = 287.058        # specific gas constant for dry air [J/(kg·K)]
    rho_0 = 1.225      # sea-level density at 288.15 K [kg/m³]
    L = 0.0065         # temperature lapse rate [K/m]
    T_0 = 288.15       # ISA standard ground temperature [K]
    h_tropo = 11000.0  # tropopause altitude [m]

    # Scale rho_0 for non-standard ground temperature
    # Ideal gas: rho ∝ 1/T at constant pressure
    rho_ground = rho_0 * (T_0 / T_ground)

    if h <= h_tropo:
        T = T_ground - L * h
        if T < 1.0:
            return 0.0
        exponent = g / (L * R) - 1.0  # ≈ 4.256 at standard conditions
        return rho_ground * (T / T_ground) ** exponent
    elif h <= 25000.0:
        # Density at tropopause
        T_tropo = T_ground - L * h_tropo
        if T_tropo < 1.0:
            return 0.0
        exponent = g / (L * R) - 1.0
        rho_tropo = rho_ground * (T_tropo / T_ground) ** exponent
        # Isothermal stratosphere
        return rho_tropo * math.exp(-g * (h - h_tropo) / (R * T_tropo))
    else:
        return 0.0


def simulate_trajectory(
    launch_angle_deg: float,
    v_exhaust: float = 2500.0,       # exhaust velocity [m/s]
    mass_flow: float = 50.0,          # mass flow rate [kg/s]
    m_0: float = 5000.0,             # initial mass [kg]
    m_fuel: float = 3000.0,          # fuel mass [kg]
    C_D: float = 0.3,               # drag coefficient
    A: float = 1.0,                  # cross-section area [m²]
    rho: float = 1.225,             # sea-level air density [kg/m³] (unused, kept for API compat)
    T_ground: float = 288.15,       # ground temperature [K]
    g: float = 9.81,                # gravitational acceleration [m/s²]
    dt: float = 0.1,                # time step [s]
) -> dict:
    """Simulate a single rocket trajectory with altitude-dependent atmosphere.

    Uses the ISA (International Standard Atmosphere) model:
    - Troposphere (0–11 km): temperature decreases linearly, density follows power law
    - Stratosphere (11–25 km): isothermal, density decays exponentially
    - Above 25 km: negligible atmospheric density

    Returns dict with trajectory points and summary metrics.
    """
    angle = math.radians(launch_angle_deg)
    thrust = v_exhaust * mass_flow
    burn_time = m_fuel / mass_flow

    # State: position (x, y) and velocity (vx, vy)
    x, y = 0.0, 0.0
    vx = 0.0
    vy = 0.0
    t = 0.0
    m = m_0

    trajectory = []
    max_altitude = 0.0
    max_speed = 0.0
    max_accel = 0.0

    while y >= 0.0 or t < 0.5:  # run until ground impact (or at least 0.5s)
        v = math.sqrt(vx**2 + vy**2)
        max_speed = max(max_speed, v)

        trajectory.append({
            "t": round(t, 2),
            "x": round(x, 1),
            "y": round(y, 1),
            "vx": round(vx, 1),
            "vy": round(vy, 1),
            "v": round(v, 1),
            "m": round(m, 1),
        })

        # Forces
        # Thrust (only during burn, always along initial launch direction)
        if t < burn_time:
            Fx_thrust = thrust * math.cos(angle)
            Fy_thrust = thrust * math.sin(angle)
            m = m_0 - mass_flow * t
        else:
            Fx_thrust = 0.0
            Fy_thrust = 0.0
            m = m_0 - m_fuel

        # Drag (opposes velocity, altitude-dependent density)
        if v > 0.01:
            rho_local = isa_density(max(y, 0), T_ground)
            F_drag = 0.5 * rho_local * C_D * A * v**2
            Fx_drag = -F_drag * (vx / v)
            Fy_drag = -F_drag * (vy / v)
        else:
            Fx_drag = 0.0
            Fy_drag = 0.0

        # Gravity
        Fy_grav = -m * g

        # Acceleration
        ax = (Fx_thrust + Fx_drag) / m
        ay = (Fy_thrust + Fy_drag + Fy_grav) / m
        accel = math.sqrt(ax**2 + ay**2)
        max_accel = max(max_accel, accel)

        # Euler integration
        vx += ax * dt
        vy += ay * dt
        x += vx * dt
        y += vy * dt

        max_altitude = max(max_altitude, y)
        t += dt

        # Safety: stop after 600s or 500km range
        if t > 600 or abs(x) > 500000:
            break

        # Stop if we've returned to ground after launch
        if y < 0 and t > 1.0:
            # Interpolate to y=0
            if vy != 0:
                dt_back = -y / vy
                x += vx * dt_back
                y = 0.0
                t += dt_back
            trajectory.append({
                "t": round(t, 2),
                "x": round(x, 1),
                "y": 0.0,
                "vx": round(vx, 1),
                "vy": round(vy, 1),
                "v": round(math.sqrt(vx**2 + vy**2), 1),
                "m": round(m, 1),
            })
            break

    return {
        "launch_angle_deg": launch_angle_deg,
        "max_altitude_m": round(max_altitude, 1),
        "range_m": round(x, 1),
        "max_speed_ms": round(max_speed, 1),
        "max_accel_ms2": round(max_accel, 1),
        "flight_time_s": round(t, 2),
        "burn_time_s": round(burn_time, 2),
        "impact_speed_ms": round(math.sqrt(vx**2 + vy**2), 1),
        "trajectory": trajectory,
    }


def generate_svg(results: list[dict], width: int = 900, height: int = 500) -> str:
    """Generate an SVG trajectory plot from scan results."""

    # Find plot bounds
    all_x = [p["x"] for r in results for p in r["trajectory"]]
    all_y = [p["y"] for r in results for p in r["trajectory"]]
    x_max = max(all_x) * 1.05
    y_max = max(all_y) * 1.1
    if x_max < 100:
        x_max = 100
    if y_max < 100:
        y_max = 100

    margin = {"top": 40, "right": 30, "bottom": 60, "left": 70}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]

    def sx(val):
        return margin["left"] + (val / x_max) * plot_w

    def sy(val):
        return margin["top"] + plot_h - (val / y_max) * plot_h

    # Colour palette: warm amber through to cool blue
    n = len(results)
    colours = []
    for i in range(n):
        t = i / max(n - 1, 1)
        # Amber (#F59E0B) → Crimson (#DC2626) → Indigo (#4F46E5)
        if t < 0.5:
            s = t * 2
            r = int(245 * (1 - s) + 220 * s)
            g = int(158 * (1 - s) + 38 * s)
            b = int(11 * (1 - s) + 38 * s)
        else:
            s = (t - 0.5) * 2
            r = int(220 * (1 - s) + 79 * s)
            g = int(38 * (1 - s) + 70 * s)
            b = int(38 * (1 - s) + 229 * s)
        colours.append(f"rgb({r},{g},{b})")

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" ',
        f'  width="{width}" height="{height}" ',
        '  style="background:#0F172A; font-family: \'JetBrains Mono\', \'Fira Code\', monospace;">',
        '',
        '  <!-- Grid -->',
    ]

    # Grid lines
    for i in range(6):
        y_val = y_max * i / 5
        yp = sy(y_val)
        svg_lines.append(
            f'  <line x1="{margin["left"]}" y1="{yp:.1f}" x2="{width - margin["right"]}" y2="{yp:.1f}" '
            f'stroke="#1E293B" stroke-width="1"/>'
        )
        svg_lines.append(
            f'  <text x="{margin["left"] - 8}" y="{yp + 4:.1f}" text-anchor="end" '
            f'fill="#64748B" font-size="11">{y_val/1000:.0f}km</text>'
        )

    for i in range(6):
        x_val = x_max * i / 5
        xp = sx(x_val)
        svg_lines.append(
            f'  <line x1="{xp:.1f}" y1="{margin["top"]}" x2="{xp:.1f}" y2="{margin["top"] + plot_h}" '
            f'stroke="#1E293B" stroke-width="1"/>'
        )
        svg_lines.append(
            f'  <text x="{xp:.1f}" y="{margin["top"] + plot_h + 20}" text-anchor="middle" '
            f'fill="#64748B" font-size="11">{x_val/1000:.0f}km</text>'
        )

    # Axes
    svg_lines.append(
        f'  <line x1="{margin["left"]}" y1="{margin["top"] + plot_h}" '
        f'x2="{width - margin["right"]}" y2="{margin["top"] + plot_h}" stroke="#334155" stroke-width="2"/>'
    )
    svg_lines.append(
        f'  <line x1="{margin["left"]}" y1="{margin["top"]}" '
        f'x2="{margin["left"]}" y2="{margin["top"] + plot_h}" stroke="#334155" stroke-width="2"/>'
    )

    # Axis labels
    svg_lines.append(
        f'  <text x="{width / 2}" y="{height - 10}" text-anchor="middle" '
        f'fill="#94A3B8" font-size="13">Range</text>'
    )
    svg_lines.append(
        f'  <text x="16" y="{height / 2}" text-anchor="middle" '
        f'fill="#94A3B8" font-size="13" transform="rotate(-90 16 {height / 2})">Altitude</text>'
    )

    # Title
    svg_lines.append(
        f'  <text x="{margin["left"]}" y="24" fill="#F8FAFC" font-size="16" font-weight="bold">'
        'Trajectory Scan — Launch Angle Sweep</text>'
    )

    # Trajectories
    svg_lines.append('')
    svg_lines.append('  <!-- Trajectories -->')
    for i, result in enumerate(results):
        traj = result["trajectory"]
        if len(traj) < 2:
            continue

        points = " ".join(f"{sx(p['x']):.1f},{sy(p['y']):.1f}" for p in traj if p["y"] >= 0)
        angle = result["launch_angle_deg"]
        svg_lines.append(
            f'  <polyline points="{points}" fill="none" stroke="{colours[i]}" '
            f'stroke-width="1.8" stroke-linecap="round" opacity="0.85">'
            f'<title>{angle}°</title></polyline>'
        )

    # Legend (selected angles)
    legend_indices = [0, n // 4, n // 2, 3 * n // 4, n - 1]
    legend_indices = sorted(set(min(i, n - 1) for i in legend_indices))
    lx = width - margin["right"] - 90
    ly = margin["top"] + 10

    svg_lines.append('')
    svg_lines.append('  <!-- Legend -->')
    svg_lines.append(
        f'  <rect x="{lx - 10}" y="{ly - 5}" width="100" '
        f'height="{len(legend_indices) * 18 + 10}" rx="4" fill="#0F172A" fill-opacity="0.8" '
        f'stroke="#1E293B"/>'
    )
    for j, idx in enumerate(legend_indices):
        svg_lines.append(
            f'  <line x1="{lx}" y1="{ly + j * 18 + 9}" x2="{lx + 16}" y2="{ly + j * 18 + 9}" '
            f'stroke="{colours[idx]}" stroke-width="2.5"/>'
        )
        svg_lines.append(
            f'  <text x="{lx + 22}" y="{ly + j * 18 + 13}" fill="#CBD5E1" font-size="11">'
            f'{results[idx]["launch_angle_deg"]:.0f}°</text>'
        )

    svg_lines.append('</svg>')
    return "\n".join(svg_lines)


def run(config: dict, output_dir: Path):
    """Execute the launch angle parameter scan."""
    output_dir.mkdir(parents=True, exist_ok=True)

    angle_min = config.get("angle_min", 15.0)
    angle_max = config.get("angle_max", 85.0)
    steps = config.get("steps", 15)
    v_exhaust = config.get("v_exhaust", 2500.0)
    mass_flow = config.get("mass_flow", 50.0)
    m_0 = config.get("m_0", 5000.0)
    m_fuel = config.get("m_fuel", 3000.0)
    C_D = config.get("C_D", 0.3)
    T_ground = config.get("T_ground", 288.15)

    angles = [angle_min + i * (angle_max - angle_min) / max(steps - 1, 1) for i in range(steps)]

    results = []
    for angle in angles:
        result = simulate_trajectory(
            launch_angle_deg=angle,
            v_exhaust=v_exhaust,
            mass_flow=mass_flow,
            m_0=m_0,
            m_fuel=m_fuel,
            C_D=C_D,
            T_ground=T_ground,
        )
        results.append(result)

    # Write summary CSV (no trajectory points — those are large)
    csv_path = output_dir / "results.csv"
    fields = ["launch_angle_deg", "max_altitude_m", "range_m", "max_speed_ms",
              "max_accel_ms2", "flight_time_s", "burn_time_s", "impact_speed_ms"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r[k] for k in fields})

    # Write SVG trajectory plot
    svg_path = output_dir / "trajectories.svg"
    svg_content = generate_svg(results)
    with open(svg_path, "w") as f:
        f.write(svg_content)

    # Write summary JSON
    optimal_range = max(results, key=lambda r: r["range_m"])
    optimal_altitude = max(results, key=lambda r: r["max_altitude_m"])

    summary = {
        "job": "rocket_scan",
        "scan": {
            "parameter": "launch_angle_deg",
            "range": [angle_min, angle_max],
            "steps": steps,
        },
        "rocket": {
            "v_exhaust_ms": v_exhaust,
            "mass_flow_kgs": mass_flow,
            "initial_mass_kg": m_0,
            "fuel_mass_kg": m_fuel,
            "dry_mass_kg": m_0 - m_fuel,
            "thrust_N": v_exhaust * mass_flow,
            "burn_time_s": m_fuel / mass_flow,
            "TWR_initial": (v_exhaust * mass_flow) / (m_0 * 9.81),
            "C_D": C_D,
            "T_ground_K": T_ground,
            "atmosphere": "ISA (altitude-dependent)",
        },
        "optimal_range": {
            "angle_deg": optimal_range["launch_angle_deg"],
            "range_km": round(optimal_range["range_m"] / 1000, 2),
        },
        "optimal_altitude": {
            "angle_deg": optimal_altitude["launch_angle_deg"],
            "altitude_km": round(optimal_altitude["max_altitude_m"] / 1000, 2),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Rocket scan complete: {steps} trajectories, "
          f"optimal range {summary['optimal_range']['range_km']:.1f} km "
          f"at {summary['optimal_range']['angle_deg']:.0f}°")


if __name__ == "__main__":
    import sys
    config_path = Path("src/jobs/rocket_scan/config.json")
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/ephemeral/current_run")
    run(config, out)
