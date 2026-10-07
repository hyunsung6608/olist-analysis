-- Q3-1. 첫 주문 월별 코호트 재구매율
-- 대상: 첫 주문 후 180일을 관찰할 수 있는 고객 (관찰 종료일 = 하루 주문 10건 이상인 마지막 날, q3_01과 같은 기준)
-- 코호트: 첫 주문 월. 30·90·180일 누적 재구매율(첫 주문 다음 날 이후 주문 기준)
-- full_month: 코호트 월 전체가 분석 대상이면 1. 마지막 코호트 월은 관찰 기준일 이전 날짜만 포함되어 일부만 들어간다.
WITH obs AS (
    SELECT MAX(d) AS end_date
    FROM (SELECT DATE(order_purchase_timestamp) AS d, COUNT(*) AS n FROM orders GROUP BY d) t
    WHERE n >= 10
),
cohort AS (
    SELECT
        DATE_FORMAT(c.first_purchase_date, '%Y-%m') AS cohort_month,
        c.days_to_first_repurchase,
        LAST_DAY(c.first_purchase_date) + INTERVAL 180 DAY <= o.end_date AS full_month
    FROM v_customer_orders c
    CROSS JOIN obs o
    WHERE c.order_seq = 1
      AND c.first_purchase_date + INTERVAL 180 DAY <= o.end_date
)
SELECT
    cohort_month,
    COUNT(*)                                                 AS n_customers,
    MIN(full_month)                                          AS full_month,
    AVG(COALESCE(days_to_first_repurchase <= 30, 0))         AS repurchase_30d,
    AVG(COALESCE(days_to_first_repurchase <= 90, 0))         AS repurchase_90d,
    AVG(COALESCE(days_to_first_repurchase <= 180, 0))        AS repurchase_180d
FROM cohort
GROUP BY cohort_month
ORDER BY cohort_month;
