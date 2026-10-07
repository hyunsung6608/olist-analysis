-- Q2 통계 분석용 주문 단위 데이터 (Mann-Whitney 검정, 비율 검정, 로지스틱 회귀)
-- 대상: 배송 지표 대상 주문 중 리뷰가 있는 주문
-- 종속변수 후보: review_score, low_score(1~2점이면 1)
-- 설명·통제 변수: is_late, delay_days, distance_km(주문 상품별 판매자 → 고객 거리 평균, 없으면 NULL),
--   freight_value(배송비 합계), n_items(상품 수), n_sellers(판매자 수), customer_state
WITH order_distance AS (
    SELECT order_id, AVG(distance_km) AS distance_km
    FROM v_order_items_enriched
    GROUP BY order_id
)
SELECT
    o.order_id,
    r.review_score,
    CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END AS low_score,
    o.is_late,
    o.delay_days,
    d.distance_km,
    o.freight_value,
    o.n_items,
    o.n_sellers,
    o.customer_state
FROM v_orders o
JOIN v_order_reviews r ON r.order_id = o.order_id
LEFT JOIN order_distance d ON d.order_id = o.order_id
WHERE o.exclude_delivery_metrics = 0;
