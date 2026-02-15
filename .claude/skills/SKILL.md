---
name: diyu-skills-index
description: >-
  Root skill index for DIYU Agent. Provides the systematic review methodology
  (discovery mode) for auditing code against specifications. Use when reviewing
  code against architecture docs, checking scaffold completeness, auditing
  governance compliance, or any scenario where exhaustive coverage tracking is
  needed.
---

# Skill: Systematic Review (Discovery)

> Solves: "Reviewed the code but missed half the requirements" -- the incomplete
> coverage failure mode where the reviewer checks a few items then generalizes
> "everything looks fine."

## When to Activate

- Auditing code against architecture documents or design specs
- Checking scaffold/skeleton completeness against a specification
- Reviewing governance compliance (治理规范 adherence)
- Verifying document-to-code alignment (e.g., "did all DDL in the spec get migrated?")
- Any task phrased as "check if X matches Y" or "audit X against Y"
- When the user explicitly invokes this skill

## Anti-Patterns This Skill Prevents

1. **Sampling bias**: Checking 3 of 15 requirements and concluding "looks good"
2. **Memory-based review**: "I think that file exists" without actually checking
3. **Premature conclusion**: Declaring "audit complete" after reviewing 60% of items
4. **Scope creep into fixing**: Starting to fix problems mid-review instead of
   completing the full discovery pass first
5. **Invisible denominator**: Reporting "found 3 issues" without stating "out of N
   total checks" -- making it impossible to judge coverage

---

## Phase 0: Source Identification and Chunking

The #1 reason reviews are incomplete is that the source document is too large
to hold in context alongside the code being reviewed. This phase solves that.

### Steps

1. **Identify the authoritative source document(s).** This is the architecture
   spec, governance doc, design doc, or standard that defines "what should exist."

2. **Measure the source scope.** Count the total number of verifiable items:
   - For architecture docs: count sections, tables, Port definitions, DDL statements
   - For governance docs: count rules, gates, required files, CI checks
   - For scaffold specs: count required files and directories
   State: "Source contains approximately N verifiable items."

3. **Chunk the source into review batches of max 10 items each.**
   Group by logical unit (layer, phase, file group). Each chunk must be
   self-contained -- a reviewer should be able to check one chunk without
   reading others.
   ```
   Example:
   Source: 治理规范 v1.1 正文
   Chunk 1: Section 1-2 (SSOT定义 + 目录依赖) → 8 checkable items
   Chunk 2: Section 3-4 (技术栈 + 分支策略) → 7 checkable items
   Chunk 3: Section 5 (CI门禁) → 12 checkable items
   ...
   Total: 5 chunks, ~45 checkable items
   ```

4. **Declare the chunk plan to the user.** The user must see the plan before
   execution begins. This prevents the "reviewed some stuff" failure mode.

### Gate

- [ ] Source document(s) identified by exact path or reference
- [ ] Total verifiable item count stated
- [ ] Chunks defined with item counts per chunk
- [ ] Chunk plan shown to user

---

## Phase 1: Per-Chunk Extraction

Process ONE chunk at a time. Do NOT read ahead to the next chunk.

### Steps

1. **Read the chunk from the source document using a tool.**
   `cat <file> | sed -n '<start>,<end>p'` or equivalent.
   Do NOT paraphrase from memory. Fresh read is mandatory.

2. **Extract every verifiable claim as a checklist item.** Each item must be:
   - **Specific**: "File `src/ports/memory_core.py` exists" not "ports exist"
   - **Binary**: Can be answered YES or NO, not "partially"
   - **Tool-verifiable**: Can be checked with ls, grep, cat, or similar

3. **Number items sequentially across all chunks** (not resetting per chunk).
   ```
   Chunk 1:
   [C01] File pyproject.toml exists at repo root
   [C02] pyproject.toml contains ruff configuration
   [C03] File uv.lock exists at repo root
   [C04] Makefile exists at repo root
   ...
   Chunk 2:
   [C09] src/ports/memory_core.py defines MemoryCorePort interface
   [C10] src/ports/llm_call.py defines LLMCallPort interface
   ...
   ```

4. **After extraction, verify count:**
   "Chunk N: extracted M items. Running total: X / Y (estimated)."

### Rules

- Extract EVERY verifiable claim, even trivial ones ("file exists").
  Completeness > brevity.
- If a source paragraph contains no verifiable claims (e.g., motivation text),
  skip it and note: "Paragraph X: narrative only, no verifiable claims."
- If a claim is ambiguous (e.g., "appropriate testing"), flag it:
  "[C15] AMBIGUOUS: 'appropriate testing' -- cannot verify without clarification"

### Gate

- [ ] All items extracted from current chunk using tool-based source read
- [ ] Each item is specific, binary, and tool-verifiable
- [ ] Running count tracks progress toward total

---

## Phase 2: Per-Chunk Verification

Verify each item in the current chunk BEFORE moving to the next chunk.

### Steps

1. **For each item, run a verification command:**
   - File existence: `ls -la <path>` or `test -f <path> && echo EXISTS || echo MISSING`
   - Content check: `grep -n '<pattern>' <file>`
   - Structure check: `find <dir> -name '<pattern>' -type f`
   - Config check: `cat <file> | grep '<key>'`

2. **Record the result with evidence:**
   ```
   [C01] ✅ PASS -- pyproject.toml exists
         Evidence: ls -la pyproject.toml → -rw-r--r-- 1 user user 2847 ...
   [C02] ❌ FAIL -- pyproject.toml missing ruff configuration
         Evidence: grep -n 'ruff' pyproject.toml → (no output)
         Finding: F01 -- ruff config absent from pyproject.toml
   [C03] ⚠️ PARTIAL -- uv.lock exists but is empty (0 bytes)
         Evidence: ls -la uv.lock → -rw-r--r-- 1 user user 0 ...
         Finding: F02 -- uv.lock is empty, dependencies not locked
   ```

3. **Never mark an item PASS without command output evidence.**
   "I checked earlier" or "I know this exists" is NOT evidence.

4. **After each chunk, output a chunk summary:**
   ```
   Chunk 2 complete: 8 items checked
   ✅ PASS: 5  ❌ FAIL: 2  ⚠️ PARTIAL: 1
   New findings: F04, F05, F06
   Running total: 16/45 items checked, 4 findings so far
   ```

### Adversarial Self-Check (per chunk)

Before moving to the next chunk, ask:
- "Did I actually run a command for every item, or did I skip any?"
- "Did I mark anything PASS based on assumption rather than evidence?"
- "Is there an item I marked PASS that a skeptical reviewer would challenge?"

If any answer is "yes", go back and re-verify.

### Gate

- [ ] Every item in chunk has a verdict (PASS/FAIL/PARTIAL) with command evidence
- [ ] Adversarial self-check completed for this chunk
- [ ] Chunk summary with running totals displayed

---

## Phase 3: Coverage Reconciliation

After ALL chunks are processed, reconcile coverage.

### Steps

1. **Compute final coverage:**
   ```
   Total items: 45
   Checked: 45 (100%)
   ✅ PASS: 31
   ❌ FAIL: 9
   ⚠️ PARTIAL: 3
   ⚠️ AMBIGUOUS: 2
   ```

2. **Verify coverage is complete.**
   If checked < total, identify which items were missed and verify them now.
   Do NOT report until coverage = 100% of extracted items.

3. **Cross-check: scan for items the source implies but didn't explicitly state.**
   For example, if the source says "4 guard scripts" but only names 3,
   ask: "Is there a 4th I should check for?"
   Record as: "[C46] INFERRED: possible 4th guard script not explicitly named"

### Gate

- [ ] Coverage = 100% of extracted items
- [ ] Cross-check for implied but unstated items completed
- [ ] All findings numbered sequentially (F01, F02, ...)

---

## Phase 4: Findings Report

Produce the report. This is a DISCOVERY report, not a fix plan.

### Format

```
## Review Report -- {date}

### Source: {document name, version, path}
### Target: {what was reviewed -- repo path, branch, commit}

### Coverage
- Source scope: N verifiable items extracted
- Items checked: N (100%)
- Chunks: K

### Summary
- ✅ PASS: N
- ❌ FAIL: N (findings)
- ⚠️ PARTIAL: N (findings)
- ⚠️ AMBIGUOUS: N (need clarification)

### Findings

| ID | Severity | Check Item | Evidence Summary | Affected Files |
|----|----------|-----------|-----------------|----------------|
| F01 | HIGH | ruff config missing | grep returned empty | pyproject.toml |
| F02 | MED  | uv.lock empty | ls shows 0 bytes | uv.lock |
| ... | ...  | ... | ... | ... |

### Items Needing Clarification
- [C15] "appropriate testing" -- source is ambiguous, cannot verify

### Pass List (collapsed)
<details>
<summary>31 items passed -- click to expand</summary>

| ID | Item | Evidence |
|----|------|----------|
| C01 | pyproject.toml exists | ls confirmed |
| ... | ... | ... |

</details>

---
Status: REVIEW COMPLETE -- {N} findings for human triage
Reviewer: This report identifies gaps. It does NOT prioritize or fix them.
Use `adversarial-fix-verification` skill to process the findings list.
```

### Rules

- Report status is "REVIEW COMPLETE", not "everything is fine"
- EVERY finding must have evidence (command output reference)
- The pass list is included (collapsed) so the human can verify coverage
- Severity is the reviewer's best estimate; human overrides are expected
- The report explicitly links to the fix skill for next steps

---

## Context Budget Management

This skill is designed for large-scope reviews that can exceed context limits.

### Rules

1. **Never hold more than 2 chunks in active context at once**
   (current chunk being extracted + current chunk being verified).
2. **Write chunk results to a file as you go:**
   Append to `review-progress.md` after each chunk completes.
   This ensures progress survives context pressure.
3. **If context feels heavy (you notice degraded quality), STOP and tell the user:**
   "I've completed N/K chunks. Recommend continuing in a new session
   starting from Chunk {N+1}. Progress saved to review-progress.md."
4. **Maximum single-session scope: 50 items or 5 chunks, whichever comes first.**
   Beyond this, split into multiple sessions.

---

## Relationship to Other Skills

- **Output → `adversarial-fix-verification`**: This skill's findings report
  is the input to the fix verification skill.
- **Output → `cross-reference-audit`**: If the review reveals potential
  document-to-code drift, use cross-reference-audit for detailed comparison.
- This skill does NOT fix anything. It only discovers and reports.
  Mixing discovery with fixing causes both to be incomplete.

---

## Quick Reference: Review Completeness Anti-Patterns

| Anti-Pattern | Example | Why It Fails | Fix |
|---|---|---|---|
| Sampling | Check 3 of 15 items | Misses 80% of issues | Extract ALL items first |
| Memory-based | "I think that exists" | No evidence trail | Run command, paste output |
| Premature stop | "Looks mostly complete" | Unknown denominator | Track checked/total |
| Fix-during-review | Start coding a fix mid-audit | Review never finishes | Discovery ONLY, fix later |
| Invisible denominator | "Found 3 issues" | 3 of what? 10? 100? | Always state X/N |
| Stale read | Read file 20 turns ago | File may have changed | Fresh read per chunk |
