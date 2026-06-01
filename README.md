# AI Dependency Guard

## Overview
AI Dependency Guard is an automated, zero-dependency GitHub Action designed to mitigate the risk of *Phantom Dependency Squatting* within Continuous Integration pipelines. 

Large Language Models (LLMs) utilized for code generation frequently hallucinate non-existent dependencies within production manifests (e.g., `requirements.txt` and `package.json`). If these fabricated namespaces are committed to a version control system, the repository becomes vulnerable to supply chain attacks. Threat actors can register these hallucinated names on public registries, resulting in arbitrary code execution during subsequent downstream builds.

This action parses dependency manifests during the Pull Request or push phases and performs real-time validation against the official PyPI and npm APIs. The CI pipeline will fail deterministically if a hallucinated dependency is detected.

## Two-Tier Evaluation Architecture

The action employs a dual-validation mechanism to ensure comprehensive protection:

1. **Tier 1 (Explicit Blocklist / HTTP 200 Bypass Mitigation):** 
   If a hallucinated package has already been maliciously or defensively squatted, the public registry will return an `HTTP 200 OK` status, bypassing naive 404-checkers. This action evaluates every extracted dependency against an explicit blocklist of known hijacked or defensively squatted namespaces prior to executing network requests.
   
2. **Tier 2 (Real-Time API Validation / HTTP 404 Detection):** 
   Dependencies not intercepted by the Tier 1 blocklist are queried against the official PyPI and npm JSON APIs. If the registry returns an `HTTP 404 Not Found` response, the dependency is flagged as an active hallucination risk.

## Usage Instructions

To integrate AI Dependency Guard into your CI/CD pipeline, create a workflow file (e.g., `.github/workflows/ai-guard.yml`) with the following configuration:

```yaml
name: AI Dependency Guard Validation
on: [push, pull_request]

jobs:
  validate-dependencies:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        
      - name: Execute AI Dependency Guard
        uses: fabriziosalmi/ai-dependency-guard@v1
        with:
          # Optional: Define the root directory for manifest scanning.
          scan_path: '.'
          
          # Optional: Append custom namespaces to the explicit blocklist.
          # The default implementation includes empirical top-tier hallucinated packages.
          blocklist: 'keyrings,jaraco,google-colab,ruamel,en_core_web_sm'
```

## Technical Specifications
- **Supported Manifests:** `requirements.txt` (Python/PyPI), `package.json` (Node.js/npm).
- **Network Constraints:** The action utilizes standard HTTP libraries and incorporates deliberate timing delays (100ms) between API requests to strictly adhere to registry rate-limiting policies.
- **Fail-Open Posture:** In the event of a registry network timeout or HTTP 5xx error, the action will default to an `HTTP 200` assumption to prevent blocking the CI pipeline due to infrastructure instability.
