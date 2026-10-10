# Tableau 대시보드 설계서

Olist 리뷰 불만 분석(Q1~Q5)의 결과를 대시보드 3개로 보여 준다. 이 문서만 보고 Tableau에서 대시보드를 재현할 수 있도록 데이터, 시트, 계산식, 필터 동작, 색상, 검산 항목을 정리했다. 아래 내용은 실제로 만든 통합 문서(`dashboards/olist_complaint_dashboard.twbx`)에 맞춰 고친 것이다.

## 구현 현황

- **통합 문서**: `dashboards/olist_complaint_dashboard.twbx` (데이터 추출 포함, 대시보드 3개, 시트 15개)
- **대시보드 이미지**: `reports/figures/dashboard_1_complaints.png`, `dashboard_2_delay.png`, `dashboard_3_priorities.png`
- **공유 방식**: Tableau Public에 게시하지 않고, 대시보드 이미지와 통합 문서(.twbx)로 공유한다. .twbx에는 데이터 추출이 들어 있어 Tableau Desktop이나 Tableau Reader로 바로 열 수 있다.

### 설계와 달라진 점

| 구분 | 처음 설계 | 실제 구현 | 이유 |
|---|---|---|---|
| ③ 시트 수 | 7개 (3-1 ~ 3-7) | 5개, 번호를 새로 매김 (3-1 KPI, 3-2 개선안별 연간 감소, 3-3 우선순위 표, 3-4 관리 대상 판매자, 3-5 주별 지연 건수) | 아래 두 시트를 뺌 |
| ③ 효과 vs 실행 가능성 산점도 (구 3-3) | 포함 | 제외 | 우선순위 표와 정보가 겹침. 같은 차트는 `reports/figures/q5_impact_feasibility.png`에 있음 |
| ③ 판매자 보정 전후 산점도 (구 3-6) | 포함 | 제외 | 분석 방법을 설명하는 차트라 노트북·리포트로 충분함(`reports/figures/q4_seller_shrinkage.png`) |
| ③ 우선순위 표의 감소 건수 열 | 표에 포함 | 표에서 뺌 | 공간 부족. 같은 숫자를 3-2 막대에서 보여 줌 |
| ③ 판매자 클릭 → 판매자 표 필터 (구 3-6 → 3-4) | 있음 | 없음 | 산점도를 빼서 동작도 뺌 |
| 비율 계산식의 분모 | `SUM([전체 리뷰 수])` | `MIN([전체 리뷰 수])` | EXCLUDE LOD 값이 행마다 반복돼 SUM이면 분모가 부풀려짐 |
| [전체 리뷰 수]의 EXCLUDE 목록 | label, label_ko, label_order, owner, is_primary | + **[물류 강조]** | 1-4에서 [물류 강조]를 크기에 넣으면 분모가 그 값으로 나뉘어 바뀜 |
| 1-5 지도 | 모든 주 | 리뷰 30건 미만인 주 제외 | 리뷰가 적은 주의 비율이 크게 흔들림 |
| 2-4 지도 클릭 필터 | "필터로 사용"으로 다른 시트 전체 | 대시보드 동작으로 대상(2-1, 2-2, 2-3)을 직접 지정, 2-5는 제외 | 2-5는 주별 비교 차트라 한 주로 필터링하면 의미가 없음 |
| 3-4·3-5 필터 | 일반 필터 | Is Watch List(3-4), Meets Min Orders(3-5)를 **컨텍스트 필터**로 지정 | 상위 N 필터가 먼저 적용되면 3-4가 13명만 나옴 |
| 2-5 물류 불만 비율 막대 색 | 지정 안 함 | `#fc9272` | 지연율 막대(`#cb181d`)와 구분 |
| 1-2 막대 색 | 다중 연한 색 / 주 원인 진한 색 | 다중 라벨 `#9ecae1`, 주 원인 `#2171b5` | 값을 고정 |
| ② 제목 | "하루만 늦어도 저평점이 3배" | "1~3일만 늦어도 1~2점 비율이 3배 이상: 1~3일 지연 주문 32.1% vs 제때 받은 주문 9.3%" | 비교한 실제 구간(1~3일 지연)과 비교 대상(제때 받은 주문)을 밝힘. 32.1% ÷ 9.3% ≈ 3.5배 |
| ③ 제목 | "… 1,774건(15.5%) 감소" | "… 1,774건(15.5%) 감소 추정" | Q5 효과는 시나리오 추정값이라 실제 결과처럼 읽히지 않게 함 |
| 시트 제목 | 시트 이름(번호 포함) | 대시보드에서 한국어 설명형 제목 | 아래 "시트 제목" 표 |
| 공유 | 정하지 않음 | 이미지 + .twbx | Tableau Public 게시 안 함 |

### 해결된 항목

통합 문서를 읽어 확인했던 항목과 처리 결과다.

- **② 대시보드 제목 (해결됨, 2026-10-10)**: "하루만 늦어도 …"는 하루 지연과 비교한 것처럼 읽혀서, 실제 구간과 비교 대상을 밝힌 "1~3일만 늦어도 1~2점 비율이 3배 이상: 1~3일 지연 주문 32.1% vs 제때 받은 주문 9.3%"로 바꿨다. 중간 수정본의 "지연 주문 32.1%"는 지연 주문 전체(1~2점 비율 62.4%, 2-1 KPI)로 읽힐 수 있어 "1~3일 지연 주문 32.1%"로 고쳤다. 수정한 .twbx(2026-10-10 22:00 저장본)의 제목이 설계서와 같음을 확인했고, 대시보드 이미지(`reports/figures/dashboard_2_delay.png`)도 다시 내보냈다.

- **③ 대시보드 제목 (해결됨, 2026-10-10)**: Q5 효과가 실제 결과처럼 읽히지 않도록 "… 1,774건(15.5%) 감소"를 "… 1,774건(15.5%) 감소 추정"으로 바꿨다. 수정한 .twbx(2026-10-10 저장본)의 제목이 설계서와 같음을 확인했고, 대시보드 이미지(`reports/figures/dashboard_3_priorities.png`)도 다시 내보냈다.

- **2-2 하이라이트 동작의 대상 (해결됨, 2026-10-09)**: 처음에는 동작의 대상이 2-2 시트 자신으로만 지정돼 있어서, 설계("2-2에서 지연 구간을 클릭하면 2-3의 같은 구간이 강조")와 달랐다. 대시보드 동작 "2-2 구간 -> 2-3 강조"로 바꾸고 대상에 2-3을 추가했다(대시보드 ②에서 2-1·2-4·2-5 제외, `Delay Bucket` 기준). 수정한 .twbx에서 반영을 확인했다.

## 데이터

`data/tableau/`의 CSV 5개(UTF-8, BOM 없음, 쉼표 구분). `python src/analysis/export_tableau.py`로 다시 만든다.

| 파일 | 한 행 | 행 수 | 주요 컬럼 |
|---|---|---|---|
| `orders_fact.csv` | 주문 1건 | 99,441 | order_month, customer_state, exclude_delivery_metrics, is_late, delay_days, delay_bucket(+order), delivery_days, n_items, n_sellers, items_value, freight_value, has_review, review_score, is_low_score, is_classified, 유형 11개(0/1), primary_label(_ko), owner |
| `complaint_labels_long.csv` | 리뷰 × 붙은 유형 1개 | 18,992 (리뷰 14,286) | review_id, order_id, order_month, customer_state, label, label_ko, label_order, owner, is_primary |
| `seller_summary.csv` | 판매자 1명 | 3,073 | seller_state, n_orders, meets_min_orders, n_seller_ctrl, seller_ctrl_rate_raw/adj, excess_complaints(소수 1자리), n_low, low_rate_raw/adj, n_delivery_base, n_late, late_rate, is_watch_list, main_complaint_type |
| `state_summary.csv` | 고객 주 1개 | 27 | customer_state(2자리 코드), n_reviewed_orders, meets_min_orders, n_delivery_base, n_late, late_rate, n_low, low_rate, n_logistics, logistics_rate |
| `q5_scenarios.csv` | 개선안 × 시나리오 | 21 | row_type(단독/세부/묶음/보완), key, intervention, scenario_level, reduction_mean/low/high, share_of_low, priority, owner, feasibility, evidence, reason |

**값 규칙**
- `orders_fact`의 유형 11개 컬럼은 **분류되지 않은 주문(4~5점·텍스트 없음·리뷰 없음)이면 빈 값**이다. 그래서 `AVG([DELAY])`가 곧 "분류된 리뷰 중 비율"이 된다.
- `is_late`, `delay_days`, `delivery_days`는 배송 지표 대상이 아닌 주문(`exclude_delivery_metrics = 1`)이면 빈 값이다.
- `owner`는 주 원인 기준 개선 주체다. 분류되지 않은 리뷰는 `분류 대상 아님`, 리뷰가 없으면 빈 값이다.
- `state_summary`와 `seller_summary`의 비율은 건수 ÷ 분모로 계산했다. 건수 컬럼으로 다시 계산해도 같은 값이 나온다.
- 유형·주체·지연 구간의 이름과 색은 `src/analysis/mappings.py`에서 정의한 값을 그대로 쓴다.

**데이터 원본과 연결 방식** (통합 문서 기준)
- `complaint_labels_long`: 대시보드 ①. 지역 필터는 같은 원본의 `customer_state`로 건다.
- `orders_fact+`: 대시보드 ②. `orders_fact`와 `state_summary`를 `customer_state`로 관계(Relationship) 연결한 원본이다. 데이터 원본 필터 `exclude_delivery_metrics = 0`(배송 지표 대상 96,447건)이 걸려 있다.
- `state_summary`, `q5_scenarios`, `seller_summary`: 대시보드 ②의 지도·비교 차트와 ③에서 각각 독립 원본으로 쓴다.

**지리 역할**: `customer_state`, `seller_state`는 지리적 역할을 "주/도"로, 국가는 Brazil로 지정한다.

## 계산된 필드

통합 문서에 들어 있는 식 그대로다.

```text
// ── complaint_labels_long (대시보드 ①) ──

// [전체 리뷰 수] — 유형·주체를 나눠 보여도 분모는 필터 안의 전체 리뷰 수
{ EXCLUDE [label], [label_ko], [label_order], [owner], [is_primary], [물류 강조] : COUNTD([review_id]) }

// 비율 계산식의 분모는 MIN([전체 리뷰 수])를 쓴다. EXCLUDE LOD 값이 행마다 반복되므로 SUM이면 분모가 부풀려진다.
// [다중 라벨 비율] — 해당 유형(주체)이 붙은 리뷰 / 전체 리뷰
COUNTD([review_id]) / MIN([전체 리뷰 수])

// [주 원인 비율]
COUNTD(IF [is_primary] = 1 THEN [review_id] END) / MIN([전체 리뷰 수])

// [물류 주 원인 비율] (1-1 KPI, 1-5 지도)
COUNTD(IF [owner] = "물류" AND [is_primary] = 1 THEN [review_id] END) / MIN([전체 리뷰 수])

// [미수령 비율] (1-1 KPI)
COUNTD(IF [label] = "NOT_RECEIVED" THEN [review_id] END) / MIN([전체 리뷰 수])

// [월 리뷰 수] / [표본 충분] — 리뷰 100건 미만인 달은 추이에서 뺀다(Q1 기준)
{ FIXED [order_month] : COUNTD([review_id]) }
[월 리뷰 수] >= 100

// [물류 강조] — 1-4에서 물류 선만 굵게 (크기 선반). [전체 리뷰 수]의 EXCLUDE 목록에 반드시 넣는다
IF [owner] = "물류" THEN "물류" ELSE "그 외" END

// [주 리뷰 충분] — 1-5 지도에서 리뷰 30건 미만인 주 제외
{ FIXED [customer_state] : COUNTD([review_id]) } >= 30

// ── orders_fact+ (대시보드 ②) ──

// [지연율]
AVG([is_late])

// [1~2점 비율] — 리뷰 없는 주문은 is_low_score가 빈 값이라 자동으로 빠진다
AVG([is_low_score])

// [지연 주문 1~2점 비율] / [제때 주문 1~2점 비율] (2-1 KPI)
AVG(IF [is_late] = 1 THEN [is_low_score] END)
AVG(IF [is_late] = 0 THEN [is_low_score] END)

// ── q5_scenarios, seller_summary, state_summary (대시보드 ③) ──

// [시나리오 이름] — 3-2 색
IF [scenario_level] = 0.3 THEN "30%"
ELSEIF [scenario_level] = 0.5 THEN "50%"
ELSEIF [scenario_level] = 1 THEN "100%" END

// [판매자] — 3-4 표에서 판매자 ID를 앞 8자리로 줄여 표시
LEFT([seller_id], 8) + "…"

// [집중 대상 주] — 3-5 강조색
IF [customer_state] = "SP" OR [customer_state] = "RJ" OR [customer_state] = "MG" THEN "집중 대상 (A')" ELSE "그 외" END
```

`[전체 리뷰 수]`는 EXCLUDE LOD라서 차원 필터(주, 월)는 반영되고, 유형·주체 필터는 반영되지 않는다. 유형 필터를 걸어도 분모가 바뀌지 않는다는 뜻이며, 의도한 동작이다. **시트에 새 차원(색·크기·세부 정보 포함)을 넣을 때는 EXCLUDE 목록에도 추가해야 분모가 유지된다.**

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
- 약한 경고 `#fc9272`: 1~3일 지연, 보조 지표(2-5의 물류 불만 비율 막대)
- 중립 `#bdbdbd`: 제때·예정보다 빠름

**시트별 고정 색**
- 1-2: 다중 라벨 `#9ecae1`, 주 원인 `#2171b5`
- 2-5: 지연율 `#cb181d`(진한 색), 물류 불만 비율 `#fc9272`(연한 색)

**지연 구간** (`delay_bucket_order` 순서): 7일 이상 빠름 `#9ecae1` → 1~6일 빠름 `#c6dbef` → 예상일 당일 `#bdbdbd` → 1~3일 지연 `#fc9272` → 4~7일 지연 `#fb6a4a` → 8~14일 지연 `#cb181d` → 15일 이상 지연 `#67000d`. 배송 지표 없음은 표시하지 않는다.

**연속 색 범위**: 지도 같은 연속 값은 흰색에서 경고색(`#cb181d`)으로 가는 단색 순차 팔레트를 쓴다. 물류 불만 지도는 물류 색(`#d62728`) 계열을 쓴다.

**정렬 규칙**
- 유형은 `label_order`(주 원인 우선순위) 순서로 정렬한다.
- 주체는 물류 → 판매자 출고 → 상품 → 판매자 응대 → 플랫폼 정책 → 기타 → 불만 없음 순서로 고정한다.

## 시트 제목

대시보드에서는 시트 이름 대신 아래 제목을 보인다(KPI 시트는 제목을 숨김).

| 시트 | 대시보드에 보이는 제목 |
|---|---|
| 1-1 KPI | (제목 없음) |
| 1-2 유형별 비중 | 불만 유형별 비중 |
| 1-3 개선 주체별 비중 | 개선 주체별 비중 |
| 1-4 월별 주체 비중 추이 | 월별 개선 주체 비중 추이 (주 원인 기준) |
| 1-5 고객 주별 물류 비중 | 고객 주별 물류 불만 비중 (리뷰 30건 이상) |
| 2-1 KPI | (제목 없음) |
| 2-2 지연 구간별 평점 | 지연 구간별 평균 평점과 1~2점 비율 |
| 2-3 지연 구간별 불만 구성 | 지연 구간별 불만 주체 구성 |
| 2-4 고객 주별 지연율 | 고객 주별 배송 지연율 |
| 2-5 주별 지연율 vs 물류 불만 | 주별 지연율(진한 색)과 물류 불만 비율(연한 색) |
| 3-1 KPI | (제목 없음) |
| 3-2 개선안별 연간 감소 | 개선안별 연간 1~2점 리뷰 감소 (시나리오별) |
| 3-3 우선순위 표 | 개선안 우선순위 (50% 시나리오 기준) |
| 3-4 관리 대상 판매자 | 관리 대상 판매자 상위 20명 (불만율 보정 전·후, 초과 불만 순) |
| 3-5 주별 지연 건수 | 주별 지연 주문 건수 (빨강: 집중 개선 대상 SP·RJ·MG) |

## 대시보드 ① 불만 개요 (Q1)

**목적**: 글로 불만을 남긴 1~3점 리뷰의 불만 원인 구성과 그 원인을 고쳐야 할 주체를 한눈에 보여 준다.

**제목**: "저점 리뷰 불만의 3분의 1(33.9%)은 물류, 가장 큰 단일 원인은 미수령(25.2%)"

| 시트 | 원본 | 차원 | 측정값 | 차트 | 필터 |
|---|---|---|---|---|---|
| 1-1 KPI | complaint_labels_long | - | COUNTD(review_id), [물류 주 원인 비율], [미수령 비율] | 숫자 타일 3개 | 주 (동작) |
| 1-2 유형별 비중 | complaint_labels_long | label_ko (label_order 정렬) | [다중 라벨 비율] `#9ecae1`, [주 원인 비율] `#2171b5` (Measure Names로 나란히) | 가로 막대 | 주 (동작) |
| 1-3 개선 주체별 비중 | complaint_labels_long | owner | [다중 라벨 비율], [주 원인 비율] | 세로 막대, 주체 고정 색 | 주 (동작) |
| 1-4 월별 주체 비중 추이 | complaint_labels_long | order_month, owner, `[물류 강조]` → 크기 | [주 원인 비율] | 선 그래프, 물류 선만 굵게 | [표본 충분] = 참, 주 (동작) |
| 1-5 고객 주별 물류 비중 | complaint_labels_long | customer_state (지도) | [물류 주 원인 비율] | 채워진 지도 | [주 리뷰 충분] = 참 |

- 1-4는 주문 2016-09, 2018-09, 2018-10(리뷰 100건 미만)이 빠진 21개월만 보인다.

**대시보드 동작**
- **필터**: 1-5 지도에서 주를 클릭하면 대시보드의 시트들이 그 주로 필터링된다. 선택을 해제하면 모든 값이 보인다.
- **하이라이트**: 1-3에서 주체를 클릭하면 1-2에서 그 주체의 유형이 강조된다(`owner` 기준, 대상 1-2만).

## 대시보드 ② 배송 지연의 영향 (Q2)

**목적**: 예상 배송일보다 늦게 받을수록 평점이 얼마나 떨어지고 불만이 무엇으로 바뀌는지, 그리고 지연이 어느 지역에 몰리는지 보여 준다.

**제목**: "1~3일만 늦어도 1~2점 비율이 3배 이상: 1~3일 지연 주문 32.1% vs 제때 받은 주문 9.3%"

| 시트 | 원본 | 차원 | 측정값 | 차트 | 필터 |
|---|---|---|---|---|---|
| 2-1 KPI | orders_fact+ | - | [지연율], [지연 주문 1~2점 비율], [제때 주문 1~2점 비율] | 숫자 타일 (지연율 6.77%, 1~2점 62.4% vs 9.3%) | 주 (동작) |
| 2-2 지연 구간별 평점 | orders_fact+ | delay_bucket (delay_bucket_order 정렬) | AVG(review_score) 막대 + [1~2점 비율] 선 | 이중 축 (막대 + 선) | 주 (동작) |
| 2-3 지연 구간별 불만 구성 | orders_fact+ | delay_bucket, owner | COUNT(order_id) 구성비 (표 계산: 구간 안에서 합계 대비 %) | 100% 누적 막대, 주체 고정 색 | owner = 7개 주체("분류 대상 아님" 제외), 주 (동작) |
| 2-4 고객 주별 지연율 | state_summary | customer_state (지도) | late_rate (색), n_late (툴팁) | 채워진 지도, 경고색 순차 | meets_min_orders = 1 |
| 2-5 주별 지연율 vs 물류 불만 | state_summary | customer_state | late_rate `#cb181d`, logistics_rate `#fc9272` | 나란한 가로 막대 (지연율 높은 순) | meets_min_orders = 1 |

**대시보드 동작**
- **필터**: 2-4 지도에서 주를 클릭하면 2-1·2-2·2-3이 그 주로 필터링된다. "필터로 사용" 대신 대시보드 동작으로 대상을 직접 지정했고, **2-5는 대상에서 뺐다**(주별 비교 차트라 한 주만 남으면 의미가 없음). 필드는 관계로 연결된 `Customer State (State Summary.Csv)`다.
- **하이라이트**: 2-2에서 지연 구간을 클릭하면 2-2와 2-3에서 같은 구간이 강조된다(동작 "2-2 구간 -> 2-3 강조", `Delay Bucket` 기준, 대상 2-2·2-3).
- 툴팁: 2-2에 구간별 리뷰 있는 주문 수(`COUNT([is_low_score])`)를 넣어 작은 구간(예상일 당일 1,280건)의 표본 크기를 보여 준다.

## 대시보드 ③ 개선 우선순위 (Q4·Q5)

**목적**: 어떤 개선을 먼저 해야 1~2점 리뷰가 가장 많이 줄어드는지 효과·실행 가능성·근거와 함께 보여 주고, 바로 관리할 판매자와 지역을 짚는다.

**제목**: "SP·RJ·MG 지연 개선과 문제 판매자 60명 관리부터: 추천 묶음으로 연간 1~2점 리뷰 1,774건(15.5%) 감소 추정"

| 시트 | 원본 | 차원 | 측정값 | 차트 | 필터 |
|---|---|---|---|---|---|
| 3-1 KPI | q5_scenarios | intervention | reduction_mean, share_of_low | 숫자 타일 (추천 묶음 1,774건 15.5%, 전국 확대 2,370건 20.8%) | row_type = 묶음, intervention = 추천 묶음·기준 |
| 3-2 개선안별 연간 감소 | q5_scenarios | intervention (priority 정렬), [시나리오 이름] | reduction_mean (막대), reduction_low~high (오차선) | 가로 막대, 시나리오별 색 | row_type = 단독 |
| 3-3 우선순위 표 | q5_scenarios | priority, intervention, owner, feasibility, evidence, reason | - (감소 건수 열은 공간 문제로 빼고 3-2에서 보여 줌) | 텍스트 표 | row_type ∈ {단독, 보완}, scenario_level = 0.5 또는 NULL |
| 3-4 관리 대상 판매자 | seller_summary | [판매자], seller_state, main_complaint_type | n_orders, seller_ctrl_rate_raw, seller_ctrl_rate_adj, excess_complaints, late_rate | 텍스트 표 (excess_complaints 내림차순, 상위 20) | **is_watch_list = 1 (컨텍스트)**, 상위 20 |
| 3-5 주별 지연 건수 | state_summary | customer_state, `[집중 대상 주]` → 색 | n_late | 가로 막대 (내림차순, 상위 10, SP·RJ·MG 강조) | **meets_min_orders = 1 (컨텍스트)**, 상위 10 |

**대시보드 동작**
- **하이라이트**: 3-3 우선순위 표에서 개선안을 클릭하면 3-2에서 같은 개선안이 강조된다(`intervention` 기준, 대상 3-2만).
- 3-5는 다른 시트와 연결하지 않는다. 판매자 주(seller_state)와 고객 주(customer_state)는 다른 개념이라 섞지 않는다.

**표시 주의**: 3-2 하단에 "관찰 데이터 기반 시나리오 추정, 인과 효과를 보장하지 않음"과 "(E) 선제 안내는 1~2점 감소를 추정하지 않음(응대 불만 최대 818건)"을 주석으로 넣는다.

## 검산 항목

대시보드를 만든 뒤 아래 숫자가 분석 리포트(`reports/analysis/`)와 같은지 확인한다. 아래 값은 `export_tableau.py` 결과로 확인했다.

| # | 시트 | 계산 | 기대값 | 리포트 |
|---|---|---|---|---|
| 1 | ② 2-2 | orders_fact+, delay_bucket = "1~3일 지연"의 [1~2점 비율] | **32.1%** (7일 이상 빠름 9.0%) | q2_delivery_delay.md |
| 2 | ② 2-1 | orders_fact+의 [지연율] | **6.77%** (6,534 / 96,447) | q2_delivery_delay.md |
| 3 | ① 1-1 | complaint_labels_long의 COUNTD(review_id) / [미수령 비율] / [물류 주 원인 비율] | **14,286건 / 25.2% / 33.9%** | q1_complaint_causes.md |
| 4 | ③ 3-4 | seller_summary, is_watch_list = 1의 판매자 수와 excess_complaints 상위 3명 | **60명**, 115.9 / 70.9 / 45.8 (1위 7c67e144…, 주문 966, 보정 불만율 19.7%) | q4_complaint_hotspots.md |
| 5 | ② 2-4 | state_summary의 late_rate (RJ / AL) | **11.9% / 20.8%** | q4_complaint_hotspots.md |
| 6 | ③ 3-1 | q5_scenarios, 묶음 "추천 묶음"의 reduction_mean / share_of_low | **1,774건 / 15.5%** | q5_recommendations.md |

## 자주 틀리는 지점

- **물류 비중은 리뷰 기준으로 계산한다.** 반드시 `complaint_labels_long`으로 계산한다. `orders_fact`의 `owner`(주문의 대표 리뷰 기준)로 계산하면 33.8%가 나온다. 분류된 리뷰가 있는 주문은 14,376건이고, 리뷰가 여러 개인 주문은 대표 리뷰 1개만 반영되기 때문이다(검산 3번).
- **원본 필터를 빼면 값이 달라진다.** `orders_fact`의 데이터 원본 필터 `exclude_delivery_metrics = 0`을 빼면 검산 1·2번이 맞지 않는다.
- **비율의 분모는 MIN으로 집계한다.** `[전체 리뷰 수]`를 SUM으로 집계하면 행마다 반복된 값이 더해져 비율이 작게 나온다. 시트에 새 차원을 넣을 때는 EXCLUDE 목록에도 추가한다(1-4의 [물류 강조] 사례).
- **상위 N 필터는 컨텍스트 필터 뒤에 적용해야 한다.** 3-4·3-5에서 Is Watch List, Meets Min Orders를 컨텍스트 필터로 지정하지 않으면, 전체 판매자 중 상위 20명을 먼저 고른 뒤 관리 대상만 남겨서 3-4에 13명만 나온다.
- **CSV 열의 데이터 유형을 확인한다.** Tableau는 CSV를 처음 연결할 때 앞부분 값을 보고 열의 데이터 유형을 추측한다. 소수 열(예: `excess_complaints`, `late_rate`, `reduction_mean`)을 정수로 추측하면 소수가 잘려 보인다. 데이터 원본 탭에서 이런 열이 "숫자(소수)"인지 확인한다.
- **CSV 열 구성이 바뀌면 연결을 다시 읽는다.** `export_tableau.py`로 CSV를 다시 만들면서 열이 추가되거나 바뀌면(예: `state_summary`에 `n_low`, `n_logistics` 추가), "새로 고침"만으로는 새 열이 반영되지 않을 수 있다. 데이터 원본의 "연결 편집"으로 파일을 다시 지정해 열 구성을 다시 읽는다.

## 데이터 갱신 순서

1. `python run_pipeline.py`: 품질 검사, 적재, 뷰, 검증
2. `notebooks/07_q5_recommendations.ipynb` 실행: `data/processed/q5/`에 Q5 시나리오 결과 저장
3. `python src/analysis/export_tableau.py`: `data/tableau/` CSV 다시 만들기
4. Tableau에서 데이터 원본 새로 고침(열 구성이 바뀌었으면 연결 편집) 후 위 검산 항목 확인
5. 대시보드 이미지를 `reports/figures/dashboard_*.png`로 다시 내보내고 .twbx를 저장
