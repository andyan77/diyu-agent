# Knowledge 层 (SSOT-B: Knowledge Stores)

> **所属层:** 知识层（企业知识资产域）  
> **依赖性:** 软依赖，可整体拔掉降级运行  
> **版本:** v3.6
> **验证标准:** 独立验证 FK 联动、Resolver、实体注册、FK 一致性保障；拔掉后 Brain 仍能对话  

---

## 1. 核心定位

> **[v3.1 修正]** Knowledge Stores 是企业知识资产域的 SSOT-B，与 Memory Core(SSOT-A) **平行不从属**。

```
Knowledge Stores = Neo4j（结构化资产图谱 SSOT）+ Qdrant（语义资产真值 + 个人投影）+ FK 联动协议

所有者: 组织（品牌/区域/门店/平台）
特征: 结构关系密集、规模大、变更需审计、继承链与权限严格

隐私硬边界: Knowledge Stores 永远不直接读 Memory Core。
```

---

## 2. 两库在知识资产域的真值职责

### 2.1 Neo4j（企业结构化资产图谱 SSOT）

```
适合承载"真值为图"的数据:
+-- SKU/品类层级、属性网络、适配规则
+-- 搭配关系（兼容度、约束、理由、适用场景）
+-- 组织结构与继承链（brand -> region -> store）
+-- 知识对象之间的强关系（SOP -> 岗位 -> 流程 -> 检查项）

关键实现点:
+-- 多租户与 org_scope 强制字段: 每个节点/边都必须带 tenant_id + org_scope + visibility/acl
+-- 版本治理（方案 A 起步，方案 B 后期叠加）:
      方案 A（起步）: 节点/边带 version, valid_from, valid_to, is_active
      方案 B（增强）: 引入 :ChangeSet 节点连接本次变更涉及的节点/边
+-- 审计回执: 每个 upsert/delete 都产出 knowledge_write_receipt
```

### 2.2 Qdrant（双用途，同库不同 source_type）

```
用途 1: 企业语义资产索引的 SSOT (source_type = "enterprise")
  +-- 案例库、内容片段、品牌规范拆分 chunk、政策文档段落、SOP 说明
  +-- 真值不是 embedding 数值本身，而是"可检索语义资产条目(chunk) + payload 元数据 + FK 关联"
  +-- embedding 可重算，但条目与其治理元数据是不可丢失的真值
  +-- 入库时原始文本必须存入 payload 或有可寻址的原始文档引用(doc_id + chunk_offset)

用途 2: 个人记忆的语义投影 (source_type = "personal_projection", 可选增强)
  +-- 从 Memory Core 的 memory_items 异步投影
  +-- 丢了可从 Memory Core 重建（仅此场景叫投影）
```

---

## 3. FK 联动协议

> **[v3.0 新增，v3.1 保持]** 这是知识驱动一切的技术基础。

### 3.1 联动规则

```
1. 每个 Neo4j 节点有全局唯一的 graph_node_id
2. 每个 Qdrant 向量条目的 payload 中携带 graph_node_id 字段
3. 一个图谱节点可以关联 0 到 N 个向量条目（一对多）
4. 一个向量条目必须关联 1 个图谱节点（多对一）
5. 所有向量条目的 payload 中同时携带 org_id、org_chain、visibility（继承图谱节点）
```

### 3.2 图谱节点通用属性

```
+-- graph_node_id: String         全局唯一 ID（前缀 + UUID）
+-- node_type: String             实体类型（如 "Product", "Persona", "StylingRule"）
+-- tenant_id: UUID               租户 ID
+-- owner_org_id: UUID            所属组织
+-- org_scope: String             组织范围
+-- visibility: Enum              global | brand | region | store
+-- acl: JSONB                    访问控制列表
+-- inheritable: Boolean          是否可被下级继承
+-- override_allowed: Boolean     是否允许下级覆盖
+-- version: Integer              版本号
+-- valid_from / valid_to         版本时效（方案 A）
+-- is_active: Boolean            当前激活版本
+-- created_at / updated_at
```

### 3.3 向量条目通用 payload

```
+-- vector_id: String             向量条目自身 ID
+-- graph_node_id: String         [FK] 关联的图谱节点
+-- source_type: String           "enterprise" | "personal_projection"
+-- content_type: String          内容类型标识（如 "product_description", "styling_rule"）
+-- tenant_id: UUID               租户 ID
+-- org_id: UUID                  所属组织（冗余，加速过滤）
+-- org_chain: [UUID]             组织链路（冗余，加速过滤）
+-- org_scope: String             组织范围（enterprise 必须有）
+-- visibility: Enum              可见性（冗余，与图谱节点一致）
+-- brand_id: UUID                品牌 ID（冗余，加速隔离）
+-- acl: JSONB                    访问控制
+-- text: String                  原始文本（用于展示 + 重算 embedding）
+-- doc_id: String                原始文档引用（文档类）
+-- chunk_id: String              chunk 标识
+-- chunk_offset: Integer         chunk 在原文中的位置
+-- embedding_model_id: String    embedding 模型 ID
+-- normalizer_version: String    归一化版本
+-- provenance: Object            入库来源、审批信息、解析器版本、hash
+-- metadata: Object              扩展元数据
```

### 3.4 FK 联动查询模式

**模式 A: 图谱优先 -> 向量补充（精确 -> 丰富）**

```
场景: "这件羊毛大衣能配什么裤子？"

Step 1: 图谱精确查询
  MATCH (p:Product {name: "羊毛大衣"})-[:COMPATIBLE_WITH]->(match:Product)
  WHERE match.owner_org_id IN $org_chain OR match.visibility IN ['global','brand']
  RETURN match.graph_node_id, match.name, ...

Step 2: 用 graph_node_id 作为 FK 去向量库补充语义内容
  Qdrant.search(
    filter: { graph_node_id: MatchAny(["prod_001", "prod_002", ...]) },
    // 不需要向量相似度搜索，直接按 FK 精确命中
  )

结果: 精确的搭配关系（图谱）+ 丰富的描述/卖点/话术（向量）
```

**模式 B: 向量优先 -> 图谱补充（模糊 -> 精确）**

```
场景: "帮我找适合商务场合的温暖外套"

Step 1: 向量语义检索
  Qdrant.search(
    query_vector: embed("适合商务场合的温暖外套"),
    filter: {
      source_type: "enterprise",
      should: [
        { visibility: "global" },
        { org_chain: MatchAny(current_org_chain) }
      ]
    },
    limit: 10
  )
  -> 命中若干向量条目，每个带 graph_node_id

Step 2: 用 graph_node_id 回到图谱获取结构化关系
  MATCH (p:Product) WHERE p.graph_node_id IN $hit_ids
  OPTIONAL MATCH (p)-[:COMPATIBLE_WITH]->(match:Product)
  OPTIONAL MATCH (p)-[:HAS_ATTRIBUTE]->(attr:Attribute)
  OPTIONAL MATCH (p)-[:AVAILABLE_AT {stock_quantity: $gt(0)}]->(store:Store)
  RETURN p, match, attr, store

结果: 语义匹配的产品（向量）+ 可搭配商品 + 属性 + 库存状态（图谱）
```

**模式 C: 双向交叉（Promotion 场景）**

```
场景: Promotion Pipeline 将个人记忆提案写入企业知识

Step 1: 写入图谱
  CREATE (p:UserPreference {
    graph_node_id: "upref_xxx",
    node_type: "UserPreference",
    tenant_id: $tenant_id,
    owner_org_id: $org_id,
    visibility: "store",
    version: 1, is_active: true,
    valid_from: datetime()
  })

Step 2: 同时写入向量（FK 关联）
  Qdrant.upsert(
    vector: embed("该门店用户群对复古风格表现出明显兴趣"),
    payload: {
      graph_node_id: "upref_xxx",     // [FK]
      source_type: "enterprise",       // 审批后成为企业资产
      content_type: "store_insight",
      org_id: ..., visibility: "store",
      provenance: { source: "promotion", proposal_id: "...", approved_by: "..." }
    }
  )
```

### 3.5 FK 联动一致性约束

> 所有 FK 联动的一致性约束（写入、删除、自愈）详见 Section 7.3。

### 3.6 多模态 FK 扩展

> **[v3.6 新增]** enterprise_media_objects (PG) 与 Knowledge Stores (Neo4j/Qdrant) 的 FK 联动。

```
enterprise_media_objects 与图谱的关联:
  enterprise_media_objects.graph_node_id -> Neo4j graph_node_id
  遵循 Section 3.1 FK 联动规则:
    写入图谱节点的媒体属性时，必须同步创建 enterprise_media_objects 记录 (PG)
    删除图谱节点时，必须级联删除关联的 enterprise_media_objects 记录
    enterprise_media_objects DDL 定义见 06-基础设施层.md Section 9

  Qdrant enterprise collection 的向量 payload 扩展:
    新增 media_refs 可选字段 (Expand 兼容变更，遵循 ADR-033):
    {
      "graph_node_id": "...",
      "source_type": "enterprise",
      "org_id": "...",
      "media_refs": [                    -- 新增可选字段
        {
          "media_id": "UUID",            -- 外部统一用 media_id (LAW)
          "media_type": "image",         -- image | audio | video | document
          "text_fallback": "..."         -- 纯文本回退
        }
      ]
    }
    向后兼容: media_refs 为可选字段，旧条目无此字段不影响检索

  异构存储一致性:
    PG/Neo4j/Qdrant 三库无法分布式事务
    PG 事务保证 media record + event_outbox 原子性
    Neo4j/Qdrant 写入通过 FK 协议 (Section 7.3) 保证最终一致性
    sync_status 标记 + Reconciliation Job 自愈

  可见性继承判定 (enterprise_media 查询):
    Step 1: PG RLS 双向放行 (子树 + 祖先链, 见 06 Section 9 DDL 注释)
    Step 2: 应用层按 visibility + org_chain 做继承过滤
            -> 复用 Resolver 已有 filter_by_visibility(items, org_chain, brand_id) 函数
    Step 3: ACL 细粒度判定 (可选, acl JSONB 字段)
    为何 visibility 判定不放 RLS:
      RLS 保证租户/组织链安全底线 (不可绕过)
      visibility + ACL 涉及 org_chain 上溯 + tier 匹配, SQL 表达复杂且性能差
      visibility 规则可能随业务演进, 应用层修改成本低
```

### 3.7 Experiment Engine 分流切入点（Knowledge 层）

```
实验维度（引用 06 Section 5.2）:
  - Knowledge 检索策略: Resolver Profile、FK 策略、检索参数变体
  - 模型选择: embedding 模型 / reranker 模型切换

分流接入方式:
  Context Assembler（01-Brain Section 4）在构建 KnowledgeBundle 时读取 experiment_context:
    experiment_context.dimensions.knowledge_strategy?: string

  切入点 -- KnowledgeBundle 组装:
    if experiment_context?.dimensions.knowledge_strategy:
      使用 variant 对应的检索参数（top_k、RRF 权重、reranker 配置等）
    else:
      使用默认检索参数

  切入点 -- 模型选择:
    if experiment_context?.dimensions.model_selection:
      使用 variant 指定的 embedding/reranker 模型
    else:
      使用 org_settings.model_access.default_model

  Trace 关联:
    retrieval_receipt.details 记录 experiment_id + variant + 实际检索参数
    通过 trace_id 关联实验指标与检索质量（召回率/精确率/延迟）
```

---

## 4. 实体类型注册机制

> **[v3.0 核心创新]** Skill 向 Knowledge Stores 注册新的实体类型，无需修改核心代码。

### 4.1 EntityTypeDefinition

```
EntityTypeDefinition（实体类型注册）:
+-- entity_type_id: String          如 "Product", "Persona", "FAQEntry"
+-- label: String                   Neo4j 节点标签
+-- registered_by: String           "core" | "skill:xxx"
+-- schema:                         属性 schema（JSON Schema）
|     required_properties: [...]
|     optional_properties: [...]
+-- relationships:                  该类型可以有的关系
|     [{ type: "COMPATIBLE_WITH", target_types: ["Product"], direction: "out" }, ...]
+-- vector_content_types:           该类型在向量库中的内容类型
|     [{ content_type: "product_description", embedding_field: "description" }, ...]
+-- visibility_rules:               可见性规则
|     default_visibility: "brand"
|     allowed_visibilities: ["global", "brand", "region", "store"]
+-- org_scope:                      组织范围
|     who_can_create: ["brand_hq", "regional_agent"]
|     who_can_read: ["full_chain"]
+-- status: active | deprecated
```

### 4.2 内核自带的实体类型

| 实体类型 | 用途 | 注册者 |
|---------|------|--------|
| Organization | 组织树节点 | core |
| OrgMember | 组织成员 | core |
| RoleAdaptationRule | 角色适配规则 | core |
| BrandTone | 品牌调性定义 | core |
| PlatformTone | 平台调性定义 | core |
| StoreInsight | 门店级洞察 | core |
| RegionInsight | 区域级洞察 | core |
| BrandKnowledge | 品牌级知识 | core |
| GlobalKnowledge | 全局知识 | core |
| EvolutionProposal | 进化提案（Promotion Pipeline 使用） | core |

### 4.3 Skill 注册的实体类型

| 实体类型 | 用途 | 注册者 |
|---------|------|--------|
| Persona | 内容人设配置 | skill:content_writer |
| ContentType | 内容类型配置 | skill:content_writer |
| ContentBlueprint | 内容蓝图/模板 | skill:content_writer |
| Campaign | 活动/Campaign | skill:content_writer |
| ContentMatrix | 内容矩阵编排 | skill:content_writer |
| PlatformAdapter | 平台适配配置 | skill:content_writer |
| Product | 商品 | skill:merchandising |
| Category | 商品分类 | skill:merchandising |
| Attribute | 商品属性 | skill:merchandising |
| Collection | 商品系列 | skill:merchandising |
| StylingRule | 搭配规则 | skill:merchandising |
| DisplayGuide | 陈列指南 | skill:merchandising |
| TrainingMaterial | 培训材料 | skill:merchandising |

### 4.4 拔掉 Skill 时的实体处理

```
拔掉 Skill 时:
  实体类型定义保留（数据不删），标记 registered_by = "skill:xxx(removed)"
  数据仍可被其他 Skill 或 Brain 通过 Context Assembler 访问
  "拔掉一只手，知识库里的资产不丢失"
```

---

## 5. Diyu Resolver（知识解析引擎）

Resolver 是 Knowledge Stores 的统一查询入口。Context Assembler（Brain 对话时直接调用）和 Brain（代 Skill 按 Profile 预取 KnowledgeBundle）通过 Resolver 访问企业知识。Skill 本身不直接调用 Resolver，而是通过 execute(knowledge=KnowledgeBundle) 被动接收预组装的知识包。

### 5.1 职责

```
Resolver 的职责:
+-- 接收查询请求（带 org_context）
+-- 根据 Profile 路由到不同的查询策略
+-- 执行 Neo4j 查询（自动注入 org_chain 过滤 + ACL 校验）
+-- 执行 Qdrant 检索（自动注入 org_chain payload 过滤, source_type=enterprise）
+-- 执行 FK 联动（图谱结果 -> 向量补充 或 向量结果 -> 图谱补充）
+-- 按 assembly_rules 组装输出
+-- 输出 KnowledgeBundle + ResolutionMetadata
```

### 5.2 Profile（解析档）

```
Profile:
+-- profile_id / name
+-- registered_by: String           "core" 或 "skill:xxx"
+-- graph_queries:                  Neo4j 查询模板列表
|     [{ template, params_mapping, fk_enrich: true/false }]
+-- vector_queries:                 Qdrant 检索配置列表
|     [{ collection, content_types_filter, fk_enrich: true/false, top_k }]
+-- fk_strategy:                    FK 联动策略
|     mode: "graph_first" | "vector_first" | "parallel" | "none"
|     enrich_depth: Integer         FK 补充深度（1 = 直接关联，2 = 二跳）
+-- assembly_rules: Object          组装规则
+-- org_scope: self_only | self_and_below | full_chain
+-- inheritance_policy: merge | parent_override | self_override
```

**内核 Profile（Brain 使用）:**

| Profile | 用途 | FK 策略 | 注册者 |
|---------|------|--------|--------|
| role_adaptation | 加载角色适配规则 | none（纯图谱） | core |
| brand_context | 加载品牌调性和基础知识 | graph_first | core |

**Skill Profile（Skill 注册时带入）:**

| Profile | 用途 | FK 策略 | 注册者 |
|---------|------|--------|--------|
| content_production | 内容生产所需的全部知识 | parallel | skill:content_writer |
| brand_compliance | 合规检查规则 | none（纯图谱） | skill:content_writer |
| merchandising_recommend | 搭配推荐知识 | graph_first | skill:merchandising |
| merchandising_training | 培训内容知识 | vector_first | skill:merchandising |

### 5.3 resolve() 流程

```
resolve(profile_id, request, org_context) -> KnowledgeBundle

  1. 从 Profile Registry 加载 Profile
  2. 根据 fk_strategy 决定执行顺序:

     graph_first:
       图谱查询 -> 收集 graph_node_ids -> 向量库按 FK 补充语义内容

     vector_first:
       向量语义检索 -> 收集 graph_node_ids -> 图谱按 FK 补充结构关系

     parallel:
       图谱查询 -- 并行 -- 向量检索
       -> 合并结果 -> FK 交叉补充

     none:
       仅图谱查询 或 仅向量检索（由 Profile 配置决定）

  3. 所有查询自动注入 org_chain 过滤 + ACL 校验
  4. 按 assembly_rules 组装
  5. 输出 KnowledgeBundle + ResolutionMetadata
```

### 5.4 KnowledgeBundle（输出）

```
KnowledgeBundle:
+-- entities: Dict[str, List[Entity]]    按实体类型分组的实体列表
+-- relationships: List[Relationship]    实体间关系
+-- semantic_contents: List[Content]     向量库中的语义内容（已通过 FK 关联到实体）
+-- media_contents: List[MediaRef]       [v3.6 新增, 可选] 关联的企业媒体资产（见下方 Schema 扩展）
+-- org_context: Object                  组织上下文元数据
+-- metadata: ResolutionMetadata

ResolutionMetadata:
+-- resolved_at, profile_id
+-- completeness_score: Float (0-100)
+-- org_chain_used: [UUID]
+-- graph_hits: Integer, vector_hits: Integer
+-- fk_enrichments: Integer              FK 联动补充了多少条
+-- warnings: [Object]
```

#### 5.4.1 KnowledgeBundle 语义契约 v1

> **[v3.3 新增]** KnowledgeBundle 是 KnowledgePort 的核心输出结构，是 Brain/Skill 消费知识的唯一契约边界。以下定义构成 schema v1，变更须遵守兼容规则（见 ADR-033）。

```
KnowledgeBundle Schema v1:

字段                 | 类型                        | 必填 | 空值语义                          | 说明
entities             | Dict[str, List[Entity]]     | YES  | 空 Dict {} = 无匹配实体           | key 为实体类型名
relationships        | List[Relationship]           | YES  | 空 List [] = 无关系数据            | 实体间关系
semantic_contents    | List[Content]                | YES  | 空 List [] = 无向量命中            | FK 关联后的语义内容
org_context          | Object                       | YES  | 不允许为空                         | 查询时的组织上下文快照
metadata             | ResolutionMetadata           | YES  | 不允许为空                         | 解析元数据（含 completeness_score）

ResolutionMetadata Schema v1:

字段                 | 类型       | 必填 | 空值语义
resolved_at          | DateTime   | YES  | 不允许为空
profile_id           | String     | YES  | 不允许为空
completeness_score   | Float      | YES  | 0.0 = 完全未命中
org_chain_used       | List[UUID] | YES  | 不允许为空（至少含当前 org）
graph_hits           | Integer    | YES  | 0 = 图谱无命中
vector_hits          | Integer    | YES  | 0 = 向量无命中
fk_enrichments       | Integer    | YES  | 0 = 无 FK 联动补充
warnings             | List[Object] | YES | 空 List [] = 无警告

v3.6 扩展 -- media_contents (Expand 兼容变更, 遵循 ADR-033):

字段                 | 类型                        | 必填 | 空值语义                          | 说明
media_contents       | List[MediaRef]              | NO   | 空 List [] 或缺失 = 无媒体资产    | [v3.6 新增] 关联的企业媒体

MediaRef Schema:
字段                 | 类型       | 必填 | 说明
media_id             | UUID       | YES  | 外部统一用 media_id (LAW, 禁止暴露 ObjectRef)
text_fallback        | String     | YES  | 纯文本回退 (降级/无多模态能力时使用)
associated_entity_id | String     | YES  | 关联的图谱实体 graph_node_id
content_type         | String     | YES  | "product_image" | "brand_guideline" | "training_video" | ...

向后兼容:
  media_contents 为可选字段，缺失时视为空列表
  现有消费端 (Brain/Skill) 不读取此字段则行为不变
  遵循 ADR-033: 新增可选字段 = 兼容变更

兼容变更（不破坏消费者）:
  + 新增可选字段（有默认值或可为空）
  + 在 warnings 中新增警告类型

破坏性变更（需 expand-contract 迁移）:
  - 删除现有字段
  - 重命名现有字段
  - 改变现有字段的类型或语义
  - 将可选字段改为必填
  - 新增必填字段（无默认值）
```

---

## 6. 知识可见性与继承

### 6.1 企业四级 scope

| 级别 | 含义 | 继承规则 | 举例 |
|------|------|---------|------|
| global | 所有组织可见 | 无需继承 | 平台规则、行业通识 |
| brand | 品牌总部定义 | 总部 -> 省代 -> 门店 | 品牌调性、产品卖点、搭配规则 |
| region | 省代补充 | 省代 -> 本区域门店 | 区域促销话术、本地化策略 |
| store | 仅本门店可见 | 不继承 | 门店特色活动、本地客户反馈 |

> **personal_projection 例外:** Qdrant 中存在 `personal_projection` 命名空间，用于存放从 Memory Core 投影过来的个人语义索引副本。这不是 Knowledge Stores 的 scope 层级，真值始终在 Memory Core（SSOT-A）。该投影仅供 Context Assembler 做跨 SSOT 语义检索时使用，Knowledge Stores 自身不读写此区域。

---

## 7. 写入管线（Knowledge 受控写入）

> **[v3.1 修正]** Knowledge Stores 有独立的写入管线，不再通过 Brain 记忆引擎统一写入。

### 7.1 Knowledge Write API（受控写入）

```
Admin/ERP/Skill/Batch -> Knowledge Write API -> (Neo4j/Qdrant)

必过:
+-- ACL 校验（角色 + 组织范围）
+-- 幂等键（防重复写入）
+-- 审计回执 knowledge_write_receipt（来源、幂等键、变更摘要、影响范围）
+-- （文档类）脱敏与安全扫描
+-- ERP/PIM 同步走变更集（ChangeSet）以便审计与回滚

FK 保证:
+-- 写入图谱节点时，如果有语义内容，必须同步写入向量（带 FK）
+-- 写入向量条目时，必须指定 graph_node_id（不允许孤立向量，enterprise 类型）
+-- 删除图谱节点时，必须级联删除关联的向量条目

v3.6 多模态扩展:
+-- 媒体文件安全扫描（与文档类脱敏并列，安全管线详见 05-Gateway层.md Section 8.3）
+-- enterprise_media_objects 记录创建（PG 事务内，含 event_outbox media_event）
+-- Neo4j/Qdrant 联动: 遵循 FK 协议最终一致性（sync_status + Reconciliation Job）
+-- FK: graph_node_id 必须指向已存在的 Neo4j 节点
+-- 异构存储一致性: PG 事务保证 media record + outbox 原子性;
    Neo4j/Qdrant 写入通过 Section 7.3 FK 协议保证最终一致性

v3.6 企业媒体删除扩展:
+-- 删除图谱节点时，必须级联删除关联的 enterprise_media_objects 记录
+-- 删除顺序 (LAW): PG 软删标记先行 -> Qdrant-first -> Neo4j -> Object Storage 物理删除最后
+-- 删除失败策略: 详见 06-基础设施层.md Section 9.1（SSOT）
+-- 容错: Qdrant 删除失败 -> Neo4j 节点标记 sync_status = "pending_vector_delete"
    Reconciliation Job 后续补删（复用 Section 7.3 自愈机制）
```

### 7.2 Promotion Pipeline（跨域提案写入）

```
Memory Core -> (candidate) -> sanitize/scan -> conflict/dedup -> approval -> Knowledge Stores

流程:
  1. Brain 记忆引擎检测到可提升的知识模式
  2. 生成 EvolutionProposal 实体
  3. 脱敏 + 安全扫描（去除个人敏感信息）
  3.5 敏感信息分类标签（v3.5 新增，I1 修复）:
     +-- 对提案内容进行敏感分类: 个人偏好 / 商业机密 / 公开信息
     +-- 标记为"商业机密"的条目: 禁止通过 Promotion，阻断流程
     +-- 标记为"个人偏好"的条目: 需额外脱敏确认后方可继续
     +-- 标记为"公开信息"的条目: 正常流转
  4. 冲突检测 + 去重
  5. 按目标可见性路由到审批:
     +-- store 级: 门店 admin 确认
     +-- region 级: 省代 admin 确认
     +-- brand 级: 总部 admin 确认
     +-- global 级: 平台 admin 确认
  6. 审批通过 -> Knowledge Write API -> 写入 Neo4j/Qdrant enterprise 区域
  7. 生成 promotion_receipt + knowledge_write_receipt

这不是"Memory scope 升级"，而是跨 SSOT 的提案入库。

错误处理:
+-- 脱敏失败: 阻断流程，提案标记 "sanitize_failed"，不允许带个人信息写入 Knowledge
+-- 审批超时 (默认 7 天): 提案标记 "expired"，通知提案者，不写入 Knowledge
+-- 审批拒绝: 记录拒绝原因至 evolution_proposals.details，通知提案者
+-- Knowledge Write 失败: 按 Section 7.3 FK 一致性保障机制处理
+-- 所有异常: 生成 promotion_receipt 记录失败原因，写入 audit_events
```

### 7.3 FK 一致性保障机制

> **[v3.2 新增]** Section 7.1 定义了 FK 的写入规则（"必须同步写入"），本节定义失败后的处理策略。见 ADR-024。

```
权威源: Neo4j 为写入起点（graph_node_id 在 Neo4j 生成），Qdrant 为从属补写。

1. 写入时: Write-Through + sync_status + idempotency_key
   +-- Knowledge Write API 先写 Neo4j（生成 graph_node_id）
   +-- 再写 Qdrant（携带 graph_node_id FK + idempotency_key）
   +-- Qdrant 写入时附带 version 字段（= Neo4j 节点 version），防并发/重试重复补写
   +-- Qdrant 写失败 -> 重试 3 次 (exponential backoff + jitter)
   +-- 仍失败 -> Neo4j 节点标记 sync_status = "pending_vector_sync"
   +-- 反向写入（向量优先场景如 Promotion Pipeline）:
       先写 Qdrant -> 再写 Neo4j -> 失败标记 sync_status = "pending_graph_sync"

2. 两库字典 (FK Registry):
   +-- 对账查询: 检测两库之间 graph_node_id 的映射状态
   +-- 正向: Neo4j 中有 graph_node_id 且 vector_content_types 非空，但 Qdrant 无对应条目
   +-- 反向: Qdrant 中有 graph_node_id 但 Neo4j 无对应节点
   +-- 用途: 运维对账、一致性审计、故障定位

3. 自愈 Reconciliation Job:
   +-- 定期执行
   +-- 检测 sync_status = "pending_*" 的节点 -> 补写目标库（携带 idempotency_key + version 去重）
   +-- 检测字典中的孤立条目 -> 自动修复或告警
   +-- 输出 reconciliation_report 至 audit_events

4. 删除一致性:
   +-- 删除图谱节点前，先查 Qdrant 获取所有 graph_node_id 匹配的条目
   +-- 批量删除 Qdrant 条目 -> 再删 Neo4j 节点
   +-- Qdrant 删除失败 -> Neo4j 节点标记 sync_status = "pending_vector_delete"
   +-- Reconciliation Job 后续清理
```

---

> **验证方式:** 1) FK 联动: 图谱写入后向量库可按 graph_node_id 命中; 2) Resolver: 按不同 Profile 返回符合预期的 KnowledgeBundle; 3) 实体注册: 新 Skill 注册的实体类型可被查询和写入; 4) 拔掉后: Brain 层所有测试仍通过（降级模式）; 5) FK 一致性: Qdrant 写失败后 Neo4j sync_status 正确标记，Reconciliation Job 补写成功后 sync_status 清除; 6) [v3.6] 多模态 FK: enterprise_media_objects 写入后 Qdrant payload 含 media_refs，删除图谱节点时 enterprise_media_objects 和 Qdrant 条目级联清理; 7) [v3.6] KnowledgeBundle media_contents: Resolver 输出含 media_contents 可选字段，缺失时消费端行为不变; 8) [v3.6] 企业媒体删除: 遵循删除顺序 LAW (PG 软删 -> Qdrant-first -> Neo4j -> 物理删除)，失败时 sync_status 正确标记。
