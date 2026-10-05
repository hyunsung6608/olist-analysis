"""LLM 분류 결과(JSONL)를 정답 라벨(파일럿·검증)과 비교해 지표와 불일치 목록을 저장한다.

예) python src/llm/evaluate.py --run-name pilot_v1 --labels pilot
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, cohen_kappa_score, confusion_matrix
from sklearn.preprocessing import MultiLabelBinarizer

from taxonomy import load_priority, primary_label

ROOT = Path(__file__).resolve().parents[2]
RESULT_DIR = ROOT / "data" / "processed" / "llm_labels"
REPORT_DIR = ROOT / "reports" / "llm_eval"
MISMATCH_DIR = ROOT / "data" / "processed" / "llm_eval"
GOLD_FILES = {
    "pilot": ROOT / "data" / "labels" / "pilot_taxonomy_100.csv",
    "validation": ROOT / "data" / "labels" / "validation_100_labeled.csv",
}


def parse_args() -> argparse.Namespace:
    """실행 옵션을 읽는다."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-name", required=True, help="평가할 결과 파일 이름 (llm_labels/{run_name}.jsonl)")
    parser.add_argument("--labels", choices=list(GOLD_FILES), required=True, help="정답 라벨 파일")
    return parser.parse_args()


def load_gold(name: str, order: list[str]) -> pd.DataFrame:
    """정답 파일을 읽어 review_id, title, message, gold_labels(목록), note로 맞춘다.

    파일럿은 labels 컬럼('A|B'), 검증은 유형별 0/1 컬럼에서 라벨 목록을 만든다.
    """
    df = pd.read_csv(GOLD_FILES[name], encoding="utf-8-sig", dtype=str, keep_default_na=False)
    if name == "pilot":
        labels = df["labels"].str.split("|")
    else:
        labels = df.apply(lambda r: [c for c in order if r[c].strip() == "1"], axis=1)
    gold = pd.DataFrame({
        "review_id": df["review_id"],
        "title": df["review_comment_title"],
        "message": df["review_comment_message"],
        "gold_labels": labels.apply(lambda ls: [c for c in order if c in ls]),
        "gold_primary_file": df["primary_label"],
        "note": df["note"],
    })
    unknown = {c for ls in labels for c in ls} - set(order)
    assert not unknown, f"정답 파일에 알 수 없는 라벨: {unknown}"
    return gold


def load_results(run_name: str) -> pd.DataFrame:
    """결과 JSONL을 읽는다. review_id가 중복되면 첫 레코드만 쓴다."""
    path = RESULT_DIR / f"{run_name}.jsonl"
    with path.open(encoding="utf-8") as f:
        recs = [json.loads(line) for line in f if line.strip()]
    df = pd.DataFrame(recs)
    n_dup = df["review_id"].duplicated().sum()
    if n_dup:
        print(f"[주의] 결과 파일에 중복 review_id {n_dup}건 → 첫 레코드만 사용")
    return df.drop_duplicates("review_id", keep="first")


def fmt_list(labels: list[str]) -> str:
    """라벨 목록을 'A|B' 문자열로 바꾼다."""
    return "|".join(labels)


def fmt_evidence(evidence) -> str:
    """evidence 목록을 '[유형] 구절' 줄 단위 문자열로 바꾼다(없으면 빈 문자열)."""
    if not isinstance(evidence, list):
        return ""
    return "\n".join(f"[{e['label']}] {e['quote']}" for e in evidence)


def compute_metrics(df: pd.DataFrame, order: list[str]) -> dict:
    """완전 일치율, 유형별·micro·macro 지표, 주 원인 정확도·kappa를 계산한다."""
    mlb = MultiLabelBinarizer(classes=order)
    y_true = mlb.fit_transform(df["gold_labels"])
    y_pred = mlb.transform(df["llm_labels"])
    report = classification_report(y_true, y_pred, target_names=order, output_dict=True, zero_division=0)
    present = sorted(set(df["gold_primary"]) | set(df["llm_primary"]), key=order.index)
    return {
        "n": len(df),
        "exact_match": accuracy_score(y_true, y_pred),
        "per_label": {c: report[c] for c in order},
        "micro": report["micro avg"],
        "macro": report["macro avg"],
        "primary_acc": accuracy_score(df["gold_primary"], df["llm_primary"]),
        "primary_kappa": cohen_kappa_score(df["gold_primary"], df["llm_primary"]),
        "primary_labels": present,
        "primary_cm": confusion_matrix(df["gold_primary"], df["llm_primary"], labels=present),
    }


def build_report(args, meta: dict, m: dict, n_missing: int, n_extra: int, df: pd.DataFrame, order: list[str]) -> str:
    """지표 요약 마크다운을 만든다."""
    lines = [
        f"# LLM 분류 평가: {args.run_name} vs {args.labels}",
        "",
        f"- 모델: {meta['model']} / 분류 체계: {meta['taxonomy_version']} / prompt_hash: {meta['prompt_hash']}",
        f"- 평가 건수: {m['n']}건 (정답에 있는데 결과에 없는 review_id: {n_missing}건, 정답에 없는 결과: {n_extra}건)",
        "",
        "## 전체 지표",
        "",
        "| 지표 | 값 |",
        "|---|---|",
        f"| 완전 일치율 | {m['exact_match']:.3f} |",
        f"| micro F1 | {m['micro']['f1-score']:.3f} (P {m['micro']['precision']:.3f} / R {m['micro']['recall']:.3f}) |",
        f"| macro F1 | {m['macro']['f1-score']:.3f} (P {m['macro']['precision']:.3f} / R {m['macro']['recall']:.3f}) |",
        f"| 주 원인 정확도 | {m['primary_acc']:.3f} |",
        f"| 주 원인 Cohen's kappa | {m['primary_kappa']:.3f} |",
        "",
        "macro F1은 정답 건수 0인 유형도 0점으로 포함해 평균한다.",
        "",
        "## 유형별 지표",
        "",
        "| 유형 | 정밀도 | 재현율 | F1 | 정답 건수 | LLM 부여 | 빠뜨림(FN) | 잘못 붙임(FP) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    missed = Counter(c for ls in df["missed"] for c in ls)
    added = Counter(c for ls in df["added"] for c in ls)
    llm_count = Counter(c for ls in df["llm_labels"] for c in ls)
    for c in order:
        r = m["per_label"][c]
        lines.append(
            f"| {c} | {r['precision']:.3f} | {r['recall']:.3f} | {r['f1-score']:.3f} | {int(r['support'])} "
            f"| {llm_count[c]} | {missed[c]} | {added[c]} |"
        )
    labels = m["primary_labels"]
    lines += [
        "",
        "## 주 원인 혼동행렬 (행: 정답, 열: LLM)",
        "",
        "| 정답 \\ LLM | " + " | ".join(labels) + " |",
        "|---|" + "---|" * len(labels),
    ]
    for label, row in zip(labels, m["primary_cm"]):
        lines.append(f"| {label} | " + " | ".join(str(v) if v else "·" for v in row) + " |")
    return "\n".join(lines) + "\n"


def build_rule_effects(df: pd.DataFrame) -> str:
    """후처리 규칙별·발동 표현별로 적용 건수와 정답에 가까워진/틀어진 건수를 표로 만든다.

    정답과의 거리는 라벨 집합의 대칭차 크기로 잰다(raw_labels 대비 labels).
    """
    rows = Counter()
    for _, r in df.iterrows():
        gold = set(r["gold_labels"])
        before = len(gold ^ set(r["raw_labels"]))
        after = len(gold ^ set(r["llm_labels"]))
        effect = "closer" if after < before else "worse" if after > before else "same"
        for rule in r["postprocess_rules"]:
            name = rule.split(":")[0]
            keys = [(name, "(전체)")]
            if name == "R1_K_DELAY":
                keys.append((name, rule.split(":", 1)[1]))
            for key in keys:
                rows[key + ("applied",)] += 1
                rows[key + (effect,)] += 1
    keys = sorted({k[:2] for k in rows})
    lines = [
        "",
        "## 후처리 규칙 효과 (LLM 원래 결과 대비)",
        "",
        "| 규칙 | 세부 | 적용 | 정답에 가까워짐 | 변화 없음 | 틀어짐 |",
        "|---|---|---|---|---|---|",
    ]
    for key in keys:
        lines.append(
            f"| {key[0]} | {key[1]} | {rows[key + ('applied',)]} | {rows[key + ('closer',)]} "
            f"| {rows[key + ('same',)]} | {rows[key + ('worse',)]} |"
        )
    if not keys:
        lines.append("| (적용 없음) | | 0 | 0 | 0 | 0 |")
    return "\n".join(lines) + "\n"


def main() -> None:
    """결과와 정답을 결합해 지표를 계산하고 리포트·불일치 목록을 저장한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    order = load_priority()

    gold = load_gold(args.labels, order)
    results = load_results(args.run_name)
    n_missing = (~gold["review_id"].isin(results["review_id"])).sum()
    n_extra = (~results["review_id"].isin(gold["review_id"])).sum()
    if n_missing:
        print(f"[주의] 정답 파일에 있는데 결과에 없는 review_id: {n_missing}건 (평가에서 제외)")

    df = gold.merge(results, on="review_id", how="inner")
    df["llm_labels"] = df["labels"].apply(lambda ls: [c for c in order if c in ls])
    df["gold_primary"] = df["gold_labels"].apply(primary_label, order=order)
    df["llm_primary"] = df["llm_labels"].apply(primary_label, order=order)
    diff_primary = df[df["gold_primary_file"].ne("") & df["gold_primary_file"].ne(df["gold_primary"])]
    if len(diff_primary):
        print(f"[주의] 정답 파일의 primary_label이 우선순위 계산과 다른 행 {len(diff_primary)}건 → 계산값 사용")
    df["missed"] = df.apply(lambda r: [c for c in r["gold_labels"] if c not in r["llm_labels"]], axis=1)
    df["added"] = df.apply(lambda r: [c for c in r["llm_labels"] if c not in r["gold_labels"]], axis=1)

    m = compute_metrics(df, order)
    meta = {k: ", ".join(sorted(results[k].astype(str).unique())) for k in ["model", "taxonomy_version", "prompt_hash"]}
    report = build_report(args, meta, m, n_missing, n_extra, df, order)
    if "postprocess_rules" in df:
        report += build_rule_effects(df)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"{args.run_name}.md"
    report_path.write_text(report, encoding="utf-8")

    mis = df[df["missed"].str.len().gt(0) | df["added"].str.len().gt(0)]
    out = pd.DataFrame({
        "review_id": mis["review_id"],
        "제목": mis["title"],
        "본문": mis["message"],
        "정답 labels": mis["gold_labels"].apply(fmt_list),
        "LLM labels": mis["llm_labels"].apply(fmt_list),
        "빠뜨린 라벨": mis["missed"].apply(fmt_list),
        "잘못 붙인 라벨": mis["added"].apply(fmt_list),
        "LLM evidence": mis["evidence"].apply(fmt_evidence) if "evidence" in mis else "",
        "LLM reason": mis["reason"],
        "정답 note": mis["note"],
    })
    MISMATCH_DIR.mkdir(parents=True, exist_ok=True)
    mis_path = MISMATCH_DIR / f"{args.run_name}_mismatches.csv"
    out.to_csv(mis_path, index=False, encoding="utf-8-sig")

    print(report)
    print(f"저장: {report_path.relative_to(ROOT)}")
    print(f"저장: {mis_path.relative_to(ROOT)} (불일치 {len(out)}건)")


if __name__ == "__main__":
    main()
