# 产品边界合同 v1（PRODUCT_BOUNDARY_CONTRACT）

> 真源：v2.4 §二/§四 + v2.5 §二/§四 + D0 章程八项 + P1 §十八。M1 只落合同与 schema，不创建产品仓。

## 1. 终态形态（冻结）

- 产品 A（评测与审计脊柱应用）与产品 B（V1.1 内容生成资格应用 + 240+60 基线资产集）**各自交付于独立产品仓 + 独立私有远程**；
- 两仓均以**无源仓 Git 历史的干净首提交**诞生；
- B 仓自带最小自含验证套件（E9 从原始事件重算所需），**禁止 import 产品 A**；B 须在完全没有 A 与源仓的 hermetic 环境通过验收；
- 产品运行输出**不得反向写入源仓**（单向纪律）；
- 客户数据不得进入任何 Git 仓（源仓与产品仓）。

## 2. 出口物（每次搬仓必备）

| 工件 | schema/模板 | 硬门 |
|---|---|---|
| 抽取清单 | `schema/cross_repo_lift_manifest.v1.schema.json` | 逐文件 sha256；新仓首提交复现全部摘要一致 |
| 行为等价证明 | `schema/release_equivalence_attestation.v1.schema.json` | 机械同一性与行为等价**双证**；签字绑定双摘要 |
| 泄漏扫描报告 | `tools/sealed_scan.py` 输出 | denylist 撞库零命中；git 全历史/pack/LFS/子模块/软链/归档/缓存/日志/提示词/构建产物/自动记忆 |
| clean-room 验收 | `clean_room_profile.{A,B}.v1.json` | 无源仓路径/宿主缓存/editable 包；离线可运行 |
| 清权回执 | `RIGHTS_CLEARANCE.template.v1.md` | 未闭合 = 交付出口不过 |
| 客户数据边界声明 | `customer_data_governance.template.v1.md` | 合成数据负向测试通过 |

## 3. 方向纪律（机械可测）

- **导出方向唯一**：`CORE_EXPORT_ALLOWLIST` → 产品仓；allowlist 之外零字节出仓；
- **禁运方向唯一**：`DOMAIN_DATA_DENYLIST` 所列永不出仓（`tools/lift_chain.py` denylist 前缀扫描）；
- **测试方向唯一**：源仓 → 产品仓（`SOURCE_TO_PRODUCT_TEST_PROTOCOL`）；
- **依赖方向**：B ↛ A；产品 ↛ 源仓路径（import/路径扫描零命中）。

## 4. 失效规则

搬仓中改动语义代码/阈值/依赖行为/模型编排 → `A_LIFT_READY`/`B_LIFT_READY` 失效，重新资格化（D0 §⑧）；E9 后任何代码/资产/配置/依赖改变 → 资格失效（B_LIFT_CHAIN_CONTRACT）。
