# Architecture

For the full architectural blueprint, see the [Open Research Platform Blueprint (v0.2.0)](../open-research-platform-blueprint-v2.md).

## Summary

The platform is organised into four layers:

1. **Repository of Record** — source code, configurations, workflow definitions, promoted manifests, and documentation. This is the authoritative history; everything else is replaceable.

2. **Execution Plane** — GitHub Actions runners (hosted or self-hosted) executing jobs inside Docker containers. The execution plane pulls from the repository, runs jobs, and writes outputs to the data layer.

3. **Data Products** — three retention classes (ephemeral, curated, published) connected by two gates (validation gate, publication gate). Every run produces a manifest — the atomic unit of provenance.

4. **Publication Layer** (optional) — a static dashboard served via GitHub Pages. Reads only from `data/published/`. Can be disabled entirely; the platform functions without it.

## Key invariants

- The Dockerfile is the canonical environment definition.
- Every completed run produces exactly one manifest.
- Published runs are append-forbidden; corrections via supersession only.
- The dashboard never reads from live computation directories.
- The manifest schema (v2.0.0) is stable across all scaling stages.
