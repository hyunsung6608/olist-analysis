# 데이터 품질 검사 (적재 전)

- 검사일: 2026-10-06 / 스크립트: `src/etl/quality_check.py` / 원본: `data/raw` (읽기만 함)
- 처리 방침: **변환**(적재 시 값을 바꿈) / **표시**(값은 두고 플래그) / **집계에서만 제외**(원본은 두고 특정 분석에서 뺌) / **그대로 둠**

## 1. orders 날짜 논리

### 날짜 순서: 구매 > 결제 승인

- 검사 내용: 두 날짜가 모두 있는 주문 중 구매 > 결제 승인인 주문
- 건수: **0** / 99,441 주문 (0.00%)
- 처리 방침: **그대로 둠** — 위반 없음

### 날짜 순서: 결제 승인 > 택배사 인계

- 검사 내용: 두 날짜가 모두 있는 주문 중 결제 승인 > 택배사 인계인 주문
- 건수: **1,359** / 99,441 주문 (1.37%)
- 대표 사례:
  - `order_id=dcb36b511fcac050b97cd5c05de84dc3, order_status=delivered, order_approved_at=2018-06-12 23:31:02, order_delivered_carrier_date=2018-06-11 14:54:00`
  - `order_id=688052146432ef8253587b930b01a06d, order_status=delivered, order_approved_at=2018-04-24 18:25:22, order_delivered_carrier_date=2018-04-23 19:19:14`
- 처리 방침: **표시** — 대부분 수 시간~하루 차이(중앙값 약 17시간)로 시스템 기록 시점 차이로 보임. 주문 자체는 정상이므로 남기고, 승인→인계 소요 시간 분석에서만 이 주문을 빼도록 플래그를 둔다

### 날짜 순서: 택배사 인계 > 고객 수령

- 검사 내용: 두 날짜가 모두 있는 주문 중 택배사 인계 > 고객 수령인 주문
- 건수: **23** / 99,441 주문 (0.02%)
- 대표 사례:
  - `order_id=a1abeb653a4d4cd1e142ccb8c82cd069, order_status=delivered, order_delivered_carrier_date=2017-07-28 16:57:58, order_delivered_customer_date=2017-07-25 19:32:56`
  - `order_id=383aa8b2724fe452d9ccd9934a8c628b, order_status=delivered, order_delivered_carrier_date=2017-07-07 17:22:41, order_delivered_customer_date=2017-07-06 14:27:51`
- 처리 방침: **집계에서만 제외** — 인계 전에 수령할 수 없으므로 날짜 오류. 건수가 적어 원본은 두고 배송 소요 기간 집계에서 제외

### 날짜 순서: 구매 > 고객 수령

- 검사 내용: 두 날짜가 모두 있는 주문 중 구매 > 고객 수령인 주문
- 건수: **0** / 99,441 주문 (0.00%)
- 처리 방침: **그대로 둠** — 위반 없음

### delivered인데 고객 수령일 없음

- 검사 내용: order_status=delivered이고 order_delivered_customer_date가 빈 주문
- 건수: **8** / 96,478 주문 (0.01%)
- 대표 사례:
  - `order_id=2d1e2d5bf4dc7227b3bfebb81328c15f, order_status=delivered, order_delivered_carrier_date=2017-11-30 18:12:23`
  - `order_id=f5dd62b788049ad9fc0526e3ad11a097, order_status=delivered, order_delivered_carrier_date=2018-06-25 08:05:00`
- 처리 방침: **집계에서만 제외** — 수령일이 없어 배송 소요 기간·지연 여부를 계산할 수 없음. 상태 기준 집계에는 포함

### delivered가 아닌데 고객 수령일 있음

- 검사 내용: order_status≠delivered이고 고객 수령일이 있는 주문
- 건수: **6** / 2,963 주문 (0.20%)
- 대표 사례:
  - `order_id=1950d777989f6a877539f53795b4c3c3, order_status=canceled, order_delivered_customer_date=2018-03-21 22:03:51`
  - `order_id=dabf2b0e35b423f94618bf965fcb7514, order_status=canceled, order_delivered_customer_date=2016-10-16 14:36:59`
- 처리 방침: **표시** — 모두 canceled 상태로, 배송 후 취소(반품 등)로 보임. 상태는 원본대로 두고 배송 분석 시 상태 조건을 명시

### 상태별 주문 수

- 검사 내용: order_status 분포: delivered 96,478, shipped 1,107, canceled 625, unavailable 609, invoiced 314, processing 301, created 5, approved 2
- 건수: **1,234** / 99,441 주문(unavailable+canceled) (1.24%)
- 대표 사례:
  - `unavailable 609건 중 주문 상품(order_items)이 없는 주문 603건`
  - `canceled 625건 중 주문 상품이 없는 주문 164건`
- 처리 방침: **그대로 둠** — 유효한 상태값. unavailable(결제 후 품절로 보임)은 LLM의 결제 후 품절 리뷰 판단 보완에 활용

### 예상 배송일보다 늦게 받은 주문 (참고)

- 검사 내용: 고객 수령일(날짜)이 예상 배송일(날짜)보다 늦은 주문, 수령일 있는 주문 기준
- 건수: **6,535** / 96,476 주문 (6.77%)
- 대표 사례:
  - `order_id=203096f03d82e0dffbc41ebc2e2bcfb7, order_estimated_delivery_date=2017-09-28 00:00:00, order_delivered_customer_date=2017-10-09 22:23:46`
- 처리 방침: **그대로 둠** — 품질 문제가 아니라 분석 대상(Q2 배송 지연). 지연 여부는 날짜 단위로 계산

## 2. 금액과 수량

### order_items: price ≤ 0

- 검사 내용: 상품 가격이 0 이하인 행
- 건수: **0** / 112,650 행 (0.00%)
- 처리 방침: **그대로 둠** — 위반 없음

### order_items: freight_value < 0

- 검사 내용: 배송비가 음수인 행
- 건수: **0** / 112,650 행 (0.00%)
- 처리 방침: **그대로 둠** — 위반 없음 (참고: 배송비 0인 행 383건은 무료 배송으로 보고 정상 처리)

### order_payments: payment_value ≤ 0

- 검사 내용: 결제 금액이 0 이하인 행 (결제 수단: {'voucher': 6, 'not_defined': 3})
- 건수: **9** / 103,886 행 (0.01%)
- 대표 사례:
  - `order_id=8bcbe01d44d147f901cd3192671144db, payment_type=voucher, payment_value=0.00`
  - `order_id=fa65dad1b0e818e3ccc5cb0e39231352, payment_type=voucher, payment_value=0.00`
- 처리 방침: **그대로 둠** — voucher 0원은 쿠폰 전액 할인 등으로 가능. not_defined 0원은 아래 항목에서 함께 처리

### order_payments: payment_installments = 0

- 검사 내용: 할부 개월 수가 0인 행 (일시불은 1)
- 건수: **2** / 103,886 행 (0.00%)
- 대표 사례:
  - `order_id=744bade1fcf9ff3f31d860ace076d422, payment_type=credit_card, payment_installments=0, payment_value=58.69`
  - `order_id=1a57108394169c0b47d8f876acc9ba2d, payment_type=credit_card, payment_installments=0, payment_value=129.94`
- 처리 방침: **집계에서만 제외** — 0개월 할부는 정의되지 않은 값. 2건뿐이라 원본은 두고 할부 분석에서만 제외

### order_payments: payment_type = not_defined

- 검사 내용: 결제 수단이 정의되지 않은 행 (해당 주문 상태: {'canceled': 3})
- 건수: **3** / 103,886 행 (0.00%)
- 대표 사례:
  - `order_id=4637ca194b6387e2d538dc89b124b0ee, payment_type=not_defined, payment_value=0.00`
  - `order_id=00b1cb0320190ca0daa2c88b35206009, payment_type=not_defined, payment_value=0.00`
- 처리 방침: **집계에서만 제외** — 금액 0원이고 결제 수단을 알 수 없어 결제 수단별 집계에서만 제외

### 주문별 상품+배송비 합계 ≠ 결제 합계 (차이 1 이상)

- 검사 내용: 상품·결제가 모두 있는 주문 중 |결제 합계 − (상품 가격+배송비) 합계| ≥ 1. 결제가 더 많은 주문 232건, 상품 합계가 더 많은 주문 18건
- 건수: **250** / 98,665 주문 (0.25%)
- 대표 사례:
  - `order_id=ce6d150fb29ada17d2082f4847107665, 상품+배송비=1403.66, 결제=1586.47, 차이=+182.81`
  - `order_id=6e5fe7366a2e1bfbf3257dba0af1267f, 상품+배송비=287.91, 결제=406.92, 차이=+119.01`
- 처리 방침: **그대로 둠** — 결제가 더 많은 주문의 98.7%가 할부 2개월 이상(전체 주문은 51.5%)이라 할부 이자로 설명됨. 매출은 order_items, 결제는 order_payments 기준으로 구분해 쓰고 서로 대체하지 않는다

### 결제는 있는데 주문 상품이 없는 주문 (참고)

- 검사 내용: order_payments에는 있고 order_items에는 없는 주문 (상태: {'unavailable': 603, 'canceled': 164, 'created': 5, 'invoiced': 2, 'shipped': 1})
- 건수: **775** / 99,441 주문 (0.78%)
- 대표 사례:
  - `order_id=0010dedd556712d7bb69a19cb7bbd37a`
- 처리 방침: **그대로 둠** — 대부분 unavailable·canceled로 상품이 확정되기 전에 끝난 주문. 상품·판매자 분석에는 자연히 빠짐

## 3. products

### 무게·크기 빈 상품

- 검사 내용: 무게·길이·높이·너비 중 하나라도 빈 상품
- 건수: **2** / 32,951 상품 (0.01%)
- 대표 사례:
  - `product_id=09ff539a621711667c43eba6a3bd8466, product_weight_g=, product_length_cm=, product_height_cm=, product_width_cm=`
  - `product_id=5eb564652db742ff8f28759cd8d2652a, product_weight_g=, product_length_cm=, product_height_cm=, product_width_cm=`
- 처리 방침: **변환** — 빈 문자열을 NULL로 적재

### 무게·크기 0인 상품

- 검사 내용: 무게·길이·높이·너비 중 0인 값이 있는 상품
- 건수: **4** / 32,951 상품 (0.01%)
- 대표 사례:
  - `product_id=81781c0fed9fe1ad6e8c81fca1e1cb08, product_weight_g=0, product_length_cm=30, product_height_cm=25, product_width_cm=30`
  - `product_id=8038040ee2a71048d4bdbbdc985b69ab, product_weight_g=0, product_length_cm=30, product_height_cm=25, product_width_cm=30`
- 처리 방침: **변환** — 무게 0g은 실제로 불가능한 값이므로 NULL로 바꿔 적재(평균·배송비 분석 왜곡 방지)

### 카테고리 빈 상품

- 검사 내용: product_category_name이 빈 상품
- 건수: **610** / 32,951 상품 (1.85%)
- 대표 사례:
  - `product_id=a41e356c76fab66334f36de622ecbd3a, product_name_lenght=`
  - `product_id=d8dee61c2034d6d075997acef1870e9b, product_name_lenght=`
- 처리 방침: **변환** — NULL로 적재하고 분석 시 '(미분류)'로 묶음

### 번역표에 없는 카테고리

- 검사 내용: 카테고리는 있으나 번역표에 없는 상품 ({'portateis_cozinha_e_preparadores_de_alimentos': 10, 'pc_gamer': 3})
- 건수: **13** / 32,951 상품 (0.04%)
- 대표 사례:
  - `portateis_cozinha_e_preparadores_de_alimentos (10개 상품)`
  - `pc_gamer (3개 상품)`
- 처리 방침: **변환** — 원본은 두고 category_translation 적재 시 영어명 2개를 보완 행으로 추가(출처: 수동 번역 표시)

## 4. geolocation

### 브라질 범위 밖 좌표

- 검사 내용: 위도 -34~6, 경도 -74~-34 밖의 행. 범위 밖 좌표만 있는 우편번호 5개 / 전체 19,015개
- 건수: **42** / 1,000,163 행 (0.00%)
- 대표 사례:
  - `geolocation_zip_code_prefix=18243, geolocation_lat=28.008978338034268, geolocation_lng=-15.536867177679131, geolocation_city=bom retiro da esperanca`
  - `geolocation_zip_code_prefix=28165, geolocation_lat=41.61405150610495, geolocation_lng=-8.411675312504059, geolocation_city=vila nova de campos`
- 처리 방침: **집계에서만 제외** — 원본 geolocation 테이블에는 그대로 적재하고, geolocation_agg의 평균 위경도 계산에서만 제외

### customers 우편번호 중 geolocation에 없는 것

- 검사 내용: 5자리로 맞춘 우편번호 기준. 고유 우편번호 157/14,994개(1.05%) 없음
- 건수: **278** / 99,441 행 (0.28%)
- 대표 사례:
  - `customer_zip_code_prefix=72300, customer_city=brasilia, customer_state=DF`
  - `customer_zip_code_prefix=11547, customer_city=cubatao, customer_state=SP`
- 처리 방침: **그대로 둠** — LEFT JOIN 시 위경도가 NULL. 지도 분석에서는 주(state) 단위로 대체 가능

### sellers 우편번호 중 geolocation에 없는 것

- 검사 내용: 5자리로 맞춘 우편번호 기준. 고유 우편번호 7/2,246개(0.31%) 없음
- 건수: **7** / 3,095 행 (0.23%)
- 대표 사례:
  - `seller_zip_code_prefix=82040, seller_city=curitiba, seller_state=PR`
  - `seller_zip_code_prefix=91901, seller_city=porto alegre, seller_state=RS`
- 처리 방침: **그대로 둠** — LEFT JOIN 시 위경도가 NULL. 지도 분석에서는 주(state) 단위로 대체 가능

## 5. order_reviews

### review_score가 1~5 밖

- 검사 내용: 점수가 비었거나 1~5 정수가 아닌 행
- 건수: **0** / 99,224 행 (0.00%)
- 처리 방침: **그대로 둠** — 위반 없음

### 답변 시각 < 작성 시각

- 검사 내용: review_answer_timestamp가 review_creation_date보다 앞선 행
- 건수: **0** / 99,224 행 (0.00%)
- 처리 방침: **그대로 둠** — 위반 없음

### 리뷰 작성일 < 주문일

- 검사 내용: 리뷰 요청 발송일(날짜)이 구매일(날짜)보다 앞선 행
- 건수: **64** / 99,224 행 (0.06%)
- 대표 사례:
  - `review_id=3415c9f764e478409e8e0660ae816dd2, order_id=4d59cc2a2e7bb6c0a851725f5888a9b5, review_creation_date=2018-07-31 00:00:00, order_purchase_timestamp=2018-09-06 14:50:07`
  - `review_id=49f695dffa457eaba90d388a5c37e942, order_id=e5215415bb6f76fe3b7cb68103a0d1c0, review_creation_date=2016-10-09 00:00:00, order_purchase_timestamp=2016-10-22 08:25:27`
- 처리 방침: **표시** — 주문 전 리뷰는 불가능하므로 날짜 오류. 리뷰 자체(점수·텍스트)는 쓰고, 주문→리뷰 소요 기간 분석에서만 제외하도록 플래그를 둔다

## 6. review_complaint_labels

### 분류 결과 review_id가 order_reviews에 없음

- 검사 내용: review_complaint_labels.csv의 review_id 중 order_reviews에 없는 것. 참고: 여러 주문에 연결된 review_id 153건(조인 시 행이 늘어남)
- 건수: **0** / 14,286 리뷰 (0.00%)
- 처리 방침: **그대로 둠** — 누락 없음. 주문 단위로 조인할 때는 여러 주문에 연결된 리뷰를 고려

## 처리 방침 요약

| 항목 | 건수 (비율) | 방침 | 이유 |
|---|---|---|---|
| orders 날짜 논리: 날짜 순서: 구매 > 결제 승인 | 0 (0.00%) | 그대로 둠 | 위반 없음 |
| orders 날짜 논리: 날짜 순서: 결제 승인 > 택배사 인계 | 1,359 (1.37%) | 표시 | 대부분 수 시간~하루 차이(중앙값 약 17시간)로 시스템 기록 시점 차이로 보임 |
| orders 날짜 논리: 날짜 순서: 택배사 인계 > 고객 수령 | 23 (0.02%) | 집계에서만 제외 | 인계 전에 수령할 수 없으므로 날짜 오류 |
| orders 날짜 논리: 날짜 순서: 구매 > 고객 수령 | 0 (0.00%) | 그대로 둠 | 위반 없음 |
| orders 날짜 논리: delivered인데 고객 수령일 없음 | 8 (0.01%) | 집계에서만 제외 | 수령일이 없어 배송 소요 기간·지연 여부를 계산할 수 없음 |
| orders 날짜 논리: delivered가 아닌데 고객 수령일 있음 | 6 (0.20%) | 표시 | 모두 canceled 상태로, 배송 후 취소(반품 등)로 보임 |
| orders 날짜 논리: 상태별 주문 수 | 1,234 (1.24%) | 그대로 둠 | 유효한 상태값 |
| orders 날짜 논리: 예상 배송일보다 늦게 받은 주문 (참고) | 6,535 (6.77%) | 그대로 둠 | 품질 문제가 아니라 분석 대상(Q2 배송 지연) |
| 금액과 수량: order_items: price ≤ 0 | 0 (0.00%) | 그대로 둠 | 위반 없음 |
| 금액과 수량: order_items: freight_value < 0 | 0 (0.00%) | 그대로 둠 | 위반 없음 (참고: 배송비 0인 행 383건은 무료 배송으로 보고 정상 처리) |
| 금액과 수량: order_payments: payment_value ≤ 0 | 9 (0.01%) | 그대로 둠 | voucher 0원은 쿠폰 전액 할인 등으로 가능 |
| 금액과 수량: order_payments: payment_installments = 0 | 2 (0.00%) | 집계에서만 제외 | 0개월 할부는 정의되지 않은 값 |
| 금액과 수량: order_payments: payment_type = not_defined | 3 (0.00%) | 집계에서만 제외 | 금액 0원이고 결제 수단을 알 수 없어 결제 수단별 집계에서만 제외 |
| 금액과 수량: 주문별 상품+배송비 합계 ≠ 결제 합계 (차이 1 이상) | 250 (0.25%) | 그대로 둠 | 결제가 더 많은 주문의 98.7%가 할부 2개월 이상(전체 주문은 51.5%)이라 할부 이자로 설명됨 |
| 금액과 수량: 결제는 있는데 주문 상품이 없는 주문 (참고) | 775 (0.78%) | 그대로 둠 | 대부분 unavailable·canceled로 상품이 확정되기 전에 끝난 주문 |
| products: 무게·크기 빈 상품 | 2 (0.01%) | 변환 | 빈 문자열을 NULL로 적재 |
| products: 무게·크기 0인 상품 | 4 (0.01%) | 변환 | 무게 0g은 실제로 불가능한 값이므로 NULL로 바꿔 적재(평균·배송비 분석 왜곡 방지) |
| products: 카테고리 빈 상품 | 610 (1.85%) | 변환 | NULL로 적재하고 분석 시 '(미분류)'로 묶음 |
| products: 번역표에 없는 카테고리 | 13 (0.04%) | 변환 | 원본은 두고 category_translation 적재 시 영어명 2개를 보완 행으로 추가(출처: 수동 번역 표시) |
| geolocation: 브라질 범위 밖 좌표 | 42 (0.00%) | 집계에서만 제외 | 원본 geolocation 테이블에는 그대로 적재하고, geolocation_agg의 평균 위경도 계산에서만 제외 |
| geolocation: customers 우편번호 중 geolocation에 없는 것 | 278 (0.28%) | 그대로 둠 | LEFT JOIN 시 위경도가 NULL |
| geolocation: sellers 우편번호 중 geolocation에 없는 것 | 7 (0.23%) | 그대로 둠 | LEFT JOIN 시 위경도가 NULL |
| order_reviews: review_score가 1~5 밖 | 0 (0.00%) | 그대로 둠 | 위반 없음 |
| order_reviews: 답변 시각 < 작성 시각 | 0 (0.00%) | 그대로 둠 | 위반 없음 |
| order_reviews: 리뷰 작성일 < 주문일 | 64 (0.06%) | 표시 | 주문 전 리뷰는 불가능하므로 날짜 오류 |
| review_complaint_labels: 분류 결과 review_id가 order_reviews에 없음 | 0 (0.00%) | 그대로 둠 | 누락 없음 |
