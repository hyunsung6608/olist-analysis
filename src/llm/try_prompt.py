"""분류 프롬프트를 파일럿 리뷰 5건으로 시험한다(모델 호출 1회).

LLM 라벨을 파일럿 라벨과 나란히 출력하고, 응답 스키마 파싱과 토큰 수를 확인한다.
"""
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google import genai
from pydantic import TypeAdapter, ValidationError

from prompts import (
    ReviewLabel,
    build_generate_config,
    build_system_instruction,
    build_user_message,
)

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "data" / "labels" / "pilot_taxonomy_100.csv"
N_TRY = 5
SOLO = {"NO_COMPLAINT", "UNCLEAR"}


def load_pilot(n: int) -> pd.DataFrame:
    """파일럿 라벨 파일에서 앞의 n건을 불러온다."""
    df = pd.read_csv(PILOT, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    return df.head(n).reset_index(drop=True)


def call_gemini(client: genai.Client, model: str, system_instruction: str, user_message: str):
    """Gemini에 분류 요청을 1회 보내고 응답 객체를 돌려준다."""
    return client.models.generate_content(
        model=model,
        contents=user_message,
        config=build_generate_config(system_instruction),
    )


def parse_response(text: str, expected_ids: list[str]) -> list[ReviewLabel]:
    """응답 JSON을 스키마로 검증하고 review_id 대응·단독 라벨 규칙을 확인한다."""
    results = TypeAdapter(list[ReviewLabel]).validate_json(text)
    got_ids = [r.review_id for r in results]
    if sorted(got_ids) != sorted(expected_ids):
        print(f"[경고] review_id 불일치: 누락 {set(expected_ids) - set(got_ids)}, 초과 {set(got_ids) - set(expected_ids)}")
    for r in results:
        codes = {label.value for label in r.labels}
        if codes & SOLO and len(codes) > 1:
            print(f"[경고] 단독 라벨 규칙 위반: {r.review_id} {sorted(codes)}")
    return results


def print_comparison(pilot: pd.DataFrame, results: list[ReviewLabel]) -> None:
    """LLM 라벨과 파일럿 라벨을 나란히 표로 출력한다."""
    by_id = {r.review_id: r for r in results}
    print("| review_id | LLM labels | 파일럿 labels | 일치 | reason |")
    print("|---|---|---|---|---|")
    n_match = 0
    for _, row in pilot.iterrows():
        r = by_id.get(row["review_id"])
        llm = sorted(label.value for label in r.labels) if r else []
        gold = sorted(row["labels"].split("|"))
        match = llm == gold
        n_match += match
        print(
            f"| {row['review_id'][:8]} | {'|'.join(llm) or '(없음)'} | {'|'.join(gold)} "
            f"| {'O' if match else 'X'} | {r.reason if r else '(응답 없음)'} |"
        )
    print(f"\n완전 일치: {n_match}/{len(pilot)}")


def main() -> None:
    """파일럿 5건으로 프롬프트를 1회 호출해 결과·파싱·토큰 수를 출력한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(ROOT / ".env", encoding="utf-8")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "").strip()
    if not api_key or not model:
        sys.exit("[오류] .env에 GEMINI_API_KEY와 GEMINI_MODEL을 설정하세요.")

    pilot = load_pilot(N_TRY)
    reviews = [
        {"review_id": r["review_id"], "title": r["review_comment_title"], "message": r["review_comment_message"]}
        for _, r in pilot.iterrows()
    ]
    system_instruction = build_system_instruction()
    user_message = build_user_message(reviews)

    client = genai.Client(api_key=api_key)
    system_tokens = client.models.count_tokens(model=model, contents=system_instruction).total_tokens
    response = call_gemini(client, model, system_instruction, user_message)

    print(f"모델: {model} / 리뷰 {len(reviews)}건\n")
    try:
        results = parse_response(response.text, pilot["review_id"].tolist())
        print(f"스키마 파싱: 성공 ({len(results)}건)\n")
    except ValidationError as e:
        print(f"스키마 파싱: 실패\n{e}\n\n원본 응답:\n{response.text}")
        results = []
    print_comparison(pilot, results)

    usage = response.usage_metadata
    print("\n토큰 수")
    print(f"  시스템 지시문(count_tokens): {system_tokens}")
    print(f"  입력 전체: {usage.prompt_token_count}")
    print(f"  출력: {usage.candidates_token_count}")
    if usage.thoughts_token_count:
        print(f"  사고(thinking): {usage.thoughts_token_count}")


if __name__ == "__main__":
    main()
