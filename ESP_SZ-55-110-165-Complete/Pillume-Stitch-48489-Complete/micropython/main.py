"""Pillume ESP_SZ — MicroPython firmware for ESP32.

Hardware:
  SG90 signal       GPIO 13
  IR digital OUT    GPIO 27 (active LOW)
  Passive buzzer    GPIO 23 (optional)
  WS2812B DIN       GPIO 18
  SSD1306 OLED SDA  GPIO 21
  SSD1306 OLED SCL  GPIO 22

No Wi-Fi, NTP, DHT, or third-party MicroPython package is required.
"""

import bluetooth
import framebuf
import machine
import neopixel
import time
import ujson
from micropython import const

try:
    import esp32
except ImportError:
    esp32 = None


# ---------------------------------------------------------------------------
# Built-in BLE peripheral helper
# ---------------------------------------------------------------------------
#
# This class is included directly in main.py so an old ble_library.py stored on
# the ESP32 cannot be imported accidentally. No additional Python file is
# required.

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

BLE_SERVICE_UUID = bluetooth.UUID("7c8e4001-9f8b-4f44-a18f-64a6f6a50101")
BLE_COMMAND_UUID = bluetooth.UUID("7c8e4002-9f8b-4f44-a18f-64a6f6a50101")
BLE_STATUS_UUID = bluetooth.UUID("7c8e4003-9f8b-4f44-a18f-64a6f6a50101")
BLE_EVENT_UUID = bluetooth.UUID("7c8e4004-9f8b-4f44-a18f-64a6f6a50101")

_BLE_SERVICE = (
    BLE_SERVICE_UUID,
    (
        (
            BLE_COMMAND_UUID,
            _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,
        ),
        (
            BLE_STATUS_UUID,
            _FLAG_READ | _FLAG_NOTIFY,
        ),
        (
            BLE_EVENT_UUID,
            _FLAG_READ | _FLAG_NOTIFY,
        ),
    ),
)


def _append_advertising_field(payload, field_type, value):
    payload += bytes((len(value) + 1, field_type)) + value


def _advertising_payload(name, service_uuid):
    payload = bytearray()
    _append_advertising_field(payload, 0x01, b"\x06")
    _append_advertising_field(payload, 0x07, bytes(service_uuid))
    _append_advertising_field(payload, 0x09, name.encode())
    return payload


class BLESimplePeripheral:
    def __init__(self, ble, name="ESP_SZ"):
        self._ble = ble
        self._name = name
        self._connections = set()
        self._write_callback = None

        self._ble.active(True)
        try:
            self._ble.config(mtu=247)
        except (ValueError, OSError):
            pass

        self._ble.irq(self._irq)
        (
            self._command_handle,
            self._status_handle,
            self._event_handle,
        ) = self._ble.gatts_register_services((_BLE_SERVICE,))[0]

        # MicroPython's default GATT value buffer is only 20 bytes.
        self._ble.gatts_set_buffer(self._command_handle, 1024, False)
        self._ble.gatts_set_buffer(self._status_handle, 1024, False)
        self._ble.gatts_set_buffer(self._event_handle, 1024, False)

        self._payload = _advertising_payload(name, BLE_SERVICE_UUID)
        self._advertise()

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            print("[BLE] connected", conn_handle)

        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.discard(conn_handle)
            print("[BLE] disconnected", conn_handle)
            self._advertise()

        elif event == _IRQ_GATTS_WRITE:
            _, value_handle = data
            if value_handle != self._command_handle:
                return
            value = bytes(self._ble.gatts_read(self._command_handle))
            if self._write_callback:
                try:
                    self._write_callback(value)
                except Exception as error:
                    print("[BLE] command error:", error)

    def _advertise(self, interval_us=100000):
        self._ble.gap_advertise(
            interval_us,
            adv_data=self._payload,
            connectable=True,
        )
        print("[BLE] advertising as", self._name)

    def on_write(self, callback):
        self._write_callback = callback

    def is_connected(self):
        return bool(self._connections)

    def _write_and_notify(self, value_handle, value):
        if isinstance(value, str):
            value = value.encode()
        self._ble.gatts_write(value_handle, value)
        for conn_handle in tuple(self._connections):
            try:
                self._ble.gatts_notify(conn_handle, value_handle, value)
            except OSError as error:
                print("[BLE] notify failed:", error)

    def send_status(self, value):
        self._write_and_notify(self._status_handle, value)

    def send_event(self, value):
        self._write_and_notify(self._event_handle, value)


# ---------------------------------------------------------------------------
# Built-in SSD1306 I2C OLED driver
# ---------------------------------------------------------------------------
#
# Keeping this small driver in main.py means no separate ssd1306.py file is
# required on the ESP32.

class SSD1306_I2C:
    def __init__(self, width, height, i2c, address=0x3C):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.address = address
        self.buffer = bytearray(self.height * self.width // 8)
        self.framebuf = framebuf.FrameBuffer(
            self.buffer,
            self.width,
            self.height,
            framebuf.MONO_VLSB,
        )
        self._init_display()

    def _write_cmd(self, command):
        self.i2c.writeto(self.address, bytes((0x80, command)))

    def _init_display(self):
        commands = (
            0xAE,       # Display off
            0x20, 0x00, # Horizontal addressing mode
            0x40,       # Start line 0
            0xA1,       # Segment remap
            0xA8, self.height - 1,
            0xC8,       # COM output direction
            0xD3, 0x00, # Display offset
            0xDA, 0x12 if self.height == 64 else 0x02,
            0xD5, 0x80, # Display clock
            0xD9, 0xF1, # Pre-charge
            0xDB, 0x30, # VCOM deselect
            0x81, 0xCF, # Contrast
            0xA4,       # Entire display follows RAM
            0xA6,       # Normal display
            0x8D, 0x14, # Charge pump on
            0xAF,       # Display on
        )
        for command in commands:
            self._write_cmd(command)
        self.fill(0)
        self.show()

    def fill(self, color):
        self.framebuf.fill(color)

    def text(self, text, x, y, color=1):
        self.framebuf.text(text, x, y, color)

    def show(self):
        self._write_cmd(0x21)
        self._write_cmd(0)
        self._write_cmd(self.width - 1)
        self._write_cmd(0x22)
        self._write_cmd(0)
        self._write_cmd(self.height // 8 - 1)
        self.i2c.writevto(self.address, (b"\x40", self.buffer))


# ---------------------------------------------------------------------------
# Project settings
# ---------------------------------------------------------------------------

BLE_DEVICE_NAME = "ESP_SZ"
DEVICE_ID = "esp32-pill-01"

SERVO_PIN = 13
PROXIMITY_PIN = 27
BUZZER_PIN = 23
NEOPIXEL_PIN = 18
NEOPIXEL_COUNT = 8
IR_ACTIVE_LOW = True
OLED_SDA_PIN = 21
OLED_SCL_PIN = 22
OLED_I2C_ADDRESS = 0x3C
OLED_WIDTH = 128
OLED_HEIGHT = 64

DISPENSER_ANGLES = (55, 110, 165)
DISPENSER_SLOT_COUNT = len(DISPENSER_ANGLES)
REFILL_SEQUENCE = (55, 110, 165, 0)
SERVO_MAX_ANGLE = 180

PROXIMITY_HOLD_MS = 1000
SENSOR_COOLDOWN_MS = 3000
SERVO_STEP_SETTLE_MS = 850
RETURN_DELAY_MS = 30000
EMERGENCY_STEP_MS = 80
REMINDER_INTERVAL_MS = 5 * 60 * 1000
STATUS_INTERVAL_MS = 4000
OLED_UPDATE_INTERVAL_MS = 250

MEALS = (
    ("morning", "아침", 7 * 60, 9 * 60 + 30, 10 * 60),
    ("lunch", "점심", 11 * 60, 12 * 60 + 30, 13 * 60),
    ("evening", "저녁", 15 * 60, 16 * 60 + 30, 17 * 60),
)
MEAL_OLED_NAMES = ("MORNING", "LUNCH", "DINNER")
MEAL_OLED_RANGES = ("07AM - 10AM", "11AM - 01PM", "03PM - 05PM")

# ---------------------------------------------------------------------------
# Hardware
# ---------------------------------------------------------------------------

servo = machine.PWM(machine.Pin(SERVO_PIN), freq=50)
proximity = machine.Pin(PROXIMITY_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
pixels = neopixel.NeoPixel(machine.Pin(NEOPIXEL_PIN), NEOPIXEL_COUNT)
buzzer = None
oled = None

try:
    oled_i2c = machine.SoftI2C(
        sda=machine.Pin(OLED_SDA_PIN),
        scl=machine.Pin(OLED_SCL_PIN),
        freq=400000,
    )
    oled = SSD1306_I2C(
        OLED_WIDTH,
        OLED_HEIGHT,
        oled_i2c,
        OLED_I2C_ADDRESS,
    )
    print("[OLED] SSD1306 ready at 0x%02X" % OLED_I2C_ADDRESS)
except Exception as error:
    # The rest of the system remains usable while the OLED is disconnected.
    oled = None
    print("[OLED] not detected:", error)

ble = bluetooth.BLE()
p = BLESimplePeripheral(ble, BLE_DEVICE_NAME)


# ---------------------------------------------------------------------------
# Persistent and runtime state
# ---------------------------------------------------------------------------

nvs = esp32.NVS("pillume") if esp32 else None
taken_mask = 0
started_mask = 0
compartment_index = 0
stored_day_key = 0

neopixel_on = False
neopixel_color = (222, 238, 154)
neopixel_brightness = 70
current_servo_angle = 0
sensor_detected_at = None
sensor_triggered_for_presence = False
refill_active = False
refill_step = 0
time_synchronized = False
synced_epoch_seconds = 0
synced_at_ticks = 0
timezone_offset_minutes = 540
event_sequence = 0
command_queue = []

last_dispense_at = None
reset_due_at = None
buzzer_stop_at = None
emergency_until = None
emergency_last_step_at = 0
emergency_step = 0
last_status_at = 0
last_schedule_check_at = 0
last_reminder_at = [None, None, None]
last_oled_update_at = 0
last_oled_lines = None
test_mode = False
test_snapshot = None
test_slot = "morning"
test_action = ""
test_oled_lines = None
test_refill_step = 0


def _nvs_get(key, default=0):
    if not nvs:
        return default
    try:
        return nvs.get_i32(key)
    except OSError:
        return default


def load_state():
    global stored_day_key, taken_mask, started_mask, compartment_index
    stored_day_key = _nvs_get("day", 0)
    taken_mask = _nvs_get("taken", 0)
    started_mask = _nvs_get("started", 0)
    compartment_index = _nvs_get("comp", 0)
    if compartment_index < 0 or compartment_index > DISPENSER_SLOT_COUNT:
        compartment_index = 0


def persist_state():
    if not nvs:
        return
    nvs.set_i32("day", stored_day_key)
    nvs.set_i32("taken", taken_mask)
    nvs.set_i32("started", started_mask)
    nvs.set_i32("comp", compartment_index)
    nvs.commit()


# ---------------------------------------------------------------------------
# Local clock provided by the browser over BLE
# ---------------------------------------------------------------------------

def _civil_from_days(days_since_unix_epoch):
    # Howard Hinnant's civil_from_days algorithm.
    z = days_since_unix_epoch + 719468
    era = z // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    year = yoe + era * 400
    day_of_year = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * day_of_year + 2) // 153
    day = day_of_year - (153 * mp + 2) // 5 + 1
    month = mp + 3 if mp < 10 else mp - 9
    year += 1 if month <= 2 else 0
    return year, month, day


def current_epoch_seconds():
    if not time_synchronized:
        return None
    elapsed_ms = time.ticks_diff(time.ticks_ms(), synced_at_ticks)
    return synced_epoch_seconds + elapsed_ms // 1000


def local_clock():
    epoch = current_epoch_seconds()
    if epoch is None:
        return None
    local_seconds = epoch + timezone_offset_minutes * 60
    days = local_seconds // 86400
    seconds_of_day = local_seconds % 86400
    year, month, day = _civil_from_days(days)
    hour = seconds_of_day // 3600
    minute = (seconds_of_day % 3600) // 60
    second = seconds_of_day % 60
    return year, month, day, hour, minute, second


def local_iso_time():
    clock = local_clock()
    if not clock:
        return ""
    year, month, day, hour, minute, second = clock
    sign = "+" if timezone_offset_minutes >= 0 else "-"
    offset = abs(timezone_offset_minutes)
    return (
        "%04d-%02d-%02dT%02d:%02d:%02d%s%02d:%02d"
        % (
            year,
            month,
            day,
            hour,
            minute,
            second,
            sign,
            offset // 60,
            offset % 60,
        )
    )


def day_key(clock):
    return clock[0] * 10000 + clock[1] * 100 + clock[2]


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def draw_oled(lines):
    global last_oled_lines
    if oled is None:
        return
    normalized = tuple(str(line)[:16] for line in lines)
    if normalized == last_oled_lines:
        return
    last_oled_lines = normalized
    try:
        oled.fill(0)
        for index, line in enumerate(normalized[:5]):
            oled.text(line, 0, index * 12)
        oled.show()
    except Exception as error:
        print("[OLED] draw error:", error)


def update_oled():
    global last_oled_update_at
    if oled is None:
        return
    now = time.ticks_ms()
    if time.ticks_diff(now, last_oled_update_at) < OLED_UPDATE_INTERVAL_MS:
        return
    last_oled_update_at = now

    if emergency_until is not None:
        draw_oled(("!!! EMERGENCY !!!", "HELP NEEDED", "SIREN ACTIVE"))
        return

    if test_mode and test_oled_lines:
        draw_oled(test_oled_lines)
        return

    if refill_active:
        if refill_step <= 0:
            draw_oled(("REFILL MODE", "STARTING..."))
        elif refill_step < 3:
            draw_oled(
                (
                    "REFILL MODE",
                    "SLOT %d / 3" % refill_step,
                    "INSERT MEDICINE",
                    "PRESS NEXT",
                )
            )
        else:
            draw_oled(
                (
                    "REFILL MODE",
                    "SLOT 3 / 3",
                    "INSERT MEDICINE",
                    "PRESS TO FINISH",
                )
            )
        return

    clock = local_clock()
    if not clock:
        draw_oled(("PILLUME", "CONNECT ESP_SZ", "TO SYNC TIME"))
        return

    minute_of_day = clock[3] * 60 + clock[4]
    active = active_meal_index(minute_of_day)
    if active < 0:
        draw_oled(
            (
                "PILLUME READY",
                "TIME %02d:%02d" % (clock[3], clock[4]),
                "WAITING FOR",
                "MEDICINE TIME",
            )
        )
        return

    meal = MEALS[active]
    meal_taken = bool(taken_mask & (1 << active))
    reminder_active = (
        minute_of_day >= meal[3]
        and minute_of_day < meal[4]
        and not meal_taken
    )
    if reminder_active:
        draw_oled(
            (
                "PLEASE TAKE",
                "YOUR MEDICINE",
                MEAL_OLED_NAMES[active],
                MEAL_OLED_RANGES[active],
            )
        )
    elif meal_taken:
        draw_oled(
            (
                "MEDICINE TAKEN",
                MEAL_OLED_NAMES[active],
                MEAL_OLED_RANGES[active],
            )
        )
    else:
        draw_oled(
            (
                "MEDICINE TIME",
                MEAL_OLED_NAMES[active],
                MEAL_OLED_RANGES[active],
            )
        )

def servo_write(angle):
    global current_servo_angle
    angle = max(0, min(SERVO_MAX_ANGLE, int(angle)))
    pulse_us = 500 + (1900 * angle // 180)
    servo.duty_u16(pulse_us * 65535 // 20000)
    current_servo_angle = angle


def angle_for_compartment(index):
    if index <= 0:
        return 0
    return DISPENSER_ANGLES[min(index, DISPENSER_SLOT_COUNT) - 1]


def fill_pixels(color):
    for index in range(NEOPIXEL_COUNT):
        pixels[index] = color
    pixels.write()


def scaled_mood_color():
    return tuple(
        max(0, min(255, int(channel))) * neopixel_brightness // 100
        for channel in neopixel_color
    )


def restore_mood_light():
    fill_pixels(scaled_mood_color() if neopixel_on else (0, 0, 0))


def animate_blue_chase(duration_ms=SERVO_STEP_SETTLE_MS):
    if emergency_until is not None:
        time.sleep_ms(duration_ms)
        return
    frame_ms = max(40, duration_ms // max(1, NEOPIXEL_COUNT))
    for index in range(NEOPIXEL_COUNT):
        fill_pixels((0, 0, 0))
        pixels[index] = (0, 90, 255)
        pixels.write()
        time.sleep_ms(frame_ms)
    restore_mood_light()


def start_buzzer(duration_ms, frequency=2200):
    global buzzer, buzzer_stop_at
    if emergency_until is not None:
        return
    try:
        if buzzer is None:
            buzzer = machine.PWM(machine.Pin(BUZZER_PIN), freq=frequency)
        else:
            buzzer.freq(frequency)
        buzzer.duty_u16(32768)
        buzzer_stop_at = time.ticks_add(time.ticks_ms(), duration_ms)
    except Exception as error:
        # Leaving the piezo disconnected is supported.
        print("[BUZZER]", error)


def update_buzzer():
    global buzzer, buzzer_stop_at
    if emergency_until is not None:
        return
    if buzzer_stop_at is None:
        return
    if time.ticks_diff(time.ticks_ms(), buzzer_stop_at) >= 0:
        if buzzer is not None:
            buzzer.deinit()
        buzzer = None
        buzzer_stop_at = None


def set_mood_light(on, log_event=True):
    global neopixel_on
    neopixel_on = bool(on)
    if emergency_until is None:
        restore_mood_light()
    if log_event:
        publish_event(
            "NEOPIXEL_ON" if neopixel_on else "NEOPIXEL_OFF",
            "",
            0,
            "무드등 켜짐" if neopixel_on else "무드등 꺼짐",
        )


def set_light_settings(color, brightness, on=True):
    global neopixel_color, neopixel_brightness, neopixel_on

    if isinstance(color, str):
        clean = color.strip().lstrip("#")
        if len(clean) != 6:
            raise ValueError("color must be #RRGGBB")
        color = (
            int(clean[0:2], 16),
            int(clean[2:4], 16),
            int(clean[4:6], 16),
        )
    elif isinstance(color, (list, tuple)) and len(color) == 3:
        color = tuple(int(channel) for channel in color)
    else:
        raise ValueError("color must contain RGB values")

    neopixel_color = tuple(max(0, min(255, channel)) for channel in color)
    neopixel_brightness = max(1, min(100, int(brightness)))
    neopixel_on = bool(on)

    if emergency_until is None:
        restore_mood_light()

    publish_event(
        "LIGHT_UPDATED",
        "",
        0,
        "#%02X%02X%02X · %d%%" % (
            neopixel_color[0],
            neopixel_color[1],
            neopixel_color[2],
            neopixel_brightness,
        ),
    )


def start_emergency():
    global emergency_until, emergency_last_step_at, emergency_step
    global buzzer_stop_at
    # A non-None value means the alarm stays active until the web dashboard
    # explicitly sends an emergency_ack command.
    emergency_until = -1
    emergency_last_step_at = 0
    emergency_step = 0
    buzzer_stop_at = None


def acknowledge_emergency():
    global emergency_until, emergency_last_step_at, emergency_step
    global buzzer, buzzer_stop_at
    if emergency_until is None:
        return
    if buzzer is not None:
        buzzer.deinit()
    buzzer = None
    buzzer_stop_at = None
    emergency_until = None
    emergency_last_step_at = 0
    emergency_step = 0
    restore_mood_light()
    publish_event("EMERGENCY_CLEARED", "", 0, "웹에서 긴급 알림 확인")


def stop_alarm_without_event():
    global emergency_until, emergency_last_step_at, emergency_step
    global buzzer, buzzer_stop_at
    if buzzer is not None:
        try:
            buzzer.deinit()
        except Exception:
            pass
    buzzer = None
    buzzer_stop_at = None
    emergency_until = None
    emergency_last_step_at = 0
    emergency_step = 0


def update_emergency():
    global emergency_last_step_at, emergency_step
    global buzzer
    if emergency_until is None:
        return

    now = time.ticks_ms()
    if time.ticks_diff(now, emergency_last_step_at) < EMERGENCY_STEP_MS:
        return
    emergency_last_step_at = now
    emergency_step += 1

    # Fast up/down siren sweep.
    sweep = emergency_step % 20
    if sweep > 10:
        sweep = 20 - sweep
    frequency = 800 + sweep * 160
    try:
        if buzzer is None:
            buzzer = machine.PWM(machine.Pin(BUZZER_PIN), freq=frequency)
        else:
            buzzer.freq(frequency)
        buzzer.duty_u16(32768)
    except Exception as error:
        print("[BUZZER]", error)

    # Flash all NeoPixels red every 160 ms.
    fill_pixels((255, 0, 0) if (emergency_step // 2) % 2 == 0 else (0, 0, 0))


# ---------------------------------------------------------------------------
# BLE status and event protocol (compatible with the existing web dashboard)
# ---------------------------------------------------------------------------

def active_meal_index(minute_of_day):
    for index, meal in enumerate(MEALS):
        if meal[2] <= minute_of_day < meal[4]:
            return index
    return -1


def pending_dose_mask(minute_of_day):
    mask = 0
    for index, meal in enumerate(MEALS):
        if minute_of_day >= meal[2] and not (taken_mask & (1 << index)):
            mask |= 1 << index
    return mask


def pending_dose_count(minute_of_day):
    mask = pending_dose_mask(minute_of_day)
    return sum(1 for index in range(len(MEALS)) if mask & (1 << index))


def status_payload():
    clock = local_clock()
    active = -1
    pending = 0
    if clock:
        minute_of_day = clock[3] * 60 + clock[4]
        active = active_meal_index(minute_of_day)
        pending = pending_dose_count(minute_of_day)

    return {
        "online": True,
        "deviceId": DEVICE_ID,
        "bleName": BLE_DEVICE_NAME,
        "testModeSupported": True,
        "testModePolicy": "isolated-hardware-test",
        "testMode": test_mode,
        "testSlot": test_slot,
        "testAction": test_action,
        "timeSynced": time_synchronized,
        "time": local_iso_time(),
        "neopixel": neopixel_on,
        "lightColor": "#%02X%02X%02X" % neopixel_color,
        "lightBrightness": neopixel_brightness,
        "emergency": emergency_until is not None,
        "currentAngle": current_servo_angle,
        "compartmentIndex": compartment_index,
        "refillActive": refill_active,
        "refillStep": refill_step,
        "pendingDoses": pending,
        "activeSlot": MEALS[active][0] if active >= 0 else "",
        "taken": {
            "morning": bool(taken_mask & 0x01),
            "lunch": bool(taken_mask & 0x02),
            "evening": bool(taken_mask & 0x04),
        },
    }


def publish_status():
    try:
        p.send_status(ujson.dumps(status_payload()))
    except Exception as error:
        print("[BLE] status:", error)


def publish_event(event_type, meal_slot="", dose_count=0, message=""):
    global event_sequence
    event_sequence += 1
    event = {
        "seq": event_sequence,
        "deviceId": DEVICE_ID,
        "type": event_type,
        "doseCount": dose_count,
        "message": message,
    }
    if meal_slot:
        event["mealSlot"] = meal_slot
    timestamp = local_iso_time()
    if timestamp:
        event["deviceTime"] = timestamp
    payload = ujson.dumps(event)
    print(payload)
    try:
        p.send_event(payload)
    except Exception as error:
        print("[BLE] event:", error)
    publish_status()


# ---------------------------------------------------------------------------
# Medication logic
# ---------------------------------------------------------------------------

def reset_daily_state_if_needed(clock):
    global stored_day_key, taken_mask, started_mask, last_reminder_at
    today = day_key(clock)
    if today == stored_day_key:
        return
    stored_day_key = today
    taken_mask = 0
    started_mask = 0
    last_reminder_at = [None, None, None]
    persist_state()
    publish_event("NEW_DAY", "", 0, "새 날짜 복약 기록 시작")


def move_one_compartment():
    global compartment_index
    compartment_index += 1
    servo_write(angle_for_compartment(compartment_index))
    animate_blue_chase()


def advance_refill():
    global refill_active, refill_step, reset_due_at

    if emergency_until is not None:
        publish_event("REFILL_BLOCKED", "", 0, "긴급 알림 종료 후 다시 시도")
        return

    if not refill_active:
        if compartment_index != 0:
            publish_event(
                "REFILL_BLOCKED",
                "",
                0,
                "디스펜서가 0도일 때만 채우기 가능",
            )
            return
        refill_active = True
        refill_step = 0
        reset_due_at = None

    target_angle = REFILL_SEQUENCE[refill_step]
    servo_write(target_angle)
    animate_blue_chase()

    if target_angle == 0:
        refill_active = False
        refill_step = 0
        publish_event("REFILL_COMPLETE", "", 3, "3칸 채우기 완료: 0도 복귀")
        return

    refill_step += 1
    publish_event(
        "REFILL_POSITION",
        "",
        refill_step,
        "%d번 칸 위치 %d도: 약을 넣고 버튼을 다시 누르세요"
        % (refill_step, target_angle),
    )


def dispense_pending_doses(clock):
    global taken_mask, last_dispense_at, reset_due_at
    minute_of_day = clock[3] * 60 + clock[4]
    active = active_meal_index(minute_of_day)
    if active < 0:
        start_buzzer(250, 900)
        publish_event("OUTSIDE_WINDOW", "", 0, "복약 가능 시간대 아님")
        return

    due_mask = pending_dose_mask(minute_of_day)
    dose_count = sum(
        1 for index in range(len(MEALS)) if due_mask & (1 << index)
    )
    if dose_count == 0:
        start_buzzer(220, 1100)
        publish_event("ALREADY_TAKEN", MEALS[active][0], 0, "이미 복용 완료")
        return

    remaining = DISPENSER_SLOT_COUNT - compartment_index
    if dose_count > remaining:
        start_buzzer(3000, 700)
        publish_event(
            "REFILL_REQUIRED",
            MEALS[active][0],
            dose_count,
            "남은 칸 부족",
        )
        return

    due_indices = [
        index
        for index in range(len(MEALS))
        if due_mask & (1 << index)
    ]
    for index in due_indices:
        move_one_compartment()
        taken_mask |= 1 << index
        persist_state()
        publish_event(
            "DOSE_TAKEN",
            MEALS[index][0],
            1,
            MEALS[index][1] + " 복용 완료",
        )

    last_dispense_at = time.ticks_ms()
    start_buzzer(180, 2600)

    if compartment_index >= DISPENSER_SLOT_COUNT:
        reset_due_at = time.ticks_add(time.ticks_ms(), RETURN_DELAY_MS)
        publish_event(
            "DISPENSER_FULL_CYCLE",
            MEALS[active][0],
            DISPENSER_SLOT_COUNT,
            "165도 도달",
        )


def update_dispenser_reset():
    global compartment_index, reset_due_at
    if refill_active:
        return
    if reset_due_at is None:
        return
    if time.ticks_diff(time.ticks_ms(), reset_due_at) < 0:
        return
    servo_write(0)
    animate_blue_chase()
    compartment_index = 0
    reset_due_at = None
    persist_state()
    publish_event("DISPENSER_RESET", "", 0, "서보 0도 원복 완료")


def update_schedule():
    global last_schedule_check_at, started_mask
    now = time.ticks_ms()
    if time.ticks_diff(now, last_schedule_check_at) < 1000:
        return
    last_schedule_check_at = now

    clock = local_clock()
    if not clock:
        return
    reset_daily_state_if_needed(clock)
    minute_of_day = clock[3] * 60 + clock[4]

    for index, meal in enumerate(MEALS):
        bit = 1 << index
        if (
            meal[2] <= minute_of_day < meal[4]
            and not (started_mask & bit)
        ):
            started_mask |= bit
            persist_state()
            start_buzzer(3000)
            publish_event(
                "WINDOW_STARTED",
                meal[0],
                0,
                meal[1] + " 복약 시간 시작",
            )

        needs_reminder = (
            meal[3] <= minute_of_day < meal[4]
            and not (taken_mask & bit)
        )
        last = last_reminder_at[index]
        if needs_reminder and (
            last is None
            or time.ticks_diff(now, last) >= REMINDER_INTERVAL_MS
        ):
            last_reminder_at[index] = now
            start_buzzer(1800, 1800)
            publish_event(
                "MISSED_REMINDER",
                meal[0],
                0,
                meal[1] + " 약 미복용",
            )


def proximity_detected():
    raw_high = proximity.value() == 1
    return not raw_high if IR_ACTIVE_LOW else raw_high


def update_proximity_sensor():
    global sensor_detected_at, sensor_triggered_for_presence
    detected = proximity_detected()
    now = time.ticks_ms()
    if refill_active:
        sensor_detected_at = None
        sensor_triggered_for_presence = False
        return
    if not detected:
        sensor_detected_at = None
        sensor_triggered_for_presence = False
        return

    if sensor_detected_at is None:
        sensor_detected_at = now
        return

    if (
        not sensor_triggered_for_presence
        and time.ticks_diff(now, sensor_detected_at) >= PROXIMITY_HOLD_MS
    ):
        sensor_triggered_for_presence = True
        cooldown_ready = (
            last_dispense_at is None
            or time.ticks_diff(now, last_dispense_at) >= SENSOR_COOLDOWN_MS
        )
        if cooldown_ready:
            clock = local_clock()
            if clock:
                dispense_pending_doses(clock)
            else:
                start_buzzer(600, 800)
                publish_event(
                    "TIME_UNAVAILABLE",
                    "",
                    0,
                    "BLE 시간 동기화 필요",
                )


# ---------------------------------------------------------------------------
# Incoming browser commands
# ---------------------------------------------------------------------------

def synchronize_time(epoch, offset_minutes):
    global synced_epoch_seconds, synced_at_ticks
    global timezone_offset_minutes, time_synchronized
    if epoch < 1700000000:
        return
    synced_epoch_seconds = int(epoch)
    synced_at_ticks = time.ticks_ms()
    timezone_offset_minutes = max(-720, min(840, int(offset_minutes)))
    time_synchronized = True
    clock = local_clock()
    if clock:
        reset_daily_state_if_needed(clock)
    publish_event("TIME_SYNCED", "", 0, "브라우저 시간 동기화 완료")


def handle_motion(command, label="", confidence=0):
    command = str(command).upper()
    if command == "ON":
        set_mood_light(True)
    elif command == "OFF":
        set_mood_light(False)
    elif command == "EMERGENCY":
        if emergency_until is None:
            start_emergency()
            publish_event(
                "EMERGENCY",
                "",
                0,
                "X 동작 %s %d%%" % (label, int(float(confidence) * 100)),
            )


def test_slot_info(slot):
    mapping = {
        "morning": ("MORNING", "07:00 - 10:00", 1),
        "lunch": ("LUNCH", "11:00 - 13:00", 2),
        "evening": ("EVENING", "15:00 - 17:00", 3),
    }
    return mapping.get(slot, mapping["morning"])


def set_test_display(title, *lines):
    global test_oled_lines, last_oled_lines
    test_oled_lines = tuple([title] + list(lines))
    last_oled_lines = None


def test_servo_preview(count):
    count = max(1, min(3, int(count)))
    for index in range(count):
        servo_write(DISPENSER_ANGLES[index])
        animate_blue_chase()


def enter_test_mode():
    global test_mode, test_snapshot, test_action, test_refill_step
    global refill_active, refill_step, reset_due_at
    if test_mode:
        return
    if emergency_until is not None:
        print("[TEST] refused while real emergency is active")
        return
    test_snapshot = {
        "angle": current_servo_angle,
        "compartment": compartment_index,
        "light_on": neopixel_on,
        "light_color": neopixel_color,
        "light_brightness": neopixel_brightness,
        "refill_active": refill_active,
        "refill_step": refill_step,
        "reset_due_at": reset_due_at,
    }
    test_mode = True
    test_action = "enter"
    test_refill_step = 0
    refill_active = False
    refill_step = 0
    reset_due_at = None
    stop_alarm_without_event()
    set_test_display("TEST MODE", "HARDWARE ACTIVE", "NO RECORD SAVED")
    publish_status()


def exit_test_mode():
    global test_mode, test_snapshot, test_action, test_oled_lines
    global test_refill_step, compartment_index, neopixel_on
    global neopixel_color, neopixel_brightness, refill_active, refill_step
    global reset_due_at, last_oled_lines
    if not test_mode:
        return
    snapshot = test_snapshot or {}
    stop_alarm_without_event()
    servo_write(snapshot.get("angle", 0))
    compartment_index = snapshot.get("compartment", compartment_index)
    neopixel_on = snapshot.get("light_on", neopixel_on)
    neopixel_color = snapshot.get("light_color", neopixel_color)
    neopixel_brightness = snapshot.get("light_brightness", neopixel_brightness)
    refill_active = snapshot.get("refill_active", False)
    refill_step = snapshot.get("refill_step", 0)
    reset_due_at = snapshot.get("reset_due_at", None)
    restore_mood_light()
    test_mode = False
    test_snapshot = None
    test_action = ""
    test_oled_lines = None
    test_refill_step = 0
    last_oled_lines = None
    publish_status()


def handle_test_command(command):
    global test_slot, test_action, test_refill_step, neopixel_on
    action = str(command.get("action", "")).lower()
    if action == "enter":
        enter_test_mode()
        return
    if action == "exit":
        exit_test_mode()
        return
    if not test_mode:
        print("[TEST] enter command required")
        return

    slot = str(command.get("slot", test_slot)).lower()
    if slot in ("morning", "lunch", "evening"):
        test_slot = slot
    name, hours, count = test_slot_info(test_slot)
    test_action = action

    if action == "set_time":
        set_test_display("TEST MODE", name, hours, "SELECT SCENARIO")
    elif action == "window":
        start_buzzer(3000)
        set_test_display("MEDICINE TIME", name, hours, "TEST ONLY")
    elif action == "taken":
        test_servo_preview(count)
        set_test_display("MEDICINE TAKEN", name, "%d DOSE PREVIEW" % count, "TEST ONLY")
    elif action == "reminder":
        start_buzzer(2500, 1800)
        set_test_display("PLEASE TAKE", "YOUR MEDICINE", name, hours)
    elif action == "backlog":
        test_servo_preview(count)
        set_test_display("BACKLOG TEST", "%d DOSES" % count, name, "NO RECORD SAVED")
    elif action == "light":
        neopixel_on = not neopixel_on
        restore_mood_light()
        set_test_display("MOOD LIGHT TEST", "ON" if neopixel_on else "OFF", "TEST ONLY")
    elif action == "motion":
        motion = str(command.get("command", "")).upper()
        if motion == "EMERGENCY":
            start_emergency()
            set_test_display("EMERGENCY TEST", "ACK TO STOP")
        elif motion in ("ON", "OFF"):
            neopixel_on = motion == "ON"
            restore_mood_light()
            set_test_display("MOOD LIGHT TEST", motion, "TEST ONLY")
    elif action == "refill":
        test_refill_step = (test_refill_step + 1) % 4
        servo_write((0, 55, 110, 165)[test_refill_step])
        animate_blue_chase()
        set_test_display(
            "REFILL TEST",
            "HOME 0 DEG" if test_refill_step == 0 else "SLOT %d / 3" % test_refill_step,
            "TEST ONLY",
        )
    elif action == "emergency":
        start_emergency()
        set_test_display("EMERGENCY TEST", "ACK TO STOP")
    elif action == "emergency_ack":
        stop_alarm_without_event()
        restore_mood_light()
        set_test_display("EMERGENCY CLEAR", "TEST MODE", "SELECT SCENARIO")
    elif action == "reset":
        stop_alarm_without_event()
        servo_write(0)
        test_refill_step = 0
        restore_mood_light()
        set_test_display("TEST RESET", name, hours, "SELECT SCENARIO")
    publish_status()


def process_command(value):
    try:
        command = ujson.loads(value.decode())
        command_type = command.get("type", "")
        if command_type == "test" and command.get("testOnly", False):
            handle_test_command(command)
            return
        if command.get("testOnly", False):
            print("[TEST] invalid isolated command ignored")
            return
        if command_type == "time":
            synchronize_time(
                int(command.get("epoch", 0)),
                int(command.get("tzOffsetMinutes", 540)),
            )
        elif command_type == "motion":
            handle_motion(
                command.get("command", ""),
                command.get("label", ""),
                command.get("confidence", 0),
            )
        elif command_type == "light":
            set_light_settings(
                command.get("color", "#DEEE9A"),
                command.get("brightness", 70),
                command.get("on", True),
            )
        elif command_type == "emergency_ack":
            acknowledge_emergency()
        elif command_type == "refill":
            advance_refill()
        elif command_type == "status":
            publish_status()
    except Exception as error:
        print("[BLE] invalid command:", error)


def on_rx(value):
    # Keep the BLE IRQ callback short. Hardware work is done in the main loop.
    if len(command_queue) < 8:
        command_queue.append(value)


# ---------------------------------------------------------------------------
# Boot and main loop
# ---------------------------------------------------------------------------

load_state()
servo_write(angle_for_compartment(compartment_index))
set_mood_light(False, False)
p.on_write(on_rx)
if compartment_index >= DISPENSER_SLOT_COUNT:
    reset_due_at = time.ticks_add(time.ticks_ms(), RETURN_DELAY_MS)
publish_status()
print("[SYSTEM] ESP_SZ MicroPython firmware ready")

while True:
    if command_queue:
        process_command(command_queue.pop(0))
    update_emergency()
    update_buzzer()
    if not test_mode:
        update_schedule()
        update_proximity_sensor()
        update_dispenser_reset()
    update_oled()

    now = time.ticks_ms()
    if p.is_connected() and time.ticks_diff(now, last_status_at) >= STATUS_INTERVAL_MS:
        last_status_at = now
        publish_status()

    time.sleep_ms(5)
