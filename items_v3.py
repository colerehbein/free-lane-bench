#!/usr/bin/env python3
"""Aptitude-battery generators S8-S11 for Free-Lane Bench v3.

Goal: discriminate strengths at the TOP of the field (v1/v2 hit ceiling on
most families) and measure aptitudes nobody has tested yet.

S8 deep reasoning ladder (difficulty tiers): L1 slot-assignment constraint
puzzles, L2 three-entity logic deduction, L3 knights-and-knaves. Every item
is generated with a brute-force solver, so ground truth is exact and the
solution is guaranteed unique.
S9 hard coding (tiered): word break (DP), spiral order, bracket matching,
top-k with tie-break rules, and a subtle all-negative bug fix.
S10 summary fidelity: 3-sentence summary of a generated incident report with
programmatic hallucination detection (no digit token outside the source).
S11 tool-call discipline: valid JSON calls with correctly extracted args,
number-words, multi-call ordering, and no-call traps.
"""
import datetime
import itertools
import json
import os
import random

SEED = 20261009
K_DEFAULT = 3
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "items-v3-aptitude.jsonl")

END = " End your reply with a line: Answer: <answer>"


def rng(*parts):
    return random.Random(f"{SEED}-{'-'.join(map(str, parts))}")


# ---------------------------------------------------------------- S8
SLOTS = [1, 2, 3, 4]
TASKS = ["alpha", "bravo", "charlie", "delta"]


def _slot_puzzle(r):
    """Random task->slot assignment + constraints that pin it uniquely."""
    while True:
        truth = list(TASKS)
        r.shuffle(truth)  # truth[i] = task in slot i+1
        pos = {t: SLOTS[i] for i, t in enumerate(truth)}
        cons = []
        # candidate constraints (all true in `pos`)
        cand = []
        for t in TASKS:
            cand.append(("direct", t, pos[t]))
        for a, b in itertools.permutations(TASKS, 2):
            if pos[a] < pos[b]:
                cand.append(("before", a, b))
            if pos[a] == pos[b] + 1:
                cand.append(("rightafter", a, b))
        r.shuffle(cand)
        for c in cand:
            cons.append(c)
            if _count_slot_solutions(cons) == 1 and len(cons) >= 3:
                q = r.choice(TASKS)
                return pos, cons, q
            if len(cons) >= 5:
                break


def _count_slot_solutions(cons):
    n = 0
    for perm in itertools.permutations(SLOTS):
        pos = {t: perm[i] for i, t in enumerate(TASKS)}
        ok = True
        for c in cons:
            if c[0] == "direct" and pos[c[1]] != c[2]:
                ok = False
            elif c[0] == "before" and pos[c[1]] >= pos[c[2]]:
                ok = False
            elif c[0] == "rightafter" and pos[c[1]] != pos[c[2]] + 1:
                ok = False
        if ok:
            n += 1
    return n


def _logic_puzzle(r):
    people = ["alice", "bob", "carol"]
    pets = ["dog", "cat", "fish"]
    colors = ["red", "blue", "green"]
    for _ in range(400):
        pet_of = dict(zip(people, r.sample(pets, 3)))
        color_of = dict(zip(people, r.sample(colors, 3)))
        clues = []
        cand = []
        for p in people:
            cand.append(("owns", p, pet_of[p]))
            cand.append(("notowns", p, r.choice([x for x in pets if x != pet_of[p]])))
            cand.append(("likes", p, color_of[p]))
        for pet in pets:
            owner = [p for p in people if pet_of[p] == pet][0]
            cand.append(("petcolor", pet, color_of[owner]))
        r.shuffle(cand)
        for c in cand:
            clues.append(c)
            if _count_logic_solutions(clues) == 1 and len(clues) >= 4:
                return pet_of, color_of, clues
            if len(clues) >= 6:
                break


def _count_logic_solutions(clues):
    people = ["alice", "bob", "carol"]
    pets = ["dog", "cat", "fish"]
    colors = ["red", "blue", "green"]
    n = 0
    for pp in itertools.permutations(pets):
        for cc in itertools.permutations(colors):
            pet_of = dict(zip(people, pp))
            color_of = dict(zip(people, cc))
            ok = True
            for c in clues:
                if c[0] == "owns" and pet_of[c[1]] != c[2]:
                    ok = False
                elif c[0] == "notowns" and pet_of[c[1]] == c[2]:
                    ok = False
                elif c[0] == "likes" and color_of[c[1]] != c[2]:
                    ok = False
                elif c[0] == "petcolor":
                    pet, col = c[1], c[2]
                    if color_of[[p for p in people if pet_of[p] == pet][0]] != col:
                        ok = False
            if ok:
                n += 1
    return n


def _knights_puzzle(r):
    names = ["amy", "ben", "cara"]
    for _ in range(400):
        is_knight = {x: r.random() < 0.5 for x in names}
        stmts = []
        for speaker in names:
            kind = r.choice(["is_knight", "is_knave", "both_knights"])
            others = [x for x in names if x != speaker]
            target, target2 = others[0], others[1]
            if kind == "is_knight":
                claim = is_knight[target]  # "target is a knight" is true iff knight
                stmts.append((speaker, "X_IS_KNIGHT", target, claim))
            elif kind == "is_knave":
                claim = not is_knight[target]
                stmts.append((speaker, "X_IS_KNAVE", target, claim))
            else:
                claim = is_knight[target] and is_knight[target2]
                stmts.append((speaker, "BOTH_KNIGHTS", (target, target2), claim))
        # a knight's claim must be TRUE, a knave's FALSE
        consistent = True
        for speaker, _, _, claim in stmts:
            if is_knight[speaker] != claim:
                consistent = False
        if not consistent:
            continue
        if _count_knight_solutions(stmts) == 1:
            q = r.choice(names)
            return is_knight, stmts, q


def _count_knight_solutions(stmts):
    names = ["amy", "ben", "cara"]
    n = 0
    for bits in itertools.product([True, False], repeat=3):
        world = dict(zip(names, bits))
        ok = True
        for speaker, kind, target, _claim in stmts:
            if kind == "X_IS_KNIGHT":
                claim = world[target]
            elif kind == "X_IS_KNAVE":
                claim = not world[target]
            else:
                claim = world[target[0]] and world[target[1]]
            if world[speaker] != claim:  # knight <=> claim true
                ok = False
        if ok:
            n += 1
    return n


def gen_s8(i):
    for attempt in range(50):
        r = rng("S8", i, attempt)
        if i < 2:  # L1 slots
            pos, cons, q = _slot_puzzle(r)
            text = ". ".join({
                "direct": f"The {c[1]} task is in slot {c[2]}",
                "before": f"The {c[1]} task is before the {c[2]} task",
                "rightafter": f"The {c[1]} task is exactly one slot after the {c[2]} task",
            }[c[0]] for c in cons) + "."
            prompt = (f"Four tasks (alpha, bravo, charlie, delta) occupy slots 1 to 4, one per "
                      f"slot. {text}\nWhich slot does the {q} task occupy?" + END)
            expected = str(pos[q])
            break
        elif i < 4:  # L2 logic
            pet_of, color_of, clues = _logic_puzzle(r)
            text = ". ".join({
                "owns": f"{c[1].capitalize()} owns the {c[2]}",
                "notowns": f"{c[1].capitalize()} does not own the {c[2]}",
                "likes": f"{c[1].capitalize()} likes the color {c[2]}",
                "petcolor": f"The {c[1]} owner likes the color {c[2]}",
            }[c[0]] for c in clues) + "."
            owner = [p for p, x in pet_of.items() if x == "fish"][0]
            prompt = (f"Alice, Bob, and Carol each own one pet (dog, cat, fish) and each like "
                      f"one color (red, blue, green). {text}\nWho owns the fish?" + END)
            expected = owner
            break
        else:  # L3 knights and knaves
            is_knight, stmts, q = _knights_puzzle(r)
            text = ". ".join(
                f"{s.capitalize()} says: " + (
                    f"{t.capitalize()} is a knight" if k == "X_IS_KNIGHT" else
                    f"{t.capitalize()} is a knave" if k == "X_IS_KNAVE" else
                    f"{t[0].capitalize()} and {t[1].capitalize()} are both knights")
                for s, k, t, _ in stmts) + "."
            prompt = (f"Amy, Ben, and Cara are each either a knight (always tells the truth) or "
                      f"a knave (always lies). {text}\nIs {q.capitalize()} a knight?" + END)
            expected = "yes" if is_knight[q] else "no"
            break
    return {"id": f"S8-{i:02d}", "family": "S8", "k": K_DEFAULT,
            "prompt": prompt, "checker": "S8", "params": {"expected": expected}}


# ---------------------------------------------------------------- S9
S9_ITEMS = [
    {
        "prompt": ("Write a function word_break(s: str, words: list) -> bool returning True if s "
                   "can be segmented into a sequence of the given words (words may be reused). "
                   "The empty string is considered segmentable. Return code only."),
        "asserts": [
            "assert word_break('leetcode', ['leet','code']) == True",
            "assert word_break('catsandog', ['cats','dog','sand','and','cat']) == False",
            "assert word_break('', ['a']) == True",
            "assert word_break('aaaaaaa', ['aaaa','aaa']) == True",
            "assert word_break('cars', ['car','ca','rs']) == True",
        ],
    },
    {
        "prompt": ("Write a function spiral_order(matrix: list) -> list returning the elements of "
                   "a 2D list in clockwise spiral order. Empty matrix gives []. Return code only."),
        "asserts": [
            "assert spiral_order([[1,2,3],[4,5,6],[7,8,9]]) == [1,2,3,6,9,8,7,4,5]",
            "assert spiral_order([[1],[2],[3]]) == [1,2,3]",
            "assert spiral_order([[1,2,3]]) == [1,2,3]",
            "assert spiral_order([]) == []",
            "assert spiral_order([[1,2],[3,4]]) == [1,2,4,3]",
        ],
    },
    {
        "prompt": ("Write a function balanced(s: str) -> bool returning True if all (), [], {} "
                   "brackets in s are correctly matched and nested (other characters are "
                   "ignored). Return code only."),
        "asserts": [
            "assert balanced('([{}])') == True",
            "assert balanced('(]') == False",
            "assert balanced('(()') == False",
            "assert balanced('') == True",
            "assert balanced('{[()]}[]') == True",
            "assert balanced('([)]') == False",
        ],
    },
    {
        "prompt": ("Write a function top_k(records: list, k: int) -> list returning the k records "
                   "with the highest 'score', sorted by score descending; ties break by 'id' "
                   "ascending. Records are dicts with keys 'id' (str) and 'score' (int). "
                   "Return code only."),
        "asserts": [
            "assert top_k([{'id':'a','score':5},{'id':'b','score':9}], 1) == [{'id':'b','score':9}]",
            "assert top_k([{'id':'b','score':5},{'id':'a','score':5}], 1) == [{'id':'a','score':5}]",
            "assert top_k([], 3) == []",
            "assert top_k([{'id':'x','score':1}], 0) == []",
            "assert top_k([{'id':'c','score':2},{'id':'a','score':2},{'id':'b','score':7}], 2) == [{'id':'b','score':7},{'id':'a','score':2}]",
        ],
    },
    {
        "prompt": ("This function is broken. It should return the maximum sum of any contiguous "
                   "subarray (and 0 for an empty list), but it fails on all-negative input:\n"
                   "```python\ndef max_subarray(xs):\n    best = 0\n    cur = 0\n"
                   "    for x in xs:\n        cur = max(0, cur + x)\n        best = max(best, cur)\n"
                   "    return best\n```\n"
                   "Failing test: assert max_subarray([-3,-1,-2]) == -1 (it returns 0). "
                   "Return the corrected function, code only."),
        "asserts": [
            "assert max_subarray([-3,-1,-2]) == -1",
            "assert max_subarray([]) == 0",
            "assert max_subarray([1,-2,3]) == 3",
            "assert max_subarray([5]) == 5",
            "assert max_subarray([1,2,3]) == 6",
            "assert max_subarray([-2,2,-1]) == 2",
        ],
    },
]


def gen_s9(i):
    spec = S9_ITEMS[i]
    return {"id": f"S9-{i:02d}", "family": "S9", "k": K_DEFAULT,
            "prompt": spec["prompt"], "checker": "S9", "params": {"asserts": spec["asserts"]}}


# --------------------------------------------------------------- S10
def gen_s10(i):
    r = rng("S10", i)
    facts = {
        "service": r.choice(["billing-api", "auth-gateway", "search-index", "notify-worker"]),
        "duration": r.randint(5, 240),
        "users": r.randint(200, 90000),
        "region": r.choice(["us-east", "eu-west", "ap-south"]),
        "cause": r.choice(["expired TLS certificate", "connection pool exhaustion",
                           "bad config rollout", "upstream DNS failure"]),
    }
    fillers = [
        "The on-call rotation was handled by the platform team this week.",
        "Status page updates were published at regular intervals.",
        "No other services reported degraded performance during the window.",
        "The incident channel remained open until verification completed.",
    ]
    report = (
        f"{fillers[0]} The {facts['service']} incident in {facts['region']} lasted "
        f"{facts['duration']} minutes. {fillers[1]} A total of {facts['users']} users were "
        f"affected. Root cause: {facts['cause']}. {fillers[2]}"
    )
    prompt = (
        "Summarize this incident report in exactly 3 sentences. Your summary must mention the "
        "service name, the duration in minutes, and the number of users affected. Do not use "
        "any number that does not appear in the report.\n\n"
        f"Report: {report}\n\nYour summary:"
    )
    return {"id": f"S10-{i:02d}", "family": "S10", "k": K_DEFAULT,
            "prompt": prompt, "checker": "S10", "params": {"facts": facts}}


# --------------------------------------------------------------- S11
TOOLS_DESC = (
    "Tools: book_table(venue: str, party_size: int, day: str), "
    "lookup_order(order_id: int), send_email(to: str, subject: str)."
)

S11_ITEMS = [
    {
        "user": "Book a table at Luigi's for 4 people on Tuesday.",
        "expected": {"tool": "book_table",
                     "args": {"venue": "Luigi's", "party_size": 4, "day": "Tuesday"}},
    },
    {
        "user": "Thanks, that's all for now.",
        "expected": {"tool": None, "args": {}},
    },
    {
        "user": "First look up order 5821. Then email sam@example.com with subject 'Order status'.",
        "expected": [
            {"tool": "lookup_order", "args": {"order_id": 5821}},
            {"tool": "send_email", "args": {"to": "sam@example.com", "subject": "Order status"}},
        ],
    },
    {
        "user": "Book a table for seven people at The Grange on Friday.",
        "expected": {"tool": "book_table",
                     "args": {"venue": "The Grange", "party_size": 7, "day": "Friday"}},
    },
    {
        "user": "What's the weather forecast for tomorrow?",
        "expected": {"tool": None, "args": {}},
    },
]


def gen_s11(i):
    spec = S11_ITEMS[i]
    prompt = (
        f"{TOOLS_DESC}\nUser request: {spec['user']}\n"
        'Output ONLY one JSON object {"tool": <name or null>, "args": {...}}, or a JSON array '
        "of such objects in call order when multiple calls are needed. If no tool applies, "
        'output {"tool": null, "args": {}}.'
    )
    return {"id": f"S11-{i:02d}", "family": "S11", "k": K_DEFAULT,
            "prompt": prompt, "checker": "S11", "params": {"expected": spec["expected"]}}


def main():
    items = []
    items += [gen_s8(i) for i in range(6)]
    items += [gen_s9(i) for i in range(5)]
    items += [gen_s10(i) for i in range(4)]
    items += [gen_s11(i) for i in range(5)]
    with open(OUT, "w") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")
    total = sum(it["k"] for it in items)
    print(f"wrote {len(items)} items -> {OUT}; calls per lane: {total}")
    for fam in sorted({it["family"] for it in items}):
        sub = [it for it in items if it["family"] == fam]
        print(f"  {fam}: {len(sub)} items, calls={sum(x['k'] for x in sub)}")


if __name__ == "__main__":
    main()
