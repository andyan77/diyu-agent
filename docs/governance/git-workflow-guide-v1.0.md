# Git 工作流指南 v1.0

> DIYU Agent 项目 | 2026-02-16 | Owner: Faye

---

## 0. 核心术语表

```
Repository (仓库)
  被 Git 追踪的项目文件夹。包含所有代码（生产代码 + 基础设施代码）。

Commit (提交)
  代码在某一时刻的快照。每次提交都有唯一 ID（如 dbcf125）。
  类比：游戏里的"存档点"。

Branch (分支)
  一条独立的开发线。类比：代码的"平行宇宙"。
  一个分支上的改动不会影响其他分支，直到合并。

main (主分支)
  树干分支。代表项目的正式稳定版本。
  所有分支从 main 出发，最终合并回 main。

Working Branch (工作分支)
  从 main 创建出来做开发的分支（如 feat/phase2-conversation）。
  命名规范：feat/*、fix/*、chore/*。

Local vs Remote (本地 vs 远程)
  Local  = 你的电脑（通过终端访问）
  Remote = GitHub（通过浏览器或 `gh` 命令访问）
  两者是独立副本，必须手动同步。

Push (推送)
  将本地提交发送到远程。推送后，GitHub 才能看到你的改动。

Pull Request / PR (合并请求)
  在 GitHub 上发起的请求："请审查我的分支并合并到 main。"
  CI 检查在 PR 上自动运行。PR = 代码进入 main 之前的质量关卡。

Merge (合并)
  将分支的提交并入 main。合并后，main 就包含了新代码。
  工作分支随后可以删除。

CI (持续集成)
  每次推送/PR 自动运行的检查：代码规范、类型检查、测试、安全扫描。
  所有检查必须通过（全绿）才能合并。
```

---

## 1. 分支策略

### 1.1 每阶段单分支（推荐）

每个 Phase 使用一个工作分支。不要将生产代码和基础设施代码拆分到不同分支，除非两者完全没有文件交叉。

```
main
  |-- feat/phase2-core        (Phase 2 全部代码)
  |-- feat/phase3-skills       (Phase 3 全部代码)
```

### 1.2 何时可以使用多分支

仅当两条开发线的修改文件完全不重叠时：

```
main
  |-- feat/phase2-backend     (只修改 src/、tests/、migrations/)
  |-- chore/phase2-ci-upgrade  (只修改 .github/workflows/、scripts/)
```

规则：如果分支 A 和分支 B 都修改了同一个文件，它们必须是同一个分支，或者其中一个必须先合并。

### 1.3 分支命名规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feat/` | 新功能、阶段实现 | `feat/phase2-conversation` |
| `fix/` | 缺陷修复 | `fix/jwt-token-expiry` |
| `chore/` | 工具链、CI、配置、纯文档 | `chore/ci-semgrep-config` |
| `refactor/` | 代码重构，不改变行为 | `refactor/brain-layer-ports` |
| `test/` | 仅测试变更 | `test/add-rls-isolation` |

---

## 2. 完整工作流程图

```
+------------------------------------------------------------------+
|  起点：代码编写完成                                                 |
|  某个模块/功能已完成，准备保存并提交。                                |
+------------------------------------------------------------------+
                            |
                            v
+==================================================================+
||  步骤 1：本地预检（强制）                                        ||
||                                                                 ||
||  运行以下全部 5 条命令，全部必须通过才能继续。                      ||
||                                                                 ||
||  $ uv run ruff check src/ tests/ scripts/                      ||
||  $ uv run ruff format --check src/ tests/ scripts/             ||
||  $ uv run mypy src/                                            ||
||  $ uv run pytest tests/unit/ -q                                ||
||  $ bash scripts/security_scan.sh --quick                       ||
||                                                                 ||
||  任何一条失败？ --> 修复后重新运行，禁止跳过。                      ||
+==================================================================+
                            |
                            | 全部 5 条通过
                            v
+------------------------------------------------------------------+
|  步骤 2：暂存文件                                                  |
|                                                                   |
|  $ git add <具体文件>                                              |
|    或                                                              |
|  $ git add -A  （暂存所有改动）                                     |
|                                                                   |
|  然后审查暂存内容：                                                 |
|  $ git status                                                     |
|  $ git diff --cached --stat                                       |
|                                                                   |
|  检查：不得包含 .env、密钥、凭证或临时文件。                          |
+------------------------------------------------------------------+
                            |
                            v
+------------------------------------------------------------------+
|  步骤 3：提交 (Commit)                                             |
|                                                                   |
|  $ git commit -m "feat(scope): 简洁描述"                           |
|                                                                   |
|  格式：<type>(<scope>): <description>                              |
|  类型：feat / fix / docs / test / refactor / chore                |
|                                                                   |
|  示例：                                                            |
|    feat(brain): implement MemoryCorePort adapter                  |
|    fix(gateway): add missing type annotations for mypy            |
|    chore(ci): add pnpm setup to guard-checks job                  |
+------------------------------------------------------------------+
                            |
                            v
+------------------------------------------------------------------+
|  步骤 4：推送到远程 (Push)                                          |
|                                                                   |
|  首次推送（新分支）：                                                |
|  $ git push -u origin <branch-name>                               |
|                                                                   |
|  后续推送：                                                         |
|  $ git push                                                       |
|                                                                   |
|  推送后，GitHub 上的 PR 会自动触发 CI 检查。                         |
+------------------------------------------------------------------+
                            |
                            v
+------------------------------------------------------------------+
|  步骤 5：创建 PR（仅首次推送时）                                     |
|                                                                   |
|  $ gh pr create --title "feat: ..." --body "## Summary ..."      |
|                                                                   |
|  目标分支：main                                                    |
|  一个分支 = 一个 PR，禁止为同一分支创建多个 PR。                      |
+------------------------------------------------------------------+
                            |
                            v
+==================================================================+
||  步骤 6：等待 CI 结果                                             ||
||                                                                  ||
||  $ gh pr checks <PR编号>                                         ||
||                                                                  ||
||  全绿？ --> 进入步骤 7                                            ||
||  有红？ --> 进入步骤 6a（CI 修复循环）                              ||
+==================================================================+
                            |
              +-------------+-------------+
              |                           |
              v                           v
+-------------------------+  +----------------------------+
| 步骤 6a：CI 修复循环     |  |  步骤 7：合并 PR (Merge)    |
|                          |  |                            |
| 1. 查看 CI 错误日志       |  |  在 GitHub 上点击            |
| 2. 本地修复               |  |  "Merge pull request"      |
| 3. 重新运行步骤 1（全部 5 |  |                            |
|    条命令）               |  |  或通过命令行：              |
| 4. 提交修复               |  |  $ gh pr merge <编号>      |
| 5. 推送                  |  |    --squash --delete-branch|
| 6. 回到步骤 6             |  |                            |
|                          |  |  合并后，main 分支就包含了  |
| 禁止未通过步骤 1 就推送！  |  |  你的全部代码。             |
+--------------------------+  +----------------------------+
                                          |
                                          v
                              +----------------------------+
                              |  步骤 8：同步本地 main       |
                              |                            |
                              |  $ git checkout main       |
                              |  $ git pull origin main    |
                              |                            |
                              |  此时本地 main = 远程 main  |
                              |  可以开始下一阶段的开发。    |
                              +----------------------------+
                                          |
                                          v
                              +----------------------------+
                              |  步骤 9：创建新分支          |
                              |  （下一阶段/功能）           |
                              |                            |
                              |  $ git checkout -b         |
                              |    feat/phase2-core        |
                              |                            |
                              |  开始编码...                |
                              |  完成后回到步骤 1。          |
                              +----------------------------+
```

---

## 3. 预检命令速查卡

```bash
# 直接复制粘贴执行。全部必须返回退出码 0。

uv run ruff check src/ tests/ scripts/ \
  && uv run ruff format --check src/ tests/ scripts/ \
  && uv run mypy src/ \
  && uv run pytest tests/unit/ -q \
  && bash scripts/security_scan.sh --quick

# 全部通过时输出：
#   All checks passed!
#   XX files already formatted
#   Success: no issues found in NN source files
#   NNN passed in X.XXs
#   {"mode":"quick","reason":"clean",...}
```

---

## 4. CI 修复循环（详细步骤）

推送后 CI 失败时，严格按以下顺序执行：

```
1. 定位    $ gh pr checks <编号>            # 哪个 job 失败了？
2. 读日志  $ gh run view <run-id> --log     # 具体报什么错？
3. 复现    在本地运行相同的命令               # 确认本地也能重现
4. 修复    修改代码
5. 验证    运行全部 5 条预检命令              # 不是只跑失败的那一条
6. 提交    $ git add <files> && git commit -m "fix(...): ..."
7. 推送    $ git push
8. 等待    $ gh pr checks <编号>            # 现在全绿了吗？
```

核心规则：**第 5 步必须运行全部 5 条检查，而不是只跑失败的那一条。** 修一个问题经常会引入另一个问题。

---

## 5. 生产代码 vs 基础设施代码

两者共存于同一个分支、同一个仓库。分离发生在部署环节，而不是 Git 层面。

```
部署到生产服务器的：                    仅保留在仓库中的：
  src/                                   .github/workflows/
  frontend/（构建产物）                   scripts/
  migrations/                            docs/
  pyproject.toml                         delivery/
  Dockerfile                             .claude/
                                         Makefile
                                         tests/
```

Dockerfile 控制哪些文件进入生产镜像。基础设施代码永远不会离开仓库。

---

## 6. 反模式（禁止操作）

| 反模式 | 为什么会失败 | 正确做法 |
|--------|-------------|---------|
| 把生产/基础设施拆到有文件交叉的不同分支 | 合并冲突、PR 重叠嵌套 | 每阶段一个分支 |
| 未运行预检就推送 | CI 失败，需要修复循环，浪费时间 | 始终先运行 5 条预检命令 |
| 从嵌套分支创建多个 PR | PR #2 包含于 PR #3 包含于 PR #5，混乱 | 一个分支 = 一个 PR |
| 将分支 A 合并到分支 B（非 main） | 历史纠缠，无法再拆分 | 只允许将 main 合并到你的分支（用于追赶进度） |
| 强制推送 (`git push --force`) | 销毁远程历史，破坏 CI | 禁止对共享分支强制推送 |
| 直接提交到 main | 绕过 CI 和审查 | 始终使用分支 + PR |

---

## 7. 常用命令参考

### 日常操作

```bash
# 查看当前分支和状态
git status
git branch

# 从 main 创建新分支
git checkout main && git pull origin main
git checkout -b feat/phase2-core

# 暂存、提交、推送
git add <files>
git commit -m "feat(scope): description"
git push -u origin feat/phase2-core   # 首次
git push                               # 后续

# 查看 PR 的 CI 状态
gh pr checks 5
gh pr view 5 --web   # 在浏览器中打开
```

### 同步 main（当 main 有了新变更时）

```bash
# 在你的工作分支上：
git fetch origin
git merge origin/main
# 如有冲突则解决，然后：
git push
```

### PR 合并后的清理

```bash
git checkout main
git pull origin main
git branch -d feat/phase2-core   # 删除本地工作分支
```

---

## 8. AI 交互标准指令

与 AI 协作执行 Git 操作时，使用以下标准指令：

| 指令 | 含义 |
|------|------|
| "运行预检" | 执行第 3 节的 5 条命令 |
| "提交这个改动" | 暂存 + 使用规范格式提交 |
| "推送到远程" | git push 到当前分支 |
| "检查 CI 状态" | 执行 gh pr checks 查看 PR 检查结果 |
| "修复 CI 并重新推送" | 执行第 4 节的 CI 修复循环 |
| "合并 PR" | 执行 gh pr merge --squash --delete-branch |
| "为 Phase N 创建新分支" | 切换到 main，拉取最新，创建新分支 |
| "本阶段使用单分支" | 禁止拆分为多个分支 |

---

## 9. Branch Protection 验收

合并阻断以 CI required check 为准，Phase Gate 为本地验证补充。

### 9.1 配置要求

GitHub Settings > Branches > main > Branch protection rules（或 Repository Rules）:
- Require status checks to pass before merging
- 必需检查列表中包含 **"L1: Security Scan"**

### 9.2 验收命令

```bash
# Classic Branch Protection
gh api repos/{owner}/{repo}/branches/main/protection \
  --jq '.required_status_checks.contexts'

# Repository Rules (newer)
gh api repos/{owner}/{repo}/rules

# 预期输出包含: "L1: Security Scan"
```

### 9.3 验收记录

首次配置或变更后，更新 `docs/governance/branch-protection-verification.md`：
- 配置日期
- 操作人
- 验收命令输出

---

## 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-02-16 | 基于 Phase 0-1 经验教训创建初始版本 |
| 1.1 | 2026-02-16 | 预检增加安全扫描(第5条)；新增 S9 Branch Protection 验收 |
