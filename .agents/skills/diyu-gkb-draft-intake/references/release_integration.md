# Release Integration

Gold hooks and serving specs are candidate inputs only.

## Serving Spec Boundary

Serving passage spec candidates may define:

- projection scope
- allowed uses
- excluded content
- source trace requirements
- digest requirements

They must not define approved passage text, rendered body, passage text, or context bundle items.

## Gold Hook Boundary

Gold hook candidates are release input candidates for existing gates:

- Step 20 Gold Hooks Rebaseline
- Step 21 Release Gate

They must not create an independent gold system, bypass Step 20, bypass Step 21, or claim release readiness.
