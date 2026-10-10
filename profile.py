#!/usr/bin/env python3
"""Strengths/weaknesses profiler for Free-Lane Bench.

Aggregates every run dir it is given (v1 capability, v2 stress, v3 aptitude,
paid control) into per-model aptitude profiles: where each lane leads the
field, where it trails, and which items actually separate the models. The
S2-04 frozen-bank artifact is excluded (void item, see RESULTS.md).

  python3 profile.py [results/DIR results/DIR ...]
"""
import glob
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
VOID_ITEMS = {"S2-04"}  # frozen-bank garbled-phrase artifact; use items-v21
FAMILY_ORDER = ["F1", "F2", "F3", "F4", "F5", "F6",
                "S1", "S2", "S3", "S4", "S5", "S6", "S7",
                "S8", "S9", "S10", "S11"]
FAMILY_LABEL = {
    "F1": "JSON discipline", "F2": "reasoning", "F3": "coding",
    "F4": "long-ctx retrieval", "F5": "honesty", "F6": "extraction",
    "S1": "constraint soup", "S2": "char mechanics", "S3": "deep math",
    "S4": "hard coding", "S5": "multi-hop long-ctx", "S6": "verify/repair",
    "S7": "computed JSON", "S8": "deep reasoning", "S9": "harder coding",
    "S10": "summary fidelity", "S11": "tool-call discipline",
}
LANE_SHORT = {
    "A-ling31-commandcode": "A ling-3.1", "B-step5-nous": "B step-5",
    "C-longcat25-nous": "C longcat-2.5", "D-mimo26-relay": "D mimo-2.6",
    "E-omenalpha-opencodego": "E omen-alpha", "P-mimopro-paid": "P mimo-pro",
    "Q-deepseekflash-paid": "Q deepseek-f4.1", "R-glmflash-paid": "R glm-f5.3",
}


def load_records(dirs):
    recs = []
    for d in dirs:
        for path in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
            with open(path) as f:
                for line in f:
                    r = json.loads(line)
                    if r.get("item_id") in VOID_ITEMS:
                        continue
                    recs.append(r)
    return recs


def main():
    dirs = sys.argv[1:] or [
        os.path.join(HERE, "results", "20261009-full"),
        os.path.join(HERE, "results", "20261009-stress"),
        os.path.join(HERE, "results", "20261009-aptitude"),
        os.path.join(HERE, "results", "20261009-paid-control"),
    ]
    recs = load_records(dirs)
    lanes = sorted({r["lane"] for r in recs},
                   key=lambda ln: list(LANE_SHORT).index(ln) if ln in LANE_SHORT else 99)
    # drop lanes with zero delivered calls (e.g. billing-dead): no capability data
    lanes = [ln for ln in lanes
             if any(r["http_status"] == 200 for r in recs if r["lane"] == ln)]

    # per lane x family: item pass^k and call accuracy over graded calls
    fam = defaultdict(lambda: defaultdict(list))
    for r in recs:
        fam[r["lane"]][r["family"]].append(r)

    out = []
    out.append("# Free-Lane Bench — strengths and weaknesses\n")
    out.append("Aggregated across every run (S2-04 excluded as a known void item).")
    out.append("Cell = items passing all k samples (pass^k), the consistency grade.\n")

    # matrix
    out.append("| family | " + " | ".join(LANE_SHORT.get(ln, ln) for ln in lanes) + " |")
    out.append("|---" * (len(lanes) + 1) + "|")
    lane_scores = defaultdict(list)  # lane -> [(family, passk_rate)]
    for f in FAMILY_ORDER:
        row = [f"{f} {FAMILY_LABEL[f]}"]
        for ln in lanes:
            rs = fam[ln].get(f)
            if not rs:
                row.append("—")
                continue
            by_item = defaultdict(list)
            for r in rs:
                by_item[r["item_id"]].append(bool(r.get("pass")))
            pk = sum(1 for v in by_item.values() if all(v))
            row.append(f"{pk}/{len(by_item)}")
            lane_scores[ln].append((f, pk / len(by_item)))
        out.append("| " + " | ".join(row) + " |")

    # per-family field leader + discriminating items
    out.append("\n## What separates the field\n")
    for f in FAMILY_ORDER:
        scored = []
        for ln in lanes:
            rs = fam[ln].get(f)
            if not rs:
                continue
            by_item = defaultdict(list)
            for r in rs:
                by_item[r["item_id"]].append(bool(r.get("pass")))
            pk = sum(1 for v in by_item.values() if all(v))
            scored.append((pk / len(by_item), ln))
        if not scored:
            continue
        scored.sort(reverse=True)
        top = [ln for s, ln in scored if s == scored[0][0]]
        if scored[0][0] - (scored[1][0] if len(scored) > 1 else 0) > 0.30 or scored[0][0] == 1.0:
            out.append(f"- **{f} {FAMILY_LABEL[f]}**: leads "
                       + ", ".join(LANE_SHORT.get(x, x) for x in top)
                       + f" ({scored[0][0]*100:.0f}%), trails "
                       + f"{LANE_SHORT.get(scored[-1][1], scored[-1][1])} ({scored[-1][0]*100:.0f}%)")

    out.append("\n## Discriminating items (split the real field)\n")
    item_lane = defaultdict(dict)
    for r in recs:
        if r["lane"] not in lanes:
            continue
        if r["http_status"] != 200:
            item_lane[r["item_id"]][r["lane"]] = None  # no answer, transport
        else:
            item_lane[r["item_id"]][r["lane"]] = bool(r.get("pass"))
    for item, lm in sorted(item_lane.items()):
        good = [LANE_SHORT.get(k, k) for k, v in lm.items() if v is True]
        bad = [LANE_SHORT.get(k, k) for k, v in lm.items() if v is False]
        dead = [LANE_SHORT.get(k, k) for k, v in lm.items() if v is None]
        if good and bad:
            line = f"- {item}: passed by {', '.join(good)}; **missed by** {', '.join(bad)}"
            if dead:
                line += f" (no answer: {', '.join(dead)})"
            out.append(line)

    # per-model profile
    out.append("\n## Per-model profiles\n")
    for ln in lanes:
        rs = [r for r in recs if r["lane"] == ln]
        scored = sorted(lane_scores[ln], key=lambda kv: -kv[1])
        strong = [f for f, s in scored if s >= 0.99]
        weak = [f for f, s in scored if s < 0.85]
        graded = [r for r in rs if r["http_status"] == 200]
        lats = sorted(r["latency_s"] for r in graded if r.get("latency_s"))
        p50 = lats[len(lats) // 2] if lats else 0
        p95 = lats[int(len(lats) * 0.95)] if lats else 0
        first_ok = sum(1 for r in rs if r["attempts"] and r["attempts"][0]["status"] == 200)
        cap = sum(1 for r in graded if r.get("pass"))
        out.append(f"\n### {LANE_SHORT.get(ln, ln)} ({ln})")
        out.append(f"- clean sweeps: {', '.join(f + ' ' + FAMILY_LABEL[f] for f in strong) or 'none'}")
        out.append(f"- below 85%: {', '.join(f + ' ' + FAMILY_LABEL[f] for f in weak) or 'none'}")
        out.append(f"- capability on delivered calls: {cap}/{len(graded)}"
                   f" | first-attempt success: {first_ok}/{len(rs)}"
                   f" | latency p50/p95: {p50:.1f}s / {p95:.1f}s")

    text = "\n".join(out) + "\n"
    path = os.path.join(HERE, "STRENGTHS.md")
    with open(path, "w") as f:
        f.write(text)
    print(text)
    print(f"[written {path}]")


if __name__ == "__main__":
    main()
