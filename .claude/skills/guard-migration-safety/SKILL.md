---
name: guard-migration-safety
description: >-
  Guard skill that validates database migration safety rules. Use after
  creating or modifying Alembic migrations, before merging PRs that
  touch migrations/versions/, or when reviewing destructive DDL changes.
---

# Guard: Migration Safety

Validates that database migrations follow safety rules: rollback capability,
destructive DDL markers, and data-loss prevention.

## Input

- **Scope**: `migrations/versions/` directory
- **Trigger**: Any change to `migrations/versions/*.py`

## Execution

```bash
bash scripts/check_migration.sh --json
```

## Output

JSON with `status` (pass/fail), `violations` array, and `count`.

```json
{"status": "pass", "violations": [], "count": 0}
```

## Failure Condition

Exit code 1 when any rule is violated:

| Rule | Condition |
|------|-----------|
| ROLLBACK | upgrade() without matching downgrade() |
| DESTRUCTIVE | DROP TABLE/COLUMN/TRUNCATE without `[CONFIRMED-DESTRUCTIVE]` marker |
| DELETE-ALL | DELETE FROM without WHERE clause and no marker |

## Remediation

1. Add `downgrade()` function that reverses the upgrade
2. Add `# [CONFIRMED-DESTRUCTIVE]` comment above destructive operations
3. Add WHERE clause to DELETE statements
4. Re-run `bash scripts/check_migration.sh --json` to confirm fix
