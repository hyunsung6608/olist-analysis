"""sql/schema/01_create_tables.sql을 실행해 MySQL 테이블을 만든다.

--reset을 주면 기존 테이블을 SQL 파일의 생성 순서 역순(자식 → 부모)으로 지운 뒤 다시 만든다.
--reset이 없으면 CREATE TABLE IF NOT EXISTS라 이미 있는 테이블은 그대로 둔다(정의 변경은 반영되지 않음).

예) python src/etl/create_schema.py
    python src/etl/create_schema.py --reset
"""
import argparse
import re
import sys
from pathlib import Path

from sqlalchemy import inspect, text

from db import describe_url, get_engine

ROOT = Path(__file__).resolve().parents[2]
DDL = ROOT / "sql" / "schema" / "01_create_tables.sql"


def parse_args() -> argparse.Namespace:
    """실행 옵션을 읽는다."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="기존 테이블을 지우고 다시 생성 (데이터 삭제됨)")
    return parser.parse_args()


def load_statements(path: Path) -> list[str]:
    """SQL 파일에서 줄 전체 주석(--)을 빼고 세미콜론 기준으로 문장을 나눈다."""
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("--")]
    return [stmt.strip() for stmt in "\n".join(lines).split(";") if stmt.strip()]


def table_names(statements: list[str]) -> list[str]:
    """CREATE TABLE 문에서 테이블 이름을 생성 순서대로 뽑는다."""
    names = []
    for stmt in statements:
        match = re.match(r"CREATE TABLE (?:IF NOT EXISTS )?`?(\w+)`?", stmt, re.I)
        if match:
            names.append(match.group(1))
    return names


def print_tables_and_fks(engine, tables: list[str]) -> None:
    """생성된 테이블 목록과 테이블별 FK를 출력한다."""
    insp = inspect(engine)
    existing = set(insp.get_table_names())
    print("\n테이블과 FK:")
    for t in tables:
        if t not in existing:
            print(f"  {t}: (없음)")
            continue
        fks = insp.get_foreign_keys(t)
        pk = insp.get_pk_constraint(t)["constrained_columns"]
        fk_text = ", ".join(
            f"{fk['name']}({','.join(fk['constrained_columns'])} → {fk['referred_table']}.{','.join(fk['referred_columns'])})"
            for fk in fks
        ) or "FK 없음"
        print(f"  {t}  PK({', '.join(pk)})  {fk_text}")
    extra = existing - set(tables)
    if extra:
        print(f"  (SQL 파일에 없는 테이블: {sorted(extra)})")


def main() -> None:
    """(필요하면 기존 테이블을 지우고) DDL을 실행한 뒤 테이블·FK 목록을 출력한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    statements = load_statements(DDL)
    tables = table_names(statements)
    engine = get_engine()
    print(f"접속: {describe_url()}")

    existing_before = set(inspect(engine).get_table_names())
    with engine.begin() as conn:
        if args.reset:
            for t in reversed(tables):
                if t in existing_before:
                    conn.execute(text(f"DROP TABLE `{t}`"))
                    print(f"삭제: {t}")
        elif existing_before & set(tables):
            print(f"[주의] 이미 있는 테이블은 그대로 둡니다(정의 변경 미반영, 필요하면 --reset): "
                  f"{[t for t in tables if t in existing_before]}")
        for stmt in statements:
            conn.execute(text(stmt))

    created = set(inspect(engine).get_table_names()) - (set() if args.reset else existing_before)
    print(f"\n실행한 문장 {len(statements)}개 / SQL 파일의 테이블 {len(tables)}개 / 이번에 생성 {len(created & set(tables))}개")
    print_tables_and_fks(engine, tables)
    engine.dispose()


if __name__ == "__main__":
    main()
