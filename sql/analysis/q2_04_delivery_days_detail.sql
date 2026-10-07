-- Q2-3 보조. 배송 소요 일수와 약속 배송 기간 (주문 단위 상세, 분포 비교용)
-- 대상: 배송 지표 대상 주문 전체(exclude_delivery_metrics = 0)
-- delivery_days: 구매 시각 → 고객 수령 일수 / promised_days: 구매 시각 → 예상 배송일 일수(고객에게 약속한 기간)
-- grp: 'DELAY 불만 + 제때 수령', 'DELAY 불만 + 실제 지연', '그 외'(분류 리뷰가 없거나 DELAY가 없는 주문)
-- 분포 요약(중앙값·분위수)은 노트북에서 계산한다.
SELECT
    o.order_id,
    o.is_late,
    o.delivery_days,
    TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_estimated_delivery_date) / 86400 AS promised_days,
    CASE
        WHEN r.DELAY = 1 AND o.is_late = 0 THEN 'DELAY 불만 + 제때 수령'
        WHEN r.DELAY = 1 AND o.is_late = 1 THEN 'DELAY 불만 + 실제 지연'
        ELSE '그 외'
    END AS grp
FROM v_orders o
LEFT JOIN v_order_reviews r ON r.order_id = o.order_id
WHERE o.exclude_delivery_metrics = 0;
