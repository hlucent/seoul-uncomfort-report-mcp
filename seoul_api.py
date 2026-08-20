"""서울 열린데이터광장 스마트 불편신고 통계 API 공통 호출 로직."""
import os
import re
from typing import Any

import httpx

BASE_URL = "http://openapi.seoul.go.kr:8088"


def _get_api_key() -> str:
    key = os.environ.get("SEOUL_API_KEY")
    if not key:
        raise RuntimeError("SEOUL_API_KEY 환경변수가 설정되지 않았습니다.")
    return key


def _safe_int(v: Any) -> int:
    """API 숫자 필드는 float(예: 55567.0)로 오며, 미래 월은 0.0으로 온다."""
    if v is None or v == "":
        return 0
    return int(float(v))


def _parse_xml_fallback(text: str) -> dict:
    code_match = re.search(r"<CODE>(.*?)</CODE>", text)
    message_match = re.search(r"<MESSAGE>(.*?)</MESSAGE>", text)
    return {
        "RESULT": {
            "CODE": code_match.group(1) if code_match else "ERROR-UNKNOWN",
            "MESSAGE": message_match.group(1) if message_match else text[:200],
        },
        "row": [],
        "list_total_count": 0,
    }


def _request(service: str, start_index: int, end_index: int, year: str | None = None, month: str | None = None) -> dict:
    key = _get_api_key()
    segments = [BASE_URL, key, "json", service, str(start_index), str(end_index)]
    if year:
        segments.append(year)
        if month:
            segments.append(month)
    url = "/".join(segments)

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url)

    try:
        data = resp.json()
    except ValueError:
        parsed = _parse_xml_fallback(resp.text)
        return parsed

    body = data.get(service, {})
    result = body.get("RESULT", {})
    rows = body.get("row", [])
    if isinstance(rows, dict):
        rows = [rows]

    return {
        "RESULT": result,
        "row": rows,
        "list_total_count": body.get("list_total_count", 0),
    }


def fetch_sector_stat(year: str | None = None, month: str | None = None, start_index: int = 1, end_index: int = 20) -> dict:
    return _request("SmartUncomfStatSector", start_index, end_index, year, month)


def fetch_locale_stat(year: str | None = None, month: str | None = None, start_index: int = 1, end_index: int = 20) -> dict:
    return _request("SmartUncomfStatLocale", start_index, end_index, year, month)


def fetch_month_stat(year: str | None = None, start_index: int = 1, end_index: int = 20) -> dict:
    return _request("SmartUncomfStatMonth", start_index, end_index, year)
