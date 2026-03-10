# Security

## Threat model

This platform is designed for **open research workflows** where the primary assets are code integrity, data provenance, and result authenticity. It is not designed to protect classified or commercially sensitive data.

### What is defended

- **Provenance integrity:** Manifests record commit hashes, environment digests, and output hashes. Tampering with published results requires modifying multiple independent records.
- **Execution isolation:** Jobs run inside containers built from a pinned Dockerfile. The container boundary limits the blast radius of buggy or malicious job code.
- **Publication control:** The two-gate model ensures only validated, explicitly approved runs reach the public dashboard.

### What is not defended (Stage 0–1)

- **Supply chain attacks on container base images:** The Dockerfile pins a base image tag but does not verify signatures. At Stage 2+, add digest pinning and SBOM generation.
- **Compromise of the GitHub account:** If an attacker gains write access to the repository, they can modify workflows, code, and published data. Use branch protection, signed commits, and 2FA.
- **Malicious job code from collaborators:** The platform does not sandbox untrusted code beyond the container boundary. Only grant write access to trusted collaborators.

## Access controls

| Layer | Access | Notes |
|-------|--------|-------|
| Repository (Layer 1) | GitHub permissions | Enable branch protection on `main`. Require PR reviews for Stage 2+. |
| Execution (Layer 2) | Authenticated runners only | Self-hosted runners should not be exposed to the public internet. |
| Data (Layer 3) | Write via workflows only | No manual writes to `data/published/`. |
| Dashboard (Layer 4) | Public read | No write access. No execution capability. |

## Secret management

- Never commit secrets to the repository.
- Use GitHub Secrets for API keys, tokens, and credentials.
- The `.env.example` file documents required environment variables without exposing values.

## Incident response

If you suspect a compromise:

1. Revoke self-hosted runner tokens (Settings → Actions → Runners).
2. Rotate any exposed secrets.
3. Review recent commits and workflow runs for unauthorised changes.
4. Check `data/published/` for unexpected modifications.

## Reporting

If you discover a security issue, please open a private security advisory on GitHub or contact the repository maintainer directly.
