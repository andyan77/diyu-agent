# Light Expression Service

This package implements the Phase B local vertical slice of the public light-expression contract. It prepares one deterministic `LightContentPlan` or action card, then validates candidate references and deterministic hard boundaries. It does not write audience content, call a model, connect to Dify, or access a database.

Facts, narrative fragments, and the confirmed task are usable only when the server-owned trusted context has registered their exact object digests. Repeating a legal authorization reference inside the request body cannot register or upgrade new evidence.

The confirmed task carries an explicit internal content-product route, primary audience, and any precise fact kinds required by its claims. Narrative-only plans are allowed when no precise claim is requested; missing task-required facts return a collection action card. Missing product or audience routing never falls back to a hash, keyword guess, fixed product, or default audience. Unknown creative hints are ignored with diagnostics unless they attempt to override a server-owned hard boundary.

Run the focused tests and package gate:

```bash
python3 12_expression_service/expression_runtime_adapter_001/test_light_expression_service.py
python3 12_expression_service/expression_runtime_adapter_001/check_light_expression_service.py
python3 12_expression_service/expression_runtime_adapter_001/check_light_expression_service.py --selftest
```

Start a local acceptance server with the repository's explicitly non-publishable simulation identity:

```bash
python3 12_expression_service/expression_runtime_adapter_001/http_entrypoint.py \
  serve --port 8080 --simulation-context
```

Without `--simulation-context`, the process still exposes health and local static readiness, but content requests fail closed because no server-owned trusted context has been injected.
