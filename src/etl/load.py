"""원본 CSV와 LLM 분류 결과를 데이터 품질 리포트의 '변환' 방침대로 정리해 MySQL에 적재한다.

테이블은 create_schema.py로 미리 만들어 둬야 한다(이 스크립트는 테이블을 만들지 않음).
멱등성: 적재 전에 대상 테이블을 FK 역순으로 비운다. 테이블마다 트랜잭션으로 적재하고,
실패하면 그 테이블을 롤백하고 중단한다. data/raw는 읽기만 한다.

예) python src/etl/load.py
    python src/etl/load.py --tables geolocation geolocation_agg
"""
import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pandas as pd
from sqlalchemy import inspect, text
from tqdm import tqdm

from db import describe_url, get_engine

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
LABELS = ROOT / "data" / "results" / "review_complaint_labels.csv"

LOAD_ORDER = [
    "category_translation", "customers", "sellers", "products", "orders", "order_items",
    "order_payments", "order_reviews", "geolocation", "geolocation_agg", "review_complaint_labels",
]
CHUNK_SIZE = 20_000
# 번역표에 없는 카테고리 보완 (수동 번역)
EXTRA_TRANSLATIONS = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_and_food_preparers",
}
# 브라질 영토 범위 (품질 리포트와 같은 기준)
LAT_RANGE = (-34, 6)
LNG_RANGE = (-74, -34)


def read_raw(name: str) -> pd.DataFrame:
    """원본 CSV를 모두 문자열로 읽는다(앞자리 0 보존, BOM 처리, 빈 칸은 빈 문자열)."""
    return pd.read_csv(RAW / f"{name}.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")


def zip5(s: pd.Series) -> pd.Series:
    """우편번호를 5자리로 앞을 0으로 채운다."""
    return s.str.strip().str.zfill(5)


def to_datetime(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """날짜 컬럼을 datetime으로 바꾼다. 빈 값은 NaT(→ NULL)."""
    for c in cols:
        df[c] = pd.to_datetime(df[c].replace("", None), format="%Y-%m-%d %H:%M:%S")
    return df


def to_int(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """정수 컬럼을 nullable 정수로 바꾼다. 빈 값은 NULL."""
    for c in cols:
        df[c] = pd.to_numeric(df[c].replace("", None)).astype("Int64")
    return df


def to_decimal_text(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """DECIMAL 컬럼은 float 반올림 오차를 피하려고 원본 문자열 그대로 넘긴다(빈 값은 NULL)."""
    for c in cols:
        assert df[c].str.fullmatch(r"-?\d+(\.\d+)?").all(), f"{c}에 숫자가 아닌 값이 있음"
    return df


def empty_to_null(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """빈 문자열을 NULL로 바꾼다."""
    for c in cols:
        df[c] = df[c].replace("", None)
    return df


def prep_category_translation() -> tuple[pd.DataFrame, int]:
    """번역표에 누락된 카테고리 2개를 보완 행으로 추가한다."""
    df = read_raw("product_category_name_translation")
    n_src = len(df)
    dup = set(EXTRA_TRANSLATIONS) & set(df["product_category_name"])
    assert not dup, f"보완하려는 카테고리가 이미 번역표에 있음: {dup}"
    extra = pd.DataFrame(EXTRA_TRANSLATIONS.items(), columns=df.columns)
    return pd.concat([df, extra], ignore_index=True), n_src


def prep_customers() -> tuple[pd.DataFrame, int]:
    """고객 우편번호를 5자리로 맞춘다."""
    df = read_raw("olist_customers_dataset")
    df["customer_zip_code_prefix"] = zip5(df["customer_zip_code_prefix"])
    return df, len(df)


def prep_sellers() -> tuple[pd.DataFrame, int]:
    """판매자 우편번호를 5자리로 맞춘다."""
    df = read_raw("olist_sellers_dataset")
    df["seller_zip_code_prefix"] = zip5(df["seller_zip_code_prefix"])
    return df, len(df)


def prep_products() -> tuple[pd.DataFrame, int]:
    """빈 카테고리·빈 숫자는 NULL, 무게 0g은 NULL로 바꾼다."""
    df = read_raw("olist_products_dataset")
    df = empty_to_null(df, ["product_category_name"])
    df = to_int(df, [c for c in df.columns if c not in ("product_id", "product_category_name")])
    df.loc[df["product_weight_g"] == 0, "product_weight_g"] = pd.NA
    return df, len(df)


def prep_orders() -> tuple[pd.DataFrame, int]:
    """주문 날짜 5개를 DATETIME으로 바꾼다(빈 값 NULL)."""
    df = read_raw("olist_orders_dataset")
    df = to_datetime(df, [c for c in df.columns if c.startswith("order_") and c not in ("order_id", "order_status")])
    return df, len(df)


def prep_order_items() -> tuple[pd.DataFrame, int]:
    """순번은 정수, 발송 기한은 DATETIME, 금액은 DECIMAL 문자열로 둔다."""
    df = read_raw("olist_order_items_dataset")
    df = to_int(df, ["order_item_id"])
    df = to_datetime(df, ["shipping_limit_date"])
    df = to_decimal_text(df, ["price", "freight_value"])
    return df, len(df)


def prep_order_payments() -> tuple[pd.DataFrame, int]:
    """순번·할부는 정수, 결제 금액은 DECIMAL 문자열로 둔다."""
    df = read_raw("olist_order_payments_dataset")
    df = to_int(df, ["payment_sequential", "payment_installments"])
    df = to_decimal_text(df, ["payment_value"])
    return df, len(df)


def prep_order_reviews() -> tuple[pd.DataFrame, int]:
    """점수는 정수, 날짜는 DATETIME, 빈 제목·본문은 NULL로 바꾼다."""
    df = read_raw("olist_order_reviews_dataset")
    df = to_int(df, ["review_score"])
    df = to_datetime(df, ["review_creation_date", "review_answer_timestamp"])
    df = empty_to_null(df, ["review_comment_title", "review_comment_message"])
    return df, len(df)


def read_geolocation() -> pd.DataFrame:
    """위경도 원본을 읽어 우편번호 5자리, 위경도 실수로 바꾼다."""
    df = read_raw("olist_geolocation_dataset")
    df["geolocation_zip_code_prefix"] = zip5(df["geolocation_zip_code_prefix"])
    df["geolocation_lat"] = df["geolocation_lat"].astype(float)
    df["geolocation_lng"] = df["geolocation_lng"].astype(float)
    return df


def prep_geolocation() -> tuple[pd.DataFrame, int]:
    """위경도 원본은 범위 밖 좌표도 그대로 적재한다(id는 자동 증가)."""
    df = read_geolocation()
    return df, len(df)


def mode_first(s: pd.Series) -> str:
    """가장 많이 나온 값. 동률이면 사전순 첫 값(결과가 매번 같도록)."""
    counts = s.value_counts()
    return min(counts.index[counts == counts.iloc[0]])


def prep_geolocation_agg() -> tuple[pd.DataFrame, int]:
    """브라질 범위 밖 좌표를 빼고 우편번호별 평균 위경도와 최빈 city/state로 집계한다."""
    geo = read_geolocation()
    inside = geo["geolocation_lat"].between(*LAT_RANGE) & geo["geolocation_lng"].between(*LNG_RANGE)
    g = geo[inside].groupby("geolocation_zip_code_prefix")
    df = pd.DataFrame({
        "lat": g["geolocation_lat"].mean(),
        "lng": g["geolocation_lng"].mean(),
        "city": g["geolocation_city"].agg(mode_first),
        "state": g["geolocation_state"].agg(mode_first),
        "n_points": g.size(),
    }).rename_axis("zip_code_prefix").reset_index()
    print(f"  geolocation_agg: 범위 밖 좌표 {int((~inside).sum())}행 제외, 우편번호 {geo['geolocation_zip_code_prefix'].nunique():,}개 중 "
          f"{len(df):,}개 집계")
    return df, len(geo)


def prep_review_complaint_labels() -> tuple[pd.DataFrame, int]:
    """LLM 분류 결과 CSV를 그대로 읽는다(0/1 컬럼만 정수로)."""
    df = pd.read_csv(LABELS, dtype=str, keep_default_na=False, encoding="utf-8")
    int_cols = [c for c in df.columns if c.isupper() or c.startswith("flag_")]
    df = to_int(df, int_cols)
    return df, len(df)


PREPARERS: dict[str, Callable[[], tuple[pd.DataFrame, int]]] = {
    t: globals()[f"prep_{t}"] for t in LOAD_ORDER
}


def parse_args() -> argparse.Namespace:
    """실행 옵션을 읽는다."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tables", nargs="+", choices=LOAD_ORDER, help="일부 테이블만 적재 (기본: 전체)")
    return parser.parse_args()


def fk_edges(conn) -> list[tuple[str, str]]:
    """현재 DB의 FK 관계를 (자식, 부모) 목록으로 읽는다."""
    rows = conn.execute(text(
        "SELECT table_name, referenced_table_name FROM information_schema.referential_constraints "
        "WHERE constraint_schema = DATABASE()"
    )).all()
    return [(child, parent) for child, parent in rows]


def row_count(conn, table: str) -> int:
    """테이블 행 수."""
    return conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one()


def check_fk_conflicts(conn, tables: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """일부 테이블만 적재할 때 FK 때문에 비우기·적재가 실패할 상황을 찾는다."""
    problems = []
    selected = set(tables)
    for child, parent in edges:
        if parent in selected and child not in selected and row_count(conn, child) > 0:
            problems.append(f"{parent}를 비우려면 이를 참조하는 {child}(데이터 있음)도 함께 비워야 합니다 → --tables에 {child} 추가")
        if child in selected and parent not in selected and row_count(conn, parent) == 0:
            problems.append(f"{child}가 참조하는 {parent}가 비어 있어 FK 위반이 납니다 → --tables에 {parent} 추가")
    return problems


def clear_tables(engine, tables: list[str], edges: list[tuple[str, str]]) -> None:
    """대상 테이블을 FK 역순으로 비운다. 다른 테이블이 참조하는 테이블은 DELETE, 나머지는 TRUNCATE."""
    referenced = {parent for _, parent in edges}
    for t in reversed(tables):
        with engine.begin() as conn:
            if t in referenced:
                conn.execute(text(f"DELETE FROM `{t}`"))
            else:
                conn.execute(text(f"TRUNCATE TABLE `{t}`"))


def load_table(engine, table: str, df: pd.DataFrame) -> None:
    """한 테이블을 트랜잭션 하나로 나눠 적재한다. 실패하면 이 테이블 전체가 롤백된다."""
    n_chunks = (len(df) + CHUNK_SIZE - 1) // CHUNK_SIZE
    with engine.begin() as conn:
        chunks = range(0, len(df), CHUNK_SIZE)
        progress = tqdm(chunks, desc=f"  {table}", unit="chunk", dynamic_ncols=True, leave=False) if n_chunks > 5 else chunks
        for start in progress:
            df.iloc[start:start + CHUNK_SIZE].to_sql(table, conn, if_exists="append", index=False)


def main() -> None:
    """대상 테이블을 비우고 순서대로 적재한 뒤 테이블별 행 수와 소요 시간을 출력한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    tables = [t for t in LOAD_ORDER if not args.tables or t in args.tables]
    engine = get_engine()
    print(f"접속: {describe_url()}")
    print(f"대상 테이블: {', '.join(tables)}")

    missing = [t for t in tables if t not in inspect(engine).get_table_names()]
    if missing:
        sys.exit(f"[중단] 테이블이 없습니다: {missing} — 먼저 python src/etl/create_schema.py 를 실행하세요.")
    with engine.connect() as conn:
        edges = fk_edges(conn)
        problems = check_fk_conflicts(conn, tables, edges)
    if problems:
        print("[경고] FK 관계 때문에 이 조합으로는 적재할 수 없습니다. 아무것도 바꾸지 않고 중단합니다.")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    t0 = time.perf_counter()
    clear_tables(engine, tables, edges)
    print(f"비우기 완료 (FK 역순, {time.perf_counter() - t0:.1f}초)\n")

    results = []
    for table in tables:
        start = time.perf_counter()
        try:
            df, n_src = PREPARERS[table]()
            load_table(engine, table, df)
        except Exception as e:  # noqa: BLE001 — 어떤 오류든 이 테이블은 롤백됐으므로 출력하고 중단
            print(f"[실패] {table}: 롤백했습니다. 이후 테이블은 적재하지 않습니다.\n  {type(e).__name__}: {str(e)[:500]}")
            sys.exit(1)
        with engine.connect() as conn:
            n_db = row_count(conn, table)
        elapsed = time.perf_counter() - start
        results.append((table, n_src, len(df), n_db, elapsed))
        print(f"  {table:<24} 원본 {n_src:>9,}행 → 적재 {len(df):>9,}행 / DB {n_db:>9,}행  ({elapsed:.1f}초)")

    print("\n[요약]")
    print(f"{'테이블':<24} {'원본 행':>10} {'적재 행':>10} {'DB 행':>10} {'일치':>4} {'초':>7}")
    for table, n_src, n_df, n_db, elapsed in results:
        print(f"{table:<24} {n_src:>10,} {n_df:>10,} {n_db:>10,} {'O' if n_df == n_db else 'X':>4} {elapsed:>7.1f}")
    print(f"총 소요 시간: {time.perf_counter() - t0:.1f}초")
    engine.dispose()


if __name__ == "__main__":
    main()
