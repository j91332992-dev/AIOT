# Design QA — Stitch screen 48489

## Target

- Stitch project: `11037894770739194384`
- Stitch screen: `48489c9463d94f0a812844956c626fda`
- Implementation: `dashboard.html`
- Desktop preview viewport: 1280 × 1024 CSS px

## Fidelity checks

- Typography: Stitch의 `Inter`, 상단 `text-3xl`(30px), 700 weight를 적용했습니다.
- Color: 배경 `#f4f7f6`, 강조색 `#1677d2`, 카드 `#ffffff`,
  본문 `#252525`, 보조 텍스트 `#757575`를 적용했습니다.
- Layout: 콘텐츠 최대 폭 1024px, 7:5 메인 그리드, 24px 간격,
  24px 카드 반경을 적용했습니다.
- Structure: 복약 일정, 무드등/밀린 복약 상태 타일, 알약 채우기,
  최근 활동, 원형 AI 챗봇 런처 구조를 유지했습니다.
- Copy: `안녕하세요!`, `오늘의 복약을 도와드릴게요.`, `복약 일정`,
  `알약 채우기`, `최근 활동`을 Stitch 화면과 맞췄습니다.

## Functional checks

- BLE 연결 버튼 및 `ESP_SZ` 명령 처리
- Teachable Machine 카메라/모델 설정
- 무드등 ON/OFF, 색상, 밝기, 긴급상황
- 긴급상황 확인 전까지 경보 유지
- 알약 채우기 55 → 110 → 165 → 0도
- 최근 로그 기본 3개 및 더보기
- 캘린더 복약 기록
- AI 챗봇 API 및 수동 복약 기록 확인 단계
- TEST 아이콘 진입 및 아침·점심·저녁 가상 시간 이동
- 미복용 경고·누적 배출·무드등·채우기·긴급상황 시뮬레이션
- TEST 종료 후 상태·기록·버튼 활성 상태 복원
- TEST 중 BLE 쓰기·localStorage·AI API 요청 격리

## Runtime verification

- Production build: PASS
- `GET /dashboard.html`: 200
- `GET /api/health`: 200
- `OPTIONS /api/assistant`: 204
- Browser TEST flow: PASS
- Dashboard and firmware duplicate hashes: MATCH
- Secret scan: PASS

## Responsive and accessibility checks

- 900px 이하에서 1열 레이아웃으로 전환
- 620px 이하에서 헤더와 버튼을 모바일 크기로 조정
- 버튼/입력에 focus-visible 표시
- 의미 있는 버튼 요소와 ARIA 레이블 유지
- reduced-motion 환경에서 과도한 애니메이션을 비활성화

## Findings

최종 패스에서 P0, P1, P2 수준의 디자인 또는 기능 오류는 발견되지
않았습니다. 인앱 브라우저 캡처 백엔드의 가로 DPR 출력 제한으로 전체
데스크톱 이미지는 한 장에 담기지 않았지만, 좌측 영역의 시각 비교와 전체
DOM 치수 측정으로 1024px 셸, 7:5 그리드, 카드 위치를 확인했습니다.
