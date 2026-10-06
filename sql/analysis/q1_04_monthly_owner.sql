-- Q1-4. 주문 월별 분류 리뷰 수와 개선 주체별 비중
-- 리뷰를 order_reviews → orders로 연결해 주문 월(구매 시각 기준)로 묶는다.
-- 한 리뷰가 여러 주문에 연결된 경우(153건) 구매 시각이 가장 이른 주문 1건을 대표 주문으로 쓴다.
-- share_primary: 그 달 리뷰 중 주 원인이 해당 주체인 비율 (합 100%)
-- share_any: 그 달 리뷰 중 해당 주체의 유형이 하나라도 붙은 비율
-- low_sample: 그 달 분류 리뷰가 100건 미만이면 1 (비율 해석 주의)
WITH review_order AS (
    SELECT review_id, order_id, order_purchase_timestamp
    FROM (
        SELECT r.review_id, o.order_id, o.order_purchase_timestamp,
               ROW_NUMBER() OVER (PARTITION BY r.review_id ORDER BY o.order_purchase_timestamp, o.order_id) AS rn
        FROM order_reviews r
        JOIN orders o ON o.order_id = r.order_id
        WHERE r.review_id IN (SELECT review_id FROM review_complaint_labels)
    ) x
    WHERE rn = 1
),
owners AS (
    SELECT *
    FROM JSON_TABLE(
        '[["물류",1,"NOT_RECEIVED"],["물류",1,"DELAY"],["판매자 출고",2,"WRONG_MISSING"],
          ["상품",3,"DAMAGED"],["상품",3,"NOT_AS_DESCRIBED"],["상품",3,"LOW_QUALITY"],
          ["판매자 응대",4,"SERVICE"],["플랫폼 정책",5,"SHIPPING_COST"],
          ["기타",6,"OTHER"],["기타",6,"UNCLEAR"],["불만 없음",7,"NO_COMPLAINT"]]',
        '$[*]' COLUMNS (owner VARCHAR(20) PATH '$[0]', owner_ord INT PATH '$[1]', label VARCHAR(20) PATH '$[2]')
    ) AS o
),
per_review AS (
    SELECT
        DATE_FORMAT(ro.order_purchase_timestamp, '%Y-%m') AS order_month,
        l.review_id,
        o.owner,
        o.owner_ord,
        MAX(CASE o.label
            WHEN 'NOT_RECEIVED' THEN l.NOT_RECEIVED WHEN 'WRONG_MISSING' THEN l.WRONG_MISSING
            WHEN 'DAMAGED' THEN l.DAMAGED WHEN 'NOT_AS_DESCRIBED' THEN l.NOT_AS_DESCRIBED
            WHEN 'LOW_QUALITY' THEN l.LOW_QUALITY WHEN 'SHIPPING_COST' THEN l.SHIPPING_COST
            WHEN 'DELAY' THEN l.DELAY WHEN 'SERVICE' THEN l.SERVICE WHEN 'OTHER' THEN l.OTHER
            WHEN 'UNCLEAR' THEN l.UNCLEAR WHEN 'NO_COMPLAINT' THEN l.NO_COMPLAINT
        END) AS has_owner,
        MAX(CASE WHEN l.primary_label = o.label THEN 1 ELSE 0 END) AS is_primary_owner
    FROM review_complaint_labels l
    JOIN review_order ro ON ro.review_id = l.review_id
    CROSS JOIN owners o
    GROUP BY order_month, l.review_id, o.owner, o.owner_ord
),
monthly AS (
    SELECT order_month, COUNT(DISTINCT review_id) AS n_reviews FROM per_review GROUP BY order_month
)
SELECT
    p.order_month,
    m.n_reviews,
    CASE WHEN m.n_reviews < 100 THEN 1 ELSE 0 END AS low_sample,
    p.owner_ord,
    p.owner,
    SUM(p.is_primary_owner)               AS n_primary,
    SUM(p.is_primary_owner) / m.n_reviews AS share_primary,
    SUM(p.has_owner)                      AS n_any,
    SUM(p.has_owner) / m.n_reviews        AS share_any
FROM per_review p
JOIN monthly m ON m.order_month = p.order_month
GROUP BY p.order_month, m.n_reviews, p.owner_ord, p.owner
ORDER BY p.order_month, p.owner_ord;
