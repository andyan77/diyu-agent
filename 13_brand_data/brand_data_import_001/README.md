# Brand data import-ready package

This package is the offline, simulation-only handoff for
`DIYU_BRAND_DATA_IMPORT_READY_001`. It contains nine byte-identical source
snapshots, deterministic level-one narrative sections, a small precise-fact
set, expression import candidates, and compact checker cases.

Nothing here is database-imported, retrieval-ready, runtime-authoritative, or
publishable. `READY_FOR_PACKAGE_5_REVIEW` means only that source, registered
scope, and authorization references close well enough for package 5 to review;
it never means direct runtime consumption.

Regenerate the derived data from the frozen snapshots:

```bash
python3 13_brand_data/brand_data_import_001/materialize_brand_data.py
```

Run the only checker entry:

```bash
python3 13_brand_data/brand_data_import_001/check_brand_data_import.py
python3 13_brand_data/brand_data_import_001/check_brand_data_import.py --selftest
```

The checker intentionally refuses `python3 -O` with exit code 2. It proves
byte identity, reference closure, registered identifier and authorization
constraints, deterministic materialization, write scope, and explicit false
readiness. It does not claim to understand source semantics or expression
quality; those judgments are recorded by the two independent reviews.
