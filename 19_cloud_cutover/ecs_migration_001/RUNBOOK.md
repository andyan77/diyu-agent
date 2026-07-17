# Package 9 ECS Cutover Runbook

This package adopts the existing Package 7 application, dataset, database, and
bridge. It does not create a parallel Diyu runtime.

## Order of operations

1. Inventory the live host and keep every object whose ownership or dependency
   is not proven.
2. Create encrypted, server-external backups and verify database, vector, file,
   and proxy restores in isolated containers.
3. Stop the existing bridge. Install the Package 8 operational tables, import
   the second synthetic brand, and materialize the current database projection.
4. Reconcile the existing Dify application and dataset to that projection.
5. Apply database role separation and forced row-level security with
   `ecs_cutover.py apply-database-security`.
6. Recreate the same bridge with the non-bypass runtime role and the frozen
   release tree. Add only the `/apps/` loopback proxy to the existing TLS site.
7. Run deterministic checks before the bounded remote journeys. Delete only
   legacy objects whose dependency, encrypted backup, and isolated restore are
   all proven.
8. Verify restart, backup, isolated restore, and rollback. Keep every backup
   until Package 10 and a later Founder disposal decision are complete.

## Security invariants

- Secrets live only in root-restricted server state and never in Git.
- The browser cannot set tenant, brand, organization, store, account, or
  principal database scope.
- The runtime role cannot bypass row-level security or read migration-only
  tables.
- Dify, PostgreSQL, Qdrant, their internal data, and unrelated applications are
  preserved.
- `production_ready`, `release_ready`, and all other production readiness flags
  remain false. A passing Package 9 result is only a Package 10 candidate.

## Rollback

Remove the `/apps/` location, restore the prior bridge release and environment,
and run `ecs_cutover.py rollback-database-security` with the restricted admin
connection. If data restoration is required, use the matching encrypted backup
manifest and offline release bundle; never restore an unverified or mismatched
artifact.
