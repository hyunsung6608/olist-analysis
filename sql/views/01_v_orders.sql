-- v_orders: 주문 단위 분석 뷰
-- 목적: 주문·고객 정보와 주문 상품 집계, 배송 지표, 데이터 품질 플래그를 한 행에 모은다.
-- 한 행: 주문 1건 (orders와 행 수가 같음)
-- 주요 컬럼:
--   n_items / n_sellers           주문 상품 수 / 판매자 수 (상품 없는 주문은 0)
--   items_value / freight_value   상품 금액 합계 / 배송비 합계 (상품 없는 주문은 NULL)
--   delivery_days                 구매 시각 → 고객 수령 시각 일수 (소수 포함)
--   delay_days                    예상 배송일 → 고객 수령일 일수, 날짜 단위 (양수면 지연, 예상일 당일 수령은 0)
--   is_late                       delay_days > 0이면 1, 수령일이 없으면 NULL
--   flag_carrier_before_approval  택배사 인계가 결제 승인보다 앞섬 (품질 리포트 '표시')
--   flag_status_date_mismatch     delivered가 아닌데 수령일이 있음 (품질 리포트 '표시')
--   exclude_delivery_metrics      1이면 배송 지표 계산에서 제외 (delivered가 아님, 수령일 없음, 인계 > 수령)
--                                 배송 기간·지연율은 exclude_delivery_metrics = 0인 주문으로만 계산한다.
CREATE OR REPLACE VIEW v_orders AS
WITH items AS (
    SELECT
        order_id,
        COUNT(*)                  AS n_items,
        COUNT(DISTINCT seller_id) AS n_sellers,
        SUM(price)                AS items_value,
        SUM(freight_value)        AS freight_value
    FROM order_items
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.customer_state,
    c.customer_zip_code_prefix,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    COALESCE(i.n_items, 0)   AS n_items,
    COALESCE(i.n_sellers, 0) AS n_sellers,
    i.items_value,
    i.freight_value,
    TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date) / 86400 AS delivery_days,
    DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date)                 AS delay_days,
    CASE
        WHEN o.order_delivered_customer_date IS NULL THEN NULL
        WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) > 0 THEN 1
        ELSE 0
    END AS is_late,
    CASE WHEN o.order_delivered_carrier_date < o.order_approved_at THEN 1 ELSE 0 END AS flag_carrier_before_approval,
    CASE WHEN o.order_status <> 'delivered' AND o.order_delivered_customer_date IS NOT NULL THEN 1 ELSE 0 END
        AS flag_status_date_mismatch,
    CASE
        WHEN o.order_status <> 'delivered' THEN 1
        WHEN o.order_delivered_customer_date IS NULL THEN 1
        WHEN o.order_delivered_carrier_date > o.order_delivered_customer_date THEN 1
        ELSE 0
    END AS exclude_delivery_metrics
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN items i ON i.order_id = o.order_id;
