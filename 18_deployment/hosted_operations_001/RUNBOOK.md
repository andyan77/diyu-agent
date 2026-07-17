# 第8包运行手册

本包只管理笛语应用命名空间。Dify 1.15.0、PostgreSQL 14 及兼容检索服务须已存在；本包不会安装整套 Dify，也不会连接真实云端对象。

## 安全前提

- 数据库名和命名空间必须以 `diyu-pkg8-` 开头。
- 数据库连接只从 `DIYU_PKG8_DATABASE_URL` 读取。
- 登录密码只从 `DIYU_PKG8_PRINCIPAL_PASSWORD` 读取，不写进品牌文件或日志。
- 如使用密钥文件，文件权限必须为当前用户私有。
- 备份目录须位于仓库外，原始备份不得提交。备份不含明文密钥，但包含登录凭据校验值和运行状态，必须按受限敏感数据保管。
- 本包验证的是非生产应用范围隔离和关系库当前状态复核；数据库行级安全策略及真实服务器加固由第9包另行授权。

## 标准顺序

```bash
python3 hosted_operations.py --namespace "$NAMESPACE" preflight
python3 hosted_operations.py --namespace "$NAMESPACE" install
python3 hosted_operations.py --namespace "$NAMESPACE" initialize
python3 hosted_operations.py --namespace "$NAMESPACE" import --brand-file fixtures/second_brand_fixture.v1.yaml
python3 hosted_operations.py --namespace "$NAMESPACE" materialize-dify --output-directory "$EXTERNAL_MATERIALIZATION_DIR" --as-of 2026-07-16T00:00:00Z
python3 hosted_operations.py --namespace "$NAMESPACE" health
```

`install`、`initialize` 和相同品牌包的 `import` 可重复运行；相同输入不会增加重复对象。`update` 使用同一品牌文件合同，只在摘要变化时追加版本。

## 撤回与回滚

```bash
python3 hosted_operations.py --namespace "$NAMESPACE" revoke --tenant-id TENANT-ID --kind authorization --object-id AUTH-ID --reason-ref revoke://ticket
python3 hosted_operations.py --namespace "$NAMESPACE" rollback --tenant-id TENANT-ID --revision 1
```

撤回立即更新关系数据库权威状态。检索返回仍须经过当前状态复核；索引中的滞后副本不能放行。整包回滚追加一个新版本，不删除历史版本。

## 备份与恢复

```bash
python3 hosted_operations.py --namespace "$NAMESPACE" backup --output-directory "$EXTERNAL_BACKUP_DIR"
python3 hosted_operations.py --namespace "$NAMESPACE" restore --manifest "$EXTERNAL_BACKUP_DIR/backup_manifest.v1.json"
```

备份同时生成离线发布包。发布包只收纳当前应用的最小可运行文件闭包，包括运维实现、Dify 应用、薄桥接、品牌导入合同、运行依赖和检索资料重建输入；不包含整个仓库、密钥或真实客户资料。

恢复目标必须是另一个全新、空白且以 `diyu-pkg8-` 开头的 PostgreSQL 数据库。恢复会先验证发布对象清单、版本和逐文件摘要，数据库恢复后再用同一时间点重新物化 Dify 资料并比较摘要。对象缺失、损坏、版本不符或资料无法重建时均失败关闭。

品牌文件必须显式选择 `SIMULATION` 或 `AUTHORIZED_REAL`。真实品牌模式还须提供来源、有效授权、时效与撤回状态、操作者确认；导入成功仍不授予发布或生产就绪。仓库测试只使用无真实客户资料的安全夹具。

## 升级

```bash
python3 hosted_operations.py --namespace "$NAMESPACE" upgrade --target-version 2
python3 hosted_operations.py --namespace "$NAMESPACE" rollback-schema --target-version 1
```

第8包用一项品牌版本查询索引验证 `v1 -> v2 -> v1` 的真实结构升级与事务回滚。真实服务器安装、Dify 导入、数据库行级安全、域名、证书和流量切换属于第9包。
