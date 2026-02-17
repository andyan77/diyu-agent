#!/usr/bin/env bash
# run_phase2_v4.sh - V4 Phase 2 Build Orchestrator
#
# Executes the 9-workflow pipeline defined in delivery/v4-phase2-workflows.yaml.
# Supports checkpoint/resume so interrupted sessions can continue.
#
# Differences from Phase 1 orchestrator:
#   - Reads timeout_s per workflow from YAML (not hardcoded 120s)
#   - Writes per-WF evidence (commit_sha, exit_code, duration, logs)
#   - Reads agent_dispatch from YAML for /phase2-build dispatch table
#   - Reads check cmd/desc fields (Phase 1 used name/command)
#
# Usage:
#   bash scripts/run_phase2_v4.sh                     # Run all pending workflows
#   bash scripts/run_phase2_v4.sh --wf WF2-B1         # Run specific workflow
#   bash scripts/run_phase2_v4.sh --resume             # Resume from last checkpoint
#   bash scripts/run_phase2_v4.sh --dry-run            # Show execution plan
#   bash scripts/run_phase2_v4.sh --json               # JSON output
#   bash scripts/run_phase2_v4.sh --status             # Show current state
#   bash scripts/run_phase2_v4.sh --reset              # Clear checkpoint, start fresh
#
# Architecture:
#   This orchestrator manages the BUILD pipeline (WF2-P0 -> WF2-A1 -> WF2-B{1..6} -> WF2-A2).
#   The existing W1-W4 governance pipeline (run_all.sh) is invoked AS PART of WF2-A1/WF2-A2.
#
# Agent dispatch is MANDATORY. The /phase2-build command reads agent_dispatch
# from the workflow YAML and logs evidence to evidence/v4-phase2/agent-dispatch.jsonl.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKFLOWS_FILE="$ROOT_DIR/delivery/v4-phase2-workflows.yaml"
EVIDENCE_DIR="$ROOT_DIR/evidence/v4-phase2"
CHECKPOINT_FILE="$EVIDENCE_DIR/checkpoint.json"
SESSION_ID="${SESSION_ID:-$(date +%Y%m%dT%H%M%S)}"

# Defaults
TARGET_WF=""
RESUME=false
DRY_RUN=false
JSON_OUTPUT=false
SHOW_STATUS=false
RESET=false

# Parameter parsing
while [ $# -gt 0 ]; do
  case "$1" in
    --wf)       shift; TARGET_WF="${1:-}" ;;
    --wf=*)     TARGET_WF="${1#--wf=}" ;;
    --resume)   RESUME=true ;;
    --dry-run)  DRY_RUN=true ;;
    --json)     JSON_OUTPUT=true ;;
    --status)   SHOW_STATUS=true ;;
    --reset)    RESET=true ;;
  esac
  shift
done

mkdir -p "$EVIDENCE_DIR"

# --- Checkpoint functions ---

save_checkpoint() {
  local wf_id="$1"
  local status="$2"
  local timestamp
  timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  python3 -c "
import json, sys, os

cp_file = sys.argv[1]
wf_id = sys.argv[2]
status = sys.argv[3]
ts = sys.argv[4]
session = sys.argv[5]

if os.path.exists(cp_file):
    with open(cp_file) as f:
        cp = json.load(f)
else:
    cp = {'session_id': session, 'phase': 'phase_2', 'workflows': {}, 'created': ts}

cp['workflows'][wf_id] = {'status': status, 'timestamp': ts}
cp['updated'] = ts

with open(cp_file, 'w') as f:
    json.dump(cp, f, indent=2, ensure_ascii=False)
" "$CHECKPOINT_FILE" "$wf_id" "$status" "$timestamp" "$SESSION_ID"
}

load_checkpoint() {
  if [ -f "$CHECKPOINT_FILE" ]; then
    python3 -c "
import json
with open('$CHECKPOINT_FILE') as f:
    cp = json.load(f)
print(json.dumps(cp))
"
  else
    echo "{}"
  fi
}

get_wf_status() {
  local wf_id="$1"
  python3 -c "
import json, sys
cp_file = sys.argv[1]
wf_id = sys.argv[2]
try:
    with open(cp_file) as f:
        cp = json.load(f)
    status = cp.get('workflows', {}).get(wf_id, {}).get('status', 'pending')
    print(status)
except (FileNotFoundError, json.JSONDecodeError):
    print('pending')
" "$CHECKPOINT_FILE" "$wf_id"
}

# --- Workflow YAML loading ---
# Phase 2 uses cmd/desc fields (not name/command like Phase 1)

load_workflow_ids() {
  python3 -c "
import yaml
with open('$WORKFLOWS_FILE') as f:
    data = yaml.safe_load(f)
for wf in data['workflows']:
    print(wf['id'])
"
}

load_workflow_deps() {
  local wf_id="$1"
  python3 -c "
import yaml, sys
with open('$WORKFLOWS_FILE') as f:
    data = yaml.safe_load(f)
for wf in data['workflows']:
    if wf['id'] == sys.argv[1]:
        for dep in wf.get('depends_on', []):
            print(dep)
        break
" "$wf_id"
}

load_workflow_checks() {
  local wf_id="$1"
  python3 -c "
import yaml, json, sys
with open('$WORKFLOWS_FILE') as f:
    data = yaml.safe_load(f)
for wf in data['workflows']:
    if wf['id'] == sys.argv[1]:
        print(json.dumps(wf.get('checks', [])))
        break
" "$wf_id"
}

load_workflow_name() {
  local wf_id="$1"
  python3 -c "
import yaml, sys
with open('$WORKFLOWS_FILE') as f:
    data = yaml.safe_load(f)
for wf in data['workflows']:
    if wf['id'] == sys.argv[1]:
        print(wf['name'])
        break
" "$wf_id"
}

load_workflow_cards() {
  local wf_id="$1"
  python3 -c "
import yaml, json, sys
with open('$WORKFLOWS_FILE') as f:
    data = yaml.safe_load(f)
for wf in data['workflows']:
    if wf['id'] == sys.argv[1]:
        print(json.dumps(wf.get('task_cards', [])))
        break
" "$wf_id"
}

load_workflow_timeout() {
  local wf_id="$1"
  python3 -c "
import yaml, sys
with open('$WORKFLOWS_FILE') as f:
    data = yaml.safe_load(f)
for wf in data['workflows']:
    if wf['id'] == sys.argv[1]:
        print(wf.get('timeout_s', 300))
        break
" "$wf_id"
}

load_workflow_agents() {
  local wf_id="$1"
  python3 -c "
import yaml, json, sys
with open('$WORKFLOWS_FILE') as f:
    data = yaml.safe_load(f)
for wf in data['workflows']:
    if wf['id'] == sys.argv[1]:
        print(json.dumps(wf.get('agent_dispatch', [])))
        break
" "$wf_id"
}

# --- Reset ---

if [ "$RESET" = true ]; then
  rm -f "$CHECKPOINT_FILE"
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"action":"reset","phase":"phase_2","status":"done"}'
  else
    echo "Phase 2 checkpoint cleared. Next run starts fresh."
  fi
  exit 0
fi

# --- Status ---

if [ "$SHOW_STATUS" = true ]; then
  CP=$(load_checkpoint)
  if [ "$JSON_OUTPUT" = true ]; then
    echo "$CP"
  else
    echo "=== V4 Phase 2 Build Status ==="
    echo ""
    WF_IDS=$(load_workflow_ids)
    while IFS= read -r wf_id; do
      wf_status=$(get_wf_status "$wf_id")
      wf_name=$(load_workflow_name "$wf_id")
      agents=$(load_workflow_agents "$wf_id")
      case "$wf_status" in
        done)    marker="[x]" ;;
        failed)  marker="[!]" ;;
        running) marker="[~]" ;;
        *)       marker="[ ]" ;;
      esac
      echo "  $marker $wf_id: $wf_name ($wf_status)"
      # Show agent dispatch requirements
      agent_count=$(python3 -c "import json; print(len(json.loads('$agents')))")
      if [ "$agent_count" -gt 0 ]; then
        echo "      agents: $agents"
      fi
    done <<< "$WF_IDS"
    echo ""
    if [ -f "$CHECKPOINT_FILE" ]; then
      echo "Checkpoint: $CHECKPOINT_FILE"
    else
      echo "No checkpoint (fresh start)"
    fi
  fi
  exit 0
fi

# --- Dependency check ---

check_deps_met() {
  local wf_id="$1"
  local deps
  deps=$(load_workflow_deps "$wf_id")
  if [ -z "$deps" ]; then
    return 0
  fi
  while IFS= read -r dep; do
    local dep_status
    dep_status=$(get_wf_status "$dep")
    if [ "$dep_status" != "done" ]; then
      return 1
    fi
  done <<< "$deps"
  return 0
}

# --- Run checks for a workflow ---
# Phase 2 difference: uses cmd/desc fields, per-WF timeout, writes evidence with
# commit_sha, exit_code, duration, logs.

run_wf_checks() {
  local wf_id="$1"
  local checks_json
  checks_json=$(load_workflow_checks "$wf_id")
  local wf_timeout
  wf_timeout=$(load_workflow_timeout "$wf_id")

  # Per-check timeout = wf_timeout / num_checks, clamped to [30, 180]
  local per_check_timeout
  per_check_timeout=$(python3 -c "
import json, sys
checks = json.loads(sys.argv[1])
wf_timeout = int(sys.argv[2])
n = max(len(checks), 1)
t = max(30, min(180, wf_timeout // n))
print(t)
" "$checks_json" "$wf_timeout")

  python3 -c "
import json, subprocess, sys, os, time

wf_id = sys.argv[1]
checks = json.loads(sys.argv[2])
evidence_dir = sys.argv[3]
json_output = sys.argv[4] == 'true'
root_dir = sys.argv[5]
per_check_timeout = int(sys.argv[6])

os.makedirs(f'{evidence_dir}/{wf_id}', exist_ok=True)

# Get current commit SHA
try:
    sha = subprocess.run(
        ['git', 'rev-parse', 'HEAD'], capture_output=True, text=True,
        cwd=root_dir, timeout=5
    ).stdout.strip()
except Exception:
    sha = 'unknown'

results = []
total = len(checks)
passed_count = 0
failed_count = 0

for check in checks:
    desc = check.get('desc', 'unnamed')
    cmd = check.get('cmd', '')
    if not cmd:
        results.append({'desc': desc, 'status': 'skip', 'reason': 'no command'})
        continue

    start = time.time()
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=per_check_timeout, cwd=root_dir
        )
        duration = round(time.time() - start, 2)
        if r.returncode == 0:
            results.append({
                'desc': desc, 'status': 'pass',
                'duration_s': duration, 'exit_code': 0
            })
            passed_count += 1
        else:
            results.append({
                'desc': desc, 'status': 'fail',
                'exit_code': r.returncode,
                'duration_s': duration,
                'stderr': r.stderr[:1000] if r.stderr else '',
                'stdout_tail': r.stdout[-500:] if r.stdout else ''
            })
            failed_count += 1
    except subprocess.TimeoutExpired:
        duration = round(time.time() - start, 2)
        results.append({
            'desc': desc, 'status': 'fail',
            'reason': f'timeout ({per_check_timeout}s)',
            'duration_s': duration
        })
        failed_count += 1
    except Exception as e:
        duration = round(time.time() - start, 2)
        results.append({
            'desc': desc, 'status': 'fail',
            'reason': str(e), 'duration_s': duration
        })
        failed_count += 1

# Write per-WF evidence
evidence = {
    'workflow': wf_id,
    'commit_sha': sha,
    'checks': results,
    'total': total,
    'passed': passed_count,
    'failed': failed_count,
    'per_check_timeout_s': per_check_timeout,
}
with open(f'{evidence_dir}/{wf_id}/checks.json', 'w') as f:
    json.dump(evidence, f, indent=2)

if not json_output:
    for r in results:
        icon = 'PASS' if r['status'] == 'pass' else 'FAIL' if r['status'] == 'fail' else 'SKIP'
        dur = r.get('duration_s', '-')
        print(f'    [{icon}] {r[\"desc\"]} ({dur}s)')

sys.exit(1 if failed_count > 0 else 0)
" "$wf_id" "$checks_json" "$EVIDENCE_DIR" "$JSON_OUTPUT" "$ROOT_DIR" "$per_check_timeout"
}

# --- Dry run ---

if [ "$DRY_RUN" = true ]; then
  if [ "$JSON_OUTPUT" = true ]; then
    python3 -c "
import yaml, json
with open('$WORKFLOWS_FILE') as f:
    data = yaml.safe_load(f)
plan = []
for wf in data['workflows']:
    plan.append({
        'id': wf['id'], 'name': wf['name'],
        'depends_on': wf.get('depends_on', []),
        'task_cards': wf.get('task_cards', []),
        'agent_dispatch': wf.get('agent_dispatch', []),
        'checks_count': len(wf.get('checks', [])),
        'timeout_s': wf.get('timeout_s', 300)
    })
print(json.dumps({'mode': 'dry-run', 'phase': 'phase_2', 'plan': plan}, indent=2))
"
  else
    echo "=== V4 Phase 2 Build Plan (dry-run) ==="
    echo ""
    WF_IDS=$(load_workflow_ids)
    while IFS= read -r wf_id; do
      wf_name=$(load_workflow_name "$wf_id")
      wf_status=$(get_wf_status "$wf_id")
      wf_cards=$(load_workflow_cards "$wf_id")
      wf_timeout=$(load_workflow_timeout "$wf_id")
      agents=$(load_workflow_agents "$wf_id")
      deps=$(load_workflow_deps "$wf_id")
      echo "  $wf_id: $wf_name (timeout: ${wf_timeout}s)"
      echo "    Status: $wf_status"
      if [ -n "$deps" ]; then
        echo "    Depends: $(echo "$deps" | tr '\n' ', ' | sed 's/,$//')"
      fi
      echo "    Cards: $wf_cards"
      agent_count=$(python3 -c "import json; print(len(json.loads('$agents')))")
      if [ "$agent_count" -gt 0 ]; then
        echo "    Agents: $agents"
      fi
      echo ""
    done <<< "$WF_IDS"
    echo "Use --resume to continue from last checkpoint."
    echo "Use --wf WF2-XX to run a specific workflow."
  fi
  exit 0
fi

# --- Main execution ---

execute_workflow() {
  local wf_id="$1"
  local wf_name
  wf_name=$(load_workflow_name "$wf_id")

  local current_status
  current_status=$(get_wf_status "$wf_id")

  if [ "$current_status" = "done" ]; then
    if [ "$JSON_OUTPUT" = false ]; then
      echo "  [$wf_id] $wf_name -- already done, skipping"
    fi
    return 0
  fi

  if ! check_deps_met "$wf_id"; then
    local deps
    deps=$(load_workflow_deps "$wf_id")
    if [ "$JSON_OUTPUT" = false ]; then
      echo "  [$wf_id] $wf_name -- blocked (unmet deps: $(echo "$deps" | tr '\n' ', '))"
    fi
    return 1
  fi

  if [ "$JSON_OUTPUT" = false ]; then
    echo "--- [$wf_id] $wf_name ---"
  fi

  save_checkpoint "$wf_id" "running"

  local wf_cards
  wf_cards=$(load_workflow_cards "$wf_id")
  local card_count
  card_count=$(python3 -c "import json; print(len(json.loads('$wf_cards')))")

  if [ "$card_count" -gt 0 ] && [ "$JSON_OUTPUT" = false ]; then
    echo "  Task cards: $wf_cards"
  fi

  # Show agent dispatch requirements
  local agents
  agents=$(load_workflow_agents "$wf_id")
  local agent_count
  agent_count=$(python3 -c "import json; print(len(json.loads('$agents')))")
  if [ "$agent_count" -gt 0 ] && [ "$JSON_OUTPUT" = false ]; then
    echo "  Agent dispatch: $agents"
  fi

  if [ "$JSON_OUTPUT" = false ]; then
    echo "  Running verification checks..."
  fi

  # Run checks
  if run_wf_checks "$wf_id"; then
    save_checkpoint "$wf_id" "done"
    if [ "$JSON_OUTPUT" = false ]; then
      echo "  -> PASS"
    fi
    return 0
  else
    save_checkpoint "$wf_id" "failed"
    if [ "$JSON_OUTPUT" = false ]; then
      echo "  -> FAIL"
    fi
    return 1
  fi
}

# --- Target single workflow ---

if [ -n "$TARGET_WF" ]; then
  execute_workflow "$TARGET_WF"
  EXIT_CODE=$?
  if [ "$JSON_OUTPUT" = true ]; then
    python3 -c "
import json
print(json.dumps({
    'workflow': '$TARGET_WF',
    'phase': 'phase_2',
    'status': 'done' if $EXIT_CODE == 0 else 'failed',
    'session': '$SESSION_ID'
}))
"
  fi
  exit $EXIT_CODE
fi

# --- Run all (with resume support) ---

if [ "$JSON_OUTPUT" = false ]; then
  echo "=== V4 Phase 2 Build Orchestrator ==="
  echo "Session: $SESSION_ID"
  if [ "$RESUME" = true ] && [ -f "$CHECKPOINT_FILE" ]; then
    echo "Mode: resume from checkpoint"
  else
    echo "Mode: full run"
  fi
  echo ""
fi

WF_IDS=$(load_workflow_ids)
TOTAL_WF=0
PASSED_WF=0
FAILED_WF=0
SKIPPED_WF=0

while IFS= read -r wf_id; do
  TOTAL_WF=$((TOTAL_WF + 1))

  if [ "$RESUME" = true ]; then
    wf_status=$(get_wf_status "$wf_id")
    if [ "$wf_status" = "done" ]; then
      SKIPPED_WF=$((SKIPPED_WF + 1))
      if [ "$JSON_OUTPUT" = false ]; then
        echo "  [$wf_id] -- done (checkpoint), skipping"
      fi
      PASSED_WF=$((PASSED_WF + 1))
      continue
    fi
  fi

  if execute_workflow "$wf_id"; then
    PASSED_WF=$((PASSED_WF + 1))
  else
    FAILED_WF=$((FAILED_WF + 1))
    if [ "$JSON_OUTPUT" = false ]; then
      echo ""
      echo "Pipeline stopped at $wf_id. Use --resume to continue after fixing."
    fi
    break
  fi
  echo ""
done <<< "$WF_IDS"

# Summary
if [ "$JSON_OUTPUT" = true ]; then
  python3 -c "
import json
print(json.dumps({
    'session': '$SESSION_ID',
    'phase': 'phase_2',
    'total': $TOTAL_WF,
    'passed': $PASSED_WF,
    'failed': $FAILED_WF,
    'skipped': $SKIPPED_WF,
    'status': 'pass' if $FAILED_WF == 0 else 'fail',
    'checkpoint': '$CHECKPOINT_FILE'
}, indent=2))
"
else
  echo "=== Summary ==="
  echo "  Total: $TOTAL_WF | Passed: $PASSED_WF | Failed: $FAILED_WF | Skipped: $SKIPPED_WF"
  echo "  Checkpoint: $CHECKPOINT_FILE"
  if [ "$FAILED_WF" -eq 0 ]; then
    echo "  Status: ALL PASSED"
  else
    echo "  Status: BLOCKED (fix and --resume)"
  fi
fi

exit $( [ "$FAILED_WF" -eq 0 ] && echo 0 || echo 1 )
