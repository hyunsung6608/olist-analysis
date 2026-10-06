-- v_order_reviews: 주문당 대표 리뷰 1건과 LLM 불만 분류 결과
-- 목적: 주문 단위 분석(배송 지연 vs 평점·불만 유형 등)에 쓸 리뷰를 주문당 1건으로 정하고 분류 결과를 붙인다.
-- 한 행: 리뷰가 있는 주문 1건
-- 대표 리뷰 선정: 한 주문에 리뷰가 여러 개면 review_creation_date가 가장 늦은 리뷰,
--   같으면 review_score가 낮은 리뷰, 그래도 같으면 review_answer_timestamp가 늦은 리뷰, 마지막으로 review_id 순(결과 고정용)
-- 주요 컬럼:
--   n_reviews_in_order        이 주문에 달린 리뷰 수 (2 이상이면 대표 리뷰를 고른 것)
--   is_classified             LLM 분류 결과가 있으면 1 (분류 대상: 텍스트 있는 1~3점 리뷰)
--   DELAY ~ NO_COMPLAINT      불만 유형 0/1 (분류 대상이 아닌 4~5점, 텍스트 없는 리뷰는 NULL)
--   primary_label             주 원인 (분류 대상이 아니면 NULL)
--   flag_review_before_order  리뷰 작성일(날짜)이 주문일(날짜)보다 앞섬 (품질 리포트 '표시', 주문→리뷰 기간 분석에서 제외)
CREATE OR REPLACE VIEW v_order_reviews AS
WITH ranked AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.order_id
            ORDER BY r.review_creation_date DESC, r.review_score ASC, r.review_answer_timestamp DESC, r.review_id
        ) AS rn,
        COUNT(*) OVER (PARTITION BY r.order_id) AS n_reviews_in_order
    FROM order_reviews r
)
SELECT
    rk.order_id,
    rk.review_id,
    rk.review_score,
    rk.review_comment_title,
    rk.review_comment_message,
    rk.review_creation_date,
    rk.review_answer_timestamp,
    rk.n_reviews_in_order,
    CASE WHEN l.review_id IS NOT NULL THEN 1 ELSE 0 END AS is_classified,
    l.DELAY,
    l.NOT_RECEIVED,
    l.WRONG_MISSING,
    l.DAMAGED,
    l.NOT_AS_DESCRIBED,
    l.LOW_QUALITY,
    l.SERVICE,
    l.SHIPPING_COST,
    l.OTHER,
    l.UNCLEAR,
    l.NO_COMPLAINT,
    l.primary_label,
    l.flag_rule_c_violation,
    l.flag_exclusive_violation,
    CASE WHEN DATE(rk.review_creation_date) < DATE(o.order_purchase_timestamp) THEN 1 ELSE 0 END
        AS flag_review_before_order
FROM ranked rk
JOIN orders o ON o.order_id = rk.order_id
LEFT JOIN review_complaint_labels l ON l.review_id = rk.review_id
WHERE rk.rn = 1;
