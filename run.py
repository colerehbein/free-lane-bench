#!/usr/bin/env python3
"""Round-robin runner for Free-Lane Bench v1.

Interleaves lanes (time-of-day effects hit all equally), concurrency 2 per lane,
retries recorded not absorbed, truncation re-run once at 8192.
Results: <outdir>/<lane>.jsonl — one record per call, checker verdict inline,
written INCREMENTALLY so a crash or Ctrl-C loses nothing. --resume skips
already-recorded (lane, item_id, sample) triples.
"""
import argparse
import concurrent.futures as cf
import json
import os
import random
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lanes  # noqa: E402
import checkers  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PAYLOAD = {
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
    ],
    "temperature": 0.7,
    "top_p": 1,
    "max_tokens": 4096,
}
FAMILY_TIMEOUT = {"F4": 240}  # 40k-token prompts need more than the 90s default


def one_call(lane_name, payload, timeout):
    """Returns (status:int, body, latency:float). Transport exceptions ->
    status 0 with the exception text (retryable, recorded)."""
    import time as _t
    t0 = _t.time()
    try:
        return lanes.call_lane(lane_name, payload, timeout=timeout)
    except Exception as e:
        return 0, f"transport: {type(e).__name__}: {e}", _t.time() - t0


def call_with_retries(lane_name, item, sample_idx, out_write, run_id):
    timeout = FAMILY_TIMEOUT.get(item["family"], 90)
    payload = dict(BASE_PAYLOAD)
    payload["messages"] = payload["messages"] + [
        {"role": "user", "content": item["prompt"]}]
    attempts = []
    status, body, lat = None, None, None
    for attempt in range(3):
        status, body, lat = one_call(lane_name, payload, timeout)
        attempts.append({"attempt": attempt, "status": status,
                         "latency": round(lat, 2)})
        if status == 200:
            break
        if status == 401 and "nous" in lane_name:
            continue  # lanes re-read auth.json fresh on next call
        if status == 429 or status >= 500 or status == 0:
            time.sleep(2 * (2 ** attempt) + random.uniform(0, 1))
            continue
        break  # 4xx other: no retry
    rec = {
        "run_id": run_id,
        "lane": lane_name,
        "model": lanes.LANES[lane_name]["model"],
        "item_id": item["id"],
        "family": item["family"],
        "sample": sample_idx,
        "attempts": attempts,
        "http_status": status,
        "latency_s": round(lat, 2) if lat is not None else None,
    }
    if status == 200 and isinstance(body, dict):
        ch = (body.get("choices") or [{}])[0]
        msg = ch.get("message") or {}
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
        rec["finish_reason"] = ch.get("finish_reason")
        rec["content"] = content
        rec["reasoning_chars"] = len(reasoning)
        rec["usage"] = body.get("usage")
        if ch.get("finish_reason") == "length":
            p2 = dict(payload)
            p2["max_tokens"] = 8192
            s2, b2, l2 = one_call(lane_name, p2, timeout)
            rec["rerun_truncation"] = {"status": s2, "latency_s": round(l2, 2)}
            if s2 == 200 and isinstance(b2, dict):
                ch2 = (b2.get("choices") or [{}])[0]
                msg2 = ch2.get("message") or {}
                rec["content"] = msg2.get("content") or ""
                rec["reasoning_chars"] = len(msg2.get("reasoning")
                                             or msg2.get("reasoning_content") or "")
                rec["finish_reason"] = ch2.get("finish_reason")
                rec["usage"] = b2.get("usage")
        ok, detail = checkers.grade(item, rec["content"])
        rec["pass"] = ok
        rec["detail"] = detail
    else:
        rec["content"] = ""
        rec["pass"] = False
        rec["detail"] = f"http {status}: {str(body)[:200]}"
    out_write(lane_name, rec)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true",
                    help="first item per family, k=1")
    ap.add_argument("--items", dest="items_file", default="items.jsonl",
                    help="item bank to run (e.g. items-v11.jsonl)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--resume", action="store_true",
                    help="skip (lane,item_id,sample) already in --out")
    ap.add_argument("--lane", default=None,
                    help="run only this lane (e.g. a new challenger from lanes.local.json)")
    ap.add_argument("--concurrency-per-lane", type=int, default=2)
    args = ap.parse_args()

    with open(os.path.join(HERE, args.items_file)) as f:
        items = [json.loads(l) for l in f]
    if args.smoke:
        seen, subset = set(), []
        for it in items:
            if it["family"] not in seen:
                seen.add(it["family"])
                subset.append(it)
        items = subset

    run_id = time.strftime("%Y%m%d-%H%M%S") + ("-smoke" if args.smoke else "")
    outdir = args.out or os.path.join(HERE, "results", run_id)
    os.makedirs(outdir, exist_ok=True)

    done_keys = set()
    if args.resume:
        for fn in os.listdir(outdir):
            if fn.endswith(".jsonl"):
                with open(os.path.join(outdir, fn)) as f:
                    for line in f:
                        r = json.loads(line)
                        done_keys.add((r["lane"], r["item_id"], r["sample"]))

    calls = []
    lane_names = [args.lane] if args.lane else lanes.LANE_ORDER
    if args.lane and args.lane not in lanes.LANES:
        sys.exit(f"unknown lane {args.lane!r}; known: {list(lanes.LANES)}")
    for i, it in enumerate(items):
        k = 1 if args.smoke else it["k"]
        for s in range(k):
            for lane_name in lane_names:
                if (lane_name, it["id"], s) in done_keys:
                    continue
                calls.append((i, s, lane_name, it))
    calls.sort(key=lambda c: (c[0], c[1], c[2]))
    print(f"{len(calls)} calls (skipped {len(done_keys)} done) -> {outdir}", flush=True)

    sems = {ln: threading.Semaphore(args.concurrency_per_lane) for ln in lanes.LANE_ORDER}
    locks = {ln: threading.Lock() for ln in lanes.LANE_ORDER}
    files = {ln: open(os.path.join(outdir, f"{ln}.jsonl"), "a") for ln in lanes.LANE_ORDER}
    counts = {"done": 0, "pass": 0}
    total = len(calls)

    def out_write(lane_name, rec):
        with locks[lane_name]:
            files[lane_name].write(json.dumps(rec) + "\n")
            files[lane_name].flush()
            counts["done"] += 1
            if rec.get("pass"):
                counts["pass"] += 1
            if counts["done"] % 25 == 0:
                print(f"  progress {counts['done']}/{total} "
                      f"(pass so far {counts['pass']})", flush=True)

    def worker(c):
        _, _, lane_name, it = c
        try:
            with sems[lane_name]:
                return call_with_retries(lane_name, it, c[1], out_write, run_id)
        except Exception as e:
            rec = {"run_id": run_id, "lane": lane_name,
                   "model": lanes.LANES[lane_name]["model"],
                   "item_id": it["id"], "family": it["family"], "sample": c[1],
                   "attempts": [], "http_status": None, "latency_s": None,
                   "content": "", "pass": False, "detail": f"harness error: {e!r}"}
            out_write(lane_name, rec)
            return rec

    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        list(ex.map(worker, calls))

    for f in files.values():
        f.close()
    summary = {}
    for ln in lanes.LANE_ORDER:
        n = p = 0
        path = os.path.join(outdir, f"{ln}.jsonl")
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    r = json.loads(line)
                    n += 1
                    p += bool(r.get("pass"))
        summary[ln] = {"calls": n, "pass": p}
    print(json.dumps(summary, indent=1))
    print(f"done: {outdir}")


if __name__ == "__main__":
    main()
