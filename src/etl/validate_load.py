"""MySQL 적재 결과를 원본 CSV와 비교해 검증하고 reports/load_validation.md로 저장한다.

기대값은 숫자로 고정하지 않고, 원본 CSV에 load.py와 같은 규칙(번역 보완, 브라질 범위 등)을 적용해 매번 계산한다.
하나라도 실패하면 종료 코드 1.

예) python src/etl/validate_load.py
"""
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import bindparam, text

from db import describe_url, get_engine
from load import EXTRA_TRANSLATIONS, LABELS, LAT_RANGE, LNG_RANGE, read_raw

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports" / "load_validation.md"
DDL = ROOT / "sql" / "schema" / "01_create_tables.sql"

RAW_FILES = {
    "category_translation": "product_category_name_translation",
    "customers": "olist_customers_dataset",
    "sellers": "olist_sellers_dataset",
    "products": "olist_products_dataset",
    "orders": "olist_orders_dataset",
    "order_items": "olist_order_items_dataset",
    "order_payments": "olist_order_payments_dataset",
    "order_reviews": "olist_order_reviews_dataset",
    "geolocation": "olist_geolocation_dataset",
}
REVIEW_SAMPLE = 100
RANDOM_STATE = 42


@dataclass
class Result:
    """검증 항목 1개의 결과."""

    group: str
    name: str
    expected: object
    actual: object

    @property
    def passed(self) -> bool:
        """기대값과 실제값이 같으면 통과."""
        return self.expected == self.actual


def scalar(conn, sql: str):
    """SQL 결과의 첫 값."""
    return conn.execute(text(sql)).scalar_one()


def check_row_counts(conn, raw: dict[str, pd.DataFrame], geo_inside: pd.DataFrame) -> list[Result]:
    """테이블별 DB 행 수를 원본 기준 기대값과 비교한다."""
    expected = {t: len(df) for t, df in raw.items()}
    expected["category_translation"] += len(EXTRA_TRANSLATIONS)
    expected["geolocation_agg"] = geo_inside["geolocation_zip_code_prefix"].nunique()
    expected["review_complaint_labels"] = len(pd.read_csv(LABELS, dtype=str, usecols=["review_id"]))
    notes = {"category_translation": f" (원본 + 보완 {len(EXTRA_TRANSLATIONS)})",
             "geolocation_agg": " (브라질 범위 안 좌표가 있는 우편번호 수)"}
    return [Result("1. 행 수", f"{t}{notes.get(t, '')}", n, scalar(conn, f"SELECT COUNT(*) FROM `{t}`"))
            for t, n in expected.items()]


def check_zip_codes(conn) -> list[Result]:
    """우편번호가 모두 5자리 숫자인지 확인한다."""
    cols = [("customers", "customer_zip_code_prefix"), ("sellers", "seller_zip_code_prefix"),
            ("geolocation", "geolocation_zip_code_prefix"), ("geolocation_agg", "zip_code_prefix")]
    return [Result("2. 우편번호", f"{t}.{c} 5자리 숫자가 아닌 값", 0,
                   scalar(conn, f"SELECT COUNT(*) FROM `{t}` WHERE `{c}` NOT REGEXP '^[0-9]{{5}}$'"))
            for t, c in cols]


def check_amounts(conn, raw: dict[str, pd.DataFrame]) -> list[Result]:
    """금액 합계를 원본 CSV의 Decimal 합계와 비교한다."""
    cols = [("order_items", "price"), ("order_items", "freight_value"), ("order_payments", "payment_value")]
    return [Result("3. 금액 합계", f"{t}.{c}", sum(map(Decimal, raw[t][c])), scalar(conn, f"SELECT SUM(`{c}`) FROM `{t}`"))
            for t, c in cols]


def check_foreign_keys(conn) -> list[Result]:
    """DB에 정의된 FK마다 LEFT JOIN으로 부모에 없는 자식 값을 센다."""
    fks = conn.execute(text(
        "SELECT table_name, column_name, referenced_table_name, referenced_column_name "
        "FROM information_schema.key_column_usage "
        "WHERE table_schema = DATABASE() AND referenced_table_name IS NOT NULL ORDER BY table_name, column_name"
    )).all()
    results = []
    for child, col, parent, pcol in fks:
        orphans = scalar(conn, f"SELECT COUNT(*) FROM `{child}` c LEFT JOIN `{parent}` p ON c.`{col}` = p.`{pcol}` "
                               f"WHERE c.`{col}` IS NOT NULL AND p.`{pcol}` IS NULL")
        results.append(Result("4. FK 무결성", f"{child}.{col} → {parent}.{pcol} 부모 없는 값", 0, orphans))
    n_ddl = DDL.read_text(encoding="utf-8").count("FOREIGN KEY")
    results.append(Result("4. FK 무결성", "DB에 정의된 FK 수 (DDL 파일 기준)", n_ddl, len(fks)))
    return results


def check_nulls(conn, raw: dict[str, pd.DataFrame]) -> list[Result]:
    """orders 날짜와 products 무게·카테고리의 NULL 건수를 원본 기준(빈 값, 무게 0g)과 비교한다."""
    o, p = raw["orders"], raw["products"]
    results = [Result("5. NULL 건수", f"orders.{c}", int((o[c] == "").sum()),
                      int(scalar(conn, f"SELECT SUM(`{c}` IS NULL) FROM orders")))
               for c in ["order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date"]]
    weight = p["product_weight_g"]
    results += [
        Result("5. NULL 건수", "products.product_weight_g (빈 값 + 0g)", int(((weight == "") | (weight == "0")).sum()),
               int(scalar(conn, "SELECT SUM(product_weight_g IS NULL) FROM products"))),
        Result("5. NULL 건수", "products.product_category_name (빈 값)", int((p["product_category_name"] == "").sum()),
               int(scalar(conn, "SELECT SUM(product_category_name IS NULL) FROM products"))),
    ]
    return results


def check_review_texts(conn, reviews: pd.DataFrame) -> list[Result]:
    """무작위 리뷰 100건의 제목·본문을 원본과 비교한다(빈 값은 NULL로 적재됐어야 함)."""
    sample = reviews.sample(REVIEW_SAMPLE, random_state=RANDOM_STATE)
    stmt = text("SELECT review_id, order_id, review_comment_title, review_comment_message FROM order_reviews "
                "WHERE review_id IN :ids").bindparams(bindparam("ids", expanding=True))
    db = pd.DataFrame(conn.execute(stmt, {"ids": sample["review_id"].tolist()}).all(),
                      columns=["review_id", "order_id", "title_db", "message_db"])
    merged = sample.merge(db, on=["review_id", "order_id"], how="left")

    def same(raw_col: str, db_col: str) -> pd.Series:
        """빈 문자열은 NULL과 같은 것으로 보고 비교한다."""
        return merged[raw_col].replace("", None).fillna("\0") == merged[db_col].fillna("\0")

    n_same = int((same("review_comment_title", "title_db") & same("review_comment_message", "message_db")).sum())
    n_text = int((sample["review_comment_message"] != "").sum())
    return [Result("6. 리뷰 텍스트", f"무작위 {REVIEW_SAMPLE}건(random_state={RANDOM_STATE}, 본문 있는 {n_text}건 포함) 원본과 일치",
                   REVIEW_SAMPLE, n_same)]


def check_geolocation_agg(conn, geo_inside: pd.DataFrame) -> list[Result]:
    """집계 좌표가 모두 브라질 범위 안인지, n_points 합계가 범위 안 원본 행 수와 같은지 확인한다."""
    outside = scalar(conn, f"SELECT COUNT(*) FROM geolocation_agg WHERE lat NOT BETWEEN {LAT_RANGE[0]} AND {LAT_RANGE[1]} "
                           f"OR lng NOT BETWEEN {LNG_RANGE[0]} AND {LNG_RANGE[1]}")
    return [
        Result("7. geolocation_agg", f"브라질 범위(위도 {LAT_RANGE}, 경도 {LNG_RANGE}) 밖 좌표", 0, outside),
        Result("7. geolocation_agg", "n_points 합계 (= 범위 안 원본 행 수)", len(geo_inside),
               int(scalar(conn, "SELECT SUM(n_points) FROM geolocation_agg"))),
    ]


def check_labels(conn) -> list[Result]:
    """분류 결과의 유형별·플래그 합계를 CSV와 비교한다."""
    df = pd.read_csv(LABELS, dtype=str, keep_default_na=False)
    cols = [c for c in df.columns if c.isupper() or c.startswith("flag_")]
    sums = conn.execute(text("SELECT " + ", ".join(f"SUM(`{c}`)" for c in cols) + " FROM review_complaint_labels")).one()
    results = [Result("8. review_complaint_labels", f"{c} 합계", int(df[c].astype(int).sum()), int(v))
               for c, v in zip(cols, sums)]
    db_primary = dict(conn.execute(text("SELECT primary_label, COUNT(*) FROM review_complaint_labels GROUP BY primary_label")).all())
    results.append(Result("8. review_complaint_labels", "primary_label 분포", df["primary_label"].value_counts().to_dict(), db_primary))
    return results


def render(results: list[Result]) -> str:
    """검증 결과를 마크다운 리포트로 만든다."""
    n_fail = sum(not r.passed for r in results)
    lines = [
        "# 적재 검증",
        "",
        f"- 실행 시각: {datetime.now().isoformat(timespec='seconds')} / 스크립트: `src/etl/validate_load.py`",
        f"- 접속: `{describe_url()}`",
        f"- 결과: **{'전체 통과' if n_fail == 0 else f'실패 {n_fail}건'}** ({len(results) - n_fail}/{len(results)} 통과)",
        "- 기대값은 원본 CSV에 load.py와 같은 규칙을 적용해 계산한다.",
        "",
    ]
    group = None
    for r in results:
        if r.group != group:
            group = r.group
            lines += ["", f"## {group}", "", "| 항목 | 기대값 | DB 값 | 판정 |", "|---|---|---|---|"]
        exp, act = (r.expected, r.actual) if not isinstance(r.expected, dict) else ("CSV 분포", "같음" if r.passed else r.actual)
        fmt = lambda v: f"{v:,}" if isinstance(v, int) else str(v)  # noqa: E731
        lines.append(f"| {r.name} | {fmt(exp)} | {fmt(act)} | {'통과' if r.passed else '**실패**'} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    """원본을 읽고 모든 검증을 실행해 리포트를 저장한다. 실패가 있으면 종료 코드 1."""
    sys.stdout.reconfigure(encoding="utf-8")
    raw = {t: read_raw(f) for t, f in RAW_FILES.items()}
    geo = raw["geolocation"]
    lat, lng = geo["geolocation_lat"].astype(float), geo["geolocation_lng"].astype(float)
    geo_inside = geo[lat.between(*LAT_RANGE) & lng.between(*LNG_RANGE)]

    engine = get_engine()
    with engine.connect() as conn:
        results = (
            check_row_counts(conn, raw, geo_inside)
            + check_zip_codes(conn)
            + check_amounts(conn, raw)
            + check_foreign_keys(conn)
            + check_nulls(conn, raw)
            + check_review_texts(conn, raw["order_reviews"])
            + check_geolocation_agg(conn, geo_inside)
            + check_labels(conn)
        )
    engine.dispose()

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render(results), encoding="utf-8")
    for r in results:
        if not isinstance(r.expected, dict):
            print(f"[{'통과' if r.passed else '실패'}] {r.group} / {r.name}: 기대 {r.expected} / DB {r.actual}")
        else:
            print(f"[{'통과' if r.passed else '실패'}] {r.group} / {r.name}")
    n_fail = sum(not r.passed for r in results)
    print(f"\n{len(results) - n_fail}/{len(results)} 통과 → 저장: {REPORT.relative_to(ROOT)}")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
