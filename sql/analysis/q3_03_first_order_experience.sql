-- Q3-2. 첫 주문 경험별 180일 재구매율
-- 대상: 첫 주문 후 180일을 관찰할 수 있는 고객 (q3_01과 같은 기준)
-- 첫 주문 경험 차원(dimension):
--   지연 여부 / 지연 구간(Q2와 같은 구간): 첫 주문이 배송 지표 대상(exclude_delivery_metrics = 0)인 경우만 값이 있고, 아니면 '배송 지표 없음'
--   리뷰 점수: 첫 주문의 대표 리뷰 점수(1~5점, 리뷰 없음)
--   주 원인 불만 유형: 첫 주문 리뷰가 LLM 분류 대상인 경우의 primary_label, 아니면 '분류 대상 아님'
--   판매자 수: 첫 주문의 판매자 수(0은 주문 상품이 없는 주문)
WITH obs AS (
    SELECT MAX(d) AS end_date
    FROM (SELECT DATE(order_purchase_timestamp) AS d, COUNT(*) AS n FROM orders GROUP BY d) t
    WHERE n >= 10
),
cust AS (
    SELECT
        c.customer_unique_id,
        COALESCE(c.days_to_first_repurchase <= 180, 0) AS repurchase_180d,
        CASE WHEN o.exclude_delivery_metrics = 1 THEN '배송 지표 없음'
             WHEN o.is_late = 1 THEN '지연' ELSE '제때' END AS late_group,
        CASE WHEN o.exclude_delivery_metrics = 1 THEN 8
             WHEN o.delay_days <= -7 THEN 1 WHEN o.delay_days <= -1 THEN 2 WHEN o.delay_days = 0 THEN 3
             WHEN o.delay_days <= 3 THEN 4 WHEN o.delay_days <= 7 THEN 5 WHEN o.delay_days <= 14 THEN 6 ELSE 7
        END AS bucket_ord,
        r.review_score,
        CASE WHEN r.is_classified = 1 THEN r.primary_label END AS primary_label,
        o.n_sellers
    FROM v_customer_orders c
    CROSS JOIN obs
    JOIN v_orders o ON o.order_id = c.order_id
    LEFT JOIN v_order_reviews r ON r.order_id = c.order_id
    WHERE c.order_seq = 1
      AND c.first_purchase_date + INTERVAL 180 DAY <= obs.end_date
),
dims AS (
    SELECT 1 AS dim_ord, '지연 여부' AS dimension UNION ALL SELECT 2, '지연 구간' UNION ALL SELECT 3, '리뷰 점수'
    UNION ALL SELECT 4, '주 원인 불만 유형' UNION ALL SELECT 5, '판매자 수'
),
long_dims AS (
    -- 고객 집합(cust)을 한 번만 계산하고 차원 목록과 교차 조인해 차원별 그룹을 정한다.
    SELECT
        d.dim_ord,
        d.dimension,
        CASE d.dim_ord
            WHEN 1 THEN FIELD(c.late_group, '제때', '지연', '배송 지표 없음')
            WHEN 2 THEN c.bucket_ord
            WHEN 3 THEN COALESCE(c.review_score, 6)
            WHEN 4 THEN COALESCE(FIELD(c.primary_label, 'NOT_RECEIVED', 'WRONG_MISSING', 'DAMAGED', 'NOT_AS_DESCRIBED',
                            'LOW_QUALITY', 'SHIPPING_COST', 'DELAY', 'SERVICE', 'OTHER', 'UNCLEAR', 'NO_COMPLAINT'), 12)
            ELSE LEAST(c.n_sellers, 3)
        END AS grp_ord,
        CASE d.dim_ord
            WHEN 1 THEN c.late_group
            WHEN 2 THEN ELT(c.bucket_ord, '7일 이상 빠름', '1~6일 빠름', '예상일 당일', '1~3일 지연', '4~7일 지연',
                            '8~14일 지연', '15일 이상 지연', '배송 지표 없음')
            WHEN 3 THEN CASE WHEN c.review_score IS NULL THEN '리뷰 없음' ELSE CONCAT(c.review_score, '점') END
            WHEN 4 THEN COALESCE(c.primary_label, '분류 대상 아님')
            ELSE CASE WHEN c.n_sellers = 0 THEN '0 (상품 없음)' WHEN c.n_sellers >= 3 THEN '3명 이상'
                      ELSE CONCAT(c.n_sellers, '명') END
        END AS grp,
        c.repurchase_180d
    FROM cust c
    CROSS JOIN dims d
)
SELECT
    dim_ord,
    dimension,
    grp_ord,
    grp,
    COUNT(*)              AS n_customers,
    SUM(repurchase_180d)  AS n_repurchase_180d,
    AVG(repurchase_180d)  AS repurchase_180d
FROM long_dims
GROUP BY dim_ord, dimension, grp_ord, grp
ORDER BY dim_ord, grp_ord;
