"""Gemini API 연결을 테스트한다.

GEMINI_MODEL이 비어 있으면 사용 가능한 flash 모델 목록만 출력하고,
설정돼 있으면 포르투갈어 리뷰 1건을 한국어로 번역 요청해 응답과 토큰 수를 출력한다.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_REVIEW = "Produto não foi entregue"


def configure_stdout() -> None:
    """Windows 콘솔에서도 한글·포르투갈어가 깨지지 않게 stdout을 UTF-8로 맞춘다."""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def load_settings() -> tuple[str, str]:
    """.env에서 API 키와 모델 이름을 읽는다. 키가 없으면 안내 후 종료한다."""
    load_dotenv(ROOT / ".env", encoding="utf-8")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "").strip()
    if not api_key:
        print(
            "[오류] GEMINI_API_KEY가 설정되지 않았습니다.\n"
            f"  1) {ROOT / '.env'} 파일을 열고\n"
            "  2) GEMINI_API_KEY=<Google AI Studio에서 발급한 키> 를 입력한 뒤 다시 실행하세요.\n"
            "  키 발급: https://aistudio.google.com/apikey",
            file=sys.stderr,
        )
        sys.exit(1)
    return api_key, model


def list_flash_models(client: genai.Client) -> None:
    """사용 가능한 모델 중 이름에 'flash'가 들어간 모델을 출력한다."""
    names = sorted(m.name for m in client.models.list() if "flash" in m.name.lower())
    print(f"GEMINI_MODEL이 비어 있습니다. 사용 가능한 flash 모델 {len(names)}개:")
    for name in names:
        print(f"  - {name.removeprefix('models/')}")
    print("\n.env의 GEMINI_MODEL에 위 이름 중 하나를 넣고 다시 실행하세요.")


def translate_sample(client: genai.Client, model: str) -> None:
    """샘플 리뷰를 한국어로 번역 요청하고 응답·토큰 수를 출력한다."""
    prompt = (
        "다음 포르투갈어 상품 리뷰를 한국어로 번역해줘. 번역문만 출력해.\n\n"
        f"리뷰: {SAMPLE_REVIEW}"
    )
    response = client.models.generate_content(model=model, contents=prompt)
    usage = response.usage_metadata
    print(f"모델: {model}")
    print(f"원문: {SAMPLE_REVIEW}")
    print(f"응답: {(response.text or '').strip()}")
    print(f"입력 토큰: {usage.prompt_token_count}")
    print(f"출력 토큰: {usage.candidates_token_count}")
    if usage.thoughts_token_count:
        print(f"사고(thinking) 토큰: {usage.thoughts_token_count}")


def main() -> None:
    """설정을 읽고 모델 목록 출력 또는 번역 테스트를 실행한다."""
    configure_stdout()
    api_key, model = load_settings()
    client = genai.Client(api_key=api_key)
    if model:
        translate_sample(client, model)
    else:
        list_flash_models(client)


if __name__ == "__main__":
    main()
