# Execution review request

Candidate scope: `13_brand_data/brand_data_import_001/**` only. Reviewers must
evaluate the fixed candidate commit recorded in `brand_data_import_result.v1.json`.

- `PKG3-A01`: Verify all nine snapshots and manifest digests are byte-identical and reproducible.
- `PKG3-A02`: Verify every narrative unit and precise fact closes to a snapshot line and byte range.
- `PKG3-A03`: Verify precise values are source-supported and missing values were not inferred.
- `PKG3-A04`: Verify review candidates use only public-contract identifiers.
- `PKG3-A05`: Verify unregistered scopes remain isolated without headquarters or store remapping.
- `PKG3-A06`: Verify missing authorization, expiry, revocation, pause, conflict, and internal limits cannot be directly consumed.
- `PKG3-A07`: Verify narrative and precise-fact partitions preserve time and precedence boundaries.
- `PKG3-A08`: Verify expression candidates, modes, and examples cannot grant facts, scope, authorization, runtime authority, or publishing.
- `PKG3-A09`: Verify all 11 accounts map to the neutral default without inventing 11 personas or runtime resolution.
- `PKG3-A10`: Verify normal, supplement, degradation, unauthorized, revoked, expired, and conflict cases remain represented.
- `PKG3-A11`: Verify deterministic materialization, one checker entry, and one compact parameterized case file.
- `PKG3-A12`: Verify external calls are zero, all readiness flags remain false, and the 300/120/86 assets are untouched.

Machine checks intentionally stop at deterministic structure and authority
closure. Source semantics, brand expression quality, and downstream usefulness
must be judged independently and must not be inferred from checker success.
