# 多模态层任务卡 (Phase 3 Multimodal M1)

> 来源: Phase 3 路线图 v1.3.3 Stage 3G
> 层级: Cross-layer (Tool / Gateway / Brain / Observability)
> Tier: A (Phase 3 + 跨层依赖)

---

### TASK-MM1-1: Personal Media Upload API

| 字段 | 内容 |
|------|------|
| **目标** | 个人媒体文件上传 API: 支持图片/音频上传到对象存储，返回 media_id |
| **范围 (In Scope)** | `src/gateway/api/media.py`, `tests/unit/gateway/test_media_upload.py` |
| **范围外 (Out of Scope)** | 媒体处理管线 / Brain 调度逻辑 / 前端上传组件 |
| **依赖** | ObjectStoragePort (I3-3) |
| **兼容策略** | 新增 API endpoint |
| **风险** | 性能: 大文件上传超时 (presigned URL 过期时间需 >= 15min); 安全: 上传文件类型白名单校验; 兼容: 新增 endpoint 不影响现有 API; 运维: MinIO 存储容量监控 |
| **决策记录** | 使用 presigned URL 直传模式 (避免 Gateway 中转大文件); 参考 ObjectStoragePort 5 方法契约 |
| **验收命令** | `pytest tests/unit/gateway/test_media_upload.py -v` (上传返回 media_id + presigned URL) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 单测通过 + API 契约文档 |

> 矩阵条目: MM1-1 | V-x: XM1-1 | M-Track: MM1-1

---

### TASK-MM1-2: WS Payload Media Extension

| 字段 | 内容 |
|------|------|
| **目标** | WebSocket 消息 payload 支持 media 附件字段 (image_url / audio_url) |
| **范围 (In Scope)** | `src/gateway/ws/handler.py`, `tests/unit/gateway/test_ws_media.py` |
| **范围外 (Out of Scope)** | 前端 WebSocket 客户端 / 媒体存储实现 / Brain 处理逻辑 |
| **依赖** | WebSocket handler (G2-2) |
| **兼容策略** | 向后兼容: 新增可选字段，不影响现有文本消息 |
| **风险** | 兼容: 新增可选字段不破坏现有 WS 消息解析; 性能: media URL 字段增加消息体大小; 安全: 防止 media_url 字段 SSRF 注入; 运维: WS 连接监控无变更 |
| **决策记录** | media 字段为可选 (Optional[str])，空值表示纯文本消息; 复用现有 WS handler 扩展而非新建 endpoint |
| **验收命令** | `pytest tests/unit/gateway/test_ws_media.py -v` (含 media 字段的 WS 消息正常解析) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 单测通过 |

> 矩阵条目: MM1-2 | V-x: X2-2 | M-Track: MM1-2

---

### TASK-MM1-3: ImageAnalyze + AudioTranscribe Integration

| 字段 | 内容 |
|------|------|
| **目标** | 集成 ImageAnalyze 和 AudioTranscribe Tool 到媒体上传流程，自动分析上传内容 |
| **范围 (In Scope)** | `src/tool/implementations/image_analyze.py`, `src/tool/implementations/audio_transcribe.py`, `tests/integration/test_media_analysis.py` |
| **范围外 (Out of Scope)** | 模型选择逻辑 / 安全扫描管线 / 前端渲染 |
| **依赖** | ImageAnalyze Tool (T3-2), AudioTranscribe Tool (T3-3) |
| **兼容策略** | 新增集成管线 |
| **风险** | 性能: 多模态分析延迟 > 2s 需异步处理; 安全: 分析结果可能含敏感内容需过滤; 兼容: 集成管线不影响现有 Tool 调用链; 运维: 外部 API 调用监控 + 降级策略 |
| **决策记录** | 采用异步分析模式，上传即返回 media_id，分析结果通过回调通知; Tool 调用通过 ToolRegistry 统一管理 |
| **验收命令** | `pytest tests/integration/test_media_analysis.py -v` (图片返回描述 + 音频返回转录文本) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 集成测试通过 |

> 矩阵条目: MM1-3 | V-x: XM1-1 | M-Track: MM1-3

---

### TASK-MM1-4: Brain Multimodal Model Selection

| 字段 | 内容 |
|------|------|
| **目标** | Brain 层根据输入类型 (文本/图片/音频) 自动选择合适的多模态模型 |
| **范围 (In Scope)** | `src/brain/model/selector.py`, `tests/unit/brain/test_model_selector.py` |
| **范围外 (Out of Scope)** | 模型推理实现 / Tool 调用逻辑 / 计费管线 |
| **依赖** | Brain model router (B2-1), Tool registry (T2-2) |
| **兼容策略** | 向后兼容: 纯文本输入使用默认模型，多模态输入使用扩展模型 |
| **风险** | 性能: 模型切换增加路由判断延迟 (目标 < 10ms); 安全: 模型选择不暴露内部模型列表; 兼容: 纯文本输入走默认模型路径无变更; 运维: 模型可用性监控 + 降级到文本模型 |
| **决策记录** | 基于输入 content_type 字段路由，支持 text/image/audio 三类; 降级策略: 多模态模型不可用时回退到纯文本模型 |
| **验收命令** | `pytest tests/unit/brain/test_model_selector.py -v` (图片输入 -> vision model; 音频输入 -> audio model) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 单测通过 |

> 矩阵条目: MM1-4 | V-x: X2-1 | M-Track: MM1-4

---

### TASK-MM1-5: Security Status 3-Layer Intercept

| 字段 | 内容 |
|------|------|
| **目标** | 媒体内容经过 3 层安全拦截: 上传时扫描 + 处理时校验 + 展示时过滤 |
| **范围 (In Scope)** | `src/gateway/security/media_check.py`, `tests/unit/gateway/test_media_security.py` |
| **范围外 (Out of Scope)** | 内容审核人工队列 / 法务合规策略 / 第三方安全API集成 |
| **依赖** | Content security pipeline (OS3-1) |
| **兼容策略** | 复用 SecurityStatus 6-state 模型 |
| **风险** | 安全: 安全扫描漏网率 < 0.1% 需持续验证; 性能: 3 层拦截增加处理延迟 (目标 p95 < 500ms); 兼容: 复用 SecurityStatus 6-state 不引入新状态; 运维: 安全拦截率监控 + 告警 |
| **决策记录** | 复用 ContentSecurityChecker 的 SecurityStatus 6-state 模型; 3 层拦截: upload-time scan + process-time verify + display-time filter |
| **验收命令** | `pytest tests/unit/gateway/test_media_security.py -v` (恶意媒体被 BLOCKED; security_status 正确流转) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 单测通过 + 安全扫描报告 |

> 矩阵条目: MM1-5 | V-x: XM1-2 | M-Track: MM1-5

---

### TASK-MM1-6: Personal Media Delete Tombstone

| 字段 | 内容 |
|------|------|
| **目标** | 媒体删除使用 tombstone 标记 (软删除)，保留审计追踪，30 天后物理清理 |
| **范围 (In Scope)** | `src/gateway/api/media.py`, `tests/unit/gateway/test_media_delete.py` |
| **范围外 (Out of Scope)** | 物理清理定时任务 / 存储层清理逻辑 / 前端删除确认弹窗 |
| **依赖** | Memory lifecycle (MC4-1) |
| **兼容策略** | 新增软删除字段，不影响现有媒体查询 |
| **风险** | 安全: 软删除数据 30 天内仍可恢复需审计追踪; 兼容: 删除 API 返回 410 Gone 而非 404 (可能影响客户端); 性能: tombstone 标记不影响查询性能 (需索引 is_deleted 字段); 运维: 清理定时任务需独立监控 |
| **决策记录** | 采用 tombstone 软删除模式 (is_deleted + deleted_at 双字段); 30 天物理清理由独立 cron job 负责，不在本卡范围内 |
| **验收命令** | `pytest tests/unit/gateway/test_media_delete.py -v` (删除后 GET 返回 410 Gone; 审计事件已记录) |
| **回滚方案** | `git revert <commit>` |
| **证据** | 单测通过 |

> 矩阵条目: MM1-6 | V-x: X4-4 | M-Track: MM1-6
