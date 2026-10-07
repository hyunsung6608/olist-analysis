-- Q3-0. 관찰 기간 설정: 첫 주문 후 180일을 모두 관찰할 수 있는 고객만 분석 대상으로 정한다.
-- 재구매 정의: 첫 주문 날짜 다음 날 이후의 주문 (v_customer_orders.days_to_first_repurchase)
-- 관찰 종료일을 두 가지로 계산해 비교한다.
--   (1) 실제 수집 종료일: 하루 주문이 10건 이상인 마지막 날. 2018-08-29 이후에는 주문이 거의 없어(9~10월 20건, 배송 완료 0건)
--       그 이후 기간의 재구매는 관찰할 수 없으므로 이 날짜를 분석 기준으로 쓴다.
--   (2) 데이터 마지막 주문일: MAX(order_purchase_timestamp). 문자 그대로의 기준(민감도 확인용)
-- 분석 대상: 첫 주문일 + 180일 ≤ 관찰 종료일. 결과 변수: 첫 주문 후 180일 안에 재구매했는지(30·90일도 함께)
WITH daily AS (
    SELECT DATE(order_purchase_timestamp) AS d, COUNT(*) AS n
    FROM orders
    GROUP BY d
),
ends AS (
    SELECT 1 AS ord, '실제 수집 종료일 (하루 10건 이상 마지막 날, 분석 기준)' AS end_rule, MAX(d) AS end_date FROM daily WHERE n >= 10
    UNION ALL
    SELECT 2, '데이터 마지막 주문일 (민감도 확인용)', MAX(d) FROM daily
),
customers_first AS (
    SELECT customer_unique_id, first_purchase_date, days_to_first_repurchase
    FROM v_customer_orders
    WHERE order_seq = 1
)
SELECT
    e.ord,
    e.end_rule,
    e.end_date,
    e.end_date - INTERVAL 180 DAY                                             AS last_first_purchase_date,
    COUNT(*)                                                                  AS n_customers_total,
    SUM(c.first_purchase_date + INTERVAL 180 DAY <= e.end_date)               AS n_included,
    SUM(c.first_purchase_date + INTERVAL 180 DAY > e.end_date)                AS n_excluded,
    AVG(CASE WHEN c.first_purchase_date + INTERVAL 180 DAY <= e.end_date
             THEN COALESCE(c.days_to_first_repurchase <= 30, 0) END)          AS repurchase_30d,
    AVG(CASE WHEN c.first_purchase_date + INTERVAL 180 DAY <= e.end_date
             THEN COALESCE(c.days_to_first_repurchase <= 90, 0) END)          AS repurchase_90d,
    AVG(CASE WHEN c.first_purchase_date + INTERVAL 180 DAY <= e.end_date
             THEN COALESCE(c.days_to_first_repurchase <= 180, 0) END)         AS repurchase_180d,
    AVG(c.days_to_first_repurchase IS NOT NULL)                               AS repurchase_ever_all_customers
FROM customers_first c
CROSS JOIN ends e
GROUP BY e.ord, e.end_rule, e.end_date
ORDER BY e.ord;
