"""리뷰를 Gemini로 불만 유형별 분류해 JSONL로 저장한다.

결과 파일(data/processed/llm_labels/{run_name}.jsonl)에 이미 있는 review_id는 건너뛰므로
중간에 멈춰도 같은 명령으로 이어서 실행할 수 있다.

예) python src/llm/classify_reviews.py --input all --dry-run
    python src/llm/classify_reviews.py --input pilot --run-name test_resume --max-calls 1
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors
from pydantic import TypeAdapter, ValidationError
from tenacity import retry, retry_if_exception, stop_after_attempt
from tqdm import tqdm

from data import INPUTS, load_targets
from postprocess import find_violations, postprocess
from prompts import ReviewLabel, build_generate_config, build_system_instruction, build_user_message
from taxonomy import SOLO, load_priority, load_version, primary_label

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "processed" / "llm_labels"

MAX_RETRIES = 5  # 429·서버 오류 재시도 횟수(첫 시도 제외)
RETRYABLE_CODES = {429, 500, 503, 504}


class ResponseInvalid(Exception):
    """응답이 스키마나 검증 규칙을 통과하지 못함."""


class CallLimitReached(Exception):
    """이번 실행의 최대 호출 수(--max-calls)에 도달함."""


def parse_args() -> argparse.Namespace:
    """실행 옵션을 읽는다. --dry-run이 아니면 --run-name과 --max-calls가 필수."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", choices=INPUTS, required=True, help="분류 대상")
    parser.add_argument("--run-name", help="결과 파일 이름 (data/processed/llm_labels/{run_name}.jsonl)")
    parser.add_argument("--batch-size", type=int, default=30, help="호출 1회당 리뷰 수 (기본 30)")
    parser.add_argument("--rpm", type=float, default=10, help="분당 최대 호출 수 (기본 10)")
    parser.add_argument("--max-calls", type=int, help="이번 실행의 최대 API 호출 수 (재시도·재요청 포함)")
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 대상 건수·호출 수·예상 토큰만 출력")
    args = parser.parse_args()
    if not args.dry_run and (not args.run_name or args.max_calls is None):
        parser.error("실제 실행에는 --run-name과 --max-calls가 필요합니다.")
    if args.run_name and not re.fullmatch(r"[\w.-]+", args.run_name):
        parser.error("--run-name에는 영문·숫자·_ . - 만 쓸 수 있습니다.")
    return args


def estimate_tokens(text: str) -> int:
    """API 없이 토큰 수를 대략 추정한다(ASCII 3.5자당 1토큰, 한글 등 그 외 문자 1자당 1토큰).

    파일럿 2배치 실측(호출당 입력 약 7,800토큰)에 맞춰 보정한 값이다.
    """
    n_ascii = sum(ch.isascii() for ch in text)
    return math.ceil(n_ascii / 3.5 + (len(text) - n_ascii))


def to_review_dicts(batch) -> list[dict]:
    """DataFrame 일부를 프롬프트 입력용 dict 목록(review_id, title, message)으로 바꾼다."""
    def clean(value) -> str:
        return "" if value is None or (isinstance(value, float) and math.isnan(value)) else str(value)

    return [
        {"review_id": r.review_id, "title": clean(r.review_comment_title), "message": clean(r.review_comment_message)}
        for r in batch.itertuples(index=False)
    ]


def make_prompt_hash(system_instruction: str) -> str:
    """시스템 지시문·사용자 메시지 형식·응답 스키마를 합친 해시(앞 12자리)를 만든다."""
    sample_message = build_user_message([{"review_id": "x", "title": "", "message": ""}])
    schema = json.dumps(TypeAdapter(list[ReviewLabel]).json_schema(), ensure_ascii=False, sort_keys=True)
    payload = "\n".join([system_instruction, sample_message, schema])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def read_done(path: Path) -> tuple[set[str], set[tuple[str, str]]]:
    """기존 결과 파일에서 처리된 review_id와 (model, prompt_hash) 조합을 읽는다. 깨진 줄은 무시한다."""
    done, versions = set(), set()
    if not path.exists():
        return done, versions
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                print(f"[주의] {path.name} {n}번째 줄이 깨져 있어 무시합니다(해당 리뷰는 다시 처리).")
                continue
            done.add(rec["review_id"])
            versions.add((rec.get("model"), rec.get("prompt_hash")))
    return done, versions


def append_jsonl(path: Path, records: list[dict]) -> None:
    """레코드를 JSONL 끝에 추가하고 바로 디스크에 기록한다."""
    with path.open("a", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def retry_delay_seconds(err: errors.APIError) -> float | None:
    """429 응답에 담긴 재시도 대기 시간(RetryInfo.retryDelay 또는 메시지의 'retry in Ns')을 초로 읽는다."""
    details = (err.details or {}).get("error", {}).get("details", []) if isinstance(err.details, dict) else []
    for d in details:
        if str(d.get("@type", "")).endswith("RetryInfo") and d.get("retryDelay"):
            return float(str(d["retryDelay"]).rstrip("s"))
    match = re.search(r"retry in ([\d.]+)\s*s", str(err.message or ""), re.I)
    return float(match.group(1)) if match else None


def is_retryable(exc: BaseException) -> bool:
    """429·서버 오류(500/503/504)만 재시도한다."""
    return isinstance(exc, errors.APIError) and exc.code in RETRYABLE_CODES


def wait_for_retry(retry_state) -> float:
    """429는 응답이 알려 준 대기 시간 + 1초, 그 외는 지수 백오프(최대 60초)로 기다린다."""
    exc = retry_state.outcome.exception()
    delay = retry_delay_seconds(exc) if exc.code == 429 else None
    if delay is None:
        delay = min(2 ** retry_state.attempt_number * 2, 60)
    else:
        delay += 1
    tqdm.write(f"[재시도 {retry_state.attempt_number}/{MAX_RETRIES}] {exc.code} {exc.status} → {delay:.0f}초 대기")
    return delay


class GeminiClassifier:
    """요청 간격·호출 수 제한·재시도를 지키며 Gemini를 호출한다."""

    def __init__(self, api_key: str, model: str, rpm: float, max_calls: int):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.min_interval = 60 / rpm
        self.max_calls = max_calls
        self.calls = 0
        self.last_call = 0.0
        self.tokens = Counter()

    def _throttle(self) -> None:
        """직전 호출 시작 후 60/rpm초가 지나도록 기다린다."""
        wait = self.last_call + self.min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.last_call = time.monotonic()

    @retry(
        retry=retry_if_exception(is_retryable),
        stop=stop_after_attempt(MAX_RETRIES + 1),
        wait=wait_for_retry,
        reraise=True,
    )
    def call_model(self, system_instruction: str, user_message: str) -> str:
        """모델을 1회 호출해 응답 텍스트를 돌려준다. 다른 모델로 바꿀 때는 이 메서드만 교체한다."""
        if self.calls >= self.max_calls:
            raise CallLimitReached
        self._throttle()
        self.calls += 1
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_message,
            config=build_generate_config(system_instruction),
        )
        usage = response.usage_metadata
        if usage:
            self.tokens["input"] += usage.prompt_token_count or 0
            self.tokens["output"] += usage.candidates_token_count or 0
            self.tokens["thinking"] += usage.thoughts_token_count or 0
        return response.text or ""


def validate(text: str, expected_ids: list[str]) -> list[ReviewLabel]:
    """응답이 스키마에 맞고, review_id가 모두 정확히 한 번씩 오고, 라벨 규칙을 지키는지 확인한다."""
    try:
        results = TypeAdapter(list[ReviewLabel]).validate_json(text)
    except ValidationError as e:
        raise ResponseInvalid(f"스키마 불일치: {e.errors()[:3]}") from e
    counts = Counter(r.review_id for r in results)
    missing = set(expected_ids) - set(counts)
    extra = set(counts) - set(expected_ids)
    dup = [rid for rid, n in counts.items() if n > 1]
    if missing or extra or dup:
        raise ResponseInvalid(f"review_id 불일치: 누락 {len(missing)}, 초과 {len(extra)}, 중복 {len(dup)}")
    for r in results:
        codes = {label.value for label in r.labels}
        if not codes:
            raise ResponseInvalid(f"빈 labels: {r.review_id}")
        if codes & set(SOLO) and len(codes) > 1:
            raise ResponseInvalid(f"단독 라벨 규칙 위반: {r.review_id} {sorted(codes)}")
    return results


def classify_batch(clf: GeminiClassifier, system_instruction: str, reviews: list[dict]) -> list[ReviewLabel]:
    """배치 1개를 분류한다. 검증 실패 시 1회 재요청하고, 그래도 실패하면 ResponseInvalid를 던진다."""
    user_message = build_user_message(reviews)
    expected = [r["review_id"] for r in reviews]
    for attempt in (1, 2):
        text = clf.call_model(system_instruction, user_message)
        try:
            return validate(text, expected)
        except ResponseInvalid as e:
            if attempt == 2:
                raise ResponseInvalid(f"{e} | 응답 앞부분: {text[:500]}") from e
            tqdm.write(f"[검증 실패 → 재요청] {e}")


def print_dry_run(args, targets, pending, system_instruction: str) -> None:
    """API 호출 없이 대상 건수, 필요한 호출 수, 예상 입력 토큰을 출력한다."""
    n_calls = math.ceil(len(pending) / args.batch_size)
    system_tokens = estimate_tokens(system_instruction)
    review_tokens = sum(
        estimate_tokens(build_user_message(to_review_dicts(pending.iloc[i:i + args.batch_size])))
        for i in range(0, len(pending), args.batch_size)
    )
    total = system_tokens * n_calls + review_tokens
    print(f"[dry-run] 입력: {args.input} / 배치 크기: {args.batch_size} / RPM: {args.rpm:g}")
    print(f"  대상 리뷰: {len(targets):,}건 (이미 처리: {len(targets) - len(pending):,}건, 남은 건: {len(pending):,}건)")
    print(f"  필요한 호출 수: {n_calls:,}회")
    print(f"  예상 입력 토큰(근사): 시스템 지시문 {system_tokens:,} × {n_calls:,}회 + 리뷰 {review_tokens:,} = {total:,}")
    print(f"  호출 1회당 평균 입력 토큰(근사): {total / max(n_calls, 1):,.0f}")
    print(f"  최소 소요 시간(RPM 기준): 약 {n_calls / args.rpm:,.0f}분")
    if args.max_calls is not None:
        print(f"  --max-calls {args.max_calls} 기준 이번 실행 처리량: 최대 {min(args.max_calls * args.batch_size, len(pending)):,}건")


def main() -> None:
    """대상 리뷰를 배치로 나눠 분류하고, 배치마다 결과를 JSONL에 기록한 뒤 요약을 출력한다."""
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()

    targets = load_targets(args.input)
    out_path = OUT_DIR / f"{args.run_name}.jsonl" if args.run_name else None
    err_path = OUT_DIR / f"{args.run_name}_errors.jsonl" if args.run_name else None
    done, versions = read_done(out_path) if out_path else (set(), set())
    pending = targets[~targets["review_id"].isin(done)].reset_index(drop=True)
    system_instruction = build_system_instruction()

    if args.dry_run:
        print_dry_run(args, targets, pending, system_instruction)
        return

    load_dotenv(ROOT / ".env", encoding="utf-8")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "").strip()
    if not api_key or not model:
        sys.exit("[오류] .env에 GEMINI_API_KEY와 GEMINI_MODEL을 설정하세요.")

    prompt_hash = make_prompt_hash(system_instruction)
    taxonomy_version = load_version()
    order = load_priority()
    if versions - {(model, prompt_hash)}:
        print(f"[주의] 기존 결과에 다른 모델·프롬프트로 만든 레코드가 있습니다: {sorted(versions, key=str)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    clf = GeminiClassifier(api_key, model, args.rpm, args.max_calls)
    n_saved = n_error = n_error_batches = 0
    rule_counts, violation_counts = Counter(), Counter()
    stop_reason = "완료"
    batches = [pending.iloc[i:i + args.batch_size] for i in range(0, len(pending), args.batch_size)]
    print(f"모델: {model} / 분류 체계 {taxonomy_version} / prompt_hash {prompt_hash}")
    print(f"대상 {len(targets):,}건 중 이미 처리 {len(targets) - len(pending):,}건, 남은 {len(pending):,}건 ({len(batches):,}배치)")

    with tqdm(total=min(len(pending), args.max_calls * args.batch_size), unit="건") as bar:
        for batch in batches:
            reviews = to_review_dicts(batch)
            try:
                results = classify_batch(clf, system_instruction, reviews)
            except CallLimitReached:
                stop_reason = f"최대 호출 수({args.max_calls}회) 도달"
                break
            except ResponseInvalid as e:
                n_error += len(reviews)
                n_error_batches += 1
                append_jsonl(err_path, [{
                    "review_ids": [r["review_id"] for r in reviews],
                    "error": str(e),
                    "model": model,
                    "prompt_hash": prompt_hash,
                    "run_name": args.run_name,
                    "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }])
                tqdm.write(f"[에러 기록] {len(reviews)}건 → {err_path.name}")
                bar.update(len(reviews))
                continue
            except errors.APIError as e:
                stop_reason = f"API 오류로 중단: {e.code} {e.status} {str(e.message)[:200]}"
                break

            by_id = {r.review_id: r for r in results}
            created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            records = []
            for review in reviews:
                r = by_id[review["review_id"]]
                raw_labels = [c for c in order if c in {label.value for label in r.labels}]
                evidence = [{"quote": e.quote, "label": e.label.value} for e in r.evidence]
                labels, rules = postprocess(
                    {"raw_labels": raw_labels, "evidence": evidence}, review["title"], review["message"]
                )
                rule_counts.update(rule.split(":")[0] for rule in rules)
                violation_counts.update(find_violations(labels))
                records.append({
                    "review_id": review["review_id"],
                    "evidence": evidence,
                    "raw_labels": raw_labels,
                    "labels": labels,
                    "postprocess_rules": rules,
                    "primary_label": primary_label(labels, order),
                    "reason": r.reason,
                    "model": model,
                    "taxonomy_version": taxonomy_version,
                    "prompt_hash": prompt_hash,
                    "run_name": args.run_name,
                    "created_at": created_at,
                })
            append_jsonl(out_path, records)
            n_saved += len(records)
            bar.update(len(records))

    remaining = len(pending) - n_saved - n_error
    print(f"\n[요약] {stop_reason}")
    print(f"  이번 호출 수: {clf.calls}회 (최대 {args.max_calls}회)")
    print(f"  처리 건수: {n_saved}건 → {out_path.relative_to(ROOT)}")
    print(f"  에러 건수: {n_error}건 ({n_error_batches}배치)" + (f" → {err_path.relative_to(ROOT)}" if n_error else ""))
    print(f"  남은 건수: {remaining:,}건")
    print(f"  후처리 적용: {dict(rule_counts) or '없음'} / 남은 규칙 위반: {dict(violation_counts) or '없음'}")
    print(f"  입력 토큰: {clf.tokens['input']:,} / 출력 토큰: {clf.tokens['output']:,} (사고 토큰 {clf.tokens['thinking']:,} 별도)")


if __name__ == "__main__":
    main()
