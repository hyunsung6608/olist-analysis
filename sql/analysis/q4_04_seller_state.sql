-- Q4-3b. 판매자 주별 불만 지표
-- 대상: 리뷰가 있는 주문 중 판매자가 1명인 주문 (q4_01과 같은 기준)
-- 지표: 주문 수, 판매자 수, 지연율(배송 지표 대상 주문 기준), 판매자 통제 가능 불만 비율, 1~2점 비율
WITH single_seller AS (
    SELECT order_id, MIN(seller_id) AS seller_id
    FROM order_items
    GROUP BY order_id
    HAVING COUNT(DISTINCT seller_id) = 1
)
SELECT
    se.seller_state,
    COUNT(*)                                                                         AS n_orders,
    COUNT(DISTINCT s.seller_id)                                                      AS n_sellers,
    AVG(r.review_score <= 2)                                                         AS low_rate,
    AVG(CASE WHEN o.exclude_delivery_metrics = 0 THEN o.is_late END)                 AS late_rate,
    AVG(COALESCE(GREATEST(r.WRONG_MISSING, r.DAMAGED, r.NOT_AS_DESCRIBED, r.LOW_QUALITY, r.SERVICE), 0))
                                                                                     AS seller_ctrl_rate
FROM single_seller s
JOIN sellers se ON se.seller_id = s.seller_id
JOIN v_orders o ON o.order_id = s.order_id
JOIN v_order_reviews r ON r.order_id = s.order_id
GROUP BY se.seller_state
ORDER BY n_orders DESC;
