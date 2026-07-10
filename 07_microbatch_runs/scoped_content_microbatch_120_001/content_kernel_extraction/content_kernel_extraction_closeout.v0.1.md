# Content Kernel Extraction Closeout

The extraction split the scoped 120 into two lanes:

- `user_visible_kernel_matrix.v0.1.yaml`: content fuel candidates such as object anchors, human subjects, actions, scenes, business judgment, tension, spoken-line seeds, and output asset hints.
- `review_packet_kernel_matrix.v0.1.yaml`: claim boundaries, fact slots, downgrade paths, owner route, and release status. This lane is review-only and must not leak into user-visible body text.

Source traces point back to `rich_body_blocks.yaml` and preserve original source hashes. This is not a Serving Projection, RAG context bundle, DIFY workflow, CandidatePack, KE truth source, or production asset.

Clean-A routing is summary-only: 100 candidates are represented as a derived pool rather than invented per-item CPSS scores. Explicit per-ID queues are limited to B, C, and receipt first-review items.
