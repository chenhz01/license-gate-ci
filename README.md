# license-gate-ci

A license compliance gate for dependency manifests: unknown, undeclared, or denylisted licenses fail the build with exit code 1 — the same "compliance is code" mechanism high-profile projects use when incomplete third-party license data breaks CI. If a dependency's license is a mystery, this gate refuses to let it merge.

**Confidence: High (85%)** that allowlist/denylist/matrix gating catches the license mistakes that actually ship (undeclared licenses, sneaky AGPL, weak-copyleft surprises); **Medium (65%)** that the built-in baseline lists match your legal posture without tuning [estimated].

## Problem

License compliance is usually a release-eve spreadsheet ritual: someone exports dependencies, squints at 200 licenses, and misses the one package that quietly changed to AGPL. The failure mode is predictable — *undeclared* licenses (the field is empty, so nobody notices) and *unknown* licenses (some custom text) slip through human review. Projects like Zed (as of 2026-10-11) solved this by making incomplete license data a hard CI failure via cargo-about; this tool brings the same gate to plain JSON manifests with zero dependencies.

- **Why novel:** the gate checks for *absence of information* as harshly as for *forbidden information* — most checkers only look at what's there.
- **Overlooked angle:** a three-way classification (allowlist / denylist / unknown-risk) turns legal posture into a versionable, reviewable file.

## How it works

Input: a dependency manifest (`[{"name", "version", "license"}, ...]` or `{"dependencies": [...]}`) and a policy file (project license, allowed list, denied list, exceptions). Each dependency is classified:

| Condition | Status | Result |
|---|---|---|
| license in allowed list | ok | PASS |
| license in denied list, no exception | FAIL | build breaks |
| license in denied list, exception on file | WARN | REVIEW verdict |
| weak copyleft, compatible per matrix with project license | ok | PASS |
| weak copyleft, incompatible | FAIL | build breaks |
| license missing / unknown to all lists | FAIL | build breaks — by design |

License IDs are normalized (casing, whitespace, common aliases like "Apache 2.0" → `Apache-2.0`). The compatibility matrix encodes which copyleft licenses a project license may accept (e.g. GPL-3.0 projects may use GPL-2.0/MPL-2.0 deps; MIT projects may not). Exit codes: 0 = PASS/REVIEW, 1 = FAIL, 2 = usage error.

## How this differs from EmbarkStudios/cargo-about

cargo-about (797★ as of 2026-10-11) is a mature, polished tool and the honest baseline here: a Cargo plugin that generates a license listing for all dependencies of a crate (transitive deps included), with `cargo about init` scaffolding and Handlebars-template rendering to HTML, backed by real SPDX data. It is Rust-ecosystem-bound and its core loop is generate-a-report.

This repo shares no code with it and adds two outputs its README and docs do not offer:

- **Obligation-tier checklist export** (`obligations`) — cargo-about renders whatever your template asks for, but ships no structured obligation model. This tool classifies every dep into permissive / weak-copyleft / strong-copyleft / unknown tiers and emits an ordered must-do checklist (retain notices; publish modified covered files; release the whole derivative under the same license; resolve unknowns first), aggregated per tier. It is a checklist generator over declared fields, not legal advice.
- **License drift diff** (`diff old.json new.json`) — cargo-about regenerates a listing per run but has no compare-two-versions mode. This tool diffs two manifest versions and flags added/removed deps, license changes, and *tier escalations* (e.g. a routine upgrade quietly moving MIT → BUSL-1.1), exiting 1 so the escalation breaks CI like any other gate failure.

The fail-closed gate remains the core difference: cargo-about is a report generator you can wire into CI; this tool fails on *absent* license data by design, for any stack that can emit a JSON manifest.

## Quickstart (~2 min)

```bash
# 1. Self-test: 27 checks, functional / error-path / extreme-edge (~2 s)
python self_test.py

# 2. Demo: 6 deps, 4 correctly FAILed (GPL, undeclared, unknown, LGPL-under-MIT) (~1 s)
python cli.py check --demo        # -> FAIL, exit 1

# 3. Ship-time obligations for the same manifest
python cli.py obligations --demo

# 4. License drift between two lockfile exports (exit 1 on tier escalation)
python cli.py diff old_deps.json new_deps.json

# 5. Gate your own dependencies
python cli.py init-policy         # write policy.json, review it
python cli.py check deps.json --policy policy.json --exceptions exc.json --report r.json
```

## Why not X

| Alternative | Why not |
|---|---|
| cargo-about / cargo-deny | Excellent, but Rust-ecosystem-bound; this gates any stack whose deps fit a JSON manifest (Python, Node dumps, vendored lists) with zero toolchain |
| FOSSA / Snyk license scanning | SaaS, per-seat pricing, and data egress of your dependency tree; this runs locally in milliseconds and never phones home |
| Manual review at release time | Humans miss undeclared fields by construction; gates don't blink, and "UNKNOWN → FAIL" converts silence into a build error |
| pip-licenses / license-checker (report-only) | They report; nothing breaks. The value here is the exit code, not the table |

## Minimal Fallback (PLAN B)

No Python? The policy is the table above plus two lists. In shell: `jq -e '.dependencies[] | select(.license == null or .license == "")' deps.json` and fail on non-empty output — that alone catches the undeclared-license class, which is the highest-frequency failure. The JSON report schema is the contract for re-implementations.

## Design Trade-offs

Priority order: **fail-closed > simplicity > ecosystem coverage**. Unknown licenses FAIL (fail-closed) — noisy at first adoption, which is intentional: the noise *is* the inventory work. License detection is not attempted (no file scanning for license text); we trust the declared field, so a wrong declaration passes — declaration vs reality reconciliation needs heavier tooling. The compatibility matrix is a coarse two-level approximation of license law, not legal advice; exceptions carry free-text justifications because review context matters more than taxonomy purity.

## Limits & Second-order Effects

- Fail-closed on unknown licenses can push teams to *label* dependencies optimistically rather than resolve them — audit exception justifications, not just the gate's green check.
- The gate only sees what the manifest lists; transitive dependencies with unlisted licenses remain invisible unless your lockfile export feeds this tool.
- Denylist maintenance drifts: new copyleft variants (BUSL-style) appear yearly; a stale denylist is a slowly leaking gate.
- If the gate is too annoying, teams may vendor dependencies to avoid the manifest entirely — watch for that escape hatch.

## FAQ

**Is this legal advice?** No. The allow/deny/matrix defaults encode a common open-source posture (permissive-friendly, strong-copyleft-cautious). Have counsel set your lists; this tool makes them enforceable.

**Why FAIL on unknown instead of WARN?** Undeclared licenses are the most common real-world defect. Failing closed turns "nobody looked" into a ticket; WARN queues rot.

**When NOT to use this?** Don't use it as your only compliance control (it can't detect license text misdeclaration, and it doesn't read transitive deps), not for proprietary-license postures it wasn't tuned for (commercial or bespoke terms need custom lists), and not before you've actually written a policy — a gate without a policy is just denial by default.

**Can I import from requirements.txt / package-lock.json?** Not in v0.1 — export to the JSON shape first (a one-liner with `pip-licenses --format=json` or `jq`). Adapters are the natural next step.

## [Core Assumptions]

1. Declared license fields in manifests are mostly accurate; the gate's job is catching *absence* and *policy violations*, not fraud.
2. A coarse allowlist/denylist/matrix model is sufficient for CI gating; edge cases belong in human-reviewed exceptions with justifications.
3. Fail-closed is the correct default for compliance noise economics: false alarms cost minutes, missed AGPL costs releases.
4. Exceptions are rare, deliberate, and auditable — a list of {name, justification} is enough structure to review them.

*Data as of 2026-10-11. Measured: 27/27 self-test checks (~2 s) and 6-dep demo (4 FAILed), repro via `python self_test.py` / `python cli.py check --demo` on Windows 10 / CPython 3.11. Zed's mechanism and cargo-about's workflow referenced from their READMEs as of this date; adoption-cost figures [estimated].*
