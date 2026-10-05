"""MySQL 연결과 utf8mb4 저장·조회를 테스트한다.

MySQL 버전, 현재 DB·연결의 문자 집합과 콜레이션을 출력하고,
임시 테이블에 포르투갈어·한국어·이모지를 넣었다가 다시 읽어 원래 문자열과 같은지 확인한 뒤 테이블을 삭제한다.
"""
import sys

from sqlalchemy import text

from db import describe_url, get_engine

SAMPLES = ["Não recebi o produto até hoje", "배송 지연", "🤔"]
TEMP_TABLE = "tmp_charset_check"


def print_server_info(conn) -> None:
    """MySQL 버전과 DB·연결 문자 집합, 콜레이션을 출력한다."""
    row = conn.execute(text(
        "SELECT VERSION(), DATABASE(), @@character_set_database, @@collation_database, "
        "@@character_set_client, @@character_set_connection, @@character_set_results, @@collation_connection"
    )).one()
    print(f"MySQL 버전: {row[0]}")
    print(f"현재 DB: {row[1]} / 문자 집합: {row[2]} / 콜레이션: {row[3]}")
    print(f"연결 문자 집합: client={row[4]}, connection={row[5]}, results={row[6]} / 콜레이션: {row[7]}")


def roundtrip_test(conn) -> bool:
    """임시 테이블에 샘플 문자열을 넣고 다시 읽어 원래 문자열과 같은지 확인한다."""
    conn.execute(text(f"DROP TEMPORARY TABLE IF EXISTS {TEMP_TABLE}"))
    conn.execute(text(
        f"CREATE TEMPORARY TABLE {TEMP_TABLE} (id INT PRIMARY KEY, val VARCHAR(100)) "
        "DEFAULT CHARSET=utf8mb4"  # 콜레이션은 DB 기본값(utf8mb4_0900_ai_ci)을 따름
    ))
    try:
        conn.execute(
            text(f"INSERT INTO {TEMP_TABLE} (id, val) VALUES (:id, :val)"),
            [{"id": i, "val": s} for i, s in enumerate(SAMPLES)],
        )
        rows = dict(conn.execute(text(f"SELECT id, val FROM {TEMP_TABLE}")).all())
        all_ok = True
        for i, original in enumerate(SAMPLES):
            got = rows.get(i)
            ok = got == original
            all_ok &= ok
            print(f"  {'OK ' if ok else 'NG '} 넣은 값: {original!r} / 읽은 값: {got!r}")
        return all_ok
    finally:
        conn.execute(text(f"DROP TEMPORARY TABLE IF EXISTS {TEMP_TABLE}"))
        print(f"임시 테이블 {TEMP_TABLE} 삭제")


def main() -> None:
    """연결 정보를 출력하고 서버 정보와 문자열 왕복 테스트를 실행한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"접속: {describe_url()}")
    engine = get_engine()
    with engine.connect() as conn:
        print_server_info(conn)
        print("\n문자열 저장·조회 테스트 (utf8mb4)")
        ok = roundtrip_test(conn)
    engine.dispose()
    print(f"\n결과: {'모두 일치' if ok else '불일치 있음'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
