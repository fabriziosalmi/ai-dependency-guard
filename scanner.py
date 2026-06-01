import os
import sys
import re
import json
import urllib.request
import urllib.error
import time

def check_pypi(package_name):
    url = f"https://pypi.org/pypi/{package_name}/json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (AI-Dependency-Guard)'})
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        return True
    except Exception:
        return True

def check_npm(package_name):
    url = f"https://registry.npmjs.org/{package_name}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (AI-Dependency-Guard)'})
    try:
        urllib.request.urlopen(req, timeout=5)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        return True
    except Exception:
        return True

def main():
    scan_path = sys.argv[1] if len(sys.argv) > 1 else "."
    blocklist_raw = sys.argv[2] if len(sys.argv) > 2 else ""
    
    # Parse blocklist
    blocklist = [pkg.strip().lower() for pkg in blocklist_raw.split(",") if pkg.strip()]
    
    hallucinations_found = []
    known_squatted_found = []
    
    for root, dirs, files in os.walk(scan_path):
        if "requirements.txt" in files:
            filepath = os.path.join(root, "requirements.txt")
            print(f"🔍 Scanning {filepath}...")
            with open(filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    
                    pkg = re.split(r'[=><~]', line)[0].strip().lower()
                    if pkg and not pkg.startswith("-"):
                        # Tier 1: Check blocklist (HTTP 200 Bypass Prevention)
                        if pkg in blocklist:
                            known_squatted_found.append((filepath, pkg, "PyPI"))
                            continue
                            
                        # Tier 2: Check Registry (404 Detection)
                        time.sleep(0.1)
                        if not check_pypi(pkg):
                            hallucinations_found.append((filepath, pkg, "PyPI"))
                            
        if "package.json" in files:
            filepath = os.path.join(root, "package.json")
            print(f"🔍 Scanning {filepath}...")
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                deps = list(data.get("dependencies", {}).keys()) + list(data.get("devDependencies", {}).keys())
                for pkg_raw in deps:
                    pkg = pkg_raw.strip().lower()
                    
                    if pkg in blocklist:
                        known_squatted_found.append((filepath, pkg, "npm"))
                        continue
                        
                    time.sleep(0.1)
                    if not check_npm(pkg):
                        hallucinations_found.append((filepath, pkg, "npm"))
            except:
                pass

    if hallucinations_found or known_squatted_found:
        print("::error::🚨 LLM DEPENDENCY HALLUCINATION DETECTED! 🚨")
        
        if known_squatted_found:
            print("The following packages are EXPLICITLY BLOCKED because they are known to be defensively squatted or hijacked (HTTP 200 Bypass):")
            for fp, pkg, reg in known_squatted_found:
                print(f"::error file={fp}::Known Squatted Package '{pkg}' blocked on {reg}.")
                
        if hallucinations_found:
            print("The following packages DO NOT EXIST in the public registry. This is a critical security risk (Phantom Dependency Squatting).")
            for fp, pkg, reg in hallucinations_found:
                print(f"::error file={fp}::Hallucinated package '{pkg}' not found on {reg}.")
                
        sys.exit(1)
        
    print("✅ No hallucinated dependencies found. Supply chain secure.")
    sys.exit(0)

if __name__ == "__main__":
    main()
