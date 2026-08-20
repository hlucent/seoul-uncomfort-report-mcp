"""서울시 스마트 불편신고 통계 MCP 서버."""
import os
import time
from collections import defaultdict

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from seoul_api import _safe_int, fetch_locale_stat, fetch_month_stat, fetch_sector_stat

load_dotenv()

mcp = FastMCP("seoul-uncomfort-report-mcp")

SECTOR_NAMES = {
    "01": "교통", "02": "도로", "03": "청소", "04": "주택건축", "05": "치수방재",
    "06": "가로정비", "07": "보건", "08": "공원녹지", "09": "환경", "10": "경제/산업",
    "11": "소방안전", "12": "기타 불편사항",
}

GU_NAMES = [
    "종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구",
    "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구",
    "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구",
    "강동구",
]


def _normalize_sector_row(row: dict) -> dict:
    result = {"year": row.get("YEAR"), "month": row.get("MONTH")}
    for code, name in SECTOR_NAMES.items():
        result[name] = _safe_int(row.get(f"RCPT_CNT_{code}"))
    result["합계"] = _safe_int(row.get("RCPT_CNT_TOTAL"))
    return result


def _normalize_locale_row(row: dict) -> dict:
    result = {"year": row.get("YEAR"), "month": row.get("MONTH")}
    for i, name in enumerate(GU_NAMES, start=1):
        result[name] = _safe_int(row.get(f"GU_NM_{i:02d}"))
    result["타시도"] = _safe_int(row.get("GU_NM_ETC"))
    return result


def _normalize_month_row(row: dict) -> dict:
    result = {"year": row.get("YEAR")}
    for m in range(1, 13):
        result[f"{m}월"] = _safe_int(row.get(f"MON_{m:02d}"))
    result["합계"] = _safe_int(row.get("MON_TOTAL"))
    return result


@mcp.tool()
def get_uncomfort_report_by_sector(
    year: str | None = None,
    month: str | None = None,
    start_index: int = 1,
    end_index: int = 20,
) -> dict:
    """서울시 스마트 불편신고를 분야별(교통/도로/청소 등 12개 분야) 건수로 조회한다.

    단위: 건수(정수). year/month를 생략하면 전체 기간을 페이징하여 반환한다.
    year만 지정하면 해당 연도의 월별 데이터를 모두 반환한다.
    """
    data = fetch_sector_stat(year, month, start_index, end_index)
    return {
        "result": data["RESULT"],
        "total_count": data["list_total_count"],
        "rows": [_normalize_sector_row(r) for r in data["row"]],
    }


@mcp.tool()
def get_uncomfort_report_by_district(
    year: str | None = None,
    month: str | None = None,
    start_index: int = 1,
    end_index: int = 20,
) -> dict:
    """서울시 스마트 불편신고를 자치구별(25개 자치구 + 타시도) 건수로 조회한다.

    단위: 건수(정수). year/month를 생략하면 전체 기간을 페이징하여 반환한다.
    """
    data = fetch_locale_stat(year, month, start_index, end_index)
    return {
        "result": data["RESULT"],
        "total_count": data["list_total_count"],
        "rows": [_normalize_locale_row(r) for r in data["row"]],
    }


@mcp.tool()
def get_uncomfort_report_by_month(
    year: str | None = None,
    start_index: int = 1,
    end_index: int = 20,
) -> dict:
    """서울시 스마트 불편신고를 연도별 월간(1~12월) 건수로 조회한다.

    단위: 건수(정수). MONTH 파라미터는 존재하지 않는다(연도 단위 집계만 지원).
    아직 지나지 않은 달은 0으로 표시된다.
    """
    data = fetch_month_stat(year, start_index, end_index)
    return {
        "result": data["RESULT"],
        "total_count": data["list_total_count"],
        "rows": [_normalize_month_row(r) for r in data["row"]],
    }


# ---- Rate limit middleware (CLAUDE.md 5절 표준 3단계) ----

_minute_hits: dict[str, list[float]] = defaultdict(list)
_daily_hits: dict[str, list[float]] = defaultdict(list)
_block_429_hits: dict[str, list[float]] = defaultdict(list)
_blocked_until: dict[str, float] = {}


def _get_client_ip(request: Request) -> str:
    fly_client_ip = request.headers.get("fly-client-ip")
    if fly_client_ip:
        return fly_client_ip.strip()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        ip = _get_client_ip(request)
        now = time.time()

        if ip in _blocked_until:
            if now < _blocked_until[ip]:
                return JSONResponse({"error": "blocked for 24h due to repeated rate limit violations"}, status_code=429)
            del _blocked_until[ip]

        _minute_hits[ip] = [t for t in _minute_hits[ip] if now - t < 60]
        _daily_hits[ip] = [t for t in _daily_hits[ip] if now - t < 86400]
        _block_429_hits[ip] = [t for t in _block_429_hits[ip] if now - t < 3600]

        rate_limited = False
        if len(_minute_hits[ip]) >= 3:
            rate_limited = True
        elif len(_daily_hits[ip]) >= 30:
            rate_limited = True

        if rate_limited:
            _block_429_hits[ip].append(now)
            if len(_block_429_hits[ip]) >= 5:
                _blocked_until[ip] = now + 86400
            return JSONResponse({"error": "rate limit exceeded"}, status_code=429)

        _minute_hits[ip].append(now)
        _daily_hits[ip].append(now)

        return await call_next(request)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        stateless_http=True,
        middleware=[Middleware(RateLimitMiddleware)],
    )
