-- Q4-4. 여러 판매자 주문 가설 검증 (Q2 발견 5번: 판매자가 여러 명인 주문은 지연과 별개로 저평점 위험이 크다)
-- 대상: 리뷰가 있고 주문 상품이 있는 주문
-- 그룹: '판매자 1명·상품 1개' / '판매자 1명·상품 2개 이상'(같은 판매자의 여러 상품, 비교군) / '판매자 2명 이상'
-- 지표: 신뢰구간을 계산할 수 있게 비율 대신 건수를 낸다(비율은 노트북에서 계산)
--   n_low: 1~2점 주문 / n_late: 지연 주문(분모 n_delivery_base = 배송 지표 대상 주문)
--   n_<유형>: 해당 유형이 붙은 주문 수. 분모를 n_orders로 하면 전체 주문 대비 비율(분류되지 않은 주문은 0),
--             n_classified로 하면 분류된 주문 중 비율(불만 구성 비교용)
WITH ord AS (
    SELECT
        CASE WHEN o.n_sellers >= 2 THEN 3 WHEN o.n_items >= 2 THEN 2 ELSE 1 END AS grp_ord,
        o.exclude_delivery_metrics, o.is_late, r.review_score, r.is_classified,
        COALESCE(r.WRONG_MISSING, 0) AS wm, COALESCE(r.NOT_RECEIVED, 0) AS nr, COALESCE(r.DELAY, 0) AS dl,
        COALESCE(r.DAMAGED, 0) AS dmg, COALESCE(r.NOT_AS_DESCRIBED, 0) AS nad, COALESCE(r.LOW_QUALITY, 0) AS lq,
        COALESCE(r.SERVICE, 0) AS svc
    FROM v_orders o
    JOIN v_order_reviews r ON r.order_id = o.order_id
    WHERE o.n_items >= 1
)
SELECT
    grp_ord,
    ELT(grp_ord, '판매자 1명·상품 1개', '판매자 1명·상품 2개 이상', '판매자 2명 이상') AS grp,
    COUNT(*)                                  AS n_orders,
    SUM(review_score <= 2)                    AS n_low,
    SUM(exclude_delivery_metrics = 0)         AS n_delivery_base,
    SUM(exclude_delivery_metrics = 0 AND is_late = 1) AS n_late,
    SUM(is_classified)                        AS n_classified,
    SUM(wm) AS n_WRONG_MISSING, SUM(nr) AS n_NOT_RECEIVED, SUM(dl) AS n_DELAY, SUM(dmg) AS n_DAMAGED,
    SUM(nad) AS n_NOT_AS_DESCRIBED, SUM(lq) AS n_LOW_QUALITY, SUM(svc) AS n_SERVICE
FROM ord
GROUP BY grp_ord
ORDER BY grp_ord;
