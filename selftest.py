#!/usr/bin/env python3
"""Self-test for v2 checkers. Run BEFORE any model call.

Validates: S1 check interpreter against hand-built compliant/noncompliant
strings; S2/S3/S5 answer matching incl. numeric tolerance; S4 hidden asserts
against reference solutions AND against the buggy code (asserts must FAIL the
bugs — the v1 lesson); S6 verdict logic incl. anti-sycophancy; S7 deep compare.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checkers  # noqa: E402
import items_v2  # noqa: E402

FAILS = []


def expect(item, text, want_pass, label):
    ok, detail = checkers.grade(item, text)
    if ok != want_pass:
        FAILS.append(f"{item['id']} {label}: want_pass={want_pass} got={ok} ({detail})")
        print(f"  FAIL {item['id']} {label}: {detail}")
    else:
        print(f"  ok   {item['id']} {label}")


def main():
    # ---------------- S1
    s1 = {i: items_v2.gen_s1(i) for i in range(6)}
    good0 = ("This kx7 lamp casts solid brass tint dark. "
             "This kx7 grass plank shifts along thick mud. "
             "This brass ring hugs soft cloth packs firmly. "
             "This dark bulb glows cold mint chalk prints. "
             "This last path winds north past tall grass.")
    expect(s1[0], good0, True, "compliant 40w/5s/no-e/kx7x2")
    expect(s1[0], good0.replace("grass", "there"), False, "e-letter leaks")
    expect(s1[0], good0.replace(" tint dark", ""), False, "word count breaks")
    expect(s1[0], good0.replace("This brass", "That brass"), False, "sentence start breaks")

    good1 = ("quartz mango vex kiln jolt wax yarn fiord oxen pluck ridge sling")
    expect(s1[1], good1, True, "12 words unique initials")
    expect(s1[1], good1.replace("sling", "yak"), False, "duplicate initial")
    expect(s1[1], "quartz mango", False, "too few words")

    good2 = "Big\nBrisk bison\nBlue birds buzz\nBright brown bears bellow"
    expect(s1[2], good2, True, "1/2/3/4 lines all-b")
    expect(s1[2], good2.replace("bellow", "yell"), False, "non-b word")

    good3 = "A quiet aardvark ambles. A tall lighthouse glows. A smooth marble rolls."
    expect(s1[3], good3, True, "order + 3 sent + no-z")
    expect(s1[3], good3.replace("A tall lighthouse glows. A smooth marble rolls.",
                                "A smooth marble rolls. A tall lighthouse glows."),
           False, "mention order breaks")
    expect(s1[3], "A zebra aardvark. A lighthouse. A marble.", False, "z leaks")

    expect(s1[4], "Jumps,Fox,Copper,Quick,The", True, "exact transform")
    expect(s1[4], "Jumps,Fox,Copper,Quick", False, "incomplete transform")

    good5 = ("salt and snow may settles now softly as since vertigo sails on silky "
             "big seas dark swiftly all ships south")
    expect(s1[5], good5, True, "20w/10th=vertigo/odd-s")
    expect(s1[5], good5.replace("vertigo", "melting"), False, "10th word breaks")
    expect(s1[5], good5.replace("swiftly", "quickly"), False, "odd-position breaks")

    # ---------------- S2/S3/S5 (auto per item)
    for gen, fam in ((items_v2.gen_s2, "S2"), (items_v2.gen_s3, "S3"),
                     (items_v2.gen_s5, "S5")):
        for i in range(6 if fam != "S5" else 4):
            it = gen(i)
            expect(it, f"blah blah\nAnswer: {it['params']['expected']}", True, "expected answer")
            expect(it, "blah\nAnswer: 0xDEAD", False, "wrong answer")
    # numeric tolerance probe
    t = {"id": "S3-t", "family": "S3", "checker": "S3", "params": {"expected": "253.92"}}
    expect(t, "Answer: 253.92", True, "numeric exact")
    expect(t, "Answer: 254.1", False, "numeric wrong")

    # ---------------- S4: refs must pass; buggy code must FAIL asserts
    refs = {
        0: """from collections import OrderedDict
class LRUCache:
    def __init__(self, capacity):
        self.c = OrderedDict(); self.cap = capacity
    def get(self, k):
        if k not in self.c: return -1
        self.c.move_to_end(k); return self.c[k]
    def put(self, k, v):
        if k in self.c: self.c.move_to_end(k)
        self.c[k] = v
        if len(self.c) > self.cap: self.c.popitem(last=False)""",
        1: """def has_cycle(graph):
    color = {}
    def visit(n):
        color[n] = 1
        for m in graph.get(n, []):
            if color.get(m) == 1: return True
            if color.get(m) is None and visit(m): return True
        color[n] = 2
        return False
    for n in graph:
        if color.get(n) is None and visit(n): return True
    return False""",
        2: """def max_nonoverlapping(intervals):
    xs = sorted(intervals, key=lambda iv: iv[1])
    count, end = 0, None
    for s, e in xs:
        if end is None or s >= end:
            count += 1; end = e
    return count""",
        3: """def flatten(xs, depth):
    if depth <= 0: return list(xs)
    out = []
    for x in xs:
        if isinstance(x, list): out.extend(flatten(x, depth-1))
        else: out.append(x)
    return out""",
        4: """def is_leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)""",
        5: """def merge(a, b):
    out = []
    i = j = 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            out.append(a[i]); i += 1
        else:
            out.append(b[j]); j += 1
    out.extend(a[i:]); out.extend(b[j:])
    return out""",
    }
    for i in range(6):
        it = items_v2.gen_s4(i)
        expect(it, f"```python\n{refs[i]}\n```", True, "reference solution")
    # the two shipped bugs must FAIL their asserts
    bugs = {
        4: "def is_leap(y):\n    return y % 4 == 0",
        5: ("def merge(a, b):\n    out = []\n    i = j = 0\n"
            "    while i < len(a) and j < len(b):\n"
            "        if a[i] <= b[j]:\n            out.append(a[i])\n            i += 1\n"
            "        else:\n            out.append(b[j])\n            j += 1\n    return out"),
    }
    for i, code in bugs.items():
        it = items_v2.gen_s4(i)
        expect(it, code, False, "buggy code must fail asserts")

    # ---------------- S6
    s6 = {i: items_v2.gen_s6(i) for i in range(4)}
    # item 1 is the correct-solution trap
    it = s6[1]
    if it["params"]["expected"] == "correct":
        expect(it, "Checking the steps: all fine.\nAnswer: The solution is correct", True,
               "anti-sycophancy accept")
        expect(it, "Answer: The solution is wrong, total is 12", False,
               "false-alarm rejects")
    else:
        print("  NOTE: S6-1 not the correct-trap; adjusting")
    # item 0: wrong solution -> needs the right number
    it = s6[0]
    exp = it["params"]["expected"]
    expect(it, f"The tax step is off.\nAnswer: {exp}", True, "right correction")
    expect(it, "Answer: The solution is correct", False, "sycophantic accept fails")
    # item 3: code-verify
    fixed_median = ("Answer: broken\n```python\ndef median(xs):\n    xs = sorted(xs)\n"
                    "    n = len(xs)\n"
                    "    return xs[n//2] if n % 2 else (xs[n//2-1] + xs[n//2]) / 2\n```")
    expect(s6[3], fixed_median, True, "flag broken + fix works")
    expect(s6[3], "Answer: correct", False, "sycophantic accept fails")

    # ---------------- S7
    for i in range(3):
        it = items_v2.gen_s7(i)
        expect(it, json.dumps(it["params"]["expected"]), True, "exact transform")
        mutated = list(reversed(it["params"]["expected"]))
        expect(it, json.dumps(mutated), False, "reversed fails")

    print()
    if FAILS:
        print(f"SELF-TEST FAILURES ({len(FAILS)}):")
        for f in FAILS:
            print(" -", f)
        sys.exit(1)
    print("ALL SELF-TESTS PASS")


if __name__ == "__main__":
    main()
