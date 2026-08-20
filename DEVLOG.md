# DEVLOG.md — seoul-uncomfort-report-mcp

진행 기록을 시간순으로 남깁니다. 실측으로 확인된 내용, 발생한 문제, 해결 방법을 구체적으로
기록합니다.

---

## 2026-08-20 — 설계 문서 4종 작성 (Claude 웹챗)

- DEVPLAN.md/CLAUDE.md/README.md/DEVLOG.md 4종 작성 완료.
- 서울시 스마트 불편신고 통계 API 3종(`SmartUncomfStatSector`, `SmartUncomfStatLocale`,
  `SmartUncomfStatMonth`)을 통합 1개 MCP로 설계. 제공부서(디지털도시국 공간정보과)와
  원본시스템(서울시 스마트 불편신고)이 3개 서비스 모두 동일함을 명세서로 확인.
- 명세서(xls) 3개 + 실제 응답 예제(XML) 3개를 모두 확보한 상태로 시작 — 응답 구조(최상위
  태그, `row` 반복 구조, `list_total_count` 위치)를 사전에 확인했으므로 실측 단계에서
  구조 관련 에러 발생 가능성은 낮음.
- 예제로 사전 확인된 사항:
  - 3개 서비스 모두 `<{SERVICE}><list_total_count>...</list_total_count><RESULT>...</RESULT><row>...</row>...</{SERVICE}>` 구조 공유
  - `SmartUncomfStatMonth`는 아직 지나지 않은 달이 빈 태그(`<MON_08/>`)로 옴 — 파싱 시
    안전 처리 필요 (CLAUDE.md 1-5절에 이미 반영)
  - `SmartUncomfStatMonth`는 다른 2개와 달리 MONTH 선택 파라미터가 명세서에 없음 — 툴
    설계에서 파라미터를 다르게 함 (CLAUDE.md 4절 "하지 말 것"에 명시)
- **아직 실측 필요** (DEVPLAN.md 2절 참고, Claude Code가 확인할 것):
  1. 인증키 위치(경로 세그먼트 vs 쿼리 파라미터)
  2. 선택 파라미터(YEAR/MONTH) 부분 채움 시 에러 여부
  3. JSON 요청 시 XML과 동일 스키마인지
  4. 3개 서비스가 인증키 1개로 공용 동작하는지
  5. 빈 태그 필드가 JSON에서 빈 문자열/null 중 어느 쪽으로 오는지

---

## 2026-08-20 — 구현 및 로컬 실측 테스트 (Claude Code)

- `requirements.txt`, `seoul_api.py`, `server.py`, `Dockerfile`, `fly.toml` 작성 완료.
- DEVPLAN.md 2절 "실측 필요 항목" 5가지 전부 확인 완료 (`.env`에 이미 유효한 키가 있어
  즉시 실측 진행):
  1. **인증키 위치**: 경로 세그먼트 방식(`/{KEY}/json/{SERVICE}/{START}/{END}/...`)이
     첫 시도에 즉시 성공(`INFO-000`). 쿼리 파라미터 방식은 시도하지 않음.
  2. **YEAR/MONTH 부분 채움**: 전부 생략(`SmartUncomfStatSector`가 167건 반환),
     YEAR만 지정(6건 반환), YEAR+MONTH 모두 지정(1건 반환) 모두 정상 동작 확인.
     `SmartUncomfStatMonth`는 MONTH 세그먼트를 아예 붙이지 않고 YEAR까지만 붙여 정상 동작.
  3. **JSON 스키마**: `TYPE=json` 요청 시 최상위 키가 서비스명이고 그 아래
     `list_total_count`/`RESULT`/`row` 구조로, 명세서 XML 구조와 필드명이 동일함을 확인.
  4. **키 공유 여부**: 3개 서비스 모두 하나의 `SEOUL_API_KEY`로 정상 응답(`INFO-000`) —
     서비스별 개별 활용신청 불필요한 것으로 확인.
  5. **빈 태그 필드**: 지나지 않은 달(예: 2026-08 시점 기준 `MON_08`~`MON_12`)이 JSON에서
     빈 문자열/null이 아니라 **`0.0`(실수)**으로 옴을 실측 확인. `_safe_int()`로 정수 변환.
  - 추가 발견: 모든 숫자 필드가 JSON에서 정수가 아니라 실수(`55567.0`)로 내려옴 —
    `_safe_int()`가 `float()` 경유 변환으로 처리.
- `server.py` FastMCP 스모크 테스트: `initialize` 요청 정상 응답, `tools/list`로 3개 툴
  (`get_uncomfort_report_by_sector`, `get_uncomfort_report_by_district`,
  `get_uncomfort_report_by_month`) 노출 확인.
- Rate limit 미들웨어 동작 확인: 동일 IP로 4회 연속 요청 시 1회 성공(200) 이후
  3회 연속 429 반환 — 분당 3회 제한 정상 동작.
- `stateless_http=True` 적용 및 `Fly-Client-IP` 우선 IP 추출, OPTIONS 제외 로직 반영.

## (다음 항목 — 사용자가 fly.io 배포 시 확인)

- [x] 로컬 실측 테스트 결과 — 위 항목 참고
- [ ] 배포 결과 및 커넥터 연결 확인
