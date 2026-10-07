"""분석·대시보드 공통 매핑: 불만 유형 이름, 개선 주체 묶음, 주체별 색, 지연 구간.

유형·주체의 한국어 이름과 색은 이 파일에서만 정의하고, Tableau 내보내기와 설계서가 같은 값을 쓴다.
"""
import math

# 불만 유형 코드 → 한국어 이름 (주 원인 우선순위 순서, complaint_taxonomy.md와 같음)
LABEL_KO = {
    "NOT_RECEIVED": "미수령",
    "WRONG_MISSING": "오배송·누락",
    "DAMAGED": "파손·불량",
    "NOT_AS_DESCRIBED": "설명 불일치",
    "LOW_QUALITY": "품질 불만",
    "SHIPPING_COST": "배송비·수령 불편",
    "DELAY": "배송 지연",
    "SERVICE": "응대·환불",
    "OTHER": "기타",
    "UNCLEAR": "판단 불가",
    "NO_COMPLAINT": "불만 없음",
}
LABELS = list(LABEL_KO)

# 개선 주체 묶음 (Q1과 같음)
OWNER_OF_LABEL = {
    "NOT_RECEIVED": "물류", "DELAY": "물류",
    "WRONG_MISSING": "판매자 출고",
    "DAMAGED": "상품", "NOT_AS_DESCRIBED": "상품", "LOW_QUALITY": "상품",
    "SERVICE": "판매자 응대",
    "SHIPPING_COST": "플랫폼 정책",
    "OTHER": "기타", "UNCLEAR": "기타",
    "NO_COMPLAINT": "불만 없음",
}
OWNER_ORDER = ["물류", "판매자 출고", "상품", "판매자 응대", "플랫폼 정책", "기타", "불만 없음"]
NOT_CLASSIFIED = "분류 대상 아님"  # 4~5점이거나 텍스트가 없어 LLM 분류를 하지 않은 리뷰

# 판매자 통제 가능 불만 유형 (Q4)
SELLER_CONTROLLABLE = ["WRONG_MISSING", "DAMAGED", "NOT_AS_DESCRIBED", "LOW_QUALITY", "SERVICE"]

# 개선 주체별 고정 색 (Q1 노트북 차트와 같음), 경고색
OWNER_COLORS = {
    "물류": "#d62728", "판매자 출고": "#ff7f0e", "상품": "#1f77b4", "판매자 응대": "#9467bd",
    "플랫폼 정책": "#8c564b", "기타": "#7f7f7f", "불만 없음": "#2ca02c", NOT_CLASSIFIED: "#d9d9d9",
}
WARNING_COLORS = {"저평점·지연(강)": "#cb181d", "저평점·지연(약)": "#fc9272", "정상": "#bdbdbd"}

# 지연 구간: delay_days(예상 배송일 → 고객 수령일, 날짜 단위) 기준 (Q2와 같음)
DELAY_BUCKETS = [
    (-math.inf, -7, "7일 이상 빠름"),
    (-6, -1, "1~6일 빠름"),
    (0, 0, "예상일 당일"),
    (1, 3, "1~3일 지연"),
    (4, 7, "4~7일 지연"),
    (8, 14, "8~14일 지연"),
    (15, math.inf, "15일 이상 지연"),
]
NO_DELIVERY_METRIC = "배송 지표 없음"


def delay_bucket(delay_days, exclude_delivery_metrics) -> str:
    """지연 일수를 Q2와 같은 구간 이름으로 바꾼다. 배송 지표 대상이 아니면 '배송 지표 없음'."""
    if exclude_delivery_metrics == 1 or delay_days is None or (isinstance(delay_days, float) and math.isnan(delay_days)):
        return NO_DELIVERY_METRIC
    for low, high, name in DELAY_BUCKETS:
        if low <= delay_days <= high:
            return name
    raise ValueError(f"구간에 속하지 않는 지연 일수: {delay_days}")


def delay_bucket_order(name: str) -> int:
    """지연 구간 정렬 순서(1~7, 배송 지표 없음은 8)."""
    names = [n for _, _, n in DELAY_BUCKETS]
    return names.index(name) + 1 if name in names else len(names) + 1
