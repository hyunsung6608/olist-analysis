"""검증 정답 라벨 중 분류 체계 규칙과 어긋난 건을 바로잡은 사본을 만든다.

원본(validation_100_labeled.csv)은 수정하지 않고, validation_100_adjudicated.csv로 저장한다.
수정한 행의 note 끝에 '[판정 수정] ...'을 덧붙이고, primary_label은 우선순위로 다시 계산한다.
"""
import sys
from pathlib import Path

import pandas as pd

from taxonomy import LABEL_CODES, load_priority, primary_label

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "labels" / "validation_100_labeled.csv"
OUT = ROOT / "data" / "labels" / "validation_100_adjudicated.csv"

# no: (제거할 유형, 추가할 유형, 근거)
CORRECTIONS = {
    39: (["NOT_RECEIVED"], [], "규칙 C: 일부만 받은 경우 NOT_RECEIVED 제외"),
    40: ([], ["DELAY"], "규칙 K: 미수령 + 경과 기간('mais de 30 dias') → DELAY"),
    58: ([], ["DELAY"], "규칙 K: 미수령 + 현재까지('até o momento') → DELAY"),
}


def main() -> None:
    """원본 정답을 읽어 CORRECTIONS를 적용하고 사본을 저장한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    order = load_priority()
    df = pd.read_csv(SRC, encoding="utf-8-sig", dtype=str, keep_default_na=False)

    for no, (remove, add, reason) in CORRECTIONS.items():
        idx = df.index[df["no"].astype(int) == no]
        assert len(idx) == 1, f"no {no} 행이 없음"
        i = idx[0]
        before = [c for c in LABEL_CODES if df.at[i, c] == "1"]
        for c in remove:
            assert df.at[i, c] == "1", f"no {no}: 제거할 {c}가 원래 없음"
            df.at[i, c] = "0"
        for c in add:
            assert df.at[i, c] == "0", f"no {no}: 추가할 {c}가 이미 있음"
            df.at[i, c] = "1"
        after = [c for c in LABEL_CODES if df.at[i, c] == "1"]
        note = df.at[i, "note"]
        df.at[i, "note"] = (note + " / " if note else "") + f"[판정 수정] {reason}"
        print(f"no {no}: {'|'.join(before)} → {'|'.join(after)} ({reason})")

    df["primary_label"] = df.apply(
        lambda r: primary_label([c for c in LABEL_CODES if r[c] == "1"], order), axis=1
    )
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"저장: {OUT.relative_to(ROOT)} {df.shape}")


if __name__ == "__main__":
    main()
