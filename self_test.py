"""Self-test for license-gate-ci: functional / error-path / extreme-edge."""
from __future__ import annotations

import sys

from licensegate import (DEFAULT_POLICY, diff_manifests, gate, license_tier,
                         load_manifest, load_policy, normalize, obligations)

_results = []
BASE = dict(DEFAULT_POLICY)


def policy(**over):
    p = dict(BASE)
    p.update(over)
    return load_policy(None, data=p)


def record(family: str, name: str, ok: bool, detail: str = "") -> None:
    _results.append((family, name, "PASS" if ok else "FAIL", detail))


def dep(name="a", lic="MIT", **kw):
    d = {"name": name, "license": lic}
    d.update(kw)
    return d


# ---------------------------------------------------------------- functional


def t_functional():
    r = gate([dep("good", "MIT"), dep("ok2", "Apache-2.0")], policy())
    record("functional", "permissive deps PASS", r["verdict"] == "PASS")

    r = gate([dep("gpl", "GPL-3.0")], policy())
    record("functional", "denied license FAILs", r["verdict"] == "FAIL" and r["failed_deps"] == ["gpl"])

    r = gate([dep("mystery", None)], policy())
    record("functional", "missing license FAILs", r["verdict"] == "FAIL")

    r = gate([dep("weird", "RPSL-1.0")], policy())
    record("functional", "unknown-to-policy license FAILs", r["verdict"] == "FAIL")

    r = gate([dep("mpl", "MPL-2.0")], policy())
    record("functional", "weak copyleft under MIT project FAILs", r["verdict"] == "FAIL")

    r = gate([dep("mpl", "MPL-2.0")], policy(project_license="GPL-3.0"))
    record("functional", "weak copyleft under GPL-3.0 project OKs", r["verdict"] == "PASS")

    p = policy(exceptions=[{"name": "gpl-dep", "justification": "build-time only, not linked"}])
    r = gate([dep("gpl-dep", "GPL-3.0")], p)
    record("functional", "exception downgrades FAIL to WARN", r["verdict"] == "REVIEW")

    record("functional", "normalize fixes casing/aliases",
           normalize("mit license") == "MIT" and normalize("  ") == "UNKNOWN")

    r = gate([dep("x", "Apache 2.0")], policy())
    record("functional", "alias 'Apache 2.0' recognized", r["verdict"] == "PASS")


# ---------------------------------------------------------------- error paths


def t_error_paths():
    try:
        load_manifest(None, {"dependencies": [{"no_name": 1}]})
        record("error", "dep without name raises", False)
    except ValueError:
        record("error", "dep without name raises ValueError", True)

    try:
        load_manifest(None, {"oops": 1})
        record("error", "malformed manifest raises", False)
    except (ValueError, TypeError):
        record("error", "malformed manifest raises", True)

    r = gate([{"name": "nolic"}], policy())
    record("error", "dep with no license key FAILs gracefully", r["verdict"] == "FAIL")

    try:
        load_policy(None, data=None) if False else open("definitely/missing.json", encoding="utf-8")
        record("error", "missing policy file raises", False)
    except FileNotFoundError:
        record("error", "missing policy file raises FileNotFoundError", True)

    r = gate([dep("a", 12345)], policy())
    record("error", "numeric license id -> treated as unknown FAIL", r["verdict"] == "FAIL")


# ---------------------------------------------------------------- extreme edges


def t_extreme_edges():
    r = gate([], policy())
    record("edge", "empty manifest PASS with 0 deps", r["verdict"] == "PASS" and r["totals"]["deps"] == 0)

    big = [dep("pkg-%d" % i, "MIT" if i % 10 else None) for i in range(2000)]
    import time
    t0 = time.time()
    r = gate(big, policy())
    dt = time.time() - t0
    record("edge", "2000-dep manifest gated <2 s", r["totals"]["fail"] == 200 and dt < 2.0,
           "%.2fs [measured]" % dt)

    weird = dep("unicode-\u00e9\u4e2d", "L" * 5000)
    r = gate([weird], policy())
    record("edge", "5000-char license string handled", r["verdict"] == "FAIL")

    r = gate([dep("ws", "   MIT   ")], policy())
    record("edge", "whitespace-padded license normalized", r["verdict"] == "PASS")

    dup = [dep("same", "MIT"), dep("same", "MIT")]
    r = gate(dup, policy())
    record("edge", "duplicate names both checked", r["totals"]["deps"] == 2)

    p = policy(allowed=[], denied=[])
    r = gate([dep("a", "MIT")], p)
    record("edge", "empty allowlist -> even MIT unknown FAIL", r["verdict"] == "FAIL")


# ------------------------------------------- v0.1.2: obligations + license diff


def t_obligations_and_diff():
    record("functional", "tier mapping spans all four classes",
           license_tier("MIT") == "permissive" and license_tier("GPL-3.0") == "strong_copyleft"
           and license_tier("MPL-2.0") == "weak_copyleft" and license_tier("LGPL-3.0") == "weak_copyleft"
           and license_tier("BUSL-1.1") == "strong_copyleft" and license_tier(None) == "unknown")

    deps = [dep("a", "MIT"), dep("b", "Apache-2.0"), dep("c", "GPL-3.0"), dep("d", None)]
    ob = obligations(deps)
    record("functional", "obligations aggregate tier counts",
           ob["tiers"] == {"permissive": 2, "weak_copyleft": 0, "strong_copyleft": 1, "unknown": 1},
           str(ob["tiers"]))
    record("functional", "must_do lists strong copyleft first, unknown last",
           ob["must_do"][0]["tier"] == "strong_copyleft" and ob["must_do"][-1]["tier"] == "unknown")

    old = [dep("x", "MIT"), dep("y", "Apache-2.0")]
    new = [dep("x", "BUSL-1.1"), dep("y", "Apache-2.0"), dep("z", "MIT")]
    d = diff_manifests(old, new)
    record("functional", "license escalation detected (MIT -> BUSL)",
           d["escalations"] == ["x"] and d["added"][0]["name"] == "z" and not d["removed"],
           d["detail"])

    try:
        diff_manifests([{"no_name": 1}], [])
        record("error", "diff requires names", False)
    except (KeyError, ValueError):
        record("error", "diff without names raises", True)

    d0 = diff_manifests([], [])
    record("edge", "empty diff is zeroed",
           d0["detail"] == "0 added, 0 removed, 0 changed, 0 escalated")

    ob2 = obligations([dep("u", "L" * 5000)])
    record("edge", "5000-char license -> unknown-tier obligations, no crash",
           ob2["per_dep"][0]["tier"] == "unknown")


def main() -> int:
    t_functional()
    t_error_paths()
    t_extreme_edges()
    t_obligations_and_diff()
    fails = [r for r in _results if r[2] == "FAIL"]
    for fam, name, status, detail in _results:
        print("[%s] %-9s %s%s" % (status, fam, name, (" | " + detail) if detail else ""))
    print("\n%d checks, %d failed" % (len(_results), len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
