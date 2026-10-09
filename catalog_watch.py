#!/usr/bin/env python3
"""Catalog watcher for Free-Lane Bench — the cadence engine's trigger.

Polls the hosted model catalogs (Nous, CommandCode, OpenCode Go), diffs
against catalog-manifest.json, and reports new/removed ids with new
free-tier ids flagged. Read-only by default.

  python3 catalog_watch.py            # human-readable diff vs manifest
  python3 catalog_watch.py --check    # exit 1 if new free ids (cron hook)
  python3 catalog_watch.py --update   # accept current catalogs as baseline

The manifest is the accepted baseline: it only changes when you say so, so
the diff is always "since the last accepted run."
"""
import argparse
import datetime
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lanes  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "catalog-manifest.json")

CATALOGS = {
    "nous": (
        "https://inference-api.nousresearch.com/v1/models",
        lambda: {"Authorization": f"Bearer {lanes.nous_auth()}"},
    ),
    "commandcode": (
        "https://api.commandcode.ai/provider/v1/models",
        lambda: {"Authorization": f"Bearer {lanes.cc_key()}"},
    ),
    "opencode-go": (
        "https://opencode.ai/zen/go/v1/models",
        lambda: {"Authorization": f"Bearer {lanes.go_key()}"},
    ),
}


def fetch_ids(url, headers):
    req = urllib.request.Request(url, headers={
        "User-Agent": lanes.UA, "Accept": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
    return sorted(m["id"] for m in d.get("data", []))


def is_free(mid):
    return "free" in mid.lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if new free-tier ids appear")
    ap.add_argument("--update", action="store_true",
                    help="write current catalogs as the accepted baseline")
    args = ap.parse_args()

    current = {}
    errors = []
    for name, (url, hf) in CATALOGS.items():
        try:
            current[name] = fetch_ids(url, hf())
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")
            current[name] = []

    baseline = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            baseline = json.load(f).get("catalogs", {})

    diff = {}
    for name, ids in current.items():
        old = set(baseline.get(name, []))
        new = [i for i in ids if i not in old]
        gone = sorted(old - set(ids))
        if new or gone:
            diff[name] = {
                "new": new,
                "new_free": [i for i in new if is_free(i)],
                "removed": gone,
            }

    out = {
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "counts": {k: len(v) for k, v in current.items()},
        "baseline_present": bool(baseline),
        "diff": diff,
        "errors": errors,
    }
    print(json.dumps(out, indent=1))

    if args.update:
        with open(MANIFEST, "w") as f:
            json.dump({
                "generated_at": out["checked_at"],
                "catalogs": current,
            }, f, indent=1)
        print(f"[baseline updated: {MANIFEST}]", file=sys.stderr)

    new_free = [i for d in diff.values() for i in d["new_free"]] if baseline else []
    if args.check and new_free:
        sys.exit(1)


if __name__ == "__main__":
    main()
