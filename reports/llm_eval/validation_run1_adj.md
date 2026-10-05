# LLM 분류 평가: validation_run1_adj vs adjudicated

- 평가 대상 라벨: labels(후처리 후)
- 모델: gemini-3.5-flash-lite / 분류 체계: v0.5 / prompt_hash: b0abafe22cb0
- 평가 건수: 100건 (정답에 있는데 결과에 없는 review_id: 0건, 정답에 없는 결과: 0건)

## 전체 지표

| 지표 | 값 |
|---|---|
| 완전 일치율 | 0.810 |
| micro F1 | 0.900 (P 0.921 / R 0.880) |
| macro F1 | 0.903 (P 0.927 / R 0.891) |
| 주 원인 정확도 | 0.890 |
| 주 원인 Cohen's kappa | 0.871 |

macro F1은 정답 건수 0인 유형도 0점으로 포함해 평균한다.

## 유형별 지표

| 유형 | 정밀도 | 재현율 | F1 | 정답 건수 | LLM 부여 | 빠뜨림(FN) | 잘못 붙임(FP) |
|---|---|---|---|---|---|---|---|
| NOT_RECEIVED | 1.000 | 0.706 | 0.828 | 17 | 12 | 5 | 0 |
| WRONG_MISSING | 1.000 | 0.933 | 0.966 | 30 | 28 | 2 | 0 |
| DAMAGED | 1.000 | 0.857 | 0.923 | 14 | 12 | 2 | 0 |
| NOT_AS_DESCRIBED | 0.800 | 1.000 | 0.889 | 8 | 10 | 0 | 2 |
| LOW_QUALITY | 1.000 | 0.800 | 0.889 | 10 | 8 | 2 | 0 |
| SHIPPING_COST | 1.000 | 1.000 | 1.000 | 2 | 2 | 0 | 0 |
| DELAY | 0.850 | 0.944 | 0.895 | 18 | 20 | 1 | 3 |
| SERVICE | 0.833 | 0.938 | 0.882 | 16 | 18 | 1 | 3 |
| OTHER | 0.714 | 0.625 | 0.667 | 8 | 7 | 3 | 2 |
| UNCLEAR | 1.000 | 1.000 | 1.000 | 2 | 2 | 0 | 0 |
| NO_COMPLAINT | 1.000 | 1.000 | 1.000 | 8 | 8 | 0 | 0 |

## 주 원인 혼동행렬 (행: 정답, 열: LLM)

| 정답 \ LLM | NOT_RECEIVED | WRONG_MISSING | DAMAGED | NOT_AS_DESCRIBED | LOW_QUALITY | SHIPPING_COST | DELAY | SERVICE | OTHER | UNCLEAR | NO_COMPLAINT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NOT_RECEIVED | 12 | · | · | · | · | · | 1 | 3 | 1 | · | · |
| WRONG_MISSING | · | 28 | 1 | · | · | · | 1 | · | · | · | · |
| DAMAGED | · | · | 9 | 2 | · | · | · | · | · | · | · |
| NOT_AS_DESCRIBED | · | · | · | 5 | · | · | · | · | · | · | · |
| LOW_QUALITY | · | · | · | 1 | 6 | · | · | · | · | · | · |
| SHIPPING_COST | · | · | · | · | · | 2 | · | · | · | · | · |
| DELAY | · | · | · | · | · | · | 8 | · | · | · | · |
| SERVICE | · | · | · | · | · | · | · | 4 | · | · | · |
| OTHER | · | · | · | · | · | · | 1 | · | 5 | · | · |
| UNCLEAR | · | · | · | · | · | · | · | · | · | 2 | · |
| NO_COMPLAINT | · | · | · | · | · | · | · | · | · | · | 8 |

## 후처리 규칙 효과 (LLM 원래 결과 대비)

| 규칙 | 세부 | 적용 | 정답에 가까워짐 | 변화 없음 | 틀어짐 |
|---|---|---|---|---|---|
| R1_K_DELAY | (전체) | 2 | 0 | 0 | 2 |
| R1_K_DELAY | ate agora | 1 | 0 | 0 | 1 |
| R1_K_DELAY | ate o momento | 1 | 0 | 0 | 1 |
