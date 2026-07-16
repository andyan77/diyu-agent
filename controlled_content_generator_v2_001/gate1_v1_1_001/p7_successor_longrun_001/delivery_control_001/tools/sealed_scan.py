#!/usr/bin/env python3
"""密封摘要 denylist 撞库扫描 + 合成客户数据标记扫描（SEALED_CUSTODY_PROTOCOL §3-4）。

范围：工作树文件、git 全历史对象（rev-list --objects --all + cat-file）、
软链接目标、（可选）附加目录（缓存/日志/构建产物/自动记忆快照）。
M1 仅以合成标记运行负向测试，不接触真实密封材料。
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

DC = Path(__file__).resolve().parents[1]
SYNTHETIC_CUSTOMER_MARKER = b"SYNTH-CUSTOMER-MARKER-0000"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scan_worktree(root: Path, denylist_digests: set[str],
                  extra_dirs: list[Path] | None = None) -> list[dict]:
    hits: list[dict] = []
    scopes = [root] + list(extra_dirs or [])
    for scope in scopes:
        if not scope.exists():
            continue
        for path in scope.rglob("*"):
            if path.is_symlink():
                try:
                    target = path.resolve()
                    if target.is_file():
                        digest = sha256_bytes(target.read_bytes())
                        if digest in denylist_digests:
                            hits.append({"kind": "SYMLINK_TARGET",
                                         "path": str(path), "digest": digest})
                except OSError:
                    continue
            elif path.is_file():
                try:
                    digest = sha256_bytes(path.read_bytes())
                except OSError:
                    continue
                if digest in denylist_digests:
                    hits.append({"kind": "WORKTREE_FILE",
                                 "path": str(path), "digest": digest})
    return hits


def scan_git_history(repo: Path, denylist_digests: set[str]) -> list[dict]:
    """git 全历史（含 pack 对象）撞库：逐 blob 计算内容 sha256 比对。"""
    hits: list[dict] = []
    r = subprocess.run(["git", "-C", str(repo), "rev-list", "--objects",
                        "--all"], capture_output=True, text=True)
    if r.returncode != 0:
        return [{"kind": "SCAN_ERROR", "path": str(repo),
                 "digest": None, "note": r.stderr.strip()[:200]}]
    for line in r.stdout.splitlines():
        parts = line.split(" ", 1)
        oid = parts[0]
        rel = parts[1] if len(parts) > 1 else ""
        blob = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", oid],
                              capture_output=True)
        if blob.returncode != 0:
            continue  # tree/commit 对象
        digest = sha256_bytes(blob.stdout)
        if digest in denylist_digests:
            hits.append({"kind": "GIT_HISTORY_BLOB", "path": rel,
                         "object": oid, "digest": digest})
    return hits


def scan_customer_markers(root: Path, marker: bytes = SYNTHETIC_CUSTOMER_MARKER
                          ) -> list[dict]:
    hits: list[dict] = []
    if not root.exists():
        return hits
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            if marker in path.read_bytes():
                hits.append({"kind": "CUSTOMER_DATA_MARKER", "path": str(path)})
        except OSError:
            continue
    return hits


def load_denylist(path: Path | None = None) -> set[str]:
    path = path or (DC / "state/SEALED_PAYLOAD_DENYLIST.v1.json")
    if not path.is_file():
        return set()
    value = json.loads(path.read_text(encoding="utf-8"))
    return {row["sha256"] for row in value.get("entries", [])}


def selftest() -> int:
    import tempfile
    failures: list[str] = []

    def expect(name: str, cond: bool) -> None:
        print(f"[{'ok' if cond else 'FAIL'}] sealed_scan_selftest:{name}")
        if not cond:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sealed_payload = b"SYNTHETIC-SEALED-PAYLOAD-QUAL-MARKER-001"
        sealed_digest = sha256_bytes(sealed_payload)
        denylist = {sealed_digest}

        # 干净树零命中
        (root / "clean").mkdir()
        (root / "clean/app.py").write_bytes(b"print('ok')\n")
        expect("clean_tree_no_hits",
               scan_worktree(root / "clean", denylist) == [])

        # 工作树撞库命中
        (root / "dirty").mkdir()
        (root / "dirty/innocuous_name.bin").write_bytes(sealed_payload)
        hits = scan_worktree(root / "dirty", denylist)
        expect("worktree_collision_detected",
               len(hits) == 1 and hits[0]["kind"] == "WORKTREE_FILE")

        # git 全历史撞库：提交后删除，明文只活在历史 → 仍必须命中
        repo = root / "repo"
        repo.mkdir()
        subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t",
                        "-c", "user.name=t", "commit", "-q", "--allow-empty",
                        "-m", "init"], check=True)
        (repo / "leaked.bin").write_bytes(sealed_payload)
        subprocess.run(["git", "-C", str(repo), "add", "leaked.bin"], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t",
                        "-c", "user.name=t", "commit", "-q", "-m", "leak"],
                       check=True)
        (repo / "leaked.bin").unlink()
        subprocess.run(["git", "-C", str(repo), "add", "-u"], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t",
                        "-c", "user.name=t", "commit", "-q", "-m", "remove"],
                       check=True)
        expect("worktree_clean_after_removal",
               scan_worktree(repo, denylist) == [])
        history_hits = scan_git_history(repo, denylist)
        expect("git_history_collision_detected",
               any(h["kind"] == "GIT_HISTORY_BLOB" for h in history_hits))

        # 软链接目标命中
        (root / "linkdir").mkdir()
        (root / "linkdir/real.bin").write_bytes(sealed_payload)
        (root / "linked").mkdir()
        (root / "linked/alias").symlink_to(root / "linkdir/real.bin")
        expect("symlink_target_collision_detected",
               any(h["kind"] == "SYMLINK_TARGET"
                   for h in scan_worktree(root / "linked", denylist)))

        # 合成客户数据标记：日志/缓存内命中
        (root / "logs").mkdir()
        (root / "logs/app.log").write_bytes(
            b"request from " + SYNTHETIC_CUSTOMER_MARKER + b" processed\n")
        expect("customer_marker_in_logs_detected",
               scan_customer_markers(root / "logs") != [])
        expect("customer_marker_clean_dir",
               scan_customer_markers(root / "clean") == [])

    print("SEALED_SCAN_SELFTEST:", "ALL_PASS" if not failures
          else f"FAILED {failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else 2)
