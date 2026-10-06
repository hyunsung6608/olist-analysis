"""sql/views/의 SQL 파일을 파일 이름 순서대로 실행해 분석용 뷰를 만든다(CREATE OR REPLACE VIEW).

생성 후 뷰별 행 수와 생성·조회 시간을 출력한다.

예) python src/etl/create_views.py
"""
import re
import sys
import time
from pathlib import Path

from sqlalchemy import text

from create_schema import load_statements
from db import describe_url, get_engine

ROOT = Path(__file__).resolve().parents[2]
VIEW_DIR = ROOT / "sql" / "views"


def main() -> None:
    """뷰 SQL을 실행하고 뷰별 생성 시간, 행 수, COUNT 조회 시간을 출력한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    files = sorted(VIEW_DIR.glob("*.sql"))
    if not files:
        sys.exit(f"[중단] {VIEW_DIR.relative_to(ROOT)}에 SQL 파일이 없습니다.")
    engine = get_engine()
    print(f"접속: {describe_url()}")
    print(f"{'뷰':<26} {'파일':<30} {'생성(초)':>8} {'행 수':>12} {'COUNT(초)':>10}")
    for path in files:
        for stmt in load_statements(path):
            match = re.search(r"CREATE OR REPLACE VIEW `?(\w+)`?", stmt, re.I)
            if not match:
                sys.exit(f"[중단] {path.name}: CREATE OR REPLACE VIEW 문이 아닙니다.")
            view = match.group(1)
            start = time.perf_counter()
            with engine.begin() as conn:
                conn.execute(text(stmt))
            created = time.perf_counter() - start
            start = time.perf_counter()
            with engine.connect() as conn:
                n = conn.execute(text(f"SELECT COUNT(*) FROM `{view}`")).scalar_one()
            counted = time.perf_counter() - start
            print(f"{view:<26} {path.name:<30} {created:>8.2f} {n:>12,} {counted:>10.2f}")
    engine.dispose()


if __name__ == "__main__":
    main()
