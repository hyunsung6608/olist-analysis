-- Q4-1. 판매자별 불만 지표 (판매자가 1명인 주문만)
-- 대상: 리뷰가 있는 주문 중 판매자가 1명인 주문 (배송 지표 제외 여부와 무관). 여러 판매자 주문은 책임 판매자를 정할 수 없어 뺀다.
-- 지표 (분모는 판매자의 전체 주문, 분류되지 않은 주문(4~5점·텍스트 없음)은 해당 불만 없음으로 본다)
--   low_rate          1~2점 비율
--   late_rate         지연율 (배송 지표 대상 주문 n_delivery_base 기준)
--   seller_ctrl_rate  판매자 통제 가능 불만 주문 비율: WRONG_MISSING·DAMAGED·NOT_AS_DESCRIBED·LOW_QUALITY·SERVICE 중 하나라도 있는 주문
--   logistics_rate    물류 불만 주문 비율: NOT_RECEIVED·DELAY 중 하나라도 있는 주문
--   n_<유형>          판매자 통제 가능 유형별 주문 수 (주요 불만 유형을 고르는 데 쓴다)
-- 베이지안 보정과 순위는 노트북에서 한다.
WITH single_seller AS (
    SELECT order_id, MIN(seller_id) AS seller_id
    FROM order_items
    GROUP BY order_id
    HAVING COUNT(DISTINCT seller_id) = 1
),
ord AS (
    SELECT
        s.seller_id,
        o.order_id,
        o.exclude_delivery_metrics,
        o.is_late,
        r.review_score,
        r.is_classified,
        COALESCE(r.WRONG_MISSING, 0) AS wm, COALESCE(r.DAMAGED, 0) AS dmg, COALESCE(r.NOT_AS_DESCRIBED, 0) AS nad,
        COALESCE(r.LOW_QUALITY, 0) AS lq, COALESCE(r.SERVICE, 0) AS svc,
        COALESCE(GREATEST(r.WRONG_MISSING, r.DAMAGED, r.NOT_AS_DESCRIBED, r.LOW_QUALITY, r.SERVICE), 0) AS seller_ctrl,
        COALESCE(GREATEST(r.NOT_RECEIVED, r.DELAY), 0) AS logistics
    FROM single_seller s
    JOIN v_orders o ON o.order_id = s.order_id
    JOIN v_order_reviews r ON r.order_id = s.order_id
)
SELECT
    ord.seller_id,
    se.seller_state,
    COUNT(*)                                                        AS n_orders,
    SUM(review_score <= 2)                                          AS n_low,
    AVG(review_score <= 2)                                          AS low_rate,
    SUM(exclude_delivery_metrics = 0)                               AS n_delivery_base,
    AVG(CASE WHEN exclude_delivery_metrics = 0 THEN is_late END)    AS late_rate,
    SUM(is_classified)                                              AS n_classified,
    SUM(seller_ctrl)                                                AS n_seller_ctrl,
    AVG(seller_ctrl)                                                AS seller_ctrl_rate,
    SUM(logistics)                                                  AS n_logistics,
    AVG(logistics)                                                  AS logistics_rate,
    SUM(wm) AS n_WRONG_MISSING, SUM(dmg) AS n_DAMAGED, SUM(nad) AS n_NOT_AS_DESCRIBED, SUM(lq) AS n_LOW_QUALITY, SUM(svc) AS n_SERVICE
FROM ord
JOIN sellers se ON se.seller_id = ord.seller_id
GROUP BY ord.seller_id, se.seller_state
ORDER BY n_orders DESC;
