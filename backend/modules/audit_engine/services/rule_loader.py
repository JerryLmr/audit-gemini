import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


RULES_DIR = Path(__file__).resolve().parents[1] / "rules"


@lru_cache(maxsize=16)
def load_rule_json(filename: str) -> Dict[str, Any]:
    path = RULES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"规则文件不存在: {path}")
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def rule_file_path(filename: str) -> Path:
    return RULES_DIR / filename
