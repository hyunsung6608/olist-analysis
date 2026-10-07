"""Tableau 대시보드용 CSV를 MySQL과 Q5 결과에서 만들어 data/tableau/에 저장한다(UTF-8, BOM 없음, LF).

파일: orders_fact.csv, complaint_labels_long.csv, seller_summary.csv, state_summary.csv, q5_scenarios.csv
유형·주체 이름, 지연 구간은 src/analysis/mappings.py, 판매자 보정은 seller_scoring.py를 따른다.
q5_scenarios.csv는 notebooks/07_q5_recommendations.ipynb를 실행해 생긴 data/processed/q5/의 결과를 쓴다.

예) python src/analysis/export_tableau.py
"""
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "etl"))
from db import get_engine  # noqa: E402
from mappings import (  # noqa: E402
    LABEL_KO, LABELS, NOT_CLASSIFIED, OWNER_OF_LABEL, SELLER_CONTROLLABLE, delay_bucket, delay_bucket_order,
)
from seller_scoring import score_sellers, watch_list_mask  # noqa: E402

OUT_DIR = ROOT / "data" / "tableau"
SQL_DIR = ROOT / "sql" / "analysis"
Q5_DIR = ROOT / "data" / "processed" / "q5"

ORDERS_SQL = """
SELECT
    o.order_id,
    DATE(o.order_purchase_timestamp)                  AS purchase_date,
    DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m')  AS order_month,
    o.customer_state,
    o.order_status,
    o.exclude_delivery_metrics,
    o.is_late,
    o.delay_days,
    o.delivery_days,
    o.n_items,
    o.n_sellers,
    o.items_value,
    o.freight_value,
    o.flag_carrier_before_approval,
    o.flag_status_date_mismatch,
    r.review_id,
    r.review_score,
    r.is_classified,
    r.NOT_RECEIVED, r.WRONG_MISSING, r.DAMAGED, r.NOT_AS_DESCRIBED, r.LOW_QUALITY, r.SHIPPING_COST,
    r.DELAY, r.SERVICE, r.OTHER, r.UNCLEAR, r.NO_COMPLAINT,
    r.primary_label
FROM v_orders o
LEFT JOIN v_order_reviews r ON r.order_id = o.order_id
"""

# 리뷰 × 유형: 한 리뷰가 여러 주문에 연결되면 구매 시각이 가장 이른 주문을 대표 주문으로 쓴다(Q1과 같은 기준)
LABELS_SQL = """
WITH review_order AS (
    SELECT review_id, order_id, order_purchase_timestamp, customer_state
    FROM (
        SELECT r.review_id, o.order_id, o.order_purchase_timestamp, o.customer_state,
               ROW_NUMBER() OVER (PARTITION BY r.review_id ORDER BY o.order_purchase_timestamp, o.order_id) AS rn
        FROM order_reviews r
        JOIN v_orders o ON o.order_id = r.order_id
        WHERE r.review_id IN (SELECT review_id FROM review_complaint_labels)
    ) x
    WHERE rn = 1
)
SELECT l.*, ro.order_id, DATE_FORMAT(ro.order_purchase_timestamp, '%Y-%m') AS order_month, ro.customer_state
FROM review_complaint_labels l
JOIN review_order ro ON ro.review_id = l.review_id
"""


def run_sql(engine, sql: str) -> pd.DataFrame:
    """SQL을 실행해 DataFrame으로 돌려준다(DECIMAL은 float로)."""
    df = pd.read_sql(text(sql), engine)
    for c in df.columns:
        if df[c].dtype == object and df[c].map(lambda v: hasattr(v, "as_tuple")).any():
            df[c] = df[c].astype(float)
    return df


def owner_of(primary_label, is_classified) -> str:
    """주 원인 유형의 개선 주체. 분류하지 않은 리뷰는 '분류 대상 아님', 리뷰가 없으면 빈 값."""
    if pd.isna(is_classified):
        return None
    if is_classified == 0 or pd.isna(primary_label):
        return NOT_CLASSIFIED
    return OWNER_OF_LABEL[primary_label]


def build_orders_fact(engine) -> pd.DataFrame:
    """주문 1행: 배송 지표, 대표 리뷰, 분류 결과, 지연 구간, 개선 주체."""
    df = run_sql(engine, ORDERS_SQL)
    df["has_review"] = df["review_id"].notna().astype(int)
    df["is_low_score"] = (df["review_score"] <= 2).astype("Int64").where(df["has_review"] == 1)
    # 배송 지표 대상이 아닌 주문은 지연 관련 값을 비워 둔다(Q2와 같은 기준)
    metric = df["exclude_delivery_metrics"] == 0
    for c in ["is_late", "delay_days"]:
        df[c] = df[c].astype("Int64").where(metric)
    df["delivery_days"] = df["delivery_days"].astype(float).round(2).where(metric)
    df["review_score"] = df["review_score"].astype("Int64")
    df["delay_bucket"] = [delay_bucket(d, e) for d, e in zip(df["delay_days"], df["exclude_delivery_metrics"])]
    df["delay_bucket_order"] = df["delay_bucket"].map(delay_bucket_order)
    # 분류되지 않은 리뷰의 유형 컬럼은 빈 값(NULL): Tableau에서 평균을 내면 '분류된 리뷰 중 비율'이 된다
    for c in LABELS:
        df[c] = df[c].astype("Int64").where(df["is_classified"] == 1)
    df["is_classified"] = df["is_classified"].astype("Int64")
    df["primary_label_ko"] = df["primary_label"].map(LABEL_KO)
    df["owner"] = [owner_of(p, c) for p, c in zip(df["primary_label"], df["is_classified"])]
    # 파일 크기를 줄이려고 review_id(리뷰 단위는 complaint_labels_long.csv에 있음)는 넣지 않는다
    cols = ["order_id", "purchase_date", "order_month", "customer_state", "order_status", "exclude_delivery_metrics",
            "is_late", "delay_days", "delay_bucket", "delay_bucket_order", "delivery_days", "n_items", "n_sellers",
            "items_value", "freight_value", "flag_carrier_before_approval", "flag_status_date_mismatch",
            "has_review", "review_score", "is_low_score", "is_classified", *LABELS,
            "primary_label", "primary_label_ko", "owner"]
    return df[cols]


def build_labels_long(engine) -> pd.DataFrame:
    """리뷰 × 유형 1행 (붙은 유형만)."""
    df = run_sql(engine, LABELS_SQL)
    long = df.melt(id_vars=["review_id", "order_id", "order_month", "customer_state", "primary_label"],
                   value_vars=LABELS, var_name="label", value_name="has_label")
    long = long[long["has_label"] == 1].copy()
    long["label_ko"] = long["label"].map(LABEL_KO)
    long["owner"] = long["label"].map(OWNER_OF_LABEL)
    long["is_primary"] = (long["label"] == long["primary_label"]).astype(int)
    long["label_order"] = long["label"].map({c: i + 1 for i, c in enumerate(LABELS)})
    return long.sort_values(["review_id", "label_order"])[
        ["review_id", "order_id", "order_month", "customer_state", "label", "label_ko", "label_order", "owner", "is_primary"]]


def build_seller_summary(engine) -> pd.DataFrame:
    """판매자별 지표와 베이지안 보정, 관리 대상 여부 (Q4 노트북과 같은 기준, 판매자 1명 주문만)."""
    df = run_sql(engine, (SQL_DIR / "q4_01_seller_metrics.sql").read_text(encoding="utf-8"))
    df, _ = score_sellers(df, "n_seller_ctrl", prefix="seller_ctrl_rate_")
    df, _ = score_sellers(df, "n_low", prefix="low_rate_")
    overall = df["n_seller_ctrl"].sum() / df["n_orders"].sum()
    df["is_watch_list"] = watch_list_mask(df, "n_seller_ctrl", "seller_ctrl_rate_adj").astype(int)
    df["excess_complaints"] = df["n_seller_ctrl"] - df["n_orders"] * overall
    type_counts = df[[f"n_{t}" for t in SELLER_CONTROLLABLE]]
    df["main_complaint_type"] = type_counts.idxmax(axis=1).str[2:].map(LABEL_KO).where(df["n_seller_ctrl"] > 0)
    df["main_complaint_share"] = (type_counts.max(axis=1) / df["n_seller_ctrl"]).where(df["n_seller_ctrl"] > 0)
    df["meets_min_orders"] = (df["n_orders"] >= 30).astype(int)
    return df[["seller_id", "seller_state", "n_orders", "meets_min_orders", "n_seller_ctrl", "seller_ctrl_rate_raw",
               "seller_ctrl_rate_adj", "excess_complaints", "n_low", "low_rate_raw", "low_rate_adj", "n_delivery_base",
               "late_rate", "is_watch_list", "main_complaint_type", "main_complaint_share"]]


def build_state_summary(engine) -> pd.DataFrame:
    """고객 주별 주문 수, 지연율, 1~2점 비율, 물류 불만 비율 (리뷰 있는 주문 기준, Q4와 같음)."""
    df = run_sql(engine, (SQL_DIR / "q4_03_customer_state.sql").read_text(encoding="utf-8"))
    df["n_late"] = (df["late_rate"] * df["n_delivery_base"]).round().astype(int)
    df["meets_min_orders"] = (df["n_orders"] >= 300).astype(int)
    return df.rename(columns={"n_orders": "n_reviewed_orders"})[
        ["customer_state", "n_reviewed_orders", "meets_min_orders", "n_delivery_base", "n_late", "late_rate", "low_rate", "logistics_rate"]]


def build_q5_scenarios() -> pd.DataFrame:
    """Q5 노트북 결과(단독·세부·묶음 효과, 우선순위)를 한 표로 합친다."""
    paths = {n: Q5_DIR / f"q5_{n}.csv" for n in ["single_effects", "bundles", "priority", "baseline"]}
    missing = [str(p.relative_to(ROOT)) for p in paths.values() if not p.exists()]
    if missing:
        sys.exit(f"[중단] Q5 결과 파일이 없습니다: {missing} — notebooks/07_q5_recommendations.ipynb를 먼저 실행하세요.")
    single = pd.read_csv(paths["single_effects"])
    bundles = pd.read_csv(paths["bundles"])
    prio = pd.read_csv(paths["priority"]).set_index("key")
    total_low = int(pd.read_csv(paths["baseline"], index_col=0).loc["total_low", "value"])

    single["parent"] = single["key"].where(~single["key"].isin(["D1", "D2", "D3"]), "D")
    rows = pd.DataFrame({
        "row_type": single["key"].map(lambda k: "세부" if k in ("D1", "D2", "D3") else "단독"),
        "key": single["key"],
        "intervention": single["개선안"].str.strip(),
        "scenario": single["시나리오"],
        "scenario_level": single["level"],
        "reduction_mean": single["1~2점 감소(평균)"],
        "reduction_low": single["범위 하한"],
        "reduction_high": single["범위 상한"],
        "share_of_low": single["1~2점 대비 비율"],
        "fixed_orders": single["개선 주문 수(기대)"],
        "priority": single["parent"].map(prio["우선순위"]),
        "owner": single["parent"].map(prio["개선 주체"]),
        "feasibility": single["parent"].map(prio["실행 가능성"]),
        "evidence": single["parent"].map(prio["근거 강도"]),
        "reason": single["parent"].map(prio["이유"]),
    })
    bundle_rows = pd.DataFrame({
        "row_type": "묶음", "key": "BUNDLE", "intervention": bundles["묶음 시나리오"], "scenario": "",
        "reduction_mean": bundles["겹침 제거 후"], "reduction_low": bundles["범위 하한"], "reduction_high": bundles["범위 상한"],
        "share_of_low": bundles["1~2점 대비 비율"], "simple_sum": bundles["단순 합"],
        "repurchase_customers_added": bundles["(F) 늘어나는 재구매 고객"],
    })
    e = prio.loc["E"]
    e_row = pd.DataFrame([{"row_type": "보완", "key": "E", "intervention": e["개선안"], "owner": e["개선 주체"],
                           "feasibility": e["실행 가능성"], "evidence": e["근거 강도"], "reason": e["이유"],
                           "service_complaints_max": e["응대 불만 최대치"]}])
    out = pd.concat([rows, bundle_rows, e_row], ignore_index=True)
    out["priority"] = out["priority"].astype("Int64")
    out["baseline_low_reviews"] = total_low
    return out


def main() -> None:
    """모든 파일을 만들어 저장하고 파일별 행 수와 크기를 출력한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    engine = get_engine()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    builders = {
        "orders_fact.csv": lambda: build_orders_fact(engine),
        "complaint_labels_long.csv": lambda: build_labels_long(engine),
        "seller_summary.csv": lambda: build_seller_summary(engine),
        "state_summary.csv": lambda: build_state_summary(engine),
        "q5_scenarios.csv": build_q5_scenarios,
    }
    print(f"{'파일':<28} {'행 수':>9} {'열 수':>5} {'크기':>9}")
    for name, build in builders.items():
        df = build()
        path = OUT_DIR / name
        df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
        print(f"{name:<28} {len(df):>9,} {df.shape[1]:>5} {path.stat().st_size / 1024 / 1024:>7.2f}MB")
    engine.dispose()


if __name__ == "__main__":
    main()
