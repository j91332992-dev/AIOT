# 🏠 AIoT 프로젝트 통합 가이드 및 정리 문서 (README)

이 워크스페이스는 **스마트홈(Smart Home)** 관련 프로젝트와 **필룸(Pillume) 스마트 디스펜서** 관련 프로젝트로 구성되어 있습니다. 각 프로젝트의 개요, 구성 파일, 센서 정보, 그리고 작동 목표를 정리한 문서입니다.

---

## 1. 스마트홈 프로젝트 (Smart Home & Smart Lamp)

### 📌 개요 및 목표
ESP32와 웹 브라우저를 NUS(Nordic UART Service) 저전력 블루투스(BLE)로 연결하여, 실내 환경(온도, 습도, 밝기)을 실시간으로 모니터링하고 스마트 램프(RGB LED)와 블라인드(서보 모터) 등을 원격 제어하는 스마트홈 교육용 템플릿입니다.

### 📂 구성 파일
- **메인 소스코드**: [smartHome.py](file:///c:/Users/hpo20/AIoT%20-%20antigravity/s_SmartHome/smartHome.py) (ESP32 MicroPython 동작 펌웨어)
- **웹 대시보드**: [index.html](file:///c:/Users/hpo20/AIoT%20-%20antigravity/s_SmartHome/index.html) (환경 정보 표시 및 블루투스 NUS 제어 웹 UI)
- **발표 및 디자인 문서**: 
  - [Design.md](file:///c:/Users/hpo20/AIoT%20-%20antigravity/s_SmartHome/Design.md) & [PRD_s.md](file:///c:/Users/hpo20/AIoT%20-%20antigravity/s_SmartHome/PRD_s.md) (요구사항 및 디자인 계획)
  - [PPT_Draft.md](file:///c:/Users/hpo20/AIoT%20-%20antigravity/s_SmartHome/PPT_Draft.md) & [generate_ppt.py](file:///c:/Users/hpo20/AIoT%20-%20antigravity/s_SmartHome/generate_ppt.py) (PPT 자동 생성 및 초안)
- **보조 문서**: [student_web_dashboard_guide.md](file:///c:/Users/hpo20/AIoT%20-%20antigravity/s_SmartHome/student_web_dashboard_guide.md) (학생용 제작 가이드) & [스마트홈_회로연결.txt](file:///c:/Users/hpo20/AIoT%20-%20antigravity/s_SmartHome/%EC%8A%A4%EB%A7%88%ED%8A%B8%ED%99%88_%ED%9A%8C%EB%A1%9C%EC%20%EC%97%B0%EA%B2%B0.txt) (ESP32 핀 정보)
- **백업 파일**: `archives/s_SmartHome.zip` (초기 프로젝트 원본 백업)

### 🔌 사용 센서 및 액추에이터
- **DHT11 온습도 센서** (GPIO 14): 실내 온도 및 습도 측정
- **LDR 조도 센서** (GPIO 36): 주변 밝기(빛 세기) 측정
- **정전식 터치 센서 (4개)** (GPIO 17, 5, 18, 19): 버튼 입력을 대신하는 터치 이벤트 감지
- **SG90 서보 모터** (GPIO 13): 창문 또는 스마트 블라인드 여닫이 구동
- **RGB LED** (GPIO 25, 26, 27): 스마트 램프의 3색 조명 제어
- **I2C LCD 16x2** (SDA 21, SCL 22, 주소 0x27): 온도, 습도 값을 화면에 직접 표시
- **OLED 디스플레이 (SSD1306)** (SDA 21, SCL 22, 주소 0x3C): 대기 화면 캐릭터([pochacca.pbm](file:///c:/Users/hpo20/AIoT%20-%20antigravity/s_SmartHome/img/pochacca.pbm)) 출력
- **피에조 부저** (GPIO 23): 블라인드 작동 시 알림음 멜로디 출력

---

## 2. 필룸 스마트 알약 디스펜서 프로젝트 (Pillume Smart Dispenser)

### 📌 개요 및 목표
스마트 헬스케어 장비인 알약 배출기(Dispenser)의 구동 프로젝트입니다. 웹 대시보드와 BLE로 연결하여 시간을 동기화하고, 정해진 시간(아침, 점심, 저녁)에 서보 모터를 구동하여 알약을 배출합니다. 또한 미복용 시 LED 경고 및 부저 사이렌을 울리며, 웹캠 비디오 기반 **Teachable Machine 이미지/동작 분류** 기능을 연동하여 손동작 제스처로 무드등을 켜고 끌 수 있는 고급 융합 AIoT 프로젝트입니다.

### 📂 구성 파일
- **메인 소스코드 (MicroPython)**: [main.py](file:///c:/Users/hpo20/AIoT%20-%20antigravity/Pillume-Stitch-48489-Complete/micropython/main.py) (ESP32 디스펜서 구동 메인)
- **보조 펌웨어 (Arduino)**: [SmartDispenser.ino](file:///c:/Users/hpo20/AIoT%20-%20antigravity/Pillume-Stitch-48489-Complete/firmware/SmartDispenser.ino) (WiFi/웹 서버 통신 방식의 아두이노 스케치)
- **디자인 요구사항 (PRD)**: [Pillume_Dashboard_PRD_Stitch.md](file:///c:/Users/hpo20/AIoT%20-%20antigravity/Pillume-Stitch-48489-Complete/docs/Pillume_Dashboard_PRD_Stitch.md) (디자인 개선용 명세서)
- **웹 대시보드**: 
  - [dashboard_base.html](file:///c:/Users/hpo20/AIoT%20-%20antigravity/Pillume-Stitch-48489-Complete/web-standalone/dashboard_base.html) (블루투스로 연결하는 기본형 HTML 대시보드)
  - `Pillume-Stitch-48489-Complete/app/` (Next.js 기반의 다기능 복약 관리 시스템 대시보드 웹 앱)
- **동작인식 카메라 컨트롤러 (Teachable Machine)**:
  - `t_TeachableMachine/` 폴더 내 파일 ([index.html](file:///c:/Users/hpo20/AIoT%20-%20antigravity/t_TeachableMachine/index.html), [app.js](file:///c:/Users/hpo20/AIoT%20-%20antigravity/t_TeachableMachine/app.js), [index.css](file:///c:/Users/hpo20/AIoT%20-%20antigravity/t_TeachableMachine/index.css), [PRD.md](file:///c:/Users/hpo20/AIoT%20-%20antigravity/t_TeachableMachine/PRD.md))
  - 웹캠 영상을 통해 학습시킨 Teachable Machine 모델을 실행하고 판정 결과를 Web BLE를 통해 ESP32로 전송하는 독립 기능 웹 앱.

### 🔌 사용 센서 및 액추에이터
- **SG90 서보 모터** (GPIO 13): 3회전식(55도 → 110도 → 165도) 알약 통 회전 제어
- **IR 적외선 장애물 감지 센서** (GPIO 27): 배출구 아래 손을 감지하여 1초 이상 머물면 알약 배출 트리거
- **WS2812B 네오픽셀 LED 스트립** (GPIO 18): 알약 배출 시 조명 체이싱 효과 및 동작 제스처에 따른 무드등(밝기/색상 제어)
- **피에조 부저** (GPIO 23): 약을 제때 복용하지 않았을 때 경고음(긴급 사이렌) 송출
- **OLED 디스플레이 (SSD1306)** (SDA 21, SCL 22): 현재 시간대 정보, 복약 상태 안내(영어)
- **웹캠 및 브라우저 (Teachable Machine)**: ml5.js 기반 인공지능 이미지 인식을 통해 제스처 판별 및 LED 원격 제어
- **BLE (저전력 블루투스)** (장치명 `ESP_SZ`): 시간 동기화 및 원격 제어용 무선 통신
