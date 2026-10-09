#!/usr/bin/env python3
"""Scorecard + routing table for Free-Lane Bench v1.

Per family: strict end-to-end accuracy AND capability accuracy over HTTP-200
calls only (a throttled call degrades reliability, not capability — DESIGN.md),
Wilson 95% CI, pass^k item rate, first-attempt HTTP success, truncations,
latency p50/p95, reasoning tax. Decision rule pre-registered in DESIGN.md:
pass^k ranking, >=2-item margin for a win, else tie -> lower p95;
reliability gate >5% first-attempt failure flagged. Routing slots take the
family winner of their family (majority for multi-family slots, p95 tiebreak).
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANE_ORDER = ["A-ling31-commandcode", "B-step5-nous", "C-longcat25-nous",
              "D-mimo26-relay", "E-omenalpha-opencodego"]
FAMILIES = []  # derived from data after load()
SLOT_FAMILIES = {
    "simple": ["F1"], "medium": ["F6"], "hard": ["F2", "F5"],
    "research": ["F4"], "coding": ["F3"], "structured-cron": ["F1", "F6"],
}


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return max(0.0, (c - m) / d), min(1.0, (c + m) / d)


def pctl(xs, q):
    if not xs:
        return 0.0
    xs = sorted(xs)
    i = min(len(xs) - 1, int(round(q * (len(xs) - 1))))
    return xs[i]


def load(results_dir):
    per_lane = {}
    for ln in LANE_ORDER:
        recs = []
        for path in sorted(glob.glob(os.path.join(results_dir, f"{ln}*.jsonl"))):
            with open(path) as f:
                recs += [json.loads(l) for l in f]
        per_lane[ln] = recs
    return per_lane


def main():
    results_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(
        glob.glob(os.path.join(HERE, "results", "*")))[-1]
    per_lane = load(results_dir)
    fams = sorted({r["family"] for recs in per_lane.values() for r in recs})
    FAMILIES.clear()
    FAMILIES.extend(fams)
    out = []
    out.append(f"# Free-Lane Bench v1 — scorecard\n\nresults: `{results_dir}`\n")

    fam_stats = {f: {} for f in FAMILIES}
    for fam in FAMILIES:
        for ln in LANE_ORDER:
            recs = [r for r in per_lane[ln] if r["family"] == fam]
            if not recs:
                continue
            calls = len(recs)
            passes = sum(1 for r in recs if r.get("pass"))
            lo, hi = wilson(passes, calls)
            ok_calls = [r for r in recs if r["http_status"] == 200]
            cap_passes = sum(1 for r in ok_calls if r.get("pass"))
            by_item = {}
            for r in recs:
                by_item.setdefault(r["item_id"], []).append(bool(r.get("pass")))
            item_passk = sum(1 for v in by_item.values() if all(v))
            first_ok = sum(1 for r in recs if r["attempts"] and r["attempts"][0]["status"] == 200)
            trunc = sum(1 for r in recs if r.get("rerun_truncation")
                        or r.get("finish_reason") == "length")
            lats = [r["latency_s"] for r in recs if r.get("latency_s")]
            rat = [r["reasoning_chars"] for r in recs if r.get("reasoning_chars")]
            fam_stats[fam][ln] = {
                "calls": calls, "passes": passes, "acc": passes / calls,
                "ci": (lo, hi), "ok_calls": len(ok_calls),
                "cap_acc": (cap_passes / len(ok_calls)) if ok_calls else 0.0,
                "items": len(by_item), "passk": item_passk,
                "first_ok": first_ok, "trunc": trunc,
                "p50": pctl(lats, 0.5), "p95": pctl(lats, 0.95),
                "reason_mean": (sum(rat) / len(rat)) if rat else 0,
            }
        out.append(f"\n## {fam}\n")
        out.append("| lane | e2e acc | cap acc (200s) | Wilson 95% CI | pass^k items | 1st-attempt 200 | trunc | p50 s | p95 s | reason chars |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        for ln in LANE_ORDER:
            s = fam_stats[fam].get(ln)
            if not s:
                continue
            out.append(f"| {ln} | {s['passes']}/{s['calls']} = {s['acc']*100:.0f}% "
                       f"| {s['cap_acc']*100:.0f}% ({s['ok_calls']} calls) "
                       f"| [{s['ci'][0]*100:.0f},{s['ci'][1]*100:.0f}] "
                       f"| {s['passk']}/{s['items']} "
                       f"| {s['first_ok']}/{s['calls']} | {s['trunc']} "
                       f"| {s['p50']:.1f} | {s['p95']:.1f} | {s['reason_mean']:.0f} |")

    out.append("\n## Family winners (pre-registered rule: pass^k first, >=2-item margin, else tie -> lower p95)\n")
    fam_winner = {}
    for fam in FAMILIES:
        st = fam_stats[fam]
        if not st:
            continue
        ranked = sorted(st.items(), key=lambda kv: (-kv[1]["passk"], -kv[1]["acc"], kv[1]["p95"]))
        (l1, s1), (l2, s2) = ranked[0], ranked[1]
        if s1["passk"] - s2["passk"] >= 2:
            fam_winner[fam] = l1
            out.append(f"- **{fam}: {l1}** ({s1['passk']}/{s1['items']} pass^k; margin {s1['passk']-s2['passk']})")
        else:
            fam_winner[fam] = l1 if s1["p95"] <= s2["p95"] else l2
            out.append(f"- {fam}: TIE ({l1} vs {l2}, margin {s1['passk']-s2['passk']}) -> "
                       f"**{fam_winner[fam]}** on lower p95")

    out.append("\n## Reliability gate (flag >5% first-attempt non-200)\n")
    for ln in LANE_ORDER:
        recs = per_lane[ln]
        if not recs:
            continue
        first_ok = sum(1 for r in recs if r["attempts"] and r["attempts"][0]["status"] == 200)
        rate = 1 - first_ok / len(recs)
        flag = " ⚠ FLAG" if rate > 0.05 else ""
        out.append(f"- {ln}: {rate*100:.1f}% first-attempt failures ({len(recs)-first_ok}/{len(recs)}){flag}")

    out.append("\n## Routing table (slot -> family winner; multi-family slots: majority, p95 tiebreak)\n")
    out.append("| slot | families | winner |")
    out.append("|---|---|---|")
    for slot, fams in SLOT_FAMILIES.items():
        wins = [fam_winner[f] for f in fams if f in fam_winner]
        if not wins:
            continue
        counts = {}
        for w in wins:
            counts[w] = counts.get(w, 0) + 1
        top = max(counts.values())
        cands = [ln for ln, c in counts.items() if c == top]
        if len(cands) == 1:
            winner = cands[0]
        else:
            def slot_p95(ln):
                return sum(fam_stats[f][ln]["p95"] for f in fams if ln in fam_stats[f])
            winner = min(cands, key=slot_p95)
        out.append(f"| {slot} | {'+'.join(fams)} | **{winner}** |")

    out.append("\n## Graded misses (failure-mode queue; http-200 calls that failed the checker)\n")
    for ln in LANE_ORDER:
        for r in per_lane[ln]:
            if r["http_status"] == 200 and not r.get("pass"):
                out.append(f"- [{ln}] {r['item_id']} sample {r['sample']} [{r['family']}]: {r['detail']}")
                out.append(f"  > {str(r.get('content',''))[:220]}")

    text = "\n".join(out) + "\n"
    path = os.path.join(results_dir, "scorecard.md")
    with open(path, "w") as f:
        f.write(text)
    print(text)
    print(f"[written {path}]")


if __name__ == "__main__":
    main()
