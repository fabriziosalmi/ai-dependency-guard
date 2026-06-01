import os
import sys
import re
import json
import urllib.request
import urllib.error
import time
import argparse
import logging
import concurrent.futures
from typing import List, Tuple, Set

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

USER_AGENT = 'Mozilla/5.0 (AI-Dependency-Guard)'
DELAY_MS = 100

def check_registry(package_name: str, registry_type: str) -> bool:
    """
    Queries the public registry for package existence.
    Returns True if the package exists (or if HTTP 5xx/Timeout occurs to fail-open).
    Returns False ONLY if HTTP 404 is strictly returned.
    """
    if registry_type == "PyPI":
        url = f"https://pypi.org/pypi/{package_name}/json"
    else:
        url = f"https://registry.npmjs.org/{package_name}"
        
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        return True
    except Exception:
        # Fail-open posture for timeouts and transient network errors
        return True

def process_package(pkg: str, filepath: str, registry: str, blocklist: Set[str]) -> Tuple[str, str, str, str]:
    """
    Evaluates a single package against the Two-Tier architecture.
    Returns a tuple: (status, filepath, package_name, registry)
    status can be: 'ok', 'squatted', 'hallucinated'
    """
    pkg = pkg.strip().lower()
    if not pkg or pkg.startswith("-"):
        return ('ok', filepath, pkg, registry)
        
    # Tier 1: Blocklist Check
    if pkg in blocklist:
        return ('squatted', filepath, pkg, registry)
        
    # Tier 2: Real-time API Check
    time.sleep(DELAY_MS / 1000.0) # Rate limit respect per worker
    if not check_registry(pkg, registry):
        return ('hallucinated', filepath, pkg, registry)
        
    return ('ok', filepath, pkg, registry)

def parse_requirements(filepath: str) -> List[Tuple[str, str, str]]:
    """Extracts Python dependencies from a requirements.txt file."""
    packages = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                pkg = re.split(r'[=><~]', line)[0].strip()
                if pkg:
                    packages.append((pkg, filepath, "PyPI"))
    except Exception as e:
        logger.warning(f"::warning file={filepath}::Failed to parse requirements.txt: {e}")
    return packages

def parse_package_json(filepath: str) -> List[Tuple[str, str, str]]:
    """Extracts Node dependencies from a package.json file."""
    packages = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        deps = list(data.get("dependencies", {}).keys()) + list(data.get("devDependencies", {}).keys())
        for pkg in deps:
            packages.append((pkg, filepath, "npm"))
    except Exception as e:
        logger.warning(f"::warning file={filepath}::Failed to parse package.json: {e}")
    return packages

def main() -> None:
    parser = argparse.ArgumentParser(description="AI Dependency Guard Scanner")
    parser.add_argument("--scan-path", default=".", help="Root directory to scan for manifests")
    parser.add_argument("--blocklist", default="", help="Comma-separated blocklist of explicitly denied packages")
    args = parser.parse_args()

    blocklist_set = {pkg.strip().lower() for pkg in args.blocklist.split(",") if pkg.strip()}
    
    all_packages_to_scan = []

    for root, _, files in os.walk(args.scan_path):
        if "requirements.txt" in files:
            filepath = os.path.join(root, "requirements.txt")
            logger.info(f"🔍 Discovered {filepath}")
            all_packages_to_scan.extend(parse_requirements(filepath))
            
        if "package.json" in files:
            filepath = os.path.join(root, "package.json")
            logger.info(f"🔍 Discovered {filepath}")
            all_packages_to_scan.extend(parse_package_json(filepath))

    if not all_packages_to_scan:
        logger.info("✅ No dependency manifests found. Supply chain secure.")
        sys.exit(0)

    logger.info(f"🚀 Initiating Two-Tier Scan for {len(all_packages_to_scan)} dependencies...")
    
    hallucinations_found = []
    known_squatted_found = []
    
    # ThreadPoolExecutor for high-performance concurrent evaluation
    # Max workers kept low to respect API rate limits alongside DELAY_MS
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(process_package, pkg, fp, reg, blocklist_set): pkg
            for pkg, fp, reg in all_packages_to_scan
        }
        
        for future in concurrent.futures.as_completed(futures):
            try:
                status, fp, pkg, reg = future.result()
                if status == 'squatted':
                    known_squatted_found.append((fp, pkg, reg))
                elif status == 'hallucinated':
                    hallucinations_found.append((fp, pkg, reg))
            except Exception as exc:
                logger.error(f"Package evaluation generated an exception: {exc}")

    if hallucinations_found or known_squatted_found:
        logger.error("::error::🚨 LLM DEPENDENCY HALLUCINATION DETECTED! 🚨")
        
        if known_squatted_found:
            logger.error("The following packages are EXPLICITLY BLOCKED because they are known to be defensively squatted or hijacked (HTTP 200 Bypass):")
            for fp, pkg, reg in known_squatted_found:
                logger.error(f"::error file={fp}::Known Squatted Package '{pkg}' blocked on {reg}.")
                
        if hallucinations_found:
            logger.error("The following packages DO NOT EXIST in the public registry. This is a critical security risk (Phantom Dependency Squatting).")
            for fp, pkg, reg in hallucinations_found:
                logger.error(f"::error file={fp}::Hallucinated package '{pkg}' not found on {reg}.")
                
        sys.exit(1)
        
    logger.info("✅ All dependencies verified against public registries. Supply chain secure.")
    sys.exit(0)

if __name__ == "__main__":
    main()
