"""LLM 분류 결과에 규칙 기반 후처리를 적용한다(API 호출 없음).

규칙 2(근거 일치): evidence가 있으면 labels를 evidence의 유형 집합으로 맞춘다.
규칙 1(규칙 K 보완): NOT_RECEIVED가 있고 WRONG_MISSING이 없으며, 제목+본문에
                    계속 대기 표현이나 경과 기간이 있으면 DELAY를 추가한다.
규칙 2를 먼저 적용한다(규칙 1이 붙인 DELAY는 evidence에 없으므로 순서가 바뀌면 지워짐).
"""
import re
import unicodedata

from taxonomy import SOLO, load_priority

ORDER = load_priority()

# 계속 대기 표현 (소문자·악센트 제거 후 매칭, hj = hoje 줄임말)
WAITING_PATTERNS = {
    "ate hoje": r"\bate (?:hoje|hj)\b",
    "ate o dia de hoje": r"\bate o dia de (?:hoje|hj)\b",
    "ate o momento": r"\bate o momento\b",
    "ate o presente momento": r"\bate o presente momento\b",
    "ate agora": r"\bate agora\b",
    "ainda nao": r"\bainda (?:nao|n)\b",
}
# 경과 기간: 숫자(또는 수사) + 일·주·월
NUMBER = r"(?:\d+|um|uma|dois|duas|tres|quatro|cinco|seis|sete|oito|nove|dez|quinze|vinte|trinta)"
ELAPSED_PATTERN = rf"\b{NUMBER}\s+(?:dias?|semanas?|mes|meses)\b"

RULE_EVIDENCE = "R2_EVIDENCE"
RULE_K_DELAY = "R1_K_DELAY"


def normalize(text: str) -> str:
    """소문자로 바꾸고 악센트를 제거하고 공백을 하나로 합친다."""
    text = unicodedata.normalize("NFKD", text or "").lower()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text)


def find_delay_trigger(title: str, message: str) -> str | None:
    """제목+본문에서 계속 대기 표현이나 경과 기간을 찾아 이름을 돌려준다. 없으면 None."""
    text = normalize(f"{title or ''} {message or ''}")
    for name, pattern in WAITING_PATTERNS.items():
        if re.search(pattern, text):
            return name
    if re.search(ELAPSED_PATTERN, text):
        return "경과 기간"
    return None


def postprocess(record: dict, title: str, message: str) -> tuple[list[str], list[str]]:
    """레코드(raw_labels 또는 labels, evidence)에 후처리를 적용해 (labels, 적용된 규칙 목록)을 돌려준다.

    규칙 이름 뒤 ':' 다음에는 세부 내용(규칙 1은 발동 표현)을 붙인다.
    """
    labels = set(record.get("raw_labels") or record["labels"])
    rules = []

    evidence_labels = {e["label"] for e in record.get("evidence") or []}
    if evidence_labels and evidence_labels != labels:
        removed = sorted(labels - evidence_labels, key=ORDER.index)
        added = sorted(evidence_labels - labels, key=ORDER.index)
        labels = evidence_labels
        rules.append(f"{RULE_EVIDENCE}:" + ",".join([f"-{c}" for c in removed] + [f"+{c}" for c in added]))

    if "NOT_RECEIVED" in labels and "WRONG_MISSING" not in labels and "DELAY" not in labels:
        trigger = find_delay_trigger(title, message)
        if trigger:
            labels.add("DELAY")
            rules.append(f"{RULE_K_DELAY}:{trigger}")

    return [c for c in ORDER if c in labels], rules


def find_violations(labels: list[str]) -> list[str]:
    """후처리 후에도 남은 규칙 위반을 찾는다(자동 수정하지 않음)."""
    violations = []
    if set(labels) & set(SOLO) and len(labels) > 1:
        violations.append("단독 라벨(NO_COMPLAINT·UNCLEAR) 위반")
    if "NOT_RECEIVED" in labels and "WRONG_MISSING" in labels:
        violations.append("규칙 C 위반(부분 미수령에 NOT_RECEIVED)")
    return violations
