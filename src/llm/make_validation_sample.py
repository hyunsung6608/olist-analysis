"""검증용 블라인드 라벨링 샘플(300건)을 만든다.

텍스트가 있는 1~3점 리뷰에서 파일럿 100건을 제외하고,
점수별 실제 비율대로 층화 추출한 뒤 행 순서를 섞어 저장한다.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_REVIEWS = ROOT / "data" / "raw" / "olist_order_reviews_dataset.csv"
PILOT = ROOT / "data" / "labels" / "pilot_taxonomy_100.csv"
OUT_BLANK = ROOT / "data" / "labels" / "validation_300_blank.csv"
OUT_META = ROOT / "data" / "labels" / "validation_300_meta.csv"

N_SAMPLE = 300
SCORES = [1, 2, 3]
RANDOM_STATE = 42
LABEL_COLS = [
    "DELAY", "NOT_RECEIVED", "WRONG_MISSING", "DAMAGED", "NOT_AS_DESCRIBED", "LOW_QUALITY",
    "SERVICE", "SHIPPING_COST", "OTHER", "UNCLEAR", "NO_COMPLAINT",
]


def load_population() -> pd.DataFrame:
    """텍스트가 있는 1~3점 리뷰를 review_id 기준 중복 제거해 불러온다."""
    df = pd.read_csv(RAW_REVIEWS, encoding="utf-8")
    has_text = df["review_comment_message"].notna() & (df["review_comment_message"].str.strip() != "")
    df = df[has_text & df["review_score"].isin(SCORES)]
    return df.drop_duplicates("review_id", keep="first").reset_index(drop=True)


def allocate(counts: pd.Series, n: int) -> pd.Series:
    """점수별 비율대로 n건을 배분한다(최대잉여법으로 합계를 n에 맞춤)."""
    raw = counts / counts.sum() * n
    alloc = raw.astype(int)
    remainder = (raw - alloc).sort_values(ascending=False)
    alloc[remainder.index[: n - alloc.sum()]] += 1
    return alloc


def stratified_sample(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """점수별 층화 추출 후 행 순서를 섞는다."""
    alloc = allocate(df["review_score"].value_counts().sort_index(), n)
    parts = [df[df["review_score"] == s].sample(k, random_state=RANDOM_STATE) for s, k in alloc.items()]
    sample = pd.concat(parts).sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)
    sample.insert(0, "no", range(1, len(sample) + 1))
    return sample


def report(pop: pd.DataFrame, sample: pd.DataFrame, pilot_ids: set) -> None:
    """점수별 비율, 파일럿 중복, review_id 고유성을 확인해 출력한다."""
    summary = pd.DataFrame({
        "모집단_건수": pop["review_score"].value_counts(),
        "모집단_비율": pop["review_score"].value_counts(normalize=True).round(4),
        "추출_건수": sample["review_score"].value_counts(),
        "추출_비율": sample["review_score"].value_counts(normalize=True).round(4),
    }).sort_index()
    print(summary.to_string())
    overlap = sample["review_id"].isin(pilot_ids).sum()
    unique = sample["review_id"].nunique()
    print(f"\n파일럿과 겹치는 review_id: {overlap}건")
    print(f"고유 review_id: {unique}/{len(sample)}")
    print(f"첫 10행 점수 순서: {sample['review_score'].head(10).tolist()}")
    assert overlap == 0 and unique == len(sample) == N_SAMPLE


def main() -> None:
    """샘플을 추출하고 라벨링 파일과 메타 파일을 저장한다."""
    pilot_ids = set(pd.read_csv(PILOT, encoding="utf-8-sig")["review_id"])
    pop = load_population()
    pop = pop[~pop["review_id"].isin(pilot_ids)].reset_index(drop=True)
    sample = stratified_sample(pop, N_SAMPLE)

    blank = sample[["no", "review_id", "review_comment_title", "review_comment_message"]].copy()
    for col in LABEL_COLS + ["primary_label", "note"]:
        blank[col] = ""
    blank.to_csv(OUT_BLANK, index=False, encoding="utf-8-sig")

    meta = sample[["no", "review_id", "order_id", "review_score", "review_creation_date"]]
    meta.to_csv(OUT_META, index=False, encoding="utf-8-sig")

    print(f"모집단(파일럿 제외): {len(pop)}건\n")
    report(pop, sample, pilot_ids)
    print(f"\n저장: {OUT_BLANK.relative_to(ROOT)} {blank.shape}")
    print(f"저장: {OUT_META.relative_to(ROOT)} {meta.shape}")


if __name__ == "__main__":
    main()
