"""적재 전 원본 데이터 품질을 검사하고 reports/data_quality.md로 저장한다(원본은 읽기만 함).

검사 항목마다 건수·비율·대표 사례·처리 방침(변환 / 표시 / 집계에서만 제외 / 그대로 둠)을 기록한다.

예) python src/etl/quality_check.py
"""
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
LABELS = ROOT / "data" / "results" / "review_complaint_labels.csv"
REPORT = ROOT / "reports" / "data_quality.md"

ORDER_DATES = [
    "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
    "order_delivered_customer_date", "order_estimated_delivery_date",
]
# 브라질 영토 범위 (대략적인 경계 상자)
LAT_RANGE = (-34, 6)
LNG_RANGE = (-74, -34)
MISMATCH_TOLERANCE = 1.0  # 주문별 상품+배송비 합계와 결제 합계 차이 기준(BRL)


@dataclass
class Check:
    """검사 항목 1개의 결과."""

    section: str
    name: str
    desc: str
    n: int
    denom: int
    unit: str
    examples: list[str] = field(default_factory=list)
    policy: str = ""
    reason: str = ""

    @property
    def rate(self) -> str:
        """비율 문자열 (분모가 0이면 '-')."""
        return f"{self.n / self.denom:.2%}" if self.denom else "-"


def read_raw(name: str) -> pd.DataFrame:
    """원본 CSV를 모두 문자열로 읽는다(우편번호 앞자리 0 보존, 번역표 BOM 처리)."""
    return pd.read_csv(RAW / f"{name}.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")


def to_dt(s: pd.Series) -> pd.Series:
    """빈 문자열을 NaT로 두고 날짜로 바꾼다."""
    return pd.to_datetime(s.replace("", None))


def examples(df: pd.DataFrame, cols: list[str], n: int = 2) -> list[str]:
    """대표 사례 n건을 'col=값, ...' 문자열로 만든다."""
    return [", ".join(f"{c}={row[c]}" for c in cols) for _, row in df.head(n).iterrows()]


def check_orders(orders: pd.DataFrame, items: pd.DataFrame) -> list[Check]:
    """주문 날짜 순서, 상태-날짜 정합성, 상태별 건수, 예정일 초과 비율을 검사한다."""
    sec, total = "1. orders 날짜 논리", len(orders)
    o = orders.copy()
    for c in ORDER_DATES:
        o[c] = to_dt(o[c])
    p, a, c_, d, e = (o[c] for c in ORDER_DATES)
    ex_cols = ["order_id", "order_status"]
    checks = []

    order_rules = [
        ("구매 > 결제 승인", p > a, ["order_purchase_timestamp", "order_approved_at"],
         "그대로 둠", "위반 없음"),
        ("결제 승인 > 택배사 인계", a > c_, ["order_approved_at", "order_delivered_carrier_date"],
         "표시", "대부분 수 시간~하루 차이(중앙값 약 17시간)로 시스템 기록 시점 차이로 보임. "
                "주문 자체는 정상이므로 남기고, 승인→인계 소요 시간 분석에서만 이 주문을 빼도록 플래그를 둔다"),
        ("택배사 인계 > 고객 수령", c_ > d, ["order_delivered_carrier_date", "order_delivered_customer_date"],
         "집계에서만 제외", "인계 전에 수령할 수 없으므로 날짜 오류. 건수가 적어 원본은 두고 배송 소요 기간 집계에서 제외"),
        ("구매 > 고객 수령", p > d, ["order_purchase_timestamp", "order_delivered_customer_date"],
         "그대로 둠", "위반 없음"),
    ]
    for name, mask, cols, policy, reason in order_rules:
        mask = mask.fillna(False)
        checks.append(Check(sec, f"날짜 순서: {name}", f"두 날짜가 모두 있는 주문 중 {name}인 주문",
                            int(mask.sum()), total, "주문", examples(orders[mask], ex_cols + cols), policy, reason))

    delivered = o["order_status"] == "delivered"
    m = delivered & d.isna()
    checks.append(Check(sec, "delivered인데 고객 수령일 없음", "order_status=delivered이고 order_delivered_customer_date가 빈 주문",
                        int(m.sum()), int(delivered.sum()), "주문", examples(orders[m], ex_cols + ["order_delivered_carrier_date"]),
                        "집계에서만 제외", "수령일이 없어 배송 소요 기간·지연 여부를 계산할 수 없음. 상태 기준 집계에는 포함"))
    m = ~delivered & d.notna()
    checks.append(Check(sec, "delivered가 아닌데 고객 수령일 있음", "order_status≠delivered이고 고객 수령일이 있는 주문",
                        int(m.sum()), int((~delivered).sum()), "주문",
                        examples(orders[m], ex_cols + ["order_delivered_customer_date"]),
                        "표시", f"모두 {', '.join(o.loc[m, 'order_status'].unique())} 상태로, 배송 후 취소(반품 등)로 보임. "
                               "상태는 원본대로 두고 배송 분석 시 상태 조건을 명시"))

    status = o["order_status"].value_counts()
    no_items = ~o["order_id"].isin(items["order_id"])
    status_text = ", ".join(f"{k} {v:,}" for k, v in status.items())
    unavailable = o["order_status"] == "unavailable"
    checks.append(Check(sec, "상태별 주문 수", f"order_status 분포: {status_text}",
                        int(status.get("unavailable", 0) + status.get("canceled", 0)), total, "주문(unavailable+canceled)",
                        [f"unavailable {int(unavailable.sum()):,}건 중 주문 상품(order_items)이 없는 주문 "
                         f"{int((unavailable & no_items).sum()):,}건",
                         f"canceled {int(status.get('canceled', 0)):,}건 중 주문 상품이 없는 주문 "
                         f"{int(((o['order_status'] == 'canceled') & no_items).sum()):,}건"],
                        "그대로 둠", "유효한 상태값. unavailable(결제 후 품절로 보임)은 LLM의 결제 후 품절 리뷰 판단 보완에 활용"))

    has_d = d.notna()
    late = has_d & (d.dt.normalize() > e.dt.normalize())
    checks.append(Check(sec, "예상 배송일보다 늦게 받은 주문 (참고)", "고객 수령일(날짜)이 예상 배송일(날짜)보다 늦은 주문, 수령일 있는 주문 기준",
                        int(late.sum()), int(has_d.sum()), "주문",
                        examples(orders[late], ["order_id", "order_estimated_delivery_date", "order_delivered_customer_date"], 1),
                        "그대로 둠", "품질 문제가 아니라 분석 대상(Q2 배송 지연). 지연 여부는 날짜 단위로 계산"))
    return checks


def check_amounts(items: pd.DataFrame, payments: pd.DataFrame, orders: pd.DataFrame) -> list[Check]:
    """상품 가격·배송비·결제 금액·할부·결제 수단과 주문별 금액 합계 일치를 검사한다."""
    sec = "2. 금액과 수량"
    it = items.assign(price=items["price"].astype(float), freight_value=items["freight_value"].astype(float))
    pa = payments.assign(payment_value=payments["payment_value"].astype(float),
                         payment_installments=payments["payment_installments"].astype(int))
    checks = []

    m = it["price"] <= 0
    checks.append(Check(sec, "order_items: price ≤ 0", "상품 가격이 0 이하인 행", int(m.sum()), len(it), "행",
                        examples(items[m], ["order_id", "price"]), "그대로 둠", "위반 없음"))
    m = it["freight_value"] < 0
    checks.append(Check(sec, "order_items: freight_value < 0", "배송비가 음수인 행", int(m.sum()), len(it), "행",
                        examples(items[m], ["order_id", "freight_value"]), "그대로 둠",
                        f"위반 없음 (참고: 배송비 0인 행 {int((it['freight_value'] == 0).sum()):,}건은 무료 배송으로 보고 정상 처리)"))

    m = pa["payment_value"] <= 0
    types = pa.loc[m, "payment_type"].value_counts().to_dict()
    checks.append(Check(sec, "order_payments: payment_value ≤ 0", f"결제 금액이 0 이하인 행 (결제 수단: {types})",
                        int(m.sum()), len(pa), "행", examples(payments[m], ["order_id", "payment_type", "payment_value"]),
                        "그대로 둠", "voucher 0원은 쿠폰 전액 할인 등으로 가능. not_defined 0원은 아래 항목에서 함께 처리"))
    m = pa["payment_installments"] == 0
    checks.append(Check(sec, "order_payments: payment_installments = 0", "할부 개월 수가 0인 행 (일시불은 1)",
                        int(m.sum()), len(pa), "행",
                        examples(payments[m], ["order_id", "payment_type", "payment_installments", "payment_value"]),
                        "집계에서만 제외", "0개월 할부는 정의되지 않은 값. 2건뿐이라 원본은 두고 할부 분석에서만 제외"))
    m = pa["payment_type"] == "not_defined"
    nd_status = orders.loc[orders["order_id"].isin(pa.loc[m, "order_id"]), "order_status"].value_counts().to_dict()
    checks.append(Check(sec, "order_payments: payment_type = not_defined", f"결제 수단이 정의되지 않은 행 (해당 주문 상태: {nd_status})",
                        int(m.sum()), len(pa), "행", examples(payments[m], ["order_id", "payment_type", "payment_value"]),
                        "집계에서만 제외", "금액 0원이고 결제 수단을 알 수 없어 결제 수단별 집계에서만 제외"))

    item_sum = it.assign(total=it["price"] + it["freight_value"]).groupby("order_id")["total"].sum()
    pay_sum = pa.groupby("order_id")["payment_value"].sum()
    both = pd.concat([item_sum, pay_sum], axis=1, keys=["items", "payments"]).dropna()
    gap = both["payments"] - both["items"]
    big = gap.abs() >= MISMATCH_TOLERANCE
    pay_more = gap >= MISMATCH_TOLERANCE
    max_inst = pa.groupby("order_id")["payment_installments"].max()
    inst_rate = (max_inst.reindex(both.index[pay_more]) > 1).mean()
    base_rate = (max_inst.reindex(both.index) > 1).mean()
    ex = both[big].assign(gap=gap[big].round(2)).reset_index().rename(columns={"index": "order_id"})
    ex = ex.reindex(ex["gap"].abs().sort_values(ascending=False).index)
    checks.append(Check(
        sec, "주문별 상품+배송비 합계 ≠ 결제 합계 (차이 1 이상)",
        f"상품·결제가 모두 있는 주문 중 |결제 합계 − (상품 가격+배송비) 합계| ≥ {MISMATCH_TOLERANCE:g}. "
        f"결제가 더 많은 주문 {int(pay_more.sum())}건, 상품 합계가 더 많은 주문 {int((gap <= -MISMATCH_TOLERANCE).sum())}건",
        int(big.sum()), len(both), "주문",
        [f"order_id={r.order_id}, 상품+배송비={r['items']:.2f}, 결제={r.payments:.2f}, 차이={r.gap:+.2f}" for _, r in ex.head(2).iterrows()],
        "그대로 둠",
        f"결제가 더 많은 주문의 {inst_rate:.1%}가 할부 2개월 이상(전체 주문은 {base_rate:.1%})이라 할부 이자로 설명됨. "
        "매출은 order_items, 결제는 order_payments 기준으로 구분해 쓰고 서로 대체하지 않는다"))

    pay_only = pay_sum.index.difference(item_sum.index)
    status = orders.loc[orders["order_id"].isin(pay_only), "order_status"].value_counts().to_dict()
    checks.append(Check(sec, "결제는 있는데 주문 상품이 없는 주문 (참고)", f"order_payments에는 있고 order_items에는 없는 주문 (상태: {status})",
                        len(pay_only), len(orders), "주문", [f"order_id={x}" for x in list(pay_only[:1])],
                        "그대로 둠", "대부분 unavailable·canceled로 상품이 확정되기 전에 끝난 주문. 상품·판매자 분석에는 자연히 빠짐"))
    return checks


def check_products(products: pd.DataFrame, translation: pd.DataFrame) -> list[Check]:
    """상품 무게·크기와 카테고리 결측, 번역표 누락을 검사한다."""
    sec, total = "3. products", len(products)
    dims = ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]
    num = products[dims].apply(lambda s: pd.to_numeric(s.replace("", None)))
    checks = []

    m = num.isna().any(axis=1)
    checks.append(Check(sec, "무게·크기 빈 상품", "무게·길이·높이·너비 중 하나라도 빈 상품", int(m.sum()), total, "상품",
                        examples(products[m], ["product_id"] + dims), "변환", "빈 문자열을 NULL로 적재"))
    m = (num == 0).any(axis=1)
    checks.append(Check(sec, "무게·크기 0인 상품", "무게·길이·높이·너비 중 0인 값이 있는 상품", int(m.sum()), total, "상품",
                        examples(products[m], ["product_id"] + dims), "변환",
                        "무게 0g은 실제로 불가능한 값이므로 NULL로 바꿔 적재(평균·배송비 분석 왜곡 방지)"))
    m = products["product_category_name"] == ""
    checks.append(Check(sec, "카테고리 빈 상품", "product_category_name이 빈 상품", int(m.sum()), total, "상품",
                        examples(products[m], ["product_id", "product_name_lenght"]), "변환",
                        "NULL로 적재하고 분석 시 '(미분류)'로 묶음"))
    cat = products["product_category_name"]
    m = (cat != "") & ~cat.isin(translation["product_category_name"])
    counts = cat[m].value_counts().to_dict()
    checks.append(Check(sec, "번역표에 없는 카테고리", f"카테고리는 있으나 번역표에 없는 상품 ({counts})", int(m.sum()), total, "상품",
                        [f"{k} ({v}개 상품)" for k, v in counts.items()], "변환",
                        "원본은 두고 category_translation 적재 시 영어명 2개를 보완 행으로 추가(출처: 수동 번역 표시)"))
    return checks


def check_geolocation(geo: pd.DataFrame, customers: pd.DataFrame, sellers: pd.DataFrame) -> list[Check]:
    """브라질 범위 밖 좌표와 고객·판매자 우편번호의 위경도 누락을 검사한다."""
    sec = "4. geolocation"
    lat, lng = geo["geolocation_lat"].astype(float), geo["geolocation_lng"].astype(float)
    out = ~(lat.between(*LAT_RANGE) & lng.between(*LNG_RANGE))
    zips_all = geo["geolocation_zip_code_prefix"].nunique()
    zips_only_out = len(set(geo.loc[out, "geolocation_zip_code_prefix"]) - set(geo.loc[~out, "geolocation_zip_code_prefix"]))
    checks = [Check(
        sec, "브라질 범위 밖 좌표", f"위도 {LAT_RANGE[0]}~{LAT_RANGE[1]}, 경도 {LNG_RANGE[0]}~{LNG_RANGE[1]} 밖의 행. "
        f"범위 밖 좌표만 있는 우편번호 {zips_only_out}개 / 전체 {zips_all:,}개",
        int(out.sum()), len(geo), "행",
        examples(geo[out], ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng", "geolocation_city"]),
        "집계에서만 제외", "원본 geolocation 테이블에는 그대로 적재하고, geolocation_agg의 평균 위경도 계산에서만 제외")]

    geo_zips = set(geo["geolocation_zip_code_prefix"])
    for name, df, col in [("customers", customers, "customer_zip_code_prefix"), ("sellers", sellers, "seller_zip_code_prefix")]:
        z = df[col].str.zfill(5)
        miss = ~z.isin(geo_zips)
        uniq = z.drop_duplicates()
        n_miss_uniq = int((~uniq.isin(geo_zips)).sum())
        checks.append(Check(
            sec, f"{name} 우편번호 중 geolocation에 없는 것",
            f"5자리로 맞춘 우편번호 기준. 고유 우편번호 {n_miss_uniq}/{len(uniq):,}개({n_miss_uniq / len(uniq):.2%}) 없음",
            int(miss.sum()), len(df), "행", examples(df[miss], [col, col.replace("zip_code_prefix", "city"),
                                                               col.replace("zip_code_prefix", "state")]),
            "그대로 둠", "LEFT JOIN 시 위경도가 NULL. 지도 분석에서는 주(state) 단위로 대체 가능"))
    return checks


def check_reviews(reviews: pd.DataFrame, orders: pd.DataFrame) -> list[Check]:
    """리뷰 점수 범위, 답변·작성 시각 순서, 리뷰 작성일과 주문일 순서를 검사한다."""
    sec, total = "5. order_reviews", len(reviews)
    r = reviews.assign(score=pd.to_numeric(reviews["review_score"], errors="coerce"),
                       created=to_dt(reviews["review_creation_date"]), answered=to_dt(reviews["review_answer_timestamp"]))
    checks = []
    m = ~r["score"].between(1, 5)
    checks.append(Check(sec, "review_score가 1~5 밖", "점수가 비었거나 1~5 정수가 아닌 행", int(m.sum()), total, "행",
                        examples(reviews[m], ["review_id", "review_score"]), "그대로 둠", "위반 없음"))
    m = r["answered"] < r["created"]
    checks.append(Check(sec, "답변 시각 < 작성 시각", "review_answer_timestamp가 review_creation_date보다 앞선 행",
                        int(m.sum()), total, "행", examples(reviews[m], ["review_id", "review_creation_date", "review_answer_timestamp"]),
                        "그대로 둠", "위반 없음"))
    purchase = r["order_id"].map(orders.set_index("order_id")["order_purchase_timestamp"].pipe(to_dt))
    m = r["created"].dt.normalize() < purchase.dt.normalize()
    ex = reviews[m].assign(order_purchase_timestamp=purchase[m].astype(str))
    checks.append(Check(sec, "리뷰 작성일 < 주문일", "리뷰 요청 발송일(날짜)이 구매일(날짜)보다 앞선 행",
                        int(m.sum()), total, "행", examples(ex, ["review_id", "order_id", "review_creation_date", "order_purchase_timestamp"]),
                        "표시", "주문 전 리뷰는 불가능하므로 날짜 오류. 리뷰 자체(점수·텍스트)는 쓰고, "
                               "주문→리뷰 소요 기간 분석에서만 제외하도록 플래그를 둔다"))
    return checks


def check_labels(reviews: pd.DataFrame) -> list[Check]:
    """LLM 분류 결과의 review_id가 모두 order_reviews에 있는지 검사한다."""
    sec = "6. review_complaint_labels"
    labels = pd.read_csv(LABELS, dtype=str, keep_default_na=False, usecols=["review_id"])
    m = ~labels["review_id"].isin(reviews["review_id"])
    multi = reviews.groupby("review_id")["order_id"].nunique()
    n_multi = int(labels["review_id"].map(multi).gt(1).sum())
    return [Check(sec, "분류 결과 review_id가 order_reviews에 없음",
                  f"review_complaint_labels.csv의 review_id 중 order_reviews에 없는 것. "
                  f"참고: 여러 주문에 연결된 review_id {n_multi}건(조인 시 행이 늘어남)",
                  int(m.sum()), len(labels), "리뷰", examples(labels[m], ["review_id"]),
                  "그대로 둠", "누락 없음. 주문 단위로 조인할 때는 여러 주문에 연결된 리뷰를 고려")]


def render(checks: list[Check]) -> str:
    """검사 결과를 마크다운 리포트로 만든다."""
    lines = [
        "# 데이터 품질 검사 (적재 전)",
        "",
        f"- 검사일: {date.today().isoformat()} / 스크립트: `src/etl/quality_check.py` / 원본: `data/raw` (읽기만 함)",
        "- 처리 방침: **변환**(적재 시 값을 바꿈) / **표시**(값은 두고 플래그) / **집계에서만 제외**(원본은 두고 특정 분석에서 뺌) / **그대로 둠**",
        "",
    ]
    section = None
    for c in checks:
        if c.section != section:
            section = c.section
            lines += [f"## {section}", ""]
        lines += [
            f"### {c.name}",
            "",
            f"- 검사 내용: {c.desc}",
            f"- 건수: **{c.n:,}** / {c.denom:,} {c.unit} ({c.rate})",
        ]
        if c.examples:
            lines.append("- 대표 사례:")
            lines += [f"  - `{e}`" for e in c.examples]
        lines += [f"- 처리 방침: **{c.policy}** — {c.reason}", ""]

    lines += ["## 처리 방침 요약", "", "| 항목 | 건수 (비율) | 방침 | 이유 |", "|---|---|---|---|"]
    for c in checks:
        lines.append(f"| {c.section.split('. ', 1)[1]}: {c.name} | {c.n:,} ({c.rate}) | {c.policy} | {c.reason.split('. ')[0]} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    """원본을 읽어 모든 검사를 실행하고 리포트를 저장한 뒤 요약을 출력한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    orders = read_raw("olist_orders_dataset")
    items = read_raw("olist_order_items_dataset")
    payments = read_raw("olist_order_payments_dataset")
    products = read_raw("olist_products_dataset")
    translation = read_raw("product_category_name_translation")
    geo = read_raw("olist_geolocation_dataset")
    customers = read_raw("olist_customers_dataset")
    sellers = read_raw("olist_sellers_dataset")
    reviews = read_raw("olist_order_reviews_dataset")

    checks = (
        check_orders(orders, items)
        + check_amounts(items, payments, orders)
        + check_products(products, translation)
        + check_geolocation(geo, customers, sellers)
        + check_reviews(reviews, orders)
        + check_labels(reviews)
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render(checks), encoding="utf-8")
    for c in checks:
        print(f"[{c.policy:^8}] {c.name}: {c.n:,} / {c.denom:,} ({c.rate})")
    print(f"\n저장: {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
