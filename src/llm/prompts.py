"""리뷰 불만 분류용 프롬프트·응답 스키마·생성 설정을 만든다.

분류 규칙은 complaint_taxonomy.md 한 곳에만 두고, 호출할 때마다 읽어서 시스템 지시문에 넣는다.
"""
import json
import re
from enum import Enum
from pathlib import Path

from google.genai import types
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
TAXONOMY = ROOT / "src" / "llm" / "complaint_taxonomy.md"

LABEL_CODES = [
    "DELAY", "NOT_RECEIVED", "WRONG_MISSING", "DAMAGED", "NOT_AS_DESCRIBED", "LOW_QUALITY",
    "SERVICE", "SHIPPING_COST", "OTHER", "UNCLEAR", "NO_COMPLAINT",
]

Label = Enum("Label", {code: code for code in LABEL_CODES}, type=str)


class ReviewLabel(BaseModel):
    """리뷰 1건의 분류 결과."""

    review_id: str
    labels: list[Label] = Field(min_length=1)
    reason: str


def load_taxonomy() -> str:
    """분류 체계 문서를 읽고, 유형 정의 표의 코드가 LABEL_CODES와 같은지 확인한다."""
    text = TAXONOMY.read_text(encoding="utf-8")
    section = text.split("## 유형 정의", 1)[1].split("\n## ", 1)[0]
    codes = re.findall(r"^\| ([A-Z_]+) \|", section, re.M)
    assert sorted(codes) == sorted(LABEL_CODES), f"분류 체계 문서와 LABEL_CODES가 다름: {codes}"
    return text


def build_system_instruction() -> str:
    """역할, 분류 체계 문서 전문, 판단 원칙을 담은 시스템 지시문을 만든다."""
    return f"""당신은 브라질 이커머스 플랫폼 Olist의 고객 리뷰(포르투갈어)를 불만 유형별로 분류하는 분석가입니다.
아래 분류 체계 문서를 기준으로 각 리뷰에 불만 유형 라벨을 부여합니다.

<분류_체계>
{load_taxonomy()}
</분류_체계>

판단 원칙:
- 제목(title)과 본문(message)을 함께 보고 판단합니다. 둘 중 하나가 비어 있을 수 있습니다.
- 텍스트에 드러난 내용만을 기준으로 판단하고, 텍스트에 없는 내용은 추측하지 않습니다.
- labels에는 해당하는 유형을 모두 넣습니다. 단, NO_COMPLAINT와 UNCLEAR는 다른 유형과 함께 쓰지 않고 단독으로만 사용합니다.
- 주 원인(primary_label)은 고르지 않습니다. labels만 부여합니다.
- reason에는 판단 근거를 한국어 한 문장으로 씁니다.
- 입력된 모든 리뷰에 대해 review_id를 그대로 사용해 하나씩 결과를 반환합니다."""


def build_user_message(reviews: list[dict]) -> str:
    """리뷰 여러 건(review_id, title, message)을 JSON 배열로 담은 사용자 메시지를 만든다."""
    items = [
        {"review_id": r["review_id"], "title": r.get("title") or "", "message": r.get("message") or ""}
        for r in reviews
    ]
    return (
        f"다음 리뷰 {len(items)}건을 분류하세요.\n\n"
        + json.dumps(items, ensure_ascii=False, indent=2)
    )


def build_generate_config(system_instruction: str) -> types.GenerateContentConfig:
    """JSON 스키마 응답, 자동 함수 호출 비활성화 설정을 만든다."""
    # temperature는 지정하지 않고 모델 기본값을 쓴다.
    # Google은 Gemini 3 계열에서 temperature를 기본값(1.0)으로 두기를 권장한다(낮추면 반복·성능 저하 가능).
    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=list[ReviewLabel],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
