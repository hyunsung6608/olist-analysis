-- Q1-2. 개선 주체별 불만 비중 (리뷰 단위, 14,286건)
-- 유형을 개선 주체로 묶는다:
--   물류(NOT_RECEIVED, DELAY) / 판매자 출고(WRONG_MISSING) / 상품(DAMAGED, NOT_AS_DESCRIBED, LOW_QUALITY)
--   판매자 응대(SERVICE) / 플랫폼 정책(SHIPPING_COST) / 기타(OTHER, UNCLEAR) / 불만 없음(NO_COMPLAINT)
-- share_any: 해당 주체의 유형이 하나라도 붙은 리뷰 비율 (합이 100%를 넘을 수 있음)
-- share_primary: 주 원인(primary_label)이 해당 주체에 속하는 리뷰 비율 (합이 100%)
WITH owners AS (
    SELECT *
    FROM JSON_TABLE(
        '[["물류",1,"NOT_RECEIVED"],["물류",1,"DELAY"],["판매자 출고",2,"WRONG_MISSING"],
          ["상품",3,"DAMAGED"],["상품",3,"NOT_AS_DESCRIBED"],["상품",3,"LOW_QUALITY"],
          ["판매자 응대",4,"SERVICE"],["플랫폼 정책",5,"SHIPPING_COST"],
          ["기타",6,"OTHER"],["기타",6,"UNCLEAR"],["불만 없음",7,"NO_COMPLAINT"]]',
        '$[*]' COLUMNS (owner VARCHAR(20) PATH '$[0]', owner_ord INT PATH '$[1]', label VARCHAR(20) PATH '$[2]')
    ) AS o
),
long_labels AS (
    SELECT
        l.review_id,
        o.owner,
        o.owner_ord,
        CASE o.label
            WHEN 'NOT_RECEIVED' THEN l.NOT_RECEIVED WHEN 'WRONG_MISSING' THEN l.WRONG_MISSING
            WHEN 'DAMAGED' THEN l.DAMAGED WHEN 'NOT_AS_DESCRIBED' THEN l.NOT_AS_DESCRIBED
            WHEN 'LOW_QUALITY' THEN l.LOW_QUALITY WHEN 'SHIPPING_COST' THEN l.SHIPPING_COST
            WHEN 'DELAY' THEN l.DELAY WHEN 'SERVICE' THEN l.SERVICE WHEN 'OTHER' THEN l.OTHER
            WHEN 'UNCLEAR' THEN l.UNCLEAR WHEN 'NO_COMPLAINT' THEN l.NO_COMPLAINT
        END AS has_label,
        CASE WHEN l.primary_label = o.label THEN 1 ELSE 0 END AS is_primary
    FROM review_complaint_labels l
    CROSS JOIN owners o
),
per_review AS (
    SELECT review_id, owner, owner_ord, MAX(has_label) AS has_owner, MAX(is_primary) AS is_primary_owner
    FROM long_labels
    GROUP BY review_id, owner, owner_ord
),
total AS (
    SELECT COUNT(*) AS n_reviews FROM review_complaint_labels
)
SELECT
    p.owner_ord,
    p.owner,
    t.n_reviews,
    SUM(p.has_owner)                      AS n_any,
    SUM(p.has_owner) / t.n_reviews        AS share_any,
    SUM(p.is_primary_owner)               AS n_primary,
    SUM(p.is_primary_owner) / t.n_reviews AS share_primary
FROM per_review p
CROSS JOIN total t
GROUP BY p.owner_ord, p.owner, t.n_reviews
ORDER BY p.owner_ord;
