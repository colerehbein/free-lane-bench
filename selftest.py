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
import items_v3  # noqa: E402

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

    # ---------------- S8 (answer format + generator sanity)
    for i in range(6):
        it = items_v3.gen_s8(i)
        exp = str(it["params"]["expected"])
        expect(it, f"work\nAnswer: {exp}", True, "expected answer")
        expect(it, "work\nAnswer: zzz-not-it", False, "wrong answer")
        if i < 2:
            assert exp in "1234", f"S8-{i} slot out of range"
        elif i < 4:
            assert exp in ("alice", "bob", "carol"), f"S8-{i} person?"
        else:
            assert exp in ("yes", "no"), f"S8-{i} verdict?"

    # ---------------- S9 (reference solutions pass, shipped bug fails)
    refs9 = {
        0: """def word_break(s, words):
    ws = set(words)
    ok = [False] * (len(s) + 1)
    ok[0] = True
    for i in range(1, len(s) + 1):
        for j in range(i):
            if ok[j] and s[j:i] in ws:
                ok[i] = True
                break
    return ok[len(s)]""",
        1: """def spiral_order(matrix):
    out = []
    while matrix:
        out += matrix.pop(0)
        matrix = [list(r) for r in list(zip(*matrix))[::-1]]
    return out""",
        2: """def balanced(s):
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for c in s:
        if c in '([{':
            stack.append(c)
        elif c in pairs:
            if not stack or stack.pop() != pairs[c]:
                return False
    return not stack""",
        3: """def top_k(records, k):
    return sorted(records, key=lambda r: (-r['score'], r['id']))[:k]""",
        4: """def max_subarray(xs):
    if not xs:
        return 0
    best = cur = xs[0]
    for x in xs[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best""",
    }
    for i in range(5):
        it = items_v3.gen_s9(i)
        expect(it, f"```python\n{refs9[i]}\n```", True, "reference solution")
    broken_kadane = ("def max_subarray(xs):\n    best = 0\n    cur = 0\n"
                     "    for x in xs:\n        cur = max(0, cur + x)\n"
                     "        best = max(best, cur)\n    return best")
    expect(items_v3.gen_s9(4), broken_kadane, False, "shipped bug must fail asserts")

    # ---------------- S10 (summary fidelity + hallucination detection)
    it = items_v3.gen_s10(0)
    f10 = it["params"]["facts"]
    good10 = (f"The {f10['service']} incident lasted {f10['duration']} minutes. "
              f"It affected {f10['users']} users in the region. Root cause has been addressed.")
    expect(it, good10, True, "3-sentence compliant summary")
    expect(it, good10 + " A fourth sentence here.", False, "4 sentences fail")
    expect(it, good10.replace(str(f10["users"]), "999999"), False, "invented number fails")
    expect(it, good10.replace(str(f10["duration"]), "x", 1), False, "missing required number")

    # ---------------- S11 (tool-call discipline)
    for i in range(5):
        it = items_v3.gen_s11(i)
        exp11 = it["params"]["expected"]
        expect(it, json.dumps(exp11), True, "exact call")
        expect(it, f"```json\n{json.dumps(exp11)}\n```", False, "fenced = fail")
    it = items_v3.gen_s11(0)
    expect(it, json.dumps({"tool": "send_email", "args": {"to": "x", "subject": "y"}}),
           False, "wrong tool fails")
    expect(it, json.dumps([it["params"]["expected"]]), False, "array vs object shape fails")

    print()
    if FAILS:
        print(f"SELF-TEST FAILURES ({len(FAILS)}):")
        for f in FAILS:
            print(" -", f)
        sys.exit(1)
    print("ALL SELF-TESTS PASS")


if __name__ == "__main__":
    main()
