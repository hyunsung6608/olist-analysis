"""MySQL 연결용 SQLAlchemy 엔진을 만든다.

접속 정보는 .env의 MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB에서 읽는다.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, Engine, create_engine

ROOT = Path(__file__).resolve().parents[2]
ENV_KEYS = ["MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DB"]


def load_settings() -> dict[str, str]:
    """.env에서 접속 정보를 읽는다. 비어 있는 항목이 있으면 항목 이름을 담아 에러를 낸다."""
    load_dotenv(ROOT / ".env", encoding="utf-8")
    settings = {key: os.getenv(key, "").strip() for key in ENV_KEYS}
    missing = [key for key, value in settings.items() if not value]
    if missing:
        raise RuntimeError(f".env에 MySQL 접속 정보가 비어 있습니다: {', '.join(missing)} ({ROOT / '.env'})")
    if not settings["MYSQL_PORT"].isdigit():
        raise RuntimeError(f"MYSQL_PORT는 숫자여야 합니다: {settings['MYSQL_PORT']!r}")
    return settings


def get_url() -> URL:
    """접속 URL 객체를 만든다. URL.create가 비밀번호의 특수문자를 알아서 처리한다."""
    s = load_settings()
    return URL.create(
        "mysql+pymysql",
        username=s["MYSQL_USER"],
        password=s["MYSQL_PASSWORD"],
        host=s["MYSQL_HOST"],
        port=int(s["MYSQL_PORT"]),
        database=s["MYSQL_DB"],
        query={"charset": "utf8mb4"},
    )


def get_engine(**kwargs) -> Engine:
    """utf8mb4 PyMySQL 엔진을 만든다. 끊어진 연결은 사용 전에 확인(pool_pre_ping)한다."""
    return create_engine(get_url(), pool_pre_ping=True, **kwargs)


def describe_url() -> str:
    """비밀번호를 가린 접속 URL 문자열(로그 출력용)."""
    return get_url().render_as_string(hide_password=True)
