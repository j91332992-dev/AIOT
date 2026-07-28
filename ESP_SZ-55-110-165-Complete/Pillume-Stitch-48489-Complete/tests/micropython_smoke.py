"""CPython smoke harness for the MicroPython-only main.py boot path."""

import runpy
import json
import sys
import time
import types


micropython = types.ModuleType("micropython")
micropython.const = lambda value: value
sys.modules["micropython"] = micropython

ujson = types.ModuleType("ujson")
ujson.dumps = json.dumps
ujson.loads = json.loads
sys.modules["ujson"] = ujson


class FrameBuffer:
    def __init__(self, *_args):
        pass

    def fill(self, _color):
        return None

    def text(self, *_args):
        return None


framebuf = types.ModuleType("framebuf")
framebuf.MONO_VLSB = 0
framebuf.FrameBuffer = FrameBuffer
sys.modules["framebuf"] = framebuf


class UUID:
    def __init__(self, value):
        self.value = value

    def __bytes__(self):
        return bytes(16)


class BLE:
    def active(self, _value):
        return True

    def config(self, **_kwargs):
        return None

    def irq(self, callback):
        self.callback = callback

    def gatts_register_services(self, _services):
        return ((1, 2, 3),)

    def gatts_set_buffer(self, *_args):
        return None

    def gap_advertise(self, *_args, **_kwargs):
        return None

    def gatts_write(self, *_args):
        return None

    def gatts_notify(self, *_args):
        return None

    def gatts_read(self, _handle):
        return b""


bluetooth = types.ModuleType("bluetooth")
bluetooth.UUID = UUID
bluetooth.BLE = BLE
sys.modules["bluetooth"] = bluetooth


class Pin:
    IN = 0
    PULL_UP = 1

    def __init__(self, number, *_args):
        self.number = number

    def value(self):
        return 1


class PWM:
    def __init__(self, _pin, freq=50):
        self.frequency = freq

    def freq(self, value):
        self.frequency = value

    def duty_u16(self, _value):
        return None

    def deinit(self):
        return None


class SoftI2C:
    def __init__(self, **_kwargs):
        pass

    def writeto(self, *_args):
        return None

    def writevto(self, *_args):
        return None


machine = types.ModuleType("machine")
machine.Pin = Pin
machine.PWM = PWM
machine.SoftI2C = SoftI2C
sys.modules["machine"] = machine


class NeoPixel:
    def __init__(self, _pin, count):
        self.values = [(0, 0, 0)] * count

    def __setitem__(self, index, value):
        self.values[index] = value

    def write(self):
        return None


neopixel = types.ModuleType("neopixel")
neopixel.NeoPixel = NeoPixel
sys.modules["neopixel"] = neopixel


class NVS:
    def __init__(self, _namespace):
        self.values = {}

    def get_i32(self, key):
        if key not in self.values:
            raise OSError
        return self.values[key]

    def set_i32(self, key, value):
        self.values[key] = value

    def commit(self):
        return None


esp32 = types.ModuleType("esp32")
esp32.NVS = NVS
sys.modules["esp32"] = esp32


ticks = 0
sleep_calls = 0


def ticks_ms():
    global ticks
    ticks += 10
    return ticks


def sleep_ms(_milliseconds):
    global sleep_calls
    sleep_calls += 1
    if sleep_calls >= 5:
        raise SystemExit


time.ticks_ms = ticks_ms
time.ticks_add = lambda value, delta: value + delta
time.ticks_diff = lambda value, reference: value - reference
time.sleep_ms = sleep_ms


try:
    runpy.run_path("micropython/main.py", run_name="__main__")
except SystemExit:
    print("MICROPYTHON_BOOT_SMOKE_OK")
