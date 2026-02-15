#!/usr/bin/env bash
# run_phase1_v4.sh - V4 Phase 1 Build Orchestrator
#
# Executes the 7-workflow pipeline defined in delivery/v4-workflows.yaml.
# Supports checkpoint/resume so interrupted sessions can continue.
#
# Usage:
#   bash scripts/run_phase1_v4.sh                     # Run all pending workflows
#   bash scripts/run_phase1_v4.sh --wf WF-B1          # Run specific workflow
#   bash scripts/run_phase1_v4.sh --resume             # Resume from last checkpoint
#   bash scripts/run_phase1_v4.sh --dry-run            # Show execution plan
#   bash scripts/run_phase1_v4.sh --json               # JSON output
#   bash scripts/run_phase1_v4.sh --status             # Show current state
#   bash scripts/run_phase1_v4.sh --reset              # Clear checkpoint, start fresh
#
# Architecture:
#   This orchestrator manages the BUILD pipeline (WF-P0 -> WF-A1 -> WF-B{1..4} -> WF-A2).
#   The existing W1-W4 governance pipeline (run_all.sh) is invoked AS PART of WF-A1/WF-A2.
#
# User-level agents (/plan, /tdd, code-reviewer) are optional enhancements.
# This script runs without them. When Claude Code is available, it can invoke
# the /phase1-build command which calls this script with agent augmentation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKFLOWS_FILE="$ROOT_DIR/delivery/v4-workflows.yaml"
EVIDENCE_DIR="$ROOT_DIR/evidence/v4-phase1"
CHECKPOINT_FILE="$EVIDENCE_DIR/checkpoint.json"
SESSION_ID="${SESSION_ID:-$(date +%Y%m%dT%H%M%S)}"

# Defaults
TARGET_WF=""
RESUME=false
DRY_RUN=false
JSON_OUTPUT=false
SHOW_STATUS=false
RESET=false

# Parameter parsing (while/shift pattern)
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

# Load existing or create new
if os.path.exists(cp_file):
    with open(cp_file) as f:
        cp = json.load(f)
else:
    cp = {'session_id': session, 'workflows': {}, 'created': ts}

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

# --- Workflow loading ---

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
        for dep in wf['depends_on']:
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

# --- Reset ---

if [ "$RESET" = true ]; then
  rm -f "$CHECKPOINT_FILE"
  if [ "$JSON_OUTPUT" = true ]; then
    echo '{"action":"reset","status":"done"}'
  else
    echo "Checkpoint cleared. Next run starts fresh."
  fi
  exit 0
fi

# --- Status ---

if [ "$SHOW_STATUS" = true ]; then
  CP=$(load_checkpoint)
  if [ "$JSON_OUTPUT" = true ]; then
    echo "$CP"
  else
    echo "=== V4 Phase 1 Build Status ==="
    echo ""
    WF_IDS=$(load_workflow_ids)
    while IFS= read -r wf_id; do
      wf_status=$(get_wf_status "$wf_id")
      wf_name=$(load_workflow_name "$wf_id")
      case "$wf_status" in
        done)    marker="[x]" ;;
        failed)  marker="[!]" ;;
        *)       marker="[ ]" ;;
      esac
      echo "  $marker $wf_id: $wf_name ($wf_status)"
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

run_wf_checks() {
  local wf_id="$1"
  local checks_json
  checks_json=$(load_workflow_checks "$wf_id")

  local total=0
  local passed=0
  local failed=0

  python3 -c "
import json, subprocess, sys, os

wf_id = sys.argv[1]
checks = json.loads(sys.argv[2])
evidence_dir = sys.argv[3]
json_output = sys.argv[4] == 'true'

os.makedirs(f'{evidence_dir}/{wf_id}', exist_ok=True)

results = []
total = len(checks)
passed_count = 0
failed_count = 0

for check in checks:
    name = check['name']
    cmd = check.get('command', '')
    if not cmd:
        results.append({'name': name, 'status': 'skip', 'reason': 'no command'})
        continue

    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=120, cwd=os.path.dirname(evidence_dir).rstrip('/v4-phase1') or '.'
        )
        if r.returncode == 0:
            results.append({'name': name, 'status': 'pass'})
            passed_count += 1
        else:
            results.append({
                'name': name, 'status': 'fail',
                'exit_code': r.returncode,
                'stderr': r.stderr[:500] if r.stderr else ''
            })
            failed_count += 1
    except subprocess.TimeoutExpired:
        results.append({'name': name, 'status': 'fail', 'reason': 'timeout'})
        failed_count += 1
    except Exception as e:
        results.append({'name': name, 'status': 'fail', 'reason': str(e)})
        failed_count += 1

# Write check results
with open(f'{evidence_dir}/{wf_id}/checks.json', 'w') as f:
    json.dump({'workflow': wf_id, 'checks': results, 'total': total,
               'passed': passed_count, 'failed': failed_count}, f, indent=2)

if not json_output:
    for r in results:
        icon = 'PASS' if r['status'] == 'pass' else 'FAIL' if r['status'] == 'fail' else 'SKIP'
        print(f'    [{icon}] {r[\"name\"]}')

sys.exit(1 if failed_count > 0 else 0)
" "$wf_id" "$checks_json" "$EVIDENCE_DIR" "$JSON_OUTPUT"
}

# --- Dry run ---

if [ "$DRY_RUN" = true ]; then
  WF_IDS=$(load_workflow_ids)
  if [ "$JSON_OUTPUT" = true ]; then
    python3 -c "
import yaml, json
with open('$WORKFLOWS_FILE') as f:
    data = yaml.safe_load(f)
plan = []
for wf in data['workflows']:
    plan.append({
        'id': wf['id'], 'name': wf['name'],
        'depends_on': wf['depends_on'],
        'task_cards': wf.get('task_cards', []),
        'checks_count': len(wf.get('checks', []))
    })
print(json.dumps({'mode': 'dry-run', 'plan': plan}, indent=2))
"
  else
    echo "=== V4 Phase 1 Build Plan (dry-run) ==="
    echo ""
    while IFS= read -r wf_id; do
      wf_name=$(load_workflow_name "$wf_id")
      wf_status=$(get_wf_status "$wf_id")
      wf_cards=$(load_workflow_cards "$wf_id")
      deps=$(load_workflow_deps "$wf_id")
      echo "  $wf_id: $wf_name"
      echo "    Status: $wf_status"
      if [ -n "$deps" ]; then
        echo "    Depends: $(echo "$deps" | tr '\n' ', ' | sed 's/,$//')"
      fi
      echo "    Cards: $wf_cards"
      echo ""
    done <<< "$WF_IDS"
    echo "Use --resume to continue from last checkpoint."
    echo "Use --wf WF-XX to run a specific workflow."
  fi
  exit 0
fi

# --- Main execution ---

execute_workflow() {
  local wf_id="$1"
  local wf_name
  wf_name=$(load_workflow_name "$wf_id")

  # Check current status
  local current_status
  current_status=$(get_wf_status "$wf_id")

  if [ "$current_status" = "done" ]; then
    if [ "$JSON_OUTPUT" = false ]; then
      echo "  [$wf_id] $wf_name -- already done, skipping"
    fi
    return 0
  fi

  # Check dependencies
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

  # For build workflows (WF-B*), this is where Claude Code implements task cards.
  # The orchestrator runs the CHECK phase only. Implementation is driven by
  # the /phase1-build command or manual task card execution.

  local wf_cards
  wf_cards=$(load_workflow_cards "$wf_id")
  local card_count
  card_count=$(python3 -c "import json; print(len(json.loads('$wf_cards')))")

  if [ "$card_count" -gt 0 ] && [ "$JSON_OUTPUT" = false ]; then
    echo "  Task cards: $wf_cards"
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
    'status': 'done' if $EXIT_CODE == 0 else 'failed',
    'session': '$SESSION_ID'
}))
"
  fi
  exit $EXIT_CODE
fi

# --- Run all (with resume support) ---

if [ "$JSON_OUTPUT" = false ]; then
  echo "=== V4 Phase 1 Build Orchestrator ==="
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

  # On resume, skip already-done workflows
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
