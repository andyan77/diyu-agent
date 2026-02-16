---
description: Execute V4 Phase 1 build pipeline (Security & Tenant Foundation). Supports --status, --dry-run, --resume, --wf WF-XX.
allowed-tools: ["Bash", "Read", "Write", "Edit", "Grep", "Glob"]
---

# Phase 1 Build Orchestrator

Execute V4 Phase 1 ("Security & Tenant Foundation") build pipeline.

## Workflow Pipeline

The V4 plan defines 7 workflows executed in dependency order:

| ID | Name | Depends On | Task Cards |
|----|------|------------|------------|
| WF-P0 | Prerequisite Fixes | (none) | P0.1~P0.6 audit fix items |
| WF-A1 | Gate Entry | WF-P0 | (validation only) |
| WF-B1 | Infrastructure | WF-A1 | I1-1 ~ I1-7 |
| WF-B2 | Gateway | WF-A1 | G1-1 ~ G1-6 |
| WF-B3 | Frontend | WF-A1 | FW1-1 ~ FW1-4, FA1-1 ~ FA1-2 |
| WF-B4 | Crosscutting | WF-A1 | D1-1 ~ D1-3, OS1-1 ~ OS1-6 |
| WF-A2 | Gate Exit | WF-B1~B4 | (verification only) |

## Execution Steps

1. Read `delivery/v4-workflows.yaml` for workflow definitions
2. Read `delivery/milestone-matrix.yaml` for exit criteria and card status
3. Check `evidence/v4-phase1/checkpoint.json` for resume state
4. For each pending workflow in dependency order:
   a. Read task cards from `docs/task-cards/` for the workflow's card IDs
   b. For each unfinished task card:
      - Read card dependencies and acceptance commands
      - Write failing tests (RED)
      - Implement minimal code (GREEN)
      - Run acceptance commands from the card
      - Update milestone-matrix.yaml card status to `done`
   c. Run workflow checks from v4-workflows.yaml
   d. Save checkpoint
5. On WF-A2: run `uv run python scripts/verify_phase.py --phase 1 --json`

## CLI Usage

```bash
# Show current state
bash scripts/run_phase1_v4.sh --status

# Dry run (show plan)
bash scripts/run_phase1_v4.sh --dry-run

# Run specific workflow checks
bash scripts/run_phase1_v4.sh --wf WF-B1

# Resume from last checkpoint
bash scripts/run_phase1_v4.sh --resume

# Full run with JSON output
bash scripts/run_phase1_v4.sh --json
```

## Key Files

- `delivery/v4-workflows.yaml` - Workflow definitions (dependencies, checks, failure strategy)
- `delivery/milestone-matrix.yaml` - Phase exit criteria and card completion status
- `scripts/run_phase1_v4.sh` - Orchestrator script
- `evidence/v4-phase1/checkpoint.json` - Checkpoint state for resume

## Arguments

This command accepts optional arguments:

- `--wf WF-XX` - Target a specific workflow
- `--status` - Show current pipeline state
- `--dry-run` - Show execution plan without running
- `--resume` - Continue from last checkpoint

ARGUMENTS: $ARGUMENTS

## Execution Instructions

When invoked, perform these steps:

1. Run `bash scripts/run_phase1_v4.sh --status` to show current state
2. Identify the next pending workflow from checkpoint
3. Read the workflow's task cards from `delivery/v4-workflows.yaml`
4. For each task card in the workflow:
   - Read the task card file from `docs/task-cards/`
   - Check card dependencies (skip if deps not met)
   - Execute the card using TDD if available, otherwise manual implementation
   - Run the card's acceptance commands
   - Mark card as done in `delivery/milestone-matrix.yaml`
5. Run the workflow's verification checks
6. Save checkpoint via `bash scripts/run_phase1_v4.sh --wf <ID>`
7. Report results

Optional enhancement agents (use if available, skip if not):
- `/tdd` for test-driven implementation
- `code-reviewer` for post-implementation review
- `security-reviewer` for auth/gateway code
- `database-reviewer` for migration code
