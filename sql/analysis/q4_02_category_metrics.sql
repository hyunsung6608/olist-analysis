-- Q4-2. 카테고리별 불만 지표 (영문 카테고리, 주문 300건 이상)
-- 대상: 리뷰가 있는 주문. 한 주문에 카테고리가 여러 개면 카테고리마다 1건으로 센다(주문-카테고리 쌍 기준).
-- 지표: 주문 수, 1~2점 비율, 지연율(배송 지표 대상 주문 기준), 분류된 리뷰 수와 불만 유형별 비율(분류된 리뷰 중 해당 유형이 붙은 비율, 다중 라벨)
-- category = '(전체)' 행은 카테고리 구분 없이 전체 주문을 한 번씩만 센 비교 기준이다.
-- 전체 대비 두드러지게 높은 유형(lift)은 노트북에서 계산한다.
WITH order_cat AS (
    SELECT DISTINCT order_id, product_category_name_english AS category
    FROM v_order_items_enriched
),
ord AS (
    SELECT o.order_id, o.exclude_delivery_metrics, o.is_late, r.review_score, r.is_classified,
           r.NOT_RECEIVED, r.WRONG_MISSING, r.DAMAGED, r.NOT_AS_DESCRIBED, r.LOW_QUALITY, r.SHIPPING_COST,
           r.DELAY, r.SERVICE, r.OTHER, r.UNCLEAR, r.NO_COMPLAINT
    FROM v_orders o
    JOIN v_order_reviews r ON r.order_id = o.order_id
),
by_cat AS (
    SELECT c.category, ord.* FROM ord JOIN order_cat c ON c.order_id = ord.order_id
    UNION ALL
    SELECT '(전체)', ord.* FROM ord
)
SELECT
    category,
    COUNT(*)                                                        AS n_orders,
    AVG(review_score <= 2)                                          AS low_rate,
    AVG(CASE WHEN exclude_delivery_metrics = 0 THEN is_late END)    AS late_rate,
    SUM(is_classified)                                              AS n_classified,
    AVG(CASE WHEN is_classified = 1 THEN NOT_RECEIVED END)          AS NOT_RECEIVED,
    AVG(CASE WHEN is_classified = 1 THEN WRONG_MISSING END)         AS WRONG_MISSING,
    AVG(CASE WHEN is_classified = 1 THEN DAMAGED END)               AS DAMAGED,
    AVG(CASE WHEN is_classified = 1 THEN NOT_AS_DESCRIBED END)      AS NOT_AS_DESCRIBED,
    AVG(CASE WHEN is_classified = 1 THEN LOW_QUALITY END)           AS LOW_QUALITY,
    AVG(CASE WHEN is_classified = 1 THEN SHIPPING_COST END)         AS SHIPPING_COST,
    AVG(CASE WHEN is_classified = 1 THEN DELAY END)                 AS DELAY,
    AVG(CASE WHEN is_classified = 1 THEN SERVICE END)               AS SERVICE,
    AVG(CASE WHEN is_classified = 1 THEN OTHER END)                 AS OTHER,
    AVG(CASE WHEN is_classified = 1 THEN UNCLEAR END)               AS UNCLEAR,
    AVG(CASE WHEN is_classified = 1 THEN NO_COMPLAINT END)          AS NO_COMPLAINT
FROM by_cat
GROUP BY category
HAVING COUNT(*) >= 300
ORDER BY category = '(전체)' DESC, n_orders DESC;
