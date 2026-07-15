# Light Expression Service

This package implements the Phase B local vertical slice of the public light-expression contract. It prepares one deterministic `LightContentPlan` or action card, then validates candidate references and deterministic hard boundaries. It does not write audience content, call a model, connect to Dify, or access a database.

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
