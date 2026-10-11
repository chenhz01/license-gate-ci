"""license-gate-ci: license compliance gate for dependency manifests.

Pure standard library. Reads a dependency manifest (JSON) plus a policy file,
flags missing/unknown/forbidden licenses, checks copyleft compatibility with
the project license, supports a reviewed-exceptions file, and exits non-zero
so CI can hard-fail. Inspired by the "unknown license breaks CI" mechanism
used by high-profile projects (e.g. Zed's cargo-about gate as of 2026-10-11).
"""
from __future__ import annotations

import json
from typing import List, Optional

# Permissive baseline: safe for almost any project
DEFAULT_ALLOWED = {
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD",
    "Unlicense", "CC0-1.0", "Zlib", "BSL-1.0", "Unicode-3.0",
}
# Strong copyleft / network copyleft: incompatible with many project licenses
DEFAULT_DENIED = {
    "AGPL-3.0", "AGPL-3.0-only", "AGPL-3.0-or-later", "SSPL-1.0", "Elastic-2.0",
    "BUSL-1.1", "LGPL-3.0", "GPL-2.0", "GPL-3.0",
}
WEAK_COPYLEFT = {"MPL-2.0", "EPL-2.0", "LGPL-2.1"}

COMPAT_MATRIX = {
    # project license -> extra licenses it may accept beyond permissive baseline
    "MIT": set(),
    "Apache-2.0": set(),
    "GPL-3.0": {"GPL-2.0", "LGPL-3.0", "MPL-2.0", "EPL-2.0"},
    "MPL-2.0": {"MPL-2.0", "LGPL-2.1"},
}


def normalize(license_id: Optional[str]) -> str:
    if not license_id or not str(license_id).strip():
        return "UNKNOWN"
    lid = str(license_id).strip()
    aliases = {
        "mit license": "MIT", "apache 2.0": "Apache-2.0", "apache2": "Apache-2.0",
        "bsd": "BSD-3-Clause", "the unlicense": "Unlicense", "wtfpl": "WTFPL",
    }
    return aliases.get(lid.lower(), lid)


def load_policy(path: Optional[str], data: Optional[dict] = None) -> dict:
    if data is None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    policy = {
        "project_license": data.get("project_license", "MIT"),
        "allowed": set(data.get("allowed", DEFAULT_ALLOWED)),
        "denied": set(data.get("denied", DEFAULT_DENIED)),
        "exceptions": {e["name"]: e for e in data.get("exceptions", [])},
    }
    return policy


def load_manifest(path: Optional[str], data: Optional[dict]) -> List[dict]:
    if data is None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    deps = data.get("dependencies", data) if isinstance(data, dict) else data
    if not isinstance(deps, list):
        raise ValueError("manifest must be a list or {'dependencies': [...]}")
    for d in deps:
        if not isinstance(d, dict) or "name" not in d:
            raise ValueError("each dependency needs at least a 'name'")
    return deps


def check_dependency(dep: dict, policy: dict) -> dict:
    name = dep["name"]
    lic = normalize(dep.get("license"))
    exception = policy["exceptions"].get(name)
    result = {"name": name, "license": lic, "status": "ok", "detail": ""}

    if lic == "UNKNOWN":
        result["status"] = "FAIL"
        result["detail"] = "license missing or undeclared"
    elif lic in policy["denied"]:
        if exception:
            result["status"] = "WARN"
            result["detail"] = "denied but exception on file: %s" % exception.get("justification", "no justification given")
        else:
            result["status"] = "FAIL"
            result["detail"] = "license on project denylist"
    elif lic in policy["allowed"]:
        result["detail"] = "permissive allowlist" + (" (exception on file)" if exception else "")
    elif lic in WEAK_COPYLEFT:
        extra = COMPAT_MATRIX.get(policy["project_license"], set())
        if lic in extra:
            result["detail"] = "weak copyleft, compatible with project license per matrix"
        elif exception:
            result["status"] = "WARN"
            result["detail"] = "weak copyleft outside matrix; reviewed exception on file"
        else:
            result["status"] = "FAIL"
            result["detail"] = "weak copyleft %s not in compatibility matrix for %s" % (lic, policy["project_license"])
    else:
        result["status"] = "FAIL"
        result["detail"] = "license not in allowlist, denylist, or matrix (unknown risk)"
    return result


def gate(deps: List[dict], policy: dict) -> dict:
    results = [check_dependency(d, policy) for d in deps]
    failed = [r for r in results if r["status"] == "FAIL"]
    warned = [r for r in results if r["status"] == "WARN"]
    verdict = "FAIL" if failed else ("REVIEW" if warned else "PASS")
    return {"tool": "license-gate-ci", "project_license": policy["project_license"],
            "verdict": verdict, "totals": {"deps": len(results), "fail": len(failed), "warn": len(warned)},
            "results": results,
            "failed_deps": [r["name"] for r in failed]}


# ------------------------------------------------ v0.1.2: obligations + diff

TIER = {"permissive": 0, "weak_copyleft": 1, "strong_copyleft": 2, "unknown": 9}

OBLIGATIONS = {
    "permissive": [
        "retain copyright and license notices in distributions",
        "include attribution in a notices file / docs",
    ],
    "weak_copyleft": [
        "retain copyright and license notices",
        "publish modified copies of covered files under the same license",
        "document changes made to covered files",
    ],
    "strong_copyleft": [
        "retain copyright and license notices",
        "license the entire derivative work under the same license",
        "provide corresponding source to recipients of the binary",
    ],
    "unknown": [
        "identify the license first — no obligations can be enumerated for unknown terms",
    ],
}


def license_tier(lic: Optional[str]) -> str:
    """Map a license id to a coarse obligation tier. Unknown -> 'unknown'."""
    lid = normalize(lic)
    if lid == "UNKNOWN":
        return "unknown"
    if lid.startswith("LGPL"):
        return "weak_copyleft"
    if lid.startswith(("GPL", "AGPL")) or lid in ("SSPL-1.0", "Elastic-2.0", "BUSL-1.1"):
        return "strong_copyleft"
    if lid in WEAK_COPYLEFT:
        return "weak_copyleft"
    if lid in DEFAULT_ALLOWED:
        return "permissive"
    return "unknown"


def obligations(deps: List[dict]) -> dict:
    """Export a shipping-obligation checklist: per-dep tier, aggregate counts,
    and an ordered must-do list (strong copyleft first, unknown last).

    This is a checklist generator over declared license fields, not legal advice.
    """
    per_dep, agg = [], {"permissive": 0, "weak_copyleft": 0, "strong_copyleft": 0, "unknown": 0}
    for d in deps:
        t = license_tier(d.get("license"))
        agg[t] += 1
        per_dep.append({"name": d["name"], "license": normalize(d.get("license")),
                        "tier": t, "obligations": OBLIGATIONS[t]})
    must_do = [{"tier": t, "deps": agg[t], "obligations": OBLIGATIONS[t]}
               for t in ("strong_copyleft", "weak_copyleft", "permissive") if agg[t]]
    if agg["unknown"]:
        must_do.append({"tier": "unknown", "deps": agg["unknown"], "obligations": OBLIGATIONS["unknown"]})
    return {"tool": "license-gate-ci", "check": "obligations", "tiers": agg,
            "must_do": must_do, "per_dep": per_dep}


def diff_manifests(old_deps: List[dict], new_deps: List[dict]) -> dict:
    """License drift between two manifest versions: added/removed deps and
    license changes, with tier escalations flagged (e.g. MIT -> BUSL on upgrade).
    """
    old = {d["name"]: normalize(d.get("license")) for d in old_deps}
    new = {d["name"]: normalize(d.get("license")) for d in new_deps}
    added = [{"name": n, "license": new[n], "tier": license_tier(new[n])}
             for n in sorted(set(new) - set(old))]
    removed = [{"name": n, "license": old[n]} for n in sorted(set(old) - set(new))]
    changed = []
    for n in sorted(set(old) & set(new)):
        if old[n] != new[n]:
            t_from, t_to = license_tier(old[n]), license_tier(new[n])
            changed.append({"name": n, "from": old[n], "to": new[n],
                            "tier_change": [t_from, t_to],
                            "escalated": TIER[t_to] > TIER[t_from]})
    escalated = [c["name"] for c in changed if c["escalated"]]
    return {"check": "license_diff", "added": added, "removed": removed, "changed": changed,
            "escalations": escalated,
            "detail": "%d added, %d removed, %d changed, %d escalated"
                      % (len(added), len(removed), len(changed), len(escalated))}


DEFAULT_POLICY = {
    "project_license": "MIT",
    "allowed": sorted(DEFAULT_ALLOWED),
    "denied": sorted(DEFAULT_DENIED),
    "exceptions": [],
}
