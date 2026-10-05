"""전체 분류 결과(JSONL)를 MySQL 적재용 최종 CSV로 내보낸다(API 호출 없음).

유형 11개를 0/1 컬럼으로 펼치고, 후처리 전 라벨·적용 규칙·규칙 위반 플래그·버전 정보를 함께 담는다.
근거 구절(evidence)과 reason은 파일 크기 때문에 넣지 않는다(원본 JSONL에 남아 있음).

예) python src/llm/export_labels.py
    python src/llm/export_labels.py --run-name full_v2_post3 --out data/results/review_complaint_labels.csv
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from data import load_targets
from taxonomy import LABEL_CODES, SOLO

ROOT = Path(__file__).resolve().parents[2]
RESULT_DIR = ROOT / "data" / "processed" / "llm_labels"
DEFAULT_OUT = ROOT / "data" / "results" / "review_complaint_labels.csv"


def parse_args() -> argparse.Namespace:
    """실행 옵션을 읽는다."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-name", default="full_v2_post3", help="내보낼 결과 파일 이름")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="출력 CSV 경로")
    return parser.parse_args()


def to_row(rec: dict) -> dict:
    """결과 레코드 1건을 CSV 1행(dict)으로 바꾼다."""
    labels = set(rec["labels"])
    row = {"review_id": rec["review_id"]}
    row.update({c: int(c in labels) for c in LABEL_CODES})
    row.update({
        "primary_label": rec["primary_label"],
        "raw_labels": "|".join(rec["raw_labels"]),
        "postprocess_rules": "|".join(rec["postprocess_rules"]),
        # 규칙 C: 일부만 받은 경우(WRONG_MISSING)에 NOT_RECEIVED가 함께 붙음
        "flag_rule_c_violation": int({"NOT_RECEIVED", "WRONG_MISSING"} <= labels),
        # 단독 유형(NO_COMPLAINT·UNCLEAR)이 다른 유형과 함께 붙음
        "flag_exclusive_violation": int(bool(labels & set(SOLO)) and len(labels) > 1),
        "model": rec["model"],
        "taxonomy_version": rec["taxonomy_version"],
        "prompt_hash": rec["prompt_hash"],
    })
    return row


def main() -> None:
    """JSONL을 읽어 검증한 뒤 CSV로 저장하고 행 수·파일 크기·플래그 건수를 출력한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    src = RESULT_DIR / f"{args.run_name}.jsonl"
    with src.open(encoding="utf-8") as f:
        recs = [json.loads(line) for line in f if line.strip()]

    df = pd.DataFrame([to_row(r) for r in recs])
    target_ids = set(load_targets("all")["review_id"])
    assert df["review_id"].is_unique, "review_id 중복"
    assert set(df["review_id"]) == target_ids, (
        f"대상과 불일치: 누락 {len(target_ids - set(df['review_id']))}, 초과 {len(set(df['review_id']) - target_ids)}"
    )
    assert (df[LABEL_CODES].sum(axis=1) > 0).all(), "라벨이 없는 행이 있음"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, encoding="utf-8", lineterminator="\n")

    size_mb = args.out.stat().st_size / 1024 / 1024
    print(f"저장: {args.out.relative_to(ROOT)}")
    print(f"  행 수: {len(df):,} / 컬럼 수: {df.shape[1]} / 파일 크기: {size_mb:.2f} MB")
    print(f"  flag_rule_c_violation: {df['flag_rule_c_violation'].sum():,}건")
    print(f"  flag_exclusive_violation: {df['flag_exclusive_violation'].sum():,}건")
    print(f"  후처리 규칙이 적용된 행: {(df['postprocess_rules'] != '').sum():,}건")
    print(f"  model: {df['model'].unique().tolist()} / taxonomy_version: {df['taxonomy_version'].unique().tolist()}"
          f" / prompt_hash: {df['prompt_hash'].unique().tolist()}")


if __name__ == "__main__":
    main()
