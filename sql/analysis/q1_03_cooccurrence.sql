-- Q1-3. 함께 나타나는 불만 유형 (리뷰 단위, 14,286건)
-- 서로 다른 유형 쌍(A, B)마다 두 유형이 함께 붙은 리뷰 수와 "A가 있을 때 B도 있을 확률" P(B|A)를 구한다.
-- lift = P(B|A) / P(B): 1보다 크면 A가 있을 때 B가 평소보다 더 자주 함께 나타난다는 뜻.
-- 함께 나타난 적이 없는 쌍은 행이 없다(노트북에서 0으로 채움).
WITH long_labels AS (
    SELECT l.review_id, lb.ord, lb.label
    FROM review_complaint_labels l
    CROSS JOIN JSON_TABLE(
        '["NOT_RECEIVED","WRONG_MISSING","DAMAGED","NOT_AS_DESCRIBED","LOW_QUALITY","SHIPPING_COST","DELAY","SERVICE","OTHER","UNCLEAR","NO_COMPLAINT"]',
        '$[*]' COLUMNS (ord FOR ORDINALITY, label VARCHAR(20) PATH '$')
    ) AS lb
    WHERE CASE lb.label
            WHEN 'NOT_RECEIVED' THEN l.NOT_RECEIVED WHEN 'WRONG_MISSING' THEN l.WRONG_MISSING
            WHEN 'DAMAGED' THEN l.DAMAGED WHEN 'NOT_AS_DESCRIBED' THEN l.NOT_AS_DESCRIBED
            WHEN 'LOW_QUALITY' THEN l.LOW_QUALITY WHEN 'SHIPPING_COST' THEN l.SHIPPING_COST
            WHEN 'DELAY' THEN l.DELAY WHEN 'SERVICE' THEN l.SERVICE WHEN 'OTHER' THEN l.OTHER
            WHEN 'UNCLEAR' THEN l.UNCLEAR WHEN 'NO_COMPLAINT' THEN l.NO_COMPLAINT
          END = 1
),
label_counts AS (
    SELECT label, ord, COUNT(*) AS n_label FROM long_labels GROUP BY label, ord
),
total AS (
    SELECT COUNT(*) AS n_reviews FROM review_complaint_labels
)
SELECT
    ca.ord     AS ord_a,
    a.label    AS label_a,
    cb.ord     AS ord_b,
    b.label    AS label_b,
    COUNT(*)   AS n_both,
    ca.n_label AS n_a,
    COUNT(*) / ca.n_label                                  AS p_b_given_a,
    (COUNT(*) / ca.n_label) / (cb.n_label / t.n_reviews)   AS lift
FROM long_labels a
JOIN long_labels b ON b.review_id = a.review_id AND b.label <> a.label
JOIN label_counts ca ON ca.label = a.label
JOIN label_counts cb ON cb.label = b.label
CROSS JOIN total t
GROUP BY ca.ord, a.label, cb.ord, b.label, ca.n_label, cb.n_label, t.n_reviews
ORDER BY n_both DESC;
