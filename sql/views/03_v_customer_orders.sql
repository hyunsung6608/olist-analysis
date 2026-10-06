-- v_customer_orders: 고객별 주문 순서 (재구매·코호트 분석용)
-- 목적: 실제 고객(customer_unique_id) 기준으로 주문 순서와 재구매 여부, 다음 주문까지 기간을 계산한다.
-- 한 행: 주문 1건 (orders와 행 수가 같음). 모든 주문 상태를 포함하므로 필요하면 order_status로 거른다.
-- 주요 컬럼:
--   order_seq              고객의 몇 번째 주문인지 (구매 시각 순, 1부터. 같은 시각이면 order_id 순)
--   is_first_order         첫 주문이면 1
--   customer_total_orders  이 고객의 전체 주문 수
--   has_repurchase         이 고객이 2건 이상 주문했으면 1 (고객 단위 값이 모든 주문 행에 반복됨)
--   days_to_next_order     다음 주문까지 일수 (소수 포함, 마지막 주문이면 NULL)
CREATE OR REPLACE VIEW v_customer_orders AS
WITH base AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_status,
        o.order_purchase_timestamp,
        ROW_NUMBER() OVER w                                   AS order_seq,
        COUNT(*) OVER (PARTITION BY c.customer_unique_id)     AS customer_total_orders,
        LEAD(o.order_purchase_timestamp) OVER w               AS next_purchase_timestamp
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WINDOW w AS (PARTITION BY c.customer_unique_id ORDER BY o.order_purchase_timestamp, o.order_id)
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
    TIMESTAMPDIFF(SECOND, order_purchase_timestamp, next_purchase_timestamp) / 86400 AS days_to_next_order
FROM base;
