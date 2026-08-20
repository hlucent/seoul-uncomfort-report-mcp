# seoul-uncomfort-report-mcp

서울시 스마트 불편신고 통계 3종(분야별 / 자치구별 / 연월별)을 조회하는 MCP 서버입니다.
서울열린데이터광장(data.seoul.go.kr) 오픈API를 기반으로 합니다.

## 제공 툴

### 1. `get_uncomfort_report_by_sector`
분야별(교통, 도로, 청소, 주택건축, 치수방재, 가로정비, 보건, 공원녹지, 환경, 경제/산업,
소방안전, 기타 불편사항) 불편신고 건수를 조회합니다. 단위: 건수.

파라미터: `year`(선택), `month`(선택), `start_index`(기본 1), `end_index`(기본 20)

### 2. `get_uncomfort_report_by_district`
서울시 25개 자치구 + 타시도 기준 불편신고 건수를 조회합니다. 단위: 건수.

파라미터: `year`(선택), `month`(선택), `start_index`(기본 1), `end_index`(기본 20)

### 3. `get_uncomfort_report_by_month`
연도별 1~12월 불편신고 건수와 연간 합계를 조회합니다. 단위: 건수.
**주의**: 이 서비스는 월(MONTH) 파라미터가 없습니다 — 연도 전체 데이터만 조회 가능합니다.
아직 지나지 않은 달은 데이터가 비어 있습니다(예: 조회 시점이 2026년 7월이면 8~12월은 값 없음).

파라미터: `year`(선택), `start_index`(기본 1), `end_index`(기본 20)

## 설치 및 실행 (로컬)

```bash
pip install -r requirements.txt
cp .env.example .env  # SEOUL_API_KEY 입력
python server.py
```

## 환경변수

| 변수명 | 설명 |
|---|---|
| `SEOUL_API_KEY` | 서울열린데이터광장에서 발급받은 인증키 |
| `PORT` | 서버 포트 (기본 8000) |

## 배포

fly.io 배포 방식은 `CLAUDE.md`, 프로젝트 공통 지침을 따릅니다.
배포 완료 후 Claude.ai 커넥터 연결 시 URL 끝에 `/mcp`를 붙여야 합니다.
예: `https://seoul-uncomfort-report-mcp.fly.dev/mcp`

## 데이터 출처 및 라이선스

- 제공기관: 서울특별시
- 제공부서: 디지털도시국 공간정보과
- 원본시스템: 서울시 스마트 불편신고
- 이용허락범위: 공공누리 1유형 (출처표시, 상업적 이용 및 변경 가능)

## 알려진 제약사항 (실측 기반, 향후 갱신)

- 인증키는 URL 경로 세그먼트 방식으로 전달됩니다 (실측 확인 후 본 항목 갱신 예정).
- API 응답에서 결과가 1건일 때와 여러 건일 때 JSON 구조가 다를 수 있어 서버 내부에서
  항상 리스트로 정규화합니다.
- 이 서버는 API 키 인증 없이 공개되며, IP 기준 rate limit이 적용됩니다
  (분당 3회, 1시간 내 5회 위반 시 24시간 차단, 24시간 총 30회 — 멀티 머신 배포 시
  머신 수에 비례해 실질 완화될 수 있음).

## 라이선스

MIT
