---
description: Execute V4 Phase 2 build pipeline (Core Conversation + Knowledge). Supports --status, --dry-run, --resume, --wf WF2-XX.
allowed-tools: ["Bash", "Read", "Write", "Edit", "Grep", "Glob", "Task"]
---

# Phase 2 Build Orchestrator

Execute V4 Phase 2 ("Core Conversation + Knowledge") build pipeline.

## Workflow Pipeline

The V4 plan defines 9 workflows executed in dependency order:

| ID | Name | Depends On | Task Cards | Agents |
|----|------|------------|------------|--------|
| WF2-P0 | Prerequisites | (none) | - | - |
| WF2-A1 | Gate Entry | WF2-P0 | - | - |
| WF2-B1 | Infrastructure + MemoryCore | WF2-A1 | I2-1~5, MC2-1~7 | diyu-tdd-guide |
| WF2-B2 | Brain + Tool Layer | WF2-B1 | T2-1~3, B2-1~8 | diyu-tdd-guide, diyu-architect |
| WF2-B3 | Gateway Layer | WF2-B2 | G2-1~7 | diyu-tdd-guide, diyu-security-reviewer |
| WF2-B4 | Frontend Web | WF2-B3 | FW2-1~9 | diyu-tdd-guide |
| WF2-B5 | Frontend Admin | WF2-B3 | FA2-1~3 | diyu-tdd-guide |
| WF2-B6 | Crosscutting | WF2-B4, WF2-B5 | D2-1~5, OS2-1~5 | diyu-tdd-guide |
| WF2-A2 | Gate Exit | WF2-B6 | - | - |

## MANDATORY Agent Dispatch

Agent dispatch is NOT optional. For each build workflow (WF2-B*), the following
agents MUST be invoked. Read `delivery/v4-phase2-workflows.yaml` for the
authoritative `agent_dispatch` field per workflow.

| Workflow | Agent | Scope | Reason |
|----------|-------|-------|--------|
| WF2-B1 | diyu-tdd-guide | all cards | TDD for infra + memory |
| WF2-B2 | diyu-tdd-guide | all cards | TDD for brain + tool |
| WF2-B2 | diyu-architect | B2-1, B2-3, B2-4, T2-1 | Conversation engine, context assembler, LLMCallPort |
| WF2-B3 | diyu-tdd-guide | all cards | TDD for gateway |
| WF2-B3 | diyu-security-reviewer | G2-1, G2-2, G2-4, G2-5, G2-6 | REST/WS auth, token bypass, rate limiting, file upload |
| WF2-B4 | diyu-tdd-guide | all cards | TDD for frontend web |
| WF2-B5 | diyu-tdd-guide | all cards | TDD for frontend admin |
| WF2-B6 | diyu-tdd-guide | all cards | TDD for crosscutting |

After each agent invocation, log to `evidence/v4-phase2/agent-dispatch.jsonl`:
```json
{"workflow":"WF2-B2","agent":"diyu-architect","scope":"B2-1","timestamp":"...","outcome":"completed"}
```

## Execution Steps

1. Run `bash scripts/run_phase2_v4.sh --status` to show current state
2. Read `delivery/v4-phase2-workflows.yaml` for workflow definitions
3. Read `delivery/milestone-matrix.yaml` for exit criteria and card status
4. Check `evidence/v4-phase2/checkpoint.json` for resume state
5. For each pending workflow in dependency order:
   a. Read task cards from `docs/task-cards/` for the workflow's card IDs
   b. Read `agent_dispatch` from the workflow YAML
   c. For each task card:
      - Invoke the MANDATORY agents listed for this workflow
      - Use `Task` tool with `subagent_type` matching the agent name
      - Read card dependencies and acceptance commands
      - Write failing tests (RED) -- via diyu-tdd-guide
      - Implement minimal code (GREEN)
      - Run acceptance commands from the card
      - Update milestone-matrix.yaml card status to `done`
      - Log agent dispatch to evidence/v4-phase2/agent-dispatch.jsonl
   d. Run workflow checks via `bash scripts/run_phase2_v4.sh --wf <ID>`
   e. Save checkpoint
6. On WF2-A2: run `uv run python scripts/verify_phase.py --phase 2 --json`

## CLI Usage

```bash
# Show current state
bash scripts/run_phase2_v4.sh --status

# Dry run (show plan)
bash scripts/run_phase2_v4.sh --dry-run

# Run specific workflow checks
bash scripts/run_phase2_v4.sh --wf WF2-B1

# Resume from last checkpoint
bash scripts/run_phase2_v4.sh --resume

# Full run with JSON output
bash scripts/run_phase2_v4.sh --json
```

## Key Files

- `delivery/v4-phase2-workflows.yaml` - Workflow definitions (dependencies, checks, agents)
- `delivery/phase2-runtime-config.yaml` - Runtime configuration (LLM, billing, storage)
- `delivery/milestone-matrix.yaml` - Phase exit criteria and card status
- `scripts/run_phase2_v4.sh` - Orchestrator script
- `evidence/v4-phase2/checkpoint.json` - Checkpoint state for resume
- `evidence/v4-phase2/agent-dispatch.jsonl` - Agent dispatch evidence log

## Guard Script Binding

These guard scripts are hard gates in workflow checks:

| Guard Script | Bound To |
|-------------|----------|
| `scripts/check_layer_deps.sh` | WF2-B1, WF2-B2, WF2-B3, WF2-B6 |
| `scripts/check_port_compat.sh` | WF2-B2 |
| `scripts/check_migration.sh` | WF2-B1 |
| `scripts/check_rls.sh` | WF2-B1 |

## Arguments

This command accepts optional arguments:

- `--wf WF2-XX` - Target a specific workflow
- `--status` - Show current pipeline state
- `--dry-run` - Show execution plan without running
- `--resume` - Continue from last checkpoint

ARGUMENTS: $ARGUMENTS
