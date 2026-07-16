#!/usr/bin/env python3
"""活跃合同集合摘要工具：freeze 生成冻结摘要清单，verify 复算比对。

真源：P1 §六（ACTIVE_CONTRACT_SET = v2.5@冻结提交）与 §十-C1（D0 生效需活跃合同摘要冻结）。
- freeze:  读 ACTIVE_CONTRACT_SET.v1.json 的 active_plan + active_members，
           逐文件 sha256 → state/ACTIVE_CONTRACT_DIGESTS.v1.json（含集合摘要）。
           成员缺失 = 失败（除非 --allow-pending 且该成员声明 materializes_in）。
- verify:  重算并与冻结清单比对；任何漂移/缺失 = 非零退出。
- selftest: 合成 fixture 证明漂移与缺失会被拒绝。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

DC = Path(__file__).resolve().parents[1]
DEFAULT_SET = DC / "ACTIVE_CONTRACT_SET.v1.json"
DEFAULT_OUT = DC / "state" / "ACTIVE_CONTRACT_DIGESTS.v1.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def compute(set_path: Path, root: Path, allow_pending: bool) -> dict:
    spec = json.loads(set_path.read_text(encoding="utf-8"))
    members: list[dict] = []
    errors: list[str] = []
    entries = [{"id": "ACTIVE_PLAN", "path": spec["active_plan"]["path"],
                "declared_sha256": spec["active_plan"].get("sha256")}]
    entries += [{"id": m["id"], "path": m["path"],
                 "pending": bool(m.get("materializes_in")),
                 "declared_sha256": None} for m in spec["active_members"]]
    for e in entries:
        f = root / e["path"]
        if not f.is_file():
            if allow_pending and e.get("pending"):
                members.append({"id": e["id"], "path": e["path"],
                                "sha256": None, "status": "PENDING_MATERIALIZATION"})
                continue
            errors.append(f"missing member file: {e['id']} {e['path']}")
            continue
        digest = sha256_file(f)
        if e.get("declared_sha256") and digest != e["declared_sha256"]:
            errors.append(f"declared sha256 drift: {e['id']}")
        members.append({"id": e["id"], "path": e["path"], "sha256": digest,
                        "status": "FROZEN"})
    set_digest = hashlib.sha256("\n".join(
        f"{m['id']}:{m['sha256']}" for m in sorted(members, key=lambda x: x["id"])
    ).encode("utf-8")).hexdigest()
    return {"schema_version": "p7-active-contract-digests-v1",
            "contract_set_path": str(set_path.relative_to(root)) if set_path.is_relative_to(root) else str(set_path),
            "contract_set_sha256": sha256_file(set_path),
            "members": members,
            "pending_count": sum(1 for m in members if m["status"] != "FROZEN"),
            "active_contract_set_digest": set_digest,
            "errors": errors}


def cmd_freeze(args) -> int:
    result = compute(Path(args.set_file), Path(args.root), args.allow_pending)
    if result["errors"]:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"frozen": True, "members": len(result["members"]),
                      "pending": result["pending_count"],
                      "active_contract_set_digest": result["active_contract_set_digest"]},
                     ensure_ascii=False))
    return 0


def cmd_verify(args) -> int:
    frozen = json.loads(Path(args.out).read_text(encoding="utf-8"))
    live = compute(Path(args.set_file), Path(args.root),
                   allow_pending=frozen["pending_count"] > 0)
    drift = []
    if live["errors"]:
        drift += live["errors"]
    frozen_map = {m["id"]: m for m in frozen["members"]}
    live_map = {m["id"]: m for m in live["members"]}
    if set(frozen_map) != set(live_map):
        drift.append(f"member id set drift: {sorted(set(frozen_map) ^ set(live_map))}")
    for mid in sorted(set(frozen_map) & set(live_map)):
        if frozen_map[mid]["sha256"] != live_map[mid]["sha256"]:
            drift.append(f"member digest drift: {mid}")
    if frozen["active_contract_set_digest"] != live["active_contract_set_digest"]:
        drift.append("active_contract_set_digest drift")
    print(json.dumps({"verify": "PASS" if not drift else "FAIL", "drift": drift},
                     ensure_ascii=False, indent=2))
    return 0 if not drift else 1


def selftest() -> int:
    failures = []

    def expect(name, cond):
        print(f"[{'ok' if cond else 'FAIL'}] contract_set_selftest:{name}")
        if not cond:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a.md").write_text("A", encoding="utf-8")
        spec = {"active_plan": {"path": "a.md"},
                "active_members": [{"id": "B", "path": "b.md",
                                    "materializes_in": "C2"}]}
        sp = root / "set.json"
        sp.write_text(json.dumps(spec), encoding="utf-8")
        r = compute(sp, root, allow_pending=True)
        expect("pending_allowed", not r["errors"] and r["pending_count"] == 1)
        r2 = compute(sp, root, allow_pending=False)
        expect("missing_member_rejected", bool(r2["errors"]))
        out = root / "digests.json"
        out.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")

        args = argparse.Namespace(set_file=str(sp), root=str(root), out=str(out))
        expect("verify_pass_on_clean", cmd_verify(args) == 0)
        (root / "a.md").write_text("TAMPERED", encoding="utf-8")
        expect("verify_fails_on_drift", cmd_verify(args) == 1)
    print("CONTRACT_SET_SELFTEST:", "ALL_PASS" if not failures else f"FAILED {failures}")
    return 0 if not failures else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DC.parents[3]))
    ap.add_argument("--set-file", default=str(DEFAULT_SET))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--allow-pending", action="store_true")
    ap.add_argument("cmd", choices=["freeze", "verify", "selftest"])
    args = ap.parse_args()
    if args.cmd == "selftest":
        return selftest()
    if args.cmd == "freeze":
        return cmd_freeze(args)
    return cmd_verify(args)


if __name__ == "__main__":
    sys.exit(main())
