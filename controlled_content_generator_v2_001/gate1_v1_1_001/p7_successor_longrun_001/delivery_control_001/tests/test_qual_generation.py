#!/usr/bin/env python3
"""§四.4 真实 generation/index 绑定库直测：active pointer→manifest→index 链复算 +
内部链篡改 fail-closed。与 test_m3_recovery_interlock 的 ready_set 端负测互补。

纪律：不 skip、不降阈值；每条以真实文件复算断言（含篡改后失配）。"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
P7 = HERE.parents[2]
sys.path.insert(0, str(P7 / "eval_audit_spine_001"))
sys.path.insert(0, str(P7 / "m3_data_supply_001/tools"))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


fx = _load(P7 / "m3_data_supply_001/tools/qual_core_fixtures.py", "fx_gen")
qg = _load(P7 / "m3_data_supply_001/tools/qual_generation.py", "qg_gen")

GOLD, FACES = "0" * 64, "f" * 64


def _build(qual: Path, set_id: str = "A", gen: str = "QUAL_A_GEN_R3_PILOT_001"):
    return qg.build_generation(
        fx.build_core_gold_records(), set_id=set_id, generation_id=gen,
        dataset_manifest_digest=fx.DMD, faces_sha256=FACES, gold_sha256=GOLD,
        qual_dir=qual)


def _expected(manifest: dict) -> dict:
    return {"active_generation_id": manifest["generation_id"],
            "qualification_index_digest": manifest["qualification_index_content_digest"],
            "gold_sha256": GOLD, "faces_sha256": FACES,
            "dataset_manifest_digest": fx.DMD}


class QualGenerationChain(unittest.TestCase):

    def test_positive_chain_resolves_and_binds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            qual = Path(tmp)
            built = _build(qual)
            self.assertEqual(qg.resolve_active_generation(qual, "A")["errors"], [])
            self.assertEqual(
                qg.verify_generation_binding(qual, "A", _expected(built["manifest"])), [])

    def test_generation_id_must_be_structured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                qg.build_generation(fx.build_core_gold_records(), set_id="A",
                                    generation_id="not-structured",
                                    dataset_manifest_digest=fx.DMD,
                                    faces_sha256=FACES, gold_sha256=GOLD,
                                    qual_dir=Path(tmp))

    def test_pointer_self_digest_tamper_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            qual = Path(tmp)
            _build(qual)
            pp = qg.pointer_path(qual, "A")
            pt = json.loads(pp.read_text(encoding="utf-8"))
            pt["active_generation_id"] = "QUAL_A_GEN_SWAPPED_2"  # 不重算 pointer_digest
            pp.write_text(json.dumps(pt), encoding="utf-8")
            self.assertIn("active_pointer_self_digest",
                          qg.resolve_active_generation(qual, "A")["errors"])

    def test_manifest_file_sha_tamper_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            qual = Path(tmp)
            built = _build(qual)
            mpath = qual / built["pointer"]["generation_manifest_path"]
            mpath.write_text(mpath.read_text(encoding="utf-8") + " ", encoding="utf-8")
            self.assertIn("generation_manifest_file_sha_mismatch",
                          qg.resolve_active_generation(qual, "A")["errors"])

    def test_index_file_tamper_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            qual = Path(tmp)
            built = _build(qual)
            ipath = qual / built["manifest"]["qualification_index_path"]
            ipath.write_text(ipath.read_text(encoding="utf-8") + " ", encoding="utf-8")
            self.assertIn("qualification_index_file_sha_mismatch",
                          qg.resolve_active_generation(qual, "A")["errors"])

    def test_wrong_generation_binding_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            qual = Path(tmp)
            built = _build(qual)
            exp = _expected(built["manifest"])
            exp["active_generation_id"] = "QUAL_A_GEN_OTHER_9"
            errs = qg.verify_generation_binding(qual, "A", exp)
            self.assertIn("active_generation_id_not_bound_to_active_generation", errs)

    def test_gold_faces_mismatch_binding_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            qual = Path(tmp)
            built = _build(qual)
            exp = _expected(built["manifest"])
            exp["faces_sha256"] = "a" * 64
            self.assertIn("faces_sha256_not_bound_to_active_generation",
                          qg.verify_generation_binding(qual, "A", exp))

    def test_combined_index_digest_deterministic_and_labeled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            qual = Path(tmp)
            a = _build(qual, "A", "QUAL_A_GEN_R3_PILOT_001")
            b = _build(qual, "B", "QUAL_B_GEN_R3_PILOT_001")
            d1 = qg.combined_index_digest(a["manifest"], b["manifest"])
            self.assertEqual(d1, qg.combined_index_digest(a["manifest"], b["manifest"]))
            # 键位（QUAL_A/QUAL_B）敏感：改任一套 index 内容摘要 → 合取摘要变化
            bmod = dict(b["manifest"])
            bmod["qualification_index_content_digest"] = "7" * 64
            self.assertNotEqual(d1, qg.combined_index_digest(a["manifest"], bmod))


if __name__ == "__main__":
    unittest.main()
