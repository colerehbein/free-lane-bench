# Free-Lane Bench — strengths and weaknesses

Aggregated across every run (S2-04 excluded as a known void item).
Cell = items passing all k samples (pass^k), the consistency grade.

| family | A ling-3.1 | B step-5 | C longcat-2.5 | D mimo-2.6 | E omen-alpha | P mimo-pro | Q deepseek-f4.1 |
|---|---|---|---|---|---|---|---|
| F1 JSON discipline | 5/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| F2 reasoning | 5/8 | 8/8 | 8/8 | 7/8 | 8/8 | 8/8 | 8/8 |
| F3 coding | 2/6 | 5/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| F4 long-ctx retrieval | 3/4 | 3/4 | 4/4 | 3/4 | 4/4 | 4/4 | 4/4 |
| F5 honesty | 4/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 7/8 |
| F6 extraction | 2/4 | 2/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| S1 constraint soup | 2/6 | 4/6 | 5/6 | 3/6 | 3/6 | 5/6 | 2/6 |
| S2 char mechanics | 1/4 | 4/4 | 4/4 | 3/4 | 4/4 | 4/4 | 4/4 |
| S3 deep math | 0/6 | 6/6 | 5/6 | 6/6 | 6/6 | 5/6 | 6/6 |
| S4 hard coding | 0/6 | 6/6 | 6/6 | 5/6 | 6/6 | 6/6 | 6/6 |
| S5 multi-hop long-ctx | 2/4 | 4/4 | 4/4 | 3/4 | 4/4 | 4/4 | 2/4 |
| S6 verify/repair | 1/4 | 3/4 | 4/4 | 4/4 | 4/4 | 4/4 | 0/4 |
| S7 computed JSON | 1/3 | 3/3 | 3/3 | 3/3 | 2/3 | 3/3 | 0/3 |
| S8 deep reasoning | 2/6 | 4/6 | 5/6 | 4/6 | 1/6 | — | — |
| S9 harder coding | 4/5 | 5/5 | 5/5 | 5/5 | 5/5 | — | — |
| S10 summary fidelity | 4/4 | 4/4 | 4/4 | 3/4 | 4/4 | — | — |
| S11 tool-call discipline | 5/5 | 4/5 | 5/5 | 5/5 | 5/5 | — | — |

## What separates the field

- **F1 JSON discipline**: leads Q deepseek-f4.1, P mimo-pro, E omen-alpha, D mimo-2.6, C longcat-2.5, B step-5 (100%), trails A ling-3.1 (62%)
- **F2 reasoning**: leads Q deepseek-f4.1, P mimo-pro, E omen-alpha, C longcat-2.5, B step-5 (100%), trails A ling-3.1 (62%)
- **F3 coding**: leads Q deepseek-f4.1, P mimo-pro, E omen-alpha, D mimo-2.6, C longcat-2.5 (100%), trails A ling-3.1 (33%)
- **F4 long-ctx retrieval**: leads Q deepseek-f4.1, P mimo-pro, E omen-alpha, C longcat-2.5 (100%), trails A ling-3.1 (75%)
- **F5 honesty**: leads P mimo-pro, E omen-alpha, D mimo-2.6, C longcat-2.5, B step-5 (100%), trails A ling-3.1 (50%)
- **F6 extraction**: leads Q deepseek-f4.1, P mimo-pro, E omen-alpha, D mimo-2.6, C longcat-2.5 (100%), trails A ling-3.1 (50%)
- **S2 char mechanics**: leads Q deepseek-f4.1, P mimo-pro, E omen-alpha, C longcat-2.5, B step-5 (100%), trails A ling-3.1 (25%)
- **S3 deep math**: leads Q deepseek-f4.1, E omen-alpha, D mimo-2.6, B step-5 (100%), trails A ling-3.1 (0%)
- **S4 hard coding**: leads Q deepseek-f4.1, P mimo-pro, E omen-alpha, C longcat-2.5, B step-5 (100%), trails A ling-3.1 (0%)
- **S5 multi-hop long-ctx**: leads P mimo-pro, E omen-alpha, C longcat-2.5, B step-5 (100%), trails A ling-3.1 (50%)
- **S6 verify/repair**: leads P mimo-pro, E omen-alpha, D mimo-2.6, C longcat-2.5 (100%), trails Q deepseek-f4.1 (0%)
- **S7 computed JSON**: leads P mimo-pro, D mimo-2.6, C longcat-2.5, B step-5 (100%), trails Q deepseek-f4.1 (0%)
- **S9 harder coding**: leads E omen-alpha, D mimo-2.6, C longcat-2.5, B step-5 (100%), trails A ling-3.1 (80%)
- **S10 summary fidelity**: leads E omen-alpha, C longcat-2.5, B step-5, A ling-3.1 (100%), trails D mimo-2.6 (75%)
- **S11 tool-call discipline**: leads E omen-alpha, D mimo-2.6, C longcat-2.5, A ling-3.1 (100%), trails B step-5 (80%)

## Discriminating items (split the real field)

- F3-03: passed by A ling-3.1, C longcat-2.5, D mimo-2.6, E omen-alpha, P mimo-pro, Q deepseek-f4.1; **missed by** B step-5
- F5-01: passed by A ling-3.1, B step-5, C longcat-2.5, D mimo-2.6, E omen-alpha, P mimo-pro; **missed by** Q deepseek-f4.1
- S1-00: passed by C longcat-2.5, P mimo-pro; **missed by** A ling-3.1, B step-5, D mimo-2.6, E omen-alpha (no answer: Q deepseek-f4.1)
- S1-05: passed by A ling-3.1, B step-5, C longcat-2.5, P mimo-pro, Q deepseek-f4.1; **missed by** D mimo-2.6, E omen-alpha
- S11-02: passed by A ling-3.1, C longcat-2.5, D mimo-2.6, E omen-alpha; **missed by** B step-5
- S3-03: passed by B step-5, D mimo-2.6, E omen-alpha, P mimo-pro, Q deepseek-f4.1; **missed by** C longcat-2.5 (no answer: A ling-3.1)
- S6-01: passed by C longcat-2.5, D mimo-2.6, E omen-alpha, P mimo-pro; **missed by** B step-5 (no answer: A ling-3.1, Q deepseek-f4.1)
- S8-01: passed by A ling-3.1, B step-5, C longcat-2.5, D mimo-2.6; **missed by** E omen-alpha
- S8-04: passed by B step-5, C longcat-2.5; **missed by** A ling-3.1, D mimo-2.6, E omen-alpha
- S8-05: passed by B step-5, C longcat-2.5, D mimo-2.6; **missed by** A ling-3.1, E omen-alpha

## Per-model profiles


### A ling-3.1 (A-ling31-commandcode)
- clean sweeps: S10 summary fidelity, S11 tool-call discipline
- below 85%: S9 harder coding, F4 long-ctx retrieval, F1 JSON discipline, F2 reasoning, F5 honesty, F6 extraction, S5 multi-hop long-ctx, F3 coding, S1 constraint soup, S7 computed JSON, S8 deep reasoning, S2 char mechanics, S6 verify/repair, S3 deep math, S4 hard coding
- capability on delivered calls: 183/189 | first-attempt success: 158/265 | latency p50/p95: 4.1s / 16.1s

### B step-5 (B-step5-nous)
- clean sweeps: F1 JSON discipline, F2 reasoning, F5 honesty, S2 char mechanics, S3 deep math, S4 hard coding, S5 multi-hop long-ctx, S7 computed JSON, S9 harder coding, S10 summary fidelity
- below 85%: F3 coding, S11 tool-call discipline, F4 long-ctx retrieval, S6 verify/repair, S1 constraint soup, S8 deep reasoning, F6 extraction
- capability on delivered calls: 248/259 | first-attempt success: 255/265 | latency p50/p95: 4.7s / 34.1s

### C longcat-2.5 (C-longcat25-nous)
- clean sweeps: F1 JSON discipline, F2 reasoning, F3 coding, F4 long-ctx retrieval, F5 honesty, F6 extraction, S2 char mechanics, S4 hard coding, S5 multi-hop long-ctx, S6 verify/repair, S7 computed JSON, S9 harder coding, S10 summary fidelity, S11 tool-call discipline
- below 85%: S1 constraint soup, S3 deep math, S8 deep reasoning
- capability on delivered calls: 262/265 | first-attempt success: 261/265 | latency p50/p95: 9.4s / 52.6s

### D mimo-2.6 (D-mimo26-relay)
- clean sweeps: F1 JSON discipline, F3 coding, F5 honesty, F6 extraction, S3 deep math, S6 verify/repair, S7 computed JSON, S9 harder coding, S11 tool-call discipline
- below 85%: S4 hard coding, F4 long-ctx retrieval, S2 char mechanics, S5 multi-hop long-ctx, S10 summary fidelity, S8 deep reasoning, S1 constraint soup
- capability on delivered calls: 251/265 | first-attempt success: 261/265 | latency p50/p95: 10.2s / 32.9s

### E omen-alpha (E-omenalpha-opencodego)
- clean sweeps: F1 JSON discipline, F2 reasoning, F3 coding, F4 long-ctx retrieval, F5 honesty, F6 extraction, S2 char mechanics, S3 deep math, S4 hard coding, S5 multi-hop long-ctx, S6 verify/repair, S9 harder coding, S10 summary fidelity, S11 tool-call discipline
- below 85%: S7 computed JSON, S1 constraint soup, S8 deep reasoning
- capability on delivered calls: 251/265 | first-attempt success: 264/265 | latency p50/p95: 2.3s / 20.9s

### P mimo-pro (P-mimopro-paid)
- clean sweeps: F1 JSON discipline, F2 reasoning, F3 coding, F4 long-ctx retrieval, F5 honesty, F6 extraction, S2 char mechanics, S4 hard coding, S5 multi-hop long-ctx, S6 verify/repair, S7 computed JSON
- below 85%: S1 constraint soup, S3 deep math
- capability on delivered calls: 203/205 | first-attempt success: 204/205 | latency p50/p95: 5.9s / 29.3s

### Q deepseek-f4.1 (Q-deepseekflash-paid)
- clean sweeps: F1 JSON discipline, F2 reasoning, F3 coding, F4 long-ctx retrieval, F6 extraction, S2 char mechanics, S3 deep math, S4 hard coding
- below 85%: S5 multi-hop long-ctx, S1 constraint soup, S6 verify/repair, S7 computed JSON
- capability on delivered calls: 171/173 | first-attempt success: 173/205 | latency p50/p95: 2.9s / 20.7s
