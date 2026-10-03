"""구글 시트에서 내려받은 검증 라벨링 결과를 분석용 CSV로 정리한다.

no 1~100번 행만 사용하고, 유형 컬럼의 TRUE/FALSE를 1/0으로 바꾼 뒤
complaint_taxonomy.md의 우선순위 규칙으로 primary_label을 계산한다.
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "labels" / "validation_labeled_raw.csv"
BLANK = ROOT / "data" / "labels" / "validation_300_blank.csv"
TAXONOMY = ROOT / "src" / "llm" / "complaint_taxonomy.md"
OUT = ROOT / "data" / "labels" / "validation_100_labeled.csv"

N_LABELED = 100
LABEL_COLS = [
    "DELAY", "NOT_RECEIVED", "WRONG_MISSING", "DAMAGED", "NOT_AS_DESCRIBED", "LOW_QUALITY",
    "SERVICE", "SHIPPING_COST", "OTHER", "UNCLEAR", "NO_COMPLAINT",
]
# 우선순위 체인에 없는 유형: 다른 유형이 없을 때만 주 원인 (이 순서로 선택)
FALLBACK = ["OTHER", "UNCLEAR", "NO_COMPLAINT"]
SOLO = ["NO_COMPLAINT", "UNCLEAR"]


def load_priority() -> list[str]:
    """분류 체계 문서의 '주 원인 우선순위' 코드 블록에서 우선순위를 읽는다."""
    text = TAXONOMY.read_text(encoding="utf-8")
    section = text.split("## 주 원인 우선순위", 1)[1]
    chain = re.search(r"```\s*\n(.+?)\n```", section, re.S).group(1)
    order = [c.strip() for c in chain.split(">")] + FALLBACK
    assert sorted(order) == sorted(LABEL_COLS), f"우선순위와 유형 컬럼이 다름: {order}"
    return order


def to_binary(df: pd.DataFrame) -> pd.DataFrame:
    """유형 컬럼의 TRUE/FALSE를 1/0으로 바꾼다."""
    for col in LABEL_COLS:
        values = df[col].str.strip().str.upper()
        bad = ~values.isin(["TRUE", "FALSE"])
        assert not bad.any(), f"{col}에 TRUE/FALSE가 아닌 값: no {df.loc[bad, 'no'].tolist()}"
        df[col] = (values == "TRUE").astype(int)
    return df


def primary_of(row: pd.Series, order: list[str]) -> str:
    """체크된 유형 중 우선순위가 가장 높은 것을 주 원인으로 고른다."""
    return next((c for c in order if row[c] == 1), "")


def main() -> None:
    """라벨을 정리·저장하고 검증 결과와 유형별 건수를 출력한다."""
    order = load_priority()
    raw = pd.read_csv(RAW, encoding="utf-8", dtype=str, keep_default_na=False)
    blank = pd.read_csv(BLANK, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    assert (raw["no"] == blank["no"]).all() and (raw["review_id"] == blank["review_id"]).all(), "원본 샘플과 행이 다름"

    df = raw[raw["no"].astype(int) <= N_LABELED].copy()
    df = to_binary(df)
    assert len(df) == N_LABELED

    rest = to_binary(raw[raw["no"].astype(int) > N_LABELED].copy())
    if rest[LABEL_COLS].to_numpy().sum():
        print(f"[주의] 101번 이후에 체크된 행이 있음(제외됨): {rest.loc[rest[LABEL_COLS].sum(axis=1) > 0, 'no'].tolist()}")

    df["primary_label"] = df.apply(primary_of, axis=1, order=order)
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"저장: {OUT.relative_to(ROOT)} {df.shape}")
    print(f"우선순위: {' > '.join(order)}\n")

    n_labels = df[LABEL_COLS].sum(axis=1)
    empty = df.loc[n_labels == 0, "no"].tolist()
    solo_conflict = df.loc[(df[SOLO].sum(axis=1) > 0) & (n_labels > 1), "no"].tolist()
    print(f"[검증] 라벨이 하나도 없는 행: {len(empty)}건 {empty}")
    print(f"[검증] NO_COMPLAINT/UNCLEAR가 다른 유형과 함께 체크된 행: {len(solo_conflict)}건 {solo_conflict}")
    for no in solo_conflict:
        row = df[df["no"] == no].iloc[0]
        print(f"  no {no}: {[c for c in LABEL_COLS if row[c]]} → primary {row['primary_label']}")

    counts = pd.DataFrame({
        "다중 라벨": df[LABEL_COLS].sum(),
        "주 원인": df["primary_label"].value_counts(),
    }).reindex(order).fillna(0).astype(int)
    counts.loc["합계"] = counts.sum()
    print(f"\n{counts.to_string()}")
    print(f"\n라벨 2개 이상인 행: {(n_labels > 1).sum()}건")


if __name__ == "__main__":
    main()
