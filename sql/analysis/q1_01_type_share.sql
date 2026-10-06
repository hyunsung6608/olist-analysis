-- Q1-1. 불만 유형별 비중 (리뷰 단위, review_complaint_labels 14,286건)
-- 유형별 다중 라벨 건수·비율(해당 유형이 붙은 리뷰 / 전체 리뷰)과 주 원인 건수·비율을 구한다.
-- score_group: '전체'와 리뷰 점수 1/2/3점별. 다중 라벨 비율은 합이 100%를 넘을 수 있고, 주 원인 비율은 합이 100%.
-- 리뷰 점수는 order_reviews에서 review_id로 가져온다(여러 주문에 연결된 리뷰도 점수는 같음).
WITH scores AS (
    SELECT review_id, MIN(review_score) AS review_score
    FROM order_reviews
    GROUP BY review_id
),
base AS (
    SELECT l.*, CAST(s.review_score AS CHAR) AS score_group
    FROM review_complaint_labels l
    JOIN scores s ON s.review_id = l.review_id
    UNION ALL
    SELECT l.*, '전체' AS score_group
    FROM review_complaint_labels l
),
long_labels AS (
    SELECT
        b.score_group,
        b.review_id,
        b.primary_label,
        lb.ord,
        lb.label,
        CASE lb.label
            WHEN 'NOT_RECEIVED' THEN b.NOT_RECEIVED WHEN 'WRONG_MISSING' THEN b.WRONG_MISSING
            WHEN 'DAMAGED' THEN b.DAMAGED WHEN 'NOT_AS_DESCRIBED' THEN b.NOT_AS_DESCRIBED
            WHEN 'LOW_QUALITY' THEN b.LOW_QUALITY WHEN 'SHIPPING_COST' THEN b.SHIPPING_COST
            WHEN 'DELAY' THEN b.DELAY WHEN 'SERVICE' THEN b.SERVICE WHEN 'OTHER' THEN b.OTHER
            WHEN 'UNCLEAR' THEN b.UNCLEAR WHEN 'NO_COMPLAINT' THEN b.NO_COMPLAINT
        END AS has_label
    FROM base b
    CROSS JOIN JSON_TABLE(
        '["NOT_RECEIVED","WRONG_MISSING","DAMAGED","NOT_AS_DESCRIBED","LOW_QUALITY","SHIPPING_COST","DELAY","SERVICE","OTHER","UNCLEAR","NO_COMPLAINT"]',
        '$[*]' COLUMNS (ord FOR ORDINALITY, label VARCHAR(20) PATH '$')
    ) AS lb
),
totals AS (
    SELECT score_group, COUNT(*) AS n_reviews FROM base GROUP BY score_group
)
SELECT
    ll.score_group,
    ll.ord AS priority,
    ll.label,
    t.n_reviews,
    SUM(ll.has_label)                                AS n_multi,
    SUM(ll.has_label) / t.n_reviews                  AS share_multi,
    SUM(ll.primary_label = ll.label)                 AS n_primary,
    SUM(ll.primary_label = ll.label) / t.n_reviews   AS share_primary
FROM long_labels ll
JOIN totals t ON t.score_group = ll.score_group
GROUP BY ll.score_group, ll.ord, ll.label, t.n_reviews
ORDER BY FIELD(ll.score_group, '전체', '1', '2', '3'), ll.ord;
