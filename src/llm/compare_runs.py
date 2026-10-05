"""같은 대상을 두 번 분류한 결과(JSONL)를 비교해 재현성을 리포트로 저장한다(API 호출 없음).

예) python src/llm/compare_runs.py --run-a validation_run1 --run-b validation_run2 --out-name validation_consistency
"""
import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from evaluate import load_results
from taxonomy import load_priority, primary_label

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "reports" / "llm_eval"


def parse_args() -> argparse.Namespace:
    """실행 옵션을 읽는다."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-a", required=True, help="첫 번째 결과 파일 이름")
    parser.add_argument("--run-b", required=True, help="두 번째 결과 파일 이름")
    parser.add_argument("--out-name", required=True, help="리포트 이름 (reports/llm_eval/{out_name}.md)")
    return parser.parse_args()


def agreement(df: pd.DataFrame, col: str, order: list[str]) -> dict:
    """두 실행의 라벨 조합 일치율, 유형별 불일치 건수, 주 원인 kappa를 계산한다."""
    a, b = df[f"{col}_a"].apply(set), df[f"{col}_b"].apply(set)
    per_label = {c: int(sum((c in x) != (c in y) for x, y in zip(a, b))) for c in order}
    pa = df[f"{col}_a"].apply(primary_label, order=order)
    pb = df[f"{col}_b"].apply(primary_label, order=order)
    return {
        "exact": float((a == b).mean()),
        "per_label": per_label,
        "primary_agree": float((pa == pb).mean()),
        "primary_kappa": cohen_kappa_score(pa, pb),
    }


def main() -> None:
    """두 결과를 review_id로 결합해 재현성 지표를 계산하고 리포트를 저장한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    order = load_priority()
    ra, rb = load_results(args.run_a), load_results(args.run_b)
    df = ra.merge(rb, on="review_id", suffixes=("_a", "_b"))
    only = len(set(ra["review_id"]) ^ set(rb["review_id"]))

    post = agreement(df, "labels", order)
    raw = agreement(df, "raw_labels", order) if "raw_labels_a" in df else None

    lines = [
        f"# 재현성 비교: {args.run_a} vs {args.run_b}",
        "",
        f"- 비교 건수: {len(df)}건 (한쪽에만 있는 review_id: {only}건)",
        f"- prompt_hash: {', '.join(sorted(set(df['prompt_hash_a']) | set(df['prompt_hash_b'])))}",
        "",
        "## 전체 일치도",
        "",
        "| 지표 | 후처리 후(labels) | 후처리 전(raw_labels) |",
        "|---|---|---|",
    ]
    rows = [("라벨 조합 완전 일치율", "exact"), ("주 원인 일치율", "primary_agree"), ("주 원인 Cohen's kappa", "primary_kappa")]
    for name, key in rows:
        lines.append(f"| {name} | {post[key]:.3f} | {raw[key]:.3f} |" if raw else f"| {name} | {post[key]:.3f} | - |")
    lines += [
        "",
        "## 유형별로 두 실행의 판단이 갈린 건수",
        "",
        "| 유형 | 후처리 후 | 후처리 전 |",
        "|---|---|---|",
    ]
    for c in order:
        lines.append(f"| {c} | {post['per_label'][c]} | {raw['per_label'][c] if raw else '-'} |")
    lines.append(f"| 합계 | {sum(post['per_label'].values())} | {sum(raw['per_label'].values()) if raw else '-'} |")

    diff = df[df["labels_a"].apply(set) != df["labels_b"].apply(set)]
    lines += [
        "",
        f"## 라벨 조합이 다른 리뷰 ({len(diff)}건, 후처리 후 기준)",
        "",
        f"| review_id | {args.run_a} | {args.run_b} |",
        "|---|---|---|",
    ]
    for _, r in diff.iterrows():
        lines.append(f"| {r['review_id']} | {' + '.join(r['labels_a'])} | {' + '.join(r['labels_b'])} |")
    report = "\n".join(lines) + "\n"

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"{args.out_name}.md"
    path.write_text(report, encoding="utf-8")
    print(report)
    print(f"저장: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
