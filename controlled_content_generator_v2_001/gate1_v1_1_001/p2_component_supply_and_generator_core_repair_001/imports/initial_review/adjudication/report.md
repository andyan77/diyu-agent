# Targeted Third Adjudication

## Scope

This run adjudicates only the 92 genuine decision disagreements in the frozen 244-item P2 packet. The 152 matching primary/secondary decisions were not adjudicated. No control-rule item had a decision disagreement.

Identity: `TARGETED_THIRD_ADJUDICATION` / `P2-TARGETED-ADJUDICATOR-C` / session `019f5de8-8338-7082-9d10-96cf5bbf7c21` / run `P2-ADJUDICATION-RUN-20260713-C37A894`.

## Frozen Binding

| Input | Binding |
|---|---|
| Reviewed commit | `c37a894930025aac99db18a055d5a79294fa89dc` |
| Review packet | `controlled_content_generator_v2_001/gate1_v1_1_001/p2_component_supply_and_generator_core_repair_001/review/independent_component_review_packet.v0.1.jsonl` |
| Packet SHA-256 | `67751ab60e6ee8e227c4aaff3dccd4c7f3c5d027ceda2f910f4ea1a600231095` |
| Packet records | 244 |
| Primary records SHA-256 | `a53d4a6c23b07eb40f26e82580d08f01b6995fa613bfb394ca6b7e25846712b2` |
| Secondary records SHA-256 | `e6e3445af0113122ffb23d30e12e775e58433a6f925c36fe6dfb8e1531296e2b` |
| Frozen v1.1 standard SHA-256 | `022fc9b96919233e6f5268f5f9d0722b592914cc8919b5d1628dd3600a494542` |
| Frozen 20-product profiles SHA-256 | `d38c7139d5eb5b88745b20adc37f6e4c97e42dff3076aca5d2822d78be5c1056` |
| Frozen A/B contract SHA-256 | `6862166cffb84dfb45ad8d98c82d5ae1faed18739df5e502d43a5d21d384a221` |

Both input review files contain 244 unique packet-ordered records, bind the required commit and packet hash, and pass canonical record-digest recomputation.

## Result

| Object type | Disputed | APPROVE | REPAIR | REJECT |
|---|---:|---:|---:|---:|
| PROPOSED_ACTIVE_COMPONENT | 25 | 0 | 25 | 0 |
| PROPOSED_COMPONENT_CP_EDGE | 62 | 0 | 40 | 22 |
| AB_STRUCTURAL_PATH_CAPABILITY | 5 | 0 | 1 | 4 |
| **Total** | **92** | **0** | **66** | **26** |

Decision-pair resolution:

| Primary / Secondary | Disputed | Adjudicated outcome |
|---|---:|---|
| APPROVE / REPAIR | 57 | 57 REPAIR |
| REPAIR / APPROVE | 2 | 2 REPAIR |
| REJECT / APPROVE | 9 | 9 REJECT |
| REJECT / REPAIR | 18 | 2 REPAIR, 16 REJECT |
| APPROVE / REJECT | 1 | 1 REJECT |
| REPAIR / REJECT | 5 | 5 REPAIR |

## Adjudication Basis

1. All 23 disputed source-derived component parent references were independently recomputed against the frozen parent corpus: parent canonical digests, field paths, occurrences, and span digests all passed. Provenance identity was therefore preserved rather than treated as defective.
2. Those 23 candidates still hide factual or authorization-bearing values in generic input slots while leaving typed fact/authorization arrays empty; several also overstate what the verified span supports. The two disputed design components are honestly sourced but provide authority/perspective boundaries rather than substantive professional judgment. All 25 component disagreements therefore resolve to REPAIR.
3. Every disputed edge exactly copies a required role, profile bindings, guards, and a historically listed applicability. The frozen constructor generated those relations from exact role plus historical applicability and used a generic fit projection. Item-specific semantic fit was therefore read from the actual component mechanism and CP profile, not inferred from structural equality.
4. Forty edge relations are conditionally usable after explicit CP-specific slot/compatibility binding and any dependent component repair. Twenty-two relations require a different or reclassified mechanism and are rejected.
5. The A/B records do not bind the contract's shared fact/source/authorization/material fields, omit `primary_question` and `narrative_operator`, and repeat generic lane descriptors without realization evidence. CP16 is repairable; CP04, CP05, CP18, and CP20 require path reconstruction and are rejected.

## Rejected Edges

- `P2-P2-EDGE-CP01-professional_judgment-02`
- `P2-P2-EDGE-CP02-scene-02`
- `P2-P2-EDGE-CP03-observable_action-01`
- `P2-P2-EDGE-CP03-trigger-01`
- `P2-P2-EDGE-CP04-scene-02`
- `P2-P2-EDGE-CP04-professional_judgment-01`
- `P2-P2-EDGE-CP04-professional_judgment-02`
- `P2-P2-EDGE-CP05-scene-01`
- `P2-P2-EDGE-CP05-scene-02`
- `P2-P2-EDGE-CP05-trigger-01`
- `P2-P2-EDGE-CP05-trigger-02`
- `P2-P2-EDGE-CP05-professional_judgment-01`
- `P2-P2-EDGE-CP09-trigger-02`
- `P2-P2-EDGE-CP10-professional_judgment-02`
- `P2-P2-EDGE-CP11-scene-02`
- `P2-P2-EDGE-CP12-professional_judgment-02`
- `P2-P2-EDGE-CP15-scene-01`
- `P2-P2-EDGE-CP16-professional_judgment-02`
- `P2-P2-EDGE-CP18-scene-02`
- `P2-P2-EDGE-CP19-professional_judgment-02`
- `P2-P2-EDGE-CP20-trigger-02`
- `P2-P2-EDGE-CP20-professional_judgment-02`

A/B outcomes: `P2-AB-CP16` is REPAIR. `P2-AB-CP04`, `P2-AB-CP05`, `P2-AB-CP18`, and `P2-AB-CP20` are REJECT.

## Non-Effects

Concurrent snapshot note: repository HEAD matched `c37a894930025aac99db18a055d5a79294fa89dc` at adjudication start and advanced to `6d7aa877a12867ee9a73e50a8e292ef4a631d7a9` before artifact closeout. All repository evidence was read from the immutable reviewed Git object; the later HEAD and dirty P2 files were not read or used in any ruling.

This adjudication preserves both reviewers' original decisions and records only a third ruling for disputed items. It does not activate components, edges, paths, P3 access, generator eligibility, runtime use, serving, release, or production. It makes no generator-completion or supply-closeout claim. All readiness flags remain false.

Repository reads were bound to the immutable reviewed commit. Concurrent dirty P2 implementation files in the working tree were not read or used, and this run wrote no repository file. The only writes are the three artifacts in `/mnt/c/Users/Administrator/Documents/笛语agent/tasks/GATE1_V11_COMPONENT_SUPPLY_AND_GENERATOR_CORE_REPAIR_001/independent_reviews/adjudication`.

## Artifact

`records.jsonl` contains 92 canonical JSON records in packet order. Its SHA-256 is `84be65d38eafae22b1bb50baebe17f7674bd298592f3d1b989b22c5c766062bc`. Each `record_digest` is SHA-256 of canonical UTF-8 JSON excluding `record_digest` (sorted keys, comma/colon separators, Unicode preserved).
