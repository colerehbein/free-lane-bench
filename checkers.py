#!/usr/bin/env python3
"""Programmatic graders for F1-F6. No LLM judges anywhere.

Every checker: (ok: bool, detail: str). F5's digit-run rule is a designed trap —
failures are listed verbatim in the report for manual spot-check.
"""
import json
import re
import os
import subprocess
import sys
import tempfile


def norm_str(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


# ---------------------------------------------------------------- F1
def check_f1(params, text):
    try:
        obj = json.loads(text.strip())
    except Exception as e:
        return False, f"json_parse: {e}"
    if not isinstance(obj, dict):
        return False, "not a JSON object"
    exp = params["expected"]
    if set(obj.keys()) != set(exp.keys()):
        return False, f"keys {sorted(obj.keys())} != {sorted(exp.keys())}"
    for k, v in exp.items():
        if obj[k] != v:
            return False, f"{k}: {obj[k]!r} != {v!r}"
    if params.get("forbidden_key") and params["forbidden_key"] in obj:
        return False, "forbidden key present"
    return True, "ok"


# ------------------------------------------------------------- F2/F4
def extract_answer(text):
    ms = re.findall(r"Answer:\s*([^\n]+)", text)
    return ms[-1].strip() if ms else None


def _answer_eq(params, text):
    a = extract_answer(text)
    if a is None:
        return False, "no Answer: line"
    got = a.replace(",", "").strip()
    exp = str(params["expected"]).strip()
    if got != exp:
        return False, f"got {got!r} != {exp!r}"
    return True, "ok"


def check_f2(params, text):
    return _answer_eq(params, text)


def check_f4(params, text):
    return _answer_eq(params, text)


# --------------------------------------------------------------- F3
def extract_code(text):
    m = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return m[-1] if m else text.strip()


def check_f3(params, text):
    code = extract_code(text)
    if not code:
        return False, "no code in response"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code + "\n" + "\n".join(params["asserts"]) + "\n")
        path = f.name
    try:
        p = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=10)
        if p.returncode == 0:
            return True, "ok"
        err = (p.stderr or p.stdout or "").strip().splitlines()
        return False, (err[-1] if err else f"exit {p.returncode}")[:200]
    except subprocess.TimeoutExpired:
        return False, "timeout 10s"
    finally:
        os.unlink(path)


# --------------------------------------------------------------- F5
ABSTAIN = re.compile(
    r"(not (mentioned|stated|specified|known|available|provided|disclosed|recorded|given|included)"
    r"|can'?t (tell|say|find|determine|answer)"
    r"|could ?n'?t (tell|say|find|determine|verify|answer)"
    r"|no (information|data|details|record|mention|indication)"
    r"|unknown|don'?t know|do not know|not enough (information|context|data)"
    r"|unable to (determine|find|verify|answer)"
    r"|never (disclosed|published|released|reported)"
    r"|there is no (record|evidence|information|mention)"
    r"|I'?m not aware|not aware"
    r"|is not (real|known|documented|mentioned|available|a real)"
    r"|isn'?t (real|known|documented|mentioned)"
    r"|fictional|imaginary|made[- ]up|does not exist|doesn'?t exist"
    r"|I don'?t have (that|this|the|enough|any)"
    r"|cannot (be )?(answer|determined|verified|found))",
    re.I)


def check_f5(params, text):
    if params["expected"] == "abstain":
        allowed = set(re.findall(r"\d+", params.get("question", "") + " " + params.get("doc", "")))
        stray = [d for d in re.findall(r"\d+", text) if d not in allowed]
        rfc = re.search(r"RFC\s*#?\s*\d+", text, re.I)
        if stray or rfc:
            return False, f"fabricated token(s): {stray or [rfc.group(0)]}"
        verdict = extract_answer(text)
        explicit = bool(verdict) and "unanswerable" in verdict.lower()
        if not (ABSTAIN.search(text) or explicit):
            return False, "no abstention marker"
        return True, "ok"
    if norm_str(params["expected"]) in norm_str(text):
        return True, "ok"
    return False, f"expected {params['expected']!r} not in answer"


# --------------------------------------------------------------- F6
def check_f6(params, text):
    try:
        obj = json.loads(text.strip())
    except Exception as e:
        return False, f"json_parse: {e}"
    if not isinstance(obj, dict):
        return False, "not a JSON object"
    exp = params["expected"]
    if set(obj.keys()) != set(exp.keys()):
        return False, f"keys {sorted(obj.keys())} != {sorted(exp.keys())}"
    for k, v in exp.items():
        got = obj[k]
        if isinstance(v, int):
            try:
                ok = int(str(got).replace(",", "")) == v
            except Exception:
                ok = False
        else:
            ok = norm_str(got) == norm_str(v)
        if not ok:
            return False, f"{k}: {got!r}"
    return True, "ok"


# ---------------------------------------------------------------- S1
check_s4 = check_f3  # same code-assert runner (params: {"asserts": [...]})

def _words(text):
    toks = re.findall(r"\S+", text)
    out = []
    for t in toks:
        w = t.strip(".,;:!?\"'()[]{}")
        if w:
            out.append(w)
    return out


def _sentences(text):
    return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]


def check_s1(params, text):
    words = _words(text)
    for c in params["checks"]:
        k = c["check"]
        if k == "sent_count":
            if len(_sentences(text)) != c["n"]:
                return False, f"sent_count {len(_sentences(text))} != {c['n']}"
        elif k == "each_sentence_starts":
            bad = [s for s in _sentences(text) if not s.startswith(c["word"])]
            if bad:
                return False, f"sentence not starting with {c['word']}: {bad[0][:40]!r}"
        elif k == "word_count_total":
            if len(words) != c["n"]:
                return False, f"words {len(words)} != {c['n']}"
        elif k == "token_count":
            n = len(re.findall(rf"\b{re.escape(c['token'])}\b", text.lower()))
            if n != c["n"]:
                return False, f"token {c['token']} count {n} != {c['n']}"
        elif k == "no_letter":
            bad = [w for w in words if c["letter"] in w.lower()]
            if bad:
                return False, f"letter {c['letter']!r} in {bad[0]!r}"
        elif k == "unique_initials":
            ini = [w[0].lower() for w in words if w]
            if len(set(ini)) != len(ini):
                return False, "duplicate initial letters"
        elif k == "contains_word":
            if c["token"].lower() not in [w.lower() for w in words]:
                return False, f"{c['token']} missing"
        elif k == "line_word_counts":
            lines = [l for l in text.strip().splitlines() if l.strip()]
            got = [len(_words(l)) for l in lines]
            if got != c["counts"]:
                return False, f"line words {got} != {c['counts']}"
        elif k == "all_words_start":
            bad = [w for w in words if not w.lower().startswith(c["letter"])]
            if bad:
                return False, f"word {bad[0]!r} doesn't start with {c['letter']}"
        elif k == "mention_order":
            low = text.lower()
            idxs = [low.find(t.lower()) for t in c["tokens"]]
            if any(x < 0 for x in idxs) or idxs != sorted(idxs):
                return False, f"mention order {idxs}"
        elif k == "exact_text":
            if text.strip() != c["text"]:
                return False, f"got {text.strip()[:60]!r}"
        elif k == "nth_word":
            if len(words) < c["index"] or words[c["index"] - 1].lower() != c["word"].lower():
                got = words[c["index"] - 1] if len(words) >= c["index"] else "<missing>"
                return False, f"word {c['index']} is {got!r}"
        elif k == "odd_words_start":
            bad = [words[i] for i in range(0, len(words), 2)
                   if not words[i].lower().startswith(c["letter"])]
            if bad:
                return False, f"odd-position word {bad[0]!r}"
        else:
            return False, f"unknown check {k}"
    return True, "ok"


# ------------------------------------------------------------ S2/S3/S5
def _answer_eq_norm(params, text):
    a = extract_answer(text)
    if a is None:
        return False, "no Answer: line"
    got = a.replace(",", "").strip()
    exp = str(params["expected"]).strip()
    if re.fullmatch(r"\d+\.\d+", exp) or re.fullmatch(r"\d+\.\d+", got):
        try:
            if abs(float(got) - float(exp)) <= 0.005:
                return True, "ok"
            return False, f"got {got} != {exp}"
        except ValueError:
            return False, f"got {got!r} != {exp!r}"
    if got != exp:
        return False, f"got {got!r} != {exp!r}"
    return True, "ok"


def check_s2(params, text):
    return _answer_eq_norm(params, text)


def check_s3(params, text):
    return _answer_eq_norm(params, text)


def check_s5(params, text):
    return _answer_eq_norm(params, text)


# ---------------------------------------------------------------- S6
BROKEN = re.compile(r"\b(broken|wrong|incorrect|not correct|buggy|flawed|does not|"
                    r"doesn'?t|fails|not accurate)\b", re.I)
RIGHT = re.compile(r"\bcorrect\b", re.I)


def check_s6(params, text):
    exp = params["expected"]
    verdict = extract_answer(text) or text
    if exp == "correct":
        ok = bool(RIGHT.search(verdict)) and not BROKEN.search(verdict)
        return (True, "ok") if ok else (False, f"verdict {verdict[:60]!r}")
    if exp == "broken":
        if not BROKEN.search(verdict):
            return False, f"didn't flag as broken: {verdict[:60]!r}"
        if params.get("asserts"):
            return check_s4(params, extract_code(text))
        return True, "ok"
    # numeric expected: find the number in the answer
    nums = re.findall(r"\d+(?:\.\d+)?", (extract_answer(text) or "").replace(",", ""))
    for n in nums:
        if abs(float(n) - float(exp)) <= 0.005:
            return True, "ok"
    return False, f"expected {exp}, answer line had {nums}"


# ---------------------------------------------------------------- S7
def _close(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= 0.011
    return a == b


def _deep_eq(a, b):
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_deep_eq(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_deep_eq(a[k], b[k]) for k in a)
    return _close(a, b)


def check_s7(params, text):
    try:
        obj = json.loads(text.strip())
    except Exception as e:
        return False, f"json_parse: {e}"
    if _deep_eq(obj, params["expected"]):
        return True, "ok"
    return False, f"got {str(obj)[:120]} != {str(params['expected'])[:120]}"


# ---------------------------------------------------------- S8/S9/S10/S11
def check_s8(params, text):
    a = extract_answer(text)
    if a is None:
        return False, "no Answer: line"
    got = a.replace(",", "").strip().lower()
    exp = str(params["expected"]).strip().lower()
    if got != exp:
        return False, f"got {got!r} != {exp!r}"
    return True, "ok"


check_s9 = check_f3  # code-assert runner (params: {"asserts": [...]})
check_s4 = check_f3  # same code-assert runner (params: {"asserts": [...]})

_SENT_SPLIT = re.compile(r"[.!?]+")


def check_s10(params, text):
    text = text.strip()
    sentences = [s for s in _SENT_SPLIT.split(text) if s.strip()]
    if len(sentences) != 3:
        return False, f"{len(sentences)} sentences != 3"
    if len(re.findall(r"\S+", text)) > 80:
        return False, "over 80 words"
    facts = params["facts"]
    src_digits = set(re.findall(r"\d+", f"{facts['duration']} {facts['users']}"))
    got_digits = set(re.findall(r"\d+", text))
    stray = got_digits - src_digits
    if stray:
        return False, f"invented number(s): {sorted(stray)}"
    for need in (str(facts["duration"]), str(facts["users"])):
        if need not in got_digits:
            return False, f"missing required number {need}"
    if facts["service"].lower() not in text.lower():
        return False, f"service {facts['service']} not mentioned"
    return True, "ok"


def _deep_eq_tol(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= 0.011
    return a == b


def _call_eq(got, exp):
    if not isinstance(got, dict):
        return False
    if exp["tool"] is None:
        return got.get("tool") in (None, "null") and not got.get("args")
    if got.get("tool") != exp["tool"]:
        return False
    args = got.get("args") or {}
    if set(args) != set(exp["args"]):
        return False
    return all(_deep_eq_tol(args[k], exp["args"][k]) for k in args)


def check_s11(params, text):
    try:
        obj = json.loads(text.strip())
    except Exception as e:
        return False, f"json_parse: {e}"
    exp = params["expected"]
    if isinstance(exp, list):
        if not isinstance(obj, list) or len(obj) != len(exp):
            return False, f"call count/shape: {str(obj)[:80]}"
        if not all(_call_eq(g, e) for g, e in zip(obj, exp)):
            return False, f"call mismatch: {str(obj)[:120]}"
        return True, "ok"
    if isinstance(obj, list):
        return False, "expected single call object, got array"
    if _call_eq(obj, exp):
        return True, "ok"
    return False, f"got {str(obj)[:120]}"


CHECKERS = {
    "F1": check_f1,
    "F2": check_f2,
    "F3": check_f3,
    "F4": check_f4,
    "F5": check_f5,
    "F6": check_f6,
    "S1": check_s1,
    "S2": check_s2,
    "S3": check_s3,
    "S4": check_s4,
    "S5": check_s5,
    "S6": check_s6,
    "S7": check_s7,
    "S8": check_s8,
    "S9": check_s9,
    "S10": check_s10,
    "S11": check_s11,
}


def grade(item, text):
    return CHECKERS[item["checker"]](item["params"], text or "")
