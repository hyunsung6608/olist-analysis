-- Q2-3. 고객이 인식한 지연(DELAY 라벨) vs 실제 지연(is_late)
-- 대상: 배송 지표 대상 주문 중 대표 리뷰가 LLM 분류 대상인 주문
-- perspective = 'DELAY 불만 기준': DELAY 라벨이 붙은 주문 중 실제 지연 / 제때 수령 비율
-- perspective = '실제 지연 기준': 실제로 지연된 주문 중 리뷰에서 DELAY·NOT_RECEIVED를 언급한 비율
--   (지연됐지만 리뷰 작성 시점에 아직 못 받아 NOT_RECEIVED로 쓴 경우가 있어 함께 본다)
WITH base AS (
    SELECT o.is_late, r.DELAY, r.NOT_RECEIVED
    FROM v_orders o
    JOIN v_order_reviews r ON r.order_id = o.order_id
    WHERE o.exclude_delivery_metrics = 0 AND r.is_classified = 1
)
SELECT
    'DELAY 불만 기준'         AS perspective,
    SUM(DELAY = 1)            AS n_base,
    AVG(is_late)              AS share_a,     -- 실제로 지연된 비율
    AVG(1 - is_late)          AS share_b,     -- 제때(예상일 이내) 받은 비율
    NULL                      AS share_c
FROM base
WHERE DELAY = 1
UNION ALL
SELECT
    '실제 지연 기준',
    COUNT(*),
    AVG(DELAY),                               -- DELAY 언급 비율
    AVG(NOT_RECEIVED),                        -- NOT_RECEIVED 언급 비율
    AVG(GREATEST(DELAY, NOT_RECEIVED))        -- 둘 중 하나라도 언급한 비율
FROM base
WHERE is_late = 1;
