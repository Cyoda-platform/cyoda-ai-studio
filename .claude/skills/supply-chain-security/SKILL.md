---
name: supply-chain-security
description: Use this skill when implementing dependency lockfiles, vulnerability scanning, or supply chain security controls.
tags: [security, dependencies, supply-chain, lockfile, sbom, vulnerabilities]
---

# Supply Chain Security Skill

## Purpose
Guide for securing the software supply chain through dependency locking, hash verification, vulnerability scanning, and reproducible builds.

## When to Use This Skill
- Setting up dependency lockfiles
- Implementing hash verification
- Adding vulnerability scanning (pip-audit, safety)
- Configuring Dependabot/Renovate
- Creating SBOMs (Software Bill of Materials)
- Investigating supply chain attacks
- Ensuring reproducible builds

---

## The Problem: Zero Supply Chain Controls

### Current State (HIGH RISK - 1.6/5)

**No Lockfile:**
- 25 direct dependencies declared
- 108 transitive dependencies **uncontrolled**
- Every `pip install` resolves fresh from PyPI
- Two builds minutes apart can differ

**No Hash Verification:**
- No `--require-hashes` anywhere
- PyPI MITM would go undetected
- Compromised package would be pulled silently

**No Vulnerability Scanning:**
- No pip-audit or safety checks
- Stale CVEs go unnoticed
- No Dependabot or Renovate

**Result:** Any of 134 packages could be compromised and pulled automatically into all environments.

---

## Solution 1: Generate Lockfile with Hashes (P0 - IMMEDIATE)

### Option A: Using uv (Recommended - Fast)

```bash
# Install uv
pip install uv

# Generate lockfile from pyproject.toml
uv lock

# Output: uv.lock (includes all transitive deps with hashes)
```

**Benefits:**
- ⚡ Fast (Rust-based)
- 🔒 Secure by default (hashes included)
- 📦 Handles complex dependency resolution
- 🔄 Compatible with pip

### Option B: Using pip-tools (Traditional)

```bash
# Install pip-tools
pip install pip-tools

# Generate lockfile with hashes
pip-compile pyproject.toml \
  -o requirements.lock \
  --generate-hashes \
  --resolver=backtracking \
  --strip-extras

# Output: requirements.lock
```

**Example lockfile entry:**
```
aiofiles==24.1.0 \
    --hash=sha256:22a075c9e5a3810f0c2e48f3008c94d68c65d763b9b03857924c99e57355166c \
    --hash=sha256:b4ec55f4195e3eb5d7abd1bf7e061763e864dd4954231fb8539a0ef8bb8260e5
    # via -r pyproject.toml
```

### Commit the Lockfile

```bash
# Add to version control
git add requirements.lock  # or uv.lock
git commit -m "Add dependency lockfile with hashes

- Locks all 134 dependencies (25 direct + 108 transitive)
- Includes SHA256 hashes for integrity verification
- Ensures reproducible builds across all environments"
```

---

## Solution 2: Use Lockfile in Dockerfile (P0)

### Before (INSECURE)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

# ❌ PROBLEM: Resolves fresh from PyPI every build
RUN pip install --upgrade pip && \
    pip install -e .
```

### After (SECURE)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy only lockfile first (layer caching)
COPY requirements.lock .

# Install with hash verification
RUN pip install --upgrade pip && \
    pip install --require-hashes -r requirements.lock

# Copy rest of application
COPY . .

# Install in editable mode (already satisfied from lockfile)
RUN pip install -e . --no-deps

# Verify no unexpected packages
RUN pip check
```

**Benefits:**
- ✅ Reproducible: Same lockfile = identical dependencies
- ✅ Integrity: Hash verification detects tampering
- ✅ Fast: Layer caching when lockfile unchanged
- ✅ Secure: `--no-deps` prevents surprise additions

---

## Solution 3: Use Lockfile in CI (P0)

### Before (INSECURE)

```yaml
# .github/workflows/ci-cd.yml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -e .  # ❌ Resolves fresh, no hashes
```

### After (SECURE)

```yaml
# .github/workflows/ci-cd.yml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install --require-hashes -r requirements.lock

- name: Install package in editable mode
  run: pip install -e . --no-deps

- name: Verify installation integrity
  run: pip check
```

---

## Solution 4: Add Vulnerability Scanning (P0)

### Add pip-audit as Blocking CI Step

```yaml
# .github/workflows/ci-cd.yml
- name: Audit dependencies for known vulnerabilities
  run: |
    pip install pip-audit
    pip-audit --require-hashes -r requirements.lock --desc

# Alternative: Use action
- name: Audit dependencies
  uses: pypa/gh-action-pip-audit@v1.0.8
  with:
    inputs: requirements.lock
    require-hashes: true
```

**What pip-audit checks:**
- Known CVEs from PyPI Advisory Database
- OSV (Open Source Vulnerabilities) database
- GitHub Security Advisories

**Example output:**
```
Found 2 known vulnerabilities in 2 packages
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Name        ┃ Version     ┃ ID         ┃ Fix         ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ cryptography│ 41.0.0      │ CVE-2023-X │ >=41.0.5    │
│ urllib3     │ 1.26.0      │ CVE-2023-Y │ >=1.26.18   │
└─────────────┴─────────────┴────────────┴─────────────┘
```

### Alternative: safety check

```yaml
- name: Security check with safety
  run: |
    pip install safety
    safety check --json --file requirements.lock
```

---

## Solution 5: Configure Dependabot (P1)

### Create .github/dependabot.yml

```yaml
version: 2
updates:
  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    reviewers:
      - "security-team"
    labels:
      - "dependencies"
      - "security"
    # Group minor/patch updates together
    groups:
      development-dependencies:
        patterns:
          - "pytest*"
          - "black"
          - "isort"
          - "mypy"
          - "flake8"

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "github-actions"
      - "dependencies"

  # Docker base images
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "docker"
      - "dependencies"
```

**Dependabot will:**
- Check for updates weekly
- Open PRs for security updates immediately
- Run your CI tests against updates
- Support auto-merge for trusted updates

---

## Solution 6: Pin Docker Infrastructure Images (P1)

### Before (NON-REPRODUCIBLE)

```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus:latest  # ❌ Changes unpredictably
  grafana:
    image: grafana/grafana:latest  # ❌ Changes unpredictably
```

### After (REPRODUCIBLE)

```yaml
# docker-compose.yml
services:
  prometheus:
    # Pin to specific version (and optionally digest)
    image: prom/prometheus:v2.53.0
    # Or with digest for maximum security:
    # image: prom/prometheus:v2.53.0@sha256:abc123...

  grafana:
    image: grafana/grafana:11.1.0

  jaeger:
    image: jaegertracing/all-in-one:1.60.0

  loki:
    image: grafana/loki:3.1.0

  promtail:
    image: grafana/promtail:3.1.0
```

**Finding digests:**
```bash
# Get image digest
docker pull prom/prometheus:v2.53.0
docker inspect prom/prometheus:v2.53.0 --format='{{.RepoDigests}}'

# Output: prom/prometheus@sha256:abc123def456...
```

---

## Solution 7: Add Upper Bounds on Critical Dependencies (P1)

### Update pyproject.toml

```toml
dependencies = [
    # Security-critical: Add upper bound
    "grpcio>=1.64.1,<2",           # Major version ceiling
    "protobuf>=5.29.5,<7",         # Prevent silent major jump
    "cryptography>=46.0,<47",      # Crypto changes carefully
    "starlette>=0.49.1,<1",        # Prevent 1.0 surprise

    # High-churn but stable APIs: Allow major updates
    "pydantic>=2.12.3,<3",
    "httpx>=0.28.1,<1",

    # Internal/stable: Can be more relaxed
    "aiofiles>=24.1.0",
    "python-dotenv>=1.1.1",
]
```

**Strategy:**
- Security-critical libs: Tight bounds (minor versions)
- Stable APIs: Major version ceiling
- Internal/low-risk: Loose bounds (easier updates)

---

## Solution 8: Generate SBOM in CI (P2)

### What is SBOM?

**Software Bill of Materials** - Complete inventory of:
- All dependencies (direct + transitive)
- Versions
- Licenses
- Hashes
- Relationships

**Why needed:**
- Compliance (Executive Order 14028)
- Incident response (which systems affected?)
- License auditing
- Transparency

### Option A: CycloneDX

```yaml
# .github/workflows/ci-cd.yml
- name: Generate SBOM
  run: |
    pip install cyclonedx-bom
    cyclonedx-py environment -o sbom.json --format json

- name: Upload SBOM artifact
  uses: actions/upload-artifact@v4
  with:
    name: sbom
    path: sbom.json
```

### Option B: Syft

```yaml
- name: Generate SBOM with Syft
  uses: anchore/sbom-action@v0
  with:
    path: .
    format: spdx-json
    output-file: sbom.spdx.json
```

**Example SBOM entry:**
```json
{
  "bomFormat": "CycloneDX",
  "components": [
    {
      "type": "library",
      "name": "cryptography",
      "version": "46.0.5",
      "purl": "pkg:pypi/cryptography@46.0.5",
      "hashes": [
        {"alg": "SHA-256", "content": "abc123..."}
      ]
    }
  ]
}
```

---

## Solution 9: Make CI Checks Blocking (P2)

### Before (NON-BLOCKING)

```yaml
# All failures silently swallowed
- name: Run Black
  run: black --check . || echo "⚠️ Black formatting issues"

- name: Run Bandit
  run: bandit -r . || echo "⚠️ Security issues found"
```

### After (BLOCKING)

```yaml
- name: Run Black
  run: black --check .
  # No || echo - failure stops pipeline

- name: Run Bandit
  run: bandit -r . -ll  # Only high/medium severity
  # Failure blocks merge

- name: Audit dependencies
  run: pip-audit -r requirements.lock
  # Vulnerability blocks merge
```

**Configure required checks in GitHub:**
```
Settings → Branches → Branch protection rules
✅ Require status checks to pass before merging
  ✅ black
  ✅ bandit
  ✅ pip-audit
  ✅ pytest
```

---

## Solution 10: Pin GitHub Actions to SHA (P2)

### Before (TAG-BASED)

```yaml
steps:
  - uses: actions/checkout@v4  # Tag can be moved
  - uses: actions/setup-python@v4
```

### After (SHA-PINNED)

```yaml
steps:
  # Pin to commit SHA (immutable)
  - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
  - uses: actions/setup-python@0ae58b7b623c3fbc54c52e4c8e6b2e8f3f6e7c6d  # v5.1.0
```

**Finding SHAs:**
```bash
# Visit GitHub action repo
# https://github.com/actions/checkout/releases
# Copy full commit SHA from tag

# Or use gh cli:
gh api repos/actions/checkout/git/ref/tags/v4.1.1 --jq .object.sha
```

**Dependabot will update SHAs:**
With `dependabot.yml` configured for `github-actions`, Dependabot will:
- Detect new versions
- Update SHAs automatically
- Open PRs with changelog

---

## Attack Scenarios Prevented

| Attack | Before | After |
|--------|--------|-------|
| **Compromised PyPI package** | ❌ Pulled automatically | ✅ Blocked by hash mismatch |
| **Dependency confusion** | ❌ No detection | ✅ Lockfile pins known-good versions |
| **Typosquatting** | ❌ Could be installed | ✅ Lockfile prevents new packages |
| **Build divergence** | ❌ Prod ≠ CI ≠ local | ✅ All use same lockfile |
| **Stale CVE** | ❌ Goes unnoticed | ✅ pip-audit blocks CI |
| **GitHub Action compromise** | ⚠️ Tag can move | ✅ SHA is immutable |

---

## Workflow: Updating Dependencies

### Regular Update (No Security Issue)

```bash
# 1. Update pyproject.toml (if adding/removing dep)
vim pyproject.toml

# 2. Regenerate lockfile
uv lock
# or: pip-compile pyproject.toml -o requirements.lock --generate-hashes

# 3. Test locally
pip install --require-hashes -r requirements.lock
pytest

# 4. Commit
git add pyproject.toml requirements.lock
git commit -m "Update dependencies"

# 5. CI runs pip-audit automatically
git push
```

### Security Update (CVE Found)

```bash
# 1. pip-audit identifies CVE
pip-audit -r requirements.lock
# Found 1 known vulnerability in cryptography

# 2. Update constraint in pyproject.toml
# cryptography>=46.0.5  →  cryptography>=46.0.6

# 3. Regenerate lockfile
uv lock

# 4. Verify fix
pip-audit -r requirements.lock
# No known vulnerabilities found

# 5. Commit and deploy immediately
git add pyproject.toml requirements.lock
git commit -m "Security: Update cryptography to fix CVE-2024-XXXX"
git push
```

### Dependabot PR Workflow

```bash
# 1. Dependabot opens PR
#    "Bump cryptography from 46.0.5 to 46.0.6"

# 2. CI runs automatically:
#    - pip-audit (no vulnerabilities)
#    - pytest (all tests pass)
#    - black, isort, mypy (quality checks)

# 3. Review changes
#    - Check changelog
#    - Verify breaking changes

# 4. Merge or enable auto-merge
#    Settings → Enable auto-merge for security updates
```

---

## Monitoring & Alerts

### Prometheus Metrics

```python
# application/services/metrics/dependency_metrics.py

from prometheus_client import Gauge

dependency_vulnerabilities = Gauge(
    'dependency_vulnerabilities_total',
    'Number of known vulnerabilities in dependencies'
)

dependency_age_days = Gauge(
    'dependency_age_days',
    'Age of oldest dependency in days',
    ['package']
)

# Update in scheduled job
async def update_dependency_metrics():
    # Run pip-audit
    result = subprocess.run(
        ["pip-audit", "-r", "requirements.lock", "--format", "json"],
        capture_output=True
    )
    data = json.loads(result.stdout)

    dependency_vulnerabilities.set(len(data.get("vulnerabilities", [])))
```

### Grafana Dashboard

```yaml
# dashboards/supply-chain.json
{
  "title": "Supply Chain Security",
  "panels": [
    {
      "title": "Known Vulnerabilities",
      "targets": [{
        "expr": "dependency_vulnerabilities_total"
      }],
      "alert": {
        "conditions": [{"evaluator": {"params": [0], "type": "gt"}}],
        "message": "Dependencies have known vulnerabilities!"
      }
    }
  ]
}
```

### Slack Alerts

```yaml
# .github/workflows/security-scan.yml
name: Weekly Security Scan
on:
  schedule:
    - cron: "0 9 * * 1"  # Every Monday 9am

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Audit dependencies
        run: |
          pip install pip-audit
          pip-audit -r requirements.lock --format json > audit.json

      - name: Send to Slack if vulnerabilities found
        if: failure()
        uses: slackapi/slack-github-action@v1.26.0
        with:
          webhook-url: ${{ secrets.SLACK_WEBHOOK }}
          payload: |
            {
              "text": "⚠️ Security vulnerabilities found in dependencies!",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*cyoda-ai-studio* has vulnerable dependencies.\nReview: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
                  }
                }
              ]
            }
```

---

## Best Practices

### 1. Defense in Depth

```
Layer 1: Lockfile with hashes        → Reproducibility
Layer 2: Hash verification           → Integrity
Layer 3: Vulnerability scanning      → Known CVEs
Layer 4: Dependabot automation       → Timely updates
Layer 5: SBOM generation             → Transparency
Layer 6: Monitoring & alerts         → Continuous awareness
```

### 2. Update Cadence

| Update Type | Frequency | Automation |
|-------------|-----------|------------|
| **Security patches** | Immediate | Auto-merge |
| **Minor updates** | Weekly | Dependabot PR |
| **Major updates** | Quarterly | Manual review |
| **Dev dependencies** | Bi-weekly | Grouped PRs |

### 3. Review Process

**Security Updates (auto-merge):**
- ✅ CI passes
- ✅ pip-audit clean
- ✅ No breaking changes in changelog
- 🤖 Auto-merge enabled

**Regular Updates (manual review):**
- ✅ Review changelog for breaking changes
- ✅ Check deprecation warnings
- ✅ Run full test suite
- 👤 Manual merge

**Major Updates (careful review):**
- ✅ Create feature branch
- ✅ Update code for breaking changes
- ✅ Run extended testing
- ✅ Update documentation
- 👤 Manual merge after review

### 4. Incident Response

**If compromised package detected:**

```bash
# 1. Immediately revert to last known-good lockfile
git revert HEAD
git push --force-with-lease

# 2. Audit all deployments
kubectl get pods -o jsonpath='{.items[*].spec.containers[*].image}'

# 3. Check logs for suspicious activity
grep -r "package-name" /var/log/

# 4. Regenerate lockfile excluding bad version
# In pyproject.toml: "package-name>=1.2.3,!=1.2.4,<2"
uv lock

# 5. Redeploy with clean lockfile
kubectl rollout restart deployment/cyoda-ai-studio

# 6. Post-incident review
# - How was compromise detected?
# - What data was accessed?
# - Update detection mechanisms
```

---

## Checklist: Supply Chain Hardening

### P0 (Immediate - This Week)
- [ ] Generate lockfile with hashes (`uv lock` or `pip-compile`)
- [ ] Update Dockerfile to use `--require-hashes`
- [ ] Update CI to use lockfile
- [ ] Add `pip-audit` as blocking CI step
- [ ] Commit lockfile to version control

### P1 (This Sprint)
- [ ] Create `.github/dependabot.yml`
- [ ] Pin Docker infrastructure images in `docker-compose.yml`
- [ ] Add upper-bound constraints on critical dependencies
- [ ] Enable Dependabot security updates

### P2 (Next Sprint)
- [ ] Generate SBOM in CI pipeline
- [ ] Make all CI quality checks blocking (remove `|| echo`)
- [ ] Pin GitHub Actions to commit SHA
- [ ] Set up Grafana dashboard for dependency metrics
- [ ] Configure Slack alerts for vulnerabilities

### P3 (Continuous)
- [ ] Weekly review of Dependabot PRs
- [ ] Monthly audit of transitive dependencies
- [ ] Quarterly major version updates
- [ ] Annual supply chain security review

---

## Troubleshooting

### Issue: Lockfile Generation Fails

```bash
# Error: "Could not find a version that matches..."

# Solution 1: Check for conflicting constraints
grep -r "package-name" pyproject.toml

# Solution 2: Relax overly strict constraints
# Change: "package>=1.2.3,<1.2.4"
# To: "package>=1.2.3,<1.3"

# Solution 3: Update pip-tools
pip install --upgrade pip-tools
```

### Issue: Hash Mismatch on Install

```bash
# Error: "Hash mismatch for package-name"

# Cause: PyPI package was updated without version bump (rare but possible)

# Solution: Regenerate lockfile
uv lock --upgrade-package package-name

# Or with pip-compile:
pip-compile --upgrade-package package-name
```

### Issue: pip-audit Blocks CI with False Positive

```bash
# Temporary bypass (not recommended):
pip-audit --ignore-vuln PYSEC-2024-XXX

# Better: Add to pyproject.toml:
[tool.pip-audit]
ignore-vulns = ["PYSEC-2024-XXX"]

# Best: Update dependency if possible
```

---

## Reference Files

- `pyproject.toml` - Dependency declarations
- `requirements.lock` or `uv.lock` - Lockfile with hashes
- `.github/dependabot.yml` - Automated updates
- `.github/workflows/security-scan.yml` - Vulnerability scanning
- `docker-compose.yml` - Infrastructure image versions

---

## External Resources

- [SLSA Supply Chain Framework](https://slsa.dev/)
- [pip-audit Documentation](https://github.com/pypa/pip-audit)
- [uv Package Manager](https://github.com/astral-sh/uv)
- [pip-tools (pip-compile)](https://github.com/jazzband/pip-tools)
- [Dependabot Configuration](https://docs.github.com/en/code-security/dependabot)
- [CycloneDX SBOM Standard](https://cyclonedx.org/)
- [OWASP Dependency-Check](https://owasp.org/www-project-dependency-check/)

---

**Last Updated:** 2026-04-28
**Risk Level:** HIGH (1.6/5) → Target: LOW (4.5/5) after P0-P1
**Next Review:** After lockfile implementation
