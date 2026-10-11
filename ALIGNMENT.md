# Alignment Audit (Rules 85-100 / 16 items) — license-gate-ci

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Safety/Ethics section | N/A | Compliance tooling; no dangerous content; legal-advice disclaimer present in FAQ. |
| 2 | Privacy/keys | PASS | No keys/tokens/real names/emails anywhere; dependency names are synthetic. |
| 3 | Copyright boundary | PASS | Zed's mechanism described in one paraphrased sentence with as-of date; no copied text; MIT LICENSE present. |
| 4 | Fact-check numbers | PASS | 27/27 checks, ~2 s, and demo 4/6 FAIL measured with repro commands; adoption-cost figures marked [estimated]; anchor facts dated as-of. |
| 5 | Confidence grading | PASS | README: High (85%) and Medium (65%) [estimated] labels with basis. |
| 6 | Minimal Fallback | PASS | "Minimal Fallback (PLAN B)": jq one-liner for the undeclared-license class; schema is the contract. |
| 7 | Quickstart timing | PASS | Quickstart labelled ~2 min, staged (self-test → demo → obligations → diff → own manifest). |
| 8 | Conflict arbitration | PASS | "Design Trade-offs": fail-closed > simplicity > ecosystem coverage, with the noise-is-features rationale. |
| 9 | Changelog ≥2 iterations | PASS | CHANGELOG v0.1.0 → v0.1.1 → v0.1.2; v0.1.2 adds anchor-differentiation features (obligation tiers, license drift diff). |
| 10 | Exemption (session rule) | N/A | Session-level governance item; static repo not applicable. |
| 11 | Knowledge cutoff | PASS | Zed reference and cargo-about comparison dated "as of 2026-10-11"; README footer repeats the date. |
| 12 | Explicit assumptions | PASS | `[Core Assumptions]` lists 4 premises (declaration trust, coarse model sufficiency, fail-closed economics, exception rarity). |
| 13 | Three-part self-test | PASS | functional (13) + error paths (6) + extreme edges (8) = 27/27 PASS. |
| 14 | Socratic FAQ | PASS | "When NOT to use this?" — no policy yet, proprietary postures, not the only control. |
| 15 | Pareto iteration | PASS | Round 2: 16→20 tests (+25%), two demo bugs fixed. Round 3 (v0.1.2): 20→27 tests (+35%) + two new capabilities; CHANGELOG-traceable. |
| 16 | ≤60-word opening | PASS | First paragraph is 56 words with a judgment sentence ("this gate refuses to let it merge"). |

Additional: **Second-order effects** — "Limits & Second-order Effects" covers optimistic mislabeling, transitive-dep invisibility, denylist drift, and vendoring escape hatch.
