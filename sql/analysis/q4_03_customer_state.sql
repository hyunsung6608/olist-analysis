-- Q4-3a. 고객 주별 불만 지표
-- 대상: 리뷰가 있는 주문 (판매자 수와 무관)
-- 지표: 주문 수, 1~2점 비율, 지연율(배송 지표 대상 주문 기준), 물류 불만 비율(NOT_RECEIVED·DELAY가 있는 주문 / 전체 주문)
SELECT
    o.customer_state,
    COUNT(*)                                                              AS n_orders,
    AVG(r.review_score <= 2)                                              AS low_rate,
    SUM(o.exclude_delivery_metrics = 0)                                   AS n_delivery_base,
    AVG(CASE WHEN o.exclude_delivery_metrics = 0 THEN o.is_late END)      AS late_rate,
    AVG(COALESCE(GREATEST(r.NOT_RECEIVED, r.DELAY), 0))                   AS logistics_rate
FROM v_orders o
JOIN v_order_reviews r ON r.order_id = o.order_id
GROUP BY o.customer_state
ORDER BY n_orders DESC;
