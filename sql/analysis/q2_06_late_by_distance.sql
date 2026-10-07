-- Q2-5. 판매자 → 고객 거리 구간별 지연율 (Q5 개선안 참고용)
-- 대상: 배송 지표 대상 주문. 주문의 거리는 주문 상품별 판매자 → 고객 직선 거리(v_order_items_enriched.distance_km)의 평균
-- 좌표가 없어 거리를 계산할 수 없는 주문은 '거리 없음'으로 따로 센다.
WITH order_distance AS (
    SELECT order_id, AVG(distance_km) AS distance_km
    FROM v_order_items_enriched
    GROUP BY order_id
),
base AS (
    SELECT
        o.is_late,
        o.delivery_days,
        CASE
            WHEN d.distance_km IS NULL THEN 7
            WHEN d.distance_km < 100 THEN 1 WHEN d.distance_km < 300 THEN 2 WHEN d.distance_km < 600 THEN 3
            WHEN d.distance_km < 1000 THEN 4 WHEN d.distance_km < 2000 THEN 5 ELSE 6
        END AS bucket_ord
    FROM v_orders o
    LEFT JOIN order_distance d ON d.order_id = o.order_id
    WHERE o.exclude_delivery_metrics = 0
)
SELECT
    bucket_ord,
    ELT(bucket_ord, '100km 미만', '100~300km', '300~600km', '600~1,000km', '1,000~2,000km', '2,000km 이상', '거리 없음')
                       AS distance_bucket,
    COUNT(*)           AS n_orders,
    AVG(is_late)       AS late_rate,
    AVG(delivery_days) AS avg_delivery_days
FROM base
GROUP BY bucket_ord
ORDER BY bucket_ord;
