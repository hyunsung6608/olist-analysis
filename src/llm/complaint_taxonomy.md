# 불만 유형 분류 체계 (v0.2)

Olist 리뷰(주로 1~3점)를 불만 유형별로 분류하기 위한 기준 문서.
LLM 분류 프롬프트와 사람 라벨링이 모두 이 문서를 기준으로 한다.

## 변경 이력

| 버전 | 날짜 | 내용 |
|---|---|---|
| v0.1 | 2026-10-03 | 9개 유형(DELAY, NOT_RECEIVED, WRONG_MISSING, DAMAGED, NOT_AS_DESCRIBED, LOW_QUALITY, SERVICE, OTHER, NO_COMPLAINT) 초안. 파일럿 100건 라벨링 |
| v0.2 | 2026-10-03 | 파일럿 검토 반영. UNCLEAR·SHIPPING_COST 신설(11개 유형). WRONG_MISSING·NOT_AS_DESCRIBED 경계 재정의(주문 선택 vs 광고 표시). 분할 배송은 WRONG_MISSING. DELAY에 '기한 내지만 오래 걸림' 포함. DAMAGED에 사용 흔적 포함·포장 미흡 제외. LOW_QUALITY에 취향·기대 미달 포함. SERVICE를 부가 라벨로 규정. 주 원인 우선순위 규칙 추가. 제목+본문·텍스트 기준 원칙 명시. 유형별 판단 예시 추가 |

## 기본 원칙

1. **제목과 본문을 함께 본다.** 리뷰 제목(review_comment_title)이 있으면 본문(review_comment_message)과 함께 읽고 판단한다. 본문에 없는 불만이 제목에만 있어도 라벨을 부여한다.
2. **점수가 아닌 텍스트 기준으로 분류한다.** 1점이라도 텍스트에 불만이 없으면 NO_COMPLAINT, 3점이라도 불만이 있으면 해당 유형을 부여한다.

## 분류 방식

- **labels (다중 라벨)**: 리뷰에서 언급된 불만 유형을 모두 부여한다. `|`로 구분한다. (예: `NOT_RECEIVED|SERVICE`)
- **primary_label (주 원인 1개)**: labels 중 아래 **주 원인 우선순위**에 따라 1개를 고른다. 반드시 labels에 포함된 값이어야 한다.
- **NO_COMPLAINT, UNCLEAR**는 다른 유형과 함께 쓰지 않는다.
- **OTHER**는 다른 유형에 해당하지 않는 불만이 있을 때만 쓴다.

## 유형 정의

| 코드 | 이름 | 정의 |
|---|---|---|
| NOT_RECEIVED | 미수령 | 리뷰 작성 시점에 주문한 상품을 **전혀** 받지 못한 상태. 배송 완료로 표시됐지만 받지 못한 경우 포함. |
| WRONG_MISSING | 오배송·누락 | 고객이 **주문 시 고른 것**(상품·옵션·색상·수량)과 다른 것이 왔거나 일부가 빠진 경우. "일부만 받고 나머지 대기 중"인 분할 배송도 포함. |
| DAMAGED | 파손·불량 | 배송 중 파손, 작동 불능, 개체 결함, 사용 흔적(중고 의심)이 있는 경우. 손상 없이 포장만 미흡한 경우는 제외. |
| NOT_AS_DESCRIBED | 설명 불일치 | 주문한 상품이 왔지만 **광고·사진에 표시된 내용**과 크기·소재·사양·구성이 다른 경우. 사진 속 구성품 누락, 상품 정보 부족·누락, 정품 아님·위조품 의심 포함. |
| LOW_QUALITY | 품질 불만 | 설명과 다르다는 언급 없이 품질·마감·내구성·성능이 기대에 못 미치는 경우. 취향 불만과 기대 미달 포함. 이유 없는 불만족은 UNCLEAR. |
| SHIPPING_COST | 배송비·수령 불편 | 배송비가 비싸거나 중복 부과된 경우, 우체국 직접 수령 등 수령 방식이 불편한 경우, 반품 배송비 부담. |
| DELAY | 배송 지연 | 예정일을 넘겨 도착했거나, 기한 내라도 배송이 오래 걸렸다는 불만. 미수령 상태에서 예정일 경과·장기 대기를 언급하면 NOT_RECEIVED와 함께 부여. |
| SERVICE | 응대·환불 | 판매자·플랫폼의 무응답, 안내 부재, 환불·교환·취소 처리 지연·거부. **부가 라벨 성격**으로, 다른 불만이 없을 때만 주 원인이 된다. 집계는 다중 라벨 기준으로 한다. |
| OTHER | 기타 | 위 유형에 해당하지 않는 구체적 불만(예: 상품 옵션 구색, 포장 미흡). |
| UNCLEAR | 판단 불가 | 의미 없는 텍스트(숫자, 상품명만 기재, "할 말 없음"), 이유 없는 불만족("마음에 안 듦", "반품 원함"만 있는 경우). |
| NO_COMPLAINT | 불만 없음 | 텍스트에 불만이 드러나지 않음(칭찬, 중립). |

## 주 원인 우선순위

labels에 여러 유형이 있으면 아래 순서에서 가장 앞선 유형을 primary_label로 고른다.

```
NOT_RECEIVED > WRONG_MISSING > DAMAGED > NOT_AS_DESCRIBED > LOW_QUALITY > SHIPPING_COST > DELAY > SERVICE
```

- OTHER, UNCLEAR, NO_COMPLAINT는 위 8개 유형이 하나도 없을 때만 주 원인이 된다.
- SERVICE는 다른 불만이 없을 때만 주 원인이 된다.

## 판단 규칙

1. **NOT_RECEIVED vs DELAY**: 리뷰 시점에 못 받았으면 NOT_RECEIVED. 예정일 경과·장기 대기를 언급하면 DELAY를 함께 부여한다. 늦게라도 받았으면 DELAY만 부여한다.
2. **NOT_RECEIVED vs WRONG_MISSING**: 주문 전체를 못 받았으면 NOT_RECEIVED, 일부만 받았으면(분할 배송 포함) WRONG_MISSING.
3. **WRONG_MISSING vs NOT_AS_DESCRIBED**: 고객이 주문 시 **고른 것**과 다르면 WRONG_MISSING, 광고·사진에 **표시된 것**과 다르면 NOT_AS_DESCRIBED.
4. **NOT_AS_DESCRIBED vs LOW_QUALITY**: 광고·사진·설명과의 차이를 언급하면 NOT_AS_DESCRIBED, 언급 없이 품질·기대 미달만 말하면 LOW_QUALITY.
5. **DAMAGED vs LOW_QUALITY**: 특정 개체의 파손·결함·작동 불능이면 DAMAGED, 상품 전반의 품질·내구성 수준이 낮으면 LOW_QUALITY.
6. **SERVICE**: 환불·교환을 **요구**하는 것만으로는 부여하지 않는다. 응대·처리의 **실패**를 언급할 때 부여한다.
7. **SHIPPING_COST vs NOT_RECEIVED**: 우체국 등에서 직접 찾아왔다면 결국 받은 것이므로 NOT_RECEIVED가 아니라 SHIPPING_COST.

## 유형별 판단 예시 (파일럿에서 애매했던 사례)

### NOT_RECEIVED
- "배송을 너무 질질 끈다, 아직 못 받았다" (제목: 배송 지연) → `NOT_RECEIVED|DELAY`. 고객이 '지연'이라 표현해도 상태는 미수령.
- "배송 지연으로 평가할 수 없다" (제목: 상품이 오지 않음) → `NOT_RECEIVED|DELAY`. 제목으로 미수령 확인.
- "추적상 11일 배송 완료인데 받지 못했다" → `NOT_RECEIVED`.
- "상품을 받으려면 어떻게 해야 하나, 여전히 원한다" → `NOT_RECEIVED`. 직접 언급은 없지만 문맥상 미수령.

### WRONG_MISSING
- "TV 거치대 2개 주문, 1개만 옴, 두 번째 기다리는 중" → `WRONG_MISSING`. 분할 배송 포함.
- "두 상품 모두 9/5 도착 예정이었는데 하나만 옴" → `WRONG_MISSING|DELAY`, 주 원인 WRONG_MISSING.
- "버클까지 올블랙을 샀는데 은색 버클로 옴, 각인 없음" → `WRONG_MISSING|NOT_AS_DESCRIBED`, 주 원인 WRONG_MISSING. 고객이 고른 사양과 다름.
- 제목 "잘못된 상품" + 본문 "메일에 답이 없다" → `WRONG_MISSING|SERVICE`. 제목에서 오배송 확인.

### DAMAGED
- "이미 사용한 것 같다, 더럽고 긁혀 있다" → `DAMAGED`. 사용 흔적 포함.
- "핀으로 찌른 듯한 작은 구멍" → `DAMAGED`. 경미해도 개체 결함.
- "늦게 왔고 파손돼 있었다" → `DAMAGED|DELAY`, 주 원인 DAMAGED(우선순위).
- "새 상품이고 괜찮은데 상자가 밀봉되지 않았다" → DAMAGED 아님. `OTHER`(포장 미흡).

### NOT_AS_DESCRIBED
- "광고와 다르게 왔다" → `NOT_AS_DESCRIBED`. 광고를 기준으로 언급.
- "사진엔 보온병 커버가 있었는데 동봉되지 않았다" → `NOT_AS_DESCRIBED`. 사진 속 구성품 누락.
- "정품 인형인 줄 알았는데 중국산, 설명에 제조지가 없다" → `NOT_AS_DESCRIBED`. 정보 부족·정품 여부.
- "엡손 정품이라 했는데 위조품" → `NOT_AS_DESCRIBED`.
- "배터리 미포함, 영어 매뉴얼, 어떤 배터리를 써야 할지 모름" → `NOT_AS_DESCRIBED`. 상품 정보 부족.

### LOW_QUALITY
- "상품은 맞게 왔는데 너무 작아서 싫다" (설명 언급 없음) → `LOW_QUALITY`. 기대 미달.
- "향이 너무 달다" → `LOW_QUALITY`. 취향 불만.
- "자석이 약해 일주일 만에 안 닫힘, 실이 풀림" → `LOW_QUALITY`. 상품 전반의 내구성.
- "광고를 잘 안 봤는데 소재가 마음에 안 든다" → `LOW_QUALITY`. 고객이 광고 미확인을 인정.

### SHIPPING_COST
- "배송비를 냈는데 우체국에 직접 찾으러 가야 했다" → `SHIPPING_COST`.
- "같은 판매처 2개 상품에 배송비를 두 번 받았다" → `SHIPPING_COST`.
- "배송비가 너무 비싸다, 무료배송 해달라" → `SHIPPING_COST`.

### DELAY
- "기한 내에 왔지만 너무 오래 걸렸다" → `DELAY`.
- "조금 늦었지만 괜찮았다" → `DELAY`.

### SERVICE
- "환불을 원한다"만 있는 경우 → SERVICE 아님.
- "영수증을 버려서 교환을 못 했다" → SERVICE 아님(고객 사정).

### OTHER
- "원하던 향 옵션이 없었다" → `OTHER`(상품 구색).

### UNCLEAR
- "3", "아무 말도 하고 싶지 않다", 상품명만 기재 → `UNCLEAR`.
- "마음에 안 들어요, 반품하고 싶어요" → `UNCLEAR`. 이유 없는 불만족.

### NO_COMPLAINT
- 2점인데 "아주 좋아요" → `NO_COMPLAINT`. 텍스트 기준.
