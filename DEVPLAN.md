# DEVPLAN.md — seoul-uncomfort-report-mcp (서울시 스마트 불편신고 통계 MCP)

## 0. 개요

서울시 스마트 불편신고 시스템에서 제공하는 통계 API 3종을 하나의 MCP 서버로 통합한다.
3개 서비스 모두 제공기관(서울특별시)·제공부서(디지털도시국 공간정보과)·원본시스템(서울시
스마트 불편신고)이 동일하며, 서비스명 패턴(`SmartUncomfStat + 축`)도 일관되어 하나의
API 군으로 취급한다 (프로젝트 지침 "R-ONE 공유 엔드포인트 → 툴 통합" 원칙 적용).

| 서비스 | 서비스명(SERVICE) | 축 |
|---|---|---|
| 분야별 불편신고 조회 | `SmartUncomfStatSector` | 분야(교통/도로/청소 등 12개) |
| 위치별 불편신고건수 조회 | `SmartUncomfStatLocale` | 서울시 25개 자치구 + 타시도 |
| 년도/월별 불편신고건수 조회 | `SmartUncomfStatMonth` | 연도 × 월(1~12) |

---

## 1. API 스펙 요약

### 1-1. 공통 사항

- **Base URL**: `http://openapi.seoul.go.kr:8088`
- **요청 URL 패턴**: `http://openapi.seoul.go.kr:8088/{KEY}/{TYPE}/{SERVICE}/{START_INDEX}/{END_INDEX}/{YEAR}/{MONTH}`
  - 인증키(KEY)가 **쿼리 파라미터가 아니라 URL 경로 세그먼트**로 들어가는 서울 열린데이터광장
    표준 방식이다. `?key=` 형태로 보내면 ERROR-300(필수값 누락) 발생 가능성 높음 — 실측 필요.
  - 3개 서비스 모두 이 URL 패턴을 공유하므로, 인증키도 공용일 가능성이 높으나 **서비스별로
    별도 "활용신청" 승인이 필요한지는 실측 필요** (서울 열린데이터광장은 API별 개별 승인이
    일반적이므로, 3개 모두 마이페이지에서 승인 상태 확인 권장).
- **TYPE**: `xml`(기본), `xmlf`(xml파일), `xls`(엑셀), `json` 중 선택. MCP 서버는 `json` 우선
  사용, 실패 시 XML 폴백 파싱 구현 (CLAUDE.md 2-2절 표준 원칙).
- **응답 최상위 구조** (예제로 실측 확인됨):
  ```
  <{SERVICE명}>
    <list_total_count>N</list_total_count>
    <RESULT><CODE>INFO-000</CODE><MESSAGE>정상 처리되었습니다</MESSAGE></RESULT>
    <row>...</row>
    <row>...</row>
    ...
  </{SERVICE명}>
  ```
  `row`가 1건이면 단일 dict, 여러 건이면 list로 파싱될 수 있음 (JSON 변환 라이브러리 특성) —
  코드에서 항상 list로 정규화하는 방어 로직 필요.
- **에러코드 체계**: INFO-000(정상), INFO-100(인증키 무효), INFO-200(데이터 없음),
  ERROR-300(필수값 누락), ERROR-301(TYPE 오류), ERROR-310(SERVICE 오류), ERROR-331~336
  (INDEX 관련), ERROR-500/600/601(서버/DB 오류). 3개 서비스 모두 동일한 에러코드 체계
  공유 (명세서로 확인됨).
- **페이징**: START_INDEX/END_INDEX 방식. 명세서상 "요청종료위치에서 요청시작위치를 뺀 값이
  1000을 넘지 않도록" 제약 있음(ERROR-336). 실제로 여러 건이 정상적으로 반환되는지는 예제로
  이미 확인됨(분야별 167건, 월별 15건 중 5건씩 반환 사례 확보) — 페이징 자체는 정상 동작하는
  것으로 판단되나, 최종 확인은 실측 단계에서 진행.

### 1-2. 서비스별 상세

#### ① SmartUncomfStatSector (분야별)
- **선택 파라미터**: YEAR(STRING), MONTH(STRING)
- **출력 필드**: YEAR, MONTH, RCPT_CNT_01(교통) ~ RCPT_CNT_12(기타 불편사항, 총 12개 분야),
  RCPT_CNT_TOTAL(총합계)
  - 분야 매핑: 01=교통, 02=도로, 03=청소, 04=주택건축, 05=치수방재, 06=가로정비, 07=보건,
    08=공원녹지, 09=환경, 10=경제/산업, 11=소방안전, 12=기타 불편사항
- **단위**: 건수(정수)

#### ② SmartUncomfStatLocale (위치별)
- **선택 파라미터**: YEAR(STRING), MONTH(STRING)
- **출력 필드**: YEAR, MONTH, GU_NM_01(종로구) ~ GU_NM_25(강동구, 서울시 25개 자치구 순),
  GU_NM_ETC(타시도)
- **단위**: 건수(정수)

#### ③ SmartUncomfStatMonth (년도/월별)
- **선택 파라미터**: YEAR(STRING) — **MONTH 파라미터 없음** (다른 2개 서비스와 차이점,
  주의 필요)
- **출력 필드**: YEAR, MON_01(1월) ~ MON_12(12월), MON_TOTAL(합계)
- **단위**: 건수(정수)
- **실측으로 이미 확인된 특이사항**: 아직 지나지 않은 달은 값이 아예 없이 빈 태그로 반환됨
  (예: 2026년 데이터에서 `<MON_08/>`처럼 self-closing 태그, 즉 JSON 변환 시 빈 문자열 또는
  null이 될 가능성). 파싱 코드에서 빈 값을 0 또는 None으로 안전하게 처리하는 로직 필수.

---

## 2. 실측 필요 항목 (Claude Code가 로컬 테스트 단계에서 반드시 확인)

1. **인증키 위치**: `?KEY=`(쿼리) vs 경로 세그먼트 방식 중 실제로 어느 쪽이 동작하는지.
   명세서 요청인자 표에는 쿼리처럼 나열되어 있으나, 서울시 API 특성상 경로 세그먼트일 가능성이
   높음 (1-1절 참고). ERROR-300 반복 시 이 부분부터 의심.
2. **선택 파라미터 부분 채움 여부**: YEAR만 넣고 MONTH는 비우는 등 조합별로 500 에러가
   나는지 확인. 특히 ③번 서비스는 MONTH 파라미터 자체가 없으므로 YEAR 단독 사용만 테스트.
3. **JSON 요청 시 필드명이 XML과 동일한지**: `TYPE=json`으로 요청했을 때 최상위 키, `row`
   배열 처리 방식이 XML과 동일한 스키마를 따르는지 확인.
4. **3개 서비스가 인증키를 공유하는지**: 하나의 SEOUL_API_KEY로 3개 서비스 모두 호출
   가능한지, 아니면 서비스별 개별 승인/키가 필요한지.
5. **MON_08처럼 빈 태그로 오는 필드의 JSON 변환 결과**: 빈 문자열(`""`)인지 `null`인지
   확인 후 툴 응답에서 0 또는 "데이터 없음"으로 정규화.

---

## 3. MCP 툴 설계 (최소 개수 원칙)

총 **3개 툴**로 설계 (서비스 1개 = 툴 1개, 축이 서로 달라 통합 시 파라미터가 과도하게
복잡해지므로 병합하지 않음):

1. `get_uncomfort_report_by_sector(year: str = None, month: str = None, start_index: int = 1, end_index: int = 20)`
   → 분야별 불편신고 건수 조회 (교통/도로/청소 등 12개 분야)
2. `get_uncomfort_report_by_district(year: str = None, month: str = None, start_index: int = 1, end_index: int = 20)`
   → 서울시 자치구별 불편신고 건수 조회
3. `get_uncomfort_report_by_month(year: str = None, start_index: int = 1, end_index: int = 20)`
   → 연도별/월별 불편신고 건수 조회 (MONTH 파라미터 없음에 유의)

각 툴 docstring에 단위(건수)와 필드 의미(자치구명, 분야명, 월)를 명시한다.

---

## 4. 기술 스택

- Python 3.11+, FastMCP, httpx, python-dotenv
- 배포: fly.io (Dockerfile, `[http_service]` 방식 fly.toml — 프로젝트 표준 템플릿 사용)
- `stateless_http=True` 필수
- Rate limit 미들웨어 3단계 적용 (API 키 없이 공개하는 서버이므로 필수)

---

## 5. 디렉토리 구조

```
seoul-uncomfort-report-mcp/
├── server.py              # FastMCP 서버, 툴 3개 정의, rate limit 미들웨어
├── seoul_api.py            # API 호출 공통 로직 (JSON 우선, XML 폴백)
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── fly.toml
├── DEVPLAN.md / CLAUDE.md / README.md / DEVLOG.md
```

---

## 6. 진행 순서

CLAUDE.md 2-4절 "작업 순서" 표준 절차를 그대로 따른다 (요구사항 정의 → 공통 API 클라이언트
→ server.py 툴 3개 → .env/.gitignore → 로컬 실측 테스트(2절의 실측 필요 항목 우선 확인)
→ FastMCP 스모크 테스트 → Dockerfile/fly.toml → 문서 갱신 → commit/push → 정지).

---

## 7. 사용자가 먼저 할 일

1. 서울 열린데이터광장(data.seoul.go.kr)에서 인증키 발급 확인
   - 3개 서비스(`SmartUncomfStatSector`, `SmartUncomfStatLocale`, `SmartUncomfStatMonth`)에
     대해 개별 활용신청이 필요한지 마이페이지에서 확인 (실측 필요 항목 4번과 연결)
2. 발급받은 키를 `.env`에 `SEOUL_API_KEY`로 저장할 준비
3. 본 문서 등 4종을 `mcp-docs` 폴더에 저장 후 부트스트랩 스크립트 실행

---

## 8. 저장소 설명(Description 제안)

> 서울시 스마트 불편신고 통계(분야별·자치구별·연월별) 조회 MCP 서버 — 서울열린데이터광장 오픈API 기반
