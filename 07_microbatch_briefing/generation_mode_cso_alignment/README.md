# Generation Mode × CSO Alignment（生成模式 × 内容策略轴 对齐层）

> 任务 / task: `GKB-PROOF-MICROBATCH-CLOSEOUT-AND-GENERATION-MODE-CSO-ALIGNMENT-001`（账本 step **P7B**）
> 性质 / status: **briefing_orchestration_contract** —— **不是** `01_generation_contracts` 正式 schema，**不是** ontology truth source（`formal_schema_contract: false` / `ontology_truth_source: false`）。

## 这层解决什么

笛语不是"单纯本体知识生成系统"，而是**服装行业内容生产系统**。两条轴正交横切：

- **本体轴 / Ontology Axis**：object / fact / claim / owner / evidence / role_permission / source_boundary / readiness —— 管"什么是真、谁拥有、边界在哪"。
- **内容策略轴 / CSO Axis**：叙事节奏 / 情绪张力 / 平台原生表达 / 角色口吻 / 审美取景 / 创意跳跃 / 真实人味 / 真实场景感 —— 管"好不好看、有没有人味、像不像平台原生"。

运行时由 **generation orchestration** 把两轴**叠加**成同一个 Creative Brief。本层把这套规则编译成契约，供后续 **P7C scoped microbatch** 消费。

## 文件清单

| 文件 | 作用 |
|---|---|
| `generation_mode_contract.v0.1.yaml` | 4 种生成模式：`creative_prototype` / `fact_slot_script` / `evidence_bound_candidate` / `display_solution` |
| `fact_binding_policy.v0.1.yaml` | 无事实≠不能生成；缺事实只挡 specific claim / evidence_bound；BrandKB slot = 接口边界，不建实例、不写品牌事实 |
| `ontology_cso_composition_contract.v0.1.yaml` | 两轴关系 = `orthogonal_cross_cutting` + `compositional_overlay`；CSO 字段禁入 ABox/TBox |
| `creative_pattern_requirements.v0.1.yaml` | ≥6 类创意模式（企业叙事/角色口吻/视觉场景/陈列转内容/产品角色故事/平台表达）；是生成输入非本体真值 |
| `p0_generation_mode_matrix.v0.1.yaml` | P0_00..P0_05 各组默认生成模式；P0_00 = 控制面，不进 GKB 正文生成 |
| `p7c_scoped_microbatch_route_plan.v0.1.yaml` | 下一步 = P7C scoped 120（默认；320 需另行 founder 授权）；**只解锁 brief/go-no-go，不授权生成** |
| `p7d_3600_deferral_decision.v0.1.yaml` | 3600 = P7D，`BLOCKED_BY_P7C`；直接 3600 仍禁 |

## 硬边界（本层不做）

- 不生成任何新草稿；不生成 3600；不建 CandidatePack；不跑 Four-Gate；不写 KE/Serving/RAG/DIFY。
- 不把 CSO 字段写进本体真值；不新增 ontology Object；不翻任何 readiness。
- 不改 P7A proof 原始产物（唯一写面 = `07_microbatch_runs/proof_microbatch_001/closeout/**`）。
- `creative_gate` 不等于 production readiness。
