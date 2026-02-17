# Branch Protection 验收记录

> DIYU Agent | 追踪文件：每次变更 Branch Protection 设置后更新

---

## 配置要求

GitHub Settings > Branches > main > Branch protection rules（或 Repository Rules）:
- Require status checks to pass before merging
- 必需检查列表包含 **"L1: Security Scan"**

## 验收命令

```bash
# Classic Branch Protection
gh api repos/{owner}/{repo}/branches/main/protection \
  --jq '.required_status_checks.contexts'

# Repository Rules (newer)
gh api repos/{owner}/{repo}/rules
```

---

## 平台约束

仓库为 **private + GitHub Free plan**，branch protection / repository rulesets 不可用（HTTP 403）。

可行升级路径（二选一）：
1. 将仓库设为 public -- 免费启用 branch protection
2. 升级 GitHub Pro ($4/month) -- 私有仓库也可启用

### 补偿控制（当前生效）

| 控制层 | 机制 | 覆盖范围 |
|--------|------|---------|
| CI | `.github/workflows/ci.yml` 含 14 个必需 job | 每次 push/PR 自动执行 |
| 本地 | `scripts/pre-push-guard.sh` (pre-push hook) | 推送前强制检查 |
| 治理 | `scripts/verify_phase.py --phase N` | 阶段门禁 12 项硬检查 |
| 审计 | `make audit-e2e` + governance pipeline | 证据链完整性 |

## 验收记录

| 日期 | 操作人 | 操作内容 | 验收命令输出 |
|------|--------|---------|-------------|
| 2026-02-18 | Claude | 确认 private+Free 不支持 branch protection | `HTTP 403: Upgrade to GitHub Pro` |
| 2026-02-18 | Claude | 添加 pre-push hook 作为补偿控制 | `scripts/pre-push-guard.sh` |
| (待升级) | - | 升级 Pro 或 public 后启用 required checks | - |
