# CLAUDE.md — seoul-uncomfort-report-mcp 실행 지침

## 0. 절대 규칙 (최우선 준수)

- **DEVPLAN.md 하나만 먼저 읽고 시작한다.** 다른 문서 재탐색 금지.
- **웹서치 금지.** API 스펙은 DEVPLAN.md에 이미 정리되어 있음.
- 불확실하면 추측성 재설계 대신 기본값 1개로 구현 후 DEVLOG.md에 "확인 필요"로 기록한다.
- 동일 오류 최대 3회까지만 재시도. 3회 실패 시 기록하고 사용자에게 보고한다.
- **역할 범위는 "코드 구현 + 로컬 실측 테스트"까지다.** `fly launch`, `fly secrets set`,
  `flyctl deploy`, `fly logs` 등 fly.io 관련 명령은 절대 스스로 실행하지 않는다.
- 배포 준비(코드 구현, 로컬 테스트, git commit/push)가 끝나면 아래 "정지 시점"에서 멈추고,
  안내 문구를 출력한다.

---

## 1. 기술적으로 반드시 적용할 것

### 1-1. `.env`
BOM 없는 UTF-8로 저장. 갱신 시:
```python
# [System.IO.File]::WriteAllText(경로, "KEY=값", [System.Text.UTF8Encoding]::new($false))
```

### 1-2. `server.py`의 `mcp.run()` — `stateless_http=True` 필수
```python
mcp.run(transport="streamable-http", host="0.0.0.0", port=port, stateless_http=True)
```
이 옵션 누락 시 Claude.ai 커넥터에서 "사용 가능한 도구 없음"으로 보이는 문제 발생 전례 있음.
절대 빠뜨리지 않는다.

### 1-3. 응답 파싱 — JSON 우선, XML 폴백 필수
`response.json()`이 실패하면 정규식으로 `<CODE>`/`<MESSAGE>` 패턴을 추출하는 폴백을 구현한다.

### 1-4. `row` 필드 정규화
API 응답에서 결과가 1건이면 `row`가 단일 dict, 여러 건이면 list로 올 수 있다 (JSON 변환기
특성). 항상 list로 정규화하는 방어 로직을 넣는다:
```python
rows = data.get("row", [])
if isinstance(rows, dict):
    rows = [rows]
```

### 1-5. 빈 값 필드 처리 (SmartUncomfStatMonth 전용)
아직 지나지 않은 달은 `<MON_08/>`처럼 빈 태그로 온다. JSON 변환 시 빈 문자열이나 None이 될
수 있으므로, 숫자 필드 파싱 시 다음과 같이 안전 변환한다:
```python
def _safe_int(v):
    if v is None or v == "":
        return None  # 또는 0 — DEVLOG.md에 어느 쪽으로 확정했는지 기록
    return int(v)
```

### 1-6. 인증키 위치 — 경로 세그먼트 방식 우선 시도
DEVPLAN.md 1-1절 참고. 요청 URL은 다음 형태를 기본으로 시도한다:
```
http://openapi.seoul.go.kr:8088/{KEY}/{TYPE}/{SERVICE}/{START_INDEX}/{END_INDEX}/{YEAR}/{MONTH}
```
ERROR-300(필수값 누락)이 반복되면 쿼리 파라미터 방식(`?KEY=`)도 시도해 실측 결과를
DEVLOG.md에 남긴다.

### 1-7. IP 추출 — Fly-Client-IP 우선
```python
def _get_client_ip(request: Request) -> str:
    fly_client_ip = request.headers.get("fly-client-ip")
    if fly_client_ip:
        return fly_client_ip.strip()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
```

### 1-8. CORS preflight(OPTIONS) rate limit 제외
```python
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        # ... 이하 카운팅 로직
```

---

## 2. API 키 취급 원칙

- 실제 키 값은 `os.environ`으로만 읽는다. 코드에 하드코딩 금지.
- `.env` 갱신 후 재테스트 전, 파일이 실제로 바뀌었는지(바이트 수 또는 값 앞부분 비교) 확인한다.
- 키를 표준출력에 그대로 출력하는 디버깅 금지. 필요하면 앞 4자리 + `...` + 길이만 출력.
- 3개 서비스(SmartUncomfStatSector/Locale/Month)가 동일 키로 동작하는지 먼저 확인하고,
  안 되면 서비스별 개별 활용신청 여부를 DEVLOG.md에 "확인 필요"로 기록한다.
- 환경변수명: `SEOUL_API_KEY`

---

## 3. 작업 순서

1. `requirements.txt` (`fastmcp`, `httpx`, `python-dotenv`)
2. `seoul_api.py` — 공통 API 호출 함수 (인증키 경로 세그먼트 방식, JSON 우선 + XML 폴백,
   `row` 정규화, 빈 값 처리 포함). 서비스별로 함수 분리:
   `fetch_sector_stat()`, `fetch_locale_stat()`, `fetch_month_stat()`
3. `server.py` — 툴 3개 정의 (DEVPLAN.md 3절), docstring에 필드/단위 명시,
   `stateless_http=True` 반영, rate limit 미들웨어 포함 (2-7 표준)
4. `.env.example`, `.gitignore`
5. 로컬 테스트 (실제 키로 3개 툴 각각 호출)
   - **DEVPLAN.md 2절 "실측 필요 항목" 5가지를 순서대로 확인**
   - 인증키 위치(경로 vs 쿼리)부터 최우선 확인 — ERROR-300 반복 시 이것부터 의심
   - YEAR/MONTH 선택 파라미터 조합별 테스트 (전부 채움/전부 생략/부분 채움)
   - `SmartUncomfStatMonth`는 MONTH 파라미터가 없다는 점 재확인 (다른 2개와 다름)
   - `list_total_count`로 전체 건수 실측 확인
6. FastMCP 서버 스모크 테스트 (initialize 요청까지만)
7. `Dockerfile`, `fly.toml` (표준 `[http_service]` 템플릿 사용, 앱 이름만 치환)
8. README/DEVLOG 갱신 — 실측으로 확인된 내용을 실제 동작 기준으로 정확히 기술
9. `git add/commit/push`까지 수행 (push는 자동 진행 가능)
10. **여기서 정지** — 아래 "사용자 안내 문구" 출력

---

## 4. 하지 말 것

- 툴 개수를 3개보다 늘리지 않기 (분야/위치/월 3개 축 그대로 유지)
- 인증키 하드코딩 금지
- `stateless_http=True` 누락 금지
- `fly launch` / `fly secrets set` / `flyctl deploy` / `fly logs` 자동 실행 금지
- rate limit 미들웨어 누락 금지
- fly.toml을 `fly launch` 기본 생성 상태(`[[services]]`, `ports = []`)로 방치하지 않기
- X-Forwarded-For를 무조건 최우선 신뢰하지 않기
- CORS preflight를 rate limit 카운터에 포함시키지 않기
- `SmartUncomfStatMonth`에 존재하지 않는 MONTH 파라미터를 잘못 추가하지 않기

---

## 5. MCP 서버 보안 정책 (rate limit, 표준 3단계)

1. 분당 3회 초과 시 429
2. 1시간 내 429 5회 이상 → 24시간 차단
3. 24시간 rolling 총 30회 초과 시 429

in-memory 저장, `Fly-Client-IP` 우선 신뢰, OPTIONS 제외, `Middleware(RateLimitMiddleware)`
형태로 `mcp.run(..., middleware=[...])`에 전달. (CLAUDE.md 표준 원칙 그대로 적용)

---

## 6. 정지 시점 이후 사용자 안내 문구

```
개발 및 로컬 실측 테스트가 끝났습니다. PowerShell 창에서 아래를 순서대로 실행하세요:

cd "C:\Users\hwang\Projects\seoul-uncomfort-report-mcp"
fly launch --no-deploy

⚠️ flyctl deploy 전에 fly.toml을 열어 [[services]] 블록이 있는지 확인하세요.
있다면 "fly.toml을 http_service 방식으로 바꿔줘"라고 요청한 뒤 진행하세요.

fly secrets set SEOUL_API_KEY=발급받은키
flyctl deploy

배포 완료 후 주소 뒤에 "/mcp"를 붙여 Claude.ai 커넥터에 연결하세요.
예: https://seoul-uncomfort-report-mcp.fly.dev/mcp

연결 후 반드시 새 대화창에서 "사용 가능한 도구" 3개가 뜨는지 확인하세요.
```
