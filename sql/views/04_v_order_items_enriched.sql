-- v_order_items_enriched: 주문 상품 단위 분석 뷰
-- 목적: 주문 상품에 카테고리(원어·영문), 판매자·고객 위치, 판매자→고객 직선 거리를 붙여 판매자·카테고리·지역 분석에 쓴다.
-- 한 행: 주문 상품 1건 (order_items와 행 수가 같음)
-- 주요 컬럼:
--   product_category_name / product_category_name_english  카테고리 (빈 카테고리는 '(미분류)')
--   seller_lat, seller_lng / customer_lat, customer_lng   우편번호별 평균 좌표 (geolocation_agg, 없으면 NULL)
--   distance_km   판매자 → 고객 직선 거리(km), 하버사인 공식, 지구 반지름 6371km. 한쪽 좌표라도 없으면 NULL
CREATE OR REPLACE VIEW v_order_items_enriched AS
SELECT
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    i.shipping_limit_date,
    i.price,
    i.freight_value,
    COALESCE(p.product_category_name, '(미분류)')        AS product_category_name,
    COALESCE(t.product_category_name_english, '(미분류)') AS product_category_name_english,
    p.product_weight_g,
    s.seller_state,
    s.seller_zip_code_prefix,
    c.customer_unique_id,
    c.customer_state,
    c.customer_zip_code_prefix,
    gs.lat AS seller_lat,
    gs.lng AS seller_lng,
    gc.lat AS customer_lat,
    gc.lng AS customer_lng,
    6371 * 2 * ASIN(LEAST(1, SQRT(
        POW(SIN(RADIANS(gc.lat - gs.lat) / 2), 2)
        + COS(RADIANS(gs.lat)) * COS(RADIANS(gc.lat)) * POW(SIN(RADIANS(gc.lng - gs.lng) / 2), 2)
    ))) AS distance_km
FROM order_items i
JOIN products p              ON p.product_id = i.product_id
LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
JOIN sellers s               ON s.seller_id = i.seller_id
JOIN orders o                ON o.order_id = i.order_id
JOIN customers c             ON c.customer_id = o.customer_id
LEFT JOIN geolocation_agg gs ON gs.zip_code_prefix = s.seller_zip_code_prefix
LEFT JOIN geolocation_agg gc ON gc.zip_code_prefix = c.customer_zip_code_prefix;
