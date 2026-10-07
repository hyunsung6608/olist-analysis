-- Q3 통계 분석용 고객 단위 데이터 (비율 검정, 로지스틱 회귀, 누적 재구매 곡선)
-- 대상: 첫 주문 후 180일을 관찰할 수 있는 고객 (q3_01과 같은 기준). 한 행 = 고객 1명, 첫 주문의 경험 변수를 붙인다.
-- first_is_late / first_delay_days: 첫 주문이 배송 지표 대상이 아니면 NULL
-- first_review_score: 첫 주문 대표 리뷰 점수(없으면 NULL)
-- days_to_first_repurchase: 첫 주문 날짜부터 첫 재구매 날짜까지 일수(재구매가 없으면 NULL). 180일 초과 재구매도 그대로 둔다.
WITH obs AS (
    SELECT MAX(d) AS end_date
    FROM (SELECT DATE(order_purchase_timestamp) AS d, COUNT(*) AS n FROM orders GROUP BY d) t
    WHERE n >= 10
)
SELECT
    c.customer_unique_id,
    c.order_id                                         AS first_order_id,
    c.first_purchase_date,
    DATE_FORMAT(c.first_purchase_date, '%Y-%m')        AS cohort_month,
    c.days_to_first_repurchase,
    COALESCE(c.days_to_first_repurchase <= 180, 0)     AS repurchase_180d,
    o.order_status                                     AS first_order_status,
    o.exclude_delivery_metrics,
    CASE WHEN o.exclude_delivery_metrics = 0 THEN o.is_late END    AS first_is_late,
    CASE WHEN o.exclude_delivery_metrics = 0 THEN o.delay_days END AS first_delay_days,
    r.review_score                                     AS first_review_score,
    CASE WHEN r.is_classified = 1 THEN r.primary_label END AS first_primary_label,
    o.items_value,
    o.freight_value,
    o.n_items,
    o.n_sellers,
    o.customer_state
FROM v_customer_orders c
CROSS JOIN obs
JOIN v_orders o ON o.order_id = c.order_id
LEFT JOIN v_order_reviews r ON r.order_id = c.order_id
WHERE c.order_seq = 1
  AND c.first_purchase_date + INTERVAL 180 DAY <= obs.end_date;
