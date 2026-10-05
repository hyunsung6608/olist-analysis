"""분류 체계 문서(complaint_taxonomy.md)에서 버전·우선순위를 읽고 primary_label을 계산한다."""
import re
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TAXONOMY = ROOT / "src" / "llm" / "complaint_taxonomy.md"

# 라벨링 시트의 유형 컬럼 순서 (validation_300_blank.csv 컬럼 순서와 같아야 함)
LABEL_CODES = [
    "DELAY", "NOT_RECEIVED", "WRONG_MISSING", "DAMAGED", "NOT_AS_DESCRIBED", "LOW_QUALITY",
    "SERVICE", "SHIPPING_COST", "OTHER", "UNCLEAR", "NO_COMPLAINT",
]
# 우선순위 체인에 없는 유형: 다른 유형이 없을 때만 주 원인 (이 순서로 선택)
FALLBACK = ["OTHER", "UNCLEAR", "NO_COMPLAINT"]
# 다른 유형과 함께 쓰지 않는 단독 유형
SOLO = ["NO_COMPLAINT", "UNCLEAR"]


def load_version() -> str:
    """문서 제목 '# ... (v0.5)'에서 분류 체계 버전을 읽는다."""
    text = TAXONOMY.read_text(encoding="utf-8")
    match = re.search(r"^# .*\((v[\d.]+)\)", text, re.M)
    assert match, "분류 체계 문서 제목에서 버전을 찾지 못함"
    return match.group(1)


def load_priority() -> list[str]:
    """분류 체계 문서의 '주 원인 우선순위' 코드 블록에서 우선순위를 읽는다."""
    text = TAXONOMY.read_text(encoding="utf-8")
    section = text.split("## 주 원인 우선순위", 1)[1]
    chain = re.search(r"```\s*\n(.+?)\n```", section, re.S).group(1)
    order = [c.strip() for c in chain.split(">")] + FALLBACK
    assert sorted(order) == sorted(LABEL_CODES), f"우선순위와 유형 코드가 다름: {order}"
    return order


def primary_label(labels: Iterable[str], order: list[str] | None = None) -> str:
    """부여된 유형 중 우선순위가 가장 높은 것을 주 원인으로 고른다. 없으면 빈 문자열."""
    order = order or load_priority()
    codes = set(labels)
    return next((c for c in order if c in codes), "")
