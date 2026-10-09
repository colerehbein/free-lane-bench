#!/usr/bin/env python3
"""Stress item generators S1-S7 for Free-Lane Bench v2 — capability limits.

Design goal: items hard enough that failure is the signal. Families:
S1 constraint-soup generation, S2 counting/character mechanics, S3 deep math,
S4 hard coding, S5 multi-hop long-context w/ distractors, S6 verify-and-repair
(anti-sycophancy), S7 computed JSON transformation.
All deterministic from SEED; ground truth computed by generators.
"""
import json
import random
import re
import os
import datetime
from fractions import Fraction
from math import gcd

SEED = 20261009
K_DEFAULT = 3
K_LONGCTX = 2
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "items-v2-stress.jsonl")

END = " End your reply with a line: Answer: <answer>"


def rng(*parts):
    return random.Random(f"{SEED}-{'-'.join(map(str, parts))}")


# ---------------------------------------------------------------- S1
def gen_s1(i):
    if i == 0:
        prompt = ("Write exactly 5 sentences. Every sentence must start with the word 'This'. "
                  "The total number of whitespace-separated words must be exactly 40. "
                  "The token 'kx7' must appear exactly twice. No word may contain the letter 'e' "
                  "or 'E'. Punctuation is allowed.")
        checks = [
            {"check": "sent_count", "n": 5},
            {"check": "each_sentence_starts", "word": "This"},
            {"check": "word_count_total", "n": 40},
            {"check": "token_count", "token": "kx7", "n": 2},
            {"check": "no_letter", "letter": "e"},
        ]
    elif i == 1:
        prompt = ("Reply with exactly 12 whitespace-separated words. The first letter of each word "
                  "must be different from the first letter of every other word. The word 'quartz' "
                  "must appear among them.")
        checks = [
            {"check": "word_count_total", "n": 12},
            {"check": "unique_initials"},
            {"check": "contains_word", "token": "quartz"},
        ]
    elif i == 2:
        prompt = ("Write 4 lines. Line 1 must have exactly 1 word, line 2 exactly 2 words, "
                  "line 3 exactly 3 words, line 4 exactly 4 words. Every word must start with "
                  "the letter 'b' or 'B'.")
        checks = [
            {"check": "line_word_counts", "counts": [1, 2, 3, 4]},
            {"check": "all_words_start", "letter": "b"},
        ]
    elif i == 3:
        prompt = ("Write exactly 3 sentences. In order of appearance the sentences must mention "
                  "'aardvark', 'lighthouse', and 'marble' (case-insensitive). No word in the "
                  "reply may contain the letter 'z' or 'Z'.")
        checks = [
            {"check": "sent_count", "n": 3},
            {"check": "mention_order", "tokens": ["aardvark", "lighthouse", "marble"]},
            {"check": "no_letter", "letter": "z"},
        ]
    elif i == 4:
        prompt = ("Take the sentence 'the quick copper fox jumps' and output its words in reverse "
                  "order, comma-separated with no spaces, each word capitalized (first letter "
                  "upper, rest lower). Output ONLY that result.")
        checks = [{"check": "exact_text", "text": "Jumps,Fox,Copper,Quick,The"}]
    else:
        prompt = ("Write a single sentence of exactly 20 whitespace-separated words. The 10th word "
                  "must be exactly 'vertigo'. Every odd-positioned word (1st, 3rd, 5th, ... 19th) "
                  "must start with 's' or 'S'.")
        checks = [
            {"check": "word_count_total", "n": 20},
            {"check": "nth_word", "index": 10, "word": "vertigo"},
            {"check": "odd_words_start", "letter": "s"},
        ]
    return {"id": f"S1-{i:02d}", "family": "S1", "k": K_DEFAULT,
            "prompt": prompt, "checker": "S1", "params": {"checks": checks}}


# ---------------------------------------------------------------- S2
def gen_s2(i):
    r = rng("S2", i)
    if i == 0:
        base = r.choice(["parallel", "balloon", "committee", "mississippi", "raccoon", "llama"])
        letter = r.choice([c for c in set(base) if base.count(c) >= 2])
        word = base + letter * r.randint(1, 3)
        expected = str(word.lower().count(letter))
        prompt = (f"How many times does the letter '{letter}' appear in the word '{word}'? "
                  "Count every occurrence. Only the letter itself, case-insensitive." + END)
    elif i == 1:
        s = "".join(r.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(12))
        idx = r.randint(1, 12)
        expected = s[idx - 1]
        prompt = (f"What is the character at position {idx} (1-indexed) of the string '{s}'? "
                  "Give the single character." + END)
    elif i == 2:
        while True:
            w1 = "".join(r.choice("abcdefgrst") for _ in range(r.randint(4, 7)))
            w2 = "".join(r.choice("abcdefgrst") for _ in range(r.randint(3, 6)))
            leftover = "".join(c for c in sorted(w1) if c not in w2)
            if leftover:
                break
        expected = leftover
        prompt = (f"Take the letters of '{w1}', sort them alphabetically, and concatenate them. "
                  f"Then remove every letter that also appears in '{w2}'. "
                  "What string remains?" + END)
    elif i == 3:
        words = [r.choice(["stellar", "garden", "orbit", "lantern", "quarry", "meadow",
                           "harbor", "signal", "copper", "fabric", "oak", "drift"]) for _ in range(14)]
        clauses = []
        for j in range(0, 14, 2):
            seg = " ".join(words[j:j + 2])
            if r.random() < 0.5:
                seg = seg.replace(" ", "-", 1)
            if r.random() < 0.4:
                seg = seg + "'s"
            clauses.append(seg + r.choice([",", ";", ":"]))
        text = " ".join(clauses) + " " + words[-1] + " end."
        expected = str(len(re.findall(r"[A-Za-z]+", text)))
        prompt = ("Count the words in this text. Rule: a word is any maximal run of letters "
                  f"A-Z/a-z (hyphens, apostrophes and punctuation split words).\n\nText: \"{text}\"\n"
                  "How many words are there by this rule?" + END)
    else:
        phrase = r.choice(["Ambitious Ode", "Quiet Ember", "Iron Anchor",
                           "Open Window", "Silver Oak"])
        table = {"a": "4", "A": "4", "e": "3", "E": "3", "i": "1", "I": "1",
                 "o": "0", "O": "0"}
        expected = "".join(table.get(c, c) for c in phrase).upper()
        prompt = (f"In the phrase '{phrase}', replace every 'a' or 'A' with '4', every 'e' or 'E' "
                  "with '3', every 'i' or 'I' with '1', every 'o' or 'O' with '0' (keep spaces), "
                  "then uppercase the result." + END)
    return {"id": f"S2-{i:02d}", "family": "S2", "k": K_DEFAULT,
            "prompt": prompt, "checker": "S2", "params": {"expected": expected}}


# ---------------------------------------------------------------- S3
def gen_s3(i):
    r = rng("S3", i)
    if i == 0:
        a, b = r.randint(1000, 9999), r.randint(100, 999)
        expected = str(a * b)
        prompt = f"Compute {a} x {b} exactly. Give the exact integer." + END
    elif i == 1:
        base, exp, m = r.randint(2, 9), r.randint(10, 30), r.randint(50, 200)
        expected = str(pow(base, exp, m))
        prompt = (f"What is {base}^{exp} mod {m}? Give the remainder as an integer." + END)
    elif i == 2:
        b_val = r.randint(100, 900)
        p1, p2 = r.randint(5, 30), r.randint(5, 30)
        a_val = b_val * (1 + p1 / 100)
        c_val = round(a_val * (1 - p2 / 100), 2)
        expected = f"{c_val:.2f}"
        prompt = (f"B is {b_val}. A is {p1}% more than B. C is A minus {p2}% of A. "
                  "Give C rounded to exactly 2 decimal places." + END)
    elif i == 3:
        y1, y2 = sorted(r.sample(range(2025, 2033), 2))
        d1 = datetime.date(y1, r.randint(1, 12), r.randint(1, 28))
        d2 = datetime.date(y2, r.randint(1, 12), r.randint(1, 28))
        expected = str((d2 - d1).days)
        prompt = (f"How many days are there from {d1.isoformat()} up to but not including "
                  f"{d2.isoformat()}?" + END)
    elif i == 4:
        while True:
            f1 = Fraction(r.randint(1, 12), r.randint(2, 15))
            f2 = Fraction(r.randint(1, 12), r.randint(2, 15))
            s = f1 + f2
            if s.denominator != 1 and s.numerator < 100:
                break
        expected = f"{s.numerator}/{s.denominator}"
        prompt = (f"Compute {f1.numerator}/{f1.denominator} + {f2.numerator}/{f2.denominator} "
                  "as a reduced fraction a/b." + END)
    else:
        while True:
            frs = [Fraction(r.randint(2, 19), r.randint(3, 20)) for _ in range(3)]
            if len(set(frs)) == 3:
                break
        mx = max(frs)
        expected = f"{mx.numerator}/{mx.denominator}"
        prompt = ("Which is the largest of these three fractions? Answer with the fraction "
                  "exactly as given: " + ", ".join(f"{f.numerator}/{f.denominator}" for f in frs) + END)
    return {"id": f"S3-{i:02d}", "family": "S3", "k": K_DEFAULT,
            "prompt": prompt, "checker": "S3", "params": {"expected": expected}}


# ---------------------------------------------------------------- S4
S4_ITEMS = [
    {
        "prompt": ("Implement class LRUCache with __init__(self, capacity: int), get(key) -> value "
                   "or -1 if absent, and put(key, value). Capacity is at least 1. On put with a "
                   "full cache, evict the least-recently-used key; get and put both count as use. "
                   "Updating an existing key counts as use. Return code only."),
        "asserts": [
            "c = LRUCache(2)\nc.put('a', 1)\nc.put('b', 2)\nassert c.get('a') == 1",
            "c = LRUCache(2)\nc.put('a', 1)\nc.put('b', 2)\nc.get('a')\nc.put('c', 3)\nassert c.get('b') == -1\nassert c.get('a') == 1\nassert c.get('c') == 3",
            "c = LRUCache(1)\nc.put('x', 9)\nc.put('y', 8)\nassert c.get('x') == -1\nassert c.get('y') == 8",
            "c = LRUCache(2)\nc.put('a', 1)\nc.put('a', 2)\nc.put('b', 3)\nc.put('c', 4)\nassert c.get('a') == -1\nassert c.get('b') == 3",
        ],
    },
    {
        "prompt": ("Write a function has_cycle(graph: dict) -> bool detecting a cycle in a directed "
                   "graph given as {node: [neighbors]}. Nodes not present as keys have no outgoing "
                   "edges. Return code only."),
        "asserts": [
            "assert has_cycle({'a': ['b'], 'b': ['a']}) == True",
            "assert has_cycle({'a': ['b'], 'b': []}) == False",
            "assert has_cycle({}) == False",
            "assert has_cycle({'a': ['a']}) == True",
            "assert has_cycle({'a': ['b'], 'b': ['c'], 'c': ['a'], 'd': ['a']}) == True",
            "assert has_cycle({'a': ['b'], 'b': ['c'], 'c': []}) == False",
        ],
    },
    {
        "prompt": ("Write a function max_nonoverlapping(intervals: list) -> int returning the "
                   "maximum count of mutually non-overlapping closed intervals [s, e]. Intervals "
                   "touching at a point (e.g. [1,2] and [2,3]) do NOT overlap. Return code only."),
        "asserts": [
            "assert max_nonoverlapping([[1,3],[2,4],[5,7],[6,8]]) == 2",
            "assert max_nonoverlapping([[1,2],[2,3]]) == 2",
            "assert max_nonoverlapping([]) == 0",
            "assert max_nonoverlapping([[1,10],[2,3],[4,5]]) == 2",
            "assert max_nonoverlapping([[5,6],[1,2],[3,4]]) == 3",
        ],
    },
    {
        "prompt": ("Write a function flatten(xs, depth: int) -> list flattening nested lists to "
                   "exactly the given depth (depth=1 collapses one level). Non-list elements stay "
                   "as-is. Examples: flatten([1,[2,[3]]], 1) == [1,2,[3]]; "
                   "flatten([1,[2,[3]]], 2) == [1,2,3]. Return code only."),
        "asserts": [
            "assert flatten([1,[2,[3]]], 1) == [1,2,[3]]",
            "assert flatten([1,[2,[3]]], 2) == [1,2,3]",
            "assert flatten([1,2], 1) == [1,2]",
            "assert flatten([[1,[2]],[3]], 2) == [1,2,3]",
            "assert flatten([[1,[2]],[3]], 1) == [1,[2],3]",
            "assert flatten([1,[2,[3]]], 0) == [1,[2,[3]]]",
        ],
    },
    {
        "prompt": ("This function is claimed to be a correct leap-year check, but it has a bug:\n"
                   "```python\ndef is_leap(y):\n    return y % 4 == 0\n```\n"
                   "Failing test: assert is_leap(1900) == False (it returns True). "
                   "Return the corrected function, code only."),
        "asserts": [
            "assert is_leap(1900) == False",
            "assert is_leap(2000) == True",
            "assert is_leap(2024) == True",
            "assert is_leap(2023) == False",
            "assert is_leap(2100) == False",
        ],
    },
    {
        "prompt": ("This function is claimed to merge two sorted lists, but it has a bug:\n"
                   "```python\ndef merge(a, b):\n    out = []\n    i = j = 0\n"
                   "    while i < len(a) and j < len(b):\n"
                   "        if a[i] <= b[j]:\n            out.append(a[i])\n            i += 1\n"
                   "        else:\n            out.append(b[j])\n            j += 1\n"
                   "    return out\n```\n"
                   "Failing test: assert merge([1,2],[3]) == [1,2,3] (it returns [1,2]). "
                   "Return the corrected function, code only."),
        "asserts": [
            "assert merge([1,2],[3]) == [1,2,3]",
            "assert merge([],[1,2]) == [1,2]",
            "assert merge([5],[]) == [5]",
            "assert merge([1,3,5],[2,4,6]) == [1,2,3,4,5,6]",
            "assert merge([],[]) == []",
        ],
    },
]


def gen_s4(i):
    spec = S4_ITEMS[i]
    return {"id": f"S4-{i:02d}", "family": "S4", "k": K_DEFAULT,
            "prompt": spec["prompt"], "checker": "S4",
            "params": {"asserts": spec["asserts"]}}


# ------------------------------------------------------- S5 long-context
ADJ = ["amber", "quiet", "distant", "narrow", "brisk", "hollow", "steady", "faint",
       "granite", "copper", "silent", "ruddy"]
NOUN = ["harbor", "falcon", "arch", "signal", "meadow", "lantern", "ridge", "orchard",
        "anchor", "prism", "canyon", "beacon"]
VERB = ["drifted", "rotated", "descended", "clustered", "diverged", "circled",
        "halted", "converged"]
FILLER_TPL = [
    "The {adj} {noun} {verb} the {adj2} {noun2} {num} times before the {noun3} {verb2} at dawn.",
    "During the {adj} season every {noun} {verb2} toward the {noun2}, and the {adj2} {noun3} follows.",
    "A {adj} {noun2} {verb} exactly {num} meters past the {noun3} whenever the {adj2} {noun} appears.",
    "Observers noted that the {noun3} {verb2} while the {adj} {noun} stayed near the {adj2} {noun2}.",
    "The record shows {num} {adj} {noun2} for each {noun3} that {verb} through the {adj2} {noun}.",
]


def filler_sentence(r):
    return r.choice(FILLER_TPL).format(
        adj=r.choice(ADJ), adj2=r.choice(ADJ), noun=r.choice(NOUN),
        noun2=r.choice(NOUN), noun3=r.choice(NOUN), verb=r.choice(VERB),
        verb2=r.choice(VERB), num=r.randint(2, 900))


def doc_with_lines(r, target_words, lines):
    """Filler doc with (depth, line) insertions; depths in (0,1)."""
    placements = sorted(lines)
    sentences = []
    cur = 0
    pi = 0
    while cur < target_words:
        while pi < len(placements) and cur >= placements[pi][0] * target_words:
            sentences.append(placements[pi][1])
            pi += 1
        s = filler_sentence(r)
        sentences.append(s)
        cur += len(s.split()) + 2
    while pi < len(placements):
        sentences.append(placements[pi][1])
        pi += 1
    return " ".join(sentences)


def gen_s5(i):
    r = rng("S5", i)
    if i == 0:
        code_num = r.randint(100, 999)
        port = r.randint(1000, 9999)
        doc = doc_with_lines(r, 20000, [
            (0.10, f"The access code for section Alpha is QR-{code_num}."),
            (0.90, f"The maintenance port number is {port}."),
        ])
        expected = str(code_num + port)
        question = ("What is the sum of the numeric part of the access code (the digits after the "
                    "dash) and the maintenance port number?" + END)
    elif i == 1:
        codes = [f"K{r.randint(1,9)}{chr(65+r.randint(0,25))}" for _ in range(3)]
        doc = doc_with_lines(r, 20000, [
            (0.25, f"The first candidate code, {codes[0]}, was rejected."),
            (0.50, f"The second candidate code, {codes[1]}, was withdrawn."),
            (0.75, f"The third candidate code, {codes[2]}, was adopted."),
        ])
        expected = codes[2]
        question = "What is the adopted candidate code?" + END
    elif i == 2:
        rows = [r.randint(20, 400) for _ in range(6)]
        table_block = ("S5 units table:\n" + "\n".join(f"R{i+1}: {n}" for i, n in enumerate(rows)))
        doc = doc_with_lines(r, 20000, [(0.50, table_block)])
        expected = str(max(rows) - min(rows))
        question = ("What is the difference between the largest and the smallest value in the "
                    "S5 units table?" + END)
    else:
        token = f"zqx{r.randint(10000, 99999)}"
        doc = doc_with_lines(r, 20000, []) + f" {token}"
        expected = token
        question = "What is the very last word of the document (after the final space)?" + END
    prompt = f"Document:\n{doc}\n\nQuestion: {question}"
    return {"id": f"S5-{i:02d}", "family": "S5", "k": K_LONGCTX,
            "prompt": prompt, "checker": "S5", "params": {"expected": expected}}


# ---------------------------------------------------------------- S6
def gen_s6(i):
    r = rng("S6", i)
    if i < 3:  # solution verification; one of the three is actually CORRECT
        base = r.randint(100, 500)
        d_pct = r.choice([10, 12, 15, 20])
        t_pct = r.choice([5, 8, 15])
        step1 = base * d_pct / 100
        disc = base - step1
        step2 = round(disc * t_pct / 100, 2)
        final = round(disc + step2, 2)
        correct = (i == 1)  # middle item is the anti-sycophancy trap
        if correct:
            shown_final = final
            shown_step2 = step2
        else:
            shown_step2 = round(step2 + r.choice([-3.5, 2.0, 4.5]), 2)
            shown_final = round(disc + shown_step2, 2)
        solution = (f"Step 1: {d_pct}% of {base} = {step1:.2f}. Discounted price = {disc:.2f}. "
                    f"Step 2: {t_pct}% of {disc:.2f} = {shown_step2}. "
                    f"Total = {shown_final}.")
        prompt = (f"A jacket costs {base}. First a {d_pct}% discount is applied, then {t_pct}% tax "
                  f"is added on the discounted price. A student wrote:\n\"{solution}\"\n"
                  "If the student's solution is wrong, give the correct total. If it is correct, "
                  "reply 'correct'." + END)
        params = {"expected": "correct" if correct else f"{final:.2f}",
                  "kind": "answer"}
    else:
        prompt = ("This function is claimed to return the median of a non-empty list of numbers, "
                  "correct for both odd and even lengths (for even length: the mean of the two "
                  "middle values):\n"
                  "```python\ndef median(xs):\n    return sorted(xs)[len(xs)//2]\n```\n"
                  "Is the claim correct? If it is broken, reply 'broken' and give the corrected "
                  "function. If correct, reply 'correct'.")
        params = {"expected": "broken",
                  "kind": "code",
                  "asserts": [
                      "assert median([1,2,3]) == 2",
                      "assert median([1,2,3,4]) == 2.5",
                      "assert median([5]) == 5",
                      "assert median([4,1]) == 2.5",
                  ]}
    return {"id": f"S6-{i:02d}", "family": "S6", "k": K_DEFAULT,
            "prompt": prompt, "checker": "S6", "params": params}


# ---------------------------------------------------------------- S7
def gen_s7(i):
    r = rng("S7", i)
    recs = [{"id": f"R{r.randint(100, 999)}",
             "qty": r.randint(1, 40),
             "price": round(r.uniform(2, 80), 2),
             "region": r.choice(["north", "south", "east"])} for _ in range(4)]
    if i == 0:
        sel = [x for x in recs if x["region"] == "north"]
        sel.sort(key=lambda x: (-x["qty"], x["id"]))
        expected = [{"id": x["id"], "total": round(x["qty"] * x["price"], 2)} for x in sel]
        prompt = ("Given these records:\n" + json.dumps(recs) + "\n"
                  "Return a JSON array (no prose, no code fences) of the records whose region is "
                  "'north', sorted by qty descending (ties: id ascending). Each element must be "
                  "an object with keys 'id' and 'total', where total = qty * price rounded to 2 "
                  "decimals.")
        params = {"expected": expected}
    elif i == 1:
        totals = {}
        for x in recs:
            totals[x["region"]] = totals.get(x["region"], 0) + x["qty"]
        expected = dict(sorted(totals.items()))
        prompt = ("Given these records:\n" + json.dumps(recs) + "\n"
                  "Return a JSON object (no prose, no code fences) mapping each region to the "
                  "sum of qty over its records. Keys sorted alphabetically.")
        params = {"expected": expected}
    else:
        top = sorted(recs, key=lambda x: (-x["qty"], x["id"]))[:2]
        expected = [x["id"] for x in top]
        prompt = ("Given these records:\n" + json.dumps(recs) + "\n"
                  "Return a JSON array (no prose, no code fences) of the ids of the two records "
                  "with the highest qty (ties broken by id ascending).")
        params = {"expected": expected}
    return {"id": f"S7-{i:02d}", "family": "S7", "k": K_DEFAULT,
            "prompt": prompt, "checker": "S7", "params": params}


def main():
    items = []
    items += [gen_s1(i) for i in range(6)]
    items += [gen_s2(i) for i in range(5)]
    items += [gen_s3(i) for i in range(6)]
    items += [gen_s4(i) for i in range(6)]
    items += [gen_s5(i) for i in range(4)]
    items += [gen_s6(i) for i in range(4)]
    items += [gen_s7(i) for i in range(3)]
    with open(OUT, "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
    total = sum(it["k"] for it in items)
    print(f"wrote {len(items)} items -> {OUT}; calls per lane: {total}")
    for fam in sorted({it["family"] for it in items}):
        sub = [it for it in items if it["family"] == fam]
        print(f"  {fam}: {len(sub)} items, k={sub[0]['k']}, calls={sum(x['k'] for x in sub)}")


if __name__ == "__main__":
    main()
