# sample-run: Grok 4.5 on the OpenCode harness

Ten independent attempts per task, run in isolated 2-CPU/4-GB AMD64
Daytona sandboxes. The model route was `openrouter/x-ai/grok-4.5`; every
attempt was graded against the hidden fail-to-pass and pass-to-pass tests.

## pass@k

| Task | Solved (c/n) | pass@1 | pass@3 | pass@10 | Avg f2p fixed |
|---|---:|---:|---:|---:|---:|
| latent-credit-normalize | 8/10 | 0.800 | 1.000 | 1.000 | 4.80/5 |
| latent-doc-extractors | 0/10 | 0.000 | 0.000 | 0.000 | 4.00/4 |
| latent-financial-tools | 0/10 | 0.000 | 0.000 | 0.000 | 8.00/9 |
| latent-phone-invites | 9/10 | 0.900 | 1.000 | 1.000 | 4.90/5 |
| xrepo-fiu-latent | 2/10 | 0.200 | 0.533 | 1.000 | 3.70/5 |
| xrepo-txenrich-latent | 2/10 | 0.200 | 0.533 | 1.000 | 4.40/5 |
| xrepo-txenrich3-latent | 0/10 | 0.000 | 0.000 | 0.000 | 3.20/5 |
| xrepo-txenrich4-latent | 0/10 | 0.000 | 0.000 | 0.000 | 2.60/5 |
| **Mean** | **21/80** | **0.263** | **0.383** | **0.500** | |

Unbiased pass@k is `1 - C(n-c, k) / C(n, k)`. Means are macro
averages over the eight tasks.

## Run totals

- Valid graded attempts: 80
- Full solves: 21
- Model cost: $31.44
- Agent runtime: 357.2 minutes (summed)
- Model steps: 1047

All per-attempt results, verifier verdicts, and trajectories are under
`grok-trials/`. Representative traces (a solve where available, otherwise
the closest graded attempt) are also copied into `trajectories-matrix/`.
