-- Q2-1. 지연 구간별 주문 수와 평점 지표 (주문 단위)
-- 대상: v_orders 중 배송 지표 대상 주문(exclude_delivery_metrics = 0), 평점은 v_order_reviews의 주문당 대표 리뷰
-- 지연 구간: delay_days(예상 배송일 → 고객 수령일, 날짜 단위, 양수면 지연) 기준 7개 구간
-- 평점 지표(평균 평점, 1~2점 비율, 5점 비율)는 리뷰가 있는 주문 기준이다.
WITH base AS (
    SELECT
        o.order_id,
        o.delay_days,
        CASE
            WHEN o.delay_days <= -7 THEN 1 WHEN o.delay_days <= -1 THEN 2 WHEN o.delay_days = 0 THEN 3
            WHEN o.delay_days <= 3 THEN 4 WHEN o.delay_days <= 7 THEN 5 WHEN o.delay_days <= 14 THEN 6 ELSE 7
        END AS bucket_ord,
        r.review_score
    FROM v_orders o
    LEFT JOIN v_order_reviews r ON r.order_id = o.order_id
    WHERE o.exclude_delivery_metrics = 0
)
SELECT
    bucket_ord,
    ELT(bucket_ord, '7일 이상 빠름', '1~6일 빠름', '예상일 당일', '1~3일 지연', '4~7일 지연', '8~14일 지연', '15일 이상 지연')
                                                         AS delay_bucket,
    COUNT(*)                                             AS n_orders,
    COUNT(review_score)                                  AS n_reviewed,
    AVG(review_score)                                    AS avg_score,
    AVG(CASE WHEN review_score IS NULL THEN NULL WHEN review_score <= 2 THEN 1 ELSE 0 END) AS low_score_share,
    AVG(CASE WHEN review_score IS NULL THEN NULL WHEN review_score = 5 THEN 1 ELSE 0 END)  AS five_score_share
FROM base
GROUP BY bucket_ord
ORDER BY bucket_ord;
