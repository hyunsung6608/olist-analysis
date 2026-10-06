# 적재 검증

- 실행 시각: 2026-10-06T19:37:50 / 스크립트: `src/etl/validate_load.py`
- 접속: `mysql+pymysql://olist_user:***@localhost:3306/olist?charset=utf8mb4`
- 결과: **전체 통과** (47/47 통과)
- 기대값은 원본 CSV에 load.py와 같은 규칙을 적용해 계산한다.


## 1. 행 수

| 항목 | 기대값 | DB 값 | 판정 |
|---|---|---|---|
| category_translation (원본 + 보완 2) | 73 | 73 | 통과 |
| customers | 99,441 | 99,441 | 통과 |
| sellers | 3,095 | 3,095 | 통과 |
| products | 32,951 | 32,951 | 통과 |
| orders | 99,441 | 99,441 | 통과 |
| order_items | 112,650 | 112,650 | 통과 |
| order_payments | 103,886 | 103,886 | 통과 |
| order_reviews | 99,224 | 99,224 | 통과 |
| geolocation | 1,000,163 | 1,000,163 | 통과 |
| geolocation_agg (브라질 범위 안 좌표가 있는 우편번호 수) | 19,010 | 19,010 | 통과 |
| review_complaint_labels | 14,286 | 14,286 | 통과 |

## 2. 우편번호

| 항목 | 기대값 | DB 값 | 판정 |
|---|---|---|---|
| customers.customer_zip_code_prefix 5자리 숫자가 아닌 값 | 0 | 0 | 통과 |
| sellers.seller_zip_code_prefix 5자리 숫자가 아닌 값 | 0 | 0 | 통과 |
| geolocation.geolocation_zip_code_prefix 5자리 숫자가 아닌 값 | 0 | 0 | 통과 |
| geolocation_agg.zip_code_prefix 5자리 숫자가 아닌 값 | 0 | 0 | 통과 |

## 3. 금액 합계

| 항목 | 기대값 | DB 값 | 판정 |
|---|---|---|---|
| order_items.price | 13591643.70 | 13591643.70 | 통과 |
| order_items.freight_value | 2251909.54 | 2251909.54 | 통과 |
| order_payments.payment_value | 16008872.12 | 16008872.12 | 통과 |

## 4. FK 무결성

| 항목 | 기대값 | DB 값 | 판정 |
|---|---|---|---|
| order_items.order_id → orders.order_id 부모 없는 값 | 0 | 0 | 통과 |
| order_items.product_id → products.product_id 부모 없는 값 | 0 | 0 | 통과 |
| order_items.seller_id → sellers.seller_id 부모 없는 값 | 0 | 0 | 통과 |
| order_payments.order_id → orders.order_id 부모 없는 값 | 0 | 0 | 통과 |
| order_reviews.order_id → orders.order_id 부모 없는 값 | 0 | 0 | 통과 |
| orders.customer_id → customers.customer_id 부모 없는 값 | 0 | 0 | 통과 |
| DB에 정의된 FK 수 (DDL 파일 기준) | 6 | 6 | 통과 |

## 5. NULL 건수

| 항목 | 기대값 | DB 값 | 판정 |
|---|---|---|---|
| orders.order_approved_at | 160 | 160 | 통과 |
| orders.order_delivered_carrier_date | 1,783 | 1,783 | 통과 |
| orders.order_delivered_customer_date | 2,965 | 2,965 | 통과 |
| products.product_weight_g (빈 값 + 0g) | 6 | 6 | 통과 |
| products.product_category_name (빈 값) | 610 | 610 | 통과 |

## 6. 리뷰 텍스트

| 항목 | 기대값 | DB 값 | 판정 |
|---|---|---|---|
| 무작위 100건(random_state=42, 본문 있는 40건 포함) 원본과 일치 | 100 | 100 | 통과 |

## 7. geolocation_agg

| 항목 | 기대값 | DB 값 | 판정 |
|---|---|---|---|
| 브라질 범위(위도 (-34, 6), 경도 (-74, -34)) 밖 좌표 | 0 | 0 | 통과 |
| n_points 합계 (= 범위 안 원본 행 수) | 1,000,121 | 1,000,121 | 통과 |

## 8. review_complaint_labels

| 항목 | 기대값 | DB 값 | 판정 |
|---|---|---|---|
| DELAY 합계 | 3,103 | 3,103 | 통과 |
| NOT_RECEIVED 합계 | 3,604 | 3,604 | 통과 |
| WRONG_MISSING 합계 | 3,277 | 3,277 | 통과 |
| DAMAGED 합계 | 1,463 | 1,463 | 통과 |
| NOT_AS_DESCRIBED 합계 | 1,414 | 1,414 | 통과 |
| LOW_QUALITY 합계 | 1,234 | 1,234 | 통과 |
| SERVICE 합계 | 2,747 | 2,747 | 통과 |
| SHIPPING_COST 합계 | 467 | 467 | 통과 |
| OTHER 합계 | 397 | 397 | 통과 |
| UNCLEAR 합계 | 279 | 279 | 통과 |
| NO_COMPLAINT 합계 | 1,007 | 1,007 | 통과 |
| flag_rule_c_violation 합계 | 67 | 67 | 통과 |
| flag_exclusive_violation 합계 | 1 | 1 | 통과 |
| primary_label 분포 | CSV 분포 | 같음 | 통과 |
