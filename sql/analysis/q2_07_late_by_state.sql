-- Q2-6. 고객 주(state)별 지연율 (Q5 개선안 참고용)
-- 대상: 배송 지표 대상 주문, 주문이 300건 이상인 주만
-- promised_days: 고객에게 약속한 배송 기간(구매 → 예상 배송일) 평균. 약속 기간이 긴데도 지연이 많은 주는 물류 개선 우선순위가 높다.
SELECT
    customer_state,
    COUNT(*)                     AS n_orders,
    AVG(is_late)                 AS late_rate,
    AVG(delivery_days)           AS avg_delivery_days,
    AVG(TIMESTAMPDIFF(SECOND, order_purchase_timestamp, order_estimated_delivery_date) / 86400) AS avg_promised_days
FROM v_orders
WHERE exclude_delivery_metrics = 0
GROUP BY customer_state
HAVING COUNT(*) >= 300
ORDER BY late_rate DESC;
