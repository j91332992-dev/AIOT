from machine import Pin
from servo import Servo
from time import sleep

# 스마트홈 회로 연결에 따라 서보 모터가 D13 (GPIO 13) 핀에 연결되어 있습니다.
motor = Servo(pin=13)

print("=== SG90 서보 모터 테스트 시작 ===")
print("동작 순서: 0도 -> 90도 -> 180도 -> 90도 -> 루프")

try:
    while True:
        print("-> 0도로 이동")
        motor.move(0)
        sleep(2)
        
        print("-> 90도로 이동 (중간)")
        motor.move(45)
        sleep(2)
        
        print("-> 180도로 이동")
        motor.move(90)
        sleep(2)
        
        print("-> 90도로 이동 (복귀)")
        motor.move(135)
        sleep(2)

except KeyboardInterrupt:
    print("=== 테스트 종료 (Ctrl+C 감지) ===")
