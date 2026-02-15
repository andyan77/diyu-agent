## Summary

<!-- Brief description of what this PR does and why -->

## Changes

- [ ] ...

## Impact Analysis

<!-- Run locally: bash scripts/change_impact_router.sh --json -->
<!-- Run locally: bash scripts/risk_scorer.sh --json -->

- **Risk Score**: <!-- REQUIRED: paste output of `bash scripts/risk_scorer.sh --score-only` -->
- **Risk Level**: <!-- Low (0-3) / Medium (4-6) / High (7-9) / Critical (10-12) -->
- **Triggered Gates**: <!-- paste `bash scripts/change_impact_router.sh --json | jq .triggered_gates` -->
- **Layers Touched**: <!-- e.g., brain, gateway, ports -->

<details>
<summary>Evidence commands (expand for copy-paste)</summary>

```bash
# Run these locally and paste the outputs above
bash scripts/risk_scorer.sh --json
bash scripts/change_impact_router.sh --json
```
</details>

## Testing

- [ ] Unit tests pass (`make test`)
- [ ] Lint passes (`make lint`)
- [ ] Guard checks pass (`make check-layer-deps`)
- [ ] Acceptance gate passes (`make check-acceptance`)

## Task Card Alignment

<!-- If this PR relates to milestone matrix items, list them -->
- Matrix Item: <!-- e.g., FW0-1, G1-2, I1-3 -->
- Task Card: <!-- e.g., TASK-FW0-1 -->

## Rollback Plan

<!-- How to safely revert this change if needed -->
