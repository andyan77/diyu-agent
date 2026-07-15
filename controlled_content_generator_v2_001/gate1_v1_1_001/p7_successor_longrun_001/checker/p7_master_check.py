#!/usr/bin/env python3
"""GATE1_V11_SUCCESSOR_LONGRUN_001 唯一任务内总检查入口。

按源指令 §8：本任务只建这一个总检查入口及其自测，不为每个执行包新造平行检查器。
各检查节（section）随执行包推进逐步注册；每节返回 (passed, details)。

用法:
    python3 p7_master_check.py                 # 跑全部已注册节
    python3 p7_master_check.py --section NAME  # 只跑指定节
    python3 p7_master_check.py --list          # 列出节

退出码: 全部通过=0；任一失败=1。输出为确定性文本（重复运行零差异）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

# 仓库根 = 本文件向上 4 层 (p7/checker/ -> p7 -> gate1 -> ccg_v2 -> root)
DEFAULT_ROOT = Path(__file__).resolve().parents[4]

GATE1 = "controlled_content_generator_v2_001/gate1_v1_1_001"
P7 = f"{GATE1}/p7_successor_longrun_001"
G3 = "controlled_content_generator_v2_001/generator_v3_successor_001"

ALLOWED_WRITE_PREFIXES = (P7 + "/", G3 + "/")

BASELINE_COMMIT = "b4c40beb509d81db30b497abf38af1da6dc797da"

# 执行包1各正式轮证据的冻结提交（历史轮字节完整性锚点；新轮证据提交后在此登记）。
# 轮次语义：模块/指令随轮演进是修复协议的合法部分；历史轮的复现性由其冻结提交
# 保证（在该提交处代码+证据同锚），检查器对历史轮做字节完整性、对最新轮做对盘校验。
PKG1_ROUND_FREEZE_COMMITS = {1: "c2e5b91a6da72fdf74a8b90edd8e494eaf9b31fc"}

# 核心口径（源指令 §1，不得改变）
CORE_CALIBER = {"total": 300, "positive": 240, "abnormal": 60,
                "reference_stock": 120, "historical_component_stock": 86}

# 任务级受保护文件基线（除 frozen_inputs 18 锚点与 p5_p6 全树清单外的追加监护）
EXTRA_PROTECTED = {
    f"{GATE1}/p2_component_supply_and_generator_core_repair_001/component/historical_86_successor_dispositions.v0.1.jsonl":
        ("77570bcb2840839c8387e8fafa9ff80707c2f9892016c0fa6c652263ec989af3", 86),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_yaml_pairs(text: str) -> list[tuple[str, str]]:
    """从 frozen_inputs.v1.1.yaml 提取 (path, sha256) 对（无第三方依赖的窄解析）。"""
    import re
    return re.findall(r"path: (\S+)\n\s+sha256: ([0-9a-f]{64})", text)


# ---------------------------------------------------------------- sections

def check_freeze_integrity(root: Path) -> tuple[bool, list[str]]:
    """冻结输入摘要和受保护文件未漂移；120/86 记录数不变。"""
    details: list[str] = []
    ok = True
    fi = root / P7 / "freeze" / "frozen_inputs.v1.1.yaml"
    if not fi.is_file():
        return False, ["frozen_inputs.v1.1.yaml missing"]
    pairs = _read_yaml_pairs(fi.read_text(encoding="utf-8"))
    anchors = [(p, s) for p, s in pairs if "p7_successor_longrun_001" not in p]
    manifest = [(p, s) for p, s in pairs if p.endswith("p5_p6_full_tree_manifest.v1.1.tsv")]
    if len(anchors) != 18:
        ok = False
        details.append(f"expected 18 anchors in frozen_inputs, got {len(anchors)}")
    for rel, expected in anchors:
        f = root / rel
        if not f.is_file():
            ok = False
            details.append(f"MISSING anchor {rel}")
            continue
        actual = sha256_file(f)
        if actual != expected:
            ok = False
            details.append(f"DRIFT anchor {rel}: {actual[:12]} != {expected[:12]}")
    # p5_p6 全树逐文件比对
    for rel, expected in manifest:
        mf = root / rel
        if not mf.is_file():
            ok = False
            details.append(f"MISSING manifest {rel}")
            continue
        if sha256_file(mf) != expected:
            ok = False
            details.append("DRIFT manifest file itself changed")
        base = root / GATE1
        for line in mf.read_text(encoding="utf-8").splitlines():
            digest, size, path = line.split("\t")
            f = base / path
            if not f.is_file():
                ok = False
                details.append(f"MISSING p5_p6 file {path}")
            elif sha256_file(f) != digest:
                ok = False
                details.append(f"DRIFT p5_p6 file {path}")
    # 追加监护（86 历史候选）
    for rel, (expected, expected_lines) in EXTRA_PROTECTED.items():
        f = root / rel
        if not f.is_file():
            ok = False
            details.append(f"MISSING protected {rel}")
            continue
        if sha256_file(f) != expected:
            ok = False
            details.append(f"DRIFT protected {rel}")
        n = sum(1 for _ in open(f, encoding="utf-8"))
        if n != expected_lines:
            ok = False
            details.append(f"protected {rel} line count {n} != {expected_lines}")
    # 120 记录数（文件本身已在 18 锚点内比对过摘要；此处再验记录数口径）
    ref120 = root / GATE1 / ("p1b_signed_review_closeout_and_baseline_freeze_001"
                             "/content/reference_120_final_dispositions.v0.1.jsonl")
    if ref120.is_file():
        n = sum(1 for _ in open(ref120, encoding="utf-8"))
        if n != CORE_CALIBER["reference_stock"]:
            ok = False
            details.append(f"reference_120 line count {n} != 120")
    details.append(f"anchors_checked={len(anchors)} manifest_files_checked="
                   f"{sum(1 for rel, _ in manifest for _ in (root / rel).read_text(encoding='utf-8').splitlines()) if manifest else 0}")
    return ok, details


def check_write_surface(root: Path) -> tuple[bool, list[str]]:
    """任务分支相对基线的全部改动都落在允许写入面内。"""
    r = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", f"{BASELINE_COMMIT}..HEAD"],
        capture_output=True, text=True, check=True)
    changed = [l for l in r.stdout.splitlines() if l.strip()]
    offenders = [p for p in changed if not p.startswith(ALLOWED_WRITE_PREFIXES)]
    details = [f"files_changed_since_baseline={len(changed)}"]
    if offenders:
        details += [f"OUT_OF_SURFACE {p}" for p in offenders]
    # 未提交改动同样必须在面内
    r2 = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                        capture_output=True, text=True, check=True)
    dirty = [l[3:].strip() for l in r2.stdout.splitlines() if l.strip()]
    dirty_off = [p for p in dirty
                 if not (p.startswith(ALLOWED_WRITE_PREFIXES)
                         or (p.endswith("/") and p.rstrip("/").startswith(ALLOWED_WRITE_PREFIXES[0].rstrip("/"))
                         ) or any(p.rstrip("/") + "/" == a or p.startswith(a) for a in ALLOWED_WRITE_PREFIXES))]
    if dirty_off:
        details += [f"DIRTY_OUT_OF_SURFACE {p}" for p in dirty_off]
    return not offenders and not dirty_off, details


def check_external_workspaces(root: Path) -> tuple[bool, list[str]]:
    """三个外部工作区没有被本任务写入（外部并行变化如实分类，不算失败）。

    判定逻辑：本任务的全部写入都经由本工作区 git 历史与工作树；
    外部工作区只做只读观察并记录当前状态供交付对照。
    """
    details: list[str] = []
    ok = True
    externals = {
        "original_main": "/home/diyu/笛语领域通用数据库",
        "quality_evidence": "/home/diyu/worktrees/gate1-v1-1-300-quality-baseline",
        "public_foundation": "/home/diyu/worktrees/diyu-public-foundation-001",
    }
    for name, path in externals.items():
        p = Path(path)
        if not p.is_dir():
            details.append(f"{name}: NOT_PRESENT")
            continue
        r = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                           capture_output=True, text=True)
        head = r.stdout.strip()[:12] if r.returncode == 0 else "ERR"
        r2 = subprocess.run(["git", "-C", path, "status", "--porcelain"],
                            capture_output=True, text=True)
        dirty_all = [l for l in r2.stdout.splitlines() if l.strip()]
        # 本任务写入面的路径若出现在外部工作区改动中 → 越界证据
        breach = [l for l in dirty_all
                  if l[3:].startswith(ALLOWED_WRITE_PREFIXES)
                  and name != "original_main"]  # 原主工作区的 P7 v1.0 草案是任务前既有的用户文件
        if name == "original_main":
            # 原主工作区允许存在任务前既有的未跟踪 P7 草案；只有"跟踪文件被改"才算破口
            tracked = subprocess.run(["git", "-C", path, "diff", "--name-only", "HEAD"],
                                     capture_output=True, text=True)
            breach = [l for l in tracked.stdout.splitlines() if l.strip()]
        if breach:
            ok = False
            details.append(f"{name}: WRITE_BREACH {breach[:5]}")
        details.append(f"{name}: head={head} external_parallel_changes={len(dirty_all)}")
    return ok, details


def check_core_caliber(root: Path) -> tuple[bool, list[str]]:
    """300、120、86 口径未被改变（合同文本仍声明同一口径）。"""
    details: list[str] = []
    contract = root / P7 / "contract" / "longrun_execution_contract.v1.1.md"
    if not contract.is_file():
        return False, ["contract v1.1 missing"]
    text = contract.read_text(encoding="utf-8")
    ok = ("300: 240条批准正向内容 + 60条异常处置案例" in text
          and "120: 已冻结历史参考内容库存" in text
          and "86: 历史组件候选库存" in text)
    if not ok:
        details.append("core caliber declaration drifted in contract v1.1")
    details.append("caliber=300/120/86 declared_intact=" + str(ok).lower())
    return ok, details


# ---------------------------------------------------------------- pure helpers
# （供节与反向自测共用；反向自测用合成输入证明检查会失败）

def surface_offenders(paths: list[str]) -> list[str]:
    return [p for p in paths if not p.startswith(ALLOWED_WRITE_PREFIXES)]


def blind_leak_offenders(texts: list[str]) -> list[str]:
    import re
    leak_re = re.compile(
        r"\bCP(?:0[1-9]|1\d|20)\b|G1V11|G3-POS|G3-CUR|甲级|乙级|"
        r"岗位任务VLOG|门店时段微纪录|专业判断切片|用户问题诊断室")
    return sorted({m.group(0) for t in texts for m in [leak_re.search(t)] if m})


def role_collision_offenders(authors: set[str], reviewers: set[str]) -> list[str]:
    return sorted(authors & reviewers)


def denominator_ok(request_count: int, metrics_output_count: int,
                   retained_failed_count: int, acceptable: int) -> bool:
    return (metrics_output_count == request_count
            and retained_failed_count == request_count - acceptable)


def route_gold_ok(root: Path) -> bool:
    gold = root / GATE1 / ("p1b_signed_review_closeout_and_baseline_freeze_001"
                           "/route/route_60_gold_answers.v0.1.jsonl")
    return (gold.is_file() and sha256_file(gold)
            == "f87d984d1780423e7ace0d78c54ba40e97ab5b48c39950f691c7ffca6652e054")


# ---------------------------------------------------------------- pkg sections

def check_g3_selftest(root: Path) -> tuple[bool, list[str]]:
    """G3 单元与反向测试（26 检查含 12 篡改案例）必须全绿。"""
    r = subprocess.run(
        ["python3", str(root / "controlled_content_generator_v2_001"
                        "/generator_v3_successor_001/tests/test_g3.py")],
        capture_output=True, text=True)
    ok = r.returncode == 0 and "ALL" in r.stdout and "PASSED" in r.stdout
    tail = [l for l in r.stdout.splitlines() if l.startswith("ALL")]
    return ok, tail or [r.stdout[-200:], r.stderr[-200:]]


def _pkg1_rounds(root: Path) -> list[tuple[int, Path]]:
    """已物化冻结清单的正式轮列表 [(轮次, 轮目录)]，升序。round1=pkg1 根。"""
    pkg1 = root / P7 / "pkg1_open_regression"
    rounds = []
    if (pkg1 / "inputs/input_freeze.v1.yaml").is_file():
        rounds.append((1, pkg1))
    for d in sorted(pkg1.glob("round[0-9]*")):
        if (d / "inputs/input_freeze.v1.yaml").is_file():
            rounds.append((int(d.name[5:]), d))
    return sorted(rounds)


def history_intact(diff_lines: list[str], status_lines: list[str]) -> bool:
    """历史轮字节完整性判据：对冻结提交零差异 且 无未跟踪/未提交条目。"""
    return not diff_lines and not status_lines


def check_pkg1_input_freeze(root: Path) -> tuple[bool, list[str]]:
    """轮次感知冻结校验：最新轮冻结清单逐摘要对盘（场景基座/本轮请求/作者指令/
    生成器模块 + 分片并集=总文件）；历史轮证据对其冻结提交做字节完整性。"""
    import re as _re
    pkg1 = root / P7 / "pkg1_open_regression"
    rounds = _pkg1_rounds(root)
    if not rounds:
        return True, ["SKIP: not materialized yet"]
    ok = True
    details = []
    # --- 历史轮：对冻结提交零字节漂移（含未跟踪新增） ---
    for rnd, rdir in rounds[:-1]:
        commit = PKG1_ROUND_FREEZE_COMMITS.get(rnd)
        if commit is None:
            ok = False
            details.append(f"round{rnd}: FREEZE COMMIT UNREGISTERED")
            continue
        paths = [str((rdir / p).relative_to(root))
                 for p in ("inputs", "outputs", "review", "result", "route")
                 if (rdir / p).exists()]
        diff = subprocess.run(
            ["git", "diff", "--name-only", commit, "--", *paths],
            capture_output=True, text=True, cwd=str(root))
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", *paths],
            capture_output=True, text=True, cwd=str(root))
        diff_lines = [l for l in diff.stdout.splitlines() if l]
        status_lines = [l for l in status.stdout.splitlines() if l]
        if diff.returncode or status.returncode or not history_intact(
                diff_lines, status_lines):
            ok = False
            details.append(
                f"round{rnd}_HISTORY_TAMPERED {(diff_lines + status_lines)[:4]}")
        else:
            details.append(f"round{rnd}: byte-intact vs {commit[:7]}")
    # --- 最新轮：冻结清单逐摘要对盘 ---
    latest, latest_dir = rounds[-1]
    text = (latest_dir / "inputs/input_freeze.v1.yaml").read_text(encoding="utf-8")
    instruction = (root / G3 / ("contract/g3_author_instruction.v2.0.md"
                                if latest == 1
                                else "contract/g3_author_instruction.v2.1.md"))
    checks = [("scenarios_sha256", pkg1 / "inputs/scenarios.g3.v1.jsonl"),
              ("requests_sha256", latest_dir / "inputs/requests.g3.v1.jsonl")]
    if "author_instruction_sha256:" in text:
        checks.append(("author_instruction_sha256", instruction))
    for key, rel in checks:
        m = _re.search(rf"{key}: ([0-9a-f]{{64}})", text)
        if not (m and rel.is_file() and sha256_file(rel) == m.group(1)):
            ok = False
            details.append(f"DRIFT {key}")
    for m in _re.finditer(r"  (g3_\w+\.py): ([0-9a-f]{64})", text):
        f = (root / "controlled_content_generator_v2_001"
             / "generator_v3_successor_001" / m.group(1))
        if sha256_file(f) != m.group(2):
            ok = False
            details.append(f"DRIFT module {m.group(1)}")
    # 分片并集 = 总文件（最新轮）
    canonical = {l for l in (latest_dir / "inputs/requests.g3.v1.jsonl"
                             ).read_text(encoding="utf-8").splitlines() if l}
    shards = set()
    for shard in sorted((latest_dir / "inputs/requests_by_cp").glob("CP*.jsonl")):
        shards.update(l for l in shard.read_text(encoding="utf-8").splitlines() if l)
    if canonical != shards:
        ok = False
        details.append("shard union != canonical requests")
    details.append(f"round{latest}_requests={len(canonical)}"
                   f" shards_match={canonical == shards}")
    return ok, details


def check_pkg1_route(root: Path) -> tuple[bool, list[str]]:
    """路线60：金标未漂移 + 物化比对与全新重算逐字节一致 + pass 判据成立。"""
    pkg1 = root / P7 / "pkg1_open_regression"
    comparisons = pkg1 / "route/route_comparisons.g3.jsonl"
    if not comparisons.is_file():
        return True, ["SKIP: not materialized yet"]
    if not route_gold_ok(root):
        return False, ["ROUTE GOLD DRIFTED"]
    import importlib.util
    import tempfile
    g3dir = (root / "controlled_content_generator_v2_001"
             / "generator_v3_successor_001")
    sys.path.insert(0, str(g3dir))
    spec = importlib.util.spec_from_file_location(
        "g3_route_driver", g3dir / "g3_route_driver.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    with tempfile.TemporaryDirectory() as tmp:
        result = module.run_route_60(Path(tmp))
        fresh = (Path(tmp) / "route_comparisons.g3.jsonl").read_bytes()
    ok = fresh == comparisons.read_bytes() and result["pass"]
    return ok, [f"recompute_identical={fresh == comparisons.read_bytes()}",
                f"pass={result['pass']} action={result['action_match_count']}"
                f" reason={result['reason_match_count']}"]


def check_pkg1_blind(root: Path) -> tuple[bool, list[str]]:
    """盲审包零标签泄漏 + 映射双射 + 包与首输出一一对应（最新已物化盲包的轮）。"""
    pkg1 = root / P7 / "pkg1_open_regression"
    rounds = _pkg1_rounds(root) or [(1, pkg1)]
    with_packet = [(n, d) for n, d in rounds
                   if (d / "review/blind/neutral_packet.v1.jsonl").is_file()]
    if not with_packet:
        return True, ["SKIP: not materialized yet"]
    rnd, rdir = with_packet[-1]
    pkg1 = rdir
    packet = pkg1 / "review/blind/neutral_packet.v1.jsonl"
    rows = [json.loads(l) for l in packet.read_text(encoding="utf-8").splitlines() if l]
    leaks = []
    for row in rows:
        texts = [row["title"], *row["body"], *row["spoken_lines"], row["cta"],
                 *row["visual_execution"], *row["audio_execution"]]
        leaks += blind_leak_offenders([str(t) for t in texts])
    mapping = [json.loads(l) for l in
               (pkg1 / "review/blind/neutral_mapping.v1.jsonl"
                ).read_text(encoding="utf-8").splitlines() if l]
    neutral_ids = [r["neutral_id"] for r in mapping]
    request_ids = [r["request_id"] for r in mapping]
    bijection = (len(set(neutral_ids)) == len(neutral_ids)
                 and len(set(request_ids)) == len(request_ids)
                 and len(mapping) == len(rows))
    ok = not leaks and bijection
    return ok, [f"round={rnd} items={len(rows)}"
                f" leaks={sorted(set(leaks))} bijection={bijection}"]


def check_pkg1_reviews(root: Path) -> tuple[bool, list[str]]:
    """轮次感知审查校验（对最新已出指标的轮）：角色碰撞=0；分母完整；
    指标重算一致——现行轮用现行模块重算（非破坏：先快照、错则还原判 FAIL）；
    历史轮指标的完整性由 pkg1_input_freeze 节的冻结提交锚点担保，此处不重算。"""
    import os as _os
    pkg1 = root / P7 / "pkg1_open_regression"
    rounds = _pkg1_rounds(root)
    live = [(n, d) for n, d in rounds
            if (d / f"result/round{n}_metrics.v1.json").is_file()]
    if not live:
        return True, ["SKIP: not materialized yet"]
    n, rdir = live[-1]
    latest_freeze_round = rounds[-1][0]
    metrics_file = rdir / f"result/round{n}_metrics.v1.json"
    metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
    requests = [json.loads(l) for l in
                (rdir / "inputs/requests.g3.v1.jsonl"
                 ).read_text(encoding="utf-8").splitlines() if l]
    authors = set()
    for r in requests:
        pool = r["author_identity"]
        authors.update(map(str, pool if isinstance(pool, list) else [pool]))
    reviewers: set[str] = set()
    for f in sorted((rdir / "review").glob("*_review.*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                reviewers.add(str(json.loads(line).get("reviewer_identity")))
    collisions = role_collision_offenders(authors, reviewers)
    denominator = (metrics["output_count"] == len(requests)
                   and len(metrics["failed_ids_retained_in_denominator"])
                   == metrics["output_count"] - metrics["first_acceptable_count"])
    if n == latest_freeze_round:
        before = metrics_file.read_bytes()
        env = dict(_os.environ, PKG1_ROUND=str(n))
        r = subprocess.run(
            ["python3", str(pkg1 / "run_pkg1.py"), "metrics"],
            capture_output=True, text=True, cwd=str(root), env=env)
        after = metrics_file.read_bytes()
        recompute_identical = (r.returncode == 0 and after == before)
        if after != before:
            metrics_file.write_bytes(before)
        recompute_note = f"metrics_recompute_identical={recompute_identical}"
    else:
        recompute_identical = True
        recompute_note = (f"round{n} metrics anchored to freeze commit"
                          f" (modules superseded by round{latest_freeze_round})")
    ok = not collisions and denominator and recompute_identical
    return ok, [f"round={n} role_collisions={collisions}",
                f"denominator_intact={denominator}", recompute_note]


SECTIONS: dict[str, object] = {
    "freeze_integrity": check_freeze_integrity,
    "write_surface": check_write_surface,
    "external_workspaces": check_external_workspaces,
    "core_caliber": check_core_caliber,
    "g3_selftest": check_g3_selftest,
    "pkg1_input_freeze": check_pkg1_input_freeze,
    "pkg1_route": check_pkg1_route,
    "pkg1_blind": check_pkg1_blind,
    "pkg1_reviews": check_pkg1_reviews,
}


def selftest() -> int:
    """反向自测：证明检查会失败（源指令 §8 反向案例的机器化子集）。
    其余反向案例由 g3 tests/test_g3.py 的 12 个篡改案例覆盖（伪造组件使用、
    表面篡改、主张脱面、冻结复用、run_id 重复等）。"""
    import shutil
    import tempfile
    failures: list[str] = []

    def expect(name: str, condition: bool) -> None:
        print(f"[{'ok' if condition else 'FAIL'}] selftest:{name}")
        if not condition:
            failures.append(name)

    # 1. 修改一个受保护文件字节 → freeze_integrity 必须 FAIL
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        fi_src = DEFAULT_ROOT / P7 / "freeze"
        (tmp_root / P7 / "freeze").mkdir(parents=True)
        for f in fi_src.iterdir():
            shutil.copy(f, tmp_root / P7 / "freeze" / f.name)
        # 复制全部锚点与清单文件后篡改其中一个
        import re as _re
        pairs = _re.findall(r"path: (\S+)\n\s+sha256: [0-9a-f]{64}",
                            (fi_src / "frozen_inputs.v1.1.yaml"
                             ).read_text(encoding="utf-8"))
        manifest = (fi_src / "p5_p6_full_tree_manifest.v1.1.tsv"
                    ).read_text(encoding="utf-8")
        for rel in pairs:
            if "p7_successor_longrun_001" in rel:
                continue
            src = DEFAULT_ROOT / rel
            dst = tmp_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
        for line in manifest.splitlines():
            rel = GATE1 + "/" + line.split("\t")[2]
            src = DEFAULT_ROOT / rel
            dst = tmp_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
        for rel, (sha, _n) in EXTRA_PROTECTED.items():
            dst = tmp_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(DEFAULT_ROOT / rel, dst)
        ok_clean, _ = check_freeze_integrity(tmp_root)
        expect("tamper_baseline_clean", ok_clean)
        victim = tmp_root / pairs[0]
        data = bytearray(victim.read_bytes())
        data[0] ^= 1
        victim.write_bytes(bytes(data))
        ok_tampered, _ = check_freeze_integrity(tmp_root)
        expect("protected_byte_tamper_detected", not ok_tampered)

    # 2. 写入允许目录之外 → 必须被 surface_offenders 抓住
    expect("out_of_surface_detected",
           surface_offenders(["ci/checkers/check_gate1_v1_1_current.py"]) != [])
    expect("in_surface_clean",
           surface_offenders([P7 + "/x.txt", G3 + "/y.py"]) == [])

    # 3. 盲审材料塞入 CP 编号/产品名称 → 必须被抓住
    expect("blind_leak_cp_detected",
           blind_leak_offenders(["这条 CP07 内容"]) != [])
    expect("blind_leak_name_detected",
           blind_leak_offenders(["这是专业判断切片式内容"]) != [])
    expect("blind_clean", blind_leak_offenders(["一条干净的正文"]) == [])

    # 4. 作者兼任独立审查者 → 必须被抓住
    expect("role_collision_detected",
           role_collision_offenders({"A1", "A2"}, {"A2", "R1"}) == ["A2"])

    # 5. 删除失败候选操纵分母 → 必须被抓住
    expect("denominator_drop_detected",
           not denominator_ok(120, 119, 5, 114))
    expect("denominator_intact_ok", denominator_ok(120, 120, 6, 114))

    # 5b. 历史轮证据被改写/塞入未跟踪文件 → history_intact 必须失败
    expect("history_committed_tamper_detected",
           not history_intact(["pkg1/result/round1_metrics.v1.json"], []))
    expect("history_untracked_injection_detected",
           not history_intact([], ["?? pkg1/review/extra.jsonl"]))
    expect("history_clean_ok", history_intact([], []))

    # 6. 修改路线黄金答案 → route_gold_ok 必须失败（临时根缺文件即漂移语义）
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        gold_rel = (GATE1 + "/p1b_signed_review_closeout_and_baseline_freeze_001"
                    "/route/route_60_gold_answers.v0.1.jsonl")
        dst = tmp_root / gold_rel
        dst.parent.mkdir(parents=True)
        data = bytearray((DEFAULT_ROOT / gold_rel).read_bytes())
        data[0] ^= 1
        dst.write_bytes(bytes(data))
        expect("route_gold_tamper_detected", not route_gold_ok(tmp_root))
    expect("route_gold_clean", route_gold_ok(DEFAULT_ROOT))

    print("SELFTEST:", "ALL_NEGATIVE_CASES_ENFORCED" if not failures
          else f"FAILED {failures}")
    return 0 if not failures else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--section")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.list:
        for name in SECTIONS:
            print(name)
        return 0
    root = Path(args.root)
    names = [args.section] if args.section else list(SECTIONS)
    all_ok = True
    for name in names:
        fn = SECTIONS.get(name)
        if fn is None:
            print(f"[ERROR] unknown section {name}")
            return 1
        ok, details = fn(root)  # type: ignore[operator]
        all_ok &= ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        for d in details:
            print(f"    {d}")
    print(f"RESULT: {'ALL_PASS' if all_ok else 'FAILED'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
