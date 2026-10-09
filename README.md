# Free-Lane Bench

A small, rigorous, reproducible benchmark for **free-tier LLM lanes** — the
$0 models you actually route agent traffic to. It answers one question:
*which free lane should carry which job class, and what is each one bad at?*

Not a leaderboard. A **routing table** plus a **failure-mode taxonomy**.

- **Programmatic graders only** — zero LLM judges, zero vibes. Every scored
  item is exact-match, regex-checked, or run against hidden asserts in a
  subprocess.
- **Seeded, contamination-resistant items** — generated from templates with
  ground truth computed at generation time (random numbers, fake canaries,
  generated long-context docs).
- **Reliability measured as a first-class axis** — a throttled free lane is
  worse than a slower accurate one, so 429s degrade the reliability score,
  never masquerade as capability failures.
- **Self-tested graders** — `selftest.py` validates every checker against
  hand-built answers (and proves bug-fix items fail their bugs) *before* any
  model call. This discipline caught three harness bugs in two runs.

## Headline results (2026-10-09, five free lanes)

**Round 1 — capability baseline** (38 items, 550 calls, families F1–F6:
JSON discipline, reasoning, coding, long-context, honesty, extraction):

| lane | e2e pass | capability (200s only) | 1st-attempt failures | verdict |
|---|---|---|---|---|
| `meituan/longcat-2.5-preview:free` (Nous) | **110/110** | 110/110 | 0.9% | perfect sweep |
| `omen-alpha` (OpenCode Go) | **110/110** | 110/110 | 0.0% | perfect sweep, fastest |
| `mimo-v2.6-flash-free` (self-hosted relay) | 108/110 | 108/110 | 1.8% | 1 format miss, 1 arithmetic |
| `stepfun/step-5-preview:free` (Nous) | 101/110 | 101/104 | 8.2% ⚠ | capable; quota limits bite |
| `inclusionai/ling-3.1-flash:free` (CommandCode) | 81/110 | **81/81** | 42.7% ⚠ | throttled to death, never wrong |

**Round 2 — stress bench** (34 items, 490 calls, families S1–S7: constraint
soup, character mechanics, deep math, hard coding, multi-hop long-context,
verify-and-repair sycophancy traps, computed JSON transforms):

| lane | stress pass | Achilles heel |
|---|---|---|
| `longcat-2.5-preview:free` | 96/98 | one position slip, one reasoning runaway |
| `step-5-preview:free` | 95/98 | reasoning runaway → silent empty output |
| `omen-alpha` | 92/98 | can't stop writing — appends junk to perfect answers |
| `mimo-v2.6-flash-free` | 90/98 | counting + dropped characters |
| `ling-3.1-flash:free` | 52/98 | 45% 429s + runaway; zero wrong answers |

### What the models are actually bad at

1. **Micro-counting** — exact word counts, per-line lengths, position
   constraints ("10th word is vertigo, every odd-positioned word starts with
   s"). The #1 capability wall; nobody aced it consistently.
2. **Reasoning runaway → empty output** — reasoning models occasionally burn
   their entire token budget on chain-of-thought and emit *nothing*. One lane
   looped again at 8192 tokens and still produced no answer. Silent-empty is
   the most dangerous failure for automation.
3. **Extraneous output** — one lane wrote a *perfect* constrained sentence,
   then appended a verification table with checkmarks, blowing the word count
   from 20 to 192. Great content, unusable output format.
4. **Character-level drops** — single characters vanish in substitution and
   counting tasks (~1/3 of samples on the weakest lanes).
5. **Transform and sort-key slips** — scrambled word-order reversals, buggy
   iterative `flatten`, sorting by the computed value instead of the stated
   sort key.

## Quickstart

Python ≥ 3.9, **stdlib only**. No pip install.

```bash
# 1. Configure lanes in lanes.py (see LANE SETUP below)

# 2. Generate item banks from the fixed seed
python3 items.py      # round 1: items.jsonl (38 items)
python3 items_v2.py   # round 2: items-v2-stress.jsonl (34 items)

# 3. VERIFY GRADERS BEFORE SPENDING A SINGLE MODEL CALL
python3 selftest.py

# 4. Run (round-robin across lanes, concurrency 2 per lane)
python3 run.py --items items.jsonl         --out results/my-v1-run
python3 run.py --items items-v2-stress.jsonl --out results/my-stress-run

# 5. Scorecard: per-family accuracy, Wilson CIs, pass^k, reliability, latency
python3 report.py results/my-stress-run
```

`run.py --resume` skips already-recorded calls (incremental writes survive
crashes). `run.py --smoke` runs one item per family for a cheap sanity pass.

## Lane setup

`lanes.py` ships with the four hosted lanes of the original study; the fifth
(`mimo-v2.6-flash-free`, "D-mimo26-relay" in the published results) was served
through a self-hosted relay endpoint — bring your own endpoint to reproduce it.
Each lane is a dict of
model id, endpoint URL, and a headers factory — **add your own in five lines.**
The ones that mattered, measured the hard way:

| gotcha | detail |
|---|---|
| CommandCode + Cloudflare | non-browser User-Agent gets `403 error code: 1010`. Send a browser UA (the harness does). |
| Nous auth | OAuth token (`agent_key`) from a local `~/.hermes/auth.json` — **not** an env var. Model ids need the `provider/` prefix (`stepfun/…`, `meituan/…`); bare aliases 404. |
| OpenCode Go | requires an `x-opencode-session: <uuid>` header or 400s with `MissingSessionID`. One uuid per request is fine. |
| Reasoning models | `step-5`, `ling-3.1`, `omen-alpha` return chain-of-thought in `reasoning` / `reasoning_content`, final answer in `content`. Set `max_tokens ≥ 4096` or reasoning starves the answer to empty. |

Environment variables used: `HERMES_CUSTOM_COMMANDCODE_API_KEY`,
`OPENCODE_GO_API_KEY` (loaded from `~/.hermes/.env` if present). Nothing in
this repo reads or stores secret values itself.

## Method

- **Sampling:** temperature 0.7, top_p 1, `max_tokens` 4096 (truncations get
  one logged re-run at 8192), k = 3 per item (k = 2 for long-context).
  Identical system prompt across lanes: we measure **lanes as served**, not
  peak capability.
- **Interleaving:** calls round-robin across lanes so time-of-day and
  throttling hit all lanes equally. Concurrency 2 per lane — unpublished
  rate limits deserve politeness.
- **Reliability:** retries (2, jittered) on 429/5xx/transport are recorded,
  never absorbed. First-attempt success rate is reported beside accuracy.
- **Ranking (pre-registered):** per family, rank by pass^k (all k samples
  pass — cron needs *every* run right), then first-pass accuracy, then p95
  latency. A win requires a ≥2-item margin; below that it's a tie and the
  faster lane takes the slot. Any lane >5% first-attempt failures is flagged.
- **Statistics:** Wilson 95% intervals per family. With n ≈ 15–24 calls per
  family they are wide; treat family wins as directional, decisive only on
  large gaps. That is the honest price of "small".

Method shape follows HELM-style disaggregated scorecards (no composite
scalar) and assertion-first grading (every item programmatic).

## Reproducing the published runs

The item banks in this repo are **frozen** (`items-v1.jsonl`, `items.jsonl`,
`items-v2-stress.jsonl`) — reruns grade against the exact items behind the
published numbers, not against whatever the generators emit today. The
generators are seeded (`SEED = 20261009`) and self-contained.

| run dir | what |
|---|---|
| `results/20261009-full/` | round 1, 550 calls |
| `results/20261009-v11/` | round 1 confirmatory re-run of 2 repaired items |
| `results/20261009-stress/` | round 2, 490 calls |
| `results/20261009-stress-v21/` | round 2 confirmatory re-run of 1 repaired item |
| `results/20261009-042009-smoke/` | 30-call smoke pass |

Raw records are one JSONL line per call (response text, token usage, latency,
attempt history, checker verdict), so every score is re-auditable from the
artifacts alone. `report.py <run-dir>` regenerates any scorecard.

## Harness bug history (kept deliberately)

Three grader/generator bugs were caught by decomposing failures against the
checkers — two after runs, one in self-test before any call. They are part of
the case for the self-test discipline:

1. Long-context generator emitted the data table up to 3× (window bug); a
   model's defensible "1580" was graded wrong against a broken doc.
2. A hidden CSV assert (`parse_csv_line('') == ['']`) was unadvertised in the
   prompt; the `csv.reader` answer was defensible. Spec now states it.
3. A leet-transform generator joined a string's *characters* with spaces,
   inverting the item's ground truth; a model's sane answer was graded wrong.

## Repo map

```
items.py, items_v2.py   seeded item generators (F1–F6, S1–S7) + ground truth
items*.jsonl            frozen banks (what the published runs used)
checkers.py             programmatic graders (strict JSON, regex traps,
                        hidden-assert subprocess runner, S1 check interpreter)
selftest.py             grader validation — RUN THIS FIRST
lanes.py                lane adapters (endpoints, auth headers, gotchas)
run.py                  round-robin runner, incremental + resumable,
                        --lane for single-lane challenger runs,
                        --paid to include the paid-control lanes (spends
                        real money, see PAID_LANES in lanes.py)
report.py               scorecard + pre-registered decision rule
catalog_watch.py        catalog watcher + catalog-manifest.json baseline —
                        diffs the hosted catalogs so re-runs stay current
DESIGN.md               round 1 design (protocol, threats to validity)
RESULTS.md              both rounds' results + failure-mode taxonomy
```

## License

MIT — see [LICENSE](LICENSE).
