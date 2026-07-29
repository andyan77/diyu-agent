#!/usr/bin/env python3
"""提速补丁定向测试：安全并发（分片/并发登记/原子写/严格缓存）+ 字段级仲裁 + 分席 fail-closed。

只验证本次改动引入的真实失败面，全部 mock、零付费模型调用。纪律：不删断言、不 skip。
覆盖 7 条：
  1 分片互斥且穷尽全部批次；
  2 并发 registry 全部 JSONL 可解析（不靠「跳过坏行」拿绿）；
  3 原子写中断不破坏旧缓存；
  4 合格缓存不重写、残缺/重复/非法缓存会重跑；
  5 field-only 仲裁拒绝缺字段、多字段、非法枚举；
  6 一致字段在合并后原样保持、仅分歧字段取仲裁值；
  7 review/formulaic 分席阶段输入未齐时 assemble fail-closed。
"""

from __future__ import annotations

import importlib.util
import json
import multiprocessing
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
P7 = HERE.parents[1].parent
sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
sys.path.insert(0, str(P7 / "m3_data_supply_001/tools"))
sys.path.insert(0, str(P7 / "m3_data_supply_001/gold/tools"))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


GD = _load(P7 / "m3_data_supply_001/tools/qual_gold_derivation.py", "qual_gold_derivation")
QR = _load(P7 / "m3_data_supply_001/gold/tools/qual_runner.py", "qual_runner_par")
L = QR.L


def _label(**over) -> dict:
    base = {"risk": "HIGH", "entailment": "SUPPORTED", "reference_present": True,
            "reference_attributes": {"polarity": "POSITIVE", "modality": "ASSERTED",
                                     "time_scope": "CURRENT", "preconditions": []},
            "atom_present": True, "atom_partition": [["a1"], ["a2"]],
            "safe_to_clear": False, "disclosure_obligation": "NONE",
            "disclosure_violation": False, "misleading": False}
    base.update(over)
    return base


def _reg_worker(args):
    """子进程并发追加 registry（真跨进程 flock 路径）。"""
    path, tag, n = args
    for i in range(n):
        L.register(Path(path), {"kind": "T", "worker": tag, "i": i,
                                "pad": "并发追加撕裂检测" * 40})
    return n


class ShardSafety(unittest.TestCase):
    def test_shard_mutually_exclusive_and_exhaustive(self):
        items = [f"fb_{i:03d}" for i in range(246)]
        for count in (2, 3, 5):
            seen, union = [], set()
            for idx in range(count):
                got = [it for _o, it in QR.shard_filter(items, idx, count)]
                self.assertEqual(len(got), len(set(got)), "分片内不得重复")
                for s in seen:
                    self.assertEqual(set(got) & set(s), set(), "分片之间必须互斥")
                seen.append(got)
                union |= set(got)
            self.assertEqual(union, set(items), "全部分片并集必须穷尽所有批次")
            # 全局序号语义：ordinal 与原列表下标一致（写者归属确定）
            self.assertEqual([o for o, _ in QR.shard_filter(items, 1, count)],
                             [i for i in range(len(items)) if i % count == 1])

    def test_illegal_shard_params_rejected(self):
        with self.assertRaises(SystemExit):
            QR.shard_filter(["a"], 2, 2)
        with self.assertRaises(SystemExit):
            QR.shard_filter(["a"], 0, 0)


class ConcurrentRegistry(unittest.TestCase):
    def test_concurrent_appends_all_parsable(self):
        with tempfile.TemporaryDirectory() as td:
            reg = Path(td) / "SESSION_REGISTRY.jsonl"
            workers, per = 6, 40
            with multiprocessing.Pool(workers) as pool:
                pool.map(_reg_worker, [(str(reg), w, per) for w in range(workers)])
            lines = [l for l in reg.read_text(encoding="utf-8").splitlines() if l.strip()]
            self.assertEqual(len(lines), workers * per, "并发追加不得丢行")
            for l in lines:
                json.loads(l)          # 任一行不可解析即失败：不允许靠跳过坏行拿绿
            cost = L.registry_cost(reg)
            self.assertEqual(cost["corrupt_rows_skipped"], 0, "不得出现撕裂行")
            self.assertEqual(cost["calls"], workers * per)


class AtomicWrite(unittest.TestCase):
    def test_interrupted_write_preserves_existing_cache(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "fb_000.labels.json"
            good = [{"case_id": "C1"}]
            L.atomic_write_json(p, good)
            before = p.read_text(encoding="utf-8")
            with self.assertRaises(TypeError):        # 序列化中途失败 = 写入被打断
                L.atomic_write_json(p, [{"case_id": {1, 2}}])
            self.assertEqual(p.read_text(encoding="utf-8"), before, "旧缓存必须原样存活")
            self.assertEqual(json.loads(p.read_text(encoding="utf-8")), good)
            leftovers = [q.name for q in Path(td).iterdir() if q.name != p.name]
            self.assertEqual(leftovers, [], "不得遗留半截临时件")


class StrictCache(unittest.TestCase):
    def _write(self, p: Path, rows):
        p.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    def test_valid_cache_reused_defective_cache_rerun(self):
        expected = {"C1", "C2"}
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "fb_000.labels.json"
            ok_rows = [{"case_id": "C1", **_label()}, {"case_id": "C2", **_label()}]
            self._write(p, ok_rows)
            self.assertTrue(QR._label_cache_ok(p, expected), "合格缓存必须复用（不重写）")
            # 残缺：少一条（旧 issubset 判据会误判为完成）
            self._write(p, ok_rows[:1])
            self.assertFalse(QR._label_cache_ok(p, expected))
            # 夹带：多一条 case（批组成变化）
            self._write(p, ok_rows + [{"case_id": "C3", **_label()}])
            self.assertFalse(QR._label_cache_ok(p, expected))
            # 重复 case_id
            self._write(p, [ok_rows[0], ok_rows[0], ok_rows[1]])
            self.assertFalse(QR._label_cache_ok(p, expected))
            # schema 非法（坏枚举）
            self._write(p, [{"case_id": "C1", **_label(risk="SUPER")},
                            {"case_id": "C2", **_label()}])
            self.assertFalse(QR._label_cache_ok(p, expected))
            # 截断 / 不可解析
            p.write_text('[{"case_id": "C1"', encoding="utf-8")
            self.assertFalse(QR._label_cache_ok(p, expected))
            # 不存在
            p.unlink()
            self.assertFalse(QR._label_cache_ok(p, expected))


class FieldOnlyAdjudication(unittest.TestCase):
    def setUp(self):
        self.disputed = {"C1": ["risk", "misleading"]}
        self.a = {"C1": _label(risk="HIGH", misleading=False)}

    def _ok(self, row):
        return QR.field_adj_row_valid(row, self.disputed, self.a)

    def test_rejects_missing_extra_and_illegal_fields(self):
        self.assertTrue(self._ok({"case_id": "C1", "risk": "CRITICAL", "misleading": True}))
        # 缺分歧字段
        self.assertFalse(self._ok({"case_id": "C1", "risk": "CRITICAL"}))
        # 夹带未分歧字段
        self.assertFalse(self._ok({"case_id": "C1", "risk": "CRITICAL",
                                   "misleading": True, "entailment": "UNKNOWN"}))
        # 夹带说明性额外键
        self.assertFalse(self._ok({"case_id": "C1", "risk": "CRITICAL",
                                   "misleading": True, "rationale": "因为…"}))
        # 非法枚举
        self.assertFalse(self._ok({"case_id": "C1", "risk": "VERY_HIGH", "misleading": True}))
        # 类型非法（bool 字段给字符串）
        self.assertFalse(self._ok({"case_id": "C1", "risk": "CRITICAL", "misleading": "yes"}))
        # 不属本次争议集
        self.assertFalse(self._ok({"case_id": "CX", "risk": "CRITICAL", "misleading": True}))

    def test_agreed_fields_unchanged_only_disputed_take_adjudicated_value(self):
        a = _label(risk="HIGH", entailment="SUPPORTED", misleading=False)
        b = _label(risk="LOW", entailment="SUPPORTED", misleading=True)
        disputed = GD.field_disputes(a, b)
        self.assertEqual(set(disputed), {"risk", "misleading"})
        adj = {"case_id": "C1", "risk": "CRITICAL", "misleading": True}  # field-only
        resolved, adjudicated = GD.resolve_label_fields(a, b, adj, where="C1")
        self.assertEqual(adjudicated, frozenset({"risk", "misleading"}))
        self.assertEqual(resolved["risk"], "CRITICAL")
        self.assertEqual(resolved["misleading"], True)
        for f in GD.RICH_LABEL_FIELDS:                      # 一致字段一律原样保留
            if f not in disputed:
                self.assertEqual(resolved[f], a[f], f"一致字段 {f} 不得被改写")
        # 分歧字段缺裁决 → fail-closed（goldfreeze 据此拒绝）
        with self.assertRaises(GD.DerivationError):
            GD.resolve_label_fields(a, b, {"case_id": "C1", "risk": "CRITICAL"}, where="C1")


class SeatPhaseFailClosed(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self._saved = (QR.SEAL, QR.REG, QR.assert_sealed_ignored,
                       QR._review_items_for_set, QR._formulaic_pairs_for_set)
        QR.SEAL = tmp / "sealed"
        QR.REG = tmp / "reg.jsonl"
        (tmp / "sealed").mkdir(parents=True, exist_ok=True)
        QR.assert_sealed_ignored = lambda: None
        QR._review_items_for_set = lambda s, target=None: [
            {"item_id": f"QUAL{s}-REV-C{i}", "family_id": "F1_PEOPLE_AND_REAL_SCENE",
             "source_group_id": f"rev-sg{i}", "author_identity": f"GEN_AUTHOR::C{i}",
             "content": "内容", "claim_boundary": "边界", "authorization_scope": "范围",
             "source_summary_a": "甲", "source_summary_b": "乙"} for i in range(4)]
        QR._formulaic_pairs_for_set = lambda s: [
            {"pair_ref": f"QUAL{s}-FP-SS-{i:04d}", "left_id": f"L{i}", "right_id": f"R{i}",
             "family_id": "F1_PEOPLE_AND_REAL_SCENE", "source_group_id": f"fpair-{i}",
             "left_content": "左", "right_content": "右",
             "left_author_identity": f"A::L{i}", "right_author_identity": f"A::R{i}",
             "necessary_grammar_exception_id": None} for i in range(4)]

    def tearDown(self):
        (QR.SEAL, QR.REG, QR.assert_sealed_ignored,
         QR._review_items_for_set, QR._formulaic_pairs_for_set) = self._saved
        self._tmp.cleanup()

    def test_assemble_fails_closed_when_seat_caches_missing(self):
        # 双席缓存全空 → assemble 必须 fail-closed，绝不产出半截 units
        with self.assertRaises(SystemExit):
            QR.cmd_review("A", max_batches=99, phase="assemble")
        self.assertFalse((QR.SEAL / "qual_A" / "review_units.json").exists(),
                         "fail-closed 时不得写出 review_units")
        with self.assertRaises(SystemExit):
            QR.cmd_formulaic("A", max_batches=99, phase="assemble")
        self.assertFalse((QR.SEAL / "qual_A" / "formulaic_units.json").exists(),
                         "fail-closed 时不得写出 formulaic_units")

    def test_seat_a_only_writes_its_own_cache(self):
        calls = {"n": 0}

        def fake_attempt(prompt, ok, raw_dir, stem, reg, meta, carrier="claude"):
            calls["n"] += 1
            self.assertEqual(carrier, "codex", "seat-a 阶段只能走 Codex 载体")
            items = json.loads(prompt[prompt.index("["):prompt.rindex("]") + 1])
            return [{"item_id": it["item_id"], "decision": "APPROVE", "hard_veto": False}
                    for it in items]

        saved = L.attempt_call
        L.attempt_call = fake_attempt
        try:
            QR.cmd_review("A", max_batches=99, phase="seat-a")
        finally:
            L.attempt_call = saved
        self.assertGreater(calls["n"], 0)
        self.assertTrue((QR.SEAL / "qual_A" / "review_A").is_dir(), "席A 缓存须落盘")
        self.assertFalse((QR.SEAL / "qual_A" / "review_B").exists(), "席A 阶段不得写席B 缓存")
        self.assertFalse((QR.SEAL / "qual_A" / "review_units.json").exists(),
                         "单席阶段不得装配 units（须等双席齐）")


class NecessaryGrammarEligibility(unittest.TestCase):
    """NG 必要语法例外须**事先注册**：无 exception id 的对上取 NECESSARY_GRAMMAR 一律拒收。

    实战教训：席位经 _pair_slim 看不到注册状态，曾在 CP 对上标 NG，致 verdict_from_axes 抛
    『necessary grammar requires a preregistered exception』并阻断整条 formulaic 流。
    """
    AX_OK = {"argument_spine": "SAME", "evidence_progression": "DIFFERENT",
             "limitation_function": "DIFFERENT", "viewpoint_anchor": "SAME",
             "closing_function": "DIFFERENT", "transformation_depth": "STRUCTURAL_CHANGE"}

    def _batch(self):
        return [{"pair_ref": "QUALA-FP-SS-0001", "necessary_grammar_exception_id": "NG-1"},
                {"pair_ref": "QUALA-FP-CP-0002", "necessary_grammar_exception_id": None}]

    def test_ng_rejected_only_where_unregistered(self):
        batch = self._batch()
        ok_rows = [{"pair_ref": p["pair_ref"], "axes": dict(self.AX_OK)} for p in batch]
        self.assertTrue(QR._axis_rows_ng_legal(ok_rows, batch))
        # 已注册例外的 SS 对可取 NG
        ss_ng = [dict(r) for r in ok_rows]
        ss_ng[0]["axes"] = {**self.AX_OK, "argument_spine": "NECESSARY_GRAMMAR"}
        self.assertTrue(QR._axis_rows_ng_legal(ss_ng, batch))
        # 未注册例外的 CP 对取 NG 必须拒收（任何轴都不行）
        for axis in ("argument_spine", "transformation_depth"):
            cp_ng = [dict(r) for r in ok_rows]
            cp_ng[1] = {"pair_ref": "QUALA-FP-CP-0002",
                        "axes": {**self.AX_OK, axis: "NECESSARY_GRAMMAR"}}
            self.assertFalse(QR._axis_rows_ng_legal(cp_ng, batch),
                             f"CP 对在 {axis} 轴取 NG 未被拒收")
        # 结构不合格（缺 pair_ref 覆盖）同样拒收
        self.assertFalse(QR._axis_rows_ng_legal(ok_rows[:1], batch))


class ReviewCorpusSpansDecisionSpace(unittest.TestCase):
    """review 校准语料须按构造覆盖判定空间。

    实战教训：旧路径只取自然 claim，导致 hard_veto_cases_present=false、
    negative_specific_agreement=0.0——**不含硬否决样本的校准集在物理上无法测量硬否决一致率**，
    这不是调 rubric 能过的门。
    """
    def test_strata_cover_natural_variant_and_disclosure(self):
        self.assertEqual(sum(n for _, n in QR.REVIEW_STRATA), 50)
        kinds = {k for k, _ in QR.REVIEW_STRATA}
        self.assertEqual(kinds, {"NATURAL", "CHALLENGE_VARIANT", "DISCLOSURE"})
        for _, n in QR.REVIEW_STRATA:
            self.assertGreater(n, 0, "任一层数量为 0 则该层无法参与一致率测量")


if __name__ == "__main__":
    unittest.main(verbosity=2)
