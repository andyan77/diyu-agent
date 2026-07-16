# M1 初始 dirty worktree 盘点与处置决定 v1

> 依据：P1/M1 §七（工作树保全）。盘点时点：M1 会话开始、任何写入动作之前。
> 逐文件明细（status / size / sha256 / path）见同目录 `WORKTREE_INVENTORY_INITIAL.v1.tsv`。
> 盘点方法：`git diff --name-only`（modified）+ `git ls-files --others --exclude-standard`（untracked），仓库根执行。

## 汇总

| 类别 | 数量 | 处置 |
|---|---|---|
| MODIFIED（tracked 已修改） | 1 | 保全提交（C0，逐字入库），随后按 v2.5 §五 迁移改造 |
| UNTRACKED（真实文件） | 73 | 全部位于 M1 写面内 → 保全提交（C0，逐字入库） |
| UNTRACKED_SPECIAL（设备节点） | 19 | 沙箱遮蔽工件（char device → /dev/null），非用户数据，不入库、不触碰 |
| gitignored（不出现在盘点） | 2 项 | `.env.deepseek`（凭据）与 `.runtime/`（花费账本）——不读取、不入库、不迁移 |

## 处置细则

1. **`checker/p7_master_check.py`（MODIFIED，+280 行）**：用户既有工作成果（8 个新检查节 + 尾部状态回显）。
   属 M1 写面。处置：C0 逐字保全提交 → C2 中按 v2.5 §五 12 项做状态感知化迁移（保全在前，改造在后，历史可查）。
2. **`p7_successor_longrun_001/.gitignore`、`EVAL_AUDIT_SPINE_PRODUCT_MAP.v1.1.md`、`eval_audit_spine_001/**`（59 文件）、
   `generator_v3_successor_001/v4_recovery/**`（13 文件）**：全部在 M1 写面内，为 v2.3 §一 登记的既有实现工件。
   处置：C0 逐字保全提交。凭据模式扫描零命中（`sk-`/`api_key`/`PRIVATE KEY`/`password` 全仓 untracked 扫描 exit=无匹配）。
3. **根目录 dotfiles（`.bash_profile` `.bashrc` `.gitconfig` `.gitmodules` `.mcp.json` `.profile`
   `.ripgreprc` `.zprofile` `.zshrc` 等 19 条）**：实测为 `crw-rw-rw- nobody/nogroup 1,3` 字符设备节点
   （沙箱对敏感宿主文件的遮蔽挂载），非仓库内容。处置：不 add、不读、不删；TSV 中标记
   `DEVICE_NODE_SANDBOX_MASKED`。
4. **`.claude/`（harness 运行时环境层：settings/hooks/workflows/launch.json 等）**：属发起人环境层
   （v2.4 §三 3.6：hooks 配置属发起人环境层动作），非 M1 交付物。处置：不 add、不改。
5. **`.idea` `.vscode`**：空目录/IDE 工件。处置：不触碰。

## 保全承诺

- 暂存一律使用显式路径清单；禁 `git add -A`；禁 reset/clean/checkout--/stash/rebase/force-push。
- 本盘点 TSV 的 sha256 为 origin 仲裁锚的组成部分（初始 dirty worktree 清单摘要）。
- C0 提交后任何对上述文件的改动均通过后续胶囊提交呈现，diff 可逐行审计。
