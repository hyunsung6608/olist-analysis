# LLM 분류 평가: pilot_v2_post3 vs pilot

- 평가 대상 라벨: labels(후처리 후)
- 모델: gemini-3.5-flash-lite / 분류 체계: v0.5 / prompt_hash: b0abafe22cb0
- 평가 건수: 100건 (정답에 있는데 결과에 없는 review_id: 0건, 정답에 없는 결과: 0건)

## 전체 지표

| 지표 | 값 |
|---|---|
| 완전 일치율 | 0.920 |
| micro F1 | 0.960 (P 0.970 / R 0.949) |
| macro F1 | 0.958 (P 0.978 / R 0.942) |
| 주 원인 정확도 | 0.960 |
| 주 원인 Cohen's kappa | 0.952 |

macro F1은 정답 건수 0인 유형도 0점으로 포함해 평균한다.

## 유형별 지표

| 유형 | 정밀도 | 재현율 | F1 | 정답 건수 | LLM 부여 | 빠뜨림(FN) | 잘못 붙임(FP) |
|---|---|---|---|---|---|---|---|
| NOT_RECEIVED | 0.967 | 1.000 | 0.983 | 29 | 30 | 0 | 1 |
| WRONG_MISSING | 0.955 | 0.955 | 0.955 | 22 | 22 | 1 | 1 |
| DAMAGED | 1.000 | 1.000 | 1.000 | 10 | 10 | 0 | 0 |
| NOT_AS_DESCRIBED | 1.000 | 0.909 | 0.952 | 11 | 10 | 1 | 0 |
| LOW_QUALITY | 0.917 | 0.786 | 0.846 | 14 | 12 | 3 | 1 |
| SHIPPING_COST | 1.000 | 1.000 | 1.000 | 5 | 5 | 0 | 0 |
| DELAY | 1.000 | 0.960 | 0.980 | 25 | 24 | 1 | 0 |
| SERVICE | 0.923 | 1.000 | 0.960 | 12 | 13 | 0 | 1 |
| OTHER | 1.000 | 1.000 | 1.000 | 2 | 2 | 0 | 0 |
| UNCLEAR | 1.000 | 1.000 | 1.000 | 4 | 4 | 0 | 0 |
| NO_COMPLAINT | 1.000 | 0.750 | 0.857 | 4 | 3 | 1 | 0 |

## 주 원인 혼동행렬 (행: 정답, 열: LLM)

| 정답 \ LLM | NOT_RECEIVED | WRONG_MISSING | DAMAGED | NOT_AS_DESCRIBED | LOW_QUALITY | SHIPPING_COST | DELAY | SERVICE | OTHER | UNCLEAR | NO_COMPLAINT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NOT_RECEIVED | 29 | · | · | · | · | · | · | · | · | · | · |
| WRONG_MISSING | 1 | 20 | · | · | · | · | · | 1 | · | · | · |
| DAMAGED | · | · | 9 | · | · | · | · | · | · | · | · |
| NOT_AS_DESCRIBED | · | 1 | · | 10 | · | · | · | · | · | · | · |
| LOW_QUALITY | · | · | · | · | 10 | · | · | · | · | · | · |
| SHIPPING_COST | · | · | · | · | · | 5 | · | · | · | · | · |
| DELAY | · | · | · | · | · | · | 5 | · | · | · | · |
| SERVICE | · | · | · | · | · | · | · | · | · | · | · |
| OTHER | · | · | · | · | · | · | · | · | 1 | · | · |
| UNCLEAR | · | · | · | · | · | · | · | · | · | 4 | · |
| NO_COMPLAINT | · | · | · | · | 1 | · | · | · | · | · | 3 |

## 후처리 규칙 효과 (LLM 원래 결과 대비)

| 규칙 | 세부 | 적용 | 정답에 가까워짐 | 변화 없음 | 틀어짐 |
|---|---|---|---|---|---|
| R1_K_DELAY | (전체) | 6 | 6 | 0 | 0 |
| R1_K_DELAY | ate hoje | 1 | 1 | 0 | 0 |
| R1_K_DELAY | ate o momento | 4 | 4 | 0 | 0 |
| R1_K_DELAY | ate o presente momento | 1 | 1 | 0 | 0 |
| R2_EVIDENCE | (전체) | 2 | 2 | 0 | 0 |
