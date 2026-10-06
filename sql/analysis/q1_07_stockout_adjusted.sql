-- Q1-5c. 주문 상태로 NOT_RECEIVED를 보완했을 때 비중 변화
-- 보완 규칙: 대표 주문 상태가 unavailable·canceled이고 NO_COMPLAINT가 아닌 리뷰는 미수령(NOT_RECEIVED)으로 간주한다.
--   (불만 없음 리뷰는 고객이 직접 취소한 경우 등이 있어 바꾸지 않음)
--   주 원인은 NOT_RECEIVED가 우선순위 1위이므로 보완된 리뷰의 주 원인은 NOT_RECEIVED가 된다.
-- 비교: before(LLM 결과) / after_both(unavailable+canceled 보완) / after_unavailable(unavailable만 보완, 민감도 확인용)
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
base AS (
    SELECT
        l.NOT_RECEIVED,
        l.DELAY,
        l.primary_label,
        CASE WHEN l.NOT_RECEIVED = 1
                  OR (ro.order_status IN ('unavailable', 'canceled') AND l.NO_COMPLAINT = 0) THEN 1 ELSE 0 END AS nr_both,
        CASE WHEN l.NOT_RECEIVED = 1
                  OR (ro.order_status = 'unavailable' AND l.NO_COMPLAINT = 0) THEN 1 ELSE 0 END AS nr_unavail
    FROM review_complaint_labels l
    JOIN review_order ro ON ro.review_id = l.review_id
)
SELECT 1 AS ord, 'NOT_RECEIVED 다중 라벨 비율' AS metric,
       AVG(NOT_RECEIVED) AS before_adj, AVG(nr_both) AS after_both, AVG(nr_unavail) AS after_unavailable
FROM base
UNION ALL
SELECT 2, 'NOT_RECEIVED 주 원인 비율',
       AVG(primary_label = 'NOT_RECEIVED'), AVG(nr_both), AVG(nr_unavail)
FROM base
UNION ALL
SELECT 3, '물류(NOT_RECEIVED·DELAY) 다중 라벨 비율',
       AVG(GREATEST(NOT_RECEIVED, DELAY)), AVG(GREATEST(nr_both, DELAY)), AVG(GREATEST(nr_unavail, DELAY))
FROM base
UNION ALL
SELECT 4, '물류 주 원인 비율',
       AVG(primary_label IN ('NOT_RECEIVED', 'DELAY')),
       AVG(nr_both = 1 OR primary_label IN ('NOT_RECEIVED', 'DELAY')),
       AVG(nr_unavail = 1 OR primary_label IN ('NOT_RECEIVED', 'DELAY'))
FROM base
UNION ALL
SELECT 5, '보완으로 NOT_RECEIVED가 새로 붙은 리뷰 수',
       0, SUM(nr_both) - SUM(NOT_RECEIVED), SUM(nr_unavail) - SUM(NOT_RECEIVED)
FROM base
ORDER BY ord;
