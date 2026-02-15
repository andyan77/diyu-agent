#!/bin/bash
# user_prompt_guard.sh - UserPromptSubmit hook
# Validates user prompts before processing.
# Checks for accidental secret exposure in prompts.
#
# Input (stdin): JSON with prompt_content
# Exit 0: allow, Exit 2: block (secret pattern detected)

set -e

# Read input from stdin
INPUT=$(cat)

# Extract prompt content using Python for reliable JSON parsing
PROMPT=$(python3 -c "
import sys, json
d = json.load(sys.stdin)
ti = d.get('tool_input', d)
print(ti.get('prompt', ti.get('content', '')))
" <<< "$INPUT" 2>/dev/null || echo "")

# Check for common secret patterns in user prompts
if echo "$PROMPT" | grep -qiE '(sk-[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|-----BEGIN (RSA |EC )?PRIVATE KEY-----)'; then
    echo "[UserPromptSubmit] BLOCKED: Potential secret detected in prompt. Redact before submitting." >&2
    # Log the event (no secret content in log)
    mkdir -p .audit 2>/dev/null || true
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] SECRET_PATTERN_BLOCKED in prompt" >> .audit/prompt-guard.log 2>/dev/null || true
    exit 2
fi

# Semantic keyword detection (Section 12.7)
# Suggest relevant agents/skills based on prompt keywords
if echo "$PROMPT" | grep -qiE '(RLS|rls|row.level|multi.tenant|org_id|tenant)'; then
    echo "SUGGEST: Use diyu-security-reviewer agent for RLS/multi-tenant review" >&2
fi
if echo "$PROMPT" | grep -qiE '(layer|port|hexagonal|architect|cross.layer|import.violation)'; then
    echo "SUGGEST: Use diyu-architect agent for layer boundary review" >&2
fi
if echo "$PROMPT" | grep -qiE '(migration|alembic|schema.change|alter.table)'; then
    echo "SUGGEST: Use guard-migration-safety skill before applying migrations" >&2
fi
if echo "$PROMPT" | grep -qiE '(task.card|governance|milestone|traceability)'; then
    echo "SUGGEST: Use taskcard-governance skill for task card validation" >&2
fi
if echo "$PROMPT" | grep -qiE '(tdd|test.driven|unit.test|coverage|pytest|test.first)'; then
    echo "SUGGEST: Use diyu-tdd-guide agent for test-driven development" >&2
fi
if echo "$PROMPT" | grep -qiE '(audit|systematic.review|cross.reference|full.audit|review.report)'; then
    echo "SUGGEST: Use systematic-review or cross-reference-audit skill for codebase auditing" >&2
fi
if echo "$PROMPT" | grep -qiE '(port.compat|breaking.change|interface.contract|port.interface|backward.compat)'; then
    echo "SUGGEST: Use guard-port-compat skill for Port interface compatibility check" >&2
fi

# No secret detected, allow
echo "$INPUT"
exit 0
