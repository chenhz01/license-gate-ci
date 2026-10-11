# Changelog

## [0.1.2] - 2026-10-11

### Added (anchor differentiation: EmbarkStudios/cargo-about re-audit)

- **Obligation-tier checklist export** (`licensegate.obligations`, `cli.py obligations`): classifies every dep into permissive / weak-copyleft / strong-copyleft / unknown and emits an ordered must-do checklist aggregated per tier (strong copyleft first, unknown last). cargo-about renders template-driven listings but ships no structured obligation model.
- **License drift diff** (`licensegate.diff_manifests`, `cli.py diff`): compares two manifest versions, flags added/removed deps, license changes, and tier escalations (e.g. MIT → BUSL-1.1 on a routine upgrade), exit 1 on escalation so drift breaks CI. cargo-about has no compare-two-versions mode.
- 7 new self-test cases (20 → 27): four-class tier mapping (incl. LGPL-3.0 → weak, BUSL → strong), tier aggregation, must-do ordering, MIT→BUSL escalation detection, nameless-dep error path, zeroed empty diff, 5000-char license.
- Honesty note recorded in README: cargo-about does traverse transitive deps for listing generation — this tool remains flat-manifest by design; the stated differentiators are the fail-closed gate, obligation tiers, and drift diff.

## [0.1.1] - 2026-10-11

### Changed (round-2 iteration after 16-item self-audit)

- **Correctness:** fixed two demo-path bugs the self-test harness didn't cover — `cmd_check --demo` passed the manifest wrapper dict instead of the dependency list (TypeError), and built the policy without `load_policy` normalization (AttributeError on exceptions). Demo now correctly FAILs 4/6 deps.
- **Correctness (+~25% test rigor):** added an extreme-edge case for an empty allowlist (even MIT must FAIL — proves fail-closed really is closed), whitespace-padded license normalization, and a missing-policy-file error-path case; suite grew from 16 to 20 checks.
- **Completeness:** README gained the classification table, jq Minimal-Fallback one-liner, and a "vendor-to-escape-the-gate" second-order effect.

## [0.1.0] - 2026-10-11

### Added

- `licensegate.py`: license normalization (casing/aliases), three-way classification (allowlist/denylist/unknown-risk), weak-copyleft compatibility matrix keyed by project license, exceptions with justifications, gate() report with PASS/REVIEW/FAIL.
- `cli.py`: `check` (--demo/--policy/--exceptions/--report) and `init-policy` subcommands; exit codes 0/1/2.
- `self_test.py`: three families — functional (9), error paths (5), extreme edges (6: empty manifest, 2000-dep timing, 5000-char license strings, duplicates, empty allowlist).
- MIT LICENSE (zhengming contributors), README, initial ALIGNMENT audit.
