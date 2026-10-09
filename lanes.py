#!/usr/bin/env python3
"""Lane adapters for Free-Lane Bench. Hosted lanes verified live 2026-10-09.

Gotchas encoded here (each measured, not guessed):
- CommandCode: Cloudflare 403 error 1010 on non-browser UA -> browser UA required.
- Nous: OAuth agent_key from ~/.hermes/auth.json (never an env var); ids need
  provider/ prefix. Re-read auth.json on 401 (Hermes refreshes the token).
- OpenCode Go: requires x-opencode-session header (any uuid4 per request).

To add a lane (any OpenAI-compatible endpoint), append to LANES:

    "my-lane": {
        "model": "model-id-here",
        "url": "https://my-endpoint.example/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {os.environ['MY_KEY']}"},
    },

The original study also included one self-hosted relay lane
("D-mimo26-relay" in the published results) serving mimo-v2.6-flash-free —
bring your own endpoint to reproduce it.
"""
import json
import os
import uuid
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
HOME = os.path.expanduser("~")


def _load_env_file():
    p = os.path.join(HOME, ".hermes", ".env")
    if not os.path.exists(p):
        return
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


_load_env_file()


def nous_auth():
    with open(os.path.join(HOME, ".hermes", "auth.json")) as f:
        c = json.load(f)["credential_pool"]["nous"][0]
    return c.get("agent_key") or c.get("access_token")


def go_key():
    k = os.environ.get("OPENCODE_GO_API_KEY")
    if k:
        return k
    with open(os.path.join(HOME, ".local", "share", "opencode", "auth.json")) as f:
        return json.load(f)["opencode-go"]["key"]


def cc_key():
    return os.environ["HERMES_CUSTOM_COMMANDCODE_API_KEY"]


LANES = {
    "A-ling31-commandcode": {
        "model": "inclusionai/ling-3.1-flash:free",
        "url": "https://api.commandcode.ai/provider/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {cc_key()}"},
    },
    "B-step5-nous": {
        "model": "stepfun/step-5-preview:free",
        "url": "https://inference-api.nousresearch.com/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {nous_auth()}"},
    },
    "C-longcat25-nous": {
        "model": "meituan/longcat-2.5-preview:free",
        "url": "https://inference-api.nousresearch.com/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {nous_auth()}"},
    },
    "E-omenalpha-opencodego": {
        "model": "omen-alpha",
        "url": "https://opencode.ai/zen/go/v1/chat/completions",
        "headers": lambda: {
            "Authorization": f"Bearer {go_key()}",
            "x-opencode-session": str(uuid.uuid4()),
        },
    },
}

LANE_ORDER = list(LANES.keys())

# Ad-hoc lanes (new challengers) live in lanes.local.json — gitignored, never
# committed. Shape: {"my-lane": {"model": "...", "url": "...",
# "bearer_env": "MY_KEY", "headers": {"X-Extra": "value"}}}
_LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lanes.local.json")


def _local_headers(spec):
    def h():
        out = dict(spec.get("headers") or {})
        env = spec.get("bearer_env")
        if env:
            out["Authorization"] = f"Bearer {os.environ[env]}"
        return out
    return h


if os.path.exists(_LOCAL):
    with open(_LOCAL) as _f:
        for _name, _spec in json.load(_f).items():
            LANES[_name] = {
                "model": _spec["model"],
                "url": _spec["url"],
                "headers": _local_headers(_spec),
            }
    LANE_ORDER = list(LANES.keys())

# Paid control lanes (P/Q/R): the cheapest smart models, for the
# free-vs-paid comparison. Served via the Nous portal at pay-as-you-go rates
# (est. total <$1 for a full two-bank run on all three). CommandCode carries
# the same ids but its credit pool was empty at wiring time; the ids are
# identical, so any OpenAI-compatible host works. These SPEND REAL MONEY:
# `run.py --paid` includes them, never part of the default run.
PAID_LANES = {
    "P-mimopro-paid": {
        "model": "xiaomi/mimo-v2.6-pro",
        "url": "https://inference-api.nousresearch.com/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {nous_auth()}"},
    },
    "Q-deepseekflash-paid": {
        "model": "deepseek/deepseek-v4.1-flash",
        "url": "https://inference-api.nousresearch.com/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {nous_auth()}"},
    },
    "R-glmflash-paid": {
        "model": "z-ai/glm-5.3-flash",
        "url": "https://inference-api.nousresearch.com/v1/chat/completions",
        "headers": lambda: {"Authorization": f"Bearer {nous_auth()}"},
    },
}


def include_paid():
    LANES.update(PAID_LANES)
    for name in PAID_LANES:
        if name not in LANE_ORDER:
            LANE_ORDER.append(name)


def call_lane(lane_name, payload, timeout=90):
    """POST one chat completion. Returns (status:int, body:dict|bytes, latency:float).

    Raises URLError/timeout upward; HTTP errors return their code + raw body.
    """
    import time
    lane = LANES[lane_name]
    headers = {"Content-Type": "application/json", "User-Agent": UA}
    headers.update(lane["headers"]())
    body = dict(payload)
    body["model"] = lane["model"]
    req = urllib.request.Request(lane["url"], data=json.dumps(body).encode(),
                                 headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200, json.loads(r.read()), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:2000], time.time() - t0
