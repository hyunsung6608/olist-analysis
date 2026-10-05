# 재현성 비교: validation_run1 vs validation_run2

- 비교 건수: 100건 (한쪽에만 있는 review_id: 0건)
- prompt_hash: b0abafe22cb0

## 전체 일치도

| 지표 | 후처리 후(labels) | 후처리 전(raw_labels) |
|---|---|---|
| 라벨 조합 완전 일치율 | 0.930 | 0.920 |
| 주 원인 일치율 | 0.970 | 0.970 |
| 주 원인 Cohen's kappa | 0.965 | 0.965 |

## 유형별로 두 실행의 판단이 갈린 건수

| 유형 | 후처리 후 | 후처리 전 |
|---|---|---|
| NOT_RECEIVED | 1 | 1 |
| WRONG_MISSING | 0 | 0 |
| DAMAGED | 1 | 1 |
| NOT_AS_DESCRIBED | 0 | 0 |
| LOW_QUALITY | 1 | 1 |
| SHIPPING_COST | 0 | 0 |
| DELAY | 2 | 3 |
| SERVICE | 1 | 1 |
| OTHER | 1 | 1 |
| UNCLEAR | 1 | 1 |
| NO_COMPLAINT | 0 | 0 |
| 합계 | 8 | 9 |

## 라벨 조합이 다른 리뷰 (7건, 후처리 후 기준)

| review_id | validation_run1 | validation_run2 |
|---|---|---|
| 345cfd693c6c31cbe73bfa7f8593fd2a | DELAY | NOT_RECEIVED + DELAY |
| 2ca08c633d4c824cf268e25c3ed435bc | NOT_AS_DESCRIBED | DAMAGED + NOT_AS_DESCRIBED |
| 6c39750dd584f8f824e38486e2fc7e69 | SHIPPING_COST | SHIPPING_COST + OTHER |
| f4d8572b570b51c323f9a20383febdee | WRONG_MISSING | WRONG_MISSING + DELAY |
| 5b3f161df58789b8554493f2d884ce68 | WRONG_MISSING | WRONG_MISSING + DELAY |
| 95cf551d535a024e57bb1646d017c86e | UNCLEAR | LOW_QUALITY |
| 58f2a64617ca91372c2dd0fa2b6e1a58 | WRONG_MISSING + SERVICE | WRONG_MISSING |
