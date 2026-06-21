# JEPA-LNN Phase 0 results

Date: 2026-06-10

This document records the executed diagnostics proposed in `jepa_lnn_coupling_strategy.md`.

## D1 - Fixed latent

Same deterministic protocol as the existing comparison: 30,000 steps, seeds 1001-1005.

| latent mode | collisions | rate | reward total |
|---|---:|---:|---:|
| dynamic | 2,319 | 7.73% | -7,644.283 |
| zero fixed | 2,326 | 7.75% | -8,552.400 |
| training mean fixed | 16,838 | 56.13% | -52,839.251 |

Freezing the latent does not restore performance near the raw-observation DAgger controller. The mean latent creates an almost constant forward/servo-biased command, while zero latent creates a low-speed, near-saturated positive-turn regime.

## D3 - Latent distribution shift

| distribution | mean Mahalanobis | p95 | p99 |
|---|---:|---:|---:|
| held-out expert replay | 4.694 | 7.693 | 9.873 |
| coupled rollout | 4.535 | 7.272 | 8.585 |

Collision steps have lower, not higher, mean distance than non-collision steps (`3.728` vs `4.603`). Global or collision-local latent OOD drift is not supported by this diagnostic.

## D4 - Policy sensitivity

| input block | total gradient norm | RMS per dimension |
|---|---:|---:|
| raw observation, 3 dims | 0.3182 | 0.1837 |
| JEPA latent, 128 dims | 1.5181 | 0.1342 |

The latent block has `4.77x` the aggregate gradient norm, despite lower sensitivity per individual dimension. The dominant issue is dimensional and structural imbalance, combined with the policy's lack of an observation-only fallback.

## Revised conclusion

The original hypothesis needs refinement. The direct coupling does not primarily fail because the JEPA encoder produces globally out-of-distribution latents during rollout. It fails because the policy has learned a highly consequential 128-dimensional conditional control path whose operating point changes the action regime. Offline action history remains a plausible causal shortcut, but Mahalanobis drift is not the mechanism observed here.

Decision: skip further DAgger or epoch increases for direct injection. Prefer S2: keep the deployed LNN input identical to `dagger_002` and use JEPA only as an auxiliary training target on the LNN hidden state. S1 projection/gating remains a bounded diagnostic experiment, not the primary path.
