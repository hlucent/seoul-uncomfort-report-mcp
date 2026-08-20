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

## (다음 항목 — Claude Code가 작업 시작 시 추가)

- [ ] 로컬 실측 테스트 결과
- [ ] 배포 결과 및 커넥터 연결 확인
