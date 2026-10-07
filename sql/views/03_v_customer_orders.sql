-- v_customer_orders: 고객별 주문 순서 (재구매·코호트 분석용)
-- 목적: 실제 고객(customer_unique_id) 기준으로 주문 순서와 재구매 여부, 다음 주문까지 기간을 계산한다.
-- 한 행: 주문 1건 (orders와 행 수가 같음). 모든 주문 상태를 포함하므로 필요하면 order_status로 거른다.
-- 주요 컬럼:
--   order_seq                 고객의 몇 번째 주문인지 (구매 시각 순, 1부터. 같은 시각이면 order_id 순)
--   is_first_order            첫 주문이면 1
--   customer_total_orders     이 고객의 전체 주문 수
--   has_repurchase            이 고객이 2건 이상 주문했으면 1 (같은 날 여러 건 주문도 포함, 고객 단위 값이 모든 주문 행에 반복됨)
--   days_to_next_order        다음 주문까지 일수 (소수 포함, 마지막 주문이면 NULL)
--   first_purchase_date       고객의 첫 주문 날짜 (날짜 단위)
--   has_repurchase_nextday    첫 주문 다음 날 이후(구매 날짜 기준 1일 이상 뒤)에 주문이 있으면 1 (재구매 정의, 같은 날 추가 주문은 제외)
--   days_to_first_repurchase  첫 주문 날짜부터 첫 재구매 날짜까지 일수 (정수, 재구매가 없으면 NULL)
--   재구매 관련 3개 컬럼은 고객 단위 값이 그 고객의 모든 주문 행에 반복된다.
CREATE OR REPLACE VIEW v_customer_orders AS
WITH base AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_status,
        o.order_purchase_timestamp,
        ROW_NUMBER() OVER w                                                        AS order_seq,
        COUNT(*) OVER (PARTITION BY c.customer_unique_id)                          AS customer_total_orders,
        LEAD(o.order_purchase_timestamp) OVER w                                    AS next_purchase_timestamp,
        MIN(DATE(o.order_purchase_timestamp)) OVER (PARTITION BY c.customer_unique_id) AS first_purchase_date
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WINDOW w AS (PARTITION BY c.customer_unique_id ORDER BY o.order_purchase_timestamp, o.order_id)
),
repurchase AS (
    SELECT
        b.*,
        MIN(CASE WHEN DATE(b.order_purchase_timestamp) >= b.first_purchase_date + INTERVAL 1 DAY
                 THEN DATE(b.order_purchase_timestamp) END)
            OVER (PARTITION BY b.customer_unique_id) AS first_repurchase_date
    FROM base b
)
SELECT
    customer_unique_id,
    order_id,
    order_status,
    order_purchase_timestamp,
    order_seq,
    CASE WHEN order_seq = 1 THEN 1 ELSE 0 END AS is_first_order,
    customer_total_orders,
    CASE WHEN customer_total_orders >= 2 THEN 1 ELSE 0 END AS has_repurchase,
    TIMESTAMPDIFF(SECOND, order_purchase_timestamp, next_purchase_timestamp) / 86400 AS days_to_next_order,
    first_purchase_date,
    CASE WHEN first_repurchase_date IS NOT NULL THEN 1 ELSE 0 END AS has_repurchase_nextday,
    DATEDIFF(first_repurchase_date, first_purchase_date)          AS days_to_first_repurchase
FROM repurchase;
