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

## 验收记录

| 日期 | 操作人 | 操作内容 | 验收命令输出 |
|------|--------|---------|-------------|
| (待配置) | - | 初始配置：添加 "L1: Security Scan" 为 required check | - |
