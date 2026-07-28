# ESP_SZ MicroPython 설치

이 폴더의 버전은 Arduino IDE와 `.ino` 파일을 사용하지 않습니다.
MicroPython 펌웨어 자체에 포함된 `bluetooth`, `machine`, `neopixel`,
`ujson`, `esp32` 모듈만 사용하므로 별도 라이브러리 설치가 필요 없습니다.
BLE 클래스도 `main.py` 안에 포함되어 있어 파일 하나만 복사하면 됩니다.

## 필요한 파일

ESP32 내부 최상위 경로에 다음 파일 하나만 복사합니다.

```text
/
└─ main.py
```

## Thonny로 설치

1. ESP32용 MicroPython 펌웨어를 공식 다운로드 페이지에서 받습니다.
2. Thonny를 설치하고 ESP32를 USB로 연결합니다.
3. Thonny 오른쪽 아래 인터프리터 메뉴에서
   `MicroPython (ESP32)`를 선택합니다.
4. 펌웨어가 없다면 인터프리터 설정의
   `Install or update MicroPython`으로 먼저 설치합니다.
5. 기존 `ble_library.py`가 보드에 있으면 삭제합니다.
6. `main.py`를 열고 `File → Save as → MicroPython device`를 선택해
   보드 최상위에 `main.py`로 저장합니다.
7. ESP32의 EN/RESET 버튼을 누르거나 전원을 껐다 켭니다.

정상 실행 시 Shell에 다음 메시지가 보입니다.

```text
[BLE] advertising as ESP_SZ
[SYSTEM] ESP_SZ MicroPython firmware ready
```

이제 Chrome/Edge 대시보드에서 `ESP_SZ 연결`을 누르면 됩니다.

## AI 도우미 사용

`dashboard.html` 오른쪽 아래의 `AI 도우미`를 누르면 먼저 OpenAI API 키
입력 화면이 표시됩니다. 반드시 새로 발급한 키를 사용하세요. 입력한 키는
현재 브라우저 탭의 메모리에만 유지되고 HTML 파일이나 로컬 저장소에는
저장되지 않으며, 새로고침하면 사라집니다.

AI 호출은 보안을 위해 로컬 서버가 대신 전달합니다. 프로젝트 전체 소스
폴더에서 아래 명령을 실행한 뒤 `http://localhost:3000`으로 접속하세요.

```powershell
npm install
npm run dev
```

AI는 사용법과 오류 해결을 안내하며, 누락된 복약 완료 기록은 사용자가
`확인하고 기록`을 누른 뒤에만 저장합니다. BLE, 서보, LED, 긴급 경보,
모델 설정은 AI가 직접 변경할 수 없습니다.

현재 동작:

- IR 센서에 손이 약 1초 연속 감지되면 배출
- 서보 위치: 55도 → 110도 → 165도 → 30초 후 0도
- 서보 이동 중 WS2812B 파란색 체이스
- 웹에서 WS2812B 색상과 밝기 1–100% 조절
- SSD1306 OLED: SDA GPIO 21, SCL GPIO 22, I2C 주소 0x3C
- 복약 시간에는 `MEDICINE TIME`, 미복용 알림 때는
  `PLEASE TAKE YOUR MEDICINE` 표시
- 긴급 동작 시 웹의 `확인했습니다`를 누를 때까지 빨간 점멸과 사이렌 유지
- 알약 채우기 버튼을 누를 때마다 55도 → 110도 → 165도 → 0도 이동
- 채우기 모드에서는 IR 자동 배출 잠금

웹에서 전송하는 무드등 명령 형식:

```json
{"type":"light","color":"#7C4DFF","brightness":65,"on":true}
```

색상과 밝기는 일반 무드등에 적용됩니다. 서보 작동 중 파란 체이스와
긴급상황의 빨간 점멸은 안전 알림이므로 우선합니다. 긴급 팝업의
`확인했습니다`를 누르면 웹이 `{"type":"emergency_ack"}`를 전송하고,
ESP32가 사이렌과 점멸을 종료한 뒤 지정한 무드등 설정으로 돌아옵니다.

## 중요

- MicroPython을 설치하면 기존 Arduino 스케치는 지워집니다.
- 다시 Arduino 방식으로 돌아가려면 Arduino IDE에서 스케치를 업로드하면
  됩니다.
- 예전 `ble_library.py`는 사용하지 않으므로 삭제해도 됩니다.
- OLED 드라이버도 `main.py`에 포함되어 있으므로 `ssd1306.py`는 필요 없습니다.
- OLED가 연결되지 않아도 나머지 기능은 계속 작동합니다.
- 피에조는 연결하지 않아도 다른 기능에 영향이 없습니다.
