# Branch Protection 验收记录

> DIYU Agent | 追踪文件：每次变更 Branch Protection 设置后更新

---

## 配置要求

GitHub Settings > Branches > main > Branch protection rules:
- Require status checks to pass before merging
- Required check: **"Merge Readiness"** (aggregates 13 CI jobs)
- Require branches to be up to date before merging (strict mode)
- Enforce for administrators
- Block force pushes
- Block branch deletion

## 验收命令

```bash
# Classic Branch Protection
gh api repos/{owner}/{repo}/branches/main/protection \
  --jq '.required_status_checks.contexts'

# Repository Rules (newer)
gh api repos/{owner}/{repo}/rules
```

---

## 当前状态

仓库已转为 **public** (2026-02-19)，branch protection **已启用**。

### 服务端强制 (GitHub Branch Protection)

| 设置 | 值 |
|------|------|
| Required status checks | `Merge Readiness` (strict, up-to-date) |
| Enforce admins | true |
| Force push | blocked |
| Branch deletion | blocked |

### 补偿控制（叠加生效）

| 控制层 | 机制 | 覆盖范围 |
|--------|------|---------|
| 服务端 | GitHub Branch Protection (required checks) | PR 合并必须 Merge Readiness 通过 |
| CI | `.github/workflows/ci.yml` 含 13 个聚合 job | 每次 push/PR 自动执行 |
| 本地 | `scripts/pre-push-guard.sh` (pre-push hook, 6/6) | 推送前强制检查 (lint+format+test+layer+mypy+security) |
| 治理 | `scripts/verify_phase.py --phase N` | 阶段门禁硬检查 |
| 审计 | `make audit-e2e` + governance pipeline | 证据链完整性 |

## 验收记录

| 日期 | 操作人 | 操作内容 | 验收命令输出 |
|------|--------|---------|-------------|
| 2026-02-18 | Claude | 确认 private+Free 不支持 branch protection | `HTTP 403: Upgrade to GitHub Pro` |
| 2026-02-18 | Claude | 添加 pre-push hook 作为补偿控制 | `scripts/pre-push-guard.sh` |
| 2026-02-19 | Claude | 转为 public repo | `gh repo edit --visibility public` |
| 2026-02-19 | Claude | 启用 branch protection (required checks + enforce admins) | `required_checks: ["Merge Readiness"], strict: true, enforce_admins: true, force_push: blocked` |
| 2026-02-19 | Claude | pre-push hook 升级 4/4 -> 6/6 | `+mypy +security_scan --quick` |
