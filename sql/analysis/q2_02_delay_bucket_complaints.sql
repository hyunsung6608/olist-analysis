-- Q2-2. 지연 구간별 불만 구성 (분류된 리뷰가 있는 주문 기준)
-- 대상: 배송 지표 대상 주문 중 대표 리뷰가 LLM 분류 대상(텍스트 있는 1~3점)인 주문
-- 개선 주체 비중은 주 원인(primary_label) 기준이며 Q1과 같은 묶음을 쓴다(합 100%).
-- delay_rate / not_received_rate: DELAY·NOT_RECEIVED 라벨이 붙은 비율(다중 라벨 기준)
WITH base AS (
    SELECT
        CASE
            WHEN o.delay_days <= -7 THEN 1 WHEN o.delay_days <= -1 THEN 2 WHEN o.delay_days = 0 THEN 3
            WHEN o.delay_days <= 3 THEN 4 WHEN o.delay_days <= 7 THEN 5 WHEN o.delay_days <= 14 THEN 6 ELSE 7
        END AS bucket_ord,
        r.DELAY,
        r.NOT_RECEIVED,
        CASE
            WHEN r.primary_label IN ('NOT_RECEIVED', 'DELAY') THEN '물류'
            WHEN r.primary_label = 'WRONG_MISSING' THEN '판매자 출고'
            WHEN r.primary_label IN ('DAMAGED', 'NOT_AS_DESCRIBED', 'LOW_QUALITY') THEN '상품'
            WHEN r.primary_label = 'SERVICE' THEN '판매자 응대'
            WHEN r.primary_label = 'SHIPPING_COST' THEN '플랫폼 정책'
            WHEN r.primary_label IN ('OTHER', 'UNCLEAR') THEN '기타'
            ELSE '불만 없음'
        END AS owner
    FROM v_orders o
    JOIN v_order_reviews r ON r.order_id = o.order_id
    WHERE o.exclude_delivery_metrics = 0 AND r.is_classified = 1
)
SELECT
    bucket_ord,
    ELT(bucket_ord, '7일 이상 빠름', '1~6일 빠름', '예상일 당일', '1~3일 지연', '4~7일 지연', '8~14일 지연', '15일 이상 지연')
                                     AS delay_bucket,
    COUNT(*)                         AS n_classified,
    AVG(owner = '물류')               AS share_logistics,
    AVG(owner = '판매자 출고')         AS share_seller_fulfillment,
    AVG(owner = '상품')               AS share_product,
    AVG(owner = '판매자 응대')         AS share_seller_service,
    AVG(owner = '플랫폼 정책')         AS share_platform,
    AVG(owner = '기타')               AS share_other,
    AVG(owner = '불만 없음')           AS share_no_complaint,
    AVG(DELAY)                       AS delay_rate,
    AVG(NOT_RECEIVED)                AS not_received_rate
FROM base
GROUP BY bucket_ord
ORDER BY bucket_ord;
