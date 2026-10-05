"""LLM 분류 대상 리뷰를 불러온다."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_REVIEWS = ROOT / "data" / "raw" / "olist_order_reviews_dataset.csv"
PILOT = ROOT / "data" / "labels" / "pilot_taxonomy_100.csv"
VALIDATION = ROOT / "data" / "labels" / "validation_300_blank.csv"

SCORES = [1, 2, 3]
INPUTS = ["all", "pilot", "validation"]


def load_population() -> pd.DataFrame:
    """텍스트가 있는 1~3점 리뷰를 review_id 기준 중복 제거해 불러온다."""
    df = pd.read_csv(RAW_REVIEWS, encoding="utf-8")
    has_text = df["review_comment_message"].notna() & (df["review_comment_message"].str.strip() != "")
    df = df[has_text & df["review_score"].isin(SCORES)]
    return df.drop_duplicates("review_id", keep="first").reset_index(drop=True)


def load_ids(path: Path) -> list[str]:
    """라벨 파일에서 review_id 목록을 파일 순서대로 읽는다."""
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str)["review_id"].tolist()


def load_targets(input_name: str) -> pd.DataFrame:
    """분류 대상(all: 전체 1~3점, pilot: 파일럿 100건, validation: 검증 300건)을 불러온다.

    pilot·validation은 라벨 파일의 행 순서를 따르고, 텍스트는 원본 리뷰에서 가져온다.
    """
    pop = load_population()
    if input_name == "all":
        return pop
    path = {"pilot": PILOT, "validation": VALIDATION}[input_name]
    ids = load_ids(path)
    targets = pop.set_index("review_id").reindex(ids)
    missing = targets["review_score"].isna()
    assert not missing.any(), f"모집단에 없는 review_id: {targets.index[missing].tolist()}"
    return targets.reset_index()
