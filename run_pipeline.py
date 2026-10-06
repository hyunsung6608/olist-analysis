"""Olist 데이터 파이프라인(품질 검사 → 스키마 → 적재 → 검증)을 순서대로 실행한다.

전체 데이터 흐름:
    data/raw/*.csv (Kaggle 원본, 읽기 전용)
      → 1. 품질 검사   src/etl/quality_check.py  → reports/data_quality.md
      → 2. 스키마 생성 src/etl/create_schema.py  ← sql/schema/01_create_tables.sql
      → 3. 적재        src/etl/load.py           (품질 리포트의 변환 방침 적용, + data/results/review_complaint_labels.csv)
      → 4. 적재 검증   src/etl/validate_load.py  → reports/load_validation.md

LLM 분류가 이 파이프라인에 없는 이유:
    리뷰 분류(src/llm/classify_reviews.py → export_labels.py)는 Gemini API를 수천 번 호출하고
    무료 사용량 제한 때문에 몇 시간이 걸리며, 실행할 때마다 결과가 조금씩 달라질 수 있다.
    그래서 한 번 분류해 검증한 결과를 data/results/review_complaint_labels.csv로 고정해 커밋하고,
    이 파이프라인은 그 파일을 입력으로만 쓴다. 이렇게 하면 DB를 몇 번 다시 만들어도 API 호출이 없고 결과가 같다.

예) python run_pipeline.py          # 기존 테이블 유지 (적재 단계에서 데이터만 비우고 다시 넣음)
    python run_pipeline.py --reset  # 테이블을 지우고 스키마부터 다시 생성
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LABELS = ROOT / "data" / "results" / "review_complaint_labels.csv"
ETL = ROOT / "src" / "etl"


def parse_args() -> argparse.Namespace:
    """실행 옵션을 읽는다."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="create_schema를 --reset으로 실행 (테이블 삭제 후 재생성)")
    return parser.parse_args()


def check_labels_file() -> None:
    """LLM 분류 결과 파일이 없으면 만드는 방법을 안내하고 종료한다."""
    if LABELS.exists():
        print(f"LLM 분류 결과 확인: {LABELS.relative_to(ROOT)}")
        return
    sys.exit(
        f"[중단] {LABELS.relative_to(ROOT)}가 없습니다. LLM 분류는 이 파이프라인에 포함되지 않으므로 먼저 실행하세요:\n"
        "  1) python src/llm/classify_reviews.py --input all --run-name full_v2_post3 --max-calls <호출 수>\n"
        "  2) python src/llm/export_labels.py --run-name full_v2_post3"
    )


def run_step(no: int, name: str, args: list[str]) -> float:
    """단계 하나를 하위 프로세스로 실행하고 소요 시간을 돌려준다. 실패하면 단계 이름을 알리고 종료한다."""
    print(f"\n{'=' * 70}\n[{no}/4] {name} 시작: {' '.join(args)}\n{'=' * 70}", flush=True)
    start = time.perf_counter()
    result = subprocess.run([sys.executable, *args], cwd=ROOT)
    elapsed = time.perf_counter() - start
    if result.returncode != 0:
        print(f"\n[실패] {no}단계 '{name}'에서 멈췄습니다 (종료 코드 {result.returncode}, {elapsed:.1f}초). "
              "위 출력을 확인하세요. 이후 단계는 실행하지 않았습니다.")
        sys.exit(result.returncode)
    print(f"[{no}/4] {name} 종료 ({elapsed:.1f}초)", flush=True)
    return elapsed


def main() -> None:
    """분류 결과 파일을 확인하고 4단계를 순서대로 실행한 뒤 단계별 소요 시간을 출력한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    check_labels_file()
    steps = [
        ("품질 검사", [str(ETL / "quality_check.py")]),
        ("스키마 생성", [str(ETL / "create_schema.py")] + (["--reset"] if args.reset else [])),
        ("적재", [str(ETL / "load.py")]),
        ("적재 검증", [str(ETL / "validate_load.py")]),
    ]
    total_start = time.perf_counter()
    timings = [(name, run_step(i, name, step_args)) for i, (name, step_args) in enumerate(steps, 1)]

    print(f"\n{'=' * 70}\n[완료] 파이프라인 전체 성공")
    for name, elapsed in timings:
        print(f"  {name:<10} {elapsed:>7.1f}초")
    print(f"  {'합계':<10} {time.perf_counter() - total_start:>7.1f}초")


if __name__ == "__main__":
    main()
