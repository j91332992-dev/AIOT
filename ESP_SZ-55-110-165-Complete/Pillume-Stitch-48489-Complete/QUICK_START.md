# Pillume 빠른 실행

## 1. ESP32 실행

1. ESP32에 MicroPython을 설치합니다.
2. 이 폴더의 `main.py`를 ESP32 내부의 `main.py`로 복사합니다.
3. ESP32를 재부팅합니다.
4. Thonny Shell에서 `[BLE] advertising as ESP_SZ`가 보이는지 확인합니다.

자세한 하드웨어 결선과 설치 순서는 `A_TO_Z_GUIDE.md`를 참고하세요.

## 2. 대시보드 실행

Windows에서는 `START_PILLUME.bat`을 더블클릭하면 서버와 대시보드가 함께
실행됩니다. 브라우저 주소는 아래와 같습니다.

`http://localhost:3000/dashboard.html`

처음 실행할 때만 인터넷 연결이 필요하며 `npm install`이 자동으로 진행됩니다.
수동 실행을 원하면 이 폴더에서 아래 명령을 사용합니다.

```powershell
npm install
npm run dev
```

## 3. ESP32 연결

1. PC의 Bluetooth를 켭니다.
2. Chrome 또는 Edge로 대시보드를 엽니다.
3. 오른쪽 위 `ESP_SZ 연결` 버튼을 누릅니다.
4. 장치 목록에서 `ESP_SZ`를 선택합니다.

Web Bluetooth는 `localhost` 또는 HTTPS에서만 동작합니다.

## 4. Teachable Machine

대시보드의 카메라 메뉴에서 모델 URL을 입력합니다.

- 클래스 1: 무드등 켜기
- 클래스 2: 무드등 끄기
- 클래스 3: 긴급상황

긴급상황은 화면의 `확인했습니다` 버튼을 누를 때까지 빨간 네오픽셀과
피에조 사이렌이 계속 작동합니다.

## 5. AI 챗봇

AI 챗봇을 처음 열면 OpenAI API 키를 직접 입력합니다. API 키는 소스 파일에
포함되지 않으며 브라우저 세션에서만 사용됩니다. GitHub에 API 키를 올리지
마세요. 공개 배포 시에는 서버 환경 변수 방식으로 전환하는 것을 권장합니다.

## 6. 안전한 TEST MODE

대시보드 왼쪽 위의 `TEST` 버튼을 누르면 격리된 튜토리얼 모드가 열립니다.

- 아침·점심·저녁 가상 시간대로 즉시 이동
- 복약 시간 시작, 복용 완료, 마감 30분 전 미복용 경고
- 밀린 약 누적 배출, 무드등, 알약 채우기, 긴급상황 흐름 확인
- BLE 연결 시 서보·네오픽셀·피에조·OLED 실제 작동
- 실제 복약 기록, NVS, 설정 저장, AI API 요청은 격리
- 테스트 종료 시 시작 직전 화면과 하드웨어 상태로 복원

테스트 전에는 디스펜서에서 실제 알약을 빼고 회전부에서 손을 치워 주세요.
BLE가 연결되지 않은 경우에는 화면 안내만 동작합니다.

## 주요 파일

- `dashboard.html`: Stitch 화면 기반 완성 대시보드
- `public/dashboard.html`: 서버가 제공하는 대시보드 사본
- `main.py`: ESP32 MicroPython 펌웨어
- `app/api/assistant/route.ts`: AI 챗봇 서버 API
- `START_PILLUME.bat`: 서버와 대시보드 통합 실행
- `A_TO_Z_GUIDE.md`: 하드웨어부터 소프트웨어까지 전체 안내
- `README.md`: 기능 및 명령 상세 설명
