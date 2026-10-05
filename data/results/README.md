# data/results

분석과 MySQL 적재에 쓰는 최종 결과 파일.

## review_complaint_labels.csv

텍스트가 있는 1~3점 리뷰 14,286건(review_id 기준 중복 제거)의 불만 유형 분류 결과. 리뷰 1건당 1행.

- 형식: UTF-8(BOM 없음), 쉼표 구분, 줄바꿈 LF, 헤더 1행
- 크기: 약 1.7 MB, 20개 컬럼

### 컬럼

| 컬럼 | 형식 | 설명 |
|---|---|---|
| review_id | 문자 32자 | Olist 리뷰 ID (원본 olist_order_reviews_dataset.csv와 결합 키) |
| DELAY ~ NO_COMPLAINT | 0/1 | 불만 유형 11개(DELAY, NOT_RECEIVED, WRONG_MISSING, DAMAGED, NOT_AS_DESCRIBED, LOW_QUALITY, SERVICE, SHIPPING_COST, OTHER, UNCLEAR, NO_COMPLAINT). 후처리 후 라벨 기준. 한 리뷰에 여러 개가 1일 수 있음 |
| primary_label | 문자 | 주 원인 1개. 1인 유형 중 분류 체계의 우선순위가 가장 높은 것 |
| raw_labels | 문자 | 후처리 전 LLM 원래 라벨, `\|`로 구분 |
| postprocess_rules | 문자 | 적용된 후처리 규칙, `\|`로 구분 (없으면 빈칸). `R1_K_DELAY:<발동 표현>`, `R2_EVIDENCE:<-제거/+추가 유형>` |
| flag_rule_c_violation | 0/1 | 일부만 받은 경우(WRONG_MISSING)인데 NOT_RECEIVED도 붙은 행 (규칙 C 위반 의심) |
| flag_exclusive_violation | 0/1 | NO_COMPLAINT·UNCLEAR가 다른 유형과 함께 붙은 행 (단독 규칙 위반) |
| model / taxonomy_version / prompt_hash | 문자 | 생성 모델, 분류 체계 버전, 프롬프트 해시 |

유형 정의와 우선순위는 `src/llm/complaint_taxonomy.md` 참고. 근거 구절(evidence)과 판단 이유(reason)는 원본 JSONL(`data/processed/llm_labels/full_v2_post3.jsonl`, 커밋 대상 아님)에만 있다.

### 생성 방법

1. `src/llm/classify_reviews.py --input all --run-name full_v2_post3` — Gemini(`gemini-3.5-flash-lite`)로 30건씩 배치 분류, 분류 체계 v0.5, 프롬프트 v2(prompt_hash `b0abafe22cb0`), 후처리 post3 적용
2. `src/llm/export_labels.py` — JSONL을 이 CSV로 변환 (API 호출 없음)

### 검증 성능

사람이 직접 라벨링한 검증 샘플 100건(`data/labels/validation_100_labeled.csv`) 기준 (`reports/llm_eval/validation_run1.md`).

| 지표 | 값 |
|---|---|
| 라벨 조합 완전 일치율 (공식) | 0.78 |
| micro F1 / macro F1 | 0.89 / 0.90 |
| 주 원인 정확도 / Cohen's kappa | 0.88 / 0.86 |
| 같은 입력 2회 실행 간 라벨 조합 일치율 | 0.93 |

규칙과 어긋난 정답 3건을 바로잡은 보정 점수는 완전 일치율 0.81이다(`reports/llm_eval/validation_adjudication.md`). 다만 LLM과 불일치한 건만 재검토했으므로 낙관적인 값이다.

### 알려진 한계

- **NOT_RECEIVED 과소 추정 가능성**: 검증 재현율 0.67. 특히 결제 후 품절로 못 받은 경우를 SERVICE로만 분류하는 경향이 있다(분류 체계에 기준 없음).
- **부가 라벨 누락**: 주된 불만만 잡고 부가 불만(LOW_QUALITY, OTHER 등)을 빠뜨리는 경향이 있다. OTHER 재현율 0.63.
- **SERVICE 과다 부여**: 교환·환불을 요청만 한 경우에도 SERVICE를 붙이는 경우가 있다.
- **후처리 규칙 1 오발동**: "até agora / até o momento"가 배송이 아니라 판매자 응답을 가리킬 때도 DELAY를 붙인다(전체 0.15% 이하로 추정). 검증에서는 2번 발동해 2번 모두 오답이었다.
- **규칙 위반 68건 미수정**: flag 컬럼으로 표시만 했다. 규칙 C 위반 67건에는 "다른 상품이 대신 오고 주문한 상품은 못 받음"처럼 분류 체계에 기준이 없는 경우가 섞여 있다.
- **집계 시 주의**: 유형별 비율은 다중 라벨(유형 컬럼 합계)과 주 원인(primary_label) 중 어느 기준인지 밝힌다. DELAY·SERVICE는 부가 라벨 성격이라 두 기준의 차이가 크다(DELAY 21.7% vs 8.6%).
