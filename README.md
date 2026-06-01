# AI Dependency Guard 🛡️

**AI Dependency Guard** is a GitHub Action that automatically scans your Pull Requests and commits to ensure no **LLM-hallucinated packages** enter your dependency tree.

Large Language Models (LLMs) often hallucinate fake packages when generating boilerplate code (e.g., `requirements.txt` or `package.json`). If these are committed to your repository, malicious actors can register those exact names on PyPI or npm, leading to a critical supply chain attack known as **Phantom Dependency Squatting**.

This action blocks the PR by failing the CI build if a package is 404 Not Found on PyPI or npm, OR if it matches a known defensively squatted package.

## Usage

Create a file in your repository `.github/workflows/ai-guard.yml`:

```yaml
name: AI Dependency Guard
on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Scan for Hallucinated Dependencies
        uses: fabriziosalmi/ai-dependency-guard@v1
        with:
          # Optional: Add your own custom malicious packages to block
          # Default includes top known hallucinations (keyrings, jaraco, google-colab, etc.)
          blocklist: 'my-custom-bad-package, another-one'
```

## How It Works (Two-Tier Detection)
1. **Blocklist Check (HTTP 200 Bypass Protection):** Checks packages against a blocklist of known actively squatted or defensively mitigated packages that would otherwise return HTTP 200 OK.
2. **Registry 404 Detection:** Verifies the existence of unknown packages directly against PyPI and npm public APIs. If it doesn't exist, it's vulnerable to squatting.

## Features
- 🐍 **PyPI Support**: Scans `requirements.txt`
- 📦 **NPM Support**: Scans `package.json`
- ⚡ **Zero Configuration**: Built-in default blocklist protects you out of the box.
