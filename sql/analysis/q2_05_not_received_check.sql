-- Q2-4. NOT_RECEIVED 라벨 교차 검증: 리뷰를 쓴 시점에 정말 아직 못 받았는가?
-- 대상: 대표 리뷰가 LLM 분류 대상인 모든 주문(배송 지표 제외 여부와 무관, 미수령 주문은 수령일이 없을 수 있음)
-- 비교: NOT_RECEIVED 라벨 리뷰 vs NOT_RECEIVED가 아닌 분류 리뷰
-- created_before_delivery: 리뷰 요청 발송일(review_creation_date, 날짜) < 고객 수령일(날짜)
-- answered_before_delivery: 리뷰 작성 시각(review_answer_timestamp) < 고객 수령 시각
-- 수령일이 없는 주문(미배송·취소 등)은 비율 계산에서 빼고 n_no_delivery_date로 따로 센다.
SELECT
    CASE WHEN r.NOT_RECEIVED = 1 THEN 'NOT_RECEIVED 라벨' ELSE 'NOT_RECEIVED 아님 (비교 기준)' END AS grp,
    COUNT(*)                                                     AS n_reviews,
    SUM(o.order_delivered_customer_date IS NULL)                 AS n_no_delivery_date,
    SUM(o.order_delivered_customer_date IS NOT NULL)             AS n_with_delivery_date,
    AVG(CASE WHEN o.order_delivered_customer_date IS NULL THEN NULL
             WHEN DATE(r.review_creation_date) < DATE(o.order_delivered_customer_date) THEN 1 ELSE 0 END)
                                                                 AS created_before_delivery,
    AVG(CASE WHEN o.order_delivered_customer_date IS NULL THEN NULL
             WHEN r.review_answer_timestamp < o.order_delivered_customer_date THEN 1 ELSE 0 END)
                                                                 AS answered_before_delivery,
    AVG(o.order_status = 'delivered')                            AS delivered_status_share
FROM v_order_reviews r
JOIN v_orders o ON o.order_id = r.order_id
WHERE r.is_classified = 1
GROUP BY grp
ORDER BY grp DESC;
