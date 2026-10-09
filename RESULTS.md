# Free-Lane Bench v1 — results (2026-10-09)

Run: 550 calls, 5 lanes × 38 items (k=3, F4 k=2), round-robin, temp 0.7,
`results/20261009-full/`. Confirmatory pass on 2 corrected items:
`results/20261009-v11/` (25 calls). Full scorecard: `results/20261009-full/scorecard.md`.

## Headline

| lane | e2e pass | capability (200s only) | 1st-attempt fail | p50 range | verdict |
|---|---|---|---|---|---|
| C `longcat-2.5-preview:free` (Nous) | **110/110** | 110/110 | 0.9% | 5.6–14.8s | perfect sweep |
| E `omen-alpha` (OpenCode Go) | **110/110** | 110/110 | **0.0%** | 1.6–4.8s | perfect sweep, fastest |
| D `mimo-v2.6-flash-free` (self-hosted relay) | 108/110 | 108/110 | 1.8% | 8.1–16.3s | 1 format miss, 1 arithmetic |
| B `step-5-preview:free` (Nous) | 101/110 | 101/104 | 8.2% ⚠ | 4.7–13.7s | capable; Nous quota limits bite |
| A `ling-3.1-flash:free` (CommandCode) | 81/110 | **81/81** | **42.7%** ⚠ | 2.3–5.2s | capability fine, throttled to death |

## Decomposition (the honest reading)

- **A-ling-3.1:** every call that got through passed (81/81 graded). The 29
  losses are all HTTP 429 "Upstream model provider is temporarily unavailable"
  after retries. Unusable for routing at current CommandCode free-tier capacity
  regardless of capability.
- **B-step-5:** 3 graded misses: 2 on the F3-03 CSV item (spec ambiguity —
  hidden assert `parse_csv_line('') == ['']` was not in the prompt; the
  `csv.reader` answer returns `[]`, defensible), 1 on F4-01 (doc contained the
  units table TWICE via a generator bug; B answered 1580 = "two tables",
  defensible). Both artifacts were mine, fixed in v1.1. B could not re-verify
  on v1.1: Nous model-level quota exhausted (429 ×5).
- **D-mimo-2.6:** 2 real misses — F2-04 answered bare "Yes" with no `Answer:`
  line (instruction-following), F4-01 summed 590 instead of 790 (arithmetic;
  on the v1.1 fixed doc it added correctly).
- **C & E:** clean sweeps including the trap-heavy honesty family.

## The coding gap is closed

All five free models were tested on coding for the first time (the standing
open gap in free-tier probing). On 6 items (4 write-a-function + 2 fix-the-bug, hidden
asserts executed): C 6/6 items, D 6/6, E 6/6, B 5/6 (both misses on my
ambiguous spec), A 2/6 items (7 calls 429'd; 11/11 graded passed). **Free
coding models exist and are strong.**

## Honesty family

Zero confabulations across the entire 550-call matrix: every fake-entity trap
was refused or correctly declared unanswerable by every lane that served.
All F5 "failures" are transport 429s (all A). Spot-check complete.

## v1.1 artifacts fixed (both were harness bugs, caught by auditing my own grader)

1. `build_doc` inserted the F4 units table up to 3× (20-word window bug).
   Fixed; F4-01 regenerated. v1.1: all 4 serving lanes answer 790.
2. F3-03 hidden assert `parse_csv_line('') == ['']` unadvertised. Prompt now
   states the empty-string example.

## Routing table (pre-registered rule applied)

| slot | winner |
|---|---|
| simple / medium / hard / research / structured-cron | **E `omen-alpha`** |
| coding | **D `mimo-v2.6-flash-free`** (tie with C/E at 6/6; lower p95) |

C, D, E are one statistical tier (the ≥2-item margin never triggered between
them); E wins ties on latency (p95 5–38s vs 10–53s C, 12–35s D). For coding,
E also passed 6/6 and its p95 was inflated by one truncation re-run — treat D
and E as interchangeable there. Practical note: E rides the OpenCode Go
subscription (session-header quirk), D was served through a self-hosted relay
endpoint, and B/C need Nous OAuth.

## Threats (unchanged from DESIGN.md, plus)

- Snapshot dated 2026-10-09; free catalogs mutate. Re-run is cheap.
- Nous per-model rate limits drain under sustained load (B's v1.1 0/5 is
  quota, not capability) — fine for routing probes, bad for burst workloads.
- Wide CIs (±15–25pp per family); the tier separation is real, fine ordering
  within {C, D, E} is not.

---

# Part 2 — Stress bench v2: capability limits (2026-10-09)

Run: 490 calls, 7 stress families (S1-S7, 34 items), `results/20261009-stress/`.
v2.1 repair of S2-04 (generator bug): `results/20261009-stress-v21/`.
All graders passed `selftest.py` (hand-built cases + bug-fix asserts proven to
fail their bugs) before any model call.

## Aggregate (stress)

| lane | pass | note |
|---|---|---|
| C longcat-2.5 | 96/98 | best constraint-soup; 1 runaway |
| B step-5 | 95/98 | precision king; 2 runaways |
| E omen-alpha | 92/98 | fastest; extraneous-output habit |
| D mimo-2.6 | 90/98 | counting/char slips; never empty |
| A ling-3.1 | 52/98 | 44×429 + 2 runaways; zero wrong answers |

Family highlights: S1 constraint-soup = the discriminator (C 94%, B 89%,
D 78%, E 72%). S2 char mechanics: B/C/E 100% raw, D 87%. S3 deep math:
B/D/E 6/6 items, C 5/6. S4 hard coding: B/C/E 6/6, D 5/6. S5 multi-hop
long-ctx: B/C/E 4/4, D 3/4. S6 verify/repair: C/D/E 4/4 (anti-sycophancy
traps passed — nobody rubber-stamped), B 3/4 (runaway). S7 JSON transform:
B/C/D 3/3, E 2/3.

## Failure-mode taxonomy (what they are actually BAD at)

1. **Reasoning runaway → empty output** (A×2, B×2, C×1): burn the entire
   4096-token budget on reasoning, emit nothing. B looped again at 8192.
   Silent-empty is the most dangerous failure for automation. D (no reasoning
   field) never had it; E never had it.
2. **Micro-counting** (word counts, per-line lengths, position constraints) —
   the #1 capability wall. Nobody aced S1 at pass^k except C (5/6).
3. **Extraneous output (E's signature)**: wrote PERFECT 20-word sentences,
   then appended verification tables → 60–192 words. Great content, unusable
   output format for pipelines.
4. **Character-level drops** (v2.1 leet item): D `QU1T`, E `Q13T` — single
   char dropped in 1/3 samples each. B/C 3/3.
5. **Transform slips** (D): scrambled word-order reversal; iterative flatten
   depth bug.
6. **Sort-key trap** (E, S7): sorted by computed total instead of the stated
   qty key.
7. **Rule application** (D, S2-03): hyphen-split counting rule misapplied.
8. **Format compliance** (D, S5-03): correct content, missing `Answer:` line.

## Lane weakness profiles

- **A ling-3.1:** delivery (45% 429) + runaway. Never *wrong* — but unusable.
- **B step-5:** runaway on constraint-soup (silent-empty), 1 line-count slip;
  otherwise perfect. Best precision on character mechanics.
- **C longcat:** strongest constraint-soup; one position slip, one runaway on
  date math. Slowest p95 (66s S1).
- **D mimo:** counting + char drops + one transform bug + one format slip;
  but zero empties, zero runaways — the steady non-reasoning floor.
- **E omen:** can't-stop-writing habit, char drops, sort-key trap; fastest,
  perfect math/coding cores.

## v2 harness artifacts (self-caught)

1. S2-04 generator `" ".join(r.choice(list))` garbled the phrase; mimo's
   "wrong" answer was the sane read. Fixed, re-run (v2.1): all lanes now
   graded fairly; D/E each drop one character.
2. S4 flatten spec had a vacuous `or True` assert — caught by self-test
   BEFORE any model call (the v1 lesson institutionalized).

