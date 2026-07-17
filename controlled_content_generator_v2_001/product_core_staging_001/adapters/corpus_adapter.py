"""语料适配器：core 唯一的领域语料入口（D0 §⑤ 单向测试协议）。

core 不知道任何 GATE1 私有路径；调用方（源仓或产品装配层）把语料路径
显式注入。适配器只做行级读取与形状透传，不做任何领域推断。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


class CorpusMount:
    """显式路径挂载的只读语料源。"""

    def __init__(self, corpus_path: str | Path):
        self._path = Path(corpus_path)
        if not self._path.is_file():
            raise FileNotFoundError(f"corpus not mounted: {self._path}")

    def rows(self) -> Iterator[dict[str, Any]]:
        with open(self._path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield json.loads(line)
