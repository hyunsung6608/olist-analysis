-- Q1-4 보조. 주문 월별 실제 배송 지연율 (월별 물류 불만 비중과 비교용)
-- v_orders의 배송 지표 기준(exclude_delivery_metrics = 0)으로 주문 월별 지연 주문 비율을 구한다.
-- 리뷰 불만(텍스트 기반)과 실제 배송 데이터가 같은 방향으로 움직이는지 교차 확인하는 용도. 본격적인 분석은 Q2에서 한다.
SELECT
    DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS order_month,
    COUNT(*)                                       AS n_delivered_orders,
    SUM(is_late)                                   AS n_late,
    AVG(is_late)                                   AS late_rate
FROM v_orders
WHERE exclude_delivery_metrics = 0
GROUP BY order_month
ORDER BY order_month;
