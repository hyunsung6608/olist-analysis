# Tableau 대시보드 설계서

Olist 리뷰 불만 분석(Q1~Q5)의 결과를 대시보드 3개로 보여 준다. 이 문서만 보고 Tableau에서 대시보드를 재현할 수 있도록 데이터, 시트, 계산식, 필터 동작, 색상, 검산 항목을 정리했다.

## 데이터

`data/tableau/`의 CSV 5개(UTF-8, BOM 없음, 쉼표 구분). `python src/analysis/export_tableau.py`로 다시 만든다.

| 파일 | 한 행 | 행 수 | 주요 컬럼 |
|---|---|---|---|
| `orders_fact.csv` | 주문 1건 | 99,441 | order_month, customer_state, exclude_delivery_metrics, is_late, delay_days, delay_bucket(+order), delivery_days, n_items, n_sellers, items_value, freight_value, has_review, review_score, is_low_score, is_classified, 유형 11개(0/1), primary_label(_ko), owner |
| `complaint_labels_long.csv` | 리뷰 × 붙은 유형 1개 | 18,992 (리뷰 14,286) | review_id, order_id, order_month, customer_state, label, label_ko, label_order, owner, is_primary |
| `seller_summary.csv` | 판매자 1명 | 3,073 | seller_state, n_orders, meets_min_orders, seller_ctrl_rate_raw/adj, excess_complaints, low_rate_raw/adj, late_rate, is_watch_list, main_complaint_type |
| `state_summary.csv` | 고객 주 1개 | 27 | customer_state(2자리 코드), n_reviewed_orders, n_late, late_rate, low_rate, logistics_rate |
| `q5_scenarios.csv` | 개선안 × 시나리오 | 21 | row_type(단독/세부/묶음/보완), key, intervention, scenario_level, reduction_mean/low/high, share_of_low, priority, owner, feasibility, evidence, reason |

**값 규칙**
- `orders_fact`의 유형 11개 컬럼은 **분류되지 않은 주문(4~5점·텍스트 없음·리뷰 없음)이면 빈 값**이다. 그래서 `AVG([DELAY])`가 곧 "분류된 리뷰 중 비율"이 된다.
- `is_late`, `delay_days`, `delivery_days`는 배송 지표 대상이 아닌 주문(`exclude_delivery_metrics = 1`)이면 빈 값이다.
- `owner`는 주 원인 기준 개선 주체다. 분류되지 않은 리뷰는 `분류 대상 아님`, 리뷰가 없으면 빈 값이다.
- 유형·주체·지연 구간의 이름과 색은 `src/analysis/mappings.py`에서 정의한 값을 그대로 쓴다.

**연결 방식**: 대시보드마다 다른 원본을 쓰고, 원본 사이는 Tableau 관계(Relationship)로만 연결한다.
- ①: `complaint_labels_long`만 사용한다. 지역 필터는 같은 원본의 `customer_state`로 건다.
- ②: `orders_fact`(데이터 원본 필터 `exclude_delivery_metrics = 0`)와 `state_summary`를 `customer_state`로 관계 연결한다.
- ③: `q5_scenarios`, `seller_summary`, `state_summary`를 각각 독립 원본으로 쓴다(서로 연결하지 않음).

**지리 역할**: `customer_state`, `seller_state`는 지리적 역할을 "주/도"로, 국가는 Brazil로 지정한다.

## 공통 계산된 필드

```text
// [지연 여부] (orders_fact)
IF [is_late] = 1 THEN "지연" ELSEIF [is_late] = 0 THEN "제때" END

// [1~2점 비율] (orders_fact) — 리뷰 없는 주문은 is_low_score가 빈 값이라 자동으로 빠진다
AVG([is_low_score])

// [판매자 수 그룹] (orders_fact)
IF [n_sellers] >= 2 THEN "판매자 2명 이상"
ELSEIF [n_items] >= 2 THEN "판매자 1명·상품 2개 이상"
ELSEIF [n_items] = 1 THEN "판매자 1명·상품 1개"
ELSE "상품 없음" END

// [전체 리뷰 수] (complaint_labels_long) — 유형·주체를 나눠 보여도 분모는 필터 안의 전체 리뷰 수
{ EXCLUDE [label], [label_ko], [label_order], [owner], [is_primary] : COUNTD([review_id]) }

// [다중 라벨 비율] (complaint_labels_long) — 해당 유형(주체)이 붙은 리뷰 / 전체 리뷰
COUNTD([review_id]) / SUM([전체 리뷰 수])

// [주 원인 비율] (complaint_labels_long)
COUNTD(IF [is_primary] = 1 THEN [review_id] END) / SUM([전체 리뷰 수])

// [월 리뷰 수] / [표본 충분] (complaint_labels_long) — 100건 미만인 달은 추이에서 뺀다(Q1 기준)
{ FIXED [order_month] : COUNTD([review_id]) }
[월 리뷰 수] >= 100

// [실행 가능성 점수] / [근거 점수] (q5_scenarios)
CASE [feasibility] WHEN "높음" THEN 3 WHEN "중간" THEN 2 WHEN "낮음" THEN 1 END
CASE [evidence]    WHEN "높음" THEN 3 WHEN "중간" THEN 2 WHEN "낮음" THEN 1 END
```

**주의**: `SUM([전체 리뷰 수])`는 시트에 유형 차원이 있을 때 행마다 같은 값이 반복된다. 집계가 이상하면 `MIN([전체 리뷰 수])`를 쓴다. `[전체 리뷰 수]`는 EXCLUDE LOD라서 차원 필터(주, 월)는 반영되고, 유형·주체 필터는 반영되지 않는다. 유형 필터를 걸어도 분모는 바뀌지 않는다는 뜻이며, 의도한 동작이다.

## 색상 원칙

**개선 주체 (모든 대시보드에서 고정)**

| 주체 | 색 | 주체 | 색 |
|---|---|---|---|
| 물류 | `#d62728` 빨강 | 플랫폼 정책 | `#8c564b` 갈색 |
| 판매자 출고 | `#ff7f0e` 주황 | 기타 | `#7f7f7f` 회색 |
| 상품 | `#1f77b4` 파랑 | 불만 없음 | `#2ca02c` 초록 |
| 판매자 응대 | `#9467bd` 보라 | 분류 대상 아님 | `#d9d9d9` 연회색 |

**경고색 (저평점·지연)**
- 강한 경고 `#cb181d`: 1~2점 비율, 지연율, 4일 이상 지연 구간
- 약한 경고 `#fc9272`: 1~3일 지연, 보조 지표
- 중립 `#bdbdbd`: 제때·예정보다 빠름

**지연 구간** (`delay_bucket_order` 순서): 7일 이상 빠름 `#9ecae1` → 1~6일 빠름 `#c6dbef` → 예상일 당일 `#bdbdbd` → 1~3일 지연 `#fc9272` → 4~7일 지연 `#fb6a4a` → 8~14일 지연 `#cb181d` → 15일 이상 지연 `#67000d`. 배송 지표 없음은 표시하지 않는다.

**연속 색 범위**: 지도 같은 연속 값은 흰색에서 경고색(`#cb181d`)으로 가는 단색 순차 팔레트를 쓴다. 물류 불만 지도는 물류 색(`#d62728`) 계열을 쓴다.

정렬 규칙:
- 유형은 `label_order`(주 원인 우선순위) 순서로 정렬한다.
- 주체는 물류 → 판매자 출고 → 상품 → 판매자 응대 → 플랫폼 정책 → 기타 → 불만 없음 순서로 고정한다.

## 대시보드 ① 불만 개요 (Q1)

**목적**: 글로 불만을 남긴 1~3점 리뷰의 불만 원인 구성과 그 원인을 고쳐야 할 주체를 한눈에 보여 준다.

**핵심 메시지 (대시보드 제목)**: "저점 리뷰 불만의 3분의 1(33.9%)은 물류, 가장 큰 단일 원인은 미수령(25.2%)"

| 시트 | 파일 | 차원 | 측정값 | 차트 | 필터 |
|---|---|---|---|---|---|
| 1-1 KPI | complaint_labels_long | - | COUNTD(review_id), 물류 주 원인 비율, 미수령 다중 라벨 비율 | 숫자 타일 3개 | 주, 월 |
| 1-2 유형별 비중 | complaint_labels_long | label_ko (label_order 정렬) | [다중 라벨 비율], [주 원인 비율] (Measure Names로 나란히) | 가로 막대 (다중 연한 색, 주 원인 진한 색) | 주, 월 |
| 1-3 개선 주체별 비중 | complaint_labels_long | owner | [다중 라벨 비율], [주 원인 비율] | 세로 막대, 주체 고정 색 | 주, 월 |
| 1-4 월별 주체 비중 추이 | complaint_labels_long | order_month, owner | [주 원인 비율] | 선 그래프, 물류 선만 굵게 | [표본 충분] = 참, 주 |
| 1-5 고객 주별 물류 비중 | complaint_labels_long | customer_state (지도) | [주 원인 비율] (owner = 물류) | 채워진 지도 | 월 |

- 1-1 KPI는 `IF [owner] = "물류" AND [is_primary] = 1`, `IF [label] = "NOT_RECEIVED"` 조건을 넣은 COUNTD를 [전체 리뷰 수]로 나눠서 만든다.
- 1-4는 주문 2016-09, 2018-09, 2018-10(리뷰 100건 미만)이 빠진 21개월만 보인다.

**필터 동작**
- 1-5 지도에서 주를 클릭하면 1-1~1-4가 그 주로 필터링된다(동작: 필터, 선택 해제 시 모든 값 표시).
- 1-3에서 주체를 클릭하면 1-2가 그 주체의 유형만 강조된다(동작: 하이라이트, `owner` 기준).
- 1-4 날짜 범위는 대시보드 상단의 `order_month` 필터로 조정한다.

## 대시보드 ② 배송 지연의 영향 (Q2)

**목적**: 예상 배송일보다 늦게 받을수록 평점이 얼마나 떨어지고 불만이 무엇으로 바뀌는지, 그리고 지연이 어느 지역에 몰리는지 보여 준다.

**핵심 메시지 (대시보드 제목)**: "하루만 늦어도 저평점이 3배: 1~3일 지연 주문의 1~2점 비율 32.1% (7일 이상 일찍 받으면 9.0%)"

데이터 원본 필터는 `orders_fact.exclude_delivery_metrics = 0`(배송 지표 대상 96,447건)이다.

| 시트 | 파일 | 차원 | 측정값 | 차트 | 필터 |
|---|---|---|---|---|---|
| 2-1 KPI | orders_fact | [지연 여부] | AVG(is_late), [1~2점 비율] (지연 / 제때) | 숫자 타일 (지연율 6.77%, 1~2점 62.4% vs 9.3%) | 주, 월 |
| 2-2 지연 구간별 평점 | orders_fact | delay_bucket (delay_bucket_order 정렬) | AVG(review_score) 막대 + [1~2점 비율]·5점 비율 선 | 이중 축 (막대 + 선) | 주, 월 |
| 2-3 지연 구간별 불만 구성 | orders_fact | delay_bucket, owner | COUNT(order_id) 구성비 (표 계산: 구간 안에서 합계 대비 %) | 100% 누적 막대, 주체 고정 색 | owner ≠ "분류 대상 아님", NULL 제외, 주, 월 |
| 2-4 고객 주별 지연율 | state_summary | customer_state (지도) | late_rate (색), n_late (툴팁) | 채워진 지도, 경고색 순차 | meets_min_orders = 1 |
| 2-5 주별 지연율 vs 물류 불만 | state_summary | customer_state | late_rate, logistics_rate | 나란한 가로 막대 (지연율 높은 순) | meets_min_orders = 1 |

추가 계산된 필드:

```text
// [5점 비율] (orders_fact)
AVG(IF [review_score] = 5 THEN 1 ELSEIF NOT ISNULL([review_score]) THEN 0 END)

// [지연 구간 경고색 그룹] (orders_fact) — 2-2 막대 색
IF [delay_bucket_order] <= 2 THEN "빠름"
ELSEIF [delay_bucket_order] = 3 THEN "당일"
ELSEIF [delay_bucket_order] = 4 THEN "약한 지연"
ELSE "강한 지연" END
```

**필터 동작**
- 2-4 지도에서 주를 클릭하면 2-1·2-2·2-3이 그 주로 필터링된다(`customer_state` 관계를 통해 orders_fact에 적용).
- 2-2에서 지연 구간을 클릭하면 2-3의 같은 구간이 하이라이트된다.
- 툴팁: 2-2에 구간별 리뷰 있는 주문 수(`COUNT([is_low_score])`)를 넣어 작은 구간(예상일 당일 1,280건)의 표본 크기를 보여 준다.

## 대시보드 ③ 개선 우선순위 (Q4·Q5)

**목적**: 어떤 개선을 먼저 해야 1~2점 리뷰가 가장 많이 줄어드는지 효과·실행 가능성·근거와 함께 보여 주고, 바로 관리할 판매자와 지역을 짚는다.

**핵심 메시지 (대시보드 제목)**: "SP·RJ·MG 지연 개선과 문제 판매자 60명 관리부터: 추천 묶음으로 연간 1~2점 리뷰 1,774건(15.5%) 감소"

| 시트 | 파일 | 차원 | 측정값 | 차트 | 필터 |
|---|---|---|---|---|---|
| 3-1 KPI | q5_scenarios | intervention (row_type = 묶음) | reduction_mean, share_of_low | 숫자 타일 (추천 묶음 1,774건 15.5%, 전국 확대 2,370건 20.8%) | - |
| 3-2 개선안별 연간 감소 | q5_scenarios | intervention (priority 정렬), scenario | reduction_mean (막대), reduction_low~high (오차선: 참조 구간 또는 간트) | 가로 막대, 시나리오별 색 | row_type = 단독 |
| 3-3 효과 vs 실행 가능성 | q5_scenarios | intervention | X: reduction_mean, Y: [실행 가능성 점수], 크기: [근거 점수], 레이블: priority | 산점도 | row_type = 단독, scenario_level = 0.5 |
| 3-4 우선순위 표 | q5_scenarios | priority, intervention, owner, feasibility, evidence, reason | reduction_mean (50%) | 텍스트 표 | row_type ∈ {단독, 보완}, scenario_level = 0.5 또는 NULL |
| 3-5 관리 대상 판매자 | seller_summary | seller_id, seller_state, main_complaint_type | n_orders, seller_ctrl_rate_raw, seller_ctrl_rate_adj, excess_complaints, late_rate | 텍스트 표 (excess_complaints 내림차순, 상위 20) | is_watch_list = 1 |
| 3-6 판매자 보정 전후 | seller_summary | seller_id | X: seller_ctrl_rate_raw, Y: seller_ctrl_rate_adj, 크기: n_orders, 색: is_watch_list | 산점도 (+ 대각선 참조선) | meets_min_orders = 1 |
| 3-7 주별 지연 건수 | state_summary | customer_state | n_late | 가로 막대 (내림차순, SP·RJ·MG 강조색) | meets_min_orders = 1 |

추가 계산된 필드:

```text
// [시나리오 이름] (q5_scenarios) — 3-2 색
IF [scenario_level] = 0.3 THEN "30%" ELSEIF [scenario_level] = 0.5 THEN "50%" ELSEIF [scenario_level] = 1 THEN "100%" END

// [집중 대상 주] (state_summary) — 3-7 강조
IF [customer_state] = "SP" OR [customer_state] = "RJ" OR [customer_state] = "MG" THEN "집중 대상 (A')" ELSE "그 외" END
```

**필터 동작**
- 3-3이나 3-4에서 개선안을 클릭하면 3-2에서 같은 개선안이 하이라이트된다(`key` 기준).
- 3-6에서 점을 클릭하면 3-5 표가 그 판매자로 필터링된다(`seller_id`). 선택을 해제하면 관리 대상 전체가 보인다.
- 3-7은 다른 시트와 연결하지 않는다. 판매자 주(seller_state)와 고객 주(customer_state)는 다른 개념이라 섞지 않는다.

**표시 주의**: 3-2 하단에 "관찰 데이터 기반 시나리오 추정, 인과 효과를 보장하지 않음"과 "(E) 선제 안내는 1~2점 감소를 추정하지 않음(응대 불만 최대 818건)"을 주석으로 넣는다.

## 검산 항목

대시보드를 만든 뒤 아래 숫자가 분석 리포트(`reports/analysis/`)와 같은지 확인한다. 아래 값은 `export_tableau.py` 결과로 확인했다.

| # | 대시보드 | 계산 | 기대값 | 리포트 |
|---|---|---|---|---|
| 1 | ② 2-2 | orders_fact, exclude_delivery_metrics = 0, delay_bucket = "1~3일 지연"의 [1~2점 비율] | **32.1%** (7일 이상 빠름 9.0%) | q2_delivery_delay.md |
| 2 | ② 2-1 | orders_fact, exclude_delivery_metrics = 0의 AVG(is_late) | **6.77%** (6,534 / 96,447) | q2_delivery_delay.md |
| 3 | ① 1-1 | complaint_labels_long의 COUNTD(review_id) / 미수령 다중 라벨 비율 / 물류 주 원인 비율 | **14,286건 / 25.2% / 33.9%** | q1_complaint_causes.md |
| 4 | ③ 3-5 | seller_summary, is_watch_list = 1의 판매자 수와 excess_complaints 1위 | **60명**, 1위 7c67e144…(주문 966, 보정 불만율 19.7%) | q4_complaint_hotspots.md |
| 5 | ② 2-4 | state_summary의 late_rate (RJ / AL) | **11.9% / 20.8%** | q4_complaint_hotspots.md |
| 6 | ③ 3-1 | q5_scenarios, 묶음 "추천 묶음"의 reduction_mean / share_of_low | **1,774건 / 15.5%** | q5_recommendations.md |

**자주 틀리는 지점**
- **3번**: 물류 비중은 반드시 `complaint_labels_long`(리뷰 기준)으로 계산한다. `orders_fact`의 `owner`(주문의 대표 리뷰 기준)로 계산하면 33.8%가 나온다. 분류된 리뷰가 있는 주문은 14,376건이고, 리뷰가 여러 개인 주문은 대표 리뷰 1개만 반영되기 때문이다.
- **1·2번**: 데이터 원본 필터(`exclude_delivery_metrics = 0`)를 빼면 값이 달라진다.

## 데이터 갱신 순서

1. `python run_pipeline.py`: 품질 검사, 적재, 뷰, 검증
2. `notebooks/07_q5_recommendations.ipynb` 실행: `data/processed/q5/`에 Q5 시나리오 결과 저장
3. `python src/analysis/export_tableau.py`: `data/tableau/` CSV 다시 만들기
4. Tableau에서 데이터 원본 새로 고침 후 위 검산 항목 확인
