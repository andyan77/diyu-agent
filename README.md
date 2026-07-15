# 笛语智能体

这是笛语智能体唯一业务主仓。当前主线是把已经验证过的表达能力，与可信身份、品牌资料、内容请求、编排和交付边界连接成一个可实施的产品。

## 当前已有

- 第一版表达基座：68 个组件、8 条规则、85 条适用关系、20 组甲乙结构路径，作为离线研究、回归和实验资产保留；
- 20 项内部内容产品及 8 类用户可理解的题材入口；
- 受保护的远程自动检查与普通合并流程；
- 轻表达公共合同：可信范围、模拟账号、事实双通道、服务端表达配置、唯一轻量内容计划、准备和校验接口语义。

普通内容请求不需要引用组件、关系或甲乙结构路径。服务端品牌表达配置、少量高层模式和示例只指导表达，不能授予事实、授权或企业范围；企业专属配置尚未接入时使用明确版本的中性默认配置。

第一版生成器尚未被判定合格，300 条质量基线尚未冻结。这里的“公共基础冻结”只允许后续执行包开始施工，不代表检索、Dify、运行服务、发布或生产已经就绪。

## 当前入口

- 当前产品状态：`project-infra/current_product_status.v1.yaml`
- 当前工作区清单：`project-infra/product_workspace_manifest.v1.yaml`
- 公共基础：`11_product_foundation/public_foundation_001/`
- 表达基座：`controlled_content_generator_v2_001/gate1_v1_1_001/p2_component_supply_and_generator_core_repair_001/`

旧的 `project-infra/current_workspace_status.yaml`、`workspace_manifest.yaml` 和 `canonical_source_digest_manifest.yaml` 是历史知识生产线证据，不再决定当前产品路线。

## 后续模块

公共基础进入远程 `master` 且必需检查通过后，才允许分别启动：

1. 轻表达普通接口和内容计划运行适配；
2. 品牌叙事资料整理与少量精确事实导入；
3. Dify 普通聊天和内容制作对话外壳。

三个模块只消费同一套公共合同，不得分别发明身份、事实或内容编排模型。

## 本地检查

```bash
python3 ci/checkers/check_product_foundation.py
python3 ci/checkers/check_product_foundation.py --selftest
```

当前仓库没有 HTTP 服务、数据库表、Dify 工作流、模型调用或自动部署。本任务也不保存任何模拟登录密码。
