# 검증 평가 보정 점수: validation_run1

- 대상: 검증 100건 (validation_100_labeled.csv, no 1~100)
- 파이프라인: 프롬프트 v2 (prompt_hash b0abafe22cb0) + 후처리 post3, 모델 gemini-3.5-flash-lite, 분류 체계 v0.5
- 보정 정답: data/labels/validation_100_adjudicated.csv (src/llm/make_adjudicated_labels.py로 생성, 원본 정답 파일은 수정하지 않음)

> **주의: 보정 점수는 낙관적일 수 있다.**
> 정답 재검토는 LLM 결과와 불일치한 22건만 대상으로 했다. LLM과 일치한 78건 중에도 정답과 LLM이 같은 방향으로 틀린 건이 있을 수 있지만 재검토하지 않았다.
> 따라서 수정은 LLM에 유리한 방향으로만 일어날 수 있고, 보정 점수는 실제 성능의 상한에 가깝다.
> 외부에 보고할 때는 공식 점수를 기준으로 하고, 보정 점수는 참고로 함께 적는다.

## 공식 점수 vs 보정 점수

| 지표 | 공식 (원본 정답) | 보정 (adjudicated) | 차이 |
|---|---|---|---|
| 완전 일치율 | 0.780 | 0.810 | +0.030 |
| micro F1 | 0.888 | 0.900 | +0.012 |
| macro F1 | 0.895 | 0.903 | +0.008 |
| 주 원인 정확도 | 0.880 | 0.890 | +0.010 |
| 주 원인 Cohen's kappa | 0.860 | 0.871 | +0.011 |
| DELAY F1 | 0.833 | 0.895 | +0.062 |
| NOT_RECEIVED F1 | 0.800 | 0.828 | +0.028 |
| 불일치 건수 | 22 | 19 | -3 |

참고로 보정 정답 기준 후처리 전(raw_labels) 완전 일치율은 0.830이다. 후처리 규칙 1이 이 검증에서 2번 발동해 2번 모두 정답에서 멀어졌다("até agora / até o momento"가 배송이 아닌 판매자 응답을 가리킨 no45, no82).

## 수정한 정답 3건

| no | 원본 정답 | 보정 정답 | 근거 규칙 | 리뷰 원문 |
|---|---|---|---|---|
| 39 | NOT_RECEIVED, WRONG_MISSING | WRONG_MISSING | 규칙 C: 주문 일부만 못 받으면 WRONG_MISSING, NOT_RECEIVED는 전체를 못 받았을 때만 | "Paguei por duas mantas e só recebi uma" |
| 40 | NOT_RECEIVED | NOT_RECEIVED, DELAY | 규칙 K: 미수령 리뷰에서 경과 기간을 표현하면 DELAY 동시 부여 | "Já faz mais de 30 dias que o produto foi comprado e ainda não o recebi." |
| 58 | NOT_RECEIVED, SERVICE | NOT_RECEIVED, DELAY, SERVICE | 규칙 K: 미수령 리뷰에서 '현재까지(até o momento)'처럼 계속 못 받는 상태를 표현하면 DELAY 동시 부여 | "Até o momento o produto não chegou na minha residência e a loja não entra em contato" |

세 건 모두 LLM(run1) 판단이 보정 정답과 일치한다. 주 원인(primary_label)은 우선순위로 다시 계산했으며, no39만 NOT_RECEIVED에서 WRONG_MISSING으로 바뀌었다.

## 수정하지 않은 애매한 건

규칙만으로 정답을 확정할 수 없어 원본 정답을 유지했다. 분류 체계 보완 후 다시 판단한다.

| no | 원본 정답 | LLM | 보류 이유 |
|---|---|---|---|
| 25, 84, 87 | NOT_RECEIVED, SERVICE | SERVICE | 결제 후 품절로 못 받은 경우를 NOT_RECEIVED로 볼지 분류 체계에 기준이 없음 (규칙 P는 DELAY·SERVICE만 다룸) |
| 88 | NOT_RECEIVED, DELAY, SERVICE | OTHER | "DIFICULDADE NA ENTREGA"만 있어 규칙 R(불명확한 배송 문제 → OTHER)과 충돌 |
| 44 | DAMAGED, NOT_AS_DESCRIBED | NOT_AS_DESCRIBED | 호환 불가는 규칙 N(NOT_AS_DESCRIBED)이고 DAMAGED의 텍스트 근거가 약함 |
