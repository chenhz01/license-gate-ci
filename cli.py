"""CLI for license-gate-ci. Pure argparse, standard library only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from licensegate import (DEFAULT_POLICY, diff_manifests, gate, load_manifest,
                         load_policy, obligations)

DEMO_MANIFEST = {
    "dependencies": [
        {"name": "tiny-util", "version": "1.2.0", "license": "MIT"},
        {"name": "web-framework", "version": "0.9.1", "license": "Apache-2.0"},
        {"name": "old-parser", "version": "3.0.2", "license": "GPL-3.0"},
        {"name": "mystery-lib", "version": "0.0.1", "license": None},
        {"name": "exotic-codec", "version": "2.1", "license": "RPSL-1.0"},
        {"name": "lgpl-helper", "version": "4.4", "license": "LGPL-3.0"},
    ]
}

DEMO_EXCEPTIONS = {"project_license": "MIT", "exceptions": []}


def cmd_check(args: argparse.Namespace) -> int:
    if args.demo:
        manifest = DEMO_MANIFEST["dependencies"]
        pdata = load_policy(None, data=dict(DEFAULT_POLICY, exceptions=[]))
    else:
        manifest = load_manifest(args.manifest, None)
        pdata = load_policy(args.policy) if args.policy else load_policy(None, data=dict(DEFAULT_POLICY, exceptions=load_exceptions(args.exceptions)))
    report = gate(manifest, pdata)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return {"PASS": 0, "REVIEW": 0, "FAIL": 1}[report["verdict"]]


def load_exceptions(path):
    if not path:
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_init(_args: argparse.Namespace) -> int:
    Path("policy.json").write_text(json.dumps(DEFAULT_POLICY, indent=2) + "\n", encoding="utf-8")
    print("wrote policy.json — review allowed/denied lists before committing it")
    return 0


def cmd_obligations(args: argparse.Namespace) -> int:
    if args.demo:
        deps = DEMO_MANIFEST["dependencies"]
    else:
        deps = load_manifest(args.manifest, None)
    print(json.dumps(obligations(deps), indent=2, sort_keys=True))
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    old = load_manifest(args.old, None)
    new = load_manifest(args.new, None)
    report = diff_manifests(old, new)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return 1 if report["escalations"] else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="license-gate-ci",
                                description="License compliance gate: unknown/forbidden dependency licenses fail the build.")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("check", help="gate a dependency manifest against a policy")
    a.add_argument("manifest", nargs="?", help="path to dependency manifest JSON")
    a.add_argument("--demo", action="store_true", help="run the built-in demo manifest")
    a.add_argument("--policy", help="path to policy JSON (defaults to built-in baseline)")
    a.add_argument("--exceptions", help="path to exceptions JSON [{name, justification}]")
    a.add_argument("--report", help="write JSON report to this path")
    a.set_defaults(func=cmd_check)

    i = sub.add_parser("init-policy", help="write a starter policy.json")
    i.set_defaults(func=cmd_init)

    o = sub.add_parser("obligations", help="export a per-dep obligation checklist by license tier")
    o.add_argument("manifest", nargs="?", help="path to dependency manifest JSON")
    o.add_argument("--demo", action="store_true", help="run the built-in demo manifest")
    o.set_defaults(func=cmd_obligations)

    d = sub.add_parser("diff", help="license drift between two manifest versions; exit 1 on tier escalation")
    d.add_argument("old", help="previous manifest JSON")
    d.add_argument("new", help="current manifest JSON")
    d.add_argument("--report", help="write JSON report to this path")
    d.set_defaults(func=cmd_diff)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
