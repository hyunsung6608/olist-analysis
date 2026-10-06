-- Q1-5a. 주문 상태별 분류 리뷰 수와 NOT_RECEIVED 부여율
-- 결제 후 품절(unavailable)·취소(canceled) 주문의 리뷰에 LLM이 NOT_RECEIVED를 얼마나 붙였는지 본다.
-- 대표 주문: 한 리뷰가 여러 주문에 연결되면 구매 시각이 가장 이른 주문 1건 (q1_04와 같은 기준)
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
)
SELECT
    CASE WHEN ro.order_status IN ('unavailable', 'canceled') THEN ro.order_status ELSE '그 외' END AS status_group,
    COUNT(*)                          AS n_reviews,
    SUM(l.NOT_RECEIVED)               AS n_not_received,
    SUM(l.NOT_RECEIVED) / COUNT(*)    AS share_not_received,
    SUM(l.NO_COMPLAINT)               AS n_no_complaint
FROM review_complaint_labels l
JOIN review_order ro ON ro.review_id = l.review_id
GROUP BY status_group
ORDER BY FIELD(status_group, 'unavailable', 'canceled', '그 외');
