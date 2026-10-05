"""기존 분류 결과 JSONL에 후처리만 적용해 새 이름으로 저장한다(API 호출 없음).

후처리는 항상 LLM 원래 결과(raw_labels, 없으면 labels)에서 다시 시작하므로 여러 번 적용해도 결과가 같다.

예) python src/llm/apply_postprocess.py --run-name pilot_v2 --out-name pilot_v2_post
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from data import load_population
from postprocess import find_violations, postprocess
from taxonomy import load_priority, primary_label

ROOT = Path(__file__).resolve().parents[2]
RESULT_DIR = ROOT / "data" / "processed" / "llm_labels"


def parse_args() -> argparse.Namespace:
    """실행 옵션을 읽는다."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-name", required=True, help="원본 결과 파일 이름")
    parser.add_argument("--out-name", required=True, help="저장할 결과 파일 이름")
    args = parser.parse_args()
    if args.run_name == args.out_name:
        parser.error("--out-name은 --run-name과 달라야 합니다.")
    return args


def main() -> None:
    """결과를 읽어 후처리를 적용하고 저장한 뒤 규칙별 적용 건수와 남은 위반을 출력한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    order = load_priority()
    src = RESULT_DIR / f"{args.run_name}.jsonl"
    dst = RESULT_DIR / f"{args.out_name}.jsonl"

    with src.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    texts = load_population().set_index("review_id")[["review_comment_title", "review_comment_message"]]
    texts = texts.fillna("")

    rule_counts, detail_counts, violations = Counter(), Counter(), Counter()
    n_changed = 0
    out = []
    for rec in records:
        title, message = texts.loc[rec["review_id"]]
        raw_labels = rec.get("raw_labels") or rec["labels"]
        labels, rules = postprocess({**rec, "raw_labels": raw_labels}, title, message)
        rule_counts.update(rule.split(":")[0] for rule in rules)
        detail_counts.update(rules)
        violations.update(find_violations(labels))
        n_changed += labels != raw_labels
        new = {k: v for k, v in rec.items() if k not in {"raw_labels", "labels", "postprocess_rules", "primary_label"}}
        out.append({
            "review_id": rec["review_id"],
            **({"evidence": rec["evidence"]} if "evidence" in rec else {}),
            "raw_labels": raw_labels,
            "labels": labels,
            "postprocess_rules": rules,
            "primary_label": primary_label(labels, order),
            **{k: v for k, v in new.items() if k not in {"review_id", "evidence"}},
            "run_name": args.out_name,
            "postprocessed_from": args.run_name,
        })

    with dst.open("w", encoding="utf-8", newline="\n") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"저장: {dst.relative_to(ROOT)} ({len(out)}건, labels가 바뀐 건 {n_changed}건)")
    print("규칙별 적용 건수:")
    for rule, n in sorted(rule_counts.items()):
        print(f"  {rule}: {n}건")
        for detail, m in sorted(detail_counts.items()):
            if detail.startswith(rule + ":"):
                print(f"    - {detail.split(':', 1)[1]}: {m}건")
    print("후처리 후 남은 규칙 위반(자동 수정 안 함):")
    for name, n in violations.items():
        print(f"  {name}: {n}건")
    if not violations:
        print("  없음")


if __name__ == "__main__":
    main()
