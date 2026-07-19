# 20 项内容产品远程质量资格测试

本包在首次正式任务前进入合法终态 `STOPPED_EXTERNAL_OR_BUDGET_BOUNDARY`。远程桥接账本已使用的模型调用上界为 208，运行配置累计上限为 209，只余 1 次；冻结批次需要 240 次上界，无法安全完成首项普通内容任务。任务权限不包含修改云端运行配置，因此正式任务、模型调用和新增费用均为 0，也没有复用旧第 10 包输出或生成虚假审查分数。

已在任何正式输出前冻结 20 个内容产品各 5 个场景共 100 项任务，以及每项产品 1 份公开市场参考。任务和参考摘要分别为 `b88d59cb368a8f29c26fc8886b4995478d00fd833b806f171c4ed7e5a1772185`、`6df51b6e3ee24bfa0eba25ceb975cc2df3681ede7ed2473abeaf178cd5102d94`。六类现有成品均有覆盖，“门店线下物料”仍为暂未开放。

`qualification_runner.py` 只接受 `https://dify.diyuai.cc/apps` 网页链，预算检查先于 URL、cookie、凭据和登录。恢复后每次进程最多完成 1 项任务，返回码 4 表示必须先从远端实际账本刷新调用数、费用、完成数和事件序号；只有第 100 项完成后才登出并清除五组外部 cookie。cookie 目录必须显式指定在仓库外，运行证据只保存其摘要。

恢复执行前，既有授权的第 7 包部署/配置动作须把累计上限提高到至少 508，并在任何模型调用前复核账本仍为 204 行/208 次上界、运行代码摘要、现网模型摘要和 HTTPS 健康状态。初始费用按历史 P95 规划为 4.489824 元；每完成一项都必须以远端实际费用刷新边界，并在可能超过 5 元前停止。

本地复核：

```bash
python3 freeze_inputs.py --check
python3 qualification_runner.py selftest
python3 check_remote_quality_qualification.py
python3 check_remote_quality_qualification.py --selftest
```

当前 `evidence/run_boundary_snapshot.v1.json` 会让正式模式以返回码 3 在首次网络访问前拒绝运行，这是本终态的预期行为。`python -O` 下检查器必须以返回码 2 拒绝运行。
