"""LLM 분류 결과에 규칙 기반 후처리를 적용한다(API 호출 없음).

규칙 2(근거 일치): evidence가 있으면 labels를 evidence의 유형 집합으로 맞춘다.
규칙 1(규칙 K 보완): NOT_RECEIVED가 있고 WRONG_MISSING이 없으며, 제목+본문에
                    계속 대기 표현이나 경과 기간이 있으면 DELAY를 추가한다.
규칙 2를 먼저 적용한다(규칙 1이 붙인 DELAY는 evidence에 없으므로 순서가 바뀌면 지워짐).

알려진 한계:
- 문의·응대를 기다린 기간("há 3 dias entrando em contato")도 경과 기간으로 인식될 수 있다.
- 구매 후 사용 기간("comprei ... e com 3 dias parou de funcionar")도 패턴에 걸리지만,
  규칙 1은 NOT_RECEIVED가 있을 때만 발동하므로 영향이 작다.

예외: 미래 표현 vai/vão도 바로 뒤에 fazer가 오면 제외하지 않는다("vai fazer um mês"는 '벌써 한 달째'라는 이미 흐른 기간의 관용 표현).
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
    # '아직도 기다린다' (ainda não = '아직 못 받았다'는 미수령 기본 표현이라 제외)
    "ainda aguardando": r"\bainda (?:estou |to )?(?:aguardando|aguardo|esperando|espero)\b",
}

# 경과 기간: 이미 흐른 기간을 나타내는 형태와 함께 온 '숫자 + 기간단위'만 인정
NUMBER = r"(?:\d+|um|uma|dois|duas|tres|quatro|cinco|seis|sete|oito|nove|dez|quinze|vinte|trinta)"
UNIT = r"(?:dias?|semanas?|mes|meses)"
# 미래·추측 표현 (seria, será, serão, vai, vão, deve, deverá — 악센트 제거형, 단어 단위, 'vai fazer'는 예외)
FUTURE_VERBS = r"(?:seria|sera|serao|va[io](?!\s+fazer)|deve|devera)"
# 앞으로의 기간·기한 설명에 쓰이는 단어 (이 단어가 끼면 발동하지 않음)
FUTURE = rf"(?:prazo|aguard|esper|previs|entreg|\b{FUTURE_VERBS}\b)"
SKIP_WORDS = rf"(?:(?!{FUTURE})[a-z]+\s+){{0,2}}"  # há/faz와 숫자 사이 수식어(quase, mais de 등) 최대 2단어
ELAPSED_PATTERNS = {
    "há": rf"\bha\s+{SKIP_WORDS}{NUMBER}\s+{UNIT}\b",
    "faz": rf"\bfaz\s+{SKIP_WORDS}{NUMBER}\s+{UNIT}\b",
    "mais de": rf"\bmais de\s+{NUMBER}\s+{UNIT}\b",
    "atrás": rf"\b{NUMBER}\s+{UNIT}\s+atras\b",
    "구매 시점부터": (
        rf"\b(?:comprei|compra (?:foi )?(?:feita|efetuada|realizada)|pedido (?:foi )?feito)\b"
        rf"(?:(?!{FUTURE})[^.!?]){{0,40}}?\b{NUMBER}\s+{UNIT}\b"
    ),
}
# 기간 바로 앞(20자 이내)에 앞으로의 기간·추측을 뜻하는 단어가 있으면 제외
# (예: 'aguardar mais de 2 dias', 'seria mais de 30 dias')
FUTURE_BEFORE = rf"\b(?:aguardar|aguarde|esperar|espere|prazo|previsao|{FUTURE_VERBS})\b[^.!?]{{0,20}}$"

RULE_EVIDENCE = "R2_EVIDENCE"
RULE_K_DELAY = "R1_K_DELAY"


def normalize(text: str) -> str:
    """소문자로 바꾸고 악센트를 제거하고 공백을 하나로 합친다."""
    text = unicodedata.normalize("NFKD", text or "").lower()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text)


def find_delay_trigger(title: str, message: str) -> tuple[str, str] | None:
    """제목+본문에서 계속 대기 표현이나 경과 기간을 찾아 (이름, 매칭 구절)을 돌려준다. 없으면 None."""
    text = normalize(f"{title or ''} {message or ''}")
    for name, pattern in WAITING_PATTERNS.items():
        if match := re.search(pattern, text):
            return name, match.group(0)
    for name, pattern in ELAPSED_PATTERNS.items():
        for match in re.finditer(pattern, text):
            if not re.search(FUTURE_BEFORE, text[max(0, match.start() - 30):match.start()]):
                return f"경과 기간({name})", match.group(0)
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
            rules.append(f"{RULE_K_DELAY}:{trigger[0]}")

    return [c for c in ORDER if c in labels], rules


def find_violations(labels: list[str]) -> list[str]:
    """후처리 후에도 남은 규칙 위반을 찾는다(자동 수정하지 않음)."""
    violations = []
    if set(labels) & set(SOLO) and len(labels) > 1:
        violations.append("단독 라벨(NO_COMPLAINT·UNCLEAR) 위반")
    if "NOT_RECEIVED" in labels and "WRONG_MISSING" in labels:
        violations.append("규칙 C 위반(부분 미수령에 NOT_RECEIVED)")
    return violations
