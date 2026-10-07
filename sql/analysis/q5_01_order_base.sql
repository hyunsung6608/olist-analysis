-- Q5. 개선안 효과 추정용 주문 단위 기준 데이터 (최근 12개월)
-- 기준 기간: 관찰 종료일(하루 주문 10건 이상인 마지막 날 = 2018-08-29, Q3와 같은 규칙) 이전 12개월에 구매한 주문
-- 대상: 기준 기간 주문 중 리뷰가 있는 주문 (1~2점 리뷰 수가 효과 지표이므로). 한 행 = 주문 1건
-- 주요 컬럼
--   low_score                  대표 리뷰가 1~2점이면 1
--   exclude_delivery_metrics / is_late / delay_days   배송 지표 (Q2와 같은 정의)
--   distance_km                주문 상품별 판매자 → 고객 직선 거리 평균 (Q2 회귀 변수)
--   is_first_order             고객의 첫 주문이면 1 (재구매 파급 효과 계산용)
--   seller_id                  판매자가 1명인 주문의 판매자 (여러 명이면 NULL)
--   categories                 주문 상품의 영문 카테고리 목록 ('|' 구분, 빈 카테고리는 '(미분류)')
--   is_classified, 유형 11개    LLM 분류 결과 (분류되지 않은 주문은 유형이 NULL)
WITH obs AS (
    SELECT MAX(d) AS end_date
    FROM (SELECT DATE(order_purchase_timestamp) AS d, COUNT(*) AS n FROM orders GROUP BY d) t
    WHERE n >= 10
),
order_extra AS (
    SELECT
        order_id,
        AVG(distance_km)                                                                     AS distance_km,
        CASE WHEN COUNT(DISTINCT seller_id) = 1 THEN MIN(seller_id) END                      AS seller_id,
        GROUP_CONCAT(DISTINCT product_category_name_english ORDER BY product_category_name_english SEPARATOR '|') AS categories
    FROM v_order_items_enriched
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.order_purchase_timestamp,
    o.customer_state,
    o.order_status,
    o.exclude_delivery_metrics,
    o.is_late,
    o.delay_days,
    o.freight_value,
    o.n_items,
    o.n_sellers,
    e.distance_km,
    e.seller_id,
    e.categories,
    co.is_first_order,
    r.review_score,
    CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END AS low_score,
    r.is_classified,
    r.NOT_RECEIVED, r.WRONG_MISSING, r.DAMAGED, r.NOT_AS_DESCRIBED, r.LOW_QUALITY, r.SHIPPING_COST,
    r.DELAY, r.SERVICE, r.OTHER, r.UNCLEAR, r.NO_COMPLAINT
FROM v_orders o
CROSS JOIN obs
JOIN v_order_reviews r ON r.order_id = o.order_id
JOIN v_customer_orders co ON co.order_id = o.order_id
LEFT JOIN order_extra e ON e.order_id = o.order_id
WHERE DATE(o.order_purchase_timestamp) > obs.end_date - INTERVAL 12 MONTH
  AND DATE(o.order_purchase_timestamp) <= obs.end_date;
