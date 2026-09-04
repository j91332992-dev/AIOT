#include <WiFi.h>
#include <WebServer.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <ESP32Servo.h>
#include <Adafruit_NeoPixel.h>
#include <DHT.h>
#include <HTTPClient.h>

// ==========================================
// 사용자 설정 변수 (User Configuration)
// ==========================================
const char* WIFI_SSID = "[와이파이 이름 입력]";
const char* WIFI_PASSWORD = "[와이파이 비밀번호 입력]";
String WEB_SERVER_ENDPOINT = "[데이터를 주고받을 웹 서버 주소/IP 입력]";

// ==========================================
// 핀 맵 (Pin Map)
// ==========================================
const int SERVO_PIN = 18;
const int SENSOR_PIN = 5;
const int BUZZER_PIN = 19;
const int NEOPIXEL_PIN = 14;
const int DHT_PIN = 4;

// ==========================================
// 전역 객체 및 변수
// ==========================================
#define NUMPIXELS 4 // 네오픽셀 LED 개수 (예: 4구)
Adafruit_NeoPixel pixels(NUMPIXELS, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);
DHT dht(DHT_PIN, DHT11);
Servo myServo;
WebServer server(80);
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", 32400, 60000); // KST (+9시간)

int currentAngle = 0;

// 복약 상태 변수
bool morningTaken = false;
bool lunchTaken = false;
bool dinnerTaken = false;

// 알람 1회 재생 플래그
bool morningAlarmPlayed = false;
bool lunchAlarmPlayed = false;
bool dinnerAlarmPlayed = false;

// 부저 비동기 처리를 위한 타이머 변수
unsigned long buzzerEndTime = 0;

// ==========================================
// 유틸리티 함수
// ==========================================

// HTTP 로그 전송 함수
void sendLog(String message) {
  Serial.println("[LOG] " + message);
  if (WEB_SERVER_ENDPOINT.indexOf("http") == -1) return; // 주소가 설정되지 않은 경우 스킵
  
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(WEB_SERVER_ENDPOINT);
    http.addHeader("Content-Type", "application/json");
    
    // 온도/습도 데이터 포함
    float t = dht.readTemperature();
    float h = dht.readHumidity();
    
    String payload = "{\"message\":\"" + message + "\", \"temperature\":" + String(t) + ", \"humidity\":" + String(h) + "}";
    int httpResponseCode = http.POST(payload);
    
    if (httpResponseCode > 0) {
      Serial.println("HTTP POST 발송 완료: " + String(httpResponseCode));
    } else {
      Serial.println("HTTP POST 발송 실패: " + http.errorToString(httpResponseCode).c_str());
    }
    http.end();
  }
}

// 네오픽셀 제어 함수
void setNeopixel(uint8_t r, uint8_t g, uint8_t b) {
  for(int i=0; i<NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(r, g, b));
  }
  pixels.show();
}

// 비동기 부저 켜기
void startBuzzer(unsigned long durationMs) {
  tone(BUZZER_PIN, 1000); // 1kHz 소리
  buzzerEndTime = millis() + durationMs;
}

// 누적 복약량 계산 함수
int getPendingPills(int hour) {
  int pending = 0;
  if (hour >= 7 && hour < 24) { // 아침(7시) 이후
    if (!morningTaken) pending++;
  }
  if (hour >= 11 && hour < 24) { // 점심(11시) 이후
    if (!lunchTaken) pending++;
  }
  if (hour >= 15 && hour < 24) { // 저녁(15시) 이후
    if (!dinnerTaken) pending++;
  }
  return pending;
}

// 복약 상태 업데이트 함수
void updateTakenStatus(int hour) {
  if (hour >= 7) morningTaken = true;
  if (hour >= 11) lunchTaken = true;
  if (hour >= 15) dinnerTaken = true;
}

// 서보모터 배출 함수
void dispensePills(int count) {
  for (int i = 0; i < count; i++) {
    currentAngle += 30; // 1회당 30도 회전
    
    if (currentAngle > 180) {
      // 180도를 넘어가면 빈 카트리지이므로 0도로 원복
      Serial.println("디스펜서 리필 필요! 카트리지를 원복합니다.");
      currentAngle = 0;
      myServo.write(currentAngle);
      delay(1000);
      sendLog("약통이 비었습니다. 리필해 주세요.");
      return; 
    }
    
    myServo.write(currentAngle);
    delay(1000); // 30도 회전 후 잠시 대기
  }
}

// ==========================================
// 웹서버 라우팅 처리
// ==========================================
void handleGesture() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  if (!server.hasArg("action")) {
    server.send(400, "text/plain", "Bad Request");
    return;
  }
  
  String action = server.arg("action");
  Serial.println("웹캠 제스처 수신: " + action);
  
  if (action == "fist") {
    // 주먹 쥐기: 무드등 끄기
    setNeopixel(0, 0, 0);
    server.send(200, "text/plain", "Neopixel OFF");
  } 
  else if (action == "open") {
    // 손 펴기: 무드등 켜기 (따뜻한 노란/주황 빛)
    setNeopixel(255, 150, 50); 
    server.send(200, "text/plain", "Neopixel ON");
  } 
  else if (action == "cross") {
    // X자 만들기: 긴급 알림
    setNeopixel(255, 0, 0); // 붉은색 경고
    startBuzzer(5000); // 5초간 부저
    sendLog("🚨 위급 상황 발생! (X자 모션 감지)");
    server.send(200, "text/plain", "Emergency Alert Sent");
  } 
  else {
    server.send(400, "text/plain", "Unknown action");
  }
}

// ==========================================
// Setup 및 Loop
// ==========================================
void setup() {
  Serial.begin(115200);
  
  // 핀 모드 초기화
  pinMode(SENSOR_PIN, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);
  
  // 컴포넌트 초기화
  pixels.begin();
  setNeopixel(0, 0, 0); // 초기 끄기
  dht.begin();
  
  // ESP32Servo 라이브러리 사용 시, PWM 할당
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  myServo.setPeriodHertz(50); // 표준 50Hz 서보모터
  myServo.attach(SERVO_PIN, 500, 2400); // 서보핀 및 펄스폭 설정
  myServo.write(0); // 서보 초기 각도 0도
  
  // 와이파이 연결
  Serial.print("WiFi 연결 중: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi 연결 성공!");
  Serial.print("IP 주소: ");
  Serial.println(WiFi.localIP());
  
  // NTP 시작
  timeClient.begin();
  
  // 웹서버 라우팅
  server.on("/gesture", HTTP_GET, handleGesture);
  server.begin();
  Serial.println("HTTP 서버 시작 완료");
}

void loop() {
  server.handleClient();
  timeClient.update();
  
  int h = timeClient.getHours();
  int m = timeClient.getMinutes();
  int s = timeClient.getSeconds();
  
  // 1. 비동기 부저 끄기 처리
  if (millis() > buzzerEndTime && buzzerEndTime > 0) {
    noTone(BUZZER_PIN);
    buzzerEndTime = 0;
  }
  
  // 2. 자정(00:00) 초기화
  if (h == 0 && m == 0 && s == 0) {
    morningTaken = false;
    lunchTaken = false;
    dinnerTaken = false;
    morningAlarmPlayed = false;
    lunchAlarmPlayed = false;
    dinnerAlarmPlayed = false;
    // 하루가 지나면 서보모터 0도로 리셋
    if (currentAngle > 0) {
      currentAngle = 0;
      myServo.write(0);
    }
    delay(1000); // 1초 대기하여 중복 실행 방지
  }
  
  // 3. 시간대별 배출 시작 알림 로직 (시작 시간에 3초간 부저)
  if (h == 7 && m == 0 && !morningAlarmPlayed) {
    startBuzzer(3000); sendLog("아침 약 복용 시간입니다."); morningAlarmPlayed = true;
  }
  if (h == 11 && m == 0 && !lunchAlarmPlayed) {
    startBuzzer(3000); sendLog("점심 약 복용 시간입니다."); lunchAlarmPlayed = true;
  }
  if (h == 15 && m == 0 && !dinnerAlarmPlayed) {
    startBuzzer(3000); sendLog("저녁 약 복용 시간입니다."); dinnerAlarmPlayed = true;
  }
  
  // 4. 미복용 경고 로직 (마감 30분 전)
  if (s == 0) { // 1분 주기로 검사
    if (h == 9 && m >= 30 && !morningTaken) {
      startBuzzer(1000); sendLog("아침 약 복용 마감 30분 전입니다!"); 
      delay(1000); // 중복 방지
    }
    else if (h == 12 && m >= 30 && !lunchTaken) {
      startBuzzer(1000); sendLog("점심 약 복용 마감 30분 전입니다!");
      delay(1000);
    }
    else if (h == 16 && m >= 30 && !dinnerTaken) {
      startBuzzer(1000); sendLog("저녁 약 복용 마감 30분 전입니다!");
      delay(1000);
    }
  }
  
  // 5. 손 인식 (IR 센서) 복약 로직
  // LOW일 때 물체가 감지된 것으로 가정 (센서 타입에 따라 변경 가능)
  if (digitalRead(SENSOR_PIN) == LOW) {
    delay(200); // 디바운스
    if (digitalRead(SENSOR_PIN) == LOW) {
      int pending = getPendingPills(h);
      if (pending > 0) {
        Serial.print("누적 복약 횟수 감지: "); Serial.println(pending);
        startBuzzer(500); // 인식 알림음
        dispensePills(pending);
        updateTakenStatus(h);
        sendLog("복용 완료 (누적 횟수: " + String(pending) + ")");
      } else {
        // 이미 약을 다 먹은 상태이거나 복약 시간대가 아님
        Serial.println("복약 대기 중인 약이 없습니다.");
      }
      
      // 손이 계속 감지되어 중복 배출되는 것 방지
      while(digitalRead(SENSOR_PIN) == LOW) {
        delay(100);
        server.handleClient(); // 대기 중에도 웹 API 수신은 처리
      }
    }
  }
  
  delay(10); // 안정화
}
