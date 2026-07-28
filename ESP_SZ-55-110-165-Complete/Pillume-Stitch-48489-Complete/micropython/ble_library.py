"""ESP_SZ BLE peripheral helper for MicroPython ESP32.

The public API intentionally matches the simple form requested by the project:

    ble = bluetooth.BLE()
    p = BLESimplePeripheral(ble, "ESP_SZ")
    p.on_write(callback)
"""

import bluetooth
from micropython import const


_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

SERVICE_UUID = bluetooth.UUID("7c8e4001-9f8b-4f44-a18f-64a6f6a50101")
COMMAND_UUID = bluetooth.UUID("7c8e4002-9f8b-4f44-a18f-64a6f6a50101")
STATUS_UUID = bluetooth.UUID("7c8e4003-9f8b-4f44-a18f-64a6f6a50101")
EVENT_UUID = bluetooth.UUID("7c8e4004-9f8b-4f44-a18f-64a6f6a50101")

_COMMAND_CHAR = (
    COMMAND_UUID,
    _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,
)
_STATUS_CHAR = (
    STATUS_UUID,
    _FLAG_READ | _FLAG_NOTIFY,
)
_EVENT_CHAR = (
    EVENT_UUID,
    _FLAG_READ | _FLAG_NOTIFY,
)
_SERVICE = (
    SERVICE_UUID,
    (_COMMAND_CHAR, _STATUS_CHAR, _EVENT_CHAR),
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
    """Small BLE GATT server used by the Pillume browser dashboard."""

    def __init__(self, ble, name="ESP_SZ"):
        self._ble = ble
        self._name = name
        self._connections = set()
        self._write_callback = None

        self._ble.active(True)
        try:
            # The browser/OS still decides the final negotiated MTU.
            self._ble.config(mtu=247)
        except (ValueError, OSError):
            pass

        self._ble.irq(self._irq)
        (
            self._command_handle,
            self._status_handle,
            self._event_handle,
        ) = self._ble.gatts_register_services((_SERVICE,))[0]

        # MicroPython's default characteristic buffer is only 20 bytes.
        self._ble.gatts_set_buffer(self._command_handle, 512, False)
        self._ble.gatts_set_buffer(self._status_handle, 512, False)
        self._ble.gatts_set_buffer(self._event_handle, 512, False)

        self._payload = _advertising_payload(name, SERVICE_UUID)
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
            conn_handle, value_handle = data
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

