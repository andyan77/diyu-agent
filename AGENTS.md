# AGENTS.md

## Project role

This repository is the Diyu knowledge engineering workspace.

## Non-negotiable architecture rules

- Do not write raw Markdown or GPT output directly into ABox or TBox.
- Do not write KE truth source unless the task explicitly authorizes KE landing.
- Do not write Serving Projection unless the task explicitly authorizes serving materialization.
- Do not write RAG context_bundle unless the task explicitly authorizes RAG work.
- Do not write DIFY workflow unless the task explicitly authorizes DIFY work.
- RAG must only consume serving projection.
- DIFY must only consume context_bundle.
- User feedback must not write ABox / TBox / Evidence directly.
- No evidence means not production_servable.
- not_production_ready must not enter generation.

## Readiness flags

Unless a task explicitly authorizes a readiness transition, all of the following must remain false:

- candidatepack_ready
- KE_ready
- RAG_ready
- DIFY_ready
- production_servable
- generation_eligible
- generation_allowed
- release_ready
- production_ready

## Forbidden default writes

Do not modify:

- KE/**
- serving_projection/**
- rag/**
- dify/**
- candidatepack_etl/candidatepack_instances/**
- runtime production files
- secret files
- external service config

unless explicitly listed in the Execution Brief allowed writes.

## Required execution discipline

- Read the Execution Brief before writing.
- Stop if baseline HEAD or worktree status differs.
- Stop if allowed write surface is ambiguous.
- Stop if a task requires production, external runtime, secret handling, or true KE landing without explicit authorization.
- Run only delta checks required by the task.
- Report changed files, checks run, failures, and readiness flags.