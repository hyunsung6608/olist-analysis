-- Q1-5b. unavailable·canceled 주문 리뷰 중 NOT_RECEIVED가 없는 리뷰에 붙은 라벨
-- LLM이 미수령으로 보지 않았을 때 어떤 유형(주 원인 기준)으로 분류했는지 본다.
-- 대표 주문: 구매 시각이 가장 이른 주문 1건 (q1_04와 같은 기준)
WITH review_order AS (
    SELECT review_id, order_status
    FROM (
        SELECT r.review_id, o.order_status,
               ROW_NUMBER() OVER (PARTITION BY r.review_id ORDER BY o.order_purchase_timestamp, o.order_id) AS rn
        FROM order_reviews r
        JOIN orders o ON o.order_id = r.order_id
        WHERE r.review_id IN (SELECT review_id FROM review_complaint_labels)
    ) x
    WHERE rn = 1
),
target AS (
    SELECT l.*, ro.order_status
    FROM review_complaint_labels l
    JOIN review_order ro ON ro.review_id = l.review_id
    WHERE ro.order_status IN ('unavailable', 'canceled') AND l.NOT_RECEIVED = 0
)
SELECT
    order_status,
    primary_label,
    COUNT(*)                                                         AS n_reviews,
    COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY order_status)        AS share_in_status,
    SUM(SERVICE)                                                     AS n_with_service,
    SUM(DELAY)                                                       AS n_with_delay
FROM target
GROUP BY order_status, primary_label
ORDER BY order_status DESC, n_reviews DESC;
