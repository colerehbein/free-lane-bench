# Free-Lane Bench v1 — design

**Question this answers:** which free lane gets pinned for which job class in
Hermes routing. Not "which model is best" — there is no scalar winner here,
only per-job winners. The output is a **routing table**, not a leaderboard. The job classes are
role slots from prior local lane probing: simple / medium / hard / research /
**coding** — the
last one still untested on any free model — plus **structured-cron** (the
digest/extraction workload the Daily Brief runs).

Method shape: HELM-style disaggregated scorecards (no composite scalar) +
assertion-first grading (every scored item has a programmatic check; zero
LLM judges, zero vibes). All lanes $0, so the only scarce resource is
wall-clock and the free tiers' unpublished rate limits.

**Roster locked and smoke-verified live 2026-10-09** (each lane returned a real
completion to a real probe; gotchas are measured, not guessed):

| # | Model (exact id) | Lane | Endpoint | Auth | Smoke |
|---|---|---|---|---|---|
| A | `inclusionai/ling-3.1-flash:free` | CommandCode | `api.commandcode.ai/provider/v1` | `HERMES_CUSTOM_COMMANDCODE_API_KEY` | 200, 1.5s |
| B | `stepfun/step-5-preview:free` | Nous | `inference-api.nousresearch.com/v1` | OAuth `agent_key` in `~/.hermes/auth.json` | 200, 0.8s |
| C | `meituan/longcat-2.5-preview:free` | Nous | same | same | 200 (p50 ~2.2s prior probe; 14.5s cold) |
| D | `mimo-v2.6-flash-free` | self-hosted relay | self-hosted endpoint | n/a | 200 |
| E | `omen-alpha` | OpenCode Go | `opencode.ai/zen/go/v1` | `OPENCODE_GO_API_KEY` + `x-opencode-session: <uuid>` | 200, 0.7s |

Lane gotchas the harness must implement (each one cost a probe cycle to find):

1. **CommandCode + Cloudflare:** python-urllib's default UA gets `403 error
   code: 1010`. Send a browser User-Agent on every request.
2. **Nous auth is OAuth, not an API key.** No `NOUS*` env var exists. The
   credential is `credential_pool.nous[0].agent_key` (long-lived) /
   `access_token` (hourly) in `~/.hermes/auth.json`. Refresh flow: Hermes
   refreshes via `refresh_token`; harness reads the file fresh before each run
   and fails loudly if expired rather than sending a dead token.
3. **Nous routing rule:** model ids must carry the `provider/` prefix
   (`stepfun/...`, `meituan/...`) — bare aliases 404 (documented in a prior local probing note; re-confirmed by the failed
   bare probes).
4. **OpenCode Go needs a session header:** bare API-key POST → `400
   MissingSessionID`. `x-opencode-session: <any uuid4>` satisfies it.
   Stateless use is fine: one uuid per request works.
5. **Three of five are reasoning models** (A, B, E): chain-of-thought arrives
   in `reasoning` / `reasoning_content`, final answer in `content`. Score
   `content` only; record reasoning length as a "reasoning tax" metric. At
   small `max_tokens` the reasoning swallows the budget and `content` comes
   back empty with `finish_reason: length` — cap at 4096 upfront.
6. **Self-hosted relay lane (D):** its latency includes relay overhead; that
   overhead is real lane behavior for routing, so it stays in the
   measurements.

## Task families (38 items, same seed for all lanes)

Each item is generated from a template with a fixed seed (`20261009`) — random
numbers, names, canaries — so answers cannot be memorized and every checker
computes ground truth from the generator. Representative items shown; the full
bank is generated at run time.

**F1 — JSON discipline (8 items).** Echo a random 6-field record (nested
object + array) as strict JSON: exactly the requested keys, exact values, no
prose. Two items add a negative constraint ("do NOT include key Y").
*Checker:* `json.loads` (bare — fenced ```json``` blocks count as fail, since
cron pipes these outputs) + exact key-set + exact values.
*Job class:* structured-cron, delegation.

**F2 — Multi-step reasoning (8 items).** Generated word problems (3–4
operation chains over random ints), 2-step syllogisms with random nouns, and
date arithmetic ("3rd Tuesday of Nov 2027 + 11 days"). Answers forced into
`Answer: <x>` format.
*Checker:* exact token match on the extracted final answer.
*Job class:* hard, research.

**F3 — Coding (6 items).** Stdlib-only Python. Four write-a-function specs
(run-length encode/decode, interval merge, roman→int, CSV line parse handling
quoted commas) each with 3–5 hidden asserts; two fix-the-bug items (given
broken function + one failing visible test, output the corrected function).
*Checker:* hidden asserts run in a subprocess (`python -` , 10s timeout, no
network). Pass = all asserts green. **This is the family the free tier has
never been tested on** — a standing gap in every prior free-tier probe).
*Job class:* coding.

**F4 — Long-context retrieval (4 items).** ~15k and ~40k-token documents
assembled from generated filler with planted facts at 10/40/70/95% depth and a
number table mid-doc. Ask (a) the needle fact (exact) and (b) an aggregate
computed from the table (exact number).
*Checker:* exact match. *Job class:* research (tests the 1M-context claims on
B/C — retrieval, not marketing).

**F5 — Honesty under unanswerability (8 items).** Three fake-entity traps
("When did the IETF standardize the Quorvex protocol?" — any year `19xx/20xx`
or `RFC nnn` in the answer is a confabulation fail). Two control items over a
provided 3-sentence document that ARE answerable (exact-match; guards against
over-refusal). Three doc-unanswerable items (must abstain).
*Checker:* regex trap + abstention markers ("not (mentioned|stated|known)",
"can't (tell|say)", "no (information|data)", "unknown", "don't know") with
no fabricated token — or an explicit `Answer: unanswerable` verdict line (the
prompt-specified abstention format; added 2026-10-09 after the smoke run
showed a correct mimo refusal grading as fail). Every failure manually spot-checked — cheap at this
scale (≈60 failing responses worst case).
*Job class:* hard, research.

**F6 — Extraction fidelity (4 items).** Generated 5-fact incident report
(who/what/when/where/impact number) in prose → extract to JSON schema.
*Checker:* exact field match. *Job class:* structured-cron (the Daily Brief
shape).

## Sampling protocol

- `temperature 0.7, top_p 1, max_tokens 4096`, minimal system prompt
  ("You are a helpful assistant."), no tools, no streaming. Same denominator
  for all five — we are measuring **lanes as served**, not peak capability.
- **k = 3** per item for F1/F2/F3/F5/F6; **k = 2** for F4 (long-context calls
  are the expensive ones). 110 calls per model, 550 total.
- Round-robin across lanes (A→E, repeat) so time-of-day and throttling hit all
  lanes equally. Concurrency 2 per lane — free-tier limits are unpublished;
  this is a benchmark, not a load test.
- Timeout 90s. Up to 2 retries on 429/5xx with jittered backoff — **retries
  are recorded as a reliability signal, never silently absorbed.** A
  `finish_reason: length` at the 4096 cap is flagged and re-run once at 8192.
- Run manifest pins: item-seed, model ids, endpoint URLs, date, git hash of
  the harness. Free models get swapped silently upstream (we've watched
  longcat-2.0→2.5 and ling-3.0→3.1 happen); the manifest makes every result
  re-attributable.

## Metrics

| Metric | Definition | Why |
|---|---|---|
| Family accuracy | % strict-pass per family, Wilson 95% CI | the capability signal |
| **pass^k** | % of items where ALL k samples pass | routing needs *every* run right (cron, delegation); one lucky pass is noise |
| First-attempt success | % HTTP 200 without retry | free-lane reliability is itself a routing input |
| Truncation / empty-content rate | `finish_reason=length` after re-run, or empty `content` | catches reasoning-budget starvation |
| Latency p50/p95 per family | request→completion, lane-honest (relay overhead included for lane D) | a throttled free lane loses to a paid one |
| Reasoning tax | mean reasoning tokens, mean total tokens per item | free ≠ unlimited; verbosity burns quota windows |

## Pre-registered decision rule

1. Per family, rank by **pass^k**, then first-pass accuracy, then p95 latency.
2. A family "win" requires the leader to beat the runner-up by **≥ 2 items**
   (6 calls at k=3) on pass count. Below that the family is declared a
   **tie** and the lower-latency lane gets the slot.
3. Reliability gate: any lane with >5% first-attempt HTTP failure gets flagged
   in the routing table regardless of accuracy.
4. Routing table output = slot → winner from the matching family:
   simple (F1), medium (F6), hard (F2/F5), research (F4), coding (F3),
   structured-cron (F1+F6).
5. No aggregate score is published. If a lane wins ≥3 families it may be
   named the default free lane — that is a routing statement, not a quality
   claim.

## Threats to validity (stated up front)

- **Small n.** Per-family CIs will be ±15–25pp. Family wins are directional;
  only large gaps are decisive. That is the correct price of "small".
- **Snapshot drift.** Free catalogs mutate (they already have). Results are
  dated; re-run when `models` endpoints change hash. The bench is cheap —
  re-running is the maintenance story, not versioning gymnastics.
- **Template sensitivity.** Neutral prompts may understate models tuned for
  specific templates. Accepted: equal denominators are what fairness requires
  when the question is "which lane serves MY traffic shape".
- **Reasoning-budget interplay (A/B/E).** Cap-raise re-runs change sampling;
  only truncations get re-run, and re-runs are logged as such.
- **Nous throttling is unpublished.** 429s are reported separately from real
  failures so a throttled run degrades a reliability score, not an accuracy
  score.

## Harness spec (build target)

```
free-model-bench/
  DESIGN.md            # this file
  items.py             # seeded generators (F1–F6) → items.jsonl
  lanes.py             # 5 lane adapters (auth + headers per gotchas above)
  run.py               # round-robin runner → results/<date>/<lane>.jsonl
  checkers.py          # F1–F6 programmatic graders (incl. subprocess code runner)
  report.py            # scorecard.md + routing table + Wilson CIs
```

Stdlib only (urllib/json/subprocess/statistics) — no pip, no judge models, no
cost. Raw responses kept in full JSONL (a few MB) so every score is re-auditable
from the artifact alone.

**Budget:** $0. **Wall clock:** ~45–75 min for the full 550-call matrix at
concurrency 2 per lane.
